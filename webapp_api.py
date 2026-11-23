import os
import re
import hmac
import json
import time
import uuid
import hashlib
import tempfile
import asyncio
import html
import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, quote

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, Response, FileResponse, JSONResponse
from starlette.background import BackgroundTask
from google.auth.transport.requests import Request as GoogleAuthRequest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from study_plans import STUDY_PLAN_TEMPLATES
from receipt_generator import generate_membership_pdf

logger = logging.getLogger(__name__)


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("251") and len(digits) >= 12:
        digits = digits[3:]
    elif digits.startswith("0") and len(digits) >= 10:
        digits = digits[1:]
    return digits[-9:] if len(digits) >= 9 else ""


def normalize_username(raw: str) -> str:
    u = (raw or "").strip().lstrip("@").lower()
    return u if re.fullmatch(r"[a-z0-9_]{3,}", u) else ""


def create_webapp_router(
    bot_token: str,
    admin_user_id: int,
    get_ptb_app,
    get_bot_username,
    get_all_worksheets_fn,
    get_credentials_fn,
    eat_tz,
    get_job_status_fn=None,
    trigger_sync_drive_fn=None,
    trigger_verify_links_fn=None,
):
    router = APIRouter()
    EAT_TZ = eat_tz
    session_secret = hashlib.sha256((bot_token + ":qelal_webapp_v6").encode()).digest()
    boot_ver = str(int(time.time()))
    no_cache_headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

    reg_lock = asyncio.Lock()
    lib_lock = asyncio.Lock()
    cfg_lock = asyncio.Lock()

    state = {
        "creds": None,
        "lib_cache": None,
        "lib_cache_ts": 0.0,
        "reg_cache": None,
        "reg_cache_ts": 0.0,
        "cfg_cache": None,
        "cfg_cache_ts": 0.0,
        "keys_cache": None,
        "analytics_buffer": [],
        "last_flush_ts": time.time(),
    }

    def invalidate_library_cache():
        state["lib_cache"] = None
        state["keys_cache"] = None

    def invalidate_reg_cache():
        state["reg_cache"] = None

    def invalidate_config_cache():
        state["cfg_cache"] = None

    router.invalidate_library_cache = invalidate_library_cache
    router.invalidate_reg_cache = invalidate_reg_cache
    router.invalidate_config_cache = invalidate_config_cache

    def get_drive_access_token() -> str:
        if state["creds"] is None:
            state["creds"] = get_credentials_fn()
        if not state["creds"].valid:
            state["creds"].refresh(GoogleAuthRequest())
        return state["creds"].token

    # --- AUTH & SESSION TOKENS ---
    def verify_telegram_init_data(init_data: str) -> dict | None:
        if not init_data:
            return None
        try:
            parsed = dict(parse_qsl(init_data, keep_blank_values=True))
            received_hash = parsed.pop("hash", None)
            if not received_hash:
                return None
            data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
            secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
            expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_hash, received_hash):
                return None
            if time.time() - int(parsed.get("auth_date", "0")) > 86400:
                return None
            return json.loads(parsed.get("user", "{}"))
        except Exception:
            return None

    def create_session_token(tg_id: int) -> str:
        exp = int(time.time()) + 14400
        payload = f"{tg_id}:{exp}"
        sig = hmac.new(session_secret, payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}:{sig}"

    def verify_session_token(token: str) -> int | None:
        try:
            tg_id_str, exp_str, sig = token.split(":", 2)
            if int(exp_str) < int(time.time()):
                return None
            expected = hmac.new(session_secret, f"{tg_id_str}:{exp_str}".encode(), hashlib.sha256).hexdigest()
            return int(tg_id_str) if hmac.compare_digest(expected, sig) else None
        except Exception:
            return None

    # --- CACHED LOADERS ---
    def _load_config_sync() -> dict:
        _, _, _, _, cfg_sheet, _, _, _ = get_all_worksheets_fn()
        rows = cfg_sheet.get_all_values()[1:]
        cfg = {
            "LAUNCH_MODE": "OPEN_LAUNCH",
            "MATRIC_DATE": "2027-06-25",
            "GRADE8_MINISTRY_DATE": "2027-06-15",
            "GRADE6_MINISTRY_DATE": "2027-06-10",
            "SEMESTER_DATE": "2027-01-25",
        }
        for r in rows:
            if len(r) >= 2 and r[0].strip():
                cfg[r[0].strip()] = r[1].strip()
        return cfg

    async def get_config() -> dict:
        now = time.time()
        if state["cfg_cache"] is not None and (now - state["cfg_cache_ts"] <= 300):
            return state["cfg_cache"]
        async with cfg_lock:
            now = time.time()
            if state["cfg_cache"] is None or (now - state["cfg_cache_ts"] > 300):
                state["cfg_cache"] = await asyncio.to_thread(_load_config_sync)
                state["cfg_cache_ts"] = time.time()
            return state["cfg_cache"]

    def _load_reg_and_students_sync():
        reg_sheet, _, _, _, _, _, students_sheet, reports_sheet = get_all_worksheets_fn()
        reg_rows = reg_sheet.get_all_values()[1:]
        stu_rows = students_sheet.get_all_values()[1:]
        rpt_rows = reports_sheet.get_all_values()[1:]

        by_tg = {}
        all_regs = []
        for idx, row in enumerate(reg_rows, start=2):
            r = row + [""] * (19 - len(row))
            if r[6].strip():
                ref_code = r[12].strip()
                if not ref_code:
                    ref_code = f"QELAL-{uuid.uuid4().hex[:5].upper()}"
                    try:
                        reg_sheet.update_cell(idx, 13, ref_code)
                    except Exception:
                        pass
                rec = {
                    "row_idx": idx,
                    "id": r[0],
                    "name": r[1] or "Student",
                    "grade": r[2],
                    "phone": r[3],
                    "status": r[4].strip().upper() or "NEW",
                    "timestamp": r[5],
                    "tg_id": r[6].strip(),
                    "approved_at": r[7],
                    "expires_on": r[8],
                    "months_paid": int(r[9]) if r[9].isdigit() else 0,
                    "stream": r[11] or "General",
                    "referral_code": ref_code,
                    "referred_by": r[13],
                    "referral_count": int(r[14]) if r[14].isdigit() else 0,
                    "role": r[15] or "student",
                    "format": r[16] or "Weekend Hub",
                    "lang": r[17] if r[17] in ("en", "am", "om") else "en",
                    "username": normalize_username(r[18]),
                }
                by_tg[r[6].strip()] = rec
                all_regs.append(rec)

        children_by_parent = {}
        child_by_tg = {}
        student_by_id = {}
        all_students = []
        for idx, row in enumerate(stu_rows, start=2):
            s = row + [""] * (11 - len(row))
            if not s[0]:
                continue
            stu_obj = {
                "row_idx": idx,
                "student_id": s[0],
                "student_name": s[1],
                "grade": s[2],
                "stream": s[3] or "General",
                "format": s[4] or "Weekend Hub",
                "parent_tg_id": s[5].strip(),
                "child_tg_id": s[6].strip(),
                "child_contact": s[7],
                "link_token": s[8],
                "sibling_discount": s[9] == "YES",
            }
            student_by_id[s[0]] = stu_obj
            all_students.append(stu_obj)
            if s[5].strip():
                children_by_parent.setdefault(s[5].strip(), []).append(stu_obj)
            if s[6].strip():
                child_by_tg[s[6].strip()] = stu_obj

        approved_reports_by_stu = {}
        for row in rpt_rows:
            rp = row + [""] * (10 - len(row))
            if rp[7].strip().lower() == "approved" and rp[1]:
                approved_reports_by_stu.setdefault(rp[1], []).append({
                    "report_id": rp[0],
                    "student_id": rp[1],
                    "student_name": student_by_id.get(rp[1], {}).get("student_name", ""),
                    "grade": student_by_id.get(rp[1], {}).get("grade", ""),
                    "period": rp[2],
                    "attendance": rp[3],
                    "scores_text": rp[4],
                    "improved_note": rp[5],
                    "focus_note": rp[6],
                    "published_at": rp[8],
                    "tutor_name": rp[9],
                })

        return {
            "by_tg": by_tg,
            "all_regs": all_regs,
            "all_students": all_students,
            "children_by_parent": children_by_parent,
            "child_by_tg": child_by_tg,
            "student_by_id": student_by_id,
            "reports_by_stu": approved_reports_by_stu,
        }

    async def get_reg_bundle() -> dict:
        now = time.time()
        if state["reg_cache"] is not None and (now - state["reg_cache_ts"] <= 180):
            return state["reg_cache"]
        async with reg_lock:
            now = time.time()
            if state["reg_cache"] is None or (now - state["reg_cache_ts"] > 180):
                state["reg_cache"] = await asyncio.to_thread(_load_reg_and_students_sync)
                state["reg_cache_ts"] = time.time()
            return state["reg_cache"]

    async def get_user_access(tg_id: int) -> dict:
        bundle = await get_reg_bundle()
        cfg = await get_config()
        launch_mode = cfg.get("LAUNCH_MODE", "OPEN_LAUNCH")

        rec = bundle["by_tg"].get(str(tg_id))
        linked_child = bundle["child_by_tg"].get(str(tg_id))
        children = bundle["children_by_parent"].get(str(tg_id), [])

        if tg_id == admin_user_id and not rec:
            return {
                "registered": True, "status": "APPROVED", "tier": "FULL", "launch_mode": launch_mode,
                "role": "admin", "name": "Admin", "grade": "Grade 12", "stream": "Natural",
                "phone": "", "expires_on": "", "referral_code": "QELAL-ADMIN", "referral_count": 0,
                "lang": "en", "children": [], "reports": [], "sibling_discount": False, "is_admin": True,
            }

        if not rec and not linked_child:
            return {
                "registered": False, "status": "NOT_REGISTERED", "tier": "NONE",
                "launch_mode": launch_mode, "is_admin": False,
            }

        effective_status = rec["status"] if rec else "NEW"
        effective_expires = rec["expires_on"] if rec else ""
        if linked_child and linked_child["parent_tg_id"]:
            parent_rec = bundle["by_tg"].get(linked_child["parent_tg_id"])
            if parent_rec:
                effective_status = parent_rec["status"]
                effective_expires = parent_rec["expires_on"]

        if tg_id == admin_user_id:
            effective_status = "APPROVED"

        is_full = (tg_id == admin_user_id) or (launch_mode == "OPEN_LAUNCH") or (effective_status in ("APPROVED", "EXPIRED"))
        role = rec["role"] if rec else "student"

        reports = []
        if role == "parent":
            for ch in children:
                reports.extend(bundle["reports_by_stu"].get(ch["student_id"], []))
        elif linked_child:
            reports.extend(bundle["reports_by_stu"].get(linked_child["student_id"], []))

        bot_user = get_bot_username()
        enriched_children = []
        for ch in children:
            inv = f"https://t.me/{bot_user}?start={ch['link_token']}" if (bot_user and ch["link_token"]) else ""
            enriched_children.append({**ch, "invite_url": inv, "is_linked": bool(ch["child_tg_id"])})

        primary_grade = linked_child["grade"] if linked_child else (children[0]["grade"] if children else (rec["grade"] if rec else "Grade 12"))
        primary_stream = linked_child["stream"] if linked_child else (children[0]["stream"] if children else (rec["stream"] if rec else "General"))

        return {
            "registered": True,
            "status": effective_status,
            "tier": "FULL" if is_full else "TRIAL",
            "launch_mode": launch_mode,
            "role": role,
            "name": rec["name"] if rec else linked_child["student_name"],
            "grade": primary_grade,
            "stream": primary_stream,
            "phone": rec["phone"] if rec else "",
            "expires_on": effective_expires,
            "referral_code": rec["referral_code"] if rec else "",
            "referral_count": rec["referral_count"] if rec else 0,
            "lang": rec["lang"] if rec else "en",
            "children": enriched_children,
            "sibling_discount": any(c["sibling_discount"] for c in children),
            "reports": reports,
            "is_admin": tg_id == admin_user_id,
        }

    def compute_countdown(grade: str, cfg: dict) -> dict:
        if grade == "Grade 12":
            return {"date": cfg.get("MATRIC_DATE", "2027-06-25"), "type": "matric_12"}
        if grade == "Grade 8":
            return {"date": cfg.get("GRADE8_MINISTRY_DATE", "2027-06-15"), "type": "ministry_8"}
        if grade == "Grade 6":
            return {"date": cfg.get("GRADE6_MINISTRY_DATE", "2027-06-10"), "type": "ministry_6"}
        return {"date": cfg.get("SEMESTER_DATE", "2027-01-25"), "type": "semester"}

    def _safe_float(val) -> float:
        try:
            return float(val) if val not in (None, "") else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _load_library_and_keys_sync():
        _, pdf_sheet, keys_sheet, _, _, _, _, _ = get_all_worksheets_fn()
        pdf_rows = pdf_sheet.get_all_values()[1:]
        key_rows = keys_sheet.get_all_values()[1:]

        keys_by_id = {}
        for kr in key_rows:
            k = kr + [""] * (6 - len(kr))
            if k[0]:
                try:
                    keys_by_id[k[0]] = {
                        "total_q": int(k[1]) if k[1].isdigit() else 0,
                        "sections": json.loads(k[2]) if k[2] else [],
                        "answers": json.loads(k[3]) if k[3] else {},
                    }
                except Exception:
                    pass

        items, by_id = [], {}
        for idx, row in enumerate(pdf_rows, start=2):
            if not row or not row[0]:
                continue
            r = row + [""] * (22 - len(row))
            item = {
                "row_idx": idx, "doc_id": r[0], "file_name": r[1], "grade": r[2],
                "stream": r[3], "subject": r[4], "category": r[5], "year": r[6],
                "exam_tag": r[7], "round_or_code": r[8], "link_key": r[9],
                "linked_doc_id": r[10], "has_embedded_answer": r[11], "format": r[12],
                "file_size_mb": _safe_float(r[13]), "source": r[14],
                "drive_pdf_id": r[15], "drive_original_id": r[16], "telegram_file_id": r[17],
                "post_link": r[19], "link_status": r[20],
                "is_trial": r[21].strip().upper() == "YES",
                "has_quiz": r[0] in keys_by_id,
                "quiz_total_q": keys_by_id[r[0]]["total_q"] if r[0] in keys_by_id else 0,
            }
            items.append(item)
            by_id[item["doc_id"]] = item
        return items, by_id, keys_by_id

    async def get_library_and_keys():
        now = time.time()
        if state["lib_cache"] is not None and (now - state["lib_cache_ts"] <= 300):
            return state["lib_cache"][0], state["lib_cache"][1], state["keys_cache"]
        async with lib_lock:
            now = time.time()
            if state["lib_cache"] is None or (now - state["lib_cache_ts"] > 300):
                items, by_id, keys_by_id = await asyncio.to_thread(_load_library_and_keys_sync)
                state["lib_cache"] = (items, by_id)
                state["keys_cache"] = keys_by_id
                state["lib_cache_ts"] = time.time()
            return state["lib_cache"][0], state["lib_cache"][1], state["keys_cache"]

    def get_trial_doc_ids(items: list[dict], grade: str, stream: str) -> set[str]:
        grade_matches = [
            it for it in items
            if it["category"] != "Answer Sheet"
            and (it["drive_pdf_id"] or it["telegram_file_id"])
            and (
                it["grade"] == grade
                or (grade in ("Grade 9", "Grade 10", "Grade 11", "Grade 12")
                    and it["grade"] in ("Grade 9-12", "Grade 11-12", "Grade 9-10"))
            )
        ]
        if stream in ("Natural", "Social"):
            sf = [it for it in grade_matches if it["stream"] in (stream, "General")]
            if len(sf) >= 3:
                grade_matches = sf

        explicit = [it["doc_id"] for it in grade_matches if it["is_trial"]]
        if len(explicit) >= 3:
            return set(explicit[:3])

        picked = list(explicit)
        for cat in ("Textbook", "Short Note / Lesson", "Entrance Exam", "Model Exam", "Supplementary Book", "Study Plan / Schedule"):
            for it in grade_matches:
                if it["doc_id"] not in picked and it["category"] == cat:
                    picked.append(it["doc_id"])
                    break
            if len(picked) >= 3:
                break

        for it in items:
            if len(picked) >= 3:
                break
            if it["doc_id"] not in picked and it["category"] != "Answer Sheet":
                picked.append(it["doc_id"])
        return set(picked[:3])

    async def require_session(request: Request, token: str | None = None) -> tuple[int, dict]:
        auth_token = token
        if not auth_token:
            hdr = request.headers.get("authorization", "")
            if hdr.lower().startswith("bearer "):
                auth_token = hdr[7:].strip()
        if not auth_token:
            raise HTTPException(status_code=401, detail="Missing token")
        tg_id = verify_session_token(auth_token)
        if not tg_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        access = await get_user_access(tg_id)
        if not access["registered"] and not access["is_admin"]:
            raise HTTPException(status_code=403, detail="Not registered")
        return tg_id, access

    async def require_admin(request: Request) -> tuple[int, dict]:
        hdr = request.headers.get("authorization", "")
        auth_token = hdr[7:].strip() if hdr.lower().startswith("bearer ") else ""
        if not auth_token:
            raise HTTPException(status_code=401, detail="Missing token")
        tg_id = verify_session_token(auth_token)
        if not tg_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        if tg_id != admin_user_id:
            raise HTTPException(status_code=403, detail="Admin access required")
        return tg_id, {"is_admin": True}

    def _flush_analytics_sync(rows: list[list[str]]):
        _, _, _, analytics_sheet, _, _, _, _ = get_all_worksheets_fn()
        analytics_sheet.append_rows(rows, value_input_option="USER_ENTERED")

    async def log_analytics(tg_id: int, access: dict, action: str, doc_id: str, file_name: str, subject: str, score: str = ""):
        ts = datetime.now(eat_tz).strftime("%Y-%m-%d %H:%M")
        state["analytics_buffer"].append([
            ts, str(tg_id), access.get("name", ""), access.get("grade", ""),
            action, doc_id, file_name, subject, score,
        ])
        if action == "QUIZ_SUBMIT" or len(state["analytics_buffer"]) >= 10 or (time.time() - state["last_flush_ts"] > 45):
            batch = state["analytics_buffer"][:]
            state["analytics_buffer"].clear()
            state["last_flush_ts"] = time.time()
            try:
                await asyncio.to_thread(_flush_analytics_sync, batch)
            except Exception as e:
                logger.warning(f"Analytics flush error: {e}")

    def content_disposition_header(disp_type: str, filename: str) -> str:
        ascii_name = filename.encode("ascii", "ignore").decode("ascii").strip().replace('"', "") or "document.pdf"
        return f'{disp_type}; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'

    async def get_upstream_source(item: dict):
        if item["drive_pdf_id"]:
            token = await asyncio.to_thread(get_drive_access_token)
            url = f"https://www.googleapis.com/drive/v3/files/{item['drive_pdf_id']}?alt=media&supportsAllDrives=true"
            fname = item["file_name"] if item["file_name"].lower().endswith(".pdf") else item["file_name"].rsplit(".", 1)[0] + ".pdf"
            return url, {"Authorization": f"Bearer {token}"}, fname, "application/pdf"
        if item["drive_original_id"]:
            token = await asyncio.to_thread(get_drive_access_token)
            url = f"https://www.googleapis.com/drive/v3/files/{item['drive_original_id']}?alt=media&supportsAllDrives=true"
            return url, {"Authorization": f"Bearer {token}"}, item["file_name"], "application/octet-stream"
        if item["telegram_file_id"]:
            tg_file = await get_ptb_app().bot.get_file(item["telegram_file_id"])
            file_url = tg_file.file_path if tg_file.file_path.startswith("http") else f"https://api.telegram.org/file/bot{bot_token}/{tg_file.file_path}"
            return file_url, {}, item["file_name"], "application/pdf"
        raise HTTPException(status_code=404, detail="Source missing")

    # ==========================================================================
    # AUTO-LINKING HELPERS (PARENT <-> CHILD BY USERNAME OR PHONE)
    # ==========================================================================
    def _try_auto_link_child_on_auth_sync(tg_id: int, tg_username: str):
        if not tg_username:
            return None
        reg_sheet, _, _, _, _, _, students_sheet, _ = get_all_worksheets_fn()
        stu_rows = students_sheet.get_all_values()
        matched_stu = None
        for idx, row in enumerate(stu_rows[1:], start=2):
            s = row + [""] * (11 - len(row))
            if not s[6].strip() and normalize_username(s[7]) == tg_username and s[5].strip() != str(tg_id):
                students_sheet.update_cell(idx, 7, str(tg_id))
                matched_stu = s
                break
        if not matched_stu:
            return None

        parent_tg = matched_stu[5].strip()
        reg_rows = reg_sheet.get_all_values()
        parent_rec = None
        already_reg = False
        for rr in reg_rows[1:]:
            rp = rr + [""] * (19 - len(rr))
            if rp[6].strip() == parent_tg:
                parent_rec = rp
            if rp[6].strip() == str(tg_id):
                already_reg = True

        if not already_reg:
            my_code = f"QELAL-{uuid.uuid4().hex[:5].upper()}"
            ts = datetime.now(EAT_TZ).strftime("%Y-%m-%d %H:%M")
            p_status = parent_rec[4] if parent_rec else "NEW"
            p_app = parent_rec[7] if parent_rec else ""
            p_exp = parent_rec[8] if parent_rec else ""
            p_lang = parent_rec[17] if parent_rec and parent_rec[17] in ("en", "am", "om") else "en"
            reg_sheet.append_row([
                max(1, len(reg_rows)), matched_stu[1], matched_stu[2], "", p_status, ts, str(tg_id),
                p_app, p_exp, "0", "-1", matched_stu[3], my_code, "", "0", "student", matched_stu[4], p_lang, tg_username,
            ])
        return parent_tg, matched_stu[1], matched_stu[2]

    def _sync_username_sync(tg_id: int, tg_username: str):
        if not tg_username:
            return
        reg_sheet, _, _, _, _, _, _, _ = get_all_worksheets_fn()
        for idx, row in enumerate(reg_sheet.get_all_values()[1:], start=2):
            r = row + [""] * (19 - len(row))
            if r[6].strip() == str(tg_id) and normalize_username(r[18]) != tg_username:
                reg_sheet.update_cell(idx, 19, tg_username)
                return

    # ==========================================================================
    # PUBLIC / STUDENT / PARENT ROUTES
    # ==========================================================================
    @router.get("/favicon.ico")
    async def favicon():
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0F2342"/><text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" fill="#FBBF24" font-size="34" font-weight="bold" font-family="sans-serif">ቀ</text></svg>'
        return Response(content=svg, media_type="image/svg+xml")

    @router.get("/webapp", response_class=HTMLResponse)
    async def serve_webapp():
        html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
        if not os.path.exists(html_path):
            return HTMLResponse("<h1>Missing static/index.html</h1>", status_code=500)
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('/static/styles.css"', f'/static/styles.css?v={boot_ver}"')
        content = content.replace('/static/app.js"', f'/static/app.js?v={boot_ver}"')
        return HTMLResponse(content, headers=no_cache_headers)

    @router.get("/static/{file_path:path}")
    async def serve_static_asset(file_path: str):
        static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
        full_path = os.path.abspath(os.path.join(static_dir, file_path))
        if not full_path.startswith(static_dir) or not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="Asset not found")
        return FileResponse(full_path, headers=no_cache_headers)

    @router.post("/api/auth")
    async def api_auth(request: Request):
        try:
            body = await request.json()
            user = verify_telegram_init_data(body.get("initData", ""))
            if not user:
                return {"ok": False, "status": "OUTSIDE_TELEGRAM"}

            tg_id = int(user["id"])
            tg_username = normalize_username(user.get("username", ""))
            access = await get_user_access(tg_id)

            if not access["registered"] and not access["is_admin"] and tg_username:
                linked_info = await asyncio.to_thread(_try_auto_link_child_on_auth_sync, tg_id, tg_username)
                if linked_info:
                    invalidate_reg_cache()
                    access = await get_user_access(tg_id)
                    p_tg, c_name, c_grade = linked_info
                    if p_tg:
                        try:
                            await get_ptb_app().bot.send_message(
                                chat_id=int(p_tg),
                                text=f"<b>Account Linked:</b> Your child <b>{html.escape(c_name)}</b> ({html.escape(c_grade)}) opened Qelal and was linked automatically.",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
            elif access["registered"] and tg_username:
                bundle = await get_reg_bundle()
                existing_rec = bundle["by_tg"].get(str(tg_id))
                if existing_rec and existing_rec.get("username") != tg_username:
                    await asyncio.to_thread(_sync_username_sync, tg_id, tg_username)
                    invalidate_reg_cache()

            if not access["registered"] and not access["is_admin"]:
                return {"ok": False, "status": "NOT_REGISTERED", "tg_first_name": user.get("first_name", "")}

            cfg = await get_config()
            token = create_session_token(tg_id)
            days_left = None
            if access.get("expires_on"):
                try:
                    exp = datetime.strptime(access["expires_on"], "%Y-%m-%d").date()
                    days_left = (exp - datetime.now(eat_tz).date()).days
                except ValueError:
                    pass

            return {
                "ok": True,
                "registered": True,
                "status": access["status"],
                "tier": access["tier"],
                "launch_mode": access["launch_mode"],
                "role": access["role"],
                "name": access["name"],
                "grade": access["grade"],
                "stream": access["stream"],
                "lang": access.get("lang", "en"),
                "is_admin": access["is_admin"],
                "days_left": days_left,
                "referral_code": access.get("referral_code", ""),
                "referral_count": access.get("referral_count", 0),
                "sibling_discount": access.get("sibling_discount", False),
                "children": access.get("children", []),
                "reports": access.get("reports", []),
                "countdown": compute_countdown(access["grade"], cfg),
                "bot_username": get_bot_username(),
                "token": token,
            }
        except Exception as e:
            logger.exception("Auth failed")
            return JSONResponse({"ok": False, "detail": str(e)}, status_code=500)

    @router.post("/api/register")
    async def api_register(request: Request):
        try:
            body = await request.json()
            user = verify_telegram_init_data(body.get("initData", ""))
            if not user:
                raise HTTPException(status_code=401, detail="Open inside Telegram to register")

            tg_id = int(user["id"])
            tg_username = normalize_username(user.get("username", ""))
            existing = await get_user_access(tg_id)
            if existing["registered"]:
                return {"ok": True, "already_registered": True}

            role = "parent" if body.get("role") == "parent" else "student"
            lang = body.get("lang") if body.get("lang") in ("en", "am", "om") else "en"
            full_name = (body.get("full_name") or "").strip()
            phone = (body.get("phone") or "").strip()
            prog_format = (body.get("format") or "Weekend Hub").strip()
            entered_ref = (body.get("referral_code") or "").strip().upper()
            children = body.get("children") or []

            if not full_name or not phone:
                raise HTTPException(status_code=400, detail="Name and phone are required")
            if not children:
                raise HTTPException(status_code=400, detail="At least one student/grade is required")

            my_ref_code = f"QELAL-{uuid.uuid4().hex[:5].upper()}"
            timestamp = datetime.now(eat_tz).strftime("%Y-%m-%d %H:%M")

            def _write_registration():
                reg_sheet, _, _, _, cfg_sheet, _, students_sheet, _ = get_all_worksheets_fn()
                reg_rows = reg_sheet.get_all_values()
                stu_rows = students_sheet.get_all_values()

                valid_ref_code, referrer_name = "", ""
                if entered_ref:
                    for rr in reg_rows[1:]:
                        rp = rr + [""] * (19 - len(rr))
                        if rp[12].strip().upper() == entered_ref and rp[6].strip() != str(tg_id):
                            valid_ref_code = entered_ref
                            referrer_name = rp[1]
                            break

                next_id = max(1, len(reg_rows))
                launch_mode = "OPEN_LAUNCH"
                for cr in cfg_sheet.get_all_values()[1:]:
                    if len(cr) >= 2 and cr[0].strip() == "LAUNCH_MODE":
                        launch_mode = cr[1].strip()

                if role == "student":
                    my_phone_norm = normalize_phone(phone)
                    matched_parent_row_idx = None
                    matched_parent_tg = ""
                    matched_stu_s = None

                    for s_idx, s_row in enumerate(stu_rows[1:], start=2):
                        s = s_row + [""] * (11 - len(s_row))
                        if s[6].strip() or not s[5].strip() or s[5].strip() == str(tg_id):
                            continue
                        c_phone_norm = normalize_phone(s[7])
                        c_user_norm = normalize_username(s[7])
                        if (my_phone_norm and c_phone_norm == my_phone_norm) or (tg_username and c_user_norm == tg_username):
                            matched_parent_row_idx = s_idx
                            matched_parent_tg = s[5].strip()
                            matched_stu_s = s
                            break

                    ch = children[0]
                    grade_val = ch.get("grade", "Grade 12")
                    stream_val = ch.get("stream", "General") if grade_val in ("Grade 11", "Grade 12") else "General"
                    ch_fmt = ch.get("format", prog_format)

                    if matched_parent_row_idx:
                        p_status, p_app, p_exp = "NEW", "", ""
                        for rr in reg_rows[1:]:
                            rp = rr + [""] * (19 - len(rr))
                            if rp[6].strip() == matched_parent_tg:
                                p_status = rp[4].strip().upper() or "NEW"
                                p_app = rp[7]
                                p_exp = rp[8]
                                break

                        students_sheet.update(
                            values=[[full_name, matched_stu_s[2], matched_stu_s[3], matched_stu_s[4], matched_parent_tg, str(tg_id), phone]],
                            range_name=f"B{matched_parent_row_idx}:H{matched_parent_row_idx}",
                        )
                        reg_sheet.append_row([
                            next_id, full_name, matched_stu_s[2], phone, p_status, timestamp, str(tg_id),
                            p_app, p_exp, "0", "-1", matched_stu_s[3], my_ref_code, valid_ref_code, "0",
                            "student", matched_stu_s[4], lang, tg_username,
                        ])
                        return {
                            "valid_ref": valid_ref_code, "ref_name": referrer_name, "sibling_disc": False,
                            "created_children": [{"student_name": full_name, "grade": matched_stu_s[2], "stream": matched_stu_s[3], "child_contact": phone, "link_token": "", "auto_linked": True}],
                            "launch_mode": launch_mode, "linked_parent_tg": matched_parent_tg, "linked_child_tgs": [],
                        }

                    reg_sheet.append_row([
                        next_id, full_name, grade_val, phone, "NEW", timestamp, str(tg_id),
                        "", "", "0", "-1", stream_val, my_ref_code, valid_ref_code, "0",
                        "student", ch_fmt, lang, tg_username,
                    ])
                    stu_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
                    students_sheet.append_row([
                        stu_id, full_name, grade_val, stream_val, ch_fmt,
                        "", str(tg_id), phone, "", "NO", timestamp,
                    ])
                    return {
                        "valid_ref": valid_ref_code, "ref_name": referrer_name, "sibling_disc": False,
                        "created_children": [{"student_name": full_name, "grade": grade_val, "stream": stream_val, "child_contact": phone, "link_token": "", "auto_linked": False}],
                        "launch_mode": launch_mode, "linked_parent_tg": "", "linked_child_tgs": [],
                    }

                has_sibling_discount = len(children) >= 2
                grade_val = children[0].get("grade", "Grade 12") if len(children) == 1 else f"Parent ({len(children)} kids)"
                stream_val = children[0].get("stream", "General") if len(children) == 1 else "General"

                reg_sheet.append_row([
                    next_id, full_name, grade_val, phone, "NEW", timestamp, str(tg_id),
                    "", "", "0", "-1", stream_val, my_ref_code, valid_ref_code, "0",
                    "parent", prog_format, lang, tg_username,
                ])

                stu_reg_by_phone = {}
                stu_reg_by_user = {}
                for rr in reg_rows[1:]:
                    rp = rr + [""] * (19 - len(rr))
                    r_tg = rp[6].strip()
                    if not r_tg or r_tg == str(tg_id):
                        continue
                    pn = normalize_phone(rp[3])
                    un = normalize_username(rp[18])
                    if pn:
                        stu_reg_by_phone[pn] = r_tg
                    if un:
                        stu_reg_by_user[un] = r_tg

                stu_existing_by_child_tg = {}
                for s_idx, s_row in enumerate(stu_rows[1:], start=2):
                    s = s_row + [""] * (11 - len(s_row))
                    if s[6].strip():
                        stu_existing_by_child_tg[s[6].strip()] = (s_idx, s)

                stu_rows_to_add, stu_batch_updates, created_children, linked_child_tgs = [], [], [], []
                for ch in children:
                    c_name = (ch.get("name") or full_name).strip()
                    c_grade = ch.get("grade", "Grade 12")
                    c_stream = ch.get("stream", "General") if c_grade in ("Grade 11", "Grade 12") else "General"
                    c_fmt = ch.get("format", prog_format)
                    c_contact = (ch.get("child_contact") or "").strip()

                    cpn = normalize_phone(c_contact)
                    cun = normalize_username(c_contact)
                    matched_child_tg = (stu_reg_by_phone.get(cpn) if cpn else "") or (stu_reg_by_user.get(cun) if cun else "")

                    if matched_child_tg and matched_child_tg in stu_existing_by_child_tg:
                        ex_idx, ex_s = stu_existing_by_child_tg[matched_child_tg]
                        stu_batch_updates.append({
                            "range": f"F{ex_idx}:J{ex_idx}",
                            "values": [[str(tg_id), matched_child_tg, c_contact or ex_s[7], ex_s[8], "YES" if has_sibling_discount else "NO"]],
                        })
                        linked_child_tgs.append((matched_child_tg, c_name))
                        created_children.append({
                            "student_name": c_name, "grade": c_grade, "stream": c_stream,
                            "child_contact": c_contact, "link_token": "", "auto_linked": True,
                        })
                    else:
                        stu_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
                        link_tok = "" if matched_child_tg else f"child_{uuid.uuid4().hex[:8]}"
                        if matched_child_tg:
                            linked_child_tgs.append((matched_child_tg, c_name))
                        stu_rows_to_add.append([
                            stu_id, c_name, c_grade, c_stream, c_fmt,
                            str(tg_id), matched_child_tg, c_contact, link_tok,
                            "YES" if has_sibling_discount else "NO", timestamp,
                        ])
                        created_children.append({
                            "student_name": c_name, "grade": c_grade, "stream": c_stream,
                            "child_contact": c_contact, "link_token": link_tok, "auto_linked": bool(matched_child_tg),
                        })

                if stu_batch_updates:
                    students_sheet.batch_update(stu_batch_updates)
                if stu_rows_to_add:
                    students_sheet.append_rows(stu_rows_to_add, value_input_option="USER_ENTERED")

                return {
                    "valid_ref": valid_ref_code, "ref_name": referrer_name, "sibling_disc": has_sibling_discount,
                    "created_children": created_children, "launch_mode": launch_mode,
                    "linked_parent_tg": "", "linked_child_tgs": linked_child_tgs,
                }

            res = await asyncio.to_thread(_write_registration)
            invalidate_reg_cache()

            bot = get_ptb_app().bot
            bot_user = get_bot_username()

            if res["linked_parent_tg"]:
                try:
                    await bot.send_message(
                        chat_id=int(res["linked_parent_tg"]),
                        text=f"<b>Account Linked:</b> Your child <b>{html.escape(full_name)}</b> registered and was linked to your Parent Dashboard.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

            for c_tg, c_nm in res["linked_child_tgs"]:
                try:
                    await bot.send_message(
                        chat_id=int(c_tg),
                        text=f"<b>Parent Linked:</b> <b>{html.escape(full_name)}</b> connected your Qelal Learning student account.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

            child_lines = []
            for ch in res["created_children"]:
                inv = f"https://t.me/{bot_user}?start={ch['link_token']}" if (bot_user and ch["link_token"]) else ""
                c_txt = f"• <b>{html.escape(ch['student_name'])}</b> — {html.escape(ch['grade'])}"
                if ch["stream"] != "General":
                    c_txt += f" ({ch['stream']})"
                if ch["auto_linked"]:
                    c_txt += " <b>[Auto-Linked]</b>"
                if ch["child_contact"]:
                    c_txt += f"\n  Contact: <code>{html.escape(ch['child_contact'])}</code>"
                if inv:
                    c_txt += f"\n  Invite Link: {inv}"
                child_lines.append(c_txt)

            admin_msg = (
                f"<b>NEW {role.upper()} REGISTRATION</b>\n\n"
                f"<b>Name:</b> {html.escape(full_name)}\n"
                f"<b>Phone:</b> <code>{html.escape(phone)}</code>\n"
                f"<b>TG ID:</b> <code>{tg_id}</code> | <b>Code:</b> <code>{my_ref_code}</code>\n"
                f"{'<b>SIBLING DISCOUNT ELIGIBLE (2+ Kids)</b>\n' if res['sibling_disc'] else ''}"
                f"{f'<b>Referred by:</b> {html.escape(res['ref_name'])} (<code>{res['valid_ref']}</code>)\n' if res['valid_ref'] else ''}\n"
                f"<b>Students:</b>\n" + "\n".join(child_lines)
            )
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("Approve (Start 30d)", callback_data=f"approve_user:{tg_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_user:{tg_id}"),
            ]])
            try:
                await bot.send_message(chat_id=admin_user_id, text=admin_msg, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Failed notifying admin: {e}")

            return {"ok": True, "referral_code": my_ref_code, "sibling_discount": res["sibling_disc"], "launch_mode": res["launch_mode"]}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Registration failed")
            return JSONResponse({"ok": False, "detail": str(e)}, status_code=500)

    @router.post("/api/set-lang")
    async def api_set_lang(request: Request):
        tg_id, _ = await require_session(request)
        body = await request.json()
        lang = body.get("lang") if body.get("lang") in ("en", "am", "om") else "en"

        def _update():
            reg_sheet, _, _, _, _, _, _, _ = get_all_worksheets_fn()
            for idx, r in enumerate(reg_sheet.get_all_values()[1:], start=2):
                if len(r) >= 7 and r[6].strip() == str(tg_id):
                    reg_sheet.update_cell(idx, 18, lang)
                    return

        await asyncio.to_thread(_update)
        invalidate_reg_cache()
        return {"ok": True, "lang": lang}

    @router.get("/api/library")
    async def api_library(request: Request, refresh: bool = False):
        _, access = await require_session(request)
        if refresh and access.get("is_admin"):
            invalidate_library_cache()
        items, _, _ = await get_library_and_keys()

        trial_ids = set()
        if access["tier"] == "TRIAL":
            trial_ids = get_trial_doc_ids(items, access["grade"], access["stream"])

        public_items = []
        for it in items:
            is_unlocked = (access["tier"] == "FULL") or (it["doc_id"] in trial_ids)
            linked_id = "" if it["link_status"] == "REJECTED_MISMATCH" else it["linked_doc_id"]
            public_items.append({
                "doc_id": it["doc_id"],
                "file_name": it["file_name"],
                "grade": it["grade"],
                "stream": it["stream"],
                "subject": it["subject"],
                "category": it["category"],
                "year": it["year"],
                "round_or_code": it["round_or_code"],
                "linked_doc_id": linked_id if (access["tier"] == "FULL" or linked_id in trial_ids) else "",
                "link_status": it["link_status"],
                "has_embedded_answer": it["has_embedded_answer"],
                "format": it["format"],
                "file_size_mb": it["file_size_mb"],
                "has_pdf": bool(it["drive_pdf_id"] or (it["telegram_file_id"] and it["file_name"].lower().endswith(".pdf"))),
                "has_quiz": it["has_quiz"],
                "quiz_total_q": it["quiz_total_q"],
                "locked": not is_unlocked,
                "is_trial": it["is_trial"],
                "is_trial_pick": it["doc_id"] in trial_ids,
            })
        return {"ok": True, "tier": access["tier"], "launch_mode": access["launch_mode"], "items": public_items}

    @router.api_route("/api/file/{doc_id}/stream", methods=["GET", "HEAD"])
    async def api_stream_file(doc_id: str, request: Request, token: str | None = None):
        tg_id, access = await require_session(request, token=token)
        items, by_id, _ = await get_library_and_keys()
        item = by_id.get(doc_id)
        if not item:
            raise HTTPException(status_code=404, detail="Document not found")

        if access["tier"] == "TRIAL":
            trial_ids = get_trial_doc_ids(items, access["grade"], access["stream"])
            if doc_id not in trial_ids:
                raise HTTPException(status_code=403, detail="Locked in Trial Mode")

        url, auth_headers, fname, mime_type = await get_upstream_source(item)

        if request.method == "HEAD":
            return Response(status_code=200, headers={"Accept-Ranges": "bytes", "Content-Type": mime_type})

        range_hdr = request.headers.get("range", "")
        if not range_hdr or range_hdr.startswith("bytes=0-"):
            await log_analytics(tg_id, access, "VIEW", doc_id, item["file_name"], item["subject"])

        upstream_headers = dict(auth_headers)
        if range_hdr:
            upstream_headers["Range"] = range_hdr

        client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        req = client.build_request("GET", url, headers=upstream_headers)
        upstream_resp = await client.send(req, stream=True)
        if upstream_resp.status_code >= 400:
            err_preview = (await upstream_resp.aread()).decode("utf-8", "ignore")[:250]
            logger.error(f"Upstream stream error ({upstream_resp.status_code}) for {doc_id}: {err_preview}")
            await upstream_resp.aclose()
            await client.aclose()
            raise HTTPException(status_code=upstream_resp.status_code, detail="Storage error")

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": content_disposition_header("inline", fname),
            "Cache-Control": "private, max-age=86400",
        }
        for h in ("content-length", "content-range"):
            if h in upstream_resp.headers:
                resp_headers[h.title()] = upstream_resp.headers[h]

        async def close_upstream():
            await upstream_resp.aclose()
            await client.aclose()

        return StreamingResponse(
            upstream_resp.aiter_bytes(chunk_size=65536),
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            media_type=mime_type,
            background=BackgroundTask(close_upstream),
        )

    @router.post("/api/file/{doc_id}/send")
    async def api_send_offline_telegram(doc_id: str, request: Request):
        tg_id, access = await require_session(request)
        items, by_id, _ = await get_library_and_keys()
        item = by_id.get(doc_id)
        if not item:
            raise HTTPException(status_code=404, detail="Document not found")

        if access["tier"] == "TRIAL":
            trial_ids = get_trial_doc_ids(items, access["grade"], access["stream"])
            if doc_id not in trial_ids:
                raise HTTPException(status_code=403, detail="Locked in Trial Mode")

        bot = get_ptb_app().bot
        caption = (
            f"<b>{html.escape(item['file_name'])}</b>\n"
            f"{item['grade']} · {item['subject']} · {item['category']}\n"
            f"<i>Protected for offline reading inside Telegram only (forwarding and local saving disabled).</i>"
        )

        if item["telegram_file_id"]:
            await bot.send_document(
                chat_id=tg_id, document=item["telegram_file_id"],
                caption=caption, protect_content=True, parse_mode="HTML",
            )
            await log_analytics(tg_id, access, "SEND_CHAT", doc_id, item["file_name"], item["subject"])
            return {"ok": True, "cached": True}

        if item["file_size_mb"] > 48:
            return {"ok": False, "too_large": True, "message": "This book exceeds Telegram's 48 MB bot send limit. Read it directly in the in-app viewer."}

        url, auth_headers, fname, _ = await get_upstream_source(item)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                async with client.stream("GET", url, headers=auth_headers) as r:
                    r.raise_for_status()
                    with open(tmp_path, "wb") as f:
                        async for chunk in r.aiter_bytes(chunk_size=65536):
                            f.write(chunk)

            with open(tmp_path, "rb") as f:
                sent_msg = await bot.send_document(
                    chat_id=tg_id, document=f, filename=fname,
                    caption=caption, protect_content=True, parse_mode="HTML",
                )

            if sent_msg.document and not item["telegram_file_id"]:
                new_tg_id = sent_msg.document.file_id
                item["telegram_file_id"] = new_tg_id

                def _save_tg_id():
                    _, pdf_sheet, _, _, _, _, _, _ = get_all_worksheets_fn()
                    pdf_sheet.update_cell(item["row_idx"], 18, new_tg_id)

                await asyncio.to_thread(_save_tg_id)

            await log_analytics(tg_id, access, "SEND_CHAT", doc_id, item["file_name"], item["subject"])
            return {"ok": True, "cached": False}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    # --- QUIZ ME ENDPOINTS ---
    @router.get("/api/quiz/{doc_id}")
    async def api_get_quiz_meta(doc_id: str, request: Request):
        _, access = await require_session(request)
        _, by_id, keys_by_id = await get_library_and_keys()
        item = by_id.get(doc_id)
        key_data = keys_by_id.get(doc_id)
        if not item or not key_data:
            raise HTTPException(status_code=404, detail="Quiz key not available")

        total_q = key_data["total_q"]
        trial_limited = access["tier"] == "TRIAL"
        unlocked_q = min(10, total_q) if trial_limited else total_q
        return {
            "ok": True, "doc_id": doc_id, "file_name": item["file_name"],
            "subject": item["subject"], "year": item["year"],
            "total_q": total_q, "unlocked_q": unlocked_q,
            "trial_limited": trial_limited, "sections": key_data["sections"],
        }

    @router.post("/api/quiz/{doc_id}/submit")
    async def api_submit_quiz(doc_id: str, request: Request):
        tg_id, access = await require_session(request)
        _, by_id, keys_by_id = await get_library_and_keys()
        item = by_id.get(doc_id)
        key_data = keys_by_id.get(doc_id)
        if not item or not key_data:
            raise HTTPException(status_code=404, detail="Quiz not found")

        body = await request.json()
        user_answers = body.get("answers", {})
        answers_map = key_data["answers"]
        trial_limited = access["tier"] == "TRIAL"
        max_q = min(10, key_data["total_q"]) if trial_limited else key_data["total_q"]

        score, graded, breakdown = 0, 0, []
        for q_num in range(1, max_q + 1):
            q_str = str(q_num)
            correct = answers_map.get(q_str)
            if not correct:
                continue
            graded += 1
            yours = str(user_answers.get(q_str, "")).upper().strip()
            is_right = yours == correct
            if is_right:
                score += 1
            breakdown.append({"q": q_num, "yours": yours or "-", "correct": correct, "ok": is_right})

        pct = round((score / graded) * 100, 1) if graded else 0.0
        await log_analytics(tg_id, access, "QUIZ_SUBMIT", doc_id, item["file_name"], item["subject"], f"{score}/{graded} ({pct}%)")
        return {"ok": True, "score": score, "total_graded": graded, "percentage": pct, "trial_limited": trial_limited, "breakdown": breakdown}

    # --- STUDY PLANS & PROGRESS ---
    @router.get("/api/study-plans")
    async def api_study_plans(request: Request):
        _, access = await require_session(request)
        trial_limited = access["tier"] == "TRIAL"
        plans = []
        for p in STUDY_PLAN_TEMPLATES:
            tasks = [{"id": t["id"], "label": t["label"], "locked": trial_limited and idx >= 3} for idx, t in enumerate(p["tasks"])]
            plans.append({
                "id": p["id"], "title": p["title"], "stream": p["stream"],
                "grade": p["grade"], "description": p["description"],
                "trial_limited": trial_limited, "tasks": tasks,
            })
        return {"ok": True, "plans": plans, "trial_limited": trial_limited}

    @router.get("/api/progress")
    async def api_get_progress(request: Request):
        tg_id, _ = await require_session(request)

        def _load():
            _, _, _, _, _, prog_sheet, _, _ = get_all_worksheets_fn()
            for row in prog_sheet.get_all_values()[1:]:
                r = row + [""] * (6 - len(row))
                if r[0].strip() == str(tg_id):
                    return {
                        "bookmarks": json.loads(r[1]) if r[1] else [],
                        "last_read": json.loads(r[2]) if r[2] else {},
                        "plan_progress": json.loads(r[3]) if r[3] else {},
                        "custom_plan": json.loads(r[4]) if r[4] else [],
                    }
            return {"bookmarks": [], "last_read": {}, "plan_progress": {}, "custom_plan": []}

        return {"ok": True, **(await asyncio.to_thread(_load))}

    @router.post("/api/progress")
    async def api_save_progress(request: Request):
        tg_id, _ = await require_session(request)
        body = await request.json()
        now_str = datetime.now(eat_tz).strftime("%Y-%m-%d %H:%M")

        def _save():
            _, _, _, _, _, prog_sheet, _, _ = get_all_worksheets_fn()
            rows = prog_sheet.get_all_values()
            new_row = [
                str(tg_id), json.dumps(body.get("bookmarks", [])),
                json.dumps(body.get("last_read", {})), json.dumps(body.get("plan_progress", {})),
                json.dumps(body.get("custom_plan", [])), now_str,
            ]
            for idx, row in enumerate(rows[1:], start=2):
                if row and row[0].strip() == str(tg_id):
                    prog_sheet.update(values=[new_row], range_name=f"A{idx}:F{idx}")
                    return
            prog_sheet.append_row(new_row)

        await asyncio.to_thread(_save)
        return {"ok": True}

    @router.post("/api/request-material")
    async def api_request_material(request: Request):
        tg_id, access = await require_session(request)
        body = await request.json()
        subject = (body.get("subject") or "").strip()
        details = (body.get("details") or "").strip()
        if not details:
            raise HTTPException(status_code=400, detail="Missing details")

        await get_ptb_app().bot.send_message(
            chat_id=admin_user_id,
            text=(
                f"<b>MATERIAL REQUEST ({access.get('role','student').upper()})</b>\n\n"
                f"<b>Name:</b> {html.escape(access.get('name', 'Student'))} ({html.escape(access.get('grade', ''))})\n"
                f"<b>Phone:</b> <code>{html.escape(access.get('phone', ''))}</code> | <b>TG ID:</b> <code>{tg_id}</code>\n"
                f"<b>Subject:</b> {html.escape(subject or 'General')}\n"
                f"<b>Request:</b> {html.escape(details)}"
            ),
            parse_mode="HTML",
        )
        return {"ok": True}

    # --- LIVE PARENT VISUAL ANALYTICS ---
    @router.get("/api/parent/analytics")
    async def api_parent_analytics(request: Request):
        tg_id, access = await require_session(request)
        bundle = await get_reg_bundle()
        _, by_id, _ = await get_library_and_keys()

        children = bundle["children_by_parent"].get(str(tg_id), [])
        if not children and access.get("role") != "parent":
            return {"ok": True, "children_analytics": []}

        def _load_raw():
            _, _, _, analytics_sheet, _, prog_sheet, _, _ = get_all_worksheets_fn()
            return analytics_sheet.get_all_values()[1:], prog_sheet.get_all_values()[1:]

        ana_sheet_rows, prog_rows = await asyncio.to_thread(_load_raw)
        all_ana_rows = ana_sheet_rows + list(state["analytics_buffer"])

        prog_by_tg = {}
        for pr in prog_rows:
            p = pr + [""] * (6 - len(pr))
            if p[0].strip():
                try:
                    prog_by_tg[p[0].strip()] = {
                        "bookmarks": json.loads(p[1]) if p[1] else [],
                        "last_read": json.loads(p[2]) if p[2] else {},
                        "plan_progress": json.loads(p[3]) if p[3] else {},
                        "custom_plan": json.loads(p[4]) if p[4] else [],
                    }
                except Exception:
                    pass

        today = datetime.now(eat_tz).date()
        last_7_days = [(today - timedelta(days=offset)).isoformat() for offset in range(6, -1, -1)]
        bot_user = get_bot_username()

        results = []
        for ch in children:
            target_tg = ch["child_tg_id"] or (str(tg_id) if len(children) == 1 else "")
            is_shared_phone = not bool(ch["child_tg_id"])
            inv_url = f"https://t.me/{bot_user}?start={ch['link_token']}" if (bot_user and ch["link_token"]) else ""

            child_events = [r for r in all_ana_rows if len(r) >= 8 and target_tg and str(r[1]).strip() == target_tg]
            child_prog = prog_by_tg.get(target_tg, {"bookmarks": [], "last_read": {}, "plan_progress": {}, "custom_plan": []})

            unique_docs_viewed, total_views, offline_saved = set(), 0, 0
            quiz_trend, subj_map = [], {}
            daily_counts = {d: 0 for d in last_7_days}

            for ev in child_events:
                e = ev + [""] * (9 - len(ev))
                ts_str, _, _, _, action, doc_id, fname, subject, score_str = e[:9]
                day_str = ts_str[:10]
                if day_str in daily_counts:
                    daily_counts[day_str] += 1

                subj = subject or "General"
                subj_map.setdefault(subj, {"subject": subj, "views": 0, "quizzes": 0, "pct_sum": 0.0})

                if action == "VIEW":
                    total_views += 1
                    unique_docs_viewed.add(doc_id)
                    subj_map[subj]["views"] += 1
                elif action == "SEND_CHAT":
                    offline_saved += 1
                elif action == "QUIZ_SUBMIT":
                    m_pct = re.search(r"\((\d+(?:\.\d+)?)%\)", score_str)
                    pct = float(m_pct.group(1)) if m_pct else 0.0
                    quiz_trend.append({
                        "date": ts_str,
                        "label": fname[:26],
                        "subject": subj,
                        "score_text": score_str,
                        "pct": pct,
                    })
                    subj_map[subj]["quizzes"] += 1
                    subj_map[subj]["pct_sum"] += pct

            avg_quiz_pct = round(sum(q["pct"] for q in quiz_trend) / len(quiz_trend), 1) if quiz_trend else None

            subject_stats = [
                {
                    "subject": s["subject"],
                    "views": s["views"],
                    "quizzes": s["quizzes"],
                    "avg_pct": round(s["pct_sum"] / s["quizzes"], 1) if s["quizzes"] else None,
                }
                for s in subj_map.values()
            ]
            subject_stats.sort(key=lambda x: (x["views"] + x["quizzes"] * 2), reverse=True)

            plan_prog = child_prog.get("plan_progress", {})
            custom_plan = child_prog.get("custom_plan", [])
            plan_done, plan_total = 0, 0
            for tpl in STUDY_PLAN_TEMPLATES:
                tpl_done = sum(1 for tk in tpl["tasks"] if plan_prog.get(tk["id"]))
                if tpl_done > 0:
                    plan_done += tpl_done
                    plan_total += len(tpl["tasks"])
            if custom_plan:
                plan_done += sum(1 for t in custom_plan if t.get("done"))
                plan_total += len(custom_plan)
            if plan_total == 0:
                plan_total = 20
            plan_pct = round((plan_done / plan_total) * 100)

            recent_reads = []
            for did, info in sorted(child_prog.get("last_read", {}).items(), key=lambda x: x[1].get("ts", 0), reverse=True)[:5]:
                doc_meta = by_id.get(did)
                if doc_meta:
                    recent_reads.append({
                        "doc_id": did,
                        "file_name": doc_meta["file_name"],
                        "subject": doc_meta["subject"],
                        "page": info.get("page", 1),
                    })

            bookmarked_docs = []
            for did in child_prog.get("bookmarks", [])[:8]:
                doc_meta = by_id.get(did)
                if doc_meta:
                    bookmarked_docs.append({
                        "doc_id": did,
                        "file_name": doc_meta["file_name"],
                        "subject": doc_meta["subject"],
                        "category": doc_meta["category"],
                    })

            daily_7d = [
                {"day": datetime.strptime(d_iso, "%Y-%m-%d").strftime("%a"), "date": d_iso, "count": daily_counts[d_iso]}
                for d_iso in last_7_days
            ]

            results.append({
                "student_id": ch["student_id"],
                "student_name": ch["student_name"],
                "grade": ch["grade"],
                "stream": ch["stream"],
                "format": ch["format"],
                "is_linked": bool(ch["child_tg_id"]),
                "is_shared_phone": is_shared_phone,
                "invite_url": inv_url,
                "kpis": {
                    "pdfs_opened": len(unique_docs_viewed),
                    "total_views": total_views,
                    "offline_saved": offline_saved,
                    "quizzes_taken": len(quiz_trend),
                    "avg_quiz_pct": avg_quiz_pct,
                    "bookmarks_count": len(child_prog.get("bookmarks", [])),
                    "plan_done": plan_done,
                    "plan_total": plan_total,
                    "plan_pct": plan_pct,
                },
                "quiz_trend": quiz_trend[-10:],
                "subject_stats": subject_stats[:6],
                "daily_7d": daily_7d,
                "recent_reads": recent_reads,
                "bookmarked_docs": bookmarked_docs,
            })

        return {"ok": True, "children_analytics": results}

    # ==========================================================================
    # ADMIN CONSOLE ROUTES
    # ==========================================================================
    @router.get("/api/admin/overview")
    async def api_admin_overview(request: Request, refresh: bool = False):
        await require_admin(request)
        if refresh:
            invalidate_library_cache()
            invalidate_reg_cache()
            invalidate_config_cache()
        bundle = await get_reg_bundle()
        cfg = await get_config()
        items, by_id, keys_by_id = await get_library_and_keys()
        today = datetime.now(EAT_TZ).date()

        regs_out = []
        counts = {"APPROVED": 0, "NEW": 0, "EXPIRED": 0, "LEFT": 0, "REJECTED": 0}
        total_refs = 0
        for rec in bundle["all_regs"]:
            st = rec["status"]
            counts[st] = counts.get(st, 0) + 1
            total_refs += rec["referral_count"]
            d_left = None
            if rec["expires_on"]:
                try:
                    d_left = (datetime.strptime(rec["expires_on"], "%Y-%m-%d").date() - today).days
                except ValueError:
                    pass
            kids = bundle["children_by_parent"].get(rec["tg_id"], [])
            regs_out.append({
                "id": rec["id"],
                "tg_id": rec["tg_id"],
                "name": rec["name"],
                "grade": rec["grade"],
                "stream": rec["stream"],
                "phone": rec["phone"],
                "status": st,
                "role": rec["role"],
                "format": rec["format"],
                "expires_on": rec["expires_on"],
                "days_left": d_left,
                "months_paid": rec["months_paid"],
                "referral_code": rec["referral_code"],
                "referral_count": rec["referral_count"],
                "sibling_discount": any(k["sibling_discount"] for k in kids),
                "children": [
                    {"name": k["student_name"], "grade": k["grade"], "contact": k["child_contact"], "linked": bool(k["child_tg_id"])}
                    for k in kids
                ],
            })

        verified_links = 0
        needs_review = 0
        rejected_links = 0
        unverified_links = 0
        trial_picks = 0
        pdfs_out = []

        for it in items:
            lst = it["link_status"] or "UNVERIFIED"
            if lst in ("AUTO_VERIFIED", "MANUAL_VERIFIED"):
                verified_links += 1
            elif lst == "NEEDS_REVIEW":
                needs_review += 1
            elif lst == "REJECTED_MISMATCH":
                rejected_links += 1
            else:
                unverified_links += 1
            if it["is_trial"]:
                trial_picks += 1

            linked_id = it["linked_doc_id"]
            pdfs_out.append({
                "doc_id": it["doc_id"],
                "file_name": it["file_name"],
                "grade": it["grade"],
                "stream": it["stream"],
                "subject": it["subject"],
                "category": it["category"],
                "year": it["year"],
                "file_size_mb": it["file_size_mb"],
                "source": it["source"],
                "link_status": lst,
                "linked_doc_id": linked_id,
                "linked_file_name": by_id[linked_id]["file_name"] if linked_id and linked_id in by_id else "",
                "has_quiz": it["has_quiz"],
                "quiz_total_q": it["quiz_total_q"],
                "is_trial": it["is_trial"],
                "has_pdf": bool(it["drive_pdf_id"] or it["telegram_file_id"]),
            })

        jobs = get_job_status_fn() if get_job_status_fn else {"sync": {"running": False}, "verify": {"running": False}}

        return {
            "ok": True,
            "summary": {
                **counts,
                "total_students": len(bundle["all_students"]),
                "total_referrals": total_refs,
                "total_pdfs": len(items),
                "verified_links": verified_links,
                "needs_review": needs_review,
                "rejected_links": rejected_links,
                "unverified_links": unverified_links,
                "trial_picks": trial_picks,
                "quiz_keys": len(keys_by_id),
            },
            "jobs": jobs,
            "config": cfg,
            "registrations": regs_out,
            "students": bundle["all_students"],
            "pdfs": pdfs_out,
        }

    @router.get("/api/admin/job-status")
    async def api_admin_job_status(request: Request):
        await require_admin(request)
        jobs = get_job_status_fn() if get_job_status_fn else {"sync": {"running": False}, "verify": {"running": False}}
        return {"ok": True, "jobs": jobs}

    @router.post("/api/admin/sync-drive")
    async def api_admin_sync_drive(request: Request):
        await require_admin(request)
        if not trigger_sync_drive_fn:
            raise HTTPException(status_code=501, detail="Drive sync trigger is not configured")
        res = trigger_sync_drive_fn()
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("detail", "Could not start Drive sync"))
        jobs = get_job_status_fn() if get_job_status_fn else {}
        return {**res, "jobs": jobs}

    @router.post("/api/admin/verify-links")
    async def api_admin_verify_links(request: Request):
        await require_admin(request)
        if not trigger_verify_links_fn:
            raise HTTPException(status_code=501, detail="Verify links trigger is not configured")
        try:
            body = await request.json()
        except Exception:
            body = {}
        force = bool(body.get("force", False))
        res = trigger_verify_links_fn(force=force)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("detail", "Could not start verification"))
        jobs = get_job_status_fn() if get_job_status_fn else {}
        return {**res, "jobs": jobs}

    @router.post("/api/admin/link-action")
    async def api_admin_link_action(request: Request):
        await require_admin(request)
        body = await request.json()
        doc_id = (body.get("doc_id") or "").strip()
        action = (body.get("action") or "").strip()
        if not doc_id or action not in ("confirm", "unlink"):
            raise HTTPException(status_code=400, detail="Invalid link action")

        _, by_id, _ = await get_library_and_keys()
        item = by_id.get(doc_id)
        if not item:
            raise HTTPException(status_code=404, detail="Document not found")

        target_ids = {doc_id}
        if item["linked_doc_id"] and item["linked_doc_id"] in by_id:
            target_ids.add(item["linked_doc_id"])

        def _apply():
            _, pdf_sheet, _, _, _, _, _, _ = get_all_worksheets_fn()
            updates = []
            for idx, r in enumerate(pdf_sheet.get_all_values()[1:], start=2):
                if r and r[0] in target_ids:
                    if action == "confirm":
                        updates.append({"range": f"U{idx}", "values": [["MANUAL_VERIFIED"]]})
                    else:
                        updates.extend([
                            {"range": f"K{idx}", "values": [[""]]},
                            {"range": f"U{idx}", "values": [["REJECTED_MISMATCH"]]},
                        ])
            if updates:
                pdf_sheet.batch_update(updates)

        await asyncio.to_thread(_apply)
        invalidate_library_cache()
        return {"ok": True}

    @router.post("/api/admin/student-action")
    async def api_admin_student_action(request: Request):
        await require_admin(request)
        body = await request.json()
        tg_id_str = str(body.get("tg_id", "")).strip()
        action = body.get("action", "")
        if not tg_id_str or action not in ("approve", "mark_paid", "mark_left", "reject"):
            raise HTTPException(status_code=400, detail="Invalid action")

        today = datetime.now(EAT_TZ).date()

        def _apply():
            reg_sheet, _, _, _, _, _, _, _ = get_all_worksheets_fn()
            rows = reg_sheet.get_all_values()
            for idx, row in enumerate(rows[1:], start=2):
                r = row + [""] * (19 - len(row))
                if r[6].strip() == tg_id_str:
                    if action in ("approve", "mark_paid"):
                        is_renewal = action == "mark_paid"
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
                                r[15] or "student", r[16] or "Weekend Hub", r[17] or "en", r[18],
                            ]],
                            range_name=f"E{idx}:S{idx}",
                        )
                        credit_info = None
                        referred_by = r[13].strip().upper()
                        if prev_months == 0 and referred_by:
                            for r_idx, r_row in enumerate(rows[1:], start=2):
                                rr = r_row + [""] * (19 - len(r_row))
                                if rr[12].strip().upper() == referred_by and rr[6].strip() != tg_id_str:
                                    nc = (int(rr[14]) if rr[14].isdigit() else 0) + 1
                                    reg_sheet.update_cell(r_idx, 15, str(nc))
                                    credit_info = (int(rr[6].strip()), rr[1], referred_by, nc, r[1])
                                    break
                        return {"row": r, "ref_code": ref_code, "months": new_months, "exp": exp_str, "is_renewal": is_renewal, "credit": credit_info}

                    new_status = "LEFT" if action == "mark_left" else "REJECTED"
                    reg_sheet.update_cell(idx, 5, new_status)
                    return {"row": r, "new_status": new_status}
            return None

        res = await asyncio.to_thread(_apply)
        invalidate_reg_cache()
        if not res:
            raise HTTPException(status_code=404, detail="Account not found")

        bot = get_ptb_app().bot
        r = res["row"]
        if action in ("approve", "mark_paid"):
            try:
                grade_str = f"{r[2]} ({r[11]})" if r[11] and r[11] != "General" else r[2]
                pdf_buf = generate_membership_pdf(
                    student_id=r[0], name=r[1], grade=grade_str, phone=r[3],
                    tg_id=tg_id_str, months_paid=res["months"], approved_at=today.isoformat(),
                    expires_on=res["exp"], referral_code=res["ref_code"], is_renewal=res["is_renewal"],
                )
                webapp_base = os.getenv("WEBAPP_URL") or os.getenv("RENDER_EXTERNAL_URL") or ""
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("Open Qelal Hub", web_app=WebAppInfo(url=f"{webapp_base.rstrip('/')}/webapp"))]]) if webapp_base else None
                await bot.send_document(
                    chat_id=int(tg_id_str),
                    document=pdf_buf,
                    filename=f"Qelal_Pass_{r[1].replace(' ', '_')}_M{res['months']}.pdf",
                    caption=f"<b>{'Monthly Renewal Confirmed' if res['is_renewal'] else 'Registration Approved'}</b>\nValid until <b>{res['exp']}</b>.",
                    reply_markup=kb,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Pass PDF send failed: {e}")
            if res["credit"]:
                c_tg, _, c_code, c_cnt, f_name = res["credit"]
                try:
                    await bot.send_message(
                        chat_id=c_tg,
                        text=f"<b>Referral Credited:</b> {html.escape(f_name)} was approved using <code>{c_code}</code>. Total verified referrals: <b>{c_cnt}</b>.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        elif action == "mark_left":
            try:
                await bot.send_message(chat_id=int(tg_id_str), text="Your monthly tutoring subscription has ended. Your account is now in 3-PDF Trial mode until renewed.")
            except Exception:
                pass

        return {"ok": True}

    @router.post("/api/admin/publish-report")
    async def api_admin_publish_report(request: Request):
        await require_admin(request)
        body = await request.json()
        student_id = (body.get("student_id") or "").strip()
        period = (body.get("period") or "").strip()
        attendance = (body.get("attendance") or "").strip()
        scores_text = (body.get("scores_text") or "").strip()
        improved_note = (body.get("improved_note") or "").strip()
        focus_note = (body.get("focus_note") or "").strip()
        tutor_name = (body.get("tutor_name") or "Qelal Coordinator").strip()

        if not student_id or not period or not scores_text:
            raise HTTPException(status_code=400, detail="Student, Period, and Scores are required")

        bundle = await get_reg_bundle()
        stu = bundle["student_by_id"].get(student_id)
        if not stu:
            raise HTTPException(status_code=404, detail="Student not found")

        now_str = datetime.now(EAT_TZ).strftime("%Y-%m-%d %H:%M")
        rpt_id = f"RPT-{uuid.uuid4().hex[:5].upper()}"

        def _save_report():
            _, _, _, _, _, _, _, reports_sheet = get_all_worksheets_fn()
            reports_sheet.append_row([
                rpt_id, student_id, period, attendance, scores_text,
                improved_note, focus_note, "Approved", now_str, tutor_name,
            ])

        await asyncio.to_thread(_save_report)
        invalidate_reg_cache()

        target_tg = stu["parent_tg_id"] or stu["child_tg_id"]
        if target_tg:
            try:
                await get_ptb_app().bot.send_message(
                    chat_id=int(target_tg),
                    text=(
                        f"<b>QELAL BI-WEEKLY PROGRESS REPORT</b>\n\n"
                        f"<b>Student:</b> {html.escape(stu['student_name'])} ({html.escape(stu['grade'])})\n"
                        f"<b>Period:</b> {html.escape(period)}\n"
                        f"<b>Attendance:</b> {html.escape(attendance)}\n"
                        f"<b>Scores:</b> {html.escape(scores_text)}\n"
                        f"<b>Improved:</b> {html.escape(improved_note)}\n"
                        f"<b>Next Focus:</b> {html.escape(focus_note)}"
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Could not push report to {target_tg}: {e}")

        return {"ok": True, "report_id": rpt_id}

    @router.post("/api/admin/config")
    async def api_admin_config(request: Request):
        await require_admin(request)
        body = await request.json()

        def _update_cfg():
            _, _, _, _, cfg_sheet, _, _, _ = get_all_worksheets_fn()
            rows = cfg_sheet.get_all_values()
            key_to_row = {r[0].strip(): idx for idx, r in enumerate(rows[1:], start=2) if r and r[0].strip()}
            mapping = {
                "LAUNCH_MODE": body.get("LAUNCH_MODE"),
                "MATRIC_DATE": body.get("MATRIC_DATE"),
                "GRADE8_MINISTRY_DATE": body.get("GRADE8_MINISTRY_DATE"),
                "GRADE6_MINISTRY_DATE": body.get("GRADE6_MINISTRY_DATE"),
                "SEMESTER_DATE": body.get("SEMESTER_DATE"),
            }
            updates, appends = [], []
            for k, v in mapping.items():
                if v is None:
                    continue
                val = str(v).strip()
                if k in key_to_row:
                    updates.append({"range": f"B{key_to_row[k]}", "values": [[val]]})
                else:
                    appends.append([k, val])
            if updates:
                cfg_sheet.batch_update(updates)
            if appends:
                cfg_sheet.append_rows(appends, value_input_option="USER_ENTERED")

        await asyncio.to_thread(_update_cfg)
        invalidate_config_cache()
        return {"ok": True}

    @router.post("/api/admin/toggle-trial")
    async def api_admin_toggle_trial(request: Request):
        await require_admin(request)
        body = await request.json()
        doc_id = (body.get("doc_id") or "").strip()
        is_trial = bool(body.get("is_trial"))
        _, by_id, _ = await get_library_and_keys()
        item = by_id.get(doc_id)
        if not item:
            raise HTTPException(status_code=404, detail="Document not found")

        def _set_trial():
            _, pdf_sheet, _, _, _, _, _, _ = get_all_worksheets_fn()
            pdf_sheet.update_cell(item["row_idx"], 22, "YES" if is_trial else "")

        await asyncio.to_thread(_set_trial)
        invalidate_library_cache()
        return {"ok": True, "is_trial": is_trial}

    @router.post("/api/admin/broadcast")
    async def api_admin_broadcast(request: Request):
        await require_admin(request)
        body = await request.json()
        target = (body.get("target") or "all").lower()
        msg_text = (body.get("message") or "").strip()
        if not msg_text:
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        bundle = await get_reg_bundle()
        filters_map = {
            "all": lambda r: True,
            "parents": lambda r: r["role"] == "parent",
            "approved": lambda r: r["status"] in ("APPROVED", "EXPIRED"),
            "new": lambda r: r["status"] == "NEW",
            "natural": lambda r: r["stream"].lower() == "natural",
            "social": lambda r: r["stream"].lower() == "social",
            "grade_12": lambda r: r["grade"] == "Grade 12",
            "grade_8": lambda r: r["grade"] == "Grade 8",
            "grade_6": lambda r: r["grade"] == "Grade 6",
        }
        fn = filters_map.get(target, lambda r: True)
        recipients = list(dict.fromkeys(int(r["tg_id"]) for r in bundle["all_regs"] if r["tg_id"] and fn(r)))

        bot = get_ptb_app().bot
        formatted = f"<b>Announcement — Qelal Learning (ቀላል)</b>\n\n{html.escape(msg_text)}"
        sent = failed = 0
        for uid in recipients:
            try:
                await bot.send_message(chat_id=uid, text=formatted, parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)

        return {"ok": True, "sent": sent, "failed": failed}

    return router
