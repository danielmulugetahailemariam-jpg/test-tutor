import os
import json
import html
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

import httpx
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from fastapi import FastAPI, Request, Response
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    MenuButtonWebApp,
)
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
from link_verifier import verify_exam_answer_pair, analyze_exam_pdf
from receipt_generator import generate_membership_pdf
from webapp_api import create_webapp_router

# --- CONFIGURATION ---
BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "2087550317"))
SHEET_NAME = os.getenv("SHEET_NAME", "Bishoftu Tutoring Hub DB")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip()
CONVERTER_SCRIPT_URL = os.getenv("CONVERTER_SCRIPT_URL", "").strip()
CONVERTER_SECRET = os.getenv("CONVERTER_SECRET", "").strip()

BASE_URL = (os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
WEBAPP_URL = f"{BASE_URL}/webapp" if BASE_URL else ""

EAT_TZ = timezone(timedelta(hours=3))  # Ethiopia Time (UTC+3)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

REG_HEADERS = [
    "ID", "Name", "Grade", "Phone", "Status", "Timestamp", "Telegram_ID",
    "Approved_At", "Expires_On", "Months_Paid", "Last_Alert_Day",
]
PDF_HEADERS = [
    "Doc_ID", "File_Name", "Grade", "Stream", "Subject", "Category",
    "Year", "Exam_Tag", "Round_Or_Code", "Link_Key", "Linked_Doc_ID",
    "Has_Embedded_Answer", "Format", "File_Size_MB", "Source",
    "Drive_PDF_ID", "Drive_Original_ID", "Telegram_File_ID",
    "Unique_Key", "Post_Link", "Link_Status", "Is_Trial",
]
KEY_HEADERS = ["Doc_ID", "Total_Q", "Sections_JSON", "Answers_JSON", "Answer_Source_Doc_ID", "Updated_At"]
ANALYTICS_HEADERS = ["Timestamp", "Telegram_ID", "Student_Name", "Grade", "Action", "Doc_ID", "File_Name", "Subject", "Score"]

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Temporary stores for pending broadcasts & background scheduler
PENDING_BROADCASTS = {}
billing_task = None


# --- GOOGLE CREDENTIALS & CLIENTS ---
def get_credentials() -> Credentials:
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        return Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    if os.path.exists("/etc/secrets/credentials.json"):
        return Credentials.from_service_account_file("/etc/secrets/credentials.json", scopes=SCOPES)
    return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)


def ensure_headers(sheet, expected_headers):
    first_row = sheet.row_values(1)
    if not first_row or len(first_row) < len(expected_headers):
        sheet.update("A1", [expected_headers])


def get_or_create_worksheet(sheet_doc, title: str, headers: list[str]):
    try:
        ws = sheet_doc.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sheet_doc.add_worksheet(title=title, rows=1000, cols=max(26, len(headers)))
    ensure_headers(ws, headers)
    return ws


def get_sheets():
    creds = get_credentials()
    client = gspread.authorize(creds)
    sheet_doc = client.open(SHEET_NAME)
    reg_sheet = get_or_create_worksheet(sheet_doc, "Registrations", REG_HEADERS)
    pdf_sheet = get_or_create_worksheet(sheet_doc, "PDF_Library", PDF_HEADERS)
    return reg_sheet, pdf_sheet


def get_all_worksheets():
    creds = get_credentials()
    client = gspread.authorize(creds)
    sheet_doc = client.open(SHEET_NAME)
    reg_sheet = get_or_create_worksheet(sheet_doc, "Registrations", REG_HEADERS)
    pdf_sheet = get_or_create_worksheet(sheet_doc, "PDF_Library", PDF_HEADERS)
    keys_sheet = get_or_create_worksheet(sheet_doc, "Exam_Keys", KEY_HEADERS)
    analytics_sheet = get_or_create_worksheet(sheet_doc, "Analytics", ANALYTICS_HEADERS)
    return reg_sheet, pdf_sheet, keys_sheet, analytics_sheet


def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def library_keyboard(label="📚 Open Study Library"):
    if not WEBAPP_URL:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, web_app=WebAppInfo(url=WEBAPP_URL))]])


NAME, GRADE, PHONE = range(3)


# ==============================================================================
# 1. REGISTRATION & LIBRARY LAUNCH HANDLERS
# ==============================================================================
def find_registration_by_tg_id(reg_sheet, tg_id: int):
    rows = reg_sheet.get_all_values()
    for idx, row in enumerate(rows[1:], start=2):
        if len(row) >= 7 and str(row[6]).strip() == str(tg_id):
            status = row[4].strip().upper() if len(row) >= 5 else "NEW"
            name = row[1] if len(row) >= 2 else "Student"
            return idx, name, status
    return None


async def open_library_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    def _check():
        reg_sheet, _ = get_sheets()
        return find_registration_by_tg_id(reg_sheet, user_id)

    existing = await asyncio.to_thread(_check)
    status = existing[2] if existing else ("APPROVED" if user_id == ADMIN_USER_ID else "NOT_REGISTERED")

    if status == "NOT_REGISTERED":
        await update.message.reply_text("📝 Please register first by sending /start.")
        return
    if not WEBAPP_URL:
        await update.message.reply_text("⚠️ Web App URL is not configured yet.")
        return

    if status in ("APPROVED", "EXPIRED") or user_id == ADMIN_USER_ID:
        msg = "📚 Tap below to open the full <b>Bishoftu Tutoring Hub Study Library</b>:"
        btn_label = "📚 Open Study Library"
    else:
        msg = (
            "🎁 <b>Trial Preview Ready!</b>\n\n"
            "Your account currently has <b>3 preview PDFs</b> unlocked. "
            "300+ more exams, textbooks, and notes unlock once your registration is approved."
        )
        btn_label = "🎁 Open Trial Library (3 PDFs)"

    await update.message.reply_text(msg, reply_markup=library_keyboard(btn_label), parse_mode="HTML")


