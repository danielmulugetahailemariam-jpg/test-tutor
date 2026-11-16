import os
import hmac
import json
import time
import uuid
import hashlib
import tempfile
import asyncio
import html
import logging
from datetime import datetime
from urllib.parse import parse_qsl, quote

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, Response, FileResponse, JSONResponse
from starlette.background import BackgroundTask
from google.auth.transport.requests import Request as GoogleAuthRequest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from study_plans import STUDY_PLAN_TEMPLATES

logger = logging.getLogger(__name__)


def create_webapp_router(
    bot_token: str,
    admin_user_id: int,
    get_ptb_app,
    get_bot_username,
    get_all_worksheets_fn,
    get_credentials_fn,
    eat_tz,
):
    router = APIRouter()
    session_secret = hashlib.sha256((bot_token + ":qelal_webapp_v4").encode()).digest()

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
        if state["cfg_cache"] is None or (now - state["cfg_cache_ts"] > 60):
            state["cfg_cache"] = await asyncio.to_thread(_load_config_sync)
            state["cfg_cache_ts"] = now
        return state["cfg_cache"]

    def _load_reg_and_students_sync():
        reg_sheet, _, _, _, _, _, students_sheet, reports_sheet = get_all_worksheets_fn()
        reg_rows = reg_sheet.get_all_values()[1:]
        stu_rows = students_sheet.get_all_values()[1:]
        rpt_rows = reports_sheet.get_all_values()[1:]

        by_tg = {}
        for idx, row in enumerate(reg_rows, start=2):
            r = row + [""] * (18 - len(row))
            if r[6].strip():
                ref_code = r[12].strip()
                if not ref_code:
                    ref_code = f"QELAL-{uuid.uuid4().hex[:5].upper()}"
                    try:
                        reg_sheet.update_cell(idx, 13, ref_code)
                    except Exception:
                        pass
                by_tg[r[6].strip()] = {
                    "name": r[1] or "Student",
                    "grade": r[2],
                    "phone": r[3],
                    "status": r[4].strip().upper() or "NEW",
                    "expires_on": r[8],
                    "stream": r[11] or "General",
                    "referral_code": ref_code,
                    "referred_by": r[13],
                    "referral_count": int(r[14]) if r[14].isdigit() else 0,
                    "role": r[15] or "student",
                    "format": r[16] or "Weekend Hub",
                    "lang": r[17] or "en",
                }

        children_by_parent = {}
        child_by_tg = {}
        student_by_id = {}
        for row in stu_rows:
            s = row + [""] * (11 - len(row))
            if not s[0]:
                continue
            stu_obj = {
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
            "children_by_parent": children_by_parent,
            "child_by_tg": child_by_tg,
            "reports_by_stu": approved_reports_by_stu,
        }

    async def get_reg_bundle() -> dict:
        now = time.time()
        if state["reg_cache"] is None or (now - state["reg_cache_ts"] > 30):
            state["reg_cache"] = await asyncio.to_thread(_load_reg_and_students_sync)
            state["reg_cache_ts"] = now
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
                "file_size_mb": float(r[13]) if r[13] else 0.0, "source": r[14],
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
        if state["lib_cache"] is None or (now - state["lib_cache_ts"] > 300):
            items, by_id, keys_by_id = await asyncio.to_thread(_load_library_and_keys_sync)
            state["lib_cache"] = (items, by_id)
            state["keys_cache"] = keys_by_id
            state["lib_cache_ts"] = now
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

    def _flush_analytics_sync(rows: list[list[str]]):
        _, _, _, analytics_sheet, _, _, _, _ = get_all_worksheets_fn()
        analytics_sheet.append_rows(rows, value_input_option="USER_ENTERED")

    async def log_analytics(tg_id: int, access: dict, action: str, doc_id: str, file_name: str, subject: str, score: str = ""):
        ts = datetime.now(eat_tz).strftime("%Y-%m-%d %H:%M")
        state["analytics_buffer"].append([
            ts, str(tg_id), access.get("name", ""), access.get("grade", ""),
            action, doc_id, file_name, subject, score,
        ])
        if len(state["analytics_buffer"]) >= 10 or (time.time() - state["last_flush_ts"] > 45):
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
    # ROUTES
    # ==========================================================================
    @router.get("/webapp", response_class=HTMLResponse)
    async def serve_webapp():
        html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
        if not os.path.exists(html_path):
            return HTMLResponse("<h1>Missing static/index.html</h1>", status_code=500)
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())

    @router.get("/static/{file_path:path}")
    async def serve_static_asset(file_path: str):
        static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
        full_path = os.path.abspath(os.path.join(static_dir, file_path))
        if not full_path.startswith(static_dir) or not os.path.isfile(full_path):
            raise HTTPException(status_code=404, detail="Asset not found")
        return FileResponse(full_path)

    @router.post("/api/auth")
    async def api_auth(request: Request):
        try:
            body = await request.json()
            user = verify_telegram_init_data(body.get("initData", ""))
            if not user:
                return {"ok": False, "status": "OUTSIDE_TELEGRAM"}

            tg_id = int(user["id"])
            access = await get_user_access(tg_id)
            if not access["registered"] and not access["is_admin"]:
                return {
                    "ok": False,
                    "status": "NOT_REGISTERED",
                    "tg_first_name": user.get("first_name", ""),
                }

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
            existing = await get_user_access(tg_id)
            if existing["registered"]:
                return {"ok": True, "already_registered": True}

            role = "parent" if body.get("role") == "parent" else "student"
            lang = "am" if body.get("lang") == "am" else "en"
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

                valid_ref_code, referrer_name = "", ""
                if entered_ref:
                    for rr in reg_rows[1:]:
                        rp = rr + [""] * (18 - len(rr))
                        if rp[12].strip().upper() == entered_ref and rp[6].strip() != str(tg_id):
                            valid_ref_code = entered_ref
                            referrer_name = rp[1]
                            break

                next_id = max(1, len(reg_rows))
                has_sibling_discount = (role == "parent") and (len(children) >= 2)

                if role == "student":
                    ch = children[0]
                    grade_val = ch.get("grade", "Grade 12")
                    stream_val = ch.get("stream", "General") if grade_val in ("Grade 11", "Grade 12") else "General"
                    ch_fmt = ch.get("format", prog_format)
                else:
                    grade_val = children[0].get("grade", "Grade 12") if len(children) == 1 else f"Parent ({len(children)} kids)"
                    stream_val = children[0].get("stream", "General") if len(children) == 1 else "General"
                    ch_fmt = prog_format

                reg_sheet.append_row([
                    next_id, full_name, grade_val, phone, "NEW", timestamp, str(tg_id),
                    "", "", "0", "-1", stream_val, my_ref_code, valid_ref_code, "0",
                    role, ch_fmt, lang,
                ])

                stu_rows_to_add, created_children = [], []
                for ch in children:
                    stu_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
                    c_name = (ch.get("name") or full_name).strip()
                    c_grade = ch.get("grade", "Grade 12")
                    c_stream = ch.get("stream", "General") if c_grade in ("Grade 11", "Grade 12") else "General"
                    c_fmt = ch.get("format", prog_format)
                    c_contact = (ch.get("child_contact") or "").strip()
                    link_tok = f"child_{uuid.uuid4().hex[:8]}" if role == "parent" else ""
                    child_tg = str(tg_id) if role == "student" else ""
                    parent_tg = str(tg_id) if role == "parent" else ""

                    stu_rows_to_add.append([
                        stu_id, c_name, c_grade, c_stream, c_fmt,
                        parent_tg, child_tg, c_contact, link_tok,
                        "YES" if has_sibling_discount else "NO", timestamp,
                    ])
                    created_children.append({
                        "student_id": stu_id, "student_name": c_name, "grade": c_grade,
                        "stream": c_stream, "format": c_fmt, "child_contact": c_contact, "link_token": link_tok,
                    })

                if stu_rows_to_add:
                    students_sheet.append_rows(stu_rows_to_add, value_input_option="USER_ENTERED")

                launch_mode = "OPEN_LAUNCH"
                for cr in cfg_sheet.get_all_values()[1:]:
                    if len(cr) >= 2 and cr[0].strip() == "LAUNCH_MODE":
                        launch_mode = cr[1].strip()
                return valid_ref_code, referrer_name, has_sibling_discount, created_children, launch_mode

            valid_ref, ref_name, sibling_disc, created_children, launch_mode = await asyncio.to_thread(_write_registration)
            invalidate_reg_cache()

            bot_user = get_bot_username()
            child_lines = []
            for ch in created_children:
                inv = f"https://t.me/{bot_user}?start={ch['link_token']}" if (bot_user and ch["link_token"]) else ""
                c_txt = f"• <b>{html.escape(ch['student_name'])}</b> — {html.escape(ch['grade'])}"
                if ch["stream"] != "General":
                    c_txt += f" ({ch['stream']})"
                if ch["child_contact"]:
                    c_txt += f"\n  📲 Child TG/Contact: <code>{html.escape(ch['child_contact'])}</code>"
                if inv:
                    c_txt += f"\n  🔗 Child Invite Link: {inv}"
                child_lines.append(c_txt)

            admin_msg = (
                f"🚨 <b>NEW {role.upper()} REGISTRATION (Mini App)</b>\n\n"
                f"👤 <b>Name:</b> {html.escape(full_name)}\n"
                f"📞 <b>Phone:</b> <code>{html.escape(phone)}</code>\n"
                f"🆔 <code>{tg_id}</code> | 🔑 Code: <code>{my_ref_code}</code>\n"
                f"{'🎉 <b>SIBLING DISCOUNT ELIGIBLE (2+ Kids)!</b>\n' if sibling_disc else ''}"
                f"{f'🤝 <b>Referred by:</b> {html.escape(ref_name)} (<code>{valid_ref}</code>)\n' if valid_ref else ''}\n"
                f"<b>Students:</b>\n" + "\n".join(child_lines)
            )
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve (Start 30d)", callback_data=f"approve_user:{tg_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_user:{tg_id}"),
            ]])
            try:
                await get_ptb_app().bot.send_message(chat_id=admin_user_id, text=admin_msg, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Failed notifying admin: {e}")

            return {"ok": True, "referral_code": my_ref_code, "sibling_discount": sibling_disc, "launch_mode": launch_mode}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Registration failed")
            return JSONResponse({"ok": False, "detail": str(e)}, status_code=500)

    @router.post("/api/set-lang")
    async def api_set_lang(request: Request):
        tg_id, _ = await require_session(request)
        body = await request.json()
        lang = "am" if body.get("lang") == "am" else "en"

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
            "Cache-Control": "no-store",
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
            f"📚 <b>{html.escape(item['file_name'])}</b>\n"
            f"🏷 {item['grade']} | {item['subject']} | {item['category']}\n"
            f"🔒 <i>Viewable offline inside Telegram only (forwarding &amp; local saving disabled).</i>"
        )

        if item["telegram_file_id"]:
            await bot.send_document(
                chat_id=tg_id, document=item["telegram_file_id"],
                caption=caption, protect_content=True, parse_mode="HTML",
            )
            await log_analytics(tg_id, access, "SEND_CHAT", doc_id, item["file_name"], item["subject"])
            return {"ok": True, "cached": True}

        if item["file_size_mb"] > 48:
            return {"ok": False, "too_large": True, "message": "This large book (>48 MB) can be read directly inside the Mini App reader!"}

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
                f"📩 <b>MATERIAL REQUEST FROM {access.get('role','student').upper()}</b>\n\n"
                f"👤 <b>Name:</b> {html.escape(access.get('name', 'Student'))} ({html.escape(access.get('grade', ''))})\n"
                f"📞 <code>{html.escape(access.get('phone', ''))}</code> | 🆔 <code>{tg_id}</code>\n"
                f"📚 <b>Subject:</b> {html.escape(subject or 'General')}\n"
                f"📝 <b>Request:</b> {html.escape(details)}"
            ),
            parse_mode="HTML",
        )
        return {"ok": True}

    return router
