import os
import json
import html
import uuid
import asyncio
import logging
import threading
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from urllib.parse import quote

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
    filters,
)

from classifier import classify_material, is_excluded_file, normalize_stem
from link_verifier import (
    analyze_exam_pdf,
    analyze_answer_pdf,
    score_exam_answer_match,
)
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
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

EAT_TZ = timezone(timedelta(hours=3))

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

REG_HEADERS = [
    "ID", "Name", "Grade", "Phone", "Status", "Timestamp", "Telegram_ID",
    "Approved_At", "Expires_On", "Months_Paid", "Last_Alert_Day", "Stream",
    "Referral_Code", "Referred_By", "Referral_Count", "Role", "Format", "Lang",
]
STUDENTS_HEADERS = [
    "Student_ID", "Student_Name", "Grade", "Stream", "Format",
    "Parent_TG_ID", "Child_TG_ID", "Child_Contact", "Link_Token", "Sibling_Discount", "Created_At",
]
REPORTS_HEADERS = [
    "Report_ID", "Student_ID", "Period", "Attendance", "Scores_Text",
    "Improved_Note", "Focus_Note", "Approval_Status", "Published_At", "Tutor_Name",
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
CONFIG_HEADERS = ["Key", "Value"]
PROGRESS_HEADERS = ["Telegram_ID", "Bookmarks_JSON", "Last_Read_JSON", "Plan_Progress_JSON", "Custom_Plan_JSON", "Updated_At"]

DEFAULT_CONFIG = {
    "LAUNCH_MODE": "OPEN_LAUNCH",
    "MATRIC_DATE": "2027-06-25",
    "GRADE8_MINISTRY_DATE": "2027-06-15",
    "GRADE6_MINISTRY_DATE": "2027-06-10",
    "SEMESTER_DATE": "2027-01-25",
}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

PENDING_BROADCASTS = {}
billing_task = None

_SHEETS_LOCK = threading.Lock()
_SHEETS_READY = False
_CACHED_SHEET_ID = None


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
        sheet.update(values=[expected_headers], range_name="A1")


def get_or_create_worksheet(sheet_doc, title: str, headers: list[str], defaults: dict | None = None):
    created = False
    try:
        ws = sheet_doc.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sheet_doc.add_worksheet(title=title, rows=1000, cols=max(26, len(headers)))
        created = True
    ensure_headers(ws, headers)
    if created and defaults:
        ws.append_rows([[k, v] for k, v in defaults.items()], value_input_option="USER_ENTERED")
    return ws


def _get_spreadsheet(client):
    global _CACHED_SHEET_ID
    if _CACHED_SHEET_ID:
        try:
            return client.open_by_key(_CACHED_SHEET_ID)
        except Exception:
            _CACHED_SHEET_ID = None
    doc = client.open(SHEET_NAME)
    _CACHED_SHEET_ID = doc.id
    return doc


def _ensure_all_tabs_once(sheet_doc):
    global _SHEETS_READY
    if _SHEETS_READY:
        return
    with _SHEETS_LOCK:
        if _SHEETS_READY:
            return
        get_or_create_worksheet(sheet_doc, "Registrations", REG_HEADERS)
        get_or_create_worksheet(sheet_doc, "PDF_Library", PDF_HEADERS)
        get_or_create_worksheet(sheet_doc, "Exam_Keys", KEY_HEADERS)
        get_or_create_worksheet(sheet_doc, "Analytics", ANALYTICS_HEADERS)
        get_or_create_worksheet(sheet_doc, "Config", CONFIG_HEADERS, DEFAULT_CONFIG)
        get_or_create_worksheet(sheet_doc, "Student_Progress", PROGRESS_HEADERS)
        get_or_create_worksheet(sheet_doc, "Students", STUDENTS_HEADERS)
        get_or_create_worksheet(sheet_doc, "Progress_Reports", REPORTS_HEADERS)
        _SHEETS_READY = True


def get_sheets():
    client = gspread.authorize(get_credentials())
    sheet_doc = _get_spreadsheet(client)
    _ensure_all_tabs_once(sheet_doc)
    return sheet_doc.worksheet("Registrations"), sheet_doc.worksheet("PDF_Library")


def get_all_worksheets():
    global _SHEETS_READY
    client = gspread.authorize(get_credentials())
    sheet_doc = _get_spreadsheet(client)
    _ensure_all_tabs_once(sheet_doc)
    try:
        return (
            sheet_doc.worksheet("Registrations"),
            sheet_doc.worksheet("PDF_Library"),
            sheet_doc.worksheet("Exam_Keys"),
            sheet_doc.worksheet("Analytics"),
            sheet_doc.worksheet("Config"),
            sheet_doc.worksheet("Student_Progress"),
            sheet_doc.worksheet("Students"),
            sheet_doc.worksheet("Progress_Reports"),
        )
    except gspread.WorksheetNotFound:
        _SHEETS_READY = False
        _ensure_all_tabs_once(sheet_doc)
        return (
            sheet_doc.worksheet("Registrations"),
            sheet_doc.worksheet("PDF_Library"),
            sheet_doc.worksheet("Exam_Keys"),
            sheet_doc.worksheet("Analytics"),
            sheet_doc.worksheet("Config"),
            sheet_doc.worksheet("Student_Progress"),
            sheet_doc.worksheet("Students"),
            sheet_doc.worksheet("Progress_Reports"),
        )


def get_config_dict(config_sheet=None) -> dict:
    if config_sheet is None:
        _, _, _, _, config_sheet, _, _, _ = get_all_worksheets()
    rows = config_sheet.get_all_values()[1:]
    cfg = dict(DEFAULT_CONFIG)
    for r in rows:
        if len(r) >= 2 and r[0].strip():
            cfg[r[0].strip()] = r[1].strip()
    return cfg


def set_config_value(key: str, value: str):
    _, _, _, _, config_sheet, _, _, _ = get_all_worksheets()
    rows = config_sheet.get_all_values()
    for idx, r in enumerate(rows[1:], start=2):
        if r and r[0].strip() == key:
            config_sheet.update_cell(idx, 2, value)
            return
    config_sheet.append_row([key, value])


def get_drive_service():
    return build("drive", "v3", credentials=get_credentials(), cache_discovery=False)


def webapp_keyboard(label: str, ref_code: str = ""):
    if not WEBAPP_URL:
        return None
    target_url = f"{WEBAPP_URL}?ref={quote(ref_code)}" if ref_code else WEBAPP_URL
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, web_app=WebAppInfo(url=target_url))]])


def referral_invite_url(ref_code: str) -> str:
    if BOT_USERNAME and ref_code:
        return f"https://t.me/{BOT_USERNAME}?start=ref_{ref_code}"
    return ""