async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    def _check():
        reg_sheet, _ = get_sheets()
        return find_registration_by_tg_id(reg_sheet, user_id)

    existing = await asyncio.to_thread(_check)
    if existing:
        _, name, status = existing
        safe_name = html.escape(name)
        if status in ("APPROVED", "EXPIRED"):
            await update.message.reply_text(
                f"👋 Welcome back, <b>{safe_name}</b>!\n\n✅ Your library access is active.",
                reply_markup=library_keyboard(),
                parse_mode="HTML",
            )
            return ConversationHandler.END
        elif status == "NEW":
            await update.message.reply_text(
                f"⏳ Hi <b>{safe_name}</b>, our representative will call you soon to finish your registration.\n\n"
                f"Meanwhile, tap below to try our <b>3 free preview PDFs</b> (300+ more unlock on approval):",
                reply_markup=library_keyboard("🎁 Open Trial Library (3 PDFs)"),
                parse_mode="HTML",
            )
            return ConversationHandler.END
        elif status == "LEFT":
            await update.message.reply_text(
                f"👋 Hi <b>{safe_name}</b>, your monthly tutoring pass has expired.\n"
                f"You currently have access to the <b>3-PDF Trial Preview</b>. Contact us to renew anytime!",
                reply_markup=library_keyboard("🎁 Open Trial Library"),
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
    timestamp = datetime.now(EAT_TZ).strftime("%Y-%m-%d %H:%M")

    def _save():
        reg_sheet, _ = get_sheets()
        all_rows = reg_sheet.get_all_values()
        next_id = max(1, len(all_rows))
        reg_sheet.append_row([next_id, name, grade, phone, "NEW", timestamp, str(tg_id), "", "", "0", "-1"])

    await asyncio.to_thread(_save)
    webapp_router.invalidate_reg_cache()

    safe_name = html.escape(name)
    safe_grade = html.escape(grade)
    safe_phone = html.escape(phone)

    await update.message.reply_text(
        f"✅ <b>Pre-Registration Received!</b>\n\n"
        f"👤 <b>Name:</b> {safe_name}\n"
        f"🏫 <b>Grade:</b> {safe_grade}\n"
        f"📞 <b>Phone:</b> {safe_phone}\n\n"
        f"📞 <b>Next Step:</b> Our company representative will call you to complete your registration & payment, then unlock the full library.\n\n"
        f"🎁 Meanwhile, you can explore a <b>3-PDF Trial Preview</b> (300+ more resources unlock on approval!):",
        reply_markup=library_keyboard("🎁 Open Trial Library (3 PDFs)"),
        parse_mode="HTML",
    )

    keyboard = [[
        InlineKeyboardButton("✅ Approve (Start 30d)", callback_data=f"approve_user:{tg_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_user:{tg_id}"),
    ]]
    await context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=(
            f"🚨 <b>NEW REGISTRATION!</b>\n"
            f"👤 {safe_name} ({safe_grade})\n"
            f"📞 <code>{safe_phone}</code>\n"
            f"🆔 <code>{tg_id}</code>\n\n"
            f"Call & confirm payment, then tap Approve below or send /check_leads."
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Registration cancelled.")
    return ConversationHandler.END


# ==============================================================================
# 2. ADMIN APPROVALS, RENEWALS ("PAID") & DYNAMIC PDF PASSES
# ==============================================================================
async def send_student_pass_pdf(bot, student_row: list[str], months_paid: int, approved_at: str, expires_on: str, is_renewal: bool):
    tg_id = int(student_row[6].strip())
    pdf_buf = generate_membership_pdf(
        student_id=student_row[0],
        name=student_row[1],
        grade=student_row[2],
        phone=student_row[3],
        tg_id=tg_id,
        months_paid=months_paid,
        approved_at=approved_at,
        expires_on=expires_on,
        is_renewal=is_renewal,
    )
    filename = f"Bishoftu_Pass_{student_row[1].replace(' ', '_')}_M{months_paid}.pdf"
    caption = (
        f"🎉 <b>{'Monthly Renewal Confirmed!' if is_renewal else 'Welcome! Registration Approved!'}</b>\n\n"
        f"📄 Attached is your official Study Pass & Receipt (Valid until <b>{expires_on}</b>).\n"
        f"📚 Tap below to unlock all 300+ exams, textbooks & notes:"
    )
    await bot.send_document(
        chat_id=tg_id,
        document=pdf_buf,
        filename=filename,
        caption=caption,
        reply_markup=library_keyboard(),
        parse_mode="HTML",
    )


async def check_leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    def _fetch():
        reg_sheet, _ = get_sheets()
        return reg_sheet.get_all_values()

    rows = await asyncio.to_thread(_fetch)
    new_leads = [row for row in rows[1:] if len(row) >= 5 and row[4].strip().upper() == "NEW"]

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


async def handle_student_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    data = query.data
    await query.answer("Updating student record...")
    today = datetime.now(EAT_TZ).date()

    if data == "approve_all_new":
        def _approve_all():
            reg_sheet, _ = get_sheets()
            rows = reg_sheet.get_all_values()
            updates = []
            approved_students = []
            expires_str = (today + timedelta(days=30)).isoformat()
            today_str = today.isoformat()
            for idx, row in enumerate(rows[1:], start=2):
                r = row + [""] * (11 - len(row))
                if r[4].strip().upper() == "NEW" and r[6].strip():
                    updates.append({
                        "range": f"E{idx}:K{idx}",
                        "values": [["APPROVED", r[5], r[6], today_str, expires_str, "1", "0"]],
                    })
                    approved_students.append((r, 1, today_str, expires_str))
            if updates:
                reg_sheet.batch_update(updates)
            return approved_students

        approved_list = await asyncio.to_thread(_approve_all)
        webapp_router.invalidate_reg_cache()

        for row, months, app_at, exp_on in approved_list:
            try:
                await send_student_pass_pdf(context.bot, row, months, app_at, exp_on, is_renewal=False)
            except Exception as e:
                logger.warning(f"Failed sending pass PDF to {row[6]}: {e}")

        await query.edit_message_text(
            f"✅ Approved <b>{len(approved_list)}</b> student(s) and sent their PDF passes!",
            parse_mode="HTML",
        )
        return

    action, tg_id_str = data.split(":", 1)

    if action in ("approve_user", "mark_paid"):
        is_renewal = action == "mark_paid"

        def _activate_or_renew():
            reg_sheet, _ = get_sheets()
            rows = reg_sheet.get_all_values()
            for idx, row in enumerate(rows[1:], start=2):
                r = row + [""] * (11 - len(row))
                if r[6].strip() == tg_id_str:
                    prev_months = int(r[9]) if r[9].isdigit() else 0
                    new_months = prev_months + 1
                    # Preserve remaining days if renewing early before expiry
                    new_expires = today + timedelta(days=30)
                    if is_renewal and r[8]:
                        try:
                            old_exp = datetime.strptime(r[8], "%Y-%m-%d").date()
                            if old_exp >= today:
                                new_expires = old_exp + timedelta(days=30)
                        except ValueError:
                            pass
                    app_at = r[7] if (is_renewal and r[7]) else today.isoformat()
                    exp_str = new_expires.isoformat()
                    reg_sheet.update(
                        f"E{idx}:K{idx}",
                        [["APPROVED", r[5], r[6], app_at, exp_str, str(new_months), "0"]],
                    )
                    return r, new_months, today.isoformat(), exp_str
            return None

        res = await asyncio.to_thread(_activate_or_renew)
        webapp_router.invalidate_reg_cache()

        if not res:
            await query.edit_message_text("⚠️ Student not found in Google Sheet.")
            return

        r, months, issue_date, exp_str = res
        try:
            await send_student_pass_pdf(context.bot, r, months, issue_date, exp_str, is_renewal=is_renewal)
        except Exception as e:
            logger.warning(f"Could not send PDF pass to {tg_id_str}: {e}")

        await query.edit_message_text(
            f"{'💰 Renewed' if is_renewal else '✅ Approved'} <b>{html.escape(r[1])}</b> (Month #{months}, Valid until <b>{exp_str}</b>).\n📄 Official PDF pass sent to student!",
            parse_mode="HTML",
        )
        return

    if action in ("reject_user", "mark_left"):
        new_status = "REJECTED" if action == "reject_user" else "LEFT"

        def _set_status():
            reg_sheet, _ = get_sheets()
            rows = reg_sheet.get_all_values()
            for idx, row in enumerate(rows[1:], start=2):
                if len(row) >= 7 and row[6].strip() == tg_id_str:
                    reg_sheet.update_cell(idx, 5, new_status)
                    return row[1]
            return None

        name = await asyncio.to_thread(_set_status)
        webapp_router.invalidate_reg_cache()
        if name:
            if new_status == "LEFT":
                try:
                    await context.bot.send_message(
                        chat_id=int(tg_id_str),
                        text="ℹ️ Your monthly Bishoftu Tutoring Hub subscription has ended. You can still browse our 3-PDF Trial Library anytime, or message us to renew!",
                    )
                except Exception:
                    pass
            await query.edit_message_text(
                f"{'🚪 Marked LEFT' if new_status == 'LEFT' else '❌ Rejected'}: <b>{html.escape(name)}</b>",
                parse_mode="HTML",
            )


# ==============================================================================
# 3. AUTOMATED 30-DAY BILLING CHECKER & GRACE PERIOD ALERTS
# ==============================================================================
async def run_daily_billing_check(bot):
    today = datetime.now(EAT_TZ).date()

    def _scan_billing():
        reg_sheet, _ = get_sheets()
        rows = reg_sheet.get_all_values()
        updates = []
        alerts = []  # (kind, student_name, grade, phone, tg_id, elapsed_day, days_left)

        for idx, row in enumerate(rows[1:], start=2):
            r = row + [""] * (11 - len(row))
            status = r[4].strip().upper()
            tg_id = r[6].strip()
            exp_str = r[8].strip()
            if not tg_id or not exp_str or status not in ("APPROVED", "EXPIRED"):
                continue

            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            days_left = (exp_date - today).days
            elapsed_day = 30 - days_left  # Day 30 => days_left == 0; Day 37 => days_left == -7
            last_alert = int(r[10]) if r[10].lstrip("-").isdigit() else -1

            if elapsed_day in (23, 26, 29) and status == "APPROVED" and last_alert < elapsed_day:
                updates.append({"range": f"K{idx}", "values": [[str(elapsed_day)]]})
                alerts.append(("REMINDER", r[1], r[2], r[3], tg_id, elapsed_day, days_left))

            elif 30 <= elapsed_day <= 37 and last_alert < elapsed_day:
                # Set EXPIRED on Day 30 (student still keeps library access during 7-day grace window!)
                if status != "EXPIRED":
                    updates.append({"range": f"E{idx}", "values": [["EXPIRED"]]})
                updates.append({"range": f"K{idx}", "values": [[str(elapsed_day)]]})
                alerts.append(("GRACE", r[1], r[2], r[3], tg_id, elapsed_day, days_left))

            elif elapsed_day >= 38:
                updates.append({"range": f"E{idx}", "values": [["LEFT"]]})
                updates.append({"range": f"K{idx}", "values": [[str(elapsed_day)]]})
                alerts.append(("AUTO_LEFT", r[1], r[2], r[3], tg_id, elapsed_day, days_left))

        if updates:
            reg_sheet.batch_update(updates)
        return alerts

    alerts = await asyncio.to_thread(_scan_billing)
    if alerts:
        webapp_router.invalidate_reg_cache()

    for kind, name, grade, phone, tg_id, day_num, days_left in alerts:
        safe_name = html.escape(name)
        safe_phone = html.escape(phone)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("💰 Paid (+30d)", callback_data=f"mark_paid:{tg_id}"),
            InlineKeyboardButton("🚪 Mark Left", callback_data=f"mark_left:{tg_id}"),
        ]])

        if kind == "REMINDER":
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=(
                    f"⏰ <b>Renewal Reminder — Day {day_num}/30 ({days_left}d left)</b>\n"
                    f"👤 {safe_name} ({html.escape(grade)})\n"
                    f"📞 <code>{safe_phone}</code>"
                ),
                reply_markup=kb,
                parse_mode="HTML",
            )
        elif kind == "GRACE":
            grace_day = day_num - 30
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=(
                    f"⚠️ <b>EXPIRED (Grace Day {grace_day}/7 — Day {day_num})</b>\n"
                    f"👤 {safe_name} ({html.escape(grade)})\n"
                    f"📞 <code>{safe_phone}</code>\n"
                    f"<i>Student still has access during the 1-week grace period. Mark Paid or Left:</i>"
                ),
                reply_markup=kb,
                parse_mode="HTML",
            )
        elif kind == "AUTO_LEFT":
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=(
                    f"🔴 <b>AUTO-MOVED TO LEFT (Day {day_num})</b>\n"
                    f"👤 {safe_name} ({html.escape(grade)})\n"
                    f"📞 <code>{safe_phone}</code>\n"
                    f"<i>Grace week ended. Access downgraded to 3-PDF Trial.</i>"
                ),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Reactivate (Paid)", callback_data=f"mark_paid:{tg_id}")]]),
                parse_mode="HTML",
            )
            try:
                await bot.send_message(
                    chat_id=int(tg_id),
                    text="ℹ️ Your Bishoftu Tutoring Hub monthly plan has ended. Your account is now in 3-PDF Trial mode until renewed.",
                )
            except Exception:
                pass


