import os
import re
import csv
import time
import hashlib
import sqlite3
import logging
from contextlib import closing
from pathlib import Path
from typing import Optional

import pytz
from datetime import datetime

from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, AIORateLimiter
)

import messages as M

# ----- LOG -----
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("savitri-bot")

# ----- CONFIG -----
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMINS = {int(x.strip()) for x in os.getenv("ADMINS", "").split(",") if x.strip()}
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
PROJECT_NAME = os.getenv("PROJECT_NAME", "Savitri_Rewards")

DATA_DIR = Path("data"); DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "rewards.db"
MEDIA_DIR = DATA_DIR / "media"; MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Deadline: 30/11/2025 Europe/London
TZ = pytz.timezone("Europe/London")
DEADLINE = TZ.localize(datetime(2025, 11, 30, 23, 59, 59))

# ----- REGEX -----
WALLET_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
SIG_RE = re.compile(r"^0x[a-fA-F0-9]{130}$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")

# ----- DB -----
def init_db():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        # winners whitelist with position/xp/wallet, WVC and audit fields
        cur.execute("""
        CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            tg_id INTEGER,
            rank INTEGER,
            xp INTEGER,
            wallet TEXT,
            pending_new_wallet TEXT,
            wvc TEXT,
            wvc_used INTEGER DEFAULT 0,
            old_wallet_sig TEXT,
            old_wallet_hash TEXT,
            new_wallet_sig TEXT,
            new_wallet_hash TEXT,
            reg_sig TEXT,
            reg_hash TEXT
        );
        """)
        # proofs (Zealy screenshots)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS proofs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            file_id TEXT,
            file_hash TEXT,
            created_at INTEGER
        );
        """)
        con.commit()

def db_exec(q, p=()):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(q, p)
        con.commit()

def db_one(q, p=()):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(q, p)
        return cur.fetchone()

def upsert_winner(username: str, tg_id: Optional[int] = None, rank: Optional[int] = None,
                  xp: Optional[int] = None, wallet: Optional[str] = None,
                  wvc: Optional[str] = None, wvc_used: Optional[int] = None):
    row = db_one("SELECT id FROM winners WHERE username=?", (username.lower(),))
    sets, vals = [], []
    if tg_id is not None:
        sets.append("tg_id=?"); vals.append(int(tg_id))
    if rank is not None:
        sets.append("rank=?"); vals.append(int(rank))
    if xp is not None:
        sets.append("xp=?"); vals.append(int(xp))
    if wallet is not None:
        sets.append("wallet=?"); vals.append(wallet)
    if wvc is not None:
        sets.append("wvc=?"); vals.append(wvc)
    if wvc_used is not None:
        sets.append("wvc_used=?"); vals.append(int(wvc_used))
    if row:
        if sets:
            db_exec(f"UPDATE winners SET {', '.join(sets)} WHERE username=?", (*vals, username.lower()))
    else:
        db_exec(
            "INSERT INTO winners (username, tg_id, rank, xp, wallet, wvc, wvc_used) VALUES (?,?,?,?,?,?,?)",
            (username.lower(), tg_id, rank, xp, wallet, wvc, wvc_used if wvc_used is not None else 0)
        )

# ----- HELPERS -----
def now_local() -> datetime:
    return datetime.now(TZ)

def deadline_str() -> str:
    return DEADLINE.strftime("%d/%m/%Y")

def past_deadline() -> bool:
    return now_local() > DEADLINE

def sha256_hex(text: str) -> str:
    return "0x" + hashlib.sha256(text.encode("utf-8")).hexdigest()

def verify_personal_sign(expected_address: str, signature: str, message: str) -> bool:
    try:
        msg = encode_defunct(text=message)
        recovered = Account.recover_message(msg, signature=signature)
        return recovered.lower() == expected_address.lower()
    except Exception:
        return False

def photo_sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def is_admin(uid: int) -> bool:
    return uid in ADMINS

def is_whitelisted(username: str) -> bool:
    return db_one("SELECT id FROM winners WHERE username=?", (username.lower(),)) is not None

def get_current_user_row(tg_id: int):
    return db_one("SELECT username, rank, xp, wallet, wvc, wvc_used FROM winners WHERE tg_id=?", (tg_id,))

def user_requires_wvc(username: str) -> bool:
    row = db_one("SELECT wvc, wvc_used FROM winners WHERE username=?", (username.lower(),))
    if not row:
        return False
    wvc, used = row
    return bool(wvc) and not bool(used)

# robust int parsing for rank/XP like '#1', '1st', '1,234'
def _to_int_safe(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    m = re.search(r'[-+]?\d+', s.replace(',', ' ').replace('.', ' '))
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None

# clean wallet string and validate
def clean_wallet(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = str(v).replace('\u00A0', ' ').strip()  # remove NBSP
    s = s.replace(' ', '').strip("`'\"").lower()  # strip spaces/quotes
    return s if re.fullmatch(r"0x[a-f0-9]{40}", s) else None

# ----- COMMANDS -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(M.msg_start_request_username(), parse_mode=ParseMode.MARKDOWN)

async def set_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(M.msg_username_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    u = context.args[0].strip()
    if not USERNAME_RE.match(u):
        await update.message.reply_text(M.msg_username_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    upsert_winner(u, tg_id=update.effective_user.id)
    await update.message.reply_text(M.msg_username_saved(u), parse_mode=ParseMode.MARKDOWN)

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = get_current_user_row(update.effective_user.id)
    if not row:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    username, rank, xp, wallet, wvc, wvc_used = row
    await update.message.reply_text(
        M.msg_status(username, rank, xp, wallet, deadline_str(), wvc, wvc_used),
        parse_mode=ParseMode.MARKDOWN
    )

# --- WVC user commands ---
async def show_wvc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = get_current_user_row(update.effective_user.id)
    if not row:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    _, _, _, _, wvc, used = row
    await update.message.reply_text(M.msg_show_wvc(wvc, used), parse_mode=ParseMode.MARKDOWN)

async def use_wvc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(M.msg_command_usage("Usage: `/use_wvc <code>`"), parse_mode=ParseMode.MARKDOWN)
        return
    code = context.args[0].strip()
    row = get_current_user_row(update.effective_user.id)
    if not row:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    username, *_rest, wvc, used = row
    if not wvc or used:
        await update.message.reply_text(M.msg_show_wvc(wvc, used), parse_mode=ParseMode.MARKDOWN)
        return
    if code != wvc:
        await update.message.reply_text(M.msg_wvc_invalid(), parse_mode=ParseMode.MARKDOWN)
        return
    db_exec("UPDATE winners SET wvc_used=1 WHERE username=?", (username.lower(),))
    await update.message.reply_text(M.msg_wvc_ok(code), parse_mode=ParseMode.MARKDOWN)

# --- Registration flow ---
async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if past_deadline():
        await update.message.reply_text(M.msg_after_deadline(deadline_str()), parse_mode=ParseMode.MARKDOWN)
        return
    row = get_current_user_row(update.effective_user.id)
    if not row:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    username, _, _, _, wvc, used = row
    need_wvc = bool(wvc) and not bool(used)
    await update.message.reply_text(
        M.msg_add_wallet_guide(username, deadline_str(), need_wvc),
        parse_mode=ParseMode.MARKDOWN
    )

async def proof_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(M.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)
        return
    photo = update.message.photo[-1]
    f = await photo.get_file()
    b = await f.download_as_bytearray()
    digest = photo_sha256(bytes(b))
    db_exec("INSERT INTO proofs (tg_id, file_id, file_hash, created_at) VALUES (?,?,?,?)",
            (update.effective_user.id, photo.file_id, digest, int(time.time())))
    await update.message.reply_text(M.msg_proof_ok(), parse_mode=ParseMode.MARKDOWN)

async def set_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if past_deadline():
        await update.message.reply_text(M.msg_after_deadline(deadline_str()), parse_mode=ParseMode.MARKDOWN)
        return
    if len(context.args) != 1:
        await update.message.reply_text(M.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    candidate = clean_wallet(context.args[0])
    if not candidate:
        await update.message.reply_text(M.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    row = get_current_user_row(update.effective_user.id)
    if not row:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    username, _, _, _, wvc, used = row
    if bool(wvc) and not bool(used):
        await update.message.reply_text(M.msg_wvc_required(), parse_mode=ParseMode.MARKDOWN)
        return
    upsert_winner(username, wallet=candidate)
    await update.message.reply_text(M.msg_set_wallet_ok(candidate, username), parse_mode=ParseMode.MARKDOWN)

async def reg_sig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if past_deadline():
        await update.message.reply_text(M.msg_after_deadline(deadline_str()), parse_mode=ParseMode.MARKDOWN)
        return
    if len(context.args) != 1 or not SIG_RE.match(context.args[0].strip()):
        await update.message.reply_text(M.msg_sig_invalid(), parse_mode=ParseMode.MARKDOWN)
        return
    sig = context.args[0].strip()
    row = get_current_user_row(update.effective_user.id)
    if not row or not row[3]:
        await update.message.reply_text(M.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    username, _, _, wallet, wvc, used = row
    if bool(wvc) and not bool(used):
        await update.message.reply_text(M.msg_wvc_required(), parse_mode=ParseMode.MARKDOWN)
        return
    message = (
        f"Wallet registration — Zealy: {username} — Wallet: {wallet}\n"
        "I declare that I request the registration of the wallet indicated above and release Savitri Network from any liability in case of my own mistake."
    )
    if not verify_personal_sign(wallet, sig, message):
        await update.message.reply_text(M.msg_sig_invalid(), parse_mode=ParseMode.MARKDOWN)
        return
    h = sha256_hex(message)
    db_exec("UPDATE winners SET reg_sig=?, reg_hash=? WHERE username=?", (sig, h, username.lower()))
    await update.message.reply_text(M.msg_reg_sig_ok(wallet, h), parse_mode=ParseMode.MARKDOWN)
    if ADMIN_GROUP_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=M.admin_notify_registration(username, update.effective_user.id, wallet, sig, h),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

# --- Change flow ---
async def change_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if past_deadline():
        await update.message.reply_text(M.msg_after_deadline(deadline_str()), parse_mode=ParseMode.MARKDOWN)
        return
    row = get_current_user_row(update.effective_user.id)
    if not row or not row[3]:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    username, _, _, old_wallet, wvc, used = row
    need_wvc = bool(wvc) and not bool(used)
    await update.message.reply_text(
        M.msg_change_wallet_guide(username, old_wallet, deadline_str(), need_wvc),
        parse_mode=ParseMode.MARKDOWN
    )

async def old_sig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if past_deadline():
        await update.message.reply_text(M.msg_after_deadline(deadline_str()), parse_mode=ParseMode.MARKDOWN)
        return
    if len(context.args) != 1 or not SIG_RE.match(context.args[0].strip()):
        await update.message.reply_text(M.msg_sig_invalid(), parse_mode=ParseMode.MARKDOWN)
        return
    sig = context.args[0].strip()
    row = get_current_user_row(update.effective_user.id)
    if not row or not row[3]:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    username, _, _, old_wallet, wvc, used = row
    if bool(wvc) and not bool(used):
        await update.message.reply_text(M.msg_wvc_required(), parse_mode=ParseMode.MARKDOWN)
        return
    message = f"Wallet change request — Zealy: {username} — Old: {old_wallet}"
    if not verify_personal_sign(old_wallet, sig, message):
        await update.message.reply_text(M.msg_sig_invalid(), parse_mode=ParseMode.MARKDOWN)
        return
    h = sha256_hex(message)
    db_exec("UPDATE winners SET old_wallet_sig=?, old_wallet_hash=? WHERE username=?",
            (sig, h, username.lower()))
    await update.message.reply_text(M.msg_old_sig_ok(h), parse_mode=ParseMode.MARKDOWN)
    if ADMIN_GROUP_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=M.admin_notify_change(username, update.effective_user.id, old_wallet, "pending", sig, h),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

async def new_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if past_deadline():
        await update.message.reply_text(M.msg_after_deadline(deadline_str()), parse_mode=ParseMode.MARKDOWN)
        return
    if len(context.args) != 1:
        await update.message.reply_text(M.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    cand = clean_wallet(context.args[0])
    if not cand:
        await update.message.reply_text(M.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    row = get_current_user_row(update.effective_user.id)
    if not row or not row[3]:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    username, _, _, old_wallet, wvc, used = row
    if bool(wvc) and not bool(used):
        await update.message.reply_text(M.msg_wvc_required(), parse_mode=ParseMode.MARKDOWN)
        return
    db_exec("UPDATE winners SET pending_new_wallet=? WHERE username=?", (cand, username.lower()))
    await update.message.reply_text(M.msg_new_wallet_ok(cand, username, old_wallet), parse_mode=ParseMode.MARKDOWN)

async def new_sig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if past_deadline():
        await update.message.reply_text(M.msg_after_deadline(deadline_str()), parse_mode=ParseMode.MARKDOWN)
        return
    if len(context.args) != 1 or not SIG_RE.match(context.args[0].strip()):
        await update.message.reply_text(M.msg_sig_invalid(), parse_mode=ParseMode.MARKDOWN)
        return
    sig = context.args[0].strip()
    row = db_one("SELECT username, wallet, pending_new_wallet, wvc, wvc_used FROM winners WHERE tg_id=?", (update.effective_user.id,))
    if not row:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    username, old_wallet, pending_new, wvc, used = row
    if not old_wallet or not pending_new:
        await update.message.reply_text(M.msg_not_whitelisted(), parse_mode=ParseMode.MARKDOWN)
        return
    if bool(wvc) and not bool(used):
        await update.message.reply_text(M.msg_wvc_required(), parse_mode=ParseMode.MARKDOWN)
        return

    message = f"Wallet change request — Zealy: {username} — Old: {old_wallet} — New: {pending_new}"
    if not verify_personal_sign(pending_new, sig, message):
        await update.message.reply_text(M.msg_sig_invalid(), parse_mode=ParseMode.MARKDOWN)
        return

    h = sha256_hex(message)
    db_exec(
        "UPDATE winners SET wallet=?, pending_new_wallet=NULL, new_wallet_sig=?, new_wallet_hash=? WHERE username=?",
        (pending_new, sig, h, username.lower())
    )
    await update.message.reply_text(M.msg_new_sig_ok(old_wallet, pending_new, h), parse_mode=ParseMode.MARKDOWN)

    if ADMIN_GROUP_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=M.admin_notify_change(username, update.effective_user.id, old_wallet, pending_new, sig, h),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass

# --- Admin: import winners CSV (supports ; or ,)
# Expects columns (case/space tolerant):
# "Username", "binance smart chain address", "WVC", "Position on leadborad"/"Position on leaderboard", "XP"
def _norm(h: str) -> str:
    """normalize header: lowercase, strip spaces, collapse inner spaces, remove trailing punctuation"""
    return re.sub(r"\s+", " ", (h or "").strip().strip(":").lower())

def sniff_delim_from_sample(sample: str) -> str:
    first = sample.splitlines()[0] if sample else ""
    return ";" if first.count(";") >= first.count(",") else ","

async def admin_import_winners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not update.message or not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text(
            "📎 Reply to the CSV message with `/admin_import_winners`.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    doc = update.message.reply_to_message.document
    f = await doc.get_file()
    dest = DATA_DIR / f"import_{int(time.time())}_{doc.file_name}"
    await f.download_to_drive(str(dest))

    inserted = 0
    preview_rows = []
    try:
        with dest.open("r", encoding="utf-8-sig", newline="") as fh:
            sample = fh.read(4096); fh.seek(0)
            delim = sniff_delim_from_sample(sample)
            reader = csv.DictReader(fh, delimiter=delim)
            if not reader.fieldnames:
                await update.message.reply_text("❌ CSV has no headers.")
                return

            # mappa normalizzata -> originale
            headers = { _norm(h): h for h in reader.fieldnames }

            # alias possibili
            username_key = headers.get("username") or headers.get("user")
            rank_key = headers.get("position on leadborad") or headers.get("position on leaderboard") or headers.get("rank")
            xp_key = headers.get("xp") or headers.get("xp on zealy") or headers.get("zealy xp")
            wallet_key = (
                headers.get("binance smart chain address")
                or headers.get("bsc wallet")
                or headers.get("bsc address")
                or headers.get("bsc")
                or headers.get("wallet bsc")
            )
            wvc_key = headers.get("wvc")

            # 1° messaggio: delimiter + intestazioni
            header_text = "Detected delimiter: `{}`\nHeaders:\n{}".format(
                delim,
                "\n".join(f"- {h}" for h in reader.fieldnames)
            )
            await update.message.reply_text(header_text, parse_mode=ParseMode.MARKDOWN)

            # parsing righe
            for i, row in enumerate(reader, start=1):
                u = (row.get(username_key) or "").strip() if username_key else ""
                if not u:
                    continue

                rank_raw = (row.get(rank_key) or "").strip() if rank_key else ""
                xp_raw   = (row.get(xp_key) or "").strip() if xp_key else ""
                wal_raw  = (row.get(wallet_key) or "").strip() if wallet_key else ""
                wvc_raw  = (row.get(wvc_key) or "").strip() if wvc_key else ""

                rank_i = _to_int_safe(rank_raw)
                xp_i   = _to_int_safe(xp_raw)
                wallet = clean_wallet(wal_raw) if wal_raw else None
                wvc    = wvc_raw if wvc_raw else None

                upsert_winner(u, rank=rank_i, xp=xp_i, wallet=wallet, wvc=wvc)
                inserted += 1

                # preview (prime 3), con backtick corretti
                if i <= 3:
                    preview_rows.append(
                        f"{i:02d}: user=`{u}` | rank=`{rank_i}` | xp=`{xp_i}` | wallet=`{wallet or '-'}` | wvc=`{wvc or '-'}`"
                    )

        # 2° messaggio: risultato + preview in blocco codice per evitare errori Markdown
        preview_block = "No preview" if not preview_rows else "\n".join(preview_rows)
        summary = f"✅ Import completed. Rows processed: {inserted}\n\nPreview (first 3):\n```text\n{preview_block}\n```"
        await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(f"❌ Import failed: {e}")


# --- Admin debug tools ---
async def admin_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: `/admin_show <username>`", parse_mode=ParseMode.MARKDOWN)
        return
    u = context.args[0].strip().lower()
    row = db_one("SELECT username, tg_id, rank, xp, wallet, wvc, wvc_used FROM winners WHERE username=?", (u,))
    if not row:
        await update.message.reply_text(f"Not found: `{u}`", parse_mode=ParseMode.MARKDOWN)
        return
    username, tg_id, rank, xp, wallet, wvc, wvc_used = row
    txt = (
        f"*DB row*\n"
        f"• username: `{username}`\n"
        f"• tg_id: `{tg_id}`\n"
        f"• position: `{rank}`\n"
        f"• xp: `{xp}`\n"
        f"• wallet: `{wallet or '-'}`\n"
        f"• wvc: `{wvc or '-'}` used:{'yes' if wvc_used else 'no'}"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

async def admin_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: `/admin_link <username> <tg_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    u = context.args[0].strip().lower()
    try:
        tg = int(context.args[1])
    except:
        await update.message.reply_text("tg_id must be an integer.", parse_mode=ParseMode.MARKDOWN)
        return
    if not is_whitelisted(u):
        await update.message.reply_text(f"Username not found: `{u}`", parse_mode=ParseMode.MARKDOWN)
        return
    db_exec("UPDATE winners SET tg_id=? WHERE username=?", (tg, u))
    await update.message.reply_text(f"Linked `{u}` → tg_id `{tg}`", parse_mode=ParseMode.MARKDOWN)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).rate_limiter(AIORateLimiter()).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_username", set_username))
    app.add_handler(CommandHandler("status", status_cmd))

    # WVC
    app.add_handler(CommandHandler("show_wvc", show_wvc))
    app.add_handler(CommandHandler("use_wvc", use_wvc))

    # Registration
    app.add_handler(CommandHandler("add_wallet", add_wallet))
    app.add_handler(CommandHandler("proof", proof_cmd))
    app.add_handler(CommandHandler("set_wallet", set_wallet))
    app.add_handler(CommandHandler("reg_sig", reg_sig))

    # Change
    app.add_handler(CommandHandler("change_wallet", change_wallet))
    app.add_handler(CommandHandler("old_sig", old_sig))
    app.add_handler(CommandHandler("new_wallet", new_wallet))
    app.add_handler(CommandHandler("new_sig", new_sig))

    # Admin
    app.add_handler(CommandHandler("admin_import_winners", admin_import_winners))
    app.add_handler(CommandHandler("admin_show", admin_show))
    app.add_handler(CommandHandler("admin_link", admin_link))

    log.info("🚀 SavitriRewardsBot is running...")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