# ==============================================================================
# 1. BILINGUAL /START LAUNCHER, CHILD LINKING & REFERRAL COMMAND
# ==============================================================================
def find_registration_by_tg_id(reg_sheet, tg_id: int):
    for idx, row in enumerate(reg_sheet.get_all_values()[1:], start=2):
        r = row + [""] * (18 - len(row))
        if str(r[6]).strip() == str(tg_id):
            return idx, r
    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    arg = context.args[0].strip() if context.args else ""

    if arg.startswith("child_"):
        def _link_child():
            reg_sheet, _, _, _, _, _, students_sheet, _ = get_all_worksheets()
            for idx, row in enumerate(students_sheet.get_all_values()[1:], start=2):
                s = row + [""] * (11 - len(row))
                if s[8].strip() == arg:
                    students_sheet.update_cell(idx, 7, str(user_id))
                    if not find_registration_by_tg_id(reg_sheet, user_id):
                        all_regs = reg_sheet.get_all_values()
                        my_code = f"QELAL-{uuid.uuid4().hex[:5].upper()}"
                        ts = datetime.now(EAT_TZ).strftime("%Y-%m-%d %H:%M")
                        reg_sheet.append_row([
                            max(1, len(all_regs)), s[1], s[2], "", "APPROVED", ts, str(user_id),
                            "", "", "0", "-1", s[3], my_code, "", "0", "student", s[4], "en",
                        ])
                    return s[1], s[2]
            return None

        linked = await asyncio.to_thread(_link_child)
        webapp_router.invalidate_reg_cache()
        if linked:
            c_name, c_grade = linked
            await update.message.reply_text(
                f"✅ <b>Account Linked Successfully! | አካውንቱ ተገናኝቷል!</b>\n\n"
                f"👋 Welcome <b>{html.escape(c_name)}</b> ({html.escape(c_grade)})!\n"
                f"Tap below to open your Library, Quizzes &amp; Study Plans!\n\n"
                f"የቀላል የጥናት ማዕከል አካውንትዎ ተከፍቷል። ከታች ያለውን ቁልፍ ተጭነው ይጠቀሙ!",
                reply_markup=webapp_keyboard("🚀 Open My Study Hub | ክፈት"),
                parse_mode="HTML",
            )
            return

    ref_param = arg[4:].upper() if arg.startswith("ref_") else ""

    def _check_existing():
        reg_sheet, _, _, _, _, _, students_sheet, _ = get_all_worksheets()
        reg = find_registration_by_tg_id(reg_sheet, user_id)
        child_match = None
        for r in students_sheet.get_all_values()[1:]:
            if len(r) >= 7 and r[6].strip() == str(user_id):
                child_match = r
                break
        return reg, child_match

    existing_reg, child_match = await asyncio.to_thread(_check_existing)

    if existing_reg or child_match:
        name = existing_reg[1][1] if existing_reg else child_match[1]
        await update.message.reply_text(
            f"👋 <b>Welcome back, {html.escape(name)}! | እንኳን ደህና መጡ!</b>\n\n"
            f"Tap below to open your <b>Qelal Learning (ቀላል)</b> Library, Interactive Quizzes, Study Plans &amp; Progress Dashboard.\n\n"
            f"📞 Need help? Call: <code>+251 933 510 682</code> / <code>+251 988 666 328</code>",
            reply_markup=webapp_keyboard("🚀 Open Qelal Hub • ቀላልን ክፈት"),
            parse_mode="HTML",
        )
        return

    ref_line = f"\n🎁 <b>Referral Code Applied:</b> <code>{html.escape(ref_param)}</code>\n" if ref_param else ""
    welcome_msg = (
        f"✨ <b>QELAL LEARNING (ቀላል) — Bishoftu Study &amp; Exam Hub</b>\n"
        f"<i>Effortless Exam Prep. Zero Clutter. Built for Grades 1–12.</i>\n"
        f"{ref_line}\n"
        f"🇬🇧 <b>English:</b>\n"
        f"Prepare smarter for <b>Grade 6 &amp; 8 Ministry</b>, <b>Grade 12 ESSLCE (Matric)</b>, and school exams with <b>400+ organized textbooks &amp; past papers</b>, <b>auto-graded bubble-sheet quizzes</b>, <b>personalized study plans</b>, and <b>bi-weekly parent progress reports</b> (with <b>sibling discounts</b> for 2+ children!).\n\n"
        f"🇪🇹 <b>አማርኛ:</b>\n"
        f"ከ1ኛ–12ኛ ክፍል (ለ6ኛ፣ 8ኛ ሚኒስትሪ እና ለ12ኛ ክፍል ብሔራዊ ፈተና) የሚያዘጋጁ <b>400+ መጽሐፍትና ያለፉ ፈተናዎች</b>፣ <b>ውጤት ወዲያውኑ የሚያሳዩ ጥያቄዎች</b>፣ <b>የጥናት እቅዶች</b> እና <b>ለወላጆች የልጆች ውጤት መከታተያ</b> በአንድ ቦታ!\n\n"
        f"👉 <b>How to Register | እንዴት መመዝገብ ይችላሉ:</b>\n"
        f"1️⃣ <b>Online (60 Seconds):</b> Tap below to choose <b>English / አማርኛ</b> and register inside the Mini App.\n"
        f"2️⃣ <b>Call Us Directly | በስልክ ይደውሉ:</b>\n"
        f"📞 <code>+251 933 510 682</code>\n"
        f"📞 <code>+251 988 666 328</code>"
    )
    await update.message.reply_text(
        welcome_msg,
        reply_markup=webapp_keyboard("🚀 Launch Qelal Mini App • መተግበሪያውን ክፈት", ref_code=ref_param),
        parse_mode="HTML",
    )


async def open_library_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    def _get_or_create_code():
        reg_sheet, _ = get_sheets()
        found = find_registration_by_tg_id(reg_sheet, user_id)
        if not found:
            return None
        idx, r = found
        code = r[12].strip()
        if not code:
            code = f"QELAL-{uuid.uuid4().hex[:5].upper()}"
            reg_sheet.update_cell(idx, 13, code)
        count = int(r[14]) if r[14].isdigit() else 0
        return r[1], code, count

    res = await asyncio.to_thread(_get_or_create_code)
    if not res:
        await update.message.reply_text(
            "📝 Please launch the Mini App via /start to register and get your Referral Code!\n"
            "እባክዎ መጀመሪያ /start በመጫን ይመዝገቡ።",
            reply_markup=webapp_keyboard("🚀 Register in Mini App • ተመዝገብ"),
        )
        return

    name, code, count = res
    link = referral_invite_url(code)
    share_text = f"Join me at Qelal Learning (Bishoftu) for Grades 1-12 Exam Prep & Quizzes! Use my code: {code}"
    share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(share_text)}" if link else ""
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Share Invite on Telegram", url=share_url)]]) if share_url else None

    await update.message.reply_text(
        f"🎁 <b>Study Squad Referral Program | የግብዣ ፕሮግራም</b>\n\n"
        f"👤 <b>Name:</b> {html.escape(name)}\n"
        f"🔑 <b>Your Code:</b> <code>{code}</code>\n"
        f"🤝 <b>Verified Referrals:</b> <b>{count}</b> friend(s)\n"
        f"{f'🔗 <b>Invite Link:</b> {link}' if link else ''}\n\n"
        f"💡 <i>Invite 2 friends for Study Squad seating, bound formula folders &amp; tuition perks!</i>",
        reply_markup=kb,
        parse_mode="HTML",
    )