async def billing_scheduler_loop(bot):
    await asyncio.sleep(15)
    while True:
        try:
            await run_daily_billing_check(bot)
        except Exception as e:
            logger.error(f"Billing check error: {e}")
        await asyncio.sleep(4 * 3600)  # Check every 4 hours (idempotent via Last_Alert_Day)


# ==============================================================================
# 4. ADMIN STATS & TARGETED BROADCASTS
# ==============================================================================
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    today = datetime.now(EAT_TZ).date()

    def _gather():
        reg_sheet, pdf_sheet, keys_sheet, analytics_sheet = get_all_worksheets()
        reg_rows = reg_sheet.get_all_values()[1:]
        pdf_rows = pdf_sheet.get_all_values()[1:]
        key_rows = keys_sheet.get_all_values()[1:]
        ana_rows = analytics_sheet.get_all_values()[1:]

        counts = {"APPROVED": 0, "NEW": 0, "EXPIRED": 0, "LEFT": 0, "REJECTED": 0}
        expiring_soon = []
        for row in reg_rows:
            r = row + [""] * (11 - len(row))
            st = r[4].strip().upper() or "NEW"
            counts[st] = counts.get(st, 0) + 1
            if st in ("APPROVED", "EXPIRED") and r[8]:
                try:
                    d_left = (datetime.strptime(r[8], "%Y-%m-%d").date() - today).days
                    expiring_soon.append((d_left, r[1], r[2], st))
                except ValueError:
                    pass
        expiring_soon.sort(key=lambda x: x[0])

        verified_links = sum(1 for r in pdf_rows if len(r) >= 21 and r[20] in ("AUTO_VERIFIED", "MANUAL_VERIFIED"))
        needs_review = sum(1 for r in pdf_rows if len(r) >= 21 and r[20] == "NEEDS_REVIEW")
        unlinked_answers = sum(1 for r in pdf_rows if len(r) >= 11 and r[5] == "Answer Sheet" and not r[10])

        # Popular resources from Analytics
        popularity = {}
        for a in ana_rows:
            if len(a) >= 7 and a[4] in ("VIEW", "DOWNLOAD", "SEND_CHAT"):
                popularity[a[6]] = popularity.get(a[6], 0) + 1
        top_docs = sorted(popularity.items(), key=lambda x: x[1], reverse=True)[:5]

        return counts, expiring_soon[:8], len(pdf_rows), len(key_rows), verified_links, needs_review, unlinked_answers, top_docs

    counts, upcoming, total_pdfs, total_keys, verified_links, needs_review, unlinked_ans, top_docs = await asyncio.to_thread(_gather)

    lines = [
        "📊 <b>BISHOFTU TUTORING HUB — STATS</b>\n",
        f"👥 <b>Students:</b> {counts.get('APPROVED',0)} Approved | {counts.get('NEW',0)} Pending | {counts.get('EXPIRED',0)} Grace | {counts.get('LEFT',0)} Left",
        f"📚 <b>Library:</b> {total_pdfs} Resources | {len(range(verified_links))} Verified Links | {total_keys} Quiz Keys",
        f"⚠️ <b>Link Review Needed:</b> {needs_review} | <b>Unlinked Answers:</b> {unlinked_ans}\n",
    ]
    if upcoming:
        lines.append("⏳ <b>Days Left (Closest Renewals):</b>")
        for d_left, name, grade, st in upcoming:
            badge = f"{d_left}d left" if d_left >= 0 else f"EXPIRED {-d_left}d ago"
            lines.append(f"• {html.escape(name)} ({html.escape(grade)}): <b>{badge}</b> [{st}]")
        lines.append("")

    if top_docs:
        lines.append("🔥 <b>Most Popular Resources:</b>")
        for fname, hits in top_docs:
            lines.append(f"• {html.escape(fname[:40])} — <b>{hits}</b> views/downloads")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    raw = update.message.text.partition(" ")[2].strip()
    if not raw:
        await update.message.reply_text(
            "📢 <b>How to use /broadcast:</b>\n\n"
            "• <code>/broadcast All Hello students, check the library!</code>\n"
            "• <code>/broadcast Grade 12 New 2018 Physics Model uploaded!</code>\n"
            "• <code>/broadcast Grade 8 Tomorrow's class starts at 2:30 LT.</code>\n"
            "• <code>/broadcast New Complete your registration for full access!</code>",
            parse_mode="HTML",
        )
        return

    low = raw.lower()
    target_label = "All Students"
    filter_fn = lambda row: True
    message_text = raw

    for prefix, label, fn in [
        ("all ", "All Registered Students", lambda r: True),
        ("approved ", "Approved Students", lambda r: r[4].strip().upper() in ("APPROVED", "EXPIRED")),
        ("new ", "Pending (NEW) Students", lambda r: r[4].strip().upper() == "NEW"),
        ("grade 12 ", "Grade 12 Students", lambda r: "12" in r[2]),
        ("grade 8 ", "Grade 8 Students", lambda r: "8" in r[2]),
        ("grade 6 ", "Grade 6 Students", lambda r: "6" in r[2]),
    ]:
        if low.startswith(prefix):
            target_label = label
            filter_fn = fn
            message_text = raw[len(prefix):].strip()
            break

    if not message_text:
        await update.message.reply_text("⚠️ Please write a message after the target group.")
        return

    def _get_recipients():
        reg_sheet, _ = get_sheets()
        rows = reg_sheet.get_all_values()[1:]
        ids = []
        for row in rows:
            r = row + [""] * (11 - len(row))
            if r[6].strip() and filter_fn(r):
                ids.append(int(r[6].strip()))
        return list(dict.fromkeys(ids))

    recipients = await asyncio.to_thread(_get_recipients)
    if not recipients:
        await update.message.reply_text(f"⚠️ No students matched target: <b>{target_label}</b>", parse_mode="HTML")
        return

    bid = str(update.message.message_id)
    PENDING_BROADCASTS[bid] = {"recipients": recipients, "text": message_text, "target": target_label}

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"🚀 Send to {len(recipients)} Students", callback_data=f"bc_send:{bid}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"bc_cancel:{bid}"),
    ]])
    await update.message.reply_text(
        f"📢 <b>Broadcast Preview</b>\n"
        f"🎯 <b>Target:</b> {target_label} ({len(recipients)} users)\n\n"
        f"<i>{html.escape(message_text)}</i>",
        reply_markup=kb,
        parse_mode="HTML",
    )


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    action, bid = query.data.split(":", 1)
    payload = PENDING_BROADCASTS.pop(bid, None)
    if action == "bc_cancel" or not payload:
        await query.answer("Cancelled")
        await query.edit_message_text("❌ Broadcast cancelled.")
        return

    await query.answer("Sending broadcast...")
    await query.edit_message_text(f"📤 Sending to {len(payload['recipients'])} students...")

    sent = 0
    failed = 0
    formatted = f"📢 <b>Announcement — Bishoftu Tutoring Hub</b>\n\n{html.escape(payload['text'])}"
    for uid in payload["recipients"]:
        try:
            await context.bot.send_message(chat_id=uid, text=formatted, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await query.edit_message_text(
        f"✅ <b>Broadcast Complete!</b>\n🎯 Target: {payload['target']}\n📨 Sent: {sent} | Failed: {failed}",
        parse_mode="HTML",
    )


# ==============================================================================
# 5. CONTENT-AWARE PDF LINK VERIFIER (/verify_links & /review_links)
# ==============================================================================
async def download_doc_bytes(drive_token: str | None, drive_pdf_id: str, telegram_file_id: str) -> bytes | None:
    if drive_pdf_id and drive_token:
        url = f"https://www.googleapis.com/drive/v3/files/{drive_pdf_id}?alt=media&supportsAllDrives=true"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {drive_token}"})
            if r.status_code == 200:
                return r.content
    if telegram_file_id:
        tg_file = await ptb_app.bot.get_file(telegram_file_id)
        f_url = tg_file.file_path if tg_file.file_path.startswith("http") else f"https://api.telegram.org/file/bot{BOT_TOKEN}/{tg_file.file_path}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.get(f_url)
            if r.status_code == 200:
                return r.content
    return None


async def verify_links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    status_msg = await update.message.reply_text("🔍 Inspecting PDF contents to verify Exam ↔ Answer links & parse Quiz keys...")

    def _load():
        _, pdf_sheet, keys_sheet, _ = get_all_worksheets()
        pdf_rows = pdf_sheet.get_all_values()
        key_rows = keys_sheet.get_all_values()
        creds = get_credentials()
        if not creds.valid:
            creds.refresh(GoogleAuthRequest())
        return pdf_sheet, keys_sheet, pdf_rows, key_rows, creds.token

    pdf_sheet, keys_sheet, pdf_rows, key_rows, drive_token = await asyncio.to_thread(_load)

    by_id = {}
    for idx, row in enumerate(pdf_rows[1:], start=2):
        r = row + [""] * (22 - len(row))
        by_id[r[0]] = (idx, r)

    existing_key_ids = {r[0] for r in key_rows[1:] if r}
    pdf_updates = []
    new_keys = []
    verified_count = 0
    rejected_count = 0
    review_count = 0
    embedded_keys_parsed = 0
    now_str = datetime.now(EAT_TZ).strftime("%Y-%m-%d %H:%M")

    # 1. Verify linked Exam <-> Answer Sheet pairs
    for doc_id, (row_idx, r) in by_id.items():
        cat = r[5]
        linked_id = r[10]
        link_status = r[20]
        size_mb = float(r[13]) if r[13] else 0.0

        # Skip already manually/auto verified pairs unless missing quiz key
        if cat != "Answer Sheet" and linked_id and linked_id in by_id:
            if link_status in ("AUTO_VERIFIED", "MANUAL_VERIFIED") and doc_id in existing_key_ids:
                continue

            ans_row_idx, ans_r = by_id[linked_id]
            ans_size = float(ans_r[13]) if ans_r[13] else 0.0
            if size_mb > 25 or ans_size > 25:
                pdf_updates.append({"range": f"U{row_idx}", "values": [["NEEDS_REVIEW"]]})
                pdf_updates.append({"range": f"U{ans_row_idx}", "values": [["NEEDS_REVIEW"]]})
                review_count += 1
                continue

            exam_bytes = await download_doc_bytes(drive_token, r[15], r[17])
            ans_bytes = await download_doc_bytes(drive_token, ans_r[15], ans_r[17])
            if not exam_bytes or not ans_bytes:
                continue

            result = await asyncio.to_thread(verify_exam_answer_pair, exam_bytes, ans_bytes)
            st = result["status"]

            if st == "AUTO_VERIFIED":
                verified_count += 1
                pdf_updates.append({"range": f"U{row_idx}", "values": [["AUTO_VERIFIED"]]})
                pdf_updates.append({"range": f"U{ans_row_idx}", "values": [["AUTO_VERIFIED"]]})
                if result["answers"] and doc_id not in existing_key_ids:
                    new_keys.append([
                        doc_id,
                        result["total_q"],
                        json.dumps(result["sections"]),
                        json.dumps(result["answers"]),
                        linked_id,
                        now_str,
                    ])
                    existing_key_ids.add(doc_id)

            elif st == "REJECTED_MISMATCH":
                rejected_count += 1
                # Clear false Linked_Doc_ID from both rows!
                pdf_updates.append({"range": f"K{row_idx}", "values": [[""]]})
                pdf_updates.append({"range": f"K{ans_row_idx}", "values": [[""]]})
                pdf_updates.append({"range": f"U{row_idx}", "values": [["REJECTED_MISMATCH"]]})
                pdf_updates.append({"range": f"U{ans_row_idx}", "values": [["REJECTED_MISMATCH"]]})

            else:
                review_count += 1
                pdf_updates.append({"range": f"U{row_idx}", "values": [["NEEDS_REVIEW"]]})
                pdf_updates.append({"range": f"U{ans_row_idx}", "values": [["NEEDS_REVIEW"]]})

        # 2. Also extract quiz keys from exams that have answers embedded at the end
        elif r[11] == "Yes" and cat in ("Entrance Exam", "Model Exam", "Pilot Exam", "Practice / Weekly Exam") and doc_id not in existing_key_ids and size_mb <= 25:
            exam_bytes = await download_doc_bytes(drive_token, r[15], r[17])
            if exam_bytes:
                ex_info = await asyncio.to_thread(analyze_exam_pdf, exam_bytes)
                emb = ex_info.get("embedded_answers") or {}
                if len(emb) >= 15:
                    new_keys.append([
                        doc_id,
                        max(int(k) for k in emb.keys()),
                        json.dumps(ex_info.get("sections", [])),
                        json.dumps(emb),
                        doc_id,
                        now_str,
                    ])
                    existing_key_ids.add(doc_id)
                    embedded_keys_parsed += 1

    def _save_results():
        if pdf_updates:
            for i in range(0, len(pdf_updates), 200):
                pdf_sheet.batch_update(pdf_updates[i : i + 200])
        if new_keys:
            keys_sheet.append_rows(new_keys, value_input_option="USER_ENTERED")

    await asyncio.to_thread(_save_results)
    webapp_router.invalidate_library_cache()

    await status_msg.edit_text(
        f"✅ <b>PDF Content Verification Complete!</b>\n\n"
        f"✔️ <b>Auto-Verified Pairs:</b> {verified_count}\n"
        f"❌ <b>False Links Removed:</b> {rejected_count}\n"
        f"🧐 <b>Needs Manual Review (Scanned/Unclear):</b> {review_count}\n"
        f"🎯 <b>Quiz Answer Keys Parsed:</b> {len(new_keys)} ({embedded_keys_parsed} embedded)\n\n"
        f"{'Send /review_links to confirm scanned pairs.' if review_count else ''}",
        parse_mode="HTML",
    )


async def review_links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    def _get_reviews():
        _, pdf_sheet = get_sheets()
        rows = pdf_sheet.get_all_values()[1:]
        by_id = {r[0]: r for r in rows if r}
        pairs = []
        for r in rows:
            padded = r + [""] * (22 - len(r))
            if padded[20] == "NEEDS_REVIEW" and padded[5] != "Answer Sheet" and padded[10] in by_id:
                pairs.append((padded, by_id[padded[10]] + [""] * (22 - len(by_id[padded[10]]))))
        return pairs[:5]

    pairs = await asyncio.to_thread(_get_reviews)
    if not pairs:
        await update.message.reply_text("✅ No pairs currently waiting for manual review!")
        return

    for ex_r, ans_r in pairs:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirm Match", callback_data=f"link_ok:{ex_r[0]}:{ans_r[0]}"),
            InlineKeyboardButton("❌ Unlink", callback_data=f"link_no:{ex_r[0]}:{ans_r[0]}"),
        ]])
        await update.message.reply_text(
            f"🧐 <b>Verify Link (Scanned / Unclear)</b>\n\n"
            f"📄 <b>Exam ({ex_r[0]}):</b> {html.escape(ex_r[1])}\n"
            f"🔑 <b>Answer ({ans_r[0]}):</b> {html.escape(ans_r[1])}",
            reply_markup=kb,
            parse_mode="HTML",
        )


