# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import re
import zipfile
import html
import csv
import io
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from datetime import time as dtime  # for JobQueue daily time

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, PicklePersistence, JobQueue
)

import messages as T

# -------------------- LOGGING --------------------
class TokenSafeFormatter(logging.Formatter):
    """Formatter che nasconde i token nei messaggi di log."""
    def __init__(self, token, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
    
    def format(self, record):
        """Formatta il record e nasconde il token."""
        # Formatta normalmente
        message = super().format(record)
        # Sostituisce il token se presente
        if self.token and self.token in message:
            message = message.replace(self.token, "***TOKEN***")
        return message

class TokenSafeHandler(logging.StreamHandler):
    """Handler che nasconde i token prima di scrivere."""
    def __init__(self, token, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = token
    
    def emit(self, record):
        """Intercetta e modifica il record prima di emetterlo."""
        if self.token:
            # Sostituisce il token nel messaggio formattato
            try:
                msg = self.format(record)
                if self.token in msg:
                    msg = msg.replace(self.token, "***TOKEN***")
                    # Scrivi direttamente il messaggio modificato
                    stream = self.stream
                    stream.write(msg + self.terminator)
                    self.flush()
                else:
                    super().emit(record)
            except Exception:
                self.handleError(record)
        else:
            super().emit(record)

class TokenFilter(logging.Filter):
    """Filtro per nascondere i token nei log."""
    def __init__(self, token):
        super().__init__()
        self.token = token
    
    def filter(self, record):
        """Sostituisce il token nelle stringhe di log."""
        if not self.token:
            return True
        
        # Sostituisce il token in tutti i campi del record
        if hasattr(record, 'msg'):
            if isinstance(record.msg, str):
                record.msg = record.msg.replace(self.token, "***TOKEN***")
            elif isinstance(record.msg, (tuple, list)):
                record.msg = tuple(
                    str(arg).replace(self.token, "***TOKEN***") if isinstance(arg, str) else arg
                    for arg in record.msg
                )
        
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    str(arg).replace(self.token, "***TOKEN***") if isinstance(arg, str) else arg
                    for arg in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: str(v).replace(self.token, "***TOKEN***") if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        
        return True

# Carica il token temporaneamente per il filtro
load_dotenv()
_temp_token = os.getenv("TELEGRAM_TOKEN")

# Crea il filtro e il formatter prima di configurare il logging
token_filter = TokenFilter(_temp_token)
token_formatter = TokenSafeFormatter(_temp_token, "%(levelname)s:%(name)s:%(message)s")

# Configura il logging con handler e formatter personalizzati
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Rimuovi tutti gli handler esistenti
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Aggiungi un nuovo handler personalizzato che intercetta tutto
console_handler = TokenSafeHandler(_temp_token)
console_handler.setFormatter(token_formatter)
root_logger.addHandler(console_handler)

log = logging.getLogger("savitri-bot")

# Applica anche il filtro a tutti i logger, specialmente httpx e telegram
logging.getLogger().addFilter(token_filter)
logging.getLogger("httpx").addFilter(token_filter)
logging.getLogger("telegram").addFilter(token_filter)
logging.getLogger("httpcore").addFilter(token_filter)

# Funzione per applicare il formatter/handler personalizzato a tutti gli handler
def apply_token_protection_to_all_handlers(token_value=None):
    """Applica protezione token a tutti gli handler esistenti."""
    if token_value is None:
        token_value = globals().get('TOKEN', _temp_token)
    
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        for handler in list(logger.handlers):
            # Se non è già un TokenSafeHandler, sostituiscilo o aggiungi protezione
            if not isinstance(handler, TokenSafeHandler):
                # Crea un nuovo handler sicuro con lo stesso stream
                new_handler = TokenSafeHandler(token_value, stream=handler.stream)
                new_handler.setFormatter(token_formatter)
                new_handler.setLevel(handler.level)
                logger.removeHandler(handler)
                logger.addHandler(new_handler)
            elif isinstance(handler, TokenSafeHandler):
                # Aggiorna il token se necessario
                handler.token = token_value
                handler.setFormatter(token_formatter)
    
    # Applica anche al root logger
    for handler in list(root_logger.handlers):
        if not isinstance(handler, TokenSafeHandler):
            new_handler = TokenSafeHandler(token_value, stream=handler.stream)
            new_handler.setFormatter(token_formatter)
            new_handler.setLevel(handler.level)
            root_logger.removeHandler(handler)
            root_logger.addHandler(new_handler)
        elif isinstance(handler, TokenSafeHandler):
            handler.token = token_value
            handler.setFormatter(token_formatter)

# -------------------- ENV --------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    print("ERROR: TELEGRAM_TOKEN is not set in environment.")
    sys.exit(1)

# Aggiorna il filtro, il formatter e l'handler con il token finale
token_filter.token = TOKEN
token_formatter.token = TOKEN
console_handler.token = TOKEN

# Applica la protezione a tutti gli handler esistenti (in caso ne siano stati creati altri)
apply_token_protection_to_all_handlers(TOKEN)

ADMIN_CHAT_IDS = [int(x.strip()) for x in os.getenv("ADMIN_CHAT_IDS", "").split(",") if x.strip()]
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "backups"))
BACKUP_TIME = os.getenv("BACKUP_TIME", "03:00")  # HH:MM container time
HEARTBEAT_FILE = Path(os.getenv("HEARTBEAT_FILE", "data/heartbeat.txt"))
WATCHDOG_MAX_FAILS = int(os.getenv("WATCHDOG_MAX_FAILS", "6"))
WATCHDOG_INTERVAL = int(os.getenv("WATCHDOG_INTERVAL", "30"))
WALLET_REQUESTS_FILE = DATA_DIR / "wallet_update_requests.json"
ZEALY_CSV_PATH = os.getenv("ZEALY_CSV_PATH", "zealy_with_wvc.csv")
DEADLINE_TEXT = os.getenv("DEADLINE_TEXT", "30-11-2025")
GROUP_NOTIFY_CHAT_ID = int(os.getenv("GROUP_NOTIFY_CHAT_ID", "0")) or None
SUBMISSIONS_FILE = DATA_DIR / "user_submissions.json"