# ==============================================================================
# 2. LAUNCH PHASE TOGGLE (/end_launch & /reopen_launch)
# ==============================================================================
async def end_launch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    cfg = await asyncio.to_thread(get_config_dict)
    if cfg.get("LAUNCH_MODE") == "PAID_GATED":
        await update.message.reply_text("ℹ️ Launch Phase is already ended. Paid/Approved access mode is active.")
        return

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔴 Confirm: End Launch Phase", callback_data="launch_confirm:PAID_GATED"),
        InlineKeyboardButton("❌ Keep Free Launch", callback_data="launch_cancel"),
    ]])
    await update.message.reply_text(
        "⚠️ <b>Confirm Ending Launch Phase?</b>\n\n"
        "• Only <b>APPROVED</b> (and 7-day grace <b>EXPIRED</b>) users keep unlimited access.\n"
        "• All <b>NEW</b> and <b>LEFT</b> users switch to <b>Trial Mode</b> (3 grade books + limited Study Plan + 10-Q Quiz preview).",
        reply_markup=kb,
        parse_mode="HTML",
    )


async def reopen_launch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    await asyncio.to_thread(set_config_value, "LAUNCH_MODE", "OPEN_LAUNCH")
    webapp_router.invalidate_config_cache()
    await update.message.reply_text("🎉 Reopened <b>OPEN_LAUNCH</b> mode (all registered users have unlimited free access).", parse_mode="HTML")


async def launch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return
    await query.answer()
    if query.data == "launch_cancel":
        await query.edit_message_text("✅ Kept <b>OPEN_LAUNCH</b> mode active.", parse_mode="HTML")
        return

    await asyncio.to_thread(set_config_value, "LAUNCH_MODE", "PAID_GATED")
    webapp_router.invalidate_config_cache()
    await query.edit_message_text("🔒 <b>Launch Phase Ended!</b> Only approved/paid members now get unlimited access.", parse_mode="HTML")


# ==============================================================================
# 3. ADMIN APPROVALS, REFERRALS, RENEWALS & PDF PASSES
# ==============================================================================
async def send_student_pass_pdf(bot, student_row: list[str], months_paid: int, approved_at: str, expires_on: str, is_renewal: bool):
    tg_id = int(student_row[6].strip())
    grade_str = f"{student_row[2]} ({student_row[11]})" if len(student_row) >= 12 and student_row[11] and student_row[11] != "General" else student_row[2]
    ref_code = student_row[12] if len(student_row) >= 13 else ""

    pdf_buf = generate_membership_pdf(
        student_id=student_row[0], name=student_row[1], grade=grade_str, phone=student_row[3],
        tg_id=tg_id, months_paid=months_paid, approved_at=approved_at, expires_on=expires_on,
        referral_code=ref_code, is_renewal=is_renewal,
    )
    filename = f"Qelal_Pass_{student_row[1].replace(' ', '_')}_M{months_paid}.pdf"
    caption = (
        f"🎉 <b>{'Monthly Renewal Confirmed!' if is_renewal else 'Registration Approved! | ምዝገባዎ ጸድቋል!'}</b>\n\n"
        f"📄 Attached is your official Qelal Pass &amp; Receipt (Valid until <b>{expires_on}</b>).\n"
        f"📚 Tap below to unlock all 400+ books, exams &amp; full quizzes!"
    )
    await bot.send_document(
        chat_id=tg_id, document=pdf_buf, filename=filename, caption=caption,
        reply_markup=webapp_keyboard("🚀 Open Qelal Hub • ክፈት"), parse_mode="HTML",
    )


def credit_referrer_if_first_approval(reg_sheet, all_rows: list[list[str]], student_row: list[str]):
    months_prev = int(student_row[9]) if len(student_row) > 9 and student_row[9].isdigit() else 0
    referred_by = student_row[13].strip().upper() if len(student_row) > 13 else ""
    if months_prev > 0 or not referred_by:
        return None

    for idx, row in enumerate(all_rows[1:], start=2):
        r = row + [""] * (18 - len(row))
        if r[12].strip().upper() == referred_by and r[6].strip() != student_row[6].strip():
            new_cnt = (int(r[14]) if r[14].isdigit() else 0) + 1
            r[14] = str(new_cnt)
            all_rows[idx - 1] = r
            reg_sheet.update_cell(idx, 15, str(new_cnt))
            return int(r[6].strip()), r[1], referred_by, new_cnt, student_row[1]
    return None