async def link_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    action, ex_id, ans_id = query.data.split(":", 2)
    await query.answer("Updating link...")

    def _apply():
        _, pdf_sheet = get_sheets()
        rows = pdf_sheet.get_all_values()
        updates = []
        for idx, r in enumerate(rows[1:], start=2):
            if r and r[0] in (ex_id, ans_id):
                if action == "link_ok":
                    updates.append({"range": f"U{idx}", "values": [["MANUAL_VERIFIED"]]})
                else:
                    updates.append({"range": f"K{idx}", "values": [[""]]})
                    updates.append({"range": f"U{idx}", "values": [["REJECTED_MISMATCH"]]})
        if updates:
            pdf_sheet.batch_update(updates)

    await asyncio.to_thread(_apply)
    webapp_router.invalidate_library_cache()
    await query.edit_message_text(
        f"{'✅ Link confirmed!' if action == 'link_ok' else '❌ Link removed.'} ({ex_id} ↔ {ans_id})"
    )


# ==============================================================================
# 6. SYNC DRIVE & LIVE CHANNEL CATEGORIZER (PRESERVED + CACHE SYNC)
# ==============================================================================
async def convert_office_via_apps_script(drive_file_id: str) -> str | None:
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
    except Exception as e:
        logger.warning(f"Converter request failed for {drive_file_id}: {e}")
    return None


