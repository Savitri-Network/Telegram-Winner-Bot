# messages.py (EN)

DISCLAIMER = (
    "⚖️ *Liability Clause:*\n"
    "_I declare that I request the registration/change of the wallet indicated above and "
    "release Savitri Network from any liability in case of my own mistake._"
)

def wrap_with_disclaimer(text: str) -> str:
    return f"{text}\n\n{DISCLAIMER}"

def msg_start_request_username() -> str:
    return wrap_with_disclaimer(
        "👋 Welcome!\n"
        "To begin, please set your **Zealy username** using:\n"
        "`/set_username <your_username>`\n\n"
        "Example: `/set_username andrea_xyz`"
    )

def msg_username_saved(u: str) -> str:
    return wrap_with_disclaimer(f"✅ Username saved: `{u}`\nYou can now use `/status`.")

def msg_status(username: str, rank: str | int | None, xp: str | int | None, wallet: str | None, deadline_str: str, wvc: str | None, wvc_used: int | None) -> str:
    r = f"{rank}" if rank is not None else "-"
    x = f"{xp}" if xp is not None else "-"
    w = wallet or "-"
    return wrap_with_disclaimer(
        "🧾 *Contest Status*\n"
        f"• Zealy Username: `{username}`\n"
        f"• Rank: `{r}`\n"
        f"• XP: `{x}`\n"
        f"• Registered BSC wallet: `{w}`\n"
        f"• Wallet change deadline: *{deadline_str}*\n\n"
        "Actions:\n"
        "• `/help` → Full usage guide\n"
        "• `/change_wallet` → Change wallet\n"
        "• `/add_wallet` → Register wallet (if missing)\n"
        "• `/proof` → Send Zealy profile screenshot"
    )

def msg_not_whitelisted() -> str:
    return wrap_with_disclaimer(
        "⛔ Your username is not listed among the winners.\n"
        "If you believe this is an error, please contact support."
    )

def msg_after_deadline(deadline_str: str) -> str:
    return wrap_with_disclaimer(
        f"⛔ The period to register or change the wallet ended on *{deadline_str}*.\n"
        "It is no longer possible to make changes."
    )

def msg_add_wallet_guide(username: str, deadline_str: str, need_wvc: bool) -> str:
    gate = "" if not need_wvc else "⚠️ Your WVC must be *validated* first with `/use_wvc <code>`.\n\n"
    return wrap_with_disclaimer(
        "🆕 *BSC Wallet Registration*\n"
        + gate +
        "Please follow these steps:\n\n"
        "1️⃣ Send a *screenshot* of your Zealy profile → `/proof` (attach as a photo)\n"
        "2️⃣ Send your BSC wallet → `/set_wallet 0x...`\n"
        "3️⃣ Sign on BscScan and send the signature with `/reg_sig 0x...`\n\n"
        "*Message to sign (with the same wallet):*\n"
        "```\n"
        f"Wallet registration — Zealy: {username} — Wallet: {{wallet}}\n"
        "I declare that I request the registration of the wallet indicated above and release Savitri Network from any liability in case of my own mistake.\n"
        "```\n\n"
        f"⚠️ You have time until *{deadline_str}*"
    )

def msg_proof_ok() -> str:
    return wrap_with_disclaimer("✅ Screenshot received.\nNow send your wallet with: `/set_wallet 0x...`")

def msg_need_photo() -> str:
    return wrap_with_disclaimer("⚠️ Please send a *screenshot* as a *photo* (not as a file).")

def msg_set_wallet_ok(wallet: str, username: str) -> str:
    return wrap_with_disclaimer(
        f"🧾 Wallet provided: `{wallet}`\n"
        "Now sign on BscScan and send the signature with `/reg_sig 0x...`\n\n"
        "*Message to sign:*\n"
        "```\n"
        f"Wallet registration — Zealy: {username} — Wallet: {wallet}\n"
        "I declare that I request the registration of the wallet indicated above and release Savitri Network from any liability in case of my own mistake.\n"
        "```"
    )

def msg_reg_sig_ok(wallet: str, msg_hash: str) -> str:
    return wrap_with_disclaimer(
        f"✅ Wallet successfully registered: `{wallet}`\n\n"
        "🔎 *Technical verification*\n"
        f"SHA-256 hash of the signed message:\n`{msg_hash}`"
    )

def msg_sig_invalid() -> str:
    return wrap_with_disclaimer(
        "❌ Invalid signature. Make sure you signed *exactly* the required text "
        "and used the *same wallet* you specified."
    )

def msg_change_wallet_guide(username: str, old_wallet: str, deadline_str: str, need_wvc: bool) -> str:
    gate = "" if not need_wvc else "⚠️ Your WVC must be *validated* first with `/use_wvc <code>`.\n\n"
    return wrap_with_disclaimer(
        "🔁 *BSC Wallet Change*\n"
        + gate +
        "For security you must:\n\n"
        "1️⃣ Sign with your **old wallet** on BscScan:\n"
        "```\n"
        f"Wallet change request — Zealy: {username} — Old: {old_wallet}\n"
        "```\n"
        "2️⃣ Send the signature: `/old_sig 0x...`\n\n"
        "3️⃣ Send the *new* wallet: `/new_wallet 0x...`\n"
        "4️⃣ Sign with your **new wallet** on BscScan:\n"
        "```\n"
        f"Wallet change request — Zealy: {username} — Old: {old_wallet} — New: {{new_wallet}}\n"
        "```\n"
        "5️⃣ Send the signature: `/new_sig 0x...`\n\n"
        f"⚠️ You have time until *{deadline_str}*"
    )