async def notify_referrer(bot, credit_info):
    if not credit_info:
        return
    ref_tg_id, _, code, new_cnt, friend_name = credit_info
    try:
        await bot.send_message(
            chat_id=ref_tg_id,
            text=(
                f"🎉 <b>Referral Reward Credited!</b>\n\n"
                f"<b>{html.escape(friend_name)}</b> was just approved using your code <code>{code}</code>!\n"
                f"🤝 <b>Verified Referrals:</b> <b>{new_cnt}</b>"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Failed notifying referrer {ref_tg_id}: {e}")


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
        r = row + [""] * (18 - len(row))
        role_tag = "👨‍👩‍👧 Parent" if r[15] == "parent" else "🎓 Student"
        msg += f"• {role_tag} <b>{html.escape(r[1])}</b> | {html.escape(r[2])} | <code>{html.escape(r[3])}</code>\n"
        if r[6].strip():
            buttons.append([InlineKeyboardButton(f"✅ Approve {r[1]}", callback_data=f"approve_user:{r[6].strip()}")])

    buttons.append([InlineKeyboardButton("✔️ Approve All NEW Leads", callback_data="approve_all_new")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


async def handle_student_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return

    data = query.data
    await query.answer("Updating record...")
    today = datetime.now(EAT_TZ).date()

    if data == "approve_all_new":
        def _approve_all():
            reg_sheet, _ = get_sheets()
            rows = reg_sheet.get_all_values()
            updates, approved_students, ref_credits = [], [], []
            expires_str = (today + timedelta(days=30)).isoformat()
            today_str = today.isoformat()
            for idx, row in enumerate(rows[1:], start=2):
                r = row + [""] * (18 - len(row))
                if r[4].strip().upper() == "NEW" and r[6].strip():
                    ref_code = r[12] or f"QELAL-{uuid.uuid4().hex[:5].upper()}"
                    updates.append({
                        "range": f"E{idx}:R{idx}",
                        "values": [[
                            "APPROVED", r[5], r[6], today_str, expires_str, "1", "0",
                            r[11] or "General", ref_code, r[13], r[14] or "0",
                            r[15] or "student", r[16] or "Weekend Hub", r[17] or "en",
                        ]],
                    })
                    r[12] = ref_code
                    approved_students.append((r, 1, today_str, expires_str))
                    c_info = credit_referrer_if_first_approval(reg_sheet, rows, r)
                    if c_info:
                        ref_credits.append(c_info)
            if updates:
                reg_sheet.batch_update(updates)
            return approved_students, ref_credits

        approved_list, ref_credits = await asyncio.to_thread(_approve_all)
        webapp_router.invalidate_reg_cache()

        for row, months, app_at, exp_on in approved_list:
            try:
                await send_student_pass_pdf(context.bot, row, months, app_at, exp_on, is_renewal=False)
            except Exception as e:
                logger.warning(f"Pass PDF send failed for {row[6]}: {e}")
        for ci in ref_credits:
            await notify_referrer(context.bot, ci)

        await query.edit_message_text(f"✅ Approved <b>{len(approved_list)}</b> account(s) and sent PDF passes!", parse_mode="HTML")
        return

    action, tg_id_str = data.split(":", 1)

    if action in ("approve_user", "mark_paid"):
        is_renewal = action == "mark_paid"

        def _activate_or_renew():
            reg_sheet, _ = get_sheets()
            rows = reg_sheet.get_all_values()
            for idx, row in enumerate(rows[1:], start=2):
                r = row + [""] * (18 - len(row))
                if r[6].strip() == tg_id_str:
                    prev_months = int(r[9]) if r[9].isdigit() else 0
                    new_months = prev_months + 1
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
                    ref_code = r[12] or f"QELAL-{uuid.uuid4().hex[:5].upper()}"
                    reg_sheet.update(
                        values=[[
                            "APPROVED", r[5], r[6], app_at, exp_str, str(new_months), "0",
                            r[11] or "General", ref_code, r[13], r[14] or "0",
                            r[15] or "student", r[16] or "Weekend Hub", r[17] or "en",
                        ]],
                        range_name=f"E{idx}:R{idx}",
                    )
                    r[12] = ref_code
                    c_info = credit_referrer_if_first_approval(reg_sheet, rows, r)
                    return r, new_months, today.isoformat(), exp_str, c_info
            return None

        res = await asyncio.to_thread(_activate_or_renew)
        webapp_router.invalidate_reg_cache()
        if not res:
            await query.edit_message_text("⚠️ Record not found in Google Sheet.")
            return

        r, months, issue_date, exp_str, c_info = res
        try:
            await send_student_pass_pdf(context.bot, r, months, issue_date, exp_str, is_renewal=is_renewal)
        except Exception as e:
            logger.warning(f"Could not send PDF pass to {tg_id_str}: {e}")
        await notify_referrer(context.bot, c_info)

        ref_note = f"\n🎁 Credited referral to {html.escape(c_info[1])} (Total: {c_info[3]})" if c_info else ""
        await query.edit_message_text(
            f"{'💰 Renewed' if is_renewal else '✅ Approved'} <b>{html.escape(r[1])}</b> (Month #{months}, Valid until <b>{exp_str}</b>).{ref_note}",
            parse_mode="HTML",
        )
        return

    if action in ("reject_user", "mark_left"):
        new_status = "REJECTED" if action == "reject_user" else "LEFT"

        def _set_status():
            reg_sheet, _ = get_sheets()
            for idx, row in enumerate(reg_sheet.get_all_values()[1:], start=2):
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
                        text="ℹ️ Your monthly tutoring plan has ended. Your account is now in 3-PDF Trial mode until renewed.",
                    )
                except Exception:
                    pass
            await query.edit_message_text(f"{'🚪 Marked LEFT' if new_status == 'LEFT' else '❌ Rejected'}: <b>{html.escape(name)}</b>", parse_mode="HTML")


# ==============================================================================
# 4. PARENT PROGRESS REPORT ADMIN APPROVAL GATE (/review_reports)
# ==============================================================================
async def review_reports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    def _fetch():
        _, _, _, _, _, _, students_sheet, reports_sheet = get_all_worksheets()
        stu_map = {}
        for row in students_sheet.get_all_values()[1:]:
            s = row + [""] * (11 - len(row))
            if s[0]:
                stu_map[s[0]] = s
        pending = []
        for idx, row in enumerate(reports_sheet.get_all_values()[1:], start=2):
            rp = row + [""] * (10 - len(row))
            if rp[7].strip() == "Pending_Admin":
                pending.append((idx, rp, stu_map.get(rp[1])))
        return pending[:5]

    pending = await asyncio.to_thread(_fetch)
    if not pending:
        await update.message.reply_text("✅ All progress reports reviewed! No Pending_Admin rows.")
        return

    for row_idx, rp, stu in pending:
        s_name = stu[1] if stu else rp[1]
        s_grade = stu[2] if stu else ""
        p_tg = stu[5] if stu else "Not Linked"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve & Send", callback_data=f"rpt_approve:{row_idx}"),
            InlineKeyboardButton("⏸ Hold", callback_data=f"rpt_hold:{row_idx}"),
            InlineKeyboardButton("❌ Skip", callback_data=f"rpt_skip:{row_idx}"),
        ]])
        await update.message.reply_text(
            f"📋 <b>APPROVE PROGRESS REPORT?</b>\n"
            f"👤 <b>Student:</b> {html.escape(s_name)} ({html.escape(s_grade)})\n"
            f"🗓 <b>Period:</b> {html.escape(rp[2])} | 👨‍🏫 {html.escape(rp[9] or 'Tutor')}\n"
            f"✅ <b>Attendance:</b> {html.escape(rp[3])}\n"
            f"📊 <b>Scores:</b> {html.escape(rp[4])}\n"
            f"🔼 <b>Improved:</b> {html.escape(rp[5])}\n"
            f"🎯 <b>Next Focus:</b> {html.escape(rp[6])}\n"
            f"👨‍👩‍👧 <b>Parent TG:</b> <code>{p_tg}</code>",
            reply_markup=kb,
            parse_mode="HTML",
        )