def compute_exam_answer_links(all_rows_with_headers: list[list[str]]):
    if len(all_rows_with_headers) <= 1:
        return []
    exams_exact, exams_base, answers = {}, {}, []
    for row_idx, row in enumerate(all_rows_with_headers[1:], start=2):
        if len(row) < 12:
            continue
        doc_id, cat, link_key, linked_id, has_embedded = row[0], row[5], row[9], row[10], row[11]
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
        ex_row_idx, ex_doc_id, ex_linked = candidates[0]
        updates.append({"range": f"K{ans_row_idx}", "values": [[ex_doc_id]]})
        if not ex_linked:
            updates.append({"range": f"K{ex_row_idx}", "values": [[ans_doc_id]]})
    return updates


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
        await update.message.reply_text("⚠️ <code>DRIVE_FOLDER_ID</code> is not set.", parse_mode="HTML")
        return

    status_msg = await update.message.reply_text("🔄 Scanning Google Drive folder and classifying files...")

    def _prepare_sync():
        _, pdf_sheet = get_sheets()
        existing_rows = pdf_sheet.get_all_values()
        drive_service = get_drive_service()
        drive_files = list_drive_files_recursive(drive_service, DRIVE_FOLDER_ID)
        return pdf_sheet, existing_rows, drive_files

    try:
        pdf_sheet, existing_rows, drive_files = await asyncio.to_thread(_prepare_sync)
    except Exception as e:
        await status_msg.edit_text(f"❌ Drive sync failed: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
        return

    existing_drive_ids, existing_unique_keys, stem_to_row_idx = set(), set(), {}
    for idx, row in enumerate(existing_rows[1:], start=2):
        if len(row) >= 16 and row[15]:
            existing_drive_ids.add(row[15])
        if len(row) >= 17 and row[16]:
            existing_drive_ids.add(row[16])
        if len(row) >= 19 and row[18]:
            existing_unique_keys.add(row[18])
        if len(row) >= 2:
            stem_to_row_idx[normalize_stem(row[1])] = idx

    grouped_files, seen_md5 = {}, set(existing_unique_keys)
    skipped_excluded = skipped_duplicates = 0

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
        if ext not in grouped_files[stem]:
            grouped_files[stem][ext] = f

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

    next_num = len(existing_rows)
    new_rows, twin_updates = [], []

    for stem, ext_map in sorted(grouped_files.items()):
        pdf_file = ext_map.get("pdf")
        office_file = ext_map.get("pptx") or ext_map.get("docx")
        if stem in stem_to_row_idx and office_file and not pdf_file:
            twin_updates.append({"range": f"Q{stem_to_row_idx[stem]}", "values": [[office_file["id"]]]})
            continue
        primary = pdf_file or office_file
        if not primary:
            continue

        meta = classify_material(primary["name"])
        doc_id = f"DOC-{next_num:04d}"
        next_num += 1
        formats = [fmt for fmt, cond in [("PDF", pdf_file), ("PPTX", "pptx" in ext_map), ("DOCX", "docx" in ext_map)] if cond]
        size_mb = round(int(primary.get("size") or 0) / (1024 * 1024), 2)

        new_rows.append([
            doc_id, primary["name"], meta["grade"], meta["stream"], meta["subject"],
            meta["category"], meta["year"], meta["exam_tag"], meta["round_or_code"],
            meta["link_key"], "", meta["has_embedded_answer"], " + ".join(formats),
            size_mb, "Drive", pdf_file["id"] if pdf_file else "",
            office_file["id"] if office_file else "", "", primary.get("md5Checksum") or primary["id"], "", "", "",
        ])

    def _write_and_link():
        if twin_updates:
            pdf_sheet.batch_update(twin_updates)
        if new_rows:
            for i in range(0, len(new_rows), 250):
                pdf_sheet.append_rows(new_rows[i : i + 250], value_input_option="USER_ENTERED")
        updated_table = pdf_sheet.get_all_values()
        link_updates = compute_exam_answer_links(updated_table)
        if link_updates:
            pdf_sheet.batch_update(link_updates)
        return len(link_updates) // 2

    paired_count = await asyncio.to_thread(_write_and_link)
    webapp_router.invalidate_library_cache()

    await status_msg.edit_text(
        f"✅ <b>Google Drive Sync Complete!</b>\n\n"
        f"📥 <b>Added:</b> {len(new_rows)} | 📄 <b>Converted:</b> {converted_count}\n"
        f"🔗 <b>Candidate Pairs Found:</b> {paired_count}\n"
        f"♻️ <b>Duplicates Skipped:</b> {skipped_duplicates} | 🚫 <b>Excluded:</b> {skipped_excluded}\n\n"
        f"👉 Next, send /verify_links so I inspect the PDF contents and parse quiz keys!",
        parse_mode="HTML",
    )


async def auto_categorize_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post or not post.document or not post.document.file_name:
        return
    doc = post.document
    excluded, _ = is_excluded_file(doc.file_name)
    if excluded:
        return

    meta = classify_material(doc.file_name, post.caption or "")
    ext = doc.file_name.rsplit(".", 1)[-1].upper()
    size_mb = round((doc.file_size or 0) / (1024 * 1024), 2)
    post_link = post.link if post.link else "Channel Document"

    def _append_and_link():
        _, pdf_sheet = get_sheets()
        rows = pdf_sheet.get_all_values()
        for r in rows[1:]:
            if len(r) >= 19 and r[18] == doc.file_unique_id:
                return None, 0
        doc_id = f"DOC-{len(rows):04d}"
        pdf_sheet.append_row([
            doc_id, doc.file_name, meta["grade"], meta["stream"], meta["subject"],
            meta["category"], meta["year"], meta["exam_tag"], meta["round_or_code"],
            meta["link_key"], "", meta["has_embedded_answer"], ext, size_mb,
            "Telegram", "", "", doc.file_id, doc.file_unique_id, post_link, "", "",
        ])
        updated_table = pdf_sheet.get_all_values()
        link_updates = compute_exam_answer_links(updated_table)
        if link_updates:
            pdf_sheet.batch_update(link_updates)
        return doc_id, len(link_updates)

    doc_id, _ = await asyncio.to_thread(_append_and_link)
    webapp_router.invalidate_library_cache()


# ==============================================================================
# 7. FASTAPI APP, MINI APP ROUTER & LIFECYCLE
# ==============================================================================
app = FastAPI()
ptb_app = Application.builder().token(BOT_TOKEN).updater(None).build()

webapp_router = create_webapp_router(
    bot_token=BOT_TOKEN,
    admin_user_id=ADMIN_USER_ID,
    get_ptb_app=lambda: ptb_app,
    get_sheets_fn=get_sheets,
    get_credentials_fn=get_credentials,
    reg_headers=REG_HEADERS,
    pdf_headers=PDF_HEADERS,
)
app.include_router(webapp_router)

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
ptb_app.add_handler(CommandHandler("library", open_library_command))
ptb_app.add_handler(CommandHandler("check_leads", check_leads))
ptb_app.add_handler(CommandHandler("stats", stats_command))
ptb_app.add_handler(CommandHandler("broadcast", broadcast_command))
ptb_app.add_handler(CommandHandler("sync_drive", sync_drive_command))
ptb_app.add_handler(CommandHandler("verify_links", verify_links_command))
ptb_app.add_handler(CommandHandler("review_links", review_links_command))

ptb_app.add_handler(CallbackQueryHandler(handle_student_action_callback, pattern=r"^(approve_user:|reject_user:|mark_paid:|mark_left:|approve_all_new)"))
ptb_app.add_handler(CallbackQueryHandler(broadcast_callback, pattern=r"^(bc_send:|bc_cancel:)"))
ptb_app.add_handler(CallbackQueryHandler(link_review_callback, pattern=r"^(link_ok:|link_no:)"))
ptb_app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.Document.ALL, auto_categorize_file))


@app.on_event("startup")
async def startup_event():
    global billing_task
    await ptb_app.initialize()
    await ptb_app.start()
    if WEBAPP_URL:
        try:
            await ptb_app.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="📚 Library", web_app=WebAppInfo(url=WEBAPP_URL))
            )
        except Exception as e:
            logger.warning(f"Menu button error: {e}")
    billing_task = asyncio.create_task(billing_scheduler_loop(ptb_app.bot))


@app.on_event("shutdown")
async def shutdown_event():
    if billing_task:
        billing_task.cancel()
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
