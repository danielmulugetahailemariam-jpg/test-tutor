import os
import json
import base64
import logging
from datetime import datetime
from http import HTTPStatus
from fastapi import FastAPI, Request, Response
from google.oauth2.service_account import Credentials
import gspread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

# --- CONFIGURATION ---
BOT_TOKEN = "9214264770:AAFdw0tcw0F5BcXBrwkFxh9m7HzRODaq36I"
ADMIN_USER_ID = 2087550317
SHEET_NAME = "Bishoftu Tutoring Hub DB"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- LAZY GOOGLE SHEETS CONNECTOR ---
def get_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    encoded_creds = os.environ.get("GOOGLE_CREDENTIALS_BASE64")
    if not encoded_creds:
        raise ValueError("GOOGLE_CREDENTIALS_BASE64 environment variable is missing!")
    
    decoded_json = base64.b64decode(encoded_creds.strip()).decode("utf-8")
    creds_info = json.loads(decoded_json)
    
    # Fix private key newline formatting automatically
    if "private_key" in creds_info:
        creds_info["private_key"] = creds_info["private_key"].replace("\\\\n", "\n").replace("\\n", "\n")

    credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(credentials)
    
    sheet_doc = client.open(SHEET_NAME)
    return sheet_doc.worksheet("Registrations"), sheet_doc.worksheet("PDF_Library")
    
NAME, GRADE, PHONE = range(3)

# ==============================================================================
# 1. REGISTRATION HANDLERS
# ==============================================================================
async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 **Bishoftu Tutoring Hub**\n\nLet's reserve your seat.\n\nPlease enter the **Student's Full Name**:",
        parse_mode="Markdown"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("Grade 6", callback_data="Grade 6")],
        [InlineKeyboardButton("Grade 8", callback_data="Grade 8")],
        [InlineKeyboardButton("Grade 12 (Matric)", callback_data="Grade 12")],
    ]
    await update.message.reply_text(
        "Select the student's **Grade Level**:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return GRADE

async def get_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["grade"] = query.data
    await query.edit_message_text(
        f"Selected: **{query.data}**\n\nNow enter an active **Phone Number** (Parent or Student):",
        parse_mode="Markdown"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    name = context.user_data["name"]
    grade = context.user_data["grade"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    reg_sheet, _ = get_sheets()
    all_rows = reg_sheet.get_all_values()
    next_id = len(all_rows)
    reg_sheet.append_row([next_id, name, grade, phone, "NEW", timestamp])

    await update.message.reply_text(
        f"✅ **Pre-Registration Successful!**\n\n"
        f"👤 **Name:** {name}\n"
        f"🏫 **Grade:** {grade}\n"
        f"📞 **Phone:** {phone}\n\n"
        f"We will contact you shortly to confirm your seat assignment.",
        parse_mode="Markdown",
    )

    await context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=f"🚨 **NEW REGISTRATION!**\n👤 {name} ({grade})\n📞 {phone}\n\nSend /check_leads to review.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END

# ==============================================================================
# 2. ADMIN LEAD CHECKER
# ==============================================================================
async def check_leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    reg_sheet, _ = get_sheets()
    records = reg_sheet.get_all_records()
    new_leads = [r for r in records if str(r.get("Status")).upper() == "NEW"]

    if not new_leads:
        await update.message.reply_text("✅ All caught up! No NEW registrations right now.")
        return

    msg = f"🔔 **UNSORTED REGISTRATIONS ({len(new_leads)}):**\n\n"
    for lead in new_leads:
        msg += f"• **{lead['Name']}** | {lead['Grade']} | `{lead['Phone']}`\n"

    keyboard = [[InlineKeyboardButton("✔️ Mark All as SORTED", callback_data="mark_all_sorted")]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def mark_sorted_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    await query.answer("Updating Google Sheet...")
    reg_sheet, _ = get_sheets()
    all_values = reg_sheet.get_all_values()

    for idx, row in enumerate(all_values[1:], start=2):
        if len(row) >= 5 and row[4].upper() == "NEW":
            reg_sheet.update_cell(idx, 5, "SORTED")

    await query.edit_message_text("✅ All new leads have been marked as **SORTED** in your Google Sheet.", parse_mode="Markdown")

# ==============================================================================
# 3. AUTOMATIC CHANNEL PDF CATEGORIZER
# ==============================================================================
async def auto_categorize_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post or not post.document:
        return

    doc = post.document
    if not doc.file_name.lower().endswith(".pdf"):
        return

    file_name = doc.file_name
    caption = post.caption or ""
    search_text = f"{file_name} {caption}".lower()

    if "12" in search_text or "matric" in search_text:
        grade = "Grade 12"
    elif "8" in search_text:
        grade = "Grade 8"
    elif "6" in search_text:
        grade = "Grade 6"
    else:
        grade = "General"

    subjects = ["math", "physics", "chemistry", "biology", "english", "general science", "history", "geography"]
    detected_subject = "Other"
    for sub in subjects:
        if sub in search_text:
            detected_subject = sub.title()
            break

    post_link = post.link if post.link else "Channel Document"
    _, pdf_sheet = get_sheets()
    pdf_sheet.append_row([file_name, grade, detected_subject, doc.file_id, post_link])

# ==============================================================================
# 4. FASTAPI APP & PTB LIFECYCLE
# ==============================================================================
app = FastAPI()

ptb_app = Application.builder().token(BOT_TOKEN).build()

reg_handler = ConversationHandler(
    entry_points=[CommandHandler("register", start_register), CommandHandler("start", start_register)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        GRADE: [CallbackQueryHandler(get_grade)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
ptb_app.add_handler(reg_handler)
ptb_app.add_handler(CommandHandler("check_leads", check_leads))
ptb_app.add_handler(CallbackQueryHandler(mark_sorted_callback, pattern="^mark_all_sorted$"))
ptb_app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.Document.PDF, auto_categorize_pdf))

@app.on_event("startup")
async def startup_event():
    await ptb_app.initialize()
    await ptb_app.start()

@app.on_event("shutdown")
async def shutdown_event():
    await ptb_app.stop()
    await ptb_app.shutdown()

@app.post(f"/{BOT_TOKEN}")
async def webhook(request: Request):
    req_json = await request.json()
    update = Update.de_json(req_json, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response(status_code=HTTPStatus.OK)

@app.get("/")
def index():
    return {"status": "Bishoftu Tutoring Bot is active!"}