async def handle_report_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return
    await query.answer()

    action, row_idx_str = query.data.split(":", 1)
    row_idx = int(row_idx_str)

    def _apply():
        _, _, _, _, _, _, students_sheet, reports_sheet = get_all_worksheets()
        rp = reports_sheet.row_values(row_idx) + [""] * 10
        stu = None
        for row in students_sheet.get_all_values()[1:]:
            if row and row[0] == rp[1]:
                stu = row + [""] * (11 - len(row))
                break

        if action == "rpt_approve":
            now_str = datetime.now(EAT_TZ).strftime("%Y-%m-%d %H:%M")
            reports_sheet.update(values=[["Approved", now_str]], range_name=f"H{row_idx}:I{row_idx}")
        elif action == "rpt_hold":
            reports_sheet.update_cell(row_idx, 8, "Held")
        else:
            reports_sheet.update_cell(row_idx, 8, "Skipped")
        return rp, stu

    rp, stu = await asyncio.to_thread(_apply)
    webapp_router.invalidate_reg_cache()

    s_name = stu[1] if stu else rp[1]
    if action == "rpt_approve":
        parent_tg = stu[5].strip() if stu else ""
        if parent_tg:
            try:
                await context.bot.send_message(
                    chat_id=int(parent_tg),
                    text=(
                        f"📊 <b>QELAL BI-WEEKLY PROGRESS REPORT</b>\n\n"
                        f"👤 <b>Student:</b> {html.escape(s_name)} ({html.escape(stu[2])})\n"
                        f"🗓 <b>Period:</b> {html.escape(rp[2])}\n"
                        f"✅ <b>Attendance:</b> {html.escape(rp[3])}\n"
                        f"📈 <b>Scores:</b> {html.escape(rp[4])}\n"
                        f"🔼 <b>Improved:</b> {html.escape(rp[5])}\n"
                        f"🎯 <b>Next Focus:</b> {html.escape(rp[6])}"
                    ),
                    reply_markup=webapp_keyboard("📊 View in Parent Dashboard"),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Could not send report to parent {parent_tg}: {e}")
        await query.edit_message_text(f"✅ Approved &amp; published report for <b>{html.escape(s_name)}</b>!", parse_mode="HTML")
    elif action == "rpt_hold":
        await query.edit_message_text(f"⏸ Held report for <b>{html.escape(s_name)}</b>.", parse_mode="HTML")
    else:
        await query.edit_message_text(f"❌ Skipped report for <b>{html.escape(s_name)}</b>.", parse_mode="HTML")


# ==============================================================================
# 5. AUTOMATED 30-DAY BILLING CHECKER & GRACE ALERTS
# ==============================================================================
async def run_daily_billing_check(bot):
    today = datetime.now(EAT_TZ).date()

    def _scan_billing():
        reg_sheet, _ = get_sheets()
        updates, alerts = [], []
        for idx, row in enumerate(reg_sheet.get_all_values()[1:], start=2):
            r = row + [""] * (18 - len(row))
            status, tg_id, exp_str = r[4].strip().upper(), r[6].strip(), r[8].strip()
            if not tg_id or not exp_str or status not in ("APPROVED", "EXPIRED"):
                continue
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            days_left = (exp_date - today).days
            elapsed_day = 30 - days_left
            last_alert = int(r[10]) if r[10].lstrip("-").isdigit() else -1

            if elapsed_day in (23, 26, 29) and status == "APPROVED" and last_alert < elapsed_day:
                updates.append({"range": f"K{idx}", "values": [[str(elapsed_day)]]})
                alerts.append(("REMINDER", r[1], r[2], r[3], tg_id, elapsed_day, days_left))
            elif 30 <= elapsed_day <= 37 and last_alert < elapsed_day:
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
        safe_name, safe_phone = html.escape(name), html.escape(phone)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("💰 Paid (+30d)", callback_data=f"mark_paid:{tg_id}"),
            InlineKeyboardButton("🚪 Mark Left", callback_data=f"mark_left:{tg_id}"),
        ]])
        if kind == "REMINDER":
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"⏰ <b>Renewal Reminder — Day {day_num}/30 ({days_left}d left)</b>\n👤 {safe_name} ({html.escape(grade)})\n📞 <code>{safe_phone}</code>",
                reply_markup=kb, parse_mode="HTML",
            )
        elif kind == "GRACE":
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"⚠️ <b>EXPIRED (Grace Day {day_num - 30}/7 — Day {day_num})</b>\n👤 {safe_name} ({html.escape(grade)})\n📞 <code>{safe_phone}</code>\n<i>User keeps access during the 7-day grace window.</i>",
                reply_markup=kb, parse_mode="HTML",
            )
        elif kind == "AUTO_LEFT":
            await bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"🔴 <b>AUTO-MOVED TO LEFT (Day {day_num})</b>\n👤 {safe_name} ({html.escape(grade)})\n📞 <code>{safe_phone}</code>\n<i>Grace week ended. Downgraded to Trial.</i>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Reactivate (Paid)", callback_data=f"mark_paid:{tg_id}")]]),
                parse_mode="HTML",
            )
            try:
                await bot.send_message(chat_id=int(tg_id), text="ℹ️ Your monthly tutoring plan has ended. Your account is now in 3-PDF Trial mode until renewed.")
            except Exception:
                pass
    return len(alerts)


async def check_billing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    sent = await run_daily_billing_check(context.bot)
    if sent == 0:
        await update.message.reply_text("✅ Billing check complete — no new reminders or expirations today.")


async def billing_scheduler_loop(bot):
    await asyncio.sleep(15)
    while True:
        try:
            await run_daily_billing_check(bot)
        except Exception as e:
            logger.error(f"Billing check error: {e}")
        await asyncio.sleep(4 * 3600)


