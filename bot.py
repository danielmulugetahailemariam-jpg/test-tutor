import os
import json
import html
import base64
import asyncio
import logging
from datetime import datetime
from http import HTTPStatus

import httpx
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from fastapi import FastAPI, Request, Response
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

from classifier import classify_material, is_excluded_file, normalize_stem

# --- CONFIGURATION ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "2087550317"))
SHEET_NAME = os.getenv("SHEET_NAME", "Bishoftu Tutoring Hub DB")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip()
CONVERTER_SCRIPT_URL = os.getenv("CONVERTER_SCRIPT_URL", "").strip()
CONVERTER_SECRET = os.getenv("CONVERTER_SECRET", "").strip()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

REG_HEADERS = ["ID", "Name", "Grade", "Phone", "Status", "Timestamp", "Telegram_ID"]
PDF_HEADERS = [
    "Doc_ID",
    "File_Name",
    "Grade",
    "Stream",
    "Subject",
    "Category",
    "Year",
    "Exam_Tag",
    "Round_Or_Code",
    "Link_Key",
    "Linked_Doc_ID",
    "Has_Embedded_Answer",
    "Format",
    "File_Size_MB",
    "Source",
    "Drive_PDF_ID",
    "Drive_Original_ID",
    "Telegram_File_ID",
    "Unique_Key",
    "Post_Link",
]

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# --- GOOGLE CREDENTIALS & CLIENTS ---
def get_credentials() -> Credentials:
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        return Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    if os.path.exists("/etc/secrets/credentials.json"):
        return Credentials.from_service_account_file("/etc/secrets/credentials.json", scopes=SCOPES)
    return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)


def get_sheets():
    creds = get_credentials()
    client = gspread.authorize(creds)
    sheet_doc = client.open(SHEET_NAME)
    reg_sheet = sheet_doc.worksheet("Registrations")
    pdf_sheet = sheet_doc.worksheet("PDF_Library")
    return reg_sheet, pdf_sheet


def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def ensure_headers(sheet, expected_headers):
    first_row = sheet.row_values(1)
    if not first_row:
        sheet.update("A1", [expected_headers])
    elif first_row != expected_headers and len(first_row) < len(expected_headers):
        # Safely append any missing trailing columns (like Telegram_ID on Registrations)
        sheet.update("A1", [expected_headers])


NAME, GRADE, PHONE = range(3)


# ==============================================================================
# 1. REGISTRATION HANDLERS (WITH TELEGRAM_ID & APPROVAL CHECK)
# ==============================================================================
def find_registration_by_tg_id(reg_sheet, tg_id: int):
    rows = reg_sheet.get_all_values()
    for idx, row in enumerate(rows[1:], start=2):
        if len(row) >= 7 and str(row[6]).strip() == str(tg_id):
            status = row[4].strip().upper() if len(row) >= 5 else "NEW"
            name = row[1] if len(row) >= 2 else "Student"
            return idx, name, status
    return None


