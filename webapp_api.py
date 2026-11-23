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
    trigger_reclassify_fn=None,
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

        jobs = get_job_status_fn() if get_job_status_fn else {
            "sync": {"running": False},
            "verify": {"running": False},
            "reclassify": {"running": False},
        }

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
        jobs = get_job_status_fn() if get_job_status_fn else {
            "sync": {"running": False},
            "verify": {"running": False},
            "reclassify": {"running": False},
        }
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

    @router.post("/api/admin/reclassify-library")
    async def api_admin_reclassify_library(request: Request):
        await require_admin(request)
        if not trigger_reclassify_fn:
            raise HTTPException(status_code=501, detail="Re-classify trigger is not configured")
        res = trigger_reclassify_fn()
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("detail", "Could not start re-classification"))
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

Reply "next" after committing webapp_api.py for Part 3 of 3 (static/app.js).

Allowed: user next Here is the final Part 3 of 3 (static/app.js).

(Open static → app.js on GitHub → Select All → Delete → Paste this → Commit.
Wait ~1–2 minutes for Render to show "Your service is live", then open the Mini
App → Admin tab and tap Re-Classify PDFs.)

Part 3 of 3 — Replace Entire static/app.js

(function () {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try {
      tg.ready();
      tg.expand();
      if (typeof tg.setHeaderColor === "function") tg.setHeaderColor("#0F2342");
      if (typeof tg.setBackgroundColor === "function") tg.setBackgroundColor("#F5F3EE");
    } catch (_) {}
  }

  if (window.pdfjsLib) {
    window.pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
  }

  const GRADES = [
    "Grade 1", "Grade 2", "Grade 3",
    "Grade 4", "Grade 5", "Grade 6",
    "Grade 7", "Grade 8", "Grade 9",
    "Grade 10", "Grade 11", "Grade 12",
  ];

  // ==================== TRILINGUAL DICTIONARY (EN / AM / OM) ====================
  const I18N = {
    en: {
      brandSub: "Bishoftu Study & Exam Hub",
      loading: "Opening Qelal Learning...",
      outsideTitle: "Open inside Telegram",
      outsideBody:
        "This study portal runs inside Telegram so your reading progress, practice quizzes, and family dashboard stay connected. Open the Qelal Learning bot in Telegram and send /start.",
      retry: "Try again",
      regSub: "Bishoftu Study & Exam Hub · Grades 1–12",
      regLangLabel: "Select your language",
      regIntro:
        "Register once to read textbooks and past national exams, check quiz answers automatically, and reserve a seat for weekend coaching or 1-on-1 home tutoring in Bishoftu.",
      regRolePrompt: "Who is registering?",
      roleStudent: "Student",
      roleParent: "Parent / Guardian",
      fullNameStudent: "Student full name",
      fullNameParent: "Parent / Guardian full name",
      phoneLabel: "Phone number",
      gradeLevel: "Grade level (1–12)",
      examTag68: "Ministry Exam",
      examTag12: "National Exam",
      streamLabel: "Academic stream",
      streamNatural: "Natural Science",
      streamSocial: "Social Science",
      formatStudentLabel: "Preferred study format",
      formatParentLabel: "Default study format",
      formatWeekend: "Weekend Study Hub",
      formatHome: "1-on-1 Home Tutoring",
      childrenHeading: "Children",
      addChild: "+ Add another child",
      removeChild: "Remove",
      childCardTitle: "Child",
      childNameLabel: "Child's full name",
      childContactLabel: "Child's Telegram @username or phone (optional)",
      childContactHint:
        "If your child uses Telegram, enter their @username or phone number so their account links automatically without duplicates.",
      siblingDiscountNote:
        "Sibling discount applies automatically when 2 or more children are registered.",
      refLabel: "Referral or Study Squad code (optional)",
      legalPrefix: "By registering, you agree to Qelal Learning's",
      legalTerms: "Enrollment Terms",
      legalAnd: "and",
      legalPrivacy: "Privacy Policy",
      submitReg: "Complete registration",
      submitting: "Saving...",
      errNamePhone: "Please enter both full name and phone number.",
      errChildName: "Please enter a name for every child.",
      errGeneric: "Registration could not be completed. Please try again.",
      gradeWord: "Grade",
      navParent: "Child Progress",
      navLibrary: "Library",
      navPlans: "Study Plans",
      navAccount: "Account",
      navAdmin: "Admin",
      countdownMatric: "Grade 12 National Exam",
      countdownG8: "Grade 8 Ministry Exam",
      countdownG6: "Grade 6 Ministry Exam",
      countdownSem: "Semester Exam Target",
      daysLeftUnit: "days left",
      targetDate: "Target date",
      trialBanner:
        "Trial mode: 3 starter books for your grade and the first 10 questions of each quiz are open. Call +251 933 510 682 or +251 988 666 328 to activate full membership.",
      continueReading: "Continue reading",
      pageWord: "Page",
      searchPlaceholder: "Search books, exams, subjects...",
      allGrades: "All grades",
      myGrade: "My grade",
      allSubjects: "All subjects",
      allCategories: "All categories",
      savedBtn: "Saved",
      showingDocs: "resources",
      noDocsMatch: "No study materials matched your filters.",
      readPdf: "Read PDF",
      takeQuiz: "Quiz",
      quizPreview: "10-Q Quiz Preview",
      answerSheet: "Answer Sheet",
      sendToChat: "Send to Chat",
      saveDoc: "Save",
      savedDoc: "Saved",
      lockedFull: "Full Member",
      setTrialPick: "Trial Pick: Off",
      isTrialPick: "Trial Pick: On",
      reqPrompt: "Missing a textbook or past paper?",
      reqToggle: "Request material",
      reqSubject: "Subject & grade",
      reqDetails: "Book or exam details",
      reqSend: "Send request",
      reqSent: "Request sent to Qelal team.",
      reqEmpty: "Enter details of the material you need.",
      plansTrialNote:
        "Trial mode: the first 3 tasks of each study plan are open. Full members unlock complete multi-week schedules.",
      customPlanTitle: "Personal study checklist",
      customTaskPlaceholder: "Add a topic or revision task...",
      addBtn: "Add",
      deleteBtn: "Remove",
      doneLabel: "completed",
      lockedTask: "Full Member",
      childSwitchLabel: "Select child",
      notLinkedNote:
        "This child has not opened Telegram with their own account yet. Send the link below if they have Telegram, or share this phone to use Library and Study Plans together.",
      sharedPhoneTag: "Shared phone / Not linked",
      linkedTag: "Account linked",
      copyInvite: "Copy invite link",
      shareTg: "Share in Telegram",
      copied: "Copied",
      kpiPdfs: "Books Opened",
      kpiViews: "total opens",
      kpiQuizzes: "Quizzes Taken",
      kpiAvg: "avg",
      kpiPlan: "Study Plan",
      kpiSaved: "Saved Offline",
      kpiBookmarks: "bookmarks",
      chart7d: "7-Day Study Activity",
      quizTrendTitle: "Recent Quiz Scores",
      noQuizzesYet: "No quizzes submitted yet.",
      subjBreakdownTitle: "Activity by Subject",
      subjCol: "Subject",
      viewsCol: "Opens",
      quizzesCol: "Quizzes",
      avgCol: "Avg",
      recentActivityTitle: "Recent Reading & Bookmarks",
      biweeklyReportsTitle: "Bi-Weekly Tutor Progress Reports",
      noReportsYet: "No bi-weekly reports published yet.",
      attendanceLbl: "Attendance",
      scoresLbl: "Scores",
      improvedLbl: "Improved",
      focusLbl: "Next focus",
      accountTitle: "Account & Membership",
      nameLbl: "Name",
      roleLbl: "Role",
      statusLbl: "Status",
      tierLbl: "Access Tier",
      daysRemainLbl: "Days Left",
      squadTitle: "Study Squad & Referrals",
      squadDesc:
        "Share your code with classmates or parents in Bishoftu. Referring 2 friends qualifies for Study Squad seating and bound formula folders.",
      yourCode: "Your referral code",
      verifiedRefs: "Verified referrals",
      copyCode: "Copy code",
      childrenSectionTitle: "Registered Students",
      supportTitle: "Bishoftu Center Support",
      closeBtn: "Close",
      prevBtn: "Prev",
      nextBtn: "Next",
      quizTabBubbles: "Answer Bubbles",
      quizTabPaper: "Exam Paper (PDF)",
      quizTrialBanner:
        "Trial preview: questions 1 to 10 are graded below. Activate full membership to grade the entire exam.",
      gradeMyAnswers: "Grade my answers",
      retakeQuiz: "Retake quiz",
      scoreLabel: "Score",
      yoursCol: "Yours",
      keyCol: "Key",
      pdfLoading: "Loading document...",
      pdfError: "Could not display PDF inline.",
      pdfTryFrame: "Open fallback viewer",
      sentChatOk: "Sent to your Telegram chat.",
      adminSyncTitle: "Google Drive Sync & PDF Verification",
      syncDriveBtn: "Sync Google Drive",
      reclassifyBtn: "Re-Classify PDFs",
      verifyLinksBtn: "Verify PDF Links (40)",
      forceVerifyBtn: "Force Re-Verify",
      refreshAdminBtn: "Refresh Data",
      adminPdfTitle: "PDF Library Status",
      confirmLinkBtn: "Confirm Match",
      unlinkBtn: "Unlink",
      showMoreBtn: "Show more",
      adminConfigTitle: "System Configuration",
      saveConfig: "Save settings",
      adminPublishTitle: "Publish Bi-Weekly Progress Report",
      publishReportBtn: "Approve & Send Report",
      adminBroadcastTitle: "Send Announcement",
      sendBroadcastBtn: "Send Broadcast",
      adminAccountsTitle: "Accounts & Renewals",
      approve30d: "Approve 30d",
      renew30d: "Renew +30d",
      markLeft: "Mark Left",
      rejectBtn: "Reject",
      actionDone: "Updated successfully.",
    },
    am: {
      brandSub: "የቢሾፍቱ የጥናትና የፈተና ማዕከል",
      loading: "ቀላልን በመክፈት ላይ...",
      outsideTitle: "በቴሌግራም ውስጥ ይክፈቱ",
      outsideBody:
        "ይህ የጥናት መተግበሪያ የንባብ ሂደትዎን፣ የሙከራ ፈተናዎችንና የወላጅ መከታተያን ለማገናኘት በቴሌግራም ውስጥ ይሰራል። በቴሌግራም ውስጥ የቀላል ቦትን ከፍተው /start ይላኩ።",
      retry: "እንደገና ይሞክሩ",
      regSub: "የቢሾፍቱ የጥናትና የፈተና ማዕከል · ከ1ኛ–12ኛ ክፍል",
      regLangLabel: "ቋንቋ ይምረጡ",
      regIntro:
        "መጽሐፍትንና ያለፉ ብሔራዊ ፈተናዎችን ለማንበብ፣ ራስ-ሰር የፈተና ልምምዶችን ለመስራት እና በቢሾፍቱ የቅዳሜና እሁድ ወይም የቤት ለቤት ትምህርት ቦታ ለመያዝ አንዴ ይመዝገቡ።",
      regRolePrompt: "ማን ነው የሚመዘገበው?",
      roleStudent: "ተማሪ",
      roleParent: "ወላጅ / አሳዳጊ",
      fullNameStudent: "የተማሪው ሙሉ ስም",
      fullNameParent: "የወላጅ / አሳዳጊ ሙሉ ስም",
      phoneLabel: "ስልክ ቁጥር",
      gradeLevel: "ክፍል (1ኛ–12ኛ)",
      examTag68: "ሚኒስትሪ",
      examTag12: "ብሔራዊ ፈተና",
      streamLabel: "የትምህርት ዘርፍ",
      streamNatural: "ተፈጥሮ ሳይንስ",
      streamSocial: "ማህበራዊ ሳይንስ",
      formatStudentLabel: "የትምህርት አሰጣጥ ምርጫ",
      formatParentLabel: "ዋና የትምህርት አሰጣጥ ምርጫ",
      formatWeekend: "የቅዳሜና እሁድ ማዕከል",
      formatHome: "የቤት ለቤት 1-ለ-1",
      childrenHeading: "ልጆች",
      addChild: "+ ሌላ ልጅ ጨምር",
      removeChild: "አስወግድ",
      childCardTitle: "ልጅ",
      childNameLabel: "የልጁ ሙሉ ስም",
      childContactLabel: "የልጁ ቴሌግራም @username ወይም ስልክ (አማራጭ)",
      childContactHint:
        "ልጅዎ ቴሌግራም የሚጠቀም ከሆነ @username ወይም ስልክ ቁጥሩን ያስገቡ፤ ቦቱን ሲከፍቱ አካውንታቸው በቀጥታ ይገናኛል።",
      siblingDiscountNote:
        "2 እና ከዚያ በላይ ልጆችን ሲመዘግቡ የወንድማማች/እህትማማች ቅናሽ በቀጥታ ይታሰባል።",
      refLabel: "የግብዣ (Referral) ኮድ (አማራጭ)",
      legalPrefix: "በመመዝገብዎ የቀላልን",
      legalTerms: "የምዝገባ ውል",
      legalAnd: "እና",
      legalPrivacy: "የግላዊነት ፖሊሲ",
      submitReg: "ምዝገባውን አጠናቅቅ",
      submitting: "በመመዝገብ ላይ...",
      errNamePhone: "እባክዎ ሙሉ ስም እና ስልክ ቁጥር ያስገቡ።",
      errChildName: "እባክዎ የእያንዳንዱን ልጅ ስም ያስገቡ።",
      errGeneric: "ምዝገባው አልተሳካም። እባክዎ እንደገና ይሞክሩ።",
      gradeWord: "ክፍል",
      navParent: "የልጅ ሂደት",
      navLibrary: "ቤተ-መጽሐፍት",
      navPlans: "የጥናት እቅድ",
      navAccount: "አካውንት",
      navAdmin: "አስተዳዳሪ",
      countdownMatric: "የ12ኛ ክፍል ብሔራዊ ፈተና",
      countdownG8: "የ8ኛ ክፍል ሚኒስትሪ ፈተና",
      countdownG6: "የ6ኛ ክፍል ሚኒስትሪ ፈተና",
      countdownSem: "የሴሚስተር ፈተና ቀጠሮ",
      daysLeftUnit: "ቀናት ቀሩ",
      targetDate: "የታቀደ ቀን",
      trialBanner:
        "የሙከራ ጊዜ፡ ለክፍልዎ 3 መጽሐፍትና የእያንዳንዱ ፈተና የመጀመሪያ 10 ጥያቄዎች ተከፍተዋል። ሙሉ አገልግሎት ለማግኘት +251 933 510 682 / +251 988 666 328 ይደውሉ።",
      continueReading: "ንባብ ይቀጥሉ",
      pageWord: "ገጽ",
      searchPlaceholder: "መጽሐፍትን፣ ፈተናዎችን፣ ትምህርቶችን ይፈልጉ...",
      allGrades: "ሁሉም ክፍሎች",
      myGrade: "የኔ ክፍል",
      allSubjects: "ሁሉም ትምህርቶች",
      allCategories: "ሁሉም አይነቶች",
      savedBtn: "የተቀመጡ",
      showingDocs: "መጽሐፍት/ፋይሎች",
      noDocsMatch: "ከፍለጋዎ ጋር የሚመሳሰል ፋይል አልተገኘም።",
      readPdf: "አንብብ (PDF)",
      takeQuiz: "ፈተና ስራ",
      quizPreview: "10 ጥያቄ ሙከራ",
      answerSheet: "መልስ መመልከቻ",
      sendToChat: "ወደ ቴሌግራም ላክ",
      saveDoc: "አስቀምጥ",
      savedDoc: "ተቀምጧል",
      lockedFull: "ሙሉ አባል",
      setTrialPick: "ለሙከራ አድርግ",
      isTrialPick: "የሙከራ ምርጫ: በርቷል",
      reqPrompt: "የሚፈልጉት መጽሐፍ ወይም ፈተና ጠፋ?",
      reqToggle: "ፋይል ይጠይቁ",
      reqSubject: "ትምህርት እና ክፍል",
      reqDetails: "የመጽሐፉ ወይም የፈተናው ዝርዝር",
      reqSend: "ጥያቄ ላክ",
      reqSent: "ጥያቄዎ ለቀላል ቡድን ተልኳል።",
      reqEmpty: "እባክዎ የሚፈልጉትን ዝርዝር ይጻፉ።",
      plansTrialNote:
        "የሙከራ ጊዜ፡ የእያንዳንዱ የጥናት እቅድ የመጀመሪያ 3 ተግባራት ተከፍተዋል። ሙሉ አባላት ሙሉውን እቅድ ያገኛሉ።",
      customPlanTitle: "የግል የጥናት ዝርዝር",
      customTaskPlaceholder: "የሚጠና ርዕስ ወይም ተግባር ይጨምሩ...",
      addBtn: "ጨምር",
      deleteBtn: "አጥፋ",
      doneLabel: "ተጠናቅቋል",
      lockedTask: "ሙሉ አባል",
      childSwitchLabel: "ልጅ ይምረጡ",
      notLinkedNote:
        "ልጅዎ ገና በራሳቸው ቴሌግራም አካውንት አልገቡም። የራሳቸው ቴሌግራም ካላቸው ከታች ያለውን ሊንክ ይላኩላቸው፤ ወይም ይህንኑ ስልክ በጋራ ተጠቅመው ቤተ-መጽሐፍቱን ይክፈቱ።",
      sharedPhoneTag: "ያልተገናኘ / በጋራ ስልክ",
      linkedTag: "አካውንት ተገናኝቷል",
      copyInvite: "የግብዣ ሊንክ ቅዳ",
      shareTg: "በቴሌግራም ላክ",
      copied: "ተቀድቷል",
      kpiPdfs: "የተከፈቱ መጽሐፍት",
      kpiViews: "ጠቅላላ ንባቦች",
      kpiQuizzes: "የተሰሩ ፈተናዎች",
      kpiAvg: "አማካይ",
      kpiPlan: "የጥናት እቅድ",
      kpiSaved: "ለኦፍላይን የተላኩ",
      kpiBookmarks: "የተቀመጡ",
      chart7d: "የ7 ቀናት የጥናት እንቅስቃሴ",
      quizTrendTitle: "የቅርብ ጊዜ የፈተና ውጤቶች",
      noQuizzesYet: "እስካሁን የተሰራ የሙከራ ፈተና የለም።",
      subjBreakdownTitle: "በየትምህርቱ የተደረገ እንቅስቃሴ",
      subjCol: "ትምህርት",
      viewsCol: "ንባብ",
      quizzesCol: "ፈተና",
      avgCol: "አማካይ",
      recentActivityTitle: "የቅርብ ጊዜ ንባብ እና የተቀመጡ",
      biweeklyReportsTitle: "የሁለት ሳምንት የአስጠኚ ሪፖርቶች",
      noReportsYet: "ገና የታተመ የሁለት ሳምንት ሪፖርት የለም።",
      attendanceLbl: "ክትትል",
      scoresLbl: "ውጤቶች",
      improvedLbl: "መሻሻል",
      focusLbl: "ቀጣይ ትኩረት",
      accountTitle: "አካውንት እና አባልነት",
      nameLbl: "ስም",
      roleLbl: "ሚና",
      statusLbl: "ሁኔታ",
      tierLbl: "የአገልግሎት ደረጃ",
      daysRemainLbl: "የቀሩ ቀናት",
      squadTitle: "የጥናት ቡድን እና ግብዣ",
      squadDesc:
        "ኮድዎን በቢሾፍቱ ለሚገኙ ጓደኞች ወይም ወላጆች ያጋሩ። 2 ጓደኞችን ሲጋብዙ የጥናት ቡድን መቀመጫና የፎርሙላ ማህደር ያገኛሉ።",
      yourCode: "የእርስዎ የግብዣ ኮድ",
      verifiedRefs: "የጸደቁ ግብዣዎች",
      copyCode: "ኮድ ቅዳ",
      childrenSectionTitle: "የተመዘገቡ ልጆች",
      supportTitle: "የቢሾፍቱ ማዕከል ድጋፍ",
      closeBtn: "ዝጋ",
      prevBtn: "ቀዳሚ",
      nextBtn: "ቀጣይ",
      quizTabBubbles: "መልስ መሙያ",
      quizTabPaper: "የፈተና ወረቀት (PDF)",
      quizTrialBanner:
        "የሙከራ እይታ፡ ከ1 እስከ 10 ያሉ ጥያቄዎች ይታረማሉ። ሙሉውን ፈተና ለማረም ሙሉ አባል ይሁኑ።",
      gradeMyAnswers: "መልሶቼን አርም",
      retakeQuiz: "እንደገና ስራ",
      scoreLabel: "ውጤት",
      yoursCol: "የእርስዎ",
      keyCol: "ትክክለኛ",
      pdfLoading: "ሰነዱን በመጫን ላይ...",
      pdfError: "ፋይሉን እዚህ ማሳየት አልተቻለም።",
      pdfTryFrame: "በተለዋጭ መክፈቻ ክፈት",
      sentChatOk: "ወደ ቴሌግራም ቻትዎ ተልኳል።",
      adminSyncTitle: "የGoogle Drive እና PDF ማገናኛ",
      syncDriveBtn: "Google Drive አስምር",
      reclassifyBtn: "PDF እንደገና መድብ",
      verifyLinksBtn: "PDF አረጋግጥ (40)",
      forceVerifyBtn: "እንደገና አረጋግጥ",
      refreshAdminBtn: "መረጃ አድስ",
      adminPdfTitle: "የPDF መጽሐፍት ሁኔታ",
      confirmLinkBtn: "አጽድቅ",
      unlinkBtn: "አላቅቅ",
      showMoreBtn: "ተጨማሪ አሳይ",
      adminConfigTitle: "የስርዓት ማስተካከያ",
      saveConfig: "ቅንብሮችን አስቀምጥ",
      adminPublishTitle: "የሁለት ሳምንት ሪፖርት ላክ",
      publishReportBtn: "አጽድቅና ለወላጅ ላክ",
      adminBroadcastTitle: "ማስታወቂያ ላክ",
      sendBroadcastBtn: "መልዕክት ላክ",
      adminAccountsTitle: "አካውንቶች እና እድሳት",
      approve30d: "አጽድቅ (30 ቀን)",
      renew30d: "አድስ (+30 ቀን)",
      markLeft: "ወጥቷል በል",
      rejectBtn: "አትቀበል",
      actionDone: "ተስተካክሏል።",
    },
    om: {
      brandSub: "Giddugala Qo'annoo fi Qormaataa Bishooftuu",
      loading: "Qelal Learning banamaa jira...",
      outsideTitle: "Telegram keessatti banaa",
      outsideBody:
        "Appiin qo'annoo kun dubbisa keessan, qormaata shaakalaa fi hordoffii maatii walitti qabsiisuuf Telegram keessatti hojjeta. Botii Qelal Learning Telegram keessatti banuun /start ergaa.",
      retry: "Irra deebi'ii yaali",
      regSub: "Giddugala Qo'annoo fi Qormaataa Bishooftuu · Kutaa 1–12",
      regLangLabel: "Afaan keessan filadhaa",
      regIntro:
        "Kitaabota fi qormaata biyyaalessaa darban dubbisuuf, deebii qormaataa battalumatti sirreeffachuuf, akkasumas teessoo qo'annoo Sanbataa fi Dilbataa yookiin barsiisaa manaa Bishooftuu keessatti qabachuuf al tokko galmaa'aa.",
      regRolePrompt: "Eenyutu galmaa'aa jira?",
      roleStudent: "Barataa / Barattuu",
      roleParent: "Maatii / Guddistuu",
      fullNameStudent: "Maqaa guutuu barataa",
      fullNameParent: "Maqaa guutuu maatii / guddistuu",
      phoneLabel: "Lakkoofsa bilbilaa",
      gradeLevel: "Kutaa (1–12)",
      examTag68: "Ministirii",
      examTag12: "Qormaata Biyyaalessaa",
      streamLabel: "Gosa barumsaa",
      streamNatural: "Saayinsii Uumamaa",
      streamSocial: "Saayinsii Hawaasaa",
      formatStudentLabel: "Haala qo'annoo filatamu",
      formatParentLabel: "Haala qo'annoo ijoo",
      formatWeekend: "Giddugala Sanbataa & Dilbataa",
      formatHome: "Barsiisaa Manaa 1-if-1",
      childrenHeading: "Ijoollee",
      addChild: "+ Ijoollee biraa dabali",
      removeChild: "Haqi",
      childCardTitle: "Mucaa",
      childNameLabel: "Maqaa guutuu mucaa",
      childContactLabel: "Telegram @username ykn bilbila mucaa (dirqama miti)",
      childContactHint:
        "Mucaan keessan Telegram yoo qabaate @username ykn lakkoofsa bilbilaa galchaa; yommuu botii banan herregni isaanii ofumaan walqabata.",
      siblingDiscountNote:
        "Ijoollee 2 fi isaa ol yoo galmeessitan hir'inni kaffaltii obbolaa ofumaan hojjeta.",
      refLabel: "Koodii afeerraa / Study Squad (dirqama miti)",
      legalPrefix: "Galmaa'uun keessan",
      legalTerms: "Waliigaltee Galmee",
      legalAnd: "fi",
      legalPrivacy: "Imaammata Iccitii",
      submitReg: "Galmee xumuri",
      submitting: "Galmaa'aa jira...",
      errNamePhone: "Maaloo maqaa guutuu fi lakkoofsa bilbilaa galchaa.",
      errChildName: "Maaloo maqaa mucaa hundaa galchaa.",
      errGeneric: "Galmeen hin milkoofne. Maaloo irra deebi'aa yaalaa.",
      gradeWord: "Kutaa",
      navParent: "Hordoffii Mucaa",
      navLibrary: "Mana Kitaabaa",
      navPlans: "Karoora Qo'annoo",
      navAccount: "Herrega",
      navAdmin: "Bulchaa",
      countdownMatric: "Qormaata Biyyaalessaa Kutaa 12",
      countdownG8: "Qormaata Ministirii Kutaa 8",
      countdownG6: "Qormaata Ministirii Kutaa 6",
      countdownSem: "Qormaata Seemeestiraa",
      daysLeftUnit: "guyyoota hafe",
      targetDate: "Guyyaa qormaataa",
      trialBanner:
        "Haala Yaalii: Kitaabota jalqabaa 3 kutaa keessanii fi gaaffilee 10 jalqabaa qormaata hundaa banamaniiru. Miseensa guutuu ta'uuf +251 933 510 682 / +251 988 666 328 bilbilaa.",
      continueReading: "Dubbisa itti fufi",
      pageWord: "Fuula",
      searchPlaceholder: "Kitaabota, qormaata, gosa barumsaa barbaadi...",
      allGrades: "Kutaa hundaa",
      myGrade: "Kutaa koo",
      allSubjects: "Gosa barumsaa hundaa",
      allCategories: "Gosa qabiyyee hundaa",
      savedBtn: "Ol-kaa'ame",
      showingDocs: "qabiyyeewwan",
      noDocsMatch: "Qabiyyeen barbaacha keessaniin walsimu hin argamne.",
      readPdf: "Dubbisi (PDF)",
      takeQuiz: "Qormaata",
      quizPreview: "Yaalii Gaaffii 10",
      answerSheet: "Waraqaa Deebii",
      sendToChat: "Gara Chaatii Ergi",
      saveDoc: "Ol-kaa'i",
      savedDoc: "Ol-kaa'ameera",
      lockedFull: "Miseensa Guutuu",
      setTrialPick: "Yaalii Godhi",
      isTrialPick: "Filannoo Yaalii: Banaa",
      reqPrompt: "Kitaaba ykn qormaata barbaaddan dhabdanii?",
      reqToggle: "Qabiyyee gaafadhaa",
      reqSubject: "Gosa barumsaa fi kutaa",
      reqDetails: "Maqaa kitaabaa ykn bara qormaataa",
      reqSend: "Gaaffii ergi",
      reqSent: "Gaaffiin keessan garee Qelal tiif ergameera.",
      reqEmpty: "Maaloo waan barbaaddan barreessaa.",
      plansTrialNote:
        "Haala Yaalii: Hojiiwwan jalqabaa 3 karoora hundaa banamaniiru. Miseensonni guutuun karoora torban hedduu argatu.",
      customPlanTitle: "Tarree qo'annoo dhuunfaa",
      customTaskPlaceholder: "Mata-duree ykn hojii qo'annoo dabali...",
      addBtn: "Dabali",
      deleteBtn: "Haqi",
      doneLabel: "xumurameera",
      lockedTask: "Miseensa Guutuu",
      childSwitchLabel: "Mucaa filadhu",
      notLinkedNote:
        "Mucaan keessan ammallee Telegram dhuunfaa isaaniitiin hin banne. Telegram yoo qabaatan liinkii gadii ergaafii, yookiin bilbila kana waliin fayyadamuun Mana Kitaabaa fi Karoora banaa.",
      sharedPhoneTag: "Wal hin qabanne / Bilbila waliinii",
      linkedTag: "Herregni walqabateera",
      copyInvite: "Liinkii afeerraa garagalchi",
      shareTg: "Telegram irratti ergi",
      copied: "Garagalfameera",
      kpiPdfs: "Kitaabota Banaman",
      kpiViews: "baninsa waliigalaa",
      kpiQuizzes: "Qormaata Hojjataman",
      kpiAvg: "giddugaleessa",
      kpiPlan: "Karoora Qo'annoo",
      kpiSaved: "Offline Ol-kaa'ame",
      kpiBookmarks: "mallatteeffame",
      chart7d: "Sochii Qo'annoo Guyyoota 7",
      quizTrendTitle: "Qabxii Qormaataa Dhihoo",
      noQuizzesYet: "Ammatti qormaatni hojjatame hin jiru.",
      subjBreakdownTitle: "Sochii Gosa Barumsaatiin",
      subjCol: "Barumsa",
      viewsCol: "Baninsa",
      quizzesCol: "Qormaata",
      avgCol: "Giddugaleessa",
      recentActivityTitle: "Dubbisa Dhihoo fi Ol-kaa'aman",
      biweeklyReportsTitle: "Gabaasa Barsiisaa Torban Lamaa",
      noReportsYet: "Ammatti gabaasni torban lamaa hin maxxanfamne.",
      attendanceLbl: "Hirmaannaa",
      scoresLbl: "Qabxiiwwan",
      improvedLbl: "Fooyya'iinsa",
      focusLbl: "Xiyyeeffannoo itti aanu",
      accountTitle: "Herrega fi Miseensummaa",
      nameLbl: "Maqaa",
      roleLbl: "Gahee",
      statusLbl: "Haala",
      tierLbl: "Sadarkaa Tajaajilaa",
      daysRemainLbl: "Guyyoota Hafe",
      squadTitle: "Garee Qo'annoo fi Afeerraa",
      squadDesc:
        "Koodii keessan hiriyoota ykn maatii Bishooftuu jiraniif qoodaa. Hiriyoota 2 yoo afeertan teessoo Study Squad fi galmee foormulaa argattu.",
      yourCode: "Koodii afeerraa keessan",
      verifiedRefs: "Afeerraawwan mirkanaa'an",
      copyCode: "Koodii garagalchi",
      childrenSectionTitle: "Barattoota Galmaa'an",
      supportTitle: "Deeggarsa Giddugala Bishooftuu",
      closeBtn: "Cufi",
      prevBtn: "Kan duraa",
      nextBtn: "Itti aanu",
      quizTabBubbles: "Waraqaa Deebii",
      quizTabPaper: "Waraqaa Qormaataa (PDF)",
      quizTrialBanner:
        "Yaalii: Gaaffilee 1 hanga 10 sirreeffamu. Qormaata guutuu sirreeffachuuf miseensa guutuu ta'aa.",
      gradeMyAnswers: "Deebii koo sirreessi",
      retakeQuiz: "Irra deebi'ii hojjadhu",
      scoreLabel: "Qabxii",
      yoursCol: "Keessan",
      keyCol: "Sirrii",
      pdfLoading: "Sanadni fe'amaa jira...",
      pdfError: "PDF asitti mul'isuun hin danda'amne.",
      pdfTryFrame: "Banaa biraatiin yaali",
      sentChatOk: "Gara chaatii Telegram keessaniitti ergameera.",
      adminSyncTitle: "Qindaa'ina Google Drive fi Mirkaneessa PDF",
      syncDriveBtn: "Google Drive Qindeessi",
      reclassifyBtn: "PDF Irra Deebi'ii Qoodi",
      verifyLinksBtn: "PDF Mirkaneessi (40)",
      forceVerifyBtn: "Irra Deebi'ii Mirkaneessi",
      refreshAdminBtn: "Haaromsi",
      adminPdfTitle: "Haala Mana Kitaabaa PDF",
      confirmLinkBtn: "Mirkaneessi",
      unlinkBtn: "Addaan Baasi",
      showMoreBtn: "Dabalata agarsiisi",
      adminConfigTitle: "Qindaa'ina Sirnaa",
      saveConfig: "Qindaa'ina ol-kaa'i",
      adminPublishTitle: "Gabaasa Torban Lamaa Ergi",
      publishReportBtn: "Mirkaneessii Ergi",
      adminBroadcastTitle: "Beeksisa Ergi",
      sendBroadcastBtn: "Beeksisa Ergi",
      adminAccountsTitle: "Herregaa fi Haaromsa",
      approve30d: "Mirkaneessi (30g)",
      renew30d: "Haaromsi (+30g)",
      markLeft: "Baheera jedhi",
      rejectBtn: "Diduu",
      actionDone: "Haalaan haaromfameera.",
    },
  };

  // ==================== APP STATE ====================
  const state = {
    lang: "en",
    token: "",
    auth: null,
    activeTab: "library",
    regRole: "student",
    regStudentGrade: "Grade 12",
    regStudentStream: "Natural",
    regStudentFormat: "Weekend Hub",
    regParentFormat: "Weekend Hub",
    regChildren: [
      { name: "", grade: "Grade 8", stream: "Natural", format: "Weekend Hub", child_contact: "" },
    ],
    libraryItems: [],
    libraryLoaded: false,
    filterGrade: "MY_GRADE",
    filterSubject: "ALL",
    filterCategory: "ALL",
    filterSavedOnly: false,
    searchQuery: "",
    progress: { bookmarks: [], last_read: {}, plan_progress: {}, custom_plan: [] },
    studyPlans: [],
    parentAnalytics: null,
    activeChildIdx: 0,
    adminOverview: null,
    adminAccountFilter: "ALL",
    adminAccountSearch: "",
    adminPdfFilter: "ALL",
    adminPdfSearch: "",
    adminPdfLimit: 40,
    adminPollTimer: null,
    pdfDocId: null,
    pdfDocObj: null,
    pdfPage: 1,
    pdfTotalPages: 1,
    pdfScale: 1.15,
    pdfRenderTask: null,
    pdfSaveTimer: null,
    quizDocId: null,
    quizMeta: null,
    quizAnswers: {},
    quizPane: "bubbles",
    quizPdfDocObj: null,
    quizPdfPage: 1,
    quizPdfTotal: 1,
    quizPdfScale: 1.05,
    quizPdfRenderTask: null,
  };

  function t(key) {
    return (I18N[state.lang] && I18N[state.lang][key]) || I18N.en[key] || key;
  }

  function esc(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatGradeLabel(gradeStr) {
    const m = /^Grade\s+(\d+)$/i.exec(String(gradeStr || "").trim());
    if (!m) return gradeStr || "";
    const n = m[1];
    if (state.lang === "am") return `${n}ኛ ክፍል`;
    if (state.lang === "om") return `Kutaa ${n}`;
    return `Grade ${n}`;
  }

  function setHidden(id, hide) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.toggle("hidden", hide);
    el.style.display = hide ? "none" : "";
  }

  function showBootError(msg) {
    setHidden("screenLoading", false);
    const box = document.getElementById("loadingText") || document.getElementById("screenLoading");
    if (box) {
      box.textContent = "Error: " + msg;
      box.style.color = "#B91C1C";
    }
  }

  function showToast(msg, isError = false) {
    const box = document.getElementById("toastRegion");
    if (!box) return;
    const el = document.createElement("div");
    el.className = "toast" + (isError ? " is-error" : "");
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(() => {
      el.remove();
    }, 3200);
  }

  async function apiFetch(url, options = {}) {
    const headers = Object.assign({}, options.headers || {});
    if (state.token) {
      headers["Authorization"] = "Bearer " + state.token;
    }
    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeoutMs || 20000);
    try {
      const resp = await fetch(url, Object.assign({}, options, { headers, signal: controller.signal }));
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        throw new Error(data.detail || `HTTP ${resp.status}`);
      }
      return data;
    } catch (err) {
      if (err && err.name === "AbortError") {
        throw new Error("Server took too long to respond. Tap Try again.");
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }

  // ==================== LANGUAGE SWITCHING ====================
  async function setLanguage(lang, persist = false) {
    if (!["en", "am", "om"].includes(lang)) return;
    state.lang = lang;
    document.documentElement.lang = lang;

    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    document.querySelectorAll(".lang-card").forEach((card) => {
      card.classList.toggle("active", card.dataset.lang === lang);
    });

    applyStaticTranslations();

    if (state.auth && (state.auth.registered || state.auth.ok)) {
      state.auth.lang = lang;
      populateLibraryFilterOptions();
      renderPortalHeader();
      renderNav();
      renderActiveView();
    } else {
      renderRegistrationDynamicParts();
    }

    if (persist && state.token) {
      try {
        await apiFetch("/api/set-lang", { method: "POST", body: JSON.stringify({ lang }) });
      } catch (_) {}
    }
  }

  function applyStaticTranslations() {
    const setText = (id, key) => {
      const el = document.getElementById(id);
      if (el) el.textContent = t(key);
    };
    const setPlaceholder = (id, key) => {
      const el = document.getElementById(id);
      if (el) el.placeholder = t(key);
    };

    setText("loadingText", "loading");
    setText("outsideTitle", "outsideTitle");
    setText("outsideBody", "outsideBody");
    setText("outsideRetryBtn", "retry");

    setText("regHeaderSub", "regSub");
    setText("regLangLabel", "regLangLabel");
    setText("regIntroText", "regIntro");
    setText("regRolePrompt", "regRolePrompt");
    setText("roleStudentText", "roleStudent");
    setText("roleParentText", "roleParent");
    setText("regNameLabel", state.regRole === "parent" ? "fullNameParent" : "fullNameStudent");
    setText("regPhoneLabel", "phoneLabel");
    setText("regStudentGradeLabel", "gradeLevel");
    setText("regStudentStreamLabel", "streamLabel");
    setText("regStudentFormatLabel", "formatStudentLabel");
    setText("regParentFormatLabel", "formatParentLabel");
    setText("regChildrenHeading", "childrenHeading");
    setText("btnAddChild", "addChild");
    setText("regSiblingBanner", "siblingDiscountNote");
    setText("regRefLabel", "refLabel");
    setText("regLegalPrefix", "legalPrefix");
    setText("btnOpenTermsReg", "legalTerms");
    setText("regLegalAnd", "legalAnd");
    setText("btnOpenPrivacyReg", "legalPrivacy");
    setText("btnSubmitReg", "submitReg");

    document.querySelectorAll('[data-stream="Natural"]').forEach((b) => (b.textContent = t("streamNatural")));
    document.querySelectorAll('[data-stream="Social"]').forEach((b) => (b.textContent = t("streamSocial")));
    document.querySelectorAll('[data-format="Weekend Hub"]').forEach((b) => (b.textContent = t("formatWeekend")));
    document.querySelectorAll('[data-format="1-on-1 Home"]').forEach((b) => (b.textContent = t("formatHome")));

    setText("continueReadingTitle", "continueReading");
    setPlaceholder("libSearch", "searchPlaceholder");
    setText("filterSavedBtn", "savedBtn");
    setText("reqPromptText", "reqPrompt");
    setText("reqToggleBtn", "reqToggle");
    setText("reqSubjectLabel", "reqSubject");
    setText("reqDetailsLabel", "reqDetails");
    setText("reqSendBtn", "reqSend");

    setText("plansTrialNote", "plansTrialNote");
    setText("customPlanTitle", "customPlanTitle");
    setPlaceholder("customTaskInput", "customTaskPlaceholder");
    setText("btnAddCustomTask", "addBtn");

    setText("btnOpenTermsFooter", "legalTerms");
    setText("btnOpenPrivacyFooter", "legalPrivacy");

    setText("btnPdfClose", "closeBtn");
    setText("btnPdfPrev", "prevBtn");
    setText("btnPdfNext", "nextBtn");
    setText("btnPdfSendChat", "sendToChat");
    setText("btnQuizClose", "closeBtn");
    setText("tabQuizBubbles", "quizTabBubbles");
    setText("tabQuizPaper", "quizTabPaper");
    setText("btnQuizPdfPrev", "prevBtn");
    setText("btnQuizPdfNext", "nextBtn");
    setText("btnQuizSubmit", "gradeMyAnswers");
    setText("btnLegalClose", "closeBtn");
  }

  // ==================== REGISTRATION SCREEN ====================
  function initRegistrationScreen(firstName = "") {
    setHidden("screenLoading", true);
    setHidden("screenOutside", true);
    setHidden("screenPortal", true);
    setHidden("appHeader", true);
    setHidden("screenRegister", false);

    const nameEl = document.getElementById("regName");
    if (nameEl && firstName && !nameEl.value) {
      nameEl.value = firstName;
    }

    const params = new URLSearchParams(window.location.search);
    const refParam = params.get("ref") || (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) || "";
    const regRefEl = document.getElementById("regReferral");
    if (refParam && regRefEl) {
      const cleanRef = refParam.replace(/^ref_/i, "").toUpperCase();
      if (cleanRef && !cleanRef.startsWith("CHILD_") && cleanRef !== "PARENT" && cleanRef !== "STUDENT") {
        regRefEl.value = cleanRef;
      }
      if (refParam.toLowerCase() === "parent") {
        setRegRole("parent");
      }
    }

    applyStaticTranslations();
    renderRegistrationDynamicParts();
  }

  function setRegRole(role) {
    state.regRole = role === "parent" ? "parent" : "student";
    document.querySelectorAll(".role-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.role === state.regRole);
    });
    setHidden("regStudentBlock", state.regRole !== "student");
    setHidden("regParentBlock", state.regRole !== "parent");
    const lbl = document.getElementById("regNameLabel");
    if (lbl) lbl.textContent = t(state.regRole === "parent" ? "fullNameParent" : "fullNameStudent");
    renderRegistrationDynamicParts();
  }

  function renderGradeButtonsHtml(selectedGrade) {
    return GRADES.map((g) => {
      const num = g.replace("Grade ", "");
      const isSelected = selectedGrade === g;
      let tagHtml = "";
      if (num === "6" || num === "8") tagHtml = `<span class="grade-btn-tag">${esc(t("examTag68"))}</span>`;
      if (num === "12") tagHtml = `<span class="grade-btn-tag">${esc(t("examTag12"))}</span>`;
      return `
        <button type="button" class="grade-btn ${isSelected ? "active" : ""}" data-grade="${esc(g)}">
          <span class="grade-btn-num">${esc(formatGradeLabel(g))}</span>
          ${tagHtml}
        </button>
      `;
    }).join("");
  }

  function renderRegistrationDynamicParts() {
    const sGrid = document.getElementById("regStudentGradeGrid");
    if (sGrid) {
      sGrid.innerHTML = renderGradeButtonsHtml(state.regStudentGrade);
      sGrid.querySelectorAll(".grade-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          state.regStudentGrade = btn.dataset.grade;
          renderRegistrationDynamicParts();
        });
      });
    }

    const needsStream = state.regStudentGrade === "Grade 11" || state.regStudentGrade === "Grade 12";
    setHidden("regStudentStreamBlock", !needsStream);

    const cList = document.getElementById("regChildrenList");
    const sibBanner = document.getElementById("regSiblingBanner");
    if (sibBanner) {
      sibBanner.classList.toggle("hidden", state.regChildren.length < 2);
      sibBanner.textContent = t("siblingDiscountNote");
    }

    if (cList) {
      cList.innerHTML = state.regChildren
        .map((ch, idx) => {
          const showStream = ch.grade === "Grade 11" || ch.grade === "Grade 12";
          return `
            <div class="child-form-card" data-child-idx="${idx}">
              <div class="child-form-head">
                <strong class="h3-sub">${esc(t("childCardTitle"))} ${idx + 1}</strong>
                ${
                  state.regChildren.length > 1
                    ? `<button type="button" class="btn btn-danger btn-sm btn-remove-child" data-idx="${idx}">${esc(t("removeChild"))}</button>`
                    : ""
                }
              </div>
              <div class="field-group">
                <label class="field-label">${esc(t("childNameLabel"))}</label>
                <input type="text" class="input child-name-input" data-idx="${idx}" value="${esc(ch.name)}" required />
              </div>
              <div class="field-group">
                <label class="field-label">${esc(t("gradeLevel"))}</label>
                <div class="grade-grid child-grade-grid" data-idx="${idx}">
                  ${renderGradeButtonsHtml(ch.grade)}
                </div>
              </div>
              ${
                showStream
                  ? `
                <div class="field-group">
                  <label class="field-label">${esc(t("streamLabel"))}</label>
                  <div class="seg-row child-stream-row" data-idx="${idx}">
                    <button type="button" class="seg-btn ${ch.stream === "Natural" ? "active" : ""}" data-stream="Natural">${esc(t("streamNatural"))}</button>
                    <button type="button" class="seg-btn ${ch.stream === "Social" ? "active" : ""}" data-stream="Social">${esc(t("streamSocial"))}</button>
                  </div>
                </div>
              `
                  : ""
              }
              <div class="field-group" style="margin-bottom:0;">
                <label class="field-label">${esc(t("childContactLabel"))}</label>
                <input type="text" class="input child-contact-input" data-idx="${idx}" placeholder="@username / 09..." value="${esc(ch.child_contact)}" />
                <div class="meta-line" style="margin-top:4px;">${esc(t("childContactHint"))}</div>
              </div>
            </div>
          `;
        })
        .join("");

      cList.querySelectorAll(".child-name-input").forEach((inp) => {
        inp.addEventListener("input", (e) => {
          state.regChildren[Number(e.target.dataset.idx)].name = e.target.value;
        });
      });
      cList.querySelectorAll(".child-contact-input").forEach((inp) => {
        inp.addEventListener("input", (e) => {
          state.regChildren[Number(e.target.dataset.idx)].child_contact = e.target.value;
        });
      });
      cList.querySelectorAll(".child-grade-grid .grade-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.closest(".child-grade-grid").dataset.idx);
          state.regChildren[idx].grade = btn.dataset.grade;
          renderRegistrationDynamicParts();
        });
      });
      cList.querySelectorAll(".child-stream-row .seg-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.closest(".child-stream-row").dataset.idx);
          state.regChildren[idx].stream = btn.dataset.stream;
          renderRegistrationDynamicParts();
        });
      });
      cList.querySelectorAll(".btn-remove-child").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.dataset.idx);
          state.regChildren.splice(idx, 1);
          renderRegistrationDynamicParts();
        });
      });
    }
  }

  async function handleRegisterSubmit(e) {
    e.preventDefault();
    const errEl = document.getElementById("regErrorMsg");
    if (errEl) errEl.classList.add("hidden");

    const fullName = (document.getElementById("regName")?.value || "").trim();
    const phone = (document.getElementById("regPhone")?.value || "").trim();
    const refCode = (document.getElementById("regReferral")?.value || "").trim().toUpperCase();

    if (!fullName || !phone) {
      if (errEl) {
        errEl.textContent = t("errNamePhone");
        errEl.classList.remove("hidden");
      }
      return;
    }

    let childrenPayload = [];
    let chosenFormat = state.regStudentFormat;

    if (state.regRole === "student") {
      const streamVal =
        state.regStudentGrade === "Grade 11" || state.regStudentGrade === "Grade 12"
          ? state.regStudentStream
          : "General";
      childrenPayload = [
        {
          name: fullName,
          grade: state.regStudentGrade,
          stream: streamVal,
          format: state.regStudentFormat,
          child_contact: phone,
        },
      ];
    } else {
      chosenFormat = state.regParentFormat;
      for (const ch of state.regChildren) {
        if (!ch.name.trim()) {
          if (errEl) {
            errEl.textContent = t("errChildName");
            errEl.classList.remove("hidden");
          }
          return;
        }
      }
      childrenPayload = state.regChildren.map((ch) => ({
        name: ch.name.trim(),
        grade: ch.grade,
        stream: ch.grade === "Grade 11" || ch.grade === "Grade 12" ? ch.stream : "General",
        format: state.regParentFormat,
        child_contact: ch.child_contact.trim(),
      }));
    }

    const submitBtn = document.getElementById("btnSubmitReg");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = t("submitting");
    }

    try {
      await apiFetch("/api/register", {
        method: "POST",
        body: JSON.stringify({
          initData: tg ? tg.initData : "",
          role: state.regRole,
          lang: state.lang,
          full_name: fullName,
          phone: phone,
          format: chosenFormat,
          referral_code: refCode,
          children: childrenPayload,
        }),
      });
      await authenticate();
    } catch (err) {
      if (errEl) {
        errEl.textContent = err.message || t("errGeneric");
        errEl.classList.remove("hidden");
      }
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = t("submitReg");
      }
    }
  }

  // ==================== AUTH & PORTAL BOOT ====================
  async function authenticate() {
    setHidden("screenLoading", false);
    setHidden("screenOutside", true);
    setHidden("screenRegister", true);
    setHidden("screenPortal", true);

    const loadTxt = document.getElementById("loadingText");
    if (loadTxt) {
      loadTxt.textContent = t("loading");
      loadTxt.style.color = "";
    }

    try {
      const initData = tg ? tg.initData : "";
      const data = await apiFetch("/api/auth", {
        method: "POST",
        body: JSON.stringify({ initData }),
      });

      if (!data.ok) {
        if (data.status === "NOT_REGISTERED") {
          initRegistrationScreen(data.tg_first_name || "");
          return;
        }
        setHidden("screenLoading", true);
        setHidden("screenOutside", false);
        applyStaticTranslations();
        return;
      }

      state.auth = data;
      state.token = data.token;
      state.lang = ["en", "am", "om"].includes(data.lang) ? data.lang : "en";

      setHidden("screenLoading", true);
      setHidden("appHeader", false);
      setHidden("screenPortal", false);

      state.activeTab = data.role === "parent" ? "parent" : "library";

      await Promise.allSettled([loadProgress(), loadLibrary()]);
      await setLanguage(state.lang, false);
    } catch (err) {
      const outsideEl = document.getElementById("screenOutside");
      if (outsideEl) {
        setHidden("screenLoading", true);
        setHidden("screenOutside", false);
        const det = document.getElementById("outsideDetail");
        if (det) {
          det.textContent = err.message || "";
          det.classList.toggle("hidden", !err.message);
        }
      } else {
        showBootError(err.message || "Authentication failed");
      }
    }
  }

  function renderPortalHeader() {
    if (!state.auth) return;
    const titleEl = document.getElementById("headerTitle");
    if (titleEl) titleEl.textContent = "Qelal Learning (ቀላል)";
    const subParts = [state.auth.name];
    if (state.auth.role === "parent") {
      subParts.push(t("roleParent"));
    } else if (state.auth.grade) {
      subParts.push(formatGradeLabel(state.auth.grade));
    }
    const subEl = document.getElementById("headerSub");
    if (subEl) subEl.textContent = subParts.join(" · ");
  }

  function renderNav() {
    const nav = document.getElementById("mainNav");
    if (!nav) return;
    const tabs = [];
    if (state.auth.role === "parent") {
      tabs.push({ id: "parent", label: t("navParent") });
    }
    tabs.push({ id: "library", label: t("navLibrary") });
    tabs.push({ id: "plans", label: t("navPlans") });
    tabs.push({ id: "account", label: t("navAccount") });
    if (state.auth.is_admin) {
      tabs.push({ id: "admin", label: t("navAdmin") });
    }

    if (!tabs.some((tb) => tb.id === state.activeTab)) {
      state.activeTab = tabs[0].id;
    }

    nav.innerHTML = tabs
      .map(
        (tb) =>
          `<button type="button" class="nav-tab ${state.activeTab === tb.id ? "active" : ""}" data-tab="${tb.id}">${esc(tb.label)}</button>`
      )
      .join("");

    nav.querySelectorAll(".nav-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeTab = btn.dataset.tab;
        renderNav();
        renderActiveView();
      });
    });
  }

  function renderActiveView() {
    if (state.activeTab !== "admin") {
      stopAdminJobPolling();
    }
    ["viewParent", "viewLibrary", "viewPlans", "viewAccount", "viewAdmin"].forEach((id) => {
      setHidden(id, true);
    });

    if (state.activeTab === "parent") {
      setHidden("viewParent", false);
      renderParentView();
    } else if (state.activeTab === "library") {
      setHidden("viewLibrary", false);
      renderLibraryView();
    } else if (state.activeTab === "plans") {
      setHidden("viewPlans", false);
      renderPlansView();
    } else if (state.activeTab === "account") {
      setHidden("viewAccount", false);
      renderAccountView();
    } else if (state.activeTab === "admin" && state.auth.is_admin) {
      setHidden("viewAdmin", false);
      renderAdminView();
    }
  }

  // ==================== PROGRESS SYNC ====================
  async function loadProgress() {
    try {
      const data = await apiFetch("/api/progress");
      state.progress = {
        bookmarks: Array.isArray(data.bookmarks) ? data.bookmarks : [],
        last_read: data.last_read || {},
        plan_progress: data.plan_progress || {},
        custom_plan: Array.isArray(data.custom_plan) ? data.custom_plan : [],
      };
    } catch (_) {}
  }

  async function saveProgress() {
    try {
      await apiFetch("/api/progress", {
        method: "POST",
        body: JSON.stringify(state.progress),
      });
    } catch (_) {}
  }

  // ==================== LIBRARY VIEW ====================
  async function loadLibrary(forceRefresh = false) {
    try {
      const url = forceRefresh ? "/api/library?refresh=true" : "/api/library";
      const data = await apiFetch(url);
      state.libraryItems = data.items || [];
      state.libraryLoaded = true;
      populateLibraryFilterOptions();
      if (state.activeTab === "library") renderLibraryView();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function populateLibraryFilterOptions() {
    const gradeSel = document.getElementById("filterGrade");
    const subjSel = document.getElementById("filterSubject");
    const catSel = document.getElementById("filterCategory");
    if (!gradeSel || !subjSel || !catSel) return;

    const gradesSet = new Set(GRADES);
    const subjSet = new Set();
    const catSet = new Set();
    state.libraryItems.forEach((it) => {
      if (it.grade) gradesSet.add(it.grade);
      if (it.subject) subjSet.add(it.subject);
      if (it.category) catSet.add(it.category);
    });

    const userGrade = (state.auth && state.auth.grade) || "";
    gradeSel.innerHTML = [
      `<option value="MY_GRADE">${esc(t("myGrade"))} (${esc(formatGradeLabel(userGrade))})</option>`,
      `<option value="ALL">${esc(t("allGrades"))}</option>`,
      ...Array.from(gradesSet).map((g) => `<option value="${esc(g)}">${esc(formatGradeLabel(g))}</option>`),
    ].join("");
    if (Array.from(gradeSel.options).some((o) => o.value === state.filterGrade)) {
      gradeSel.value = state.filterGrade;
    } else {
      state.filterGrade = "ALL";
      gradeSel.value = "ALL";
    }

    subjSel.innerHTML =
      `<option value="ALL">${esc(t("allSubjects"))}</option>` +
      Array.from(subjSet)
        .sort()
        .map((s) => `<option value="${esc(s)}">${esc(s)}</option>`)
        .join("");
    subjSel.value = Array.from(subjSel.options).some((o) => o.value === state.filterSubject) ? state.filterSubject : "ALL";

    catSel.innerHTML =
      `<option value="ALL">${esc(t("allCategories"))}</option>` +
      Array.from(catSet)
        .sort()
        .map((c) => `<option value="${esc(c)}">${esc(c)}</option>`)
        .join("");
    catSel.value = Array.from(catSel.options).some((o) => o.value === state.filterCategory) ? state.filterCategory : "ALL";
  }

  function matchesUserGradeFilter(itemGrade, targetGrade) {
    if (!targetGrade) return true;
    if (itemGrade === targetGrade) return true;
    if (["Grade 9", "Grade 10", "Grade 11", "Grade 12"].includes(targetGrade) && itemGrade === "Grade 9-12") return true;
    if (["Grade 11", "Grade 12"].includes(targetGrade) && itemGrade === "Grade 11-12") return true;
    if (["Grade 9", "Grade 10"].includes(targetGrade) && itemGrade === "Grade 9-10") return true;
    return false;
  }

  function renderLibraryView() {
    const cdCard = document.getElementById("countdownCard");
    if (cdCard) {
      if (state.auth && state.auth.countdown && state.auth.countdown.date) {
        const cd = state.auth.countdown;
        const target = new Date(cd.date + "T00:00:00+03:00");
        const now = new Date();
        const diffDays = Math.max(0, Math.ceil((target - now) / (1000 * 60 * 60 * 24)));
        const labelMap = {
          matric_12: t("countdownMatric"),
          ministry_8: t("countdownG8"),
          ministry_6: t("countdownG6"),
          semester: t("countdownSem"),
        };
        cdCard.innerHTML = `
          <div>
            <div class="h3-sub">${esc(labelMap[cd.type] || t("countdownSem"))}</div>
            <div class="meta-line">${esc(t("targetDate"))}: <span class="mono-num">${esc(cd.date)}</span></div>
          </div>
          <div style="text-align:right;">
            <div class="countdown-days">${diffDays}</div>
            <div class="meta-line">${esc(t("daysLeftUnit"))}</div>
          </div>
        `;
        cdCard.classList.remove("hidden");
      } else {
        cdCard.classList.add("hidden");
      }
    }

    const trialEl = document.getElementById("trialBanner");
    if (trialEl) {
      if (state.auth && state.auth.tier === "TRIAL") {
        trialEl.textContent = t("trialBanner");
        trialEl.classList.remove("hidden");
      } else {
        trialEl.classList.add("hidden");
      }
    }

    const contWrap = document.getElementById("continueReadingSection");
    const contList = document.getElementById("continueReadingList");
    const byId = {};
    state.libraryItems.forEach((it) => (byId[it.doc_id] = it));
    const recentEntries = Object.entries(state.progress.last_read || {})
      .filter(([did]) => byId[did] && !byId[did].locked && byId[did].has_pdf)
      .sort((a, b) => (b[1].ts || 0) - (a[1].ts || 0))
      .slice(0, 3);

    if (contWrap && contList) {
      if (recentEntries.length > 0) {
        contWrap.classList.remove("hidden");
        contList.innerHTML = recentEntries
          .map(([did, info]) => {
            const item = byId[did];
            return `
              <div class="compact-row">
                <div style="min-width:0;">
                  <div class="doc-title">${esc(item.file_name)}</div>
                  <div class="doc-meta">${esc(item.subject)} · ${esc(t("pageWord"))} <span class="mono-num">${info.page || 1}</span></div>
                </div>
                <button type="button" class="btn btn-primary btn-sm btn-open-pdf" data-doc-id="${esc(did)}">${esc(t("readPdf"))}</button>
              </div>
            `;
          })
          .join("");
        contList.querySelectorAll(".btn-open-pdf").forEach((b) => {
          b.addEventListener("click", () => openPdfReader(b.dataset.docId));
        });
      } else {
        contWrap.classList.add("hidden");
      }
    }

    const q = state.searchQuery.trim().toLowerCase();
    const filtered = state.libraryItems.filter((it) => {
      if (state.filterGrade === "MY_GRADE") {
        if (!matchesUserGradeFilter(it.grade, state.auth.grade)) return false;
      } else if (state.filterGrade !== "ALL" && it.grade !== state.filterGrade) {
        return false;
      }
      if (state.filterSubject !== "ALL" && it.subject !== state.filterSubject) return false;
      if (state.filterCategory !== "ALL" && it.category !== state.filterCategory) return false;
      if (state.filterSavedOnly && !state.progress.bookmarks.includes(it.doc_id)) return false;
      if (q) {
        const hay = `${it.file_name} ${it.subject} ${it.category} ${it.grade} ${it.year}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    filtered.sort((a, b) => Number(a.locked) - Number(b.locked));

    const countEl = document.getElementById("libCountText");
    if (countEl) countEl.textContent = `${filtered.length} ${t("showingDocs")}`;
    const savedBtn = document.getElementById("filterSavedBtn");
    if (savedBtn) savedBtn.classList.toggle("active", state.filterSavedOnly);

    const listEl = document.getElementById("libList");
    if (!listEl) return;
    if (!filtered.length) {
      listEl.innerHTML = `<div class="ledger-row"><p class="muted-text">${esc(t("noDocsMatch"))}</p></div>`;
      return;
    }

    listEl.innerHTML = filtered
      .slice(0, 120)
      .map((it) => {
        const isBookmarked = state.progress.bookmarks.includes(it.doc_id);
        const metaParts = [
          formatGradeLabel(it.grade),
          it.stream && it.stream !== "General" ? it.stream : "",
          it.subject,
          it.category,
          it.year,
          it.file_size_mb ? `${it.file_size_mb} MB` : "",
        ].filter(Boolean);

        const actions = [];
        if (!it.locked) {
          if (it.has_pdf) {
            actions.push(`<button type="button" class="btn btn-primary btn-sm act-read" data-id="${esc(it.doc_id)}">${esc(t("readPdf"))}</button>`);
          }
          actions.push(`<button type="button" class="btn btn-secondary btn-sm act-send" data-id="${esc(it.doc_id)}">${esc(t("sendToChat"))}</button>`);
          if (it.linked_doc_id && it.category !== "Answer Sheet" && byId[it.linked_doc_id]) {
            actions.push(`<button type="button" class="btn btn-secondary btn-sm act-read" data-id="${esc(it.linked_doc_id)}">${esc(t("answerSheet"))}</button>`);
          }
        }
        if (it.has_quiz) {
          const qLabel = state.auth.tier === "TRIAL" ? t("quizPreview") : `${t("takeQuiz")} (${it.quiz_total_q})`;
          actions.push(`<button type="button" class="btn btn-secondary btn-sm act-quiz" data-id="${esc(it.doc_id)}">${esc(qLabel)}</button>`);
        }
        actions.push(
          `<button type="button" class="btn btn-secondary btn-sm act-bookmark ${isBookmarked ? "active" : ""}" data-id="${esc(it.doc_id)}">${esc(
            isBookmarked ? t("savedDoc") : t("saveDoc")
          )}</button>`
        );
        if (state.auth.is_admin) {
          actions.push(
            `<button type="button" class="btn btn-secondary btn-sm act-trial ${it.is_trial ? "active" : ""}" data-id="${esc(it.doc_id)}" data-trial="${it.is_trial ? "1" : "0"}">${esc(
              it.is_trial ? t("isTrialPick") : t("setTrialPick")
            )}</button>`
          );
        }

        return `
          <article class="ledger-row">
            <div class="ledger-row-head">
              <div style="min-width:0;">
                <div class="doc-title">${esc(it.file_name)}</div>
                <div class="doc-meta">${esc(metaParts.join(" · "))}</div>
              </div>
              ${it.locked ? `<span class="status-tag is-warn">${esc(t("lockedFull"))}</span>` : ""}
            </div>
            <div class="btn-row">${actions.join("")}</div>
          </article>
        `;
      })
      .join("");

    listEl.querySelectorAll(".act-read").forEach((b) => b.addEventListener("click", () => openPdfReader(b.dataset.id)));
    listEl.querySelectorAll(".act-send").forEach((b) => b.addEventListener("click", () => sendFileToTelegram(b.dataset.id, b)));
    listEl.querySelectorAll(".act-quiz").forEach((b) => b.addEventListener("click", () => openQuizRunner(b.dataset.id)));
    listEl.querySelectorAll(".act-bookmark").forEach((b) => b.addEventListener("click", () => toggleBookmark(b.dataset.id)));
    listEl.querySelectorAll(".act-trial").forEach((b) =>
      b.addEventListener("click", () => toggleAdminTrialPick(b.dataset.id, b.dataset.trial !== "1"))
    );
  }

  async function toggleBookmark(docId) {
    const idx = state.progress.bookmarks.indexOf(docId);
    if (idx >= 0) {
      state.progress.bookmarks.splice(idx, 1);
    } else {
      state.progress.bookmarks.push(docId);
    }
    if (state.activeTab === "library") renderLibraryView();
    updatePdfBookmarkBtn();
    await saveProgress();
  }

  async function sendFileToTelegram(docId, btnEl) {
    if (btnEl) btnEl.disabled = true;
    try {
      const res = await apiFetch(`/api/file/${encodeURIComponent(docId)}/send`, { method: "POST" });
      if (res.too_large) {
        showToast(res.message || "File exceeds Telegram limit; open in viewer.", true);
      } else {
        showToast(t("sentChatOk"));
      }
    } catch (err) {
      showToast(err.message, true);
    } finally {
      if (btnEl) btnEl.disabled = false;
    }
  }

  async function toggleAdminTrialPick(docId, nextState) {
    try {
      await apiFetch("/api/admin/toggle-trial", {
        method: "POST",
        body: JSON.stringify({ doc_id: docId, is_trial: nextState }),
      });
      await loadLibrary(true);
    } catch (err) {
      showToast(err.message, true);
    }
  }

  // ==================== IN-APP PDF READER (PDF.JS + FALLBACK) ====================
  function updatePdfBookmarkBtn() {
    const btn = document.getElementById("btnPdfBookmark");
    if (!btn || !state.pdfDocId) return;
    const saved = state.progress.bookmarks.includes(state.pdfDocId);
    btn.textContent = saved ? t("savedDoc") : t("saveDoc");
    btn.classList.toggle("active", saved);
  }

  async function loadPdfDocumentWithFallback(streamUrl) {
    if (!window.pdfjsLib) {
      throw new Error("PDF engine unavailable");
    }
    try {
      return await window.pdfjsLib.getDocument({ url: streamUrl, rangeChunkSize: 65536 }).promise;
    } catch (_) {
      const resp = await fetch(streamUrl);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const buf = await resp.arrayBuffer();
      return await window.pdfjsLib.getDocument({ data: buf }).promise;
    }
  }

  async function openPdfReader(docId) {
    const item = state.libraryItems.find((x) => x.doc_id === docId);
    state.pdfDocId = docId;
    state.pdfDocObj = null;
    state.pdfScale = 1.15;

    const savedPage = (state.progress.last_read && state.progress.last_read[docId] && state.progress.last_read[docId].page) || 1;
    state.pdfPage = savedPage;

    document.getElementById("pdfModalTitle").textContent = item ? item.file_name : docId;
    document.getElementById("pdfZoomLabel").textContent = "115%";
    document.getElementById("pdfCanvas").classList.remove("hidden");
    document.getElementById("pdfFallbackFrame").classList.add("hidden");
    const overlay = document.getElementById("pdfStatusOverlay");
    overlay.textContent = t("pdfLoading");
    overlay.classList.remove("hidden");

    updatePdfBookmarkBtn();
    setHidden("modalPdf", false);

    const streamUrl = `/api/file/${encodeURIComponent(docId)}/stream?token=${encodeURIComponent(state.token)}`;
    try {
      const pdfDoc = await loadPdfDocumentWithFallback(streamUrl);
      if (state.pdfDocId !== docId) return;
      state.pdfDocObj = pdfDoc;
      state.pdfTotalPages = pdfDoc.numPages;
      if (state.pdfPage > state.pdfTotalPages) state.pdfPage = 1;
      document.getElementById("pdfPageTotal").textContent = String(state.pdfTotalPages);
      overlay.classList.add("hidden");
      await renderMainPdfPage();
    } catch (_) {
      if (state.pdfDocId !== docId) return;
      overlay.innerHTML = `
        <p>${esc(t("pdfError"))}</p>
        <button type="button" id="btnTriggerFrameFallback" class="btn btn-primary btn-sm">${esc(t("pdfTryFrame"))}</button>
      `;
      document.getElementById("btnTriggerFrameFallback").addEventListener("click", () => {
        overlay.classList.add("hidden");
        document.getElementById("pdfCanvas").classList.add("hidden");
        const frame = document.getElementById("pdfFallbackFrame");
        frame.src = streamUrl;
        frame.classList.remove("hidden");
      });
    }
  }

  async function renderMainPdfPage() {
    if (!state.pdfDocObj) return;
    if (state.pdfRenderTask) {
      try {
        state.pdfRenderTask.cancel();
      } catch (_) {}
    }

    const pageNum = Math.max(1, Math.min(state.pdfPage, state.pdfTotalPages));
    state.pdfPage = pageNum;
    document.getElementById("pdfPageInput").value = String(pageNum);
    document.getElementById("pdfZoomLabel").textContent = Math.round(state.pdfScale * 100) + "%";

    const page = await state.pdfDocObj.getPage(pageNum);
    const viewportEl = document.getElementById("pdfViewport");
    const availW = Math.max(280, viewportEl.clientWidth - 28);
    const baseVp = page.getViewport({ scale: 1 });
    const fitScale = (availW / baseVp.width) * state.pdfScale;
    const vp = page.getViewport({ scale: fitScale });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const canvas = document.getElementById("pdfCanvas");
    const ctx = canvas.getContext("2d");
    canvas.width = Math.floor(vp.width * dpr);
    canvas.height = Math.floor(vp.height * dpr);
    canvas.style.width = Math.floor(vp.width) + "px";
    canvas.style.height = Math.floor(vp.height) + "px";

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const task = page.render({ canvasContext: ctx, viewport: vp });
    state.pdfRenderTask = task;

    try {
      await task.promise;
      state.progress.last_read[state.pdfDocId] = { page: pageNum, ts: Date.now() };
      clearTimeout(state.pdfSaveTimer);
      state.pdfSaveTimer = setTimeout(() => saveProgress(), 1200);
    } catch (_) {}
  }

  function closePdfReader() {
    setHidden("modalPdf", true);
    const frame = document.getElementById("pdfFallbackFrame");
    if (frame) frame.src = "about:blank";
    if (state.pdfDocObj) {
      try {
        state.pdfDocObj.destroy();
      } catch (_) {}
    }
    state.pdfDocObj = null;
    state.pdfDocId = null;
    if (state.activeTab === "library") renderLibraryView();
  }

  // ==================== BUBBLE-SHEET QUIZ RUNNER ====================
  async function openQuizRunner(docId) {
    state.quizDocId = docId;
    state.quizAnswers = {};
    state.quizPane = "bubbles";
    state.quizPdfDocObj = null;
    state.quizPdfPage = 1;
    state.quizPdfScale = 1.05;

    const item = state.libraryItems.find((x) => x.doc_id === docId);
    document.getElementById("quizModalTitle").textContent = item ? item.file_name : docId;
    document.getElementById("quizBubblesList").innerHTML = `<div class="ledger-row"><p class="muted-text">${esc(t("loading"))}</p></div>`;
    document.getElementById("quizResultPane").classList.add("hidden");
    document.getElementById("quizBubblesList").classList.remove("hidden");
    document.getElementById("quizSubmitBar").classList.remove("hidden");
    setHidden("modalQuiz", false);

    const hasPdf = item && item.has_pdf && !item.locked;
    document.getElementById("quizViewTabs").classList.toggle("hidden", !hasPdf);
    setQuizPane("bubbles");

    try {
      const meta = await apiFetch(`/api/quiz/${encodeURIComponent(docId)}`);
      state.quizMeta = meta;
      renderQuizBubbles();
    } catch (err) {
      document.getElementById("quizBubblesList").innerHTML = `<div class="ledger-row"><p class="error-inline">${esc(err.message)}</p></div>`;
    }
  }

  function setQuizPane(pane) {
    state.quizPane = pane;
    document.querySelectorAll(".quiz-subtab").forEach((b) => b.classList.toggle("active", b.dataset.pane === pane));
    document.getElementById("quizBubblePane").classList.toggle("hidden", pane !== "bubbles");
    document.getElementById("quizPdfPane").classList.toggle("hidden", pane !== "paper");

    if (pane === "paper" && !state.quizPdfDocObj && state.quizDocId) {
      loadQuizExamPdf();
    }
  }

  async function loadQuizExamPdf() {
    const statusEl = document.getElementById("quizPdfStatus");
    statusEl.textContent = t("pdfLoading");
    statusEl.classList.remove("hidden");
    const url = `/api/file/${encodeURIComponent(state.quizDocId)}/stream?token=${encodeURIComponent(state.token)}`;
    try {
      const pdfDoc = await loadPdfDocumentWithFallback(url);
      state.quizPdfDocObj = pdfDoc;
      state.quizPdfTotal = pdfDoc.numPages;
      statusEl.classList.add("hidden");
      await renderQuizPdfPage();
    } catch (_) {
      statusEl.textContent = t("pdfError");
    }
  }

  async function renderQuizPdfPage() {
    if (!state.quizPdfDocObj) return;
    if (state.quizPdfRenderTask) {
      try {
        state.quizPdfRenderTask.cancel();
      } catch (_) {}
    }
    const p = Math.max(1, Math.min(state.quizPdfPage, state.quizPdfTotal));
    state.quizPdfPage = p;
    document.getElementById("quizPdfPageLabel").textContent = `${p} / ${state.quizPdfTotal}`;

    const page = await state.quizPdfDocObj.getPage(p);
    const vpEl = document.getElementById("quizPdfViewport");
    const availW = Math.max(280, vpEl.clientWidth - 28);
    const baseVp = page.getViewport({ scale: 1 });
    const vp = page.getViewport({ scale: (availW / baseVp.width) * state.quizPdfScale });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const canvas = document.getElementById("quizPdfCanvas");
    const ctx = canvas.getContext("2d");
    canvas.width = Math.floor(vp.width * dpr);
    canvas.height = Math.floor(vp.height * dpr);
    canvas.style.width = Math.floor(vp.width) + "px";
    canvas.style.height = Math.floor(vp.height) + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const task = page.render({ canvasContext: ctx, viewport: vp });
    state.quizPdfRenderTask = task;
    try {
      await task.promise;
    } catch (_) {}
  }

  function renderQuizBubbles() {
    const meta = state.quizMeta;
    if (!meta) return;

    document.getElementById("quizMetaInfo").textContent = [meta.subject, meta.year, `${meta.unlocked_q} / ${meta.total_q} Q`]
      .filter(Boolean)
      .join(" · ");
    const trialNote = document.getElementById("quizTrialNote");
    if (meta.trial_limited && meta.total_q > meta.unlocked_q) {
      trialNote.textContent = t("quizTrialBanner");
      trialNote.classList.remove("hidden");
    } else {
      trialNote.classList.add("hidden");
    }

    const sectionStarts = {};
    if (Array.isArray(meta.sections)) {
      meta.sections.forEach((sec) => {
        if (sec && typeof sec === "object") {
          const st = Number(sec.start || sec.q_start);
          const lbl = sec.title || sec.name || sec.label;
          if (st && lbl) sectionStarts[st] = lbl;
        }
      });
    }

    let html = "";
    for (let q = 1; q <= meta.unlocked_q; q++) {
      if (sectionStarts[q]) {
        html += `<div class="bubble-section-head">${esc(sectionStarts[q])}</div>`;
      }
      const chosen = state.quizAnswers[String(q)] || "";
      html += `
        <div class="bubble-row">
          <span class="bubble-qnum">Q${q}</span>
          <div class="bubble-opts">
            ${["A", "B", "C", "D"]
              .map(
                (opt) =>
                  `<button type="button" class="bubble-opt ${chosen === opt ? "selected" : ""}" data-q="${q}" data-opt="${opt}">${opt}</button>`
              )
              .join("")}
          </div>
        </div>
      `;
    }

    const listEl = document.getElementById("quizBubblesList");
    listEl.innerHTML = html;
    updateQuizAnsweredCounter();

    listEl.querySelectorAll(".bubble-opt").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = btn.dataset.q;
        const opt = btn.dataset.opt;
        if (state.quizAnswers[q] === opt) {
          delete state.quizAnswers[q];
        } else {
          state.quizAnswers[q] = opt;
        }
        btn.parentElement.querySelectorAll(".bubble-opt").forEach((b) => {
          b.classList.toggle("selected", state.quizAnswers[q] === b.dataset.opt);
        });
        updateQuizAnsweredCounter();
      });
    });
  }

  function updateQuizAnsweredCounter() {
    if (!state.quizMeta) return;
    const count = Object.keys(state.quizAnswers).length;
    document.getElementById("quizAnsweredCounter").textContent = `${count} / ${state.quizMeta.unlocked_q}`;
  }

  async function submitQuizAnswers() {
    if (!state.quizDocId) return;
    const btn = document.getElementById("btnQuizSubmit");
    btn.disabled = true;
    try {
      const res = await apiFetch(`/api/quiz/${encodeURIComponent(state.quizDocId)}/submit`, {
        method: "POST",
        body: JSON.stringify({ answers: state.quizAnswers }),
      });

      document.getElementById("quizBubblesList").classList.add("hidden");
      document.getElementById("quizSubmitBar").classList.add("hidden");

      const rPane = document.getElementById("quizResultPane");
      rPane.classList.remove("hidden");
      rPane.innerHTML = `
        <div class="quiz-result-summary">
          <div class="meta-line">${esc(t("scoreLabel"))}</div>
          <div class="result-score-big">${res.score} / ${res.total_graded} (${res.percentage}%)</div>
          <div class="btn-row" style="margin-top:10px;">
            <button type="button" id="btnQuizRetake" class="btn btn-primary btn-sm">${esc(t("retakeQuiz"))}</button>
          </div>
        </div>
        <div class="breakdown-grid">
          ${(res.breakdown || [])
            .map(
              (b) => `
            <div class="bd-cell ${b.ok ? "ok" : "miss"}">
              <div><strong>Q${b.q}</strong> ${b.ok ? "OK" : "X"}</div>
              <div>${esc(t("yoursCol"))}: ${esc(b.yours)} | ${esc(t("keyCol"))}: ${esc(b.correct)}</div>
            </div>
          `
            )
            .join("")}
        </div>
      `;
      document.getElementById("btnQuizRetake").addEventListener("click", () => {
        state.quizAnswers = {};
        rPane.classList.add("hidden");
        document.getElementById("quizBubblesList").classList.remove("hidden");
        document.getElementById("quizSubmitBar").classList.remove("hidden");
        renderQuizBubbles();
      });
    } catch (err) {
      showToast(err.message, true);
    } finally {
      btn.disabled = false;
    }
  }

  function closeQuizRunner() {
    setHidden("modalQuiz", true);
    if (state.quizPdfDocObj) {
      try {
        state.quizPdfDocObj.destroy();
      } catch (_) {}
    }
    state.quizPdfDocObj = null;
    state.quizDocId = null;
  }

  // ==================== STUDY PLANS VIEW ====================
  async function renderPlansView() {
    const listEl = document.getElementById("plansList");
    if (!listEl) return;
    if (!state.studyPlans.length) {
      listEl.innerHTML = `<div class="panel-compact"><p class="muted-text">${esc(t("loading"))}</p></div>`;
      try {
        const res = await apiFetch("/api/study-plans");
        state.studyPlans = res.plans || [];
      } catch (err) {
        listEl.innerHTML = `<div class="panel-compact"><p class="error-inline">${esc(err.message)}</p></div>`;
        return;
      }
    }

    const trialNote = document.getElementById("plansTrialNote");
    const isTrial = state.auth && state.auth.tier === "TRIAL";
    if (trialNote) {
      trialNote.textContent = t("plansTrialNote");
      trialNote.classList.toggle("hidden", !isTrial);
    }

    listEl.innerHTML = state.studyPlans
      .map((pl) => {
        const total = pl.tasks.length;
        const doneCount = pl.tasks.filter((tk) => state.progress.plan_progress[tk.id]).length;
        const pct = total ? Math.round((doneCount / total) * 100) : 0;

        return `
          <article class="panel-compact">
            <div class="plan-head">
              <h2 class="h2-section" style="margin:0;">${esc(pl.title)}</h2>
              <span class="meta-line mono-num">${doneCount}/${total} (${pct}%)</span>
            </div>
            <div class="meta-line">${esc([formatGradeLabel(pl.grade), pl.stream].filter(Boolean).join(" · "))}</div>
            <p class="muted-text" style="margin-top:4px;">${esc(pl.description)}</p>
            <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
            <div class="task-list">
              ${pl.tasks
                .map((tk) => {
                  const checked = !!state.progress.plan_progress[tk.id];
                  return `
                    <div class="task-item ${tk.locked ? "task-locked" : ""}">
                      <label class="task-check-label">
                        <input type="checkbox" class="plan-task-cb" data-tid="${esc(tk.id)}" ${checked ? "checked" : ""} ${tk.locked ? "disabled" : ""} />
                        <span class="${checked ? "task-done" : ""}">${esc(tk.label)}</span>
                      </label>
                      ${tk.locked ? `<span class="status-tag is-warn">${esc(t("lockedTask"))}</span>` : ""}
                    </div>
                  `;
                })
                .join("")}
            </div>
          </article>
        `;
      })
      .join("");

    listEl.querySelectorAll(".plan-task-cb").forEach((cb) => {
      cb.addEventListener("change", async () => {
        state.progress.plan_progress[cb.dataset.tid] = cb.checked;
        renderPlansView();
        await saveProgress();
      });
    });

    renderCustomTasks();
  }

  function renderCustomTasks() {
    const cList = document.getElementById("customTaskList");
    if (!cList) return;
    const items = state.progress.custom_plan || [];
    if (!items.length) {
      cList.innerHTML = `<p class="muted-text" style="margin-top:8px;">—</p>`;
      return;
    }

    cList.innerHTML = items
      .map(
        (tk, idx) => `
      <div class="task-item">
        <label class="task-check-label">
          <input type="checkbox" class="custom-cb" data-idx="${idx}" ${tk.done ? "checked" : ""} />
          <span class="${tk.done ? "task-done" : ""}">${esc(tk.text)}</span>
        </label>
        <button type="button" class="btn btn-danger btn-sm custom-del" data-idx="${idx}">${esc(t("deleteBtn"))}</button>
      </div>
    `
      )
      .join("");

    cList.querySelectorAll(".custom-cb").forEach((cb) => {
      cb.addEventListener("change", async () => {
        state.progress.custom_plan[Number(cb.dataset.idx)].done = cb.checked;
        renderCustomTasks();
        await saveProgress();
      });
    });
    cList.querySelectorAll(".custom-del").forEach((btn) => {
      btn.addEventListener("click", async () => {
        state.progress.custom_plan.splice(Number(btn.dataset.idx), 1);
        renderCustomTasks();
        await saveProgress();
      });
    });
  }

  // ==================== PARENT ANALYTICS & REPORTS VIEW ====================
  async function renderParentView() {
    const view = document.getElementById("viewParent");
    if (!view) return;
    if (!state.parentAnalytics) {
      view.innerHTML = `<div class="panel-compact"><p class="muted-text">${esc(t("loading"))}</p></div>`;
      try {
        const res = await apiFetch("/api/parent/analytics");
        state.parentAnalytics = res.children_analytics || [];
      } catch (err) {
        view.innerHTML = `<div class="panel-compact"><p class="error-inline">${esc(err.message)}</p></div>`;
        return;
      }
    }

    const kids = state.parentAnalytics;
    if (!kids.length) {
      view.innerHTML = `<div class="panel-compact"><p class="muted-text">—</p></div>`;
      return;
    }

    if (state.activeChildIdx >= kids.length) state.activeChildIdx = 0;
    const ch = kids[state.activeChildIdx];
    const k = ch.kpis;
    const childReports = (state.auth.reports || []).filter((r) => r.student_id === ch.student_id);

    const maxDay = Math.max(1, ...ch.daily_7d.map((d) => d.count));
    const barW = 28;
    const gap = 14;
    const svgW = ch.daily_7d.length * (barW + gap) + gap;
    const svgBars = ch.daily_7d
      .map((d, i) => {
        const h = Math.round((d.count / maxDay) * 70);
        const x = gap + i * (barW + gap);
        const y = 86 - h;
        return `
          <rect x="${x}" y="${y}" width="${barW}" height="${Math.max(2, h)}" fill="${d.count > 0 ? "#1A4F8B" : "#D6D1C6"}" rx="2"></rect>
          <text x="${x + barW / 2}" y="106" text-anchor="middle" font-size="11" fill="#525C6A" font-family="IBM Plex Mono, monospace">${esc(d.day)}</text>
          <text x="${x + barW / 2}" y="${Math.max(12, y - 5)}" text-anchor="middle" font-size="11" fill="#121923" font-family="IBM Plex Mono, monospace">${d.count}</text>
        `;
      })
      .join("");

    view.innerHTML = `
      ${
        state.auth.sibling_discount
          ? `<div class="notice-bar notice-pass">${esc(t("siblingDiscountNote"))}</div>`
          : ""
      }

      ${
        kids.length > 1
          ? `
        <div class="panel-compact">
          <div class="field-label">${esc(t("childSwitchLabel"))}</div>
          <div class="child-tabs">
            ${kids
              .map(
                (kid, idx) =>
                  `<button type="button" class="btn btn-secondary btn-sm child-switch-btn ${idx === state.activeChildIdx ? "active" : ""}" data-idx="${idx}">${esc(
                    kid.student_name
                  )} (${esc(formatGradeLabel(kid.grade))})</button>`
              )
              .join("")}
          </div>
        </div>
      `
          : ""
      }

      <div class="panel-compact">
        <div class="ledger-row-head">
          <div>
            <h2 class="h2-section" style="margin:0;">${esc(ch.student_name)}</h2>
            <div class="doc-meta">${esc(formatGradeLabel(ch.grade))} · ${esc(ch.format)}${ch.stream && ch.stream !== "General" ? " · " + esc(ch.stream) : ""}</div>
          </div>
          <span class="status-tag ${ch.is_linked ? "is-pass" : "is-warn"}">${esc(ch.is_linked ? t("linkedTag") : t("sharedPhoneTag"))}</span>
        </div>
        ${
          !ch.is_linked && ch.invite_url
            ? `
          <div class="notice-bar notice-info" style="margin-top:10px; margin-bottom:0;">
            <p style="margin:0 0 8px 0;">${esc(t("notLinkedNote"))}</p>
            <div class="btn-row">
              <button type="button" class="btn btn-primary btn-sm" id="btnCopyChildInv">${esc(t("copyInvite"))}</button>
              <a class="btn btn-secondary btn-sm" target="_blank" href="https://t.me/share/url?url=${encodeURIComponent(ch.invite_url)}">${esc(t("shareTg"))}</a>
            </div>
          </div>
        `
            : ""
        }
      </div>

      <div class="kpi-ledger">
        <div class="kpi-cell">
          <div class="kpi-value">${k.pdfs_opened}</div>
          <div class="kpi-label">${esc(t("kpiPdfs"))}</div>
          <div class="kpi-sub">${k.total_views} ${esc(t("kpiViews"))}</div>
        </div>
        <div class="kpi-cell">
          <div class="kpi-value">${k.quizzes_taken}</div>
          <div class="kpi-label">${esc(t("kpiQuizzes"))}</div>
          <div class="kpi-sub">${k.avg_quiz_pct != null ? `${t("kpiAvg")}: ${k.avg_quiz_pct}%` : "—"}</div>
        </div>
        <div class="kpi-cell">
          <div class="kpi-value">${k.plan_pct}%</div>
          <div class="kpi-label">${esc(t("kpiPlan"))}</div>
          <div class="kpi-sub">${k.plan_done}/${k.plan_total} ${esc(t("doneLabel"))}</div>
        </div>
        <div class="kpi-cell">
          <div class="kpi-value">${k.offline_saved}</div>
          <div class="kpi-label">${esc(t("kpiSaved"))}</div>
          <div class="kpi-sub">${k.bookmarks_count} ${esc(t("kpiBookmarks"))}</div>
        </div>
      </div>

      <div class="panel-compact">
        <h3 class="h3-sub">${esc(t("chart7d"))}</h3>
        <div class="chart-wrap">
          <svg class="activity-svg" viewBox="0 0 ${svgW} 120" preserveAspectRatio="xMidYMid meet">
            <line x1="0" y1="86" x2="${svgW}" y2="86" stroke="#D6D1C6" stroke-width="1" />
            ${svgBars}
          </svg>
        </div>
      </div>

      <div class="panel-compact">
        <h3 class="h3-sub">${esc(t("quizTrendTitle"))}</h3>
        ${
          ch.quiz_trend.length
            ? `
          <table class="data-table">
            <thead><tr><th>Quiz</th><th>${esc(t("subjCol"))}</th><th>${esc(t("scoreLabel"))}</th></tr></thead>
            <tbody>
              ${ch.quiz_trend
                .map(
                  (q) =>
                    `<tr><td>${esc(q.label)}</td><td>${esc(q.subject)}</td><td class="mono-num">${esc(q.score_text)}</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        `
            : `<p class="muted-text">${esc(t("noQuizzesYet"))}</p>`
        }
      </div>

      ${
        ch.subject_stats.length
          ? `
        <div class="panel-compact">
          <h3 class="h3-sub">${esc(t("subjBreakdownTitle"))}</h3>
          <table class="data-table">
            <thead><tr><th>${esc(t("subjCol"))}</th><th>${esc(t("viewsCol"))}</th><th>${esc(t("quizzesCol"))}</th><th>${esc(t("avgCol"))}</th></tr></thead>
            <tbody>
              ${ch.subject_stats
                .map(
                  (s) =>
                    `<tr><td>${esc(s.subject)}</td><td class="mono-num">${s.views}</td><td class="mono-num">${s.quizzes}</td><td class="mono-num">${
                      s.avg_pct != null ? s.avg_pct + "%" : "—"
                    }</td></tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `
          : ""
      }

      ${
        ch.recent_reads.length
          ? `
        <div class="panel-compact">
          <h3 class="h3-sub">${esc(t("recentActivityTitle"))}</h3>
          <div class="compact-list">
            ${ch.recent_reads
              .map(
                (r) =>
                  `<div class="compact-row"><span class="doc-title">${esc(r.file_name)}</span><span class="meta-line mono-num">${esc(t("pageWord"))} ${r.page}</span></div>`
              )
              .join("")}
          </div>
        </div>
      `
          : ""
      }

      <div class="panel-compact">
        <h3 class="h3-sub">${esc(t("biweeklyReportsTitle"))}</h3>
        ${
          childReports.length
            ? `<div class="stack-gap">${childReports
                .map(
                  (rp) => `
                <article class="report-block">
                  <div class="ledger-row-head">
                    <strong>${esc(rp.period)}</strong>
                    <span class="meta-line">${esc(rp.tutor_name || "")}</span>
                  </div>
                  <div class="report-grid">
                    <div><strong>${esc(t("attendanceLbl"))}:</strong> ${esc(rp.attendance)}</div>
                    <div><strong>${esc(t("scoresLbl"))}:</strong> ${esc(rp.scores_text)}</div>
                    <div><strong>${esc(t("improvedLbl"))}:</strong> ${esc(rp.improved_note)}</div>
                    <div><strong>${esc(t("focusLbl"))}:</strong> ${esc(rp.focus_note)}</div>
                  </div>
                </article>
              `
                )
                .join("")}</div>`
            : `<p class="muted-text">${esc(t("noReportsYet"))}</p>`
        }
      </div>
    `;

    view.querySelectorAll(".child-switch-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeChildIdx = Number(btn.dataset.idx);
        renderParentView();
      });
    });

    const copyBtn = document.getElementById("btnCopyChildInv");
    if (copyBtn && ch.invite_url) {
      copyBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(ch.invite_url);
          showToast(t("copied"));
        } catch (_) {}
      });
    }
  }

  // ==================== ACCOUNT & SQUAD VIEW ====================
  function renderAccountView() {
    const a = state.auth;
    const view = document.getElementById("viewAccount");
    if (!view || !a) return;
    const statusClass =
      a.status === "APPROVED" ? "is-pass" : a.status === "EXPIRED" || a.status === "LEFT" ? "is-rubric" : "is-warn";

    const botUser = a.bot_username || "";
    const inviteLink = botUser && a.referral_code ? `https://t.me/${botUser}?start=ref_${a.referral_code}` : "";

    view.innerHTML = `
      <div class="panel-compact">
        <h2 class="h2-section">${esc(t("accountTitle"))}</h2>
        <table class="data-table">
          <tbody>
            <tr><th>${esc(t("nameLbl"))}</th><td>${esc(a.name)}</td></tr>
            <tr><th>${esc(t("roleLbl"))}</th><td>${esc(a.role === "parent" ? t("roleParent") : t("roleStudent"))}</td></tr>
            <tr><th>${esc(t("gradeWord"))}</th><td>${esc(formatGradeLabel(a.grade))}${a.stream && a.stream !== "General" ? " (" + esc(a.stream) + ")" : ""}</td></tr>
            <tr><th>${esc(t("statusLbl"))}</th><td><span class="status-tag ${statusClass}">${esc(a.status)}</span></td></tr>
            <tr><th>${esc(t("tierLbl"))}</th><td><span class="mono-num">${esc(a.tier)}</span></td></tr>
            ${
              a.days_left != null
                ? `<tr><th>${esc(t("daysRemainLbl"))}</th><td class="mono-num">${a.days_left}</td></tr>`
                : ""
            }
          </tbody>
        </table>
      </div>

      ${
        a.children && a.children.length
          ? `
        <div class="panel-compact">
          <h2 class="h2-section">${esc(t("childrenSectionTitle"))}</h2>
          <div class="compact-list">
            ${a.children
              .map(
                (ch) => `
              <div class="compact-row">
                <div>
                  <div class="doc-title">${esc(ch.student_name)}</div>
                  <div class="doc-meta">${esc(formatGradeLabel(ch.grade))} · ${esc(ch.format)}</div>
                </div>
                <span class="status-tag ${ch.is_linked ? "is-pass" : "is-warn"}">${esc(ch.is_linked ? t("linkedTag") : t("sharedPhoneTag"))}</span>
              </div>
            `
              )
              .join("")}
          </div>
        </div>
      `
          : ""
      }

      ${
        a.referral_code
          ? `
        <div class="panel-compact">
          <h2 class="h2-section">${esc(t("squadTitle"))}</h2>
          <p class="muted-text" style="margin-bottom:10px;">${esc(t("squadDesc"))}</p>
          <table class="data-table" style="margin-bottom:10px;">
            <tbody>
              <tr><th>${esc(t("yourCode"))}</th><td class="mono-num"><strong>${esc(a.referral_code)}</strong></td></tr>
              <tr><th>${esc(t("verifiedRefs"))}</th><td class="mono-num">${a.referral_count || 0}</td></tr>
            </tbody>
          </table>
          <div class="btn-row">
            <button type="button" id="btnCopyRefCode" class="btn btn-primary btn-sm">${esc(t("copyCode"))}</button>
            ${
              inviteLink
                ? `<a class="btn btn-secondary btn-sm" target="_blank" href="https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${encodeURIComponent(
                    "Join Qelal Learning (Bishoftu) with my Study Squad code: " + a.referral_code
                  )}">${esc(t("shareTg"))}</a>`
                : ""
            }
          </div>
        </div>
      `
          : ""
      }

      <div class="panel-compact">
        <h2 class="h2-section">${esc(t("supportTitle"))}</h2>
        <div class="btn-row">
          <a href="tel:+251933510682" class="btn btn-secondary btn-sm">+251 933 510 682</a>
          <a href="tel:+251988666328" class="btn btn-secondary btn-sm">+251 988 666 328</a>
        </div>
      </div>
    `;

    const refBtn = document.getElementById("btnCopyRefCode");
    if (refBtn) {
      refBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(a.referral_code);
          showToast(t("copied"));
        } catch (_) {}
      });
    }
  }

  // ==================== ADMIN CONSOLE VIEW ====================
  function stopAdminJobPolling() {
    if (state.adminPollTimer) {
      clearInterval(state.adminPollTimer);
      state.adminPollTimer = null;
    }
  }

  function renderAdminJobsBox(jobs) {
    const box = document.getElementById("adminJobsBox");
    if (!box) return;
    const sync = (jobs && jobs.sync) || {};
    const reclassify = (jobs && jobs.reclassify) || {};
    const verify = (jobs && jobs.verify) || {};

    const tagFor = (j) => (j.running ? "is-warn" : j.ok === false ? "is-rubric" : j.ok === true ? "is-pass" : "");
    const labelFor = (j) => (j.running ? "RUNNING" : j.ok === false ? "FAILED" : j.ok === true ? "DONE" : "IDLE");

    box.innerHTML = `
      <div class="compact-list">
        <div class="compact-row">
          <div style="min-width:0;">
            <div class="doc-title">Google Drive Sync</div>
            <div class="doc-meta">${esc(sync.running ? sync.message || "Running..." : sync.last_summary || sync.message || "Idle")}${sync.updated_at ? " · " + esc(sync.updated_at) : ""}</div>
          </div>
          <span class="status-tag ${tagFor(sync)}">${labelFor(sync)}</span>
        </div>
        <div class="compact-row">
          <div style="min-width:0;">
            <div class="doc-title">PDF Re-Classify</div>
            <div class="doc-meta">${esc(reclassify.running ? reclassify.message || "Running..." : reclassify.last_summary || reclassify.message || "Idle")}${reclassify.updated_at ? " · " + esc(reclassify.updated_at) : ""}</div>
          </div>
          <span class="status-tag ${tagFor(reclassify)}">${labelFor(reclassify)}</span>
        </div>
        <div class="compact-row">
          <div style="min-width:0;">
            <div class="doc-title">PDF Link Verification</div>
            <div class="doc-meta">${esc(verify.running ? verify.message || "Running..." : verify.last_summary || verify.message || "Idle")}${verify.updated_at ? " · " + esc(verify.updated_at) : ""}</div>
          </div>
          <span class="status-tag ${tagFor(verify)}">${labelFor(verify)}</span>
        </div>
      </div>
    `;

    const btnSync = document.getElementById("btnAdminSyncDrive");
    const btnReclass = document.getElementById("btnAdminReclassify");
    const btnVerify = document.getElementById("btnAdminVerifyLinks");
    const btnForce = document.getElementById("btnAdminForceVerify");
    if (btnSync) btnSync.disabled = !!sync.running;
    if (btnReclass) btnReclass.disabled = !!reclassify.running;
    if (btnVerify) btnVerify.disabled = !!verify.running;
    if (btnForce) btnForce.disabled = !!verify.running;
  }

  function startAdminJobPolling() {
    if (state.adminPollTimer) return;
    state.adminPollTimer = setInterval(async () => {
      if (state.activeTab !== "admin") {
        stopAdminJobPolling();
        return;
      }
      try {
        const res = await apiFetch("/api/admin/job-status");
        const jobs = res.jobs || {};
        const prevSync = !!(state.adminOverview && state.adminOverview.jobs && state.adminOverview.jobs.sync && state.adminOverview.jobs.sync.running);
        const prevReclass = !!(state.adminOverview && state.adminOverview.jobs && state.adminOverview.jobs.reclassify && state.adminOverview.jobs.reclassify.running);
        const prevVerify = !!(state.adminOverview && state.adminOverview.jobs && state.adminOverview.jobs.verify && state.adminOverview.jobs.verify.running);
        if (state.adminOverview) {
          state.adminOverview.jobs = jobs;
        }
        renderAdminJobsBox(jobs);

        const nowRunning =
          !!(jobs.sync && jobs.sync.running) ||
          !!(jobs.reclassify && jobs.reclassify.running) ||
          !!(jobs.verify && jobs.verify.running);
        if (!nowRunning) {
          stopAdminJobPolling();
          if (prevSync || prevReclass || prevVerify) {
            await renderAdminView(true);
            await loadLibrary(false);
          }
        }
      } catch (_) {}
    }, 4500);
  }

  function renderAdminAccountsList() {
    const listEl = document.getElementById("admAccountsList");
    const headEl = document.getElementById("admAccountsCount");
    if (!listEl || !state.adminOverview) return;

    const regs = (state.adminOverview.registrations || []).filter((r) => {
      if (state.adminAccountFilter !== "ALL" && r.status !== state.adminAccountFilter) return false;
      if (state.adminAccountSearch) {
        const hay = `${r.name} ${r.phone} ${r.grade} ${r.referral_code}`.toLowerCase();
        if (!hay.includes(state.adminAccountSearch.toLowerCase())) return false;
      }
      return true;
    });

    if (headEl) headEl.textContent = `${esc(t("adminAccountsTitle"))} (${regs.length})`;

    listEl.innerHTML = regs.length
      ? regs
          .map(
            (r) => `
          <div class="ledger-row">
            <div class="ledger-row-head">
              <div>
                <div class="doc-title">${esc(r.name)} <span class="meta-line">(${esc(r.role)})</span></div>
                <div class="doc-meta">${esc(r.grade)} · ${esc(r.phone)} · M${r.months_paid || 0} ${r.expires_on ? "· Exp " + esc(r.expires_on) : ""}</div>
              </div>
              <span class="status-tag ${r.status === "APPROVED" ? "is-pass" : r.status === "NEW" ? "is-warn" : "is-rubric"}">${esc(r.status)}</span>
            </div>
            <div class="btn-row">
              ${
                r.status === "NEW"
                  ? `<button type="button" class="btn btn-primary btn-sm adm-act-btn" data-tg="${esc(r.tg_id)}" data-act="approve">${esc(t("approve30d"))}</button>`
                  : `<button type="button" class="btn btn-primary btn-sm adm-act-btn" data-tg="${esc(r.tg_id)}" data-act="mark_paid">${esc(t("renew30d"))}</button>`
              }
              <button type="button" class="btn btn-secondary btn-sm adm-act-btn" data-tg="${esc(r.tg_id)}" data-act="mark_left">${esc(t("markLeft"))}</button>
              <button type="button" class="btn btn-danger btn-sm adm-act-btn" data-tg="${esc(r.tg_id)}" data-act="reject">${esc(t("rejectBtn"))}</button>
            </div>
          </div>
        `
          )
          .join("")
      : `<div class="ledger-row"><p class="muted-text">—</p></div>`;

    listEl.querySelectorAll(".adm-act-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await apiFetch("/api/admin/student-action", {
            method: "POST",
            body: JSON.stringify({ tg_id: btn.dataset.tg, action: btn.dataset.act }),
          });
          showToast(t("actionDone"));
          await renderAdminView(true);
        } catch (err) {
          showToast(err.message, true);
          btn.disabled = false;
        }
      });
    });
  }

  function renderAdminPdfsList() {
    const listEl = document.getElementById("admPdfsList");
    const headEl = document.getElementById("admPdfsCount");
    const moreWrap = document.getElementById("admPdfsMoreWrap");
    if (!listEl || !state.adminOverview) return;

    const allPdfs = state.adminOverview.pdfs || [];
    const filtered = allPdfs.filter((p) => {
      if (state.adminPdfFilter === "VERIFIED") {
        if (p.link_status !== "AUTO_VERIFIED" && p.link_status !== "MANUAL_VERIFIED") return false;
      } else if (state.adminPdfFilter === "NEEDS_REVIEW") {
        if (p.link_status !== "NEEDS_REVIEW") return false;
      } else if (state.adminPdfFilter === "REJECTED") {
        if (p.link_status !== "REJECTED_MISMATCH") return false;
      } else if (state.adminPdfFilter === "UNVERIFIED") {
        if (p.link_status && p.link_status !== "UNVERIFIED") return false;
      } else if (state.adminPdfFilter === "HAS_QUIZ") {
        if (!p.has_quiz) return false;
      } else if (state.adminPdfFilter === "TRIAL_PICK") {
        if (!p.is_trial) return false;
      }

      if (state.adminPdfSearch) {
        const hay = `${p.doc_id} ${p.file_name} ${p.grade} ${p.subject} ${p.category} ${p.link_status}`.toLowerCase();
        if (!hay.includes(state.adminPdfSearch.toLowerCase())) return false;
      }
      return true;
    });

    if (headEl) headEl.textContent = `${esc(t("adminPdfTitle"))} (${filtered.length})`;

    const shown = filtered.slice(0, state.adminPdfLimit);
    listEl.innerHTML = shown.length
      ? shown
          .map((p) => {
            const st = p.link_status || "UNVERIFIED";
            const tagClass =
              st === "AUTO_VERIFIED" || st === "MANUAL_VERIFIED"
                ? "is-pass"
                : st === "NEEDS_REVIEW"
                ? "is-warn"
                : st === "REJECTED_MISMATCH"
                ? "is-rubric"
                : "";
            const metaLine = [
              p.doc_id,
              p.grade,
              p.subject,
              p.category,
              p.file_size_mb ? `${p.file_size_mb} MB` : "",
              p.source,
              p.has_quiz ? `Quiz ${p.quiz_total_q}Q` : "",
            ]
              .filter(Boolean)
              .join(" · ");
            const linkLine = p.linked_doc_id
              ? `<div class="doc-meta">Linked: ${esc(p.linked_doc_id)}${p.linked_file_name ? " — " + esc(p.linked_file_name) : ""}</div>`
              : "";

            return `
              <div class="ledger-row">
                <div class="ledger-row-head">
                  <div style="min-width:0;">
                    <div class="doc-title">${esc(p.file_name)}</div>
                    <div class="doc-meta">${esc(metaLine)}</div>
                    ${linkLine}
                  </div>
                  <span class="status-tag ${tagClass}">${esc(st)}</span>
                </div>
                <div class="btn-row">
                  <button type="button" class="btn btn-secondary btn-sm adm-pdf-trial ${p.is_trial ? "active" : ""}" data-doc="${esc(p.doc_id)}" data-trial="${p.is_trial ? "1" : "0"}">${esc(
                    p.is_trial ? t("isTrialPick") : t("setTrialPick")
                  )}</button>
                  ${
                    p.linked_doc_id && st === "NEEDS_REVIEW"
                      ? `<button type="button" class="btn btn-primary btn-sm adm-pdf-link" data-doc="${esc(p.doc_id)}" data-act="confirm">${esc(t("confirmLinkBtn"))}</button>
                         <button type="button" class="btn btn-danger btn-sm adm-pdf-link" data-doc="${esc(p.doc_id)}" data-act="unlink">${esc(t("unlinkBtn"))}</button>`
                      : p.linked_doc_id
                      ? `<button type="button" class="btn btn-danger btn-sm adm-pdf-link" data-doc="${esc(p.doc_id)}" data-act="unlink">${esc(t("unlinkBtn"))}</button>`
                      : ""
                  }
                </div>
              </div>
            `;
          })
          .join("")
      : `<div class="ledger-row"><p class="muted-text">—</p></div>`;

    if (moreWrap) {
      if (filtered.length > shown.length) {
        moreWrap.innerHTML = `<button type="button" id="btnAdmPdfsMore" class="btn btn-secondary btn-sm">${esc(t("showMoreBtn"))} (${filtered.length - shown.length})</button>`;
        document.getElementById("btnAdmPdfsMore").addEventListener("click", () => {
          state.adminPdfLimit += 40;
          renderAdminPdfsList();
        });
      } else {
        moreWrap.innerHTML = "";
      }
    }

    listEl.querySelectorAll(".adm-pdf-trial").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          const nextTrial = btn.dataset.trial !== "1";
          await apiFetch("/api/admin/toggle-trial", {
            method: "POST",
            body: JSON.stringify({ doc_id: btn.dataset.doc, is_trial: nextTrial }),
          });
          showToast(t("actionDone"));
          await renderAdminView(true);
          await loadLibrary(false);
        } catch (err) {
          showToast(err.message, true);
          btn.disabled = false;
        }
      });
    });

    listEl.querySelectorAll(".adm-pdf-link").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await apiFetch("/api/admin/link-action", {
            method: "POST",
            body: JSON.stringify({ doc_id: btn.dataset.doc, action: btn.dataset.act }),
          });
          showToast(t("actionDone"));
          await renderAdminView(true);
          await loadLibrary(false);
        } catch (err) {
          showToast(err.message, true);
          btn.disabled = false;
        }
      });
    });
  }

  async function renderAdminView(forceReload = false) {
    const view = document.getElementById("viewAdmin");
    if (!view) return;
    if (!state.adminOverview || forceReload) {
      view.innerHTML = `<div class="panel-compact"><p class="muted-text">${esc(t("loading"))}</p></div>`;
      try {
        const url = forceReload ? "/api/admin/overview?refresh=true" : "/api/admin/overview";
        state.adminOverview = await apiFetch(url);
      } catch (err) {
        view.innerHTML = `<div class="panel-compact"><p class="error-inline">${esc(err.message)}</p></div>`;
        return;
      }
    }

    const ov = state.adminOverview;
    const sum = ov.summary || {};
    const cfg = ov.config || {};
    const jobs = ov.jobs || {};

    const pdfFilterTabs = [
      { id: "ALL", label: `ALL (${sum.total_pdfs || 0})` },
      { id: "VERIFIED", label: `VERIFIED (${sum.verified_links || 0})` },
      { id: "NEEDS_REVIEW", label: `REVIEW (${sum.needs_review || 0})` },
      { id: "REJECTED", label: `REJECTED (${sum.rejected_links || 0})` },
      { id: "UNVERIFIED", label: `UNVERIFIED (${sum.unverified_links || 0})` },
      { id: "HAS_QUIZ", label: `QUIZ (${sum.quiz_keys || 0})` },
      { id: "TRIAL_PICK", label: `TRIAL (${sum.trial_picks || 0})` },
    ];

    view.innerHTML = `
      <div class="kpi-ledger">
        <div class="kpi-cell"><div class="kpi-value">${sum.APPROVED || 0}</div><div class="kpi-label">Approved</div></div>
        <div class="kpi-cell"><div class="kpi-value">${sum.NEW || 0}</div><div class="kpi-label">Pending NEW</div></div>
        <div class="kpi-cell"><div class="kpi-value">${sum.total_students || 0}</div><div class="kpi-label">Students</div></div>
        <div class="kpi-cell"><div class="kpi-value">${sum.total_pdfs || 0}</div><div class="kpi-label">PDFs (${sum.quiz_keys || 0} keys)</div></div>
      </div>

      <section class="admin-section">
        <div class="ledger-row-head">
          <h2 class="h2-section" style="margin:0;">${esc(t("adminSyncTitle"))}</h2>
          <button type="button" id="btnAdminRefreshAll" class="btn btn-secondary btn-sm">${esc(t("refreshAdminBtn"))}</button>
        </div>
        <div id="adminJobsBox"></div>
        <div class="btn-row">
          <button type="button" id="btnAdminSyncDrive" class="btn btn-primary btn-sm">${esc(t("syncDriveBtn"))}</button>
          <button type="button" id="btnAdminReclassify" class="btn btn-secondary btn-sm">${esc(t("reclassifyBtn"))}</button>
          <button type="button" id="btnAdminVerifyLinks" class="btn btn-primary btn-sm">${esc(t("verifyLinksBtn"))}</button>
          <button type="button" id="btnAdminForceVerify" class="btn btn-secondary btn-sm">${esc(t("forceVerifyBtn"))}</button>
        </div>
      </section>

      <section class="admin-section">
        <h2 id="admPdfsCount" class="h2-section" style="margin:0;">${esc(t("adminPdfTitle"))} (${sum.total_pdfs || 0})</h2>
        <div class="btn-row">
          ${pdfFilterTabs
            .map(
              (tb) =>
                `<button type="button" class="btn btn-secondary btn-sm adm-pdf-filter-btn ${state.adminPdfFilter === tb.id ? "active" : ""}" data-pf="${tb.id}">${esc(tb.label)}</button>`
            )
            .join("")}
        </div>
        <input id="admPdfSearchInput" type="search" class="input" placeholder="Search DOC-ID, file name, grade, subject..." value="${esc(state.adminPdfSearch)}" />
        <div id="admPdfsList" class="ledger-list"></div>
        <div id="admPdfsMoreWrap" style="margin-top:8px;"></div>
      </section>

      <section class="admin-section">
        <h2 class="h2-section" style="margin:0;">${esc(t("adminConfigTitle"))}</h2>
        <div class="form-row-2">
          <div class="field-group" style="margin:0;">
            <label class="field-label">Launch Mode</label>
            <select id="admCfgMode" class="select">
              <option value="OPEN_LAUNCH" ${cfg.LAUNCH_MODE === "OPEN_LAUNCH" ? "selected" : ""}>OPEN_LAUNCH</option>
              <option value="PAID_GATED" ${cfg.LAUNCH_MODE === "PAID_GATED" ? "selected" : ""}>PAID_GATED</option>
            </select>
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Grade 12 Matric Date</label>
            <input id="admCfgMatric" type="date" class="input" value="${esc(cfg.MATRIC_DATE || "")}" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Grade 8 Ministry Date</label>
            <input id="admCfgG8" type="date" class="input" value="${esc(cfg.GRADE8_MINISTRY_DATE || "")}" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Grade 6 Ministry Date</label>
            <input id="admCfgG6" type="date" class="input" value="${esc(cfg.GRADE6_MINISTRY_DATE || "")}" />
          </div>
        </div>
        <div class="field-group" style="margin:0;">
          <label class="field-label">Semester Target Date</label>
          <input id="admCfgSem" type="date" class="input" value="${esc(cfg.SEMESTER_DATE || "")}" />
        </div>
        <div>
          <button type="button" id="btnSaveAdminCfg" class="btn btn-primary btn-sm">${esc(t("saveConfig"))}</button>
        </div>
      </section>

      <section class="admin-section">
        <h2 class="h2-section" style="margin:0;">${esc(t("adminPublishTitle"))}</h2>
        <div class="form-row-2">
          <div class="field-group" style="margin:0;">
            <label class="field-label">Student</label>
            <select id="admRptStudent" class="select">
              ${(ov.students || [])
                .map((s) => `<option value="${esc(s.student_id)}">${esc(s.student_name)} (${esc(s.grade)})</option>`)
                .join("")}
            </select>
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Period</label>
            <input id="admRptPeriod" type="text" class="input" placeholder="e.g. Week 1–2" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Attendance</label>
            <input id="admRptAtt" type="text" class="input" placeholder="e.g. 4/4 sessions" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Tutor</label>
            <input id="admRptTutor" type="text" class="input" value="Qelal Coordinator" />
          </div>
        </div>
        <div class="field-group" style="margin:0;">
          <label class="field-label">Diagnostic &amp; Quiz Scores</label>
          <input id="admRptScores" type="text" class="input" placeholder="e.g. Math 84%, Physics 78%" />
        </div>
        <div class="form-row-2">
          <div class="field-group" style="margin:0;">
            <label class="field-label">What Improved</label>
            <input id="admRptImproved" type="text" class="input" />
          </div>
          <div class="field-group" style="margin:0;">
            <label class="field-label">Next 2-Week Focus</label>
            <input id="admRptFocus" type="text" class="input" />
          </div>
        </div>
        <div>
          <button type="button" id="btnAdminPubReport" class="btn btn-primary btn-sm">${esc(t("publishReportBtn"))}</button>
        </div>
      </section>

      <section class="admin-section">
        <h2 class="h2-section" style="margin:0;">${esc(t("adminBroadcastTitle"))}</h2>
        <div class="field-group" style="margin:0;">
          <label class="field-label">Target Audience</label>
          <select id="admBcTarget" class="select">
            <option value="all">All Registered Accounts</option>
            <option value="parents">All Parents</option>
            <option value="approved">Approved Accounts</option>
            <option value="new">Pending (NEW) Accounts</option>
            <option value="natural">Natural Science Students</option>
            <option value="social">Social Science Students</option>
            <option value="grade_12">Grade 12</option>
            <option value="grade_8">Grade 8</option>
            <option value="grade_6">Grade 6</option>
          </select>
        </div>
        <textarea id="admBcMsg" class="textarea" placeholder="Write announcement message..."></textarea>
        <div>
          <button type="button" id="btnAdminBroadcast" class="btn btn-primary btn-sm">${esc(t("sendBroadcastBtn"))}</button>
        </div>
      </section>

      <section class="admin-section">
        <h2 id="admAccountsCount" class="h2-section" style="margin:0;">${esc(t("adminAccountsTitle"))}</h2>
        <div class="btn-row">
          ${["ALL", "NEW", "APPROVED", "EXPIRED", "LEFT"]
            .map(
              (st) =>
                `<button type="button" class="btn btn-secondary btn-sm adm-filter-btn ${state.adminAccountFilter === st ? "active" : ""}" data-st="${st}">${st}</button>`
            )
            .join("")}
        </div>
        <input id="admSearchInput" type="search" class="input" placeholder="Filter by name, phone, grade..." value="${esc(state.adminAccountSearch)}" />
        <div id="admAccountsList" class="ledger-list"></div>
      </section>
    `;

    renderAdminJobsBox(jobs);
    renderAdminPdfsList();
    renderAdminAccountsList();

    if ((jobs.sync && jobs.sync.running) || (jobs.reclassify && jobs.reclassify.running) || (jobs.verify && jobs.verify.running)) {
      startAdminJobPolling();
    } else {
      stopAdminJobPolling();
    }

    document.getElementById("btnAdminRefreshAll").addEventListener("click", () => renderAdminView(true));

    document.getElementById("btnAdminSyncDrive").addEventListener("click", async () => {
      try {
        const res = await apiFetch("/api/admin/sync-drive", { method: "POST" });
        if (res.jobs) {
          state.adminOverview.jobs = res.jobs;
          renderAdminJobsBox(res.jobs);
        }
        startAdminJobPolling();
        showToast(res.already_running ? res.detail : "Google Drive sync started...");
      } catch (err) {
        showToast(err.message, true);
      }
    });

    document.getElementById("btnAdminReclassify").addEventListener("click", async () => {
      try {
        const res = await apiFetch("/api/admin/reclassify-library", { method: "POST" });
        if (res.jobs) {
          state.adminOverview.jobs = res.jobs;
          renderAdminJobsBox(res.jobs);
        }
        startAdminJobPolling();
        showToast(res.already_running ? res.detail : "Re-classifying PDFs...");
      } catch (err) {
        showToast(err.message, true);
      }
    });

    const triggerVerify = async (force) => {
      try {
        const res = await apiFetch("/api/admin/verify-links", {
          method: "POST",
          body: JSON.stringify({ force }),
        });
        if (res.jobs) {
          state.adminOverview.jobs = res.jobs;
          renderAdminJobsBox(res.jobs);
        }
        startAdminJobPolling();
        showToast(res.already_running ? res.detail : "PDF verification started...");
      } catch (err) {
        showToast(err.message, true);
      }
    };
    document.getElementById("btnAdminVerifyLinks").addEventListener("click", () => triggerVerify(false));
    document.getElementById("btnAdminForceVerify").addEventListener("click", () => triggerVerify(true));

    view.querySelectorAll(".adm-pdf-filter-btn").forEach((b) => {
      b.addEventListener("click", () => {
        state.adminPdfFilter = b.dataset.pf;
        state.adminPdfLimit = 40;
        view.querySelectorAll(".adm-pdf-filter-btn").forEach((x) =>
          x.classList.toggle("active", x.dataset.pf === state.adminPdfFilter)
        );
        renderAdminPdfsList();
      });
    });

    document.getElementById("admPdfSearchInput").addEventListener("input", (e) => {
      state.adminPdfSearch = e.target.value;
      state.adminPdfLimit = 40;
      renderAdminPdfsList();
    });

    document.getElementById("btnSaveAdminCfg").addEventListener("click", async () => {
      try {
        await apiFetch("/api/admin/config", {
          method: "POST",
          body: JSON.stringify({
            LAUNCH_MODE: document.getElementById("admCfgMode").value,
            MATRIC_DATE: document.getElementById("admCfgMatric").value,
            GRADE8_MINISTRY_DATE: document.getElementById("admCfgG8").value,
            GRADE6_MINISTRY_DATE: document.getElementById("admCfgG6").value,
            SEMESTER_DATE: document.getElementById("admCfgSem").value,
          }),
        });
        showToast(t("actionDone"));
        await authenticate();
      } catch (err) {
        showToast(err.message, true);
      }
    });

    document.getElementById("btnAdminPubReport").addEventListener("click", async () => {
      try {
        await apiFetch("/api/admin/publish-report", {
          method: "POST",
          body: JSON.stringify({
            student_id: document.getElementById("admRptStudent").value,
            period: document.getElementById("admRptPeriod").value,
            attendance: document.getElementById("admRptAtt").value,
            scores_text: document.getElementById("admRptScores").value,
            improved_note: document.getElementById("admRptImproved").value,
            focus_note: document.getElementById("admRptFocus").value,
            tutor_name: document.getElementById("admRptTutor").value,
          }),
        });
        showToast(t("actionDone"));
        document.getElementById("admRptScores").value = "";
        document.getElementById("admRptImproved").value = "";
        document.getElementById("admRptFocus").value = "";
      } catch (err) {
        showToast(err.message, true);
      }
    });

    document.getElementById("btnAdminBroadcast").addEventListener("click", async () => {
      const target = document.getElementById("admBcTarget").value;
      const message = document.getElementById("admBcMsg").value.trim();
      if (!message) return;
      try {
        const res = await apiFetch("/api/admin/broadcast", {
          method: "POST",
          body: JSON.stringify({ target, message }),
        });
        document.getElementById("admBcMsg").value = "";
        showToast(`Sent: ${res.sent} | Failed: ${res.failed}`);
      } catch (err) {
        showToast(err.message, true);
      }
    });

    view.querySelectorAll(".adm-filter-btn").forEach((b) => {
      b.addEventListener("click", () => {
        state.adminAccountFilter = b.dataset.st;
        view.querySelectorAll(".adm-filter-btn").forEach((x) =>
          x.classList.toggle("active", x.dataset.st === state.adminAccountFilter)
        );
        renderAdminAccountsList();
      });
    });

    document.getElementById("admSearchInput").addEventListener("input", (e) => {
      state.adminAccountSearch = e.target.value;
      renderAdminAccountsList();
    });
  }

  // ==================== LEGAL MODALS ====================
  function openLegalModal(kind) {
    const titleEl = document.getElementById("legalModalTitle");
    const bodyEl = document.getElementById("legalModalBody");
    if (!titleEl || !bodyEl) return;

    if (kind === "terms") {
      titleEl.textContent = t("legalTerms");
      bodyEl.innerHTML = `
        <h3>1. Program Scope &amp; Tuition</h3>
        <p>Qelal Learning (ቀላል) operates weekend exam preparation cohorts, 1-on-1 home tutoring in Bishoftu, and the Qelal Digital Study Hub inside Telegram for Grades 1–12. Monthly tuition for in-person programs is payable upfront prior to the first session of each 30-day cycle.</p>
        <h3>2. Digital Access &amp; Copyright</h3>
        <p>Study materials, unit notes, and answer keys inside the Qelal Digital Study Hub are licensed solely for personal study by registered Qelal students and parents. Forwarding, reselling, or mass-distributing protected documents is prohibited.</p>
        <h3>3. First-Session Fit Guarantee</h3>
        <p>For 1-on-1 home tutoring, if the assigned mentor is not the right learning fit after the first session, Qelal Learning will rematch the student with another vetted instructor at no extra cost. Cancellations or reschedules require 24 hours' notice.</p>
        <h3>4. Direct Payment &amp; Non-Circumvention</h3>
        <p>All tuition payments are made directly to Qelal Learning rather than directly to tutors. Families agree not to engage Qelal-introduced tutors privately outside the platform during active enrollment and for 12 months following the final session. Private off-platform arrangements void Qelal progress reports, practice packs, and digital vault access.</p>
        <h3>5. Bishoftu Support</h3>
        <p>Questions regarding billing, schedules, or membership renewals can be directed to +251 933 510 682 or +251 988 666 328.</p>
      `;
    } else {
      titleEl.textContent = t("legalPrivacy");
      bodyEl.innerHTML = `
        <h3>1. Information Collected</h3>
        <p>When you register in Qelal Learning, we store your Telegram user ID, Telegram username (if set), full name, phone number, selected grade/stream, preferred tutoring format, and any child profiles or referral codes you provide.</p>
        <h3>2. Study &amp; Assessment Activity</h3>
        <p>To power your Continue Reading history, Study Plan checklist, and Parent Analytics dashboard, the portal records documents opened, last page read, bookmarks, quiz scores, and bi-weekly tutor progress notes.</p>
        <h3>3. Parent–Child Linking</h3>
        <p>If a parent provides a child's phone number or Telegram @username, Qelal automatically links the student and parent records so progress reports and study activity appear accurately without creating duplicate student accounts.</p>
        <h3>4. Data Storage &amp; Access</h3>
        <p>Account records are stored securely in Qelal Learning's administrative database and verified using Telegram cryptographic initData signatures. We never sell or share student or parent contact details with third-party advertisers.</p>
        <h3>5. Updates &amp; Deletion</h3>
        <p>To update your phone number, change your grade track, or request account removal, call +251 933 510 682 or +251 988 666 328.</p>
      `;
    }

    setHidden("modalLegal", false);
  }

  // ==================== SAFE EVENT WIRING ====================
  function safeAddEvent(id, event, callback) {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener(event, callback);
    } else {
      console.warn(`Warning: Element ID #${id} not found in HTML. Skipping listener.`);
    }
  }

  function wireGlobalEvents() {
    document.querySelectorAll("#langBar .lang-btn").forEach((btn) => {
      btn.addEventListener("click", () => setLanguage(btn.dataset.lang, true));
    });
    document.querySelectorAll("#regLangCards .lang-card").forEach((card) => {
      card.addEventListener("click", () => setLanguage(card.dataset.lang, false));
    });

    safeAddEvent("outsideRetryBtn", "click", authenticate);

    document.querySelectorAll(".role-btn").forEach((btn) => {
      btn.addEventListener("click", () => setRegRole(btn.dataset.role));
    });

    document.querySelectorAll("#regStudentStreamBtns .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.regStudentStream = btn.dataset.stream;
        document.querySelectorAll("#regStudentStreamBtns .seg-btn").forEach((b) =>
          b.classList.toggle("active", b.dataset.stream === state.regStudentStream)
        );
      });
    });

    document.querySelectorAll("#regStudentFormatBtns .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.regStudentFormat = btn.dataset.format;
        document.querySelectorAll("#regStudentFormatBtns .seg-btn").forEach((b) =>
          b.classList.toggle("active", b.dataset.format === state.regStudentFormat)
        );
      });
    });

    document.querySelectorAll("#regParentFormatBtns .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.regParentFormat = btn.dataset.format;
        document.querySelectorAll("#regParentFormatBtns .seg-btn").forEach((b) =>
          b.classList.toggle("active", b.dataset.format === state.regParentFormat)
        );
      });
    });

    safeAddEvent("btnAddChild", "click", () => {
      state.regChildren.push({
        name: "",
        grade: "Grade 6",
        stream: "Natural",
        format: state.regParentFormat,
        child_contact: "",
      });
      renderRegistrationDynamicParts();
    });

    safeAddEvent("regForm", "submit", handleRegisterSubmit);

    safeAddEvent("btnOpenTermsReg", "click", () => openLegalModal("terms"));
    safeAddEvent("btnOpenPrivacyReg", "click", () => openLegalModal("privacy"));
    safeAddEvent("btnOpenTermsFooter", "click", () => openLegalModal("terms"));
    safeAddEvent("btnOpenPrivacyFooter", "click", () => openLegalModal("privacy"));
    safeAddEvent("btnLegalClose", "click", () => setHidden("modalLegal", true));

    const legalModal = document.getElementById("modalLegal");
    if (legalModal) {
      legalModal.addEventListener("click", (e) => {
        if (e.target.id === "modalLegal") setHidden("modalLegal", true);
      });
    }

    safeAddEvent("libSearch", "input", (e) => {
      state.searchQuery = e.target.value;
      renderLibraryView();
    });
    safeAddEvent("filterGrade", "change", (e) => {
      state.filterGrade = e.target.value;
      renderLibraryView();
    });
    safeAddEvent("filterSubject", "change", (e) => {
      state.filterSubject = e.target.value;
      renderLibraryView();
    });
    safeAddEvent("filterCategory", "change", (e) => {
      state.filterCategory = e.target.value;
      renderLibraryView();
    });
    safeAddEvent("filterSavedBtn", "click", () => {
      state.filterSavedOnly = !state.filterSavedOnly;
      renderLibraryView();
    });

    safeAddEvent("reqToggleBtn", "click", () => {
      const box = document.getElementById("reqBox");
      if (box) box.classList.toggle("hidden");
    });
    safeAddEvent("reqSendBtn", "click", async () => {
      const subject = (document.getElementById("reqSubject")?.value || "").trim();
      const details = (document.getElementById("reqDetails")?.value || "").trim();
      const statusEl = document.getElementById("reqStatusMsg");
      if (!details) {
        if (statusEl) statusEl.textContent = t("reqEmpty");
        return;
      }
      try {
        await apiFetch("/api/request-material", {
          method: "POST",
          body: JSON.stringify({ subject, details }),
        });
        if (document.getElementById("reqSubject")) document.getElementById("reqSubject").value = "";
        if (document.getElementById("reqDetails")) document.getElementById("reqDetails").value = "";
        if (statusEl) statusEl.textContent = t("reqSent");
      } catch (err) {
        if (statusEl) statusEl.textContent = err.message;
      }
    });

    const addCustomTask = async () => {
      const inp = document.getElementById("customTaskInput");
      if (!inp) return;
      const text = inp.value.trim();
      if (!text) return;
      state.progress.custom_plan.push({ id: "cust_" + Date.now(), text, done: false });
      inp.value = "";
      renderCustomTasks();
      await saveProgress();
    };
    safeAddEvent("btnAddCustomTask", "click", addCustomTask);
    safeAddEvent("customTaskInput", "keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addCustomTask();
      }
    });

    safeAddEvent("btnPdfClose", "click", closePdfReader);
    safeAddEvent("btnPdfBookmark", "click", () => {
      if (state.pdfDocId) toggleBookmark(state.pdfDocId);
    });
    safeAddEvent("btnPdfSendChat", "click", (e) => {
      if (state.pdfDocId) sendFileToTelegram(state.pdfDocId, e.currentTarget);
    });
    safeAddEvent("btnPdfPrev", "click", () => {
      if (state.pdfPage > 1) {
        state.pdfPage--;
        renderMainPdfPage();
      }
    });
    safeAddEvent("btnPdfNext", "click", () => {
      if (state.pdfPage < state.pdfTotalPages) {
        state.pdfPage++;
        renderMainPdfPage();
      }
    });
    safeAddEvent("pdfPageInput", "change", (e) => {
      const p = parseInt(e.target.value, 10);
      if (!isNaN(p)) {
        state.pdfPage = Math.max(1, Math.min(p, state.pdfTotalPages));
        renderMainPdfPage();
      }
    });
    safeAddEvent("btnPdfZoomOut", "click", () => {
      state.pdfScale = Math.max(0.65, Number((state.pdfScale - 0.15).toFixed(2)));
      renderMainPdfPage();
    });
    safeAddEvent("btnPdfZoomIn", "click", () => {
      state.pdfScale = Math.min(2.35, Number((state.pdfScale + 0.15).toFixed(2)));
      renderMainPdfPage();
    });

    safeAddEvent("btnQuizClose", "click", closeQuizRunner);
    document.querySelectorAll(".quiz-subtab").forEach((btn) => {
      btn.addEventListener("click", () => setQuizPane(btn.dataset.pane));
    });
    safeAddEvent("btnQuizPdfPrev", "click", () => {
      if (state.quizPdfPage > 1) {
        state.quizPdfPage--;
        renderQuizPdfPage();
      }
    });
    safeAddEvent("btnQuizPdfNext", "click", () => {
      if (state.quizPdfPage < state.quizPdfTotal) {
        state.quizPdfPage++;
        renderQuizPdfPage();
      }
    });
    safeAddEvent("btnQuizPdfZoomOut", "click", () => {
      state.quizPdfScale = Math.max(0.65, Number((state.quizPdfScale - 0.15).toFixed(2)));
      renderQuizPdfPage();
    });
    safeAddEvent("btnQuizPdfZoomIn", "click", () => {
      state.quizPdfScale = Math.min(2.2, Number((state.quizPdfScale + 0.15).toFixed(2)));
      renderQuizPdfPage();
    });
    safeAddEvent("btnQuizSubmit", "click", submitQuizAnswers);
  }

  try {
    wireGlobalEvents();
    authenticate();
  } catch (err) {
    showBootError(err.message || String(err));
  }
})();