# ==============================================================================
# 6. STATS, BROADCASTS, SMART LINK VERIFIER & DRIVE SYNC
# ==============================================================================
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    today = datetime.now(EAT_TZ).date()

    def _gather():
        reg_sheet, pdf_sheet, keys_sheet, analytics_sheet, cfg_sheet, _, students_sheet, _ = get_all_worksheets()
        reg_rows = reg_sheet.get_all_values()[1:]
        pdf_rows = pdf_sheet.get_all_values()[1:]
        key_rows = keys_sheet.get_all_values()[1:]
        ana_rows = analytics_sheet.get_all_values()[1:]
        stu_rows = students_sheet.get_all_values()[1:]
        cfg = get_config_dict(cfg_sheet)

        counts = {"APPROVED": 0, "NEW": 0, "EXPIRED": 0, "LEFT": 0, "REJECTED": 0}
        expiring_soon, total_refs = [], 0
        for row in reg_rows:
            r = row + [""] * (18 - len(row))
            st = r[4].strip().upper() or "NEW"
            counts[st] = counts.get(st, 0) + 1
            if r[14].isdigit():
                total_refs += int(r[14])
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

        popularity = {}
        for a in ana_rows:
            if len(a) >= 7 and a[4] in ("VIEW", "SEND_CHAT", "QUIZ_SUBMIT"):
                popularity[a[6]] = popularity.get(a[6], 0) + 1
        top_docs = sorted(popularity.items(), key=lambda x: x[1], reverse=True)[:5]

        return cfg.get("LAUNCH_MODE", "OPEN_LAUNCH"), counts, len(stu_rows), total_refs, expiring_soon[:8], len(pdf_rows), len(key_rows), verified_links, needs_review, unlinked_answers, top_docs

    launch_mode, counts, total_students, total_refs, upcoming, total_pdfs, total_keys, verified_links, needs_review, unlinked_ans, top_docs = await asyncio.to_thread(_gather)

    lines = [
        "📊 <b>QELAL LEARNING — ADMIN STATS</b>\n",
        f"🚦 <b>Mode:</b> <code>{launch_mode}</code> ({'/end_launch to gate' if launch_mode == 'OPEN_LAUNCH' else 'Paid/Approved Gated'})",
        f"👥 <b>Accounts:</b> {counts.get('APPROVED',0)} Approved | {counts.get('NEW',0)} Pending | {counts.get('EXPIRED',0)} Grace | {counts.get('LEFT',0)} Left",
        f"🎓 <b>Total Enrolled Students:</b> {total_students} | 🤝 <b>Referrals:</b> {total_refs}",
        f"📚 <b>Library:</b> {total_pdfs} Resources | {verified_links} Verified Links | {total_keys} Quiz Keys",
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
            lines.append(f"• {html.escape(fname[:40])} — <b>{hits}</b> actions")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    raw = update.message.text.partition(" ")[2].strip()
    if not raw:
        await update.message.reply_text(
            "📢 <b>How to use /broadcast:</b>\n\n"
            "• <code>/broadcast All Hello everyone, check the library!</code>\n"
            "• <code>/broadcast Parents Bi-weekly progress reports are ready!</code>\n"
            "• <code>/broadcast Grade 12 New 2018 Physics Model uploaded!</code>\n"
            "• <code>/broadcast Grade 8 Ministry mock quiz added!</code>\n"
            "• <code>/broadcast Natural Biology unit 4 notes added!</code>\n"
            "• <code>/broadcast Social History notes updated!</code>\n"
            "• <code>/broadcast Approved Class starts Saturday 2:30 LT.</code>\n"
            "• <code>/broadcast New Call +251 933 510 682 to complete payment!</code>",
            parse_mode="HTML",
        )
        return

    low = raw.lower()
    target_label, filter_fn, message_text = "All Registered Accounts", (lambda row: True), raw
    for prefix, label, fn in [
        ("all ", "All Registered Accounts", lambda r: True),
        ("parents ", "All Parents", lambda r: r[15].strip().lower() == "parent"),
        ("approved ", "Approved Accounts", lambda r: r[4].strip().upper() in ("APPROVED", "EXPIRED")),
        ("new ", "Pending (NEW) Accounts", lambda r: r[4].strip().upper() == "NEW"),
        ("natural ", "Natural Science Students", lambda r: r[11].strip().lower() == "natural"),
        ("social ", "Social Science Students", lambda r: r[11].strip().lower() == "social"),
        ("grade 12 ", "Grade 12 Students", lambda r: r[2].strip() == "Grade 12"),
        ("grade 11 ", "Grade 11 Students", lambda r: r[2].strip() == "Grade 11"),
        ("grade 8 ", "Grade 8 Students", lambda r: r[2].strip() == "Grade 8"),
        ("grade 6 ", "Grade 6 Students", lambda r: r[2].strip() == "Grade 6"),
    ]:
        if low.startswith(prefix):
            target_label, filter_fn, message_text = label, fn, raw[len(prefix):].strip()
            break

    if not message_text:
        await update.message.reply_text("⚠️ Write a message after the target group.")
        return

    def _get_recipients():
        reg_sheet, _ = get_sheets()
        ids = []
        for row in reg_sheet.get_all_values()[1:]:
            r = row + [""] * (18 - len(row))
            if r[6].strip() and filter_fn(r):
                ids.append(int(r[6].strip()))
        return list(dict.fromkeys(ids))

    recipients = await asyncio.to_thread(_get_recipients)
    if not recipients:
        await update.message.reply_text(f"⚠️ No accounts matched target: <b>{target_label}</b>", parse_mode="HTML")
        return

    bid = str(update.message.message_id)
    PENDING_BROADCASTS[bid] = {"recipients": recipients, "text": message_text, "target": target_label}
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"🚀 Send to {len(recipients)} Users", callback_data=f"bc_send:{bid}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"bc_cancel:{bid}"),
    ]])
    await update.message.reply_text(
        f"📢 <b>Broadcast Preview</b>\n🎯 <b>Target:</b> {target_label} ({len(recipients)} users)\n\n<i>{html.escape(message_text)}</i>",
        reply_markup=kb, parse_mode="HTML",
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

    await query.answer("Sending...")
    await query.edit_message_text(f"📤 Sending to {len(payload['recipients'])} users...")
    sent = failed = 0
    formatted = f"📢 <b>Announcement — Qelal Learning (ቀላል)</b>\n\n{html.escape(payload['text'])}"
    for uid in payload["recipients"]:
        try:
            await context.bot.send_message(chat_id=uid, text=formatted, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await query.edit_message_text(f"✅ <b>Broadcast Complete!</b>\n🎯 Target: {payload['target']}\n📨 Sent: {sent} | Failed: {failed}", parse_mode="HTML")


async def download_doc_bytes(drive_token: str | None, drive_pdf_id: str, telegram_file_id: str) -> bytes | None:
    if drive_pdf_id and drive_token:
        url = f"https://www.googleapis.com/drive/v3/files/{drive_pdf_id}?alt=media&supportsAllDrives=true"
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {drive_token}"})
            if r.status_code == 200:
                return r.content
    if telegram_file_id:
        tg_file = await ptb_app.bot.get_file(telegram_file_id)
        f_url = tg_file.file_path if tg_file.file_path.startswith("http") else f"https://api.telegram.org/file/bot{BOT_TOKEN}/{tg_file.file_path}"
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            r = await client.get(f_url)
            if r.status_code == 200:
                return r.content
    return None


async def verify_links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    status_msg = await update.message.reply_text("🔍 Inspecting PDFs to verify & smart-match Exam ↔ Answer links...")

    def _load():
        _, pdf_sheet, keys_sheet, _, _, _, _, _ = get_all_worksheets()
        creds = get_credentials()
        if not creds.valid:
            creds.refresh(GoogleAuthRequest())
        return pdf_sheet, keys_sheet, pdf_sheet.get_all_values(), keys_sheet.get_all_values(), creds.token

    pdf_sheet, keys_sheet, pdf_rows, key_rows, drive_token = await asyncio.to_thread(_load)
    by_id = {(row + [""] * (22 - len(row)))[0]: (idx, row + [""] * (22 - len(row))) for idx, row in enumerate(pdf_rows[1:], start=2) if row}
    existing_key_ids = {r[0] for r in key_rows[1:] if r}

    pdf_updates, new_keys = [], []
    verified_count = rejected_count = review_count = embedded_keys_parsed = newly_discovered = 0
    now_str = datetime.now(EAT_TZ).strftime("%Y-%m-%d %H:%M")

    exam_cache, ans_cache = {}, {}

    async def get_exam_analysis(doc_id, r):
        if doc_id not in exam_cache:
            b = await download_doc_bytes(drive_token, r[15], r[17])
            exam_cache[doc_id] = await asyncio.to_thread(analyze_exam_pdf, b) if b else None
        return exam_cache[doc_id]

    async def get_ans_analysis(doc_id, r):
        if doc_id not in ans_cache:
            b = await download_doc_bytes(drive_token, r[15], r[17])
            ans_cache[doc_id] = await asyncio.to_thread(analyze_answer_pdf, b) if b else None
        return ans_cache[doc_id]

    for doc_id, (row_idx, r) in by_id.items():
        cat, linked_id, link_status = r[5], r[10], r[20]
        size_mb = float(r[13]) if r[13] else 0.0

        if cat != "Answer Sheet" and linked_id and linked_id in by_id:
            if link_status in ("AUTO_VERIFIED", "MANUAL_VERIFIED") and doc_id in existing_key_ids:
                continue
            ans_row_idx, ans_r = by_id[linked_id]
            ans_size = float(ans_r[13]) if ans_r[13] else 0.0
            if size_mb > 25 or ans_size > 25:
                pdf_updates.extend([{"range": f"U{row_idx}", "values": [["NEEDS_REVIEW"]]}, {"range": f"U{ans_row_idx}", "values": [["NEEDS_REVIEW"]]}])
                review_count += 1
                continue

            ex_info = await get_exam_analysis(doc_id, r)
            ans_info = await get_ans_analysis(linked_id, ans_r)
            if not ex_info or not ans_info:
                continue

            result = score_exam_answer_match(ex_info, ans_info, same_round_hint=(r[8] == ans_r[8]))
            if result["status"] == "AUTO_VERIFIED":
                verified_count += 1
                pdf_updates.extend([{"range": f"U{row_idx}", "values": [["AUTO_VERIFIED"]]}, {"range": f"U{ans_row_idx}", "values": [["AUTO_VERIFIED"]]}])
                if result["answers"] and doc_id not in existing_key_ids:
                    new_keys.append([doc_id, result["total_q"], json.dumps(result["sections"]), json.dumps(result["answers"]), linked_id, now_str])
                    existing_key_ids.add(doc_id)
            elif result["status"] == "REJECTED_MISMATCH":
                rejected_count += 1
                r[10] = ""
                ans_r[10] = ""
                pdf_updates.extend([
                    {"range": f"K{row_idx}", "values": [[""]]}, {"range": f"K{ans_row_idx}", "values": [[""]]},
                    {"range": f"U{row_idx}", "values": [["REJECTED_MISMATCH"]]}, {"range": f"U{ans_row_idx}", "values": [["REJECTED_MISMATCH"]]},
                ])
            else:
                review_count += 1
                pdf_updates.extend([{"range": f"U{row_idx}", "values": [["NEEDS_REVIEW"]]}, {"range": f"U{ans_row_idx}", "values": [["NEEDS_REVIEW"]]}])

        elif r[11] == "Yes" and cat in ("Entrance Exam", "Model Exam", "Pilot Exam", "Practice / Weekly Exam") and doc_id not in existing_key_ids and size_mb <= 25:
            ex_info = await get_exam_analysis(doc_id, r)
            if ex_info:
                emb = ex_info.get("embedded_answers") or {}
                if len(emb) >= 15:
                    new_keys.append([doc_id, max(int(k) for k in emb.keys()), json.dumps(ex_info.get("sections", [])), json.dumps(emb), doc_id, now_str])
                    existing_key_ids.add(doc_id)
                    embedded_keys_parsed += 1

    for ans_id, (ans_idx, ans_r) in by_id.items():
        if ans_r[5] != "Answer Sheet" or ans_r[10] or (float(ans_r[13] or 0) > 25):
            continue
        ans_info = await get_ans_analysis(ans_id, ans_r)
        if not ans_info or ans_info.get("is_scanned") or ans_info.get("looks_like_question_paper"):
            continue

        best_match = None
        for ex_id, (ex_idx, ex_r) in by_id.items():
            if ex_r[5] not in ("Entrance Exam", "Model Exam", "Pilot Exam", "Practice / Weekly Exam") or ex_r[10] or ex_r[11] == "Yes":
                continue
            if ex_r[4] != ans_r[4] or (float(ex_r[13] or 0) > 25):
                continue
            ex_info = await get_exam_analysis(ex_id, ex_r)
            if not ex_info:
                continue
            res = score_exam_answer_match(ex_info, ans_info, same_round_hint=(ex_r[8] == ans_r[8]))
            if res["status"] == "AUTO_VERIFIED":
                if not best_match or res["score"] > best_match[0]:
                    best_match = (res["score"], ex_id, ex_idx, res)

        if best_match:
            _, ex_id, ex_idx, res = best_match
            by_id[ex_id][1][10] = ans_id
            ans_r[10] = ex_id
            newly_discovered += 1
            pdf_updates.extend([
                {"range": f"K{ex_idx}", "values": [[ans_id]]}, {"range": f"K{ans_idx}", "values": [[ex_id]]},
                {"range": f"U{ex_idx}", "values": [["AUTO_VERIFIED"]]}, {"range": f"U{ans_idx}", "values": [["AUTO_VERIFIED"]]},
            ])
            if res["answers"] and ex_id not in existing_key_ids:
                new_keys.append([ex_id, res["total_q"], json.dumps(res["sections"]), json.dumps(res["answers"]), ans_id, now_str])
                existing_key_ids.add(ex_id)

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
        f"✔️ <b>Auto-Verified:</b> {verified_count} (+{newly_discovered} newly matched by content!)\n"
        f"❌ <b>False Links Removed:</b> {rejected_count}\n"
        f"🧐 <b>Needs Review:</b> {review_count} | 🎯 <b>Quiz Keys Parsed:</b> {len(new_keys)} ({embedded_keys_parsed} embedded)\n"
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
        await update.message.reply_text("✅ No pairs waiting for manual review!")
        return

    for ex_r, ans_r in pairs:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Confirm Match", callback_data=f"link_ok:{ex_r[0]}:{ans_r[0]}"),
            InlineKeyboardButton("❌ Unlink", callback_data=f"link_no:{ex_r[0]}:{ans_r[0]}"),
        ]])
        await update.message.reply_text(
            f"🧐 <b>Verify Link</b>\n📄 <b>Exam ({ex_r[0]}):</b> {html.escape(ex_r[1])}\n🔑 <b>Answer ({ans_r[0]}):</b> {html.escape(ans_r[1])}",
            reply_markup=kb, parse_mode="HTML",
        )