async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    def _check():
        reg_sheet, _ = get_sheets()
        ensure_headers(reg_sheet, REG_HEADERS)
        return find_registration_by_tg_id(reg_sheet, user_id)

    existing = await asyncio.to_thread(_check)
    if existing:
        _, name, status = existing
        safe_name = html.escape(name)
        if status == "APPROVED":
            await update.message.reply_text(
                f"👋 Welcome back, <b>{safe_name}</b>!\n\n✅ Your registration is <b>APPROVED</b>.",
                parse_mode="HTML",
            )
            return ConversationHandler.END
        elif status == "NEW":
            await update.message.reply_text(
                f"⏳ Hi <b>{safe_name}</b>, your registration is already submitted and waiting for admin approval.",
                parse_mode="HTML",
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "📚 <b>Bishoftu Tutoring Hub</b>\n\nLet's reserve your seat.\n\nPlease enter the <b>Student's Full Name</b>:",
        parse_mode="HTML",
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
        "Select the student's <b>Grade Level</b>:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return GRADE


async def get_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["grade"] = query.data
    await query.edit_message_text(
        f"Selected: <b>{html.escape(query.data)}</b>\n\nNow enter an active <b>Phone Number</b> (Parent or Student):",
        parse_mode="HTML",
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    name = context.user_data["name"]
    grade = context.user_data["grade"]
    tg_id = update.effective_user.id
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    def _save():
        reg_sheet, _ = get_sheets()
        ensure_headers(reg_sheet, REG_HEADERS)
        all_rows = reg_sheet.get_all_values()
        next_id = max(1, len(all_rows))
        reg_sheet.append_row([next_id, name, grade, phone, "NEW", timestamp, str(tg_id)])

    await asyncio.to_thread(_save)

    safe_name = html.escape(name)
    safe_grade = html.escape(grade)
    safe_phone = html.escape(phone)

    await update.message.reply_text(
        f"✅ <b>Pre-Registration Successful!</b>\n\n"
        f"👤 <b>Name:</b> {safe_name}\n"
        f"🏫 <b>Grade:</b> {safe_grade}\n"
        f"📞 <b>Phone:</b> {safe_phone}\n\n"
        f"We will contact you shortly once an admin approves your access.",
        parse_mode="HTML",
    )

    keyboard = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_user:{tg_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_user:{tg_id}"),
    ]]
    await context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=(
            f"🚨 <b>NEW REGISTRATION!</b>\n"
            f"👤 {safe_name} ({safe_grade})\n"
            f"📞 <code>{safe_phone}</code>\n"
            f"🆔 <code>{tg_id}</code>\n\n"
            f"Approve below or send /check_leads to review all."
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END


# ==============================================================================
# 2. ADMIN LEAD CHECKER & APPROVAL BUTTONS
# ==============================================================================
async def check_leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    def _fetch():
        reg_sheet, _ = get_sheets()
        ensure_headers(reg_sheet, REG_HEADERS)
        return reg_sheet.get_all_values()

    rows = await asyncio.to_thread(_fetch)
    new_leads = []
    for row in rows[1:]:
        status = row[4].strip().upper() if len(row) >= 5 else ""
        if status == "NEW":
            new_leads.append(row)

    if not new_leads:
        await update.message.reply_text("✅ All caught up! No NEW registrations right now.")
        return

    msg = f"🔔 <b>PENDING REGISTRATIONS ({len(new_leads)}):</b>\n\n"
    buttons = []
    for row in new_leads:
        name = html.escape(row[1] if len(row) > 1 else "Unknown")
        grade = html.escape(row[2] if len(row) > 2 else "")
        phone = html.escape(row[3] if len(row) > 3 else "")
        tg_id = row[6].strip() if len(row) > 6 else ""
        msg += f"• <b>{name}</b> | {grade} | <code>{phone}</code>\n"
        if tg_id:
            buttons.append([InlineKeyboardButton(f"✅ Approve {row[1]}", callback_data=f"approve_user:{tg_id}")])

    buttons.append([InlineKeyboardButton("✔️ Approve All NEW Leads", callback_data="approve_all_new")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    data = query.data
    await query.answer("Updating Google Sheet...")

    if data == "approve_all_new":
        def _approve_all():
            reg_sheet, _ = get_sheets()
            all_values = reg_sheet.get_all_values()
            approved_ids = []
            updates = []
            for idx, row in enumerate(all_values[1:], start=2):
                if len(row) >= 5 and row[4].strip().upper() == "NEW":
                    updates.append({"range": f"E{idx}", "values": [["APPROVED"]]})
                    if len(row) >= 7 and row[6].strip():
                        approved_ids.append(int(row[6].strip()))
            if updates:
                reg_sheet.batch_update(updates)
            return approved_ids

        approved_ids = await asyncio.to_thread(_approve_all)
        for uid in approved_ids:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text="🎉 <b>Good news!</b> Your Bishoftu Tutoring Hub registration has been <b>APPROVED</b>.",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Could not notify user {uid}: {e}")

        await query.edit_message_text(
            f"✅ Approved <b>{len(approved_ids)}</b> student(s) in Google Sheets.",
            parse_mode="HTML",
        )
        return

    action, tg_id_str = data.split(":", 1)
    new_status = "APPROVED" if action == "approve_user" else "REJECTED"

    def _update_single():
        reg_sheet, _ = get_sheets()
        all_values = reg_sheet.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) >= 7 and row[6].strip() == tg_id_str:
                reg_sheet.update_cell(idx, 5, new_status)
                return row[1]
        return None

    student_name = await asyncio.to_thread(_update_single)
    if student_name:
        if new_status == "APPROVED":
            try:
                await context.bot.send_message(
                    chat_id=int(tg_id_str),
                    text="🎉 <b>Good news!</b> Your Bishoftu Tutoring Hub registration has been <b>APPROVED</b>.",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Could not notify user {tg_id_str}: {e}")

        await query.edit_message_text(
            f"{'✅' if new_status == 'APPROVED' else '❌'} Marked <b>{html.escape(student_name)}</b> as <b>{new_status}</b>.",
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text("⚠️ Student row not found in Google Sheet.")


# ==============================================================================
# 3. EXAM <-> ANSWER LINKING & OPTIONAL APPS SCRIPT CONVERTER
# ==============================================================================
async def convert_office_via_apps_script(drive_file_id: str) -> str | None:
    """Asks user's Google Apps Script Web App to create a .pdf twin next to a .pptx/.docx in Drive."""
    if not CONVERTER_SCRIPT_URL:
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.post(
                CONVERTER_SCRIPT_URL,
                json={"action": "convert_drive_file", "fileId": drive_file_id, "secret": CONVERTER_SECRET},
            )
            data = resp.json()
            if data.get("ok") and data.get("pdfFileId"):
                return data["pdfFileId"]
            logger.warning(f"Converter response error for {drive_file_id}: {data}")
    except Exception as e:
        logger.warning(f"Converter request failed for {drive_file_id}: {e}")
    return None


def compute_exam_answer_links(all_rows_with_headers: list[list[str]]):
    """Finds unlinked Answer Sheets & Exams with matching Link_Key / Base_Link_Key and returns batch updates."""
    if len(all_rows_with_headers) <= 1:
        return []

    # Indexes (0-based): Doc_ID=0, Subject=4, Category=5, Year=6, Exam_Tag=7, Link_Key=9, Linked_Doc_ID=10, Has_Embedded=11
    exams_exact = {}
    exams_base = {}
    answers = []

    for row_idx, row in enumerate(all_rows_with_headers[1:], start=2):
        if len(row) < 12:
            continue
        doc_id = row[0]
        cat = row[5]
        link_key = row[9]
        linked_id = row[10]
        has_embedded = row[11]
        if not link_key:
            continue

        parts = link_key.split("|")
        base_key = "|".join(parts[:3]) if len(parts) >= 3 else link_key

        if cat == "Answer Sheet":
            answers.append((row_idx, doc_id, link_key, base_key, linked_id))
        elif has_embedded == "No":
            exams_exact.setdefault(link_key, []).append((row_idx, doc_id, linked_id))
            exams_base.setdefault(base_key, []).append((row_idx, doc_id, linked_id))

    updates = []
    for ans_row_idx, ans_doc_id, ans_link_key, ans_base_key, ans_linked in answers:
        if ans_linked:
            continue
        candidates = exams_exact.get(ans_link_key) or exams_base.get(ans_base_key)
        if not candidates:
            continue
        # Link to first matching exam (and link exam back to answer sheet)
        ex_row_idx, ex_doc_id, ex_linked = candidates[0]
        updates.append({"range": f"K{ans_row_idx}", "values": [[ex_doc_id]]})
        if not ex_linked:
            updates.append({"range": f"K{ex_row_idx}", "values": [[ans_doc_id]]})

    return updates


# ==============================================================================
# 4. GOOGLE DRIVE BULK SYNC (/sync_drive)
# ==============================================================================
def list_drive_files_recursive(drive_service, folder_id: str) -> list[dict]:
    results = []
    folders_to_visit = [folder_id]
    while folders_to_visit:
        current_folder = folders_to_visit.pop(0)
        page_token = None
        while True:
            resp = (
                drive_service.files()
                .list(
                    q=f"'{current_folder}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType, size, md5Checksum, parents)",
                    pageSize=1000,
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            for f in resp.get("files", []):
                if f.get("mimeType") == "application/vnd.google-apps.folder":
                    folders_to_visit.append(f["id"])
                else:
                    results.append(f)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    return results


async def sync_drive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    if not DRIVE_FOLDER_ID:
        await update.message.reply_text(
            "⚠️ <code>DRIVE_FOLDER_ID</code> is not set in Render Environment Variables.",
            parse_mode="HTML",
        )
        return

    status_msg = await update.message.reply_text("🔄 Scanning Google Drive folder and classifying files...")

    def _prepare_sync():
        _, pdf_sheet = get_sheets()
        ensure_headers(pdf_sheet, PDF_HEADERS)
        existing_rows = pdf_sheet.get_all_values()
        drive_service = get_drive_service()
        drive_files = list_drive_files_recursive(drive_service, DRIVE_FOLDER_ID)
        return pdf_sheet, existing_rows, drive_files

    try:
        pdf_sheet, existing_rows, drive_files = await asyncio.to_thread(_prepare_sync)
    except Exception as e:
        await status_msg.edit_text(f"❌ Drive sync failed: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
        return

    # Track already-indexed Drive IDs & MD5 checksums
    existing_drive_ids = set()
    existing_unique_keys = set()
    stem_to_row_idx = {}
    for idx, row in enumerate(existing_rows[1:], start=2):
        if len(row) >= 16 and row[15]:
            existing_drive_ids.add(row[15])
        if len(row) >= 17 and row[16]:
            existing_drive_ids.add(row[16])
        if len(row) >= 19 and row[18]:
            existing_unique_keys.add(row[18])
        if len(row) >= 2:
            stem_to_row_idx[normalize_stem(row[1])] = idx

    # Group Drive files by normalized stem so .pptx/.docx pairs with .pdf cleanly
    grouped_files = {}
    skipped_excluded = 0
    skipped_duplicates = 0
    seen_md5 = set(existing_unique_keys)

    for f in drive_files:
        fname = f["name"]
        excluded, _ = is_excluded_file(fname)
        if excluded:
            skipped_excluded += 1
            continue

        f_id = f["id"]
        md5 = f.get("md5Checksum") or f_id
        if f_id in existing_drive_ids or md5 in seen_md5:
            skipped_duplicates += 1
            continue

        seen_md5.add(md5)
        stem = normalize_stem(fname)
        ext = fname.rsplit(".", 1)[-1].lower()
        grouped_files.setdefault(stem, {})
        # Keep first copy if another (1)/(2) variant exists in the same run
        if ext not in grouped_files[stem]:
            grouped_files[stem][ext] = f

    # Optionally convert any standalone .pptx/.docx into PDF via Apps Script
    converted_count = 0
    if CONVERTER_SCRIPT_URL:
        for stem, ext_map in grouped_files.items():
            if "pdf" not in ext_map and ("pptx" in ext_map or "docx" in ext_map):
                office_file = ext_map.get("pptx") or ext_map.get("docx")
                new_pdf_id = await convert_office_via_apps_script(office_file["id"])
                if new_pdf_id:
                    ext_map["pdf"] = {
                        "id": new_pdf_id,
                        "name": office_file["name"].rsplit(".", 1)[0] + ".pdf",
                        "size": office_file.get("size", "0"),
                        "md5Checksum": new_pdf_id,
                    }
                    converted_count += 1

    # Build batch rows
    next_num = len(existing_rows)  # Header is row 1, so first item is DOC-0001
    new_rows = []
    twin_updates = []

    for stem, ext_map in sorted(grouped_files.items()):
        pdf_file = ext_map.get("pdf")
        office_file = ext_map.get("pptx") or ext_map.get("docx")

        # If PDF already existed in sheet from earlier, attach newly found PPTX/DOCX twin
        if stem in stem_to_row_idx and office_file and not pdf_file:
            row_idx = stem_to_row_idx[stem]
            twin_updates.append({"range": f"Q{row_idx}", "values": [[office_file["id"]]]})
            continue

        primary = pdf_file or office_file
        if not primary:
            continue

        meta = classify_material(primary["name"])
        doc_id = f"DOC-{next_num:04d}"
        next_num += 1

        formats = []
        if pdf_file:
            formats.append("PDF")
        if "pptx" in ext_map:
            formats.append("PPTX")
        if "docx" in ext_map:
            formats.append("DOCX")
        format_str = " + ".join(formats)

        size_bytes = int(primary.get("size") or 0)
        size_mb = round(size_bytes / (1024 * 1024), 2)

        new_rows.append([
            doc_id,
            primary["name"],
            meta["grade"],
            meta["stream"],
            meta["subject"],
            meta["category"],
            meta["year"],
            meta["exam_tag"],
            meta["round_or_code"],
            meta["link_key"],
            "",  # Linked_Doc_ID (computed right after batch append)
            meta["has_embedded_answer"],
            format_str,
            size_mb,
            "Drive",
            pdf_file["id"] if pdf_file else "",
            office_file["id"] if office_file else "",
            "",  # Telegram_File_ID
            primary.get("md5Checksum") or primary["id"],
            "",  # Post_Link
        ])

    def _write_and_link():
        if twin_updates:
            pdf_sheet.batch_update(twin_updates)
        if new_rows:
            # Append in chunks of 250 rows to stay well within payload limits
            for i in range(0, len(new_rows), 250):
                pdf_sheet.append_rows(new_rows[i : i + 250], value_input_option="USER_ENTERED")

        updated_table = pdf_sheet.get_all_values()
        link_updates = compute_exam_answer_links(updated_table)
        if link_updates:
            pdf_sheet.batch_update(link_updates)
        return len(link_updates) // 2

    paired_count = await asyncio.to_thread(_write_and_link)

    await status_msg.edit_text(
        f"✅ <b>Google Drive Sync Complete!</b>\n\n"
        f"📥 <b>Added to Library:</b> {len(new_rows)}\n"
        f"📄 <b>PPTX/DOCX Converted to PDF:</b> {converted_count}\n"
        f"🔗 <b>Exam ↔ Answer Pairs Linked:</b> {paired_count}\n"
        f"♻️ <b>Skipped Duplicates:</b> {skipped_duplicates}\n"
        f"🚫 <b>Ignored Non-Study/Admin Files:</b> {skipped_excluded}",
        parse_mode="HTML",
    )


# ==============================================================================
# 5. AUTOMATIC CHANNEL FILE CATEGORIZER (FUTURE TELEGRAM POSTS)
# ==============================================================================
async def auto_categorize_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post or not post.document or not post.document.file_name:
        return

    doc = post.document
    excluded, _ = is_excluded_file(doc.file_name)
    if excluded:
        return

    caption = post.caption or ""
    meta = classify_material(doc.file_name, caption)
    ext = doc.file_name.rsplit(".", 1)[-1].upper()
    size_mb = round((doc.file_size or 0) / (1024 * 1024), 2)
    post_link = post.link if post.link else "Channel Document"

    def _append_and_link():
        _, pdf_sheet = get_sheets()
        ensure_headers(pdf_sheet, PDF_HEADERS)
        rows = pdf_sheet.get_all_values()

        # Check duplicate by Unique_Key
        for r in rows[1:]:
            if len(r) >= 19 and r[18] == doc.file_unique_id:
                return None, 0

        doc_id = f"DOC-{len(rows):04d}"
        pdf_sheet.append_row([
            doc_id,
            doc.file_name,
            meta["grade"],
            meta["stream"],
            meta["subject"],
            meta["category"],
            meta["year"],
            meta["exam_tag"],
            meta["round_or_code"],
            meta["link_key"],
            "",
            meta["has_embedded_answer"],
            ext,
            size_mb,
            "Telegram",
            "",
            "",
            doc.file_id,
            doc.file_unique_id,
            post_link,
        ])

        updated_table = pdf_sheet.get_all_values()
        link_updates = compute_exam_answer_links(updated_table)
        if link_updates:
            pdf_sheet.batch_update(link_updates)
        return doc_id, len(link_updates)

    doc_id, links_made = await asyncio.to_thread(_append_and_link)
    if doc_id and meta["category"] == "Answer Sheet" and meta["year"] == "" and links_made == 0:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                f"ℹ️ Saved Answer Sheet <b>{html.escape(doc.file_name)}</b> as <code>{doc_id}</code> "
                f"({meta['subject']} / {meta['exam_tag']}), but no Year was found in the filename to auto-link it to an exam."
            ),
            parse_mode="HTML",
        )


# ==============================================================================
# 6. FASTAPI APP & PTB LIFECYCLE
# ==============================================================================
app = FastAPI()
ptb_app = Application.builder().token(BOT_TOKEN).updater(None).build()

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
ptb_app.add_handler(CommandHandler("sync_drive", sync_drive_command))
ptb_app.add_handler(CallbackQueryHandler(handle_approval_callback, pattern=r"^(approve_user:|reject_user:|approve_all_new)"))
ptb_app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.Document.ALL, auto_categorize_file))


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