DATA_DIR.mkdir(exist_ok=True, parents=True)
BACKUP_DIR.mkdir(exist_ok=True, parents=True)

# -------------------- UTILS / STORAGE --------------------
WALLET_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

def _now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def load_requests() -> List[dict]:
    if WALLET_REQUESTS_FILE.exists():
        try:
            data = json.loads(WALLET_REQUESTS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception as e:
            log.warning("Failed to read requests file: %s", e)
    return []

def save_requests(items: List[dict]) -> None:
    WALLET_REQUESTS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def next_request_id(items: List[dict]) -> int:
    if not items:
        return 1
    return max((r.get("id", 0) for r in items), default=0) + 1

def get_request_by_id(items: List[dict], rid: int) -> Optional[dict]:
    for r in items:
        if r.get("id") == rid:
            return r
    return None

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_CHAT_IDS

# Submissions storage (per tg_id)
def load_submissions() -> dict:
    if SUBMISSIONS_FILE.exists():
        try:
            return json.loads(SUBMISSIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_submissions(data: dict) -> None:
    SUBMISSIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def heartbeat_touch():
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.write_text(str(int(time.time())), encoding="utf-8")
    except Exception as e:
        log.warning("Heartbeat error: %s", e)

# -------------------- JOBQUEUE HELPERS --------------------
def ensure_jobqueue(app):
    """Create & start JobQueue if PTB didn't attach one (safety net)."""
    if app.job_queue is None:
        jq = JobQueue()
        jq.set_application(app)
        jq.start()
        app.job_queue = jq

# -------------------- GROUP NOTIFICATIONS --------------------
async def notify_group(context: ContextTypes.DEFAULT_TYPE, text: str):
    if not GROUP_NOTIFY_CHAT_ID:
        return
    try:
        await context.bot.send_message(chat_id=GROUP_NOTIFY_CHAT_ID, text=text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        log.warning("Group notify failed: %s", e)

# -------------------- ZEALY/WVC INDEX FROM CSV --------------------
ZEALY_INDEX: Dict[str, Dict[str, Any]] = {}

def _discover_latest_zealy_csv() -> Path:
    # Prefer explicit path; if not found, try latest import_* file under DATA_DIR
    p = Path(ZEALY_CSV_PATH)
    if p.exists():
        return p
    candidates = sorted(DATA_DIR.glob("import_*_zealy_with_wvc.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]
    return p  # fallback (may not exist)

def load_zealy_index() -> tuple[bool, str, int]:
    """
    Carica l'indice Zealy dal CSV più recente.
    Returns: (success, message, user_count)
    """
    global ZEALY_INDEX
    ZEALY_INDEX = {}
    csv_path = _discover_latest_zealy_csv()
    if not csv_path.exists():
        msg = f"CSV non trovato: {csv_path}"
        log.warning(msg)
        return False, msg, 0
    try:
        # CSV appears to be semicolon-delimited
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=';')
            if not reader.fieldnames:
                msg = "Il CSV non contiene intestazioni (header)"
                log.error(msg)
                return False, msg, 0
            # Normalize header names
            headers = {h.lower().strip(): h for h in reader.fieldnames}
            pos_key = headers.get("position on leadborad") or headers.get("position on leaderboard") or headers.get("position")
            xp_key = headers.get("xp") or headers.get("xp on zealy") or headers.get("zealy xp")
            user_key = headers.get("username")
            wallet_key = headers.get("binance smart chain address") or headers.get("bsc address") or headers.get("wallet")
            wvc_key = headers.get("wvc")
            
            if not user_key:
                msg = "Colonna 'username' non trovata nel CSV"
                log.error(msg)
                return False, msg, 0
            
            rows_processed = 0
            for row in reader:
                username = (row.get(user_key) or "").strip() if user_key else ""
                if not username:
                    continue
                key = username.lower()
                rank = (row.get(pos_key) or "").strip() if pos_key else ""
                xp = (row.get(xp_key) or "").strip() if xp_key else ""
                wallet = (row.get(wallet_key) or "").strip() if wallet_key else ""
                wvc = (row.get(wvc_key) or "").strip() if wvc_key else ""
                ZEALY_INDEX[key] = {
                    "rank": rank or None,
                    "xp": xp or None,
                    "wallet": wallet or None,
                    "wvc": wvc or None,
                    "wvc_used": None,  # unknown from CSV
                }
                rows_processed += 1
            
            log.info("Loaded Zealy index from %s: %d users", csv_path, len(ZEALY_INDEX))
            return True, f"CSV caricato da: {csv_path.name}", len(ZEALY_INDEX)
    except UnicodeDecodeError as e:
        msg = f"Errore di codifica del file CSV: {e}"
        log.error(msg)
        return False, msg, 0
    except Exception as e:
        msg = f"Errore durante il caricamento del CSV: {e}"
        log.error(msg)
        return False, msg, 0

# -------------------- NOTIFY ADMINS --------------------
async def notify_admins(app,
                        *,
                        user_display: str,
                        uid: int,
                        wallet: str,
                        ts: str,
                        req_id: int):
    """Send admin notification using safe HTML + action buttons."""
    text = (
        f"<b>🔔 New wallet update request</b>\n\n"
        f"• ID: <b>{req_id}</b>\n"
        f"• User: {html.escape(user_display)} (id: {uid})\n"
        f"• New wallet: <code>{html.escape(wallet)}</code>\n"
        f"• Timestamp: {html.escape(ts)}\n"
        f"• Status: <b>pending</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"req:approve:{req_id}"),
         InlineKeyboardButton("❌ Reject",  callback_data=f"req:reject:{req_id}")],
        [InlineKeyboardButton("📄 Details", callback_data=f"req:details:{req_id}")]
    ])
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await app.bot.send_message(chat_id=admin_id, text=text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception as e:
            log.warning("Failed to notify admin %s: %s", admin_id, e)

# -------------------- COMMAND HANDLERS (USER) --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Request wallet update", callback_data="ask_wallet")]]
    await update.message.reply_text(
        T.WELCOME,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=None  # plain text (evita problemi underscore)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(T.HELP_TEXT, parse_mode=None)

async def set_username_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Accept username as first argument; simple validation: letters, numbers, underscore, 2-32 chars
    args = context.args
    if not args:
        await update.message.reply_text(T.msg_username_format_error(), parse_mode=None)
        return
    username = args[0].strip()
    if not re.fullmatch(r"[A-Za-z0-9_]{2,32}", username):
        await update.message.reply_text(T.msg_username_format_error(), parse_mode=None)
        return
    # Persist in user_data (PicklePersistence enabled)
    context.user_data["zealy_username"] = username
    await update.message.reply_text(T.msg_username_saved(username), parse_mode=ParseMode.MARKDOWN)

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Show basic contest status for the user
    username = context.user_data.get("zealy_username")
    if not username:
        await update.message.reply_text(T.msg_start_request_username(), parse_mode=ParseMode.MARKDOWN)
        return
    # Try Zealy index first
    entry = ZEALY_INDEX.get(username.lower())
    if entry:
        rank = entry.get("rank")
        xp = entry.get("xp")
        wallet = entry.get("wallet")
        wvc = entry.get("wvc")
        wvc_used = entry.get("wvc_used")
        msg = T.msg_status(username, rank, xp, wallet, DEADLINE_TEXT, wvc, wvc_used)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return
    # Fallback: last submitted/approved wallet from local requests file
    wallet = None
    try:
        items = load_requests()
        uid = update.effective_user.id
        user_items = [r for r in items if r.get("user_id") == uid]
        approved = [r for r in user_items if r.get("status") == "approved"]
        if approved:
            approved.sort(key=lambda r: r.get("id", 0), reverse=True)
            wallet = approved[0].get("wallet")
        elif user_items:
            user_items.sort(key=lambda r: r.get("id", 0), reverse=True)
            wallet = user_items[0].get("wallet")
    except Exception:
        pass
    msg = T.msg_status(username, None, None, wallet, DEADLINE_TEXT, None, None)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def ask_wallet_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(T.ASK_WALLET, parse_mode=None)
    context.user_data["awaiting_wallet"] = True

async def update_wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        context.user_data["awaiting_wallet"] = True
        await update.message.reply_text(T.ASK_WALLET, parse_mode=None)
        return
    wallet = args[0].strip()
    await handle_wallet_submission(update, context, wallet)

async def text_collector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_wallet") and update.message:
        wallet = update.message.text.strip()
        await handle_wallet_submission(update, context, wallet)

# -------------------- USER WALLET FLOWS (REGISTRATION/CHANGE) --------------------
async def change_wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get("zealy_username")
    if not username:
        await update.message.reply_text(T.msg_start_request_username(), parse_mode=ParseMode.MARKDOWN)
        return
    # Require proof first
    if not context.user_data.get("proof_done"):
        context.user_data["awaiting_proof"] = True
        context.user_data["post_proof_action"] = "change_wallet"
        await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)
        return
    entry = ZEALY_INDEX.get(username.lower())
    old_wallet = (entry or {}).get("wallet")
    # Reset flow state
    ud = context.user_data
    ud.pop("flow", None)
    ud.pop("old_wallet", None)
    ud.pop("new_wallet", None)
    ud.pop("reg_wallet", None)
    ud.pop("reg_sig", None)
    ud.pop("old_sig", None)
    ud.pop("new_sig", None)
    ud.pop("proof_done", None)
    if old_wallet:
        ud["flow"] = "change"
        ud["old_wallet"] = old_wallet
        await update.message.reply_text(
            T.msg_change_wallet_guide(username, old_wallet, DEADLINE_TEXT, False),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        ud["flow"] = "register"
        await update.message.reply_text(
            T.msg_add_wallet_guide(username, DEADLINE_TEXT, False),
            parse_mode=ParseMode.MARKDOWN
        )

async def add_wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force registration flow regardless of CSV old wallet presence."""
    username = context.user_data.get("zealy_username")
    if not username:
        await update.message.reply_text(T.msg_start_request_username(), parse_mode=ParseMode.MARKDOWN)
        return
    if not context.user_data.get("proof_done"):
        context.user_data["awaiting_proof"] = True
        context.user_data["post_proof_action"] = "add_wallet"
        await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)
        return
    # Start registration guide
    ud = context.user_data
    ud["flow"] = "register"
    ud.pop("old_wallet", None)
    ud.pop("new_wallet", None)
    ud.pop("reg_wallet", None)
    ud.pop("reg_sig", None)
    ud.pop("old_sig", None)
    ud.pop("new_sig", None)
    await update.message.reply_text(
        T.msg_add_wallet_guide(username, DEADLINE_TEXT, False),
        parse_mode=ParseMode.MARKDOWN
    )

async def proof_collector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Accept photo uploads as proof when in flow
    if not update.message or not update.message.photo:
        return
    ud = context.user_data
    if ud.get("flow") not in {"register", "change"} and not ud.get("awaiting_proof"):
        return
    try:
        photo_sizes = update.message.photo
        best = photo_sizes[-1]
        ts = int(time.time())
        proofs_dir = DATA_DIR / "proofs"
        proofs_dir.mkdir(parents=True, exist_ok=True)
        target = proofs_dir / f"{update.effective_user.id}_{ts}.jpg"
        file = await best.get_file()
        await file.download_to_drive(custom_path=str(target))
        context.user_data["proof_done"] = True
        context.user_data.pop("awaiting_proof", None)
        await update.message.reply_text(T.msg_proof_ok(), parse_mode=ParseMode.MARKDOWN)
        # Persist proof file under submissions
        subs = load_submissions()
        sid = str(update.effective_user.id)
        rec = subs.get(sid) or {"tg_id": update.effective_user.id}
        rec["username"] = context.user_data.get("zealy_username")
        proofs = rec.get("proofs") or []
        proofs.append(str(target))
        rec["proofs"] = proofs
        subs[sid] = rec
        save_submissions(subs)
        # Group notice
        u = update.effective_user
        uname = f"@{u.username}" if u.username else u.full_name
        await notify_group(context, f"📸 Proof received from {uname}")
        # If there is a pending action (e.g., change_wallet or add_wallet), proceed with the appropriate guide now
        pending = context.user_data.pop("post_proof_action", None)
        username = context.user_data.get("zealy_username")
        if pending and username:
            if pending == "change_wallet":
                entry = ZEALY_INDEX.get(username.lower())
                old_wallet = (entry or {}).get("wallet")
                if old_wallet:
                    context.user_data["flow"] = "change"
                    context.user_data["old_wallet"] = old_wallet
                    await update.message.reply_text(
                        T.msg_change_wallet_guide(username, old_wallet, DEADLINE_TEXT, False),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    context.user_data["flow"] = "register"
                    await update.message.reply_text(
                        T.msg_add_wallet_guide(username, DEADLINE_TEXT, False),
                        parse_mode=ParseMode.MARKDOWN
                    )
            elif pending == "add_wallet":
                context.user_data["flow"] = "register"
                await update.message.reply_text(
                    T.msg_add_wallet_guide(username, DEADLINE_TEXT, False),
                    parse_mode=ParseMode.MARKDOWN
                )
    except Exception:
        await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)

async def proof_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Prompt user to send a screenshot as photo (not file)
    ud = context.user_data
    ud["awaiting_proof"] = True
    await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)

async def set_wallet_cmd2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # For registration flow: /set_wallet 0x...
    username = context.user_data.get("zealy_username")
    if not username:
        await update.message.reply_text(T.msg_start_request_username(), parse_mode=ParseMode.MARKDOWN)
        return
    if not context.user_data.get("proof_done"):
        context.user_data["awaiting_proof"] = True
        await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)
        return
    args = context.args
    if not args:
        await update.message.reply_text(T.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    wallet = args[0].strip()
    if not WALLET_REGEX.match(wallet):
        await update.message.reply_text(T.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    context.user_data["reg_wallet"] = wallet
    # Persist registration wallet
    subs = load_submissions()
    sid = str(update.effective_user.id)
    rec = subs.get(sid) or {"tg_id": update.effective_user.id}
    rec["username"] = context.user_data.get("zealy_username")
    rec["reg_wallet"] = wallet
    subs[sid] = rec
    save_submissions(subs)
    await update.message.reply_text(T.msg_set_wallet_ok(wallet, username), parse_mode=ParseMode.MARKDOWN)
    # Group notice
    u = update.effective_user
    uname = f"@{u.username}" if u.username else u.full_name
    await notify_group(context, f"💳 Wallet received from {uname}: `{wallet}`")

async def reg_sig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Final step of registration: /reg_sig 0x...
    username = context.user_data.get("zealy_username")
    ud = context.user_data
    if ud.get("flow") != "register" or not username:
        await update.message.reply_text(T.msg_command_usage("Use /change_wallet first."), parse_mode=ParseMode.MARKDOWN)
        return
    if not ud.get("proof_done"):
        ud["awaiting_proof"] = True
        await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)
        return
    args = context.args
    if not args:
        await update.message.reply_text(T.msg_command_usage("Usage: `/reg_sig 0x...`"), parse_mode=ParseMode.MARKDOWN)
        return
    sig_hash = args[0].strip()
    reg_wallet = ud.get("reg_wallet")
    if not reg_wallet:
        await update.message.reply_text(T.msg_command_usage("Send your wallet first: `/set_wallet 0x...`"), parse_mode=ParseMode.MARKDOWN)
        return
    ud["reg_sig"] = sig_hash
    # Persist reg signature
    subs = load_submissions()
    sid = str(update.effective_user.id)
    rec = subs.get(sid) or {"tg_id": update.effective_user.id}
    rec["username"] = context.user_data.get("zealy_username")
    rec["reg_sig"] = sig_hash
    subs[sid] = rec
    save_submissions(subs)
    await update.message.reply_text(T.msg_reg_sig_ok(reg_wallet, sig_hash), parse_mode=ParseMode.MARKDOWN)
    # Notify admins
    try:
        txt = T.admin_notify_registration(username, update.effective_user.id, reg_wallet, sig_hash, sig_hash)
        for admin_id in ADMIN_CHAT_IDS:
            await context.bot.send_message(chat_id=admin_id, text=txt, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        log.warning("Admin notify (registration) failed: %s", e)
    # Group notice
    u = update.effective_user
    uname = f"@{u.username}" if u.username else u.full_name
    await notify_group(context, f"✅ Registration signature confirmed for {uname}: `{reg_wallet}`")

async def old_sig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get("zealy_username")
    ud = context.user_data
    if ud.get("flow") != "change" or not username:
        await update.message.reply_text(T.msg_command_usage("Use /change_wallet first."), parse_mode=ParseMode.MARKDOWN)
        return
    if not ud.get("proof_done"):
        ud["awaiting_proof"] = True
        await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)
        return
    args = context.args
    if not args:
        await update.message.reply_text(T.msg_command_usage("Usage: `/old_sig 0x...`"), parse_mode=ParseMode.MARKDOWN)
        return
    sig_hash = args[0].strip()
    ud["old_sig"] = sig_hash
    subs = load_submissions()
    sid = str(update.effective_user.id)
    rec = subs.get(sid) or {"tg_id": update.effective_user.id}
    rec["username"] = context.user_data.get("zealy_username")
    rec["old_sig"] = sig_hash
    subs[sid] = rec
    save_submissions(subs)
    await update.message.reply_text(T.msg_old_sig_ok(sig_hash), parse_mode=ParseMode.MARKDOWN)
    # Group notice
    u = update.effective_user
    uname = f"@{u.username}" if u.username else u.full_name
    await notify_group(context, f"🧾 Old wallet signature received from {uname}")

async def new_wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get("zealy_username")
    ud = context.user_data
    if ud.get("flow") != "change" or not username:
        await update.message.reply_text(T.msg_command_usage("Use /change_wallet first."), parse_mode=ParseMode.MARKDOWN)
        return
    if not ud.get("proof_done"):
        ud["awaiting_proof"] = True
        await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)
        return
    args = context.args
    if not args:
        await update.message.reply_text(T.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    new_wallet = args[0].strip()
    if not WALLET_REGEX.match(new_wallet):
        await update.message.reply_text(T.msg_wallet_format_error(), parse_mode=ParseMode.MARKDOWN)
        return
    ud["new_wallet"] = new_wallet
    subs = load_submissions()
    sid = str(update.effective_user.id)
    rec = subs.get(sid) or {"tg_id": update.effective_user.id}
    rec["username"] = context.user_data.get("zealy_username")
    rec["new_wallet"] = new_wallet
    subs[sid] = rec
    save_submissions(subs)
    await update.message.reply_text(T.msg_new_wallet_ok(new_wallet, username, ud.get("old_wallet", "-")), parse_mode=ParseMode.MARKDOWN)
    # Group notice
    u = update.effective_user
    uname = f"@{u.username}" if u.username else u.full_name
    await notify_group(context, f"🔁 New wallet proposed by {uname}: `{new_wallet}`")

async def new_sig_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get("zealy_username")
    ud = context.user_data
    if ud.get("flow") != "change" or not username:
        await update.message.reply_text(T.msg_command_usage("Use /change_wallet first."), parse_mode=ParseMode.MARKDOWN)
        return
    if not ud.get("proof_done"):
        ud["awaiting_proof"] = True
        await update.message.reply_text(T.msg_need_photo(), parse_mode=ParseMode.MARKDOWN)
        return
    args = context.args
    if not args:
        await update.message.reply_text(T.msg_command_usage("Usage: `/new_sig 0x...`"), parse_mode=ParseMode.MARKDOWN)
        return
    sig_hash = args[0].strip()
    old_wallet = ud.get("old_wallet")
    new_wallet = ud.get("new_wallet")
    if not (old_wallet and new_wallet):
        await update.message.reply_text(T.msg_command_usage("Send `/new_wallet 0x...` first."), parse_mode=ParseMode.MARKDOWN)
        return
    ud["new_sig"] = sig_hash
    subs = load_submissions()
    sid = str(update.effective_user.id)
    rec = subs.get(sid) or {"tg_id": update.effective_user.id}
    rec["username"] = context.user_data.get("zealy_username")
    rec["new_sig"] = sig_hash
    subs[sid] = rec
    save_submissions(subs)
    await update.message.reply_text(T.msg_new_sig_ok(old_wallet, new_wallet, sig_hash), parse_mode=ParseMode.MARKDOWN)
    # Notify admins
    try:
        txt = T.admin_notify_change(username, update.effective_user.id, old_wallet, new_wallet, sig_hash, sig_hash)
        for admin_id in ADMIN_CHAT_IDS:
            await context.bot.send_message(chat_id=admin_id, text=txt, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        log.warning("Admin notify (change) failed: %s", e)
    # Group notice
    u = update.effective_user
    uname = f"@{u.username}" if u.username else u.full_name
    await notify_group(context, f"✅ Change signature confirmed for {uname}: `{old_wallet}` → `{new_wallet}`")

async def handle_wallet_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet: str):
    if not WALLET_REGEX.match(wallet):
        await update.message.reply_text(T.INVALID_WALLET, parse_mode=None)
        return

    requester = update.effective_user
    ts = _now_str()

    # Save request
    items = load_requests()
    rid = next_request_id(items)
    items.append({
        "id": rid,
        "user_id": requester.id,
        "username": requester.username,
        "first_name": requester.first_name,
        "last_name": requester.last_name,
        "wallet": wallet,
        "timestamp": ts,
        "status": "pending",
        "handled_by": None,
        "handled_at": None,
        "note": ""
    })
    save_requests(items)

    # Notify Admins
    user_display = f"@{requester.username}" if requester.username else requester.full_name
    await notify_admins(
        context.application,
        user_display=user_display,
        uid=requester.id,
        wallet=wallet,
        ts=ts,
        req_id=rid
    )

    # Ack
    await update.message.reply_text(T.CONFIRM_RECEIVED, parse_mode=None)
    context.user_data["awaiting_wallet"] = False

# -------------------- ADMIN COMMANDS --------------------
async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    show_all = bool(context.args and context.args[0].lower() == "all")
    items = load_requests()
    if not items:
        await update.message.reply_text("📭 No wallet update requests yet.")
        return
    if not show_all:
        items = [r for r in items if r.get("status") == "pending"]
        if not items:
            await update.message.reply_text("✅ No pending requests.")
            return

    items = sorted(items, key=lambda r: r.get("id", 0), reverse=True)[:30]
    lines = ["<b>📋 Wallet update requests</b>", ""]
    for r in items:
        user = r.get("username") or r.get("first_name") or str(r.get("user_id"))
        lines.append(
            f"• <b>ID</b>: {r.get('id')} | <b>Status</b>: {html.escape(r.get('status',''))}\n"
            f"  User: {html.escape(user)} (id {r.get('user_id')})\n"
            f"  Wallet: <code>{html.escape(r.get('wallet',''))}</code>\n"
            f"  Time: {html.escape(r.get('timestamp',''))}"
        )
        if r.get("handled_by"):
            lines.append(f"  Handled by: {r['handled_by']} at {r.get('handled_at')}")
        lines.append("")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    items = load_requests()
    if not items:
        await update.message.reply_text("📭 Nothing to export.")
        return
    items = sorted(items, key=lambda r: r.get("id", 0))[-100:]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "id","user_id","username","first_name","last_name","wallet","timestamp","status","handled_by","handled_at","note"
    ])
    writer.writeheader()
    for r in items:
        writer.writerow({
            "id": r.get("id"),
            "user_id": r.get("user_id"),
            "username": r.get("username"),
            "first_name": r.get("first_name"),
            "last_name": r.get("last_name"),
            "wallet": r.get("wallet"),
            "timestamp": r.get("timestamp"),
            "status": r.get("status"),
            "handled_by": r.get("handled_by"),
            "handled_at": r.get("handled_at"),
            "note": r.get("note")
        })
    data = io.BytesIO(buf.getvalue().encode("utf-8"))
    data.name = "wallet_update_requests.csv"
    await update.message.reply_document(document=data, caption="📎 Export last 100 requests (CSV)")

async def admin_export_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    subs = load_submissions()
    fieldnames = [
        "username","tg_id","rank","xp","original_wallet","updated_wallet","change_type",
        "reg_sig","old_sig","new_sig","proofs"
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    keys = set(ZEALY_INDEX.keys()) | { (rec.get("username") or "").lower() for rec in subs.values() if rec.get("username") }
    for key in sorted([k for k in keys if k]):
        z = ZEALY_INDEX.get(key) or {}
        rec = None
        for v in subs.values():
            if (v.get("username") or "").lower() == key:
                rec = v
                break
        username = (rec.get("username") if rec else None) or key
        tg_id = rec.get("tg_id") if rec else None
        rank = z.get("rank")
        xp = z.get("xp")
        original_wallet = z.get("wallet")
        updated_wallet = None
        change_type = None
        if rec:
            if rec.get("reg_wallet"):
                updated_wallet = rec.get("reg_wallet")
                change_type = "added"
            if rec.get("new_wallet"):
                updated_wallet = rec.get("new_wallet")
                change_type = "changed"
        row = {
            "username": username,
            "tg_id": tg_id,
            "rank": rank,
            "xp": xp,
            "original_wallet": original_wallet,
            "updated_wallet": updated_wallet or original_wallet,
            "change_type": change_type or ("none" if original_wallet else ("added" if updated_wallet else "none")),
            "reg_sig": rec.get("reg_sig") if rec else None,
            "old_sig": rec.get("old_sig") if rec else None,
            "new_sig": rec.get("new_sig") if rec else None,
            "proofs": ";".join(rec.get("proofs", [])) if rec else "",
        }
        writer.writerow(row)
    data = io.BytesIO(buf.getvalue().encode("utf-8"))
    data.name = "winners_final.csv"
    await update.message.reply_document(document=data, caption="📎 Final winners CSV (with updated_wallet)")

async def admin_details_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer()
        return
    q = update.callback_query
    _, _, sid = q.data.split(":")
    rid = int(sid)
    items = load_requests()
    r = get_request_by_id(items, rid)
    if not r:
        await q.answer("Not found", show_alert=True)
        return
    user = r.get("username") or r.get("first_name") or str(r.get("user_id"))
    text = (
        f"<b>Request #{r.get('id')}</b>\n"
        f"Status: <b>{html.escape(r.get('status',''))}</b>\n"
        f"User: {html.escape(user)} (id {r.get('user_id')})\n"
        f"Wallet: <code>{html.escape(r.get('wallet',''))}</code>\n"
        f"Time: {html.escape(r.get('timestamp',''))}\n"
        f"Handled by: {html.escape(str(r.get('handled_by') or '-'))}\n"
        f"Handled at: {html.escape(str(r.get('handled_at') or '-'))}\n"
        f"Note: {html.escape(str(r.get('note') or ''))}"
    )
    await q.answer()
    await q.message.reply_text(text, parse_mode=ParseMode.HTML)

async def admin_approve_reject_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer()
        return
    q = update.callback_query
    _, action, sid = q.data.split(":")
    rid = int(sid)

    items = load_requests()
    r = get_request_by_id(items, rid)
    if not r:
        await q.answer("Not found", show_alert=True)
        return
    if r.get("status") != "pending":
        await q.answer("Already handled", show_alert=True)
        return

    r["status"] = "approved" if action == "approve" else "rejected"
    r["handled_by"] = update.effective_user.id
    r["handled_at"] = _now_str()
    save_requests(items)

    await q.answer("Saved")
    try:
        await q.edit_message_text(
            text=f"✅ Request #{rid} {r['status']}.\n"
                 f"User id: {r['user_id']}\n"
                 f"Wallet: {r['wallet']}",
            parse_mode=None
        )
    except Exception:
        await q.message.reply_text(f"✅ Request #{rid} {r['status']}.")

# -------------------- BACKUP --------------------
def make_backup_archive() -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"backup_{ts}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(DATA_DIR):
            for name in files:
                fp = Path(root) / name
                arcname = str(fp.relative_to(DATA_DIR.parent))
                zf.write(fp, arcname)
    return target

async def daily_backup_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        path = make_backup_archive()
        msg = f"🗄️ Backup completed: {path.name}"
        log.info(msg)
        for admin_id in ADMIN_CHAT_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=msg)
            except Exception as e:
                log.warning("Failed to notify admin %s: %s", admin_id, e)
    except Exception as e:
        err = f"❌ Backup error: {e}"
        log.error(err)
        for admin_id in ADMIN_CHAT_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=err)
            except Exception as e2:
                log.warning("Failed to notify admin %s: %s", admin_id, e2)

def schedule_daily_backup(app):
    if app.job_queue is None:
        log.warning("JobQueue not available; skipping daily backup scheduling.")
        return
    hh, mm = [int(x) for x in BACKUP_TIME.split(":", 1)]
    backup_time = dtime(hour=hh, minute=mm)
    app.job_queue.run_daily(
        daily_backup_job,
        time=backup_time,
        name="daily_backup",
    )

# -------------------- ADMIN CSV UPLOAD --------------------
async def admin_upload_zealy_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    if not update.message:
        return
    
    # Check if message contains a document
    if not update.message.document:
        await update.message.reply_text(
            "❌ Nessun file trovato nel messaggio.\n\n"
            "Per aggiornare il CSV dei winner:\n"
            "1. Invia il file CSV direttamente al bot, oppure\n"
            "2. Rispondi a un messaggio con file CSV usando /admin_import_list"
        )
        return
    
    doc = update.message.document
    # Accept only CSV
    name = (doc.file_name or "").lower()
    if not (name.endswith(".csv") or (doc.mime_type or "").startswith("text/csv")):
        await update.message.reply_text(
            "❌ File non valido.\n\n"
            "Per favore invia un file CSV (estensione .csv)"
        )
        return
    
    # Notify that file is being processed
    processing_msg = await update.message.reply_text(
        f"📥 File ricevuto: `{doc.file_name}`\n"
        "⏳ Download in corso...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Save into DATA_DIR with timestamped name
    ts = int(time.time())
    target = DATA_DIR / f"import_{ts}_zealy_with_wvc.csv"
    try:
        tg_file = await context.bot.get_file(doc.file_id)
        await tg_file.download_to_drive(custom_path=str(target))
        log.info("CSV downloaded to: %s", target)
    except Exception as e:
        log.error("Failed to download CSV: %s", e)
        await processing_msg.edit_text(
            f"❌ **Errore durante il download del file**\n\n"
            f"Errore: `{str(e)}`\n\n"
            "Verifica che il file non sia corrotto e riprova.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Reload index from latest CSVs
    try:
        await processing_msg.edit_text(
            "📥 File scaricato con successo.\n"
            "⏳ Caricamento dati in corso...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        success, message, total = load_zealy_index()
        
        if success:
            await processing_msg.edit_text(
                f"✅ **CSV aggiornato con successo!**\n\n"
                f"📊 Utenti indicizzati: **{total}**\n"
                f"📁 File: `{target.name}`\n"
                f"ℹ️ {message}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await processing_msg.edit_text(
                f"❌ **Errore durante il caricamento del CSV**\n\n"
                f"⚠️ {message}\n\n"
                f"📁 File salvato in: `{target.name}`\n\n"
                "Verifica il formato del CSV e riprova.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        log.error("Failed to load Zealy index: %s", e)
        await processing_msg.edit_text(
            f"❌ **Errore imprevisto durante l'importazione**\n\n"
            f"Errore: `{str(e)}`\n\n"
            f"📁 File salvato in: `{target.name}`\n\n"
            "Controlla i log per maggiori dettagli.",
            parse_mode=ParseMode.MARKDOWN
        )

async def admin_import_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to import winners by replying to a CSV document message.
    Usage: reply to a .csv file with /admin_import_list (or /admin_upload_zealy_csv).
    """
    if not is_admin(update.effective_user.id):
        return
    
    if not update.message:
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Nessun messaggio a cui rispondere.\n\n"
            "Per aggiornare il CSV:\n"
            "1. Invia il file CSV direttamente al bot, oppure\n"
            "2. Rispondi a un messaggio che contiene un file CSV con questo comando"
        )
        return
    
    replied = update.message.reply_to_message
    if not replied.document:
        await update.message.reply_text(
            "❌ Il messaggio a cui stai rispondendo non contiene un file.\n\n"
            "Per favore rispondi a un messaggio che contiene un file CSV."
        )
        return
    
    doc = replied.document
    name = (doc.file_name or "").lower()
    if not (name.endswith(".csv") or (doc.mime_type or "").startswith("text/csv")):
        await update.message.reply_text(
            "❌ File non valido.\n\n"
            "Il messaggio a cui stai rispondendo deve contenere un file CSV (estensione .csv)"
        )
        return
    
    # Notify that file is being processed
    processing_msg = await update.message.reply_text(
        f"📥 File ricevuto: `{doc.file_name}`\n"
        "⏳ Download in corso...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    ts = int(time.time())
    target = DATA_DIR / f"import_{ts}_zealy_with_wvc.csv"
    try:
        tg_file = await context.bot.get_file(doc.file_id)
        await tg_file.download_to_drive(custom_path=str(target))
        log.info("CSV downloaded to: %s", target)
    except Exception as e:
        log.error("Failed to download CSV (reply import): %s", e)
        await processing_msg.edit_text(
            f"❌ **Errore durante il download del file**\n\n"
            f"Errore: `{str(e)}`\n\n"
            "Verifica che il file non sia corrotto e riprova.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        await processing_msg.edit_text(
            "📥 File scaricato con successo.\n"
            "⏳ Caricamento dati in corso...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        success, message, total = load_zealy_index()
        
        if success:
            await processing_msg.edit_text(
                f"✅ **CSV aggiornato con successo!**\n\n"
                f"📊 Utenti indicizzati: **{total}**\n"
                f"📁 File: `{target.name}`\n"
                f"ℹ️ {message}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await processing_msg.edit_text(
                f"❌ **Errore durante il caricamento del CSV**\n\n"
                f"⚠️ {message}\n\n"
                f"📁 File salvato in: `{target.name}`\n\n"
                "Verifica il formato del CSV e riprova.",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        log.error("Failed to load Zealy index (reply import): %s", e)
        await processing_msg.edit_text(
            f"❌ **Errore imprevisto durante l'importazione**\n\n"
            f"Errore: `{str(e)}`\n\n"
            f"📁 File salvato in: `{target.name}`\n\n"
            "Controlla i log per maggiori dettagli.",
            parse_mode=ParseMode.MARKDOWN
        )

# -------------------- WATCHDOG via JobQueue --------------------
async def watchdog_tick(context: ContextTypes.DEFAULT_TYPE):
    # Touch heartbeat
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.write_text(str(int(time.time())), encoding="utf-8")
    except Exception as e:
        log.warning("Heartbeat error: %s", e)

    # Fails counter in bot_data
    bot_data = context.application.bot_data
    fails = bot_data.get("wd_fails", 0)

    try:
        await context.bot.get_me()
        bot_data["wd_fails"] = 0
    except Exception as e:
        log.warning("Watchdog ping failed: %s", e)
        fails += 1
        bot_data["wd_fails"] = fails
        if fails >= WATCHDOG_MAX_FAILS:
            log.error("Watchdog: too many failures, exiting for auto-restart...")
            os._exit(1)

# -------------------- ERROR HANDLER --------------------
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.exception("Exception while handling an update: %s", context.error)

# -------------------- MAIN --------------------
def main():
    persistence = PicklePersistence(filepath=str(DATA_DIR / "bot_state"))
    application = ApplicationBuilder().token(TOKEN).persistence(persistence).build()

    # User commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("set_username", set_username_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    # Wallet flows
    application.add_handler(CommandHandler("change_wallet", change_wallet_cmd))
    application.add_handler(CommandHandler("add_wallet", add_wallet_cmd))
    application.add_handler(CommandHandler("set_wallet", set_wallet_cmd2))
    application.add_handler(CommandHandler("reg_sig", reg_sig_cmd))
    application.add_handler(CommandHandler("old_sig", old_sig_cmd))
    application.add_handler(CommandHandler("new_wallet", new_wallet_cmd))
    application.add_handler(CommandHandler("new_sig", new_sig_cmd))
    application.add_handler(CommandHandler("proof", proof_cmd))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, proof_collector))
    application.add_handler(CommandHandler("update_wallet", update_wallet_cmd))
    application.add_handler(CallbackQueryHandler(ask_wallet_cb, pattern=r"^ask_wallet$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_collector))

    # Admin
    application.add_handler(CommandHandler("admin_list", admin_list))
    application.add_handler(CommandHandler("admin_export", admin_export))
    application.add_handler(CommandHandler("admin_export_final", admin_export_final))
    application.add_handler(CallbackQueryHandler(admin_details_cb, pattern=r"^req:details:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_approve_reject_cb, pattern=r"^req:(approve|reject):\d+$"))
    # Admin: upload CSV (document) to import winners/WVC
    application.add_handler(MessageHandler(
        (filters.Document.MimeType("text/csv") | filters.Document.FileExtension("csv")),
        admin_upload_zealy_csv
    ))
    # Admin commands to import by replying to the CSV
    application.add_handler(CommandHandler("admin_import_list", admin_import_list_cmd))
    application.add_handler(CommandHandler("admin_upload_zealy_csv", admin_import_list_cmd))

    # Error handler
    application.add_error_handler(on_error)

    # Jobs (correct order)
    ensure_jobqueue(application)                 # 1) ensure JobQueue
    schedule_daily_backup(application)           # 2) schedule backup
    if application.job_queue is not None:        # 3) watchdog
        application.job_queue.run_repeating(
            watchdog_tick,
            interval=WATCHDOG_INTERVAL,
            first=WATCHDOG_INTERVAL,
            name="watchdog"
        )

    # Load Zealy index at startup
    success, msg, count = load_zealy_index()
    if success:
        log.info("Zealy index loaded at startup: %d users", count)
    else:
        log.warning("Zealy index not loaded at startup: %s", msg)
    heartbeat_touch()
    log.info("🚀 SavitriRewardsBot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