async def link_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Unauthorized", show_alert=True)
        return
    action, ex_id, ans_id = query.data.split(":", 2)
    await query.answer("Updating...")

    def _apply():
        _, pdf_sheet = get_sheets()
        updates = []
        for idx, r in enumerate(pdf_sheet.get_all_values()[1:], start=2):
            if r and r[0] in (ex_id, ans_id):
                if action == "link_ok":
                    updates.append({"range": f"U{idx}", "values": [["MANUAL_VERIFIED"]]})
                else:
                    updates.extend([{"range": f"K{idx}", "values": [[""]]}, {"range": f"U{idx}", "values": [["REJECTED_MISMATCH"]]}])
        if updates:
            pdf_sheet.batch_update(updates)

    await asyncio.to_thread(_apply)
    webapp_router.invalidate_library_cache()
    await query.edit_message_text(f"{'✅ Link confirmed!' if action == 'link_ok' else '❌ Link removed.'} ({ex_id} ↔ {ans_id})")


async def convert_office_via_apps_script(drive_file_id: str) -> str | None:
    if not CONVERTER_SCRIPT_URL:
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.post(CONVERTER_SCRIPT_URL, json={"action": "convert_drive_file", "fileId": drive_file_id, "secret": CONVERTER_SECRET})
            data = resp.json()
            if data.get("ok") and data.get("pdfFileId"):
                return data["pdfFileId"]
    except Exception as e:
        logger.warning(f"Converter error {drive_file_id}: {e}")
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
    results, folders_to_visit = [], [folder_id]
    while folders_to_visit:
        current_folder = folders_to_visit.pop(0)
        page_token = None
        while True:
            resp = drive_service.files().list(
                q=f"'{current_folder}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, size, md5Checksum, parents)",
                pageSize=1000, pageToken=page_token, supportsAllDrives=True, includeItemsFromAllDrives=True,
            ).execute()
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
        return pdf_sheet, pdf_sheet.get_all_values(), list_drive_files_recursive(get_drive_service(), DRIVE_FOLDER_ID)

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
        f_id, md5 = f["id"], f.get("md5Checksum") or f["id"]
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
                    ext_map["pdf"] = {"id": new_pdf_id, "name": office_file["name"].rsplit(".", 1)[0] + ".pdf", "size": office_file.get("size", "0"), "md5Checksum": new_pdf_id}
                    converted_count += 1

    next_num, new_rows, twin_updates = len(existing_rows), [], []
    for stem, ext_map in sorted(grouped_files.items()):
        pdf_file, office_file = ext_map.get("pdf"), ext_map.get("pptx") or ext_map.get("docx")
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
        link_updates = compute_exam_answer_links(pdf_sheet.get_all_values())
        if link_updates:
            pdf_sheet.batch_update(link_updates)
        return len(link_updates) // 2

    paired_count = await asyncio.to_thread(_write_and_link)
    webapp_router.invalidate_library_cache()

    await status_msg.edit_text(
        f"✅ <b>Google Drive Sync Complete!</b>\n\n"
        f"📥 <b>Added:</b> {len(new_rows)} | 📄 <b>Converted:</b> {converted_count}\n"
        f"🔗 <b>Candidate Pairs:</b> {paired_count} | ♻️ <b>Duplicates:</b> {skipped_duplicates} | 🚫 <b>Excluded:</b> {skipped_excluded}\n\n"
        f"👉 Run /verify_links next to verify PDF pairs &amp; parse Quiz keys!",
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
                return None
        doc_id = f"DOC-{len(rows):04d}"
        pdf_sheet.append_row([
            doc_id, doc.file_name, meta["grade"], meta["stream"], meta["subject"],
            meta["category"], meta["year"], meta["exam_tag"], meta["round_or_code"],
            meta["link_key"], "", meta["has_embedded_answer"], ext, size_mb,
            "Telegram", "", "", doc.file_id, doc.file_unique_id, post_link, "", "",
        ])
        link_updates = compute_exam_answer_links(pdf_sheet.get_all_values())
        if link_updates:
            pdf_sheet.batch_update(link_updates)
        return doc_id

    await asyncio.to_thread(_append_and_link)
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
    get_bot_username=lambda: BOT_USERNAME,
    get_all_worksheets_fn=get_all_worksheets,
    get_credentials_fn=get_credentials,
    eat_tz=EAT_TZ,
)
app.include_router(webapp_router)