def msg_old_sig_ok(msg_hash: str) -> str:
    return wrap_with_disclaimer(
        "✅ Old wallet signature verified.\n"
        f"🔎 SHA-256 message hash: `{msg_hash}`\n\n"
        "Now send the *new wallet* with: `/new_wallet 0x...`"
    )

def msg_new_wallet_ok(new_wallet: str, username: str, old_wallet: str) -> str:
    return wrap_with_disclaimer(
        f"🆕 New wallet: `{new_wallet}`\n"
        "Now sign on BscScan and send the signature with `/new_sig 0x...`\n\n"
        "*Message to sign:*\n"
        "```\n"
        f"Wallet change request — Zealy: {username} — Old: {old_wallet} — New: {new_wallet}\n"
        "```"
    )

def msg_new_sig_ok(old_wallet: str, new_wallet: str, msg_hash: str) -> str:
    return wrap_with_disclaimer(
        "✅ Wallet updated\n"
        f"• Old: `{old_wallet}`\n"
        f"• New: `{new_wallet}`\n\n"
        "🔎 *Technical verification*\n"
        f"SHA-256 message hash: `{msg_hash}`"
    )

def msg_username_format_error() -> str:
    return wrap_with_disclaimer("⚠️ Invalid username format. Example: `/set_username andrea_xyz`")

def msg_wallet_format_error() -> str:
    return wrap_with_disclaimer("⚠️ Invalid wallet. Make sure it has format `0x` + 40 hex chars.")

def msg_command_usage(s: str) -> str:
    return wrap_with_disclaimer(s)

# --- WVC messages ---
def msg_show_wvc(code: str | None, used: int | None) -> str:
    if not code:
        return wrap_with_disclaimer("ℹ️ No WVC code is assigned to your username.")
    status = "USED" if used else "NOT USED"
    return wrap_with_disclaimer(f"🔑 Your WVC: `{code}` — *{status}*\nUse `/use_wvc {code}` to validate it (one-time).")

def msg_wvc_required() -> str:
    return wrap_with_disclaimer("🔒 You must validate your WVC first: use `/use_wvc <code>`.")

def msg_wvc_ok(code: str) -> str:
    return wrap_with_disclaimer(f"✅ WVC `{code}` validated. You can proceed with wallet actions.")

def msg_wvc_invalid() -> str:
    return wrap_with_disclaimer("❌ Invalid WVC for your account (or already used). Please check your code.")

# --- Admin notifications (to admin group) ---
def admin_notify_registration(username: str, tg_id: int, wallet: str, signature: str, msg_hash: str) -> str:
    return (
        "🔐 *Wallet Registration*\n\n"
        f"User: `{username}` (TG ID: `{tg_id}`)\n"
        f"Wallet: `{wallet}`\n"
        f"Signature: `{signature}`\n"
        f"Message hash: `{msg_hash}`\n\n"
        "Verify signature:\nhttps://bscscan.com/verifiedSignatures"
    )

def admin_notify_change(username: str, tg_id: int, old_wallet: str, new_wallet: str, signature: str, msg_hash: str) -> str:
    return (
        "🔐 *Wallet Change*\n\n"
        f"User: `{username}` (TG ID: `{tg_id}`)\n"
        f"Old: `{old_wallet}`\n"
        f"New: `{new_wallet}`\n"
        f"Signature: `{signature}`\n"
        f"Message hash: `{msg_hash}`\n\n"
        "Verify signature:\nhttps://bscscan.com/verifiedSignatures"
    )

# --- Backward-compat strings expected by main.py ---
# These constants provide a simple string interface compatible with the
# existing bot flow that asks users to submit a wallet and acknowledges it.
# They are composed using the helpers above to keep a uniform tone and disclaimer.

# Start message shown on /start
WELCOME = msg_start_request_username()

# Generic help text (kept concise for the current simplified flow)
HELP_TEXT = wrap_with_disclaimer(
    "How to use this bot (full guide):\n\n"
    "1) Set your Zealy username\n"
    "   • Command: `/set_username <your_username>`\n\n"
    "2) See your current status\n"
    "   • Command: `/status` (shows username, rank, XP, wallet, deadline)\n\n"
    "3) BEFORE any wallet action: send your Zealy profile screenshot\n"
    "   • Command: `/proof` and then send the screenshot as a PHOTO (not as file)\n\n"
    "4) Register a wallet (if you have none)\n"
    "   • Command: `/add_wallet`\n"
    "   • Steps:\n"
    "     - Send wallet: `/set_wallet 0x...`\n"
    "     - Sign the message on BscScan and copy the validation hash:\n"
    "       https://bscscan.com/verifiedSignatures\n"
    "     - Send the hash: `/reg_sig 0x...`\n\n"
    "5) Change an existing wallet\n"
    "   • Command: `/change_wallet`\n"
    "   • Steps:\n"
    "     - Sign with your OLD wallet and send the hash: `/old_sig 0x...`\n"
    "     - Send the NEW wallet: `/new_wallet 0x...`\n"
    "     - Sign with your NEW wallet and send the hash: `/new_sig 0x...`\n\n"
    "Notes:\n"
    "- Always send the screenshot via `/proof` before starting.\n"
    "- The verification service is BscScan Signature Validation:\n"
    "  https://bscscan.com/verifiedSignatures\n"
    "- Deadline: shown in `/status`.\n"
)

# Prompt asking the user to provide a wallet
ASK_WALLET = wrap_with_disclaimer(
    "Please send your BSC wallet in the format `0x` + 40 hex characters."
)

# Wallet format error (reuse existing helper to ensure consistency)
INVALID_WALLET = msg_wallet_format_error()

# Confirmation sent after saving the request
CONFIRM_RECEIVED = wrap_with_disclaimer(
    "✅ Your request has been received. An admin will review it soon."
)