ptb_app.add_handler(CommandHandler("start", start_command))
ptb_app.add_handler(CommandHandler("register", start_command))
ptb_app.add_handler(CommandHandler("library", open_library_command))
ptb_app.add_handler(CommandHandler("referral", referral_command))
ptb_app.add_handler(CommandHandler("squad", referral_command))
ptb_app.add_handler(CommandHandler("check_leads", check_leads))
ptb_app.add_handler(CommandHandler("check_billing", check_billing_command))
ptb_app.add_handler(CommandHandler("review_reports", review_reports_command))
ptb_app.add_handler(CommandHandler("stats", stats_command))
ptb_app.add_handler(CommandHandler("broadcast", broadcast_command))
ptb_app.add_handler(CommandHandler("sync_drive", sync_drive_command))
ptb_app.add_handler(CommandHandler("verify_links", verify_links_command))
ptb_app.add_handler(CommandHandler("review_links", review_links_command))
ptb_app.add_handler(CommandHandler("end_launch", end_launch_command))
ptb_app.add_handler(CommandHandler("reopen_launch", reopen_launch_command))

ptb_app.add_handler(CallbackQueryHandler(handle_student_action_callback, pattern=r"^(approve_user:|reject_user:|mark_paid:|mark_left:|approve_all_new)"))
ptb_app.add_handler(CallbackQueryHandler(handle_report_decision, pattern=r"^rpt_"))
ptb_app.add_handler(CallbackQueryHandler(broadcast_callback, pattern=r"^(bc_send:|bc_cancel:)"))
ptb_app.add_handler(CallbackQueryHandler(link_review_callback, pattern=r"^(link_ok:|link_no:)"))
ptb_app.add_handler(CallbackQueryHandler(launch_callback, pattern=r"^(launch_confirm:|launch_cancel)"))
ptb_app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.Document.ALL, auto_categorize_file))


@app.on_event("startup")
async def startup_event():
    global billing_task, BOT_USERNAME
    await ptb_app.initialize()
    await ptb_app.start()
    try:
        me = await ptb_app.bot.get_me()
        BOT_USERNAME = me.username or BOT_USERNAME
    except Exception as e:
        logger.warning(f"getMe failed: {e}")

    if WEBAPP_URL:
        try:
            await ptb_app.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="🚀 Open Qelal", web_app=WebAppInfo(url=WEBAPP_URL))
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
    return {"status": "Qelal Learning (ቀላል) Bot is active!"}
