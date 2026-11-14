import io
import os
import hmac
import json
import time
import hashlib
import tempfile
import asyncio
import logging
from urllib.parse import parse_qsl, quote

import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from starlette.background import BackgroundTask
from google.auth.transport.requests import Request as GoogleAuthRequest

logger = logging.getLogger(__name__)


def create_webapp_router(
    bot_token: str,
    admin_user_id: int,
    get_ptb_app,
    get_sheets_fn,
    get_credentials_fn,
    reg_headers: list[str],
    pdf_headers: list[str],
):
    router = APIRouter()
    session_secret = hashlib.sha256((bot_token + ":bishoftu_webapp_v1").encode()).digest()

    # In-memory caches to protect Google Sheets read quotas
    state = {
        "creds": None,
        "lib_cache": None,
        "lib_cache_ts": 0.0,
        "reg_cache": None,
        "reg_cache_ts": 0.0,
    }

    def invalidate_library_cache():
        state["lib_cache"] = None
        state["lib_cache_ts"] = 0.0

    def invalidate_reg_cache():
        state["reg_cache"] = None
        state["reg_cache_ts"] = 0.0

    # Attach cache clear hooks on router for bot.py to call after /sync_drive or approvals
    router.invalidate_library_cache = invalidate_library_cache
    router.invalidate_reg_cache = invalidate_reg_cache

    def get_drive_access_token() -> str:
        if state["creds"] is None:
            state["creds"] = get_credentials_fn()
        if not state["creds"].valid:
            state["creds"].refresh(GoogleAuthRequest())
        return state["creds"].token

    # --- TELEGRAM INITDATA & SESSION TOKENS ---
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

            auth_date = int(parsed.get("auth_date", "0"))
            if time.time() - auth_date > 86400:
                return None

            user_json = parsed.get("user")
            if not user_json:
                return None
            return json.loads(user_json)
        except Exception as e:
            logger.warning(f"initData verification failed: {e}")
            return None

    def create_session_token(tg_id: int) -> str:
        exp = int(time.time()) + 14400  # 4 hours
        payload = f"{tg_id}:{exp}"
        sig = hmac.new(session_secret, payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}:{sig}"

    def verify_session_token(token: str) -> int | None:
        try:
            tg_id_str, exp_str, sig = token.split(":", 2)
            if int(exp_str) < int(time.time()):
                return None
            payload = f"{tg_id_str}:{exp_str}"
            expected = hmac.new(session_secret, payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, sig):
                return None
            return int(tg_id_str)
        except Exception:
            return None

    # --- CACHED SHEET READERS ---
    def _load_registrations_sync() -> dict[str, dict]:
        reg_sheet, _ = get_sheets_fn()
        rows = reg_sheet.get_all_values()
        by_tg_id = {}
        for row in rows[1:]:
            if len(row) >= 7 and row[6].strip():
                by_tg_id[row[6].strip()] = {
                    "name": row[1] if len(row) > 1 else "Student",
                    "grade": row[2] if len(row) > 2 else "",
                    "status": (row[4].strip().upper() if len(row) > 4 else "NEW"),
                }
        return by_tg_id

    async def get_user_access(tg_id: int) -> dict:
        now = time.time()
        if state["reg_cache"] is None or (now - state["reg_cache_ts"] > 30):
            state["reg_cache"] = await asyncio.to_thread(_load_registrations_sync)
            state["reg_cache_ts"] = now

        record = state["reg_cache"].get(str(tg_id))
        if tg_id == admin_user_id:
            return {
                "status": "APPROVED",
                "name": record["name"] if record else "Admin",
                "grade": record["grade"] if record else "Admin",
                "is_admin": True,
            }
        if not record:
            return {"status": "NOT_REGISTERED", "name": "", "grade": "", "is_admin": False}
        return {**record, "is_admin": False}

    def _load_library_sync() -> tuple[list[dict], dict[str, dict]]:
        _, pdf_sheet = get_sheets_fn()
        rows = pdf_sheet.get_all_values()
        items = []
        by_id = {}
        for idx, row in enumerate(rows[1:], start=2):
            if not row or not row[0]:
                continue
            # Pad row safely to 20 columns
            r = row + [""] * (20 - len(row))
            item = {
                "row_idx": idx,
                "doc_id": r[0],
                "file_name": r[1],
                "grade": r[2],
                "stream": r[3],
                "subject": r[4],
                "category": r[5],
                "year": r[6],
                "exam_tag": r[7],
                "round_or_code": r[8],
                "link_key": r[9],
                "linked_doc_id": r[10],
                "has_embedded_answer": r[11],
                "format": r[12],
                "file_size_mb": float(r[13]) if r[13] else 0.0,
                "source": r[14],
                "drive_pdf_id": r[15],
                "drive_original_id": r[16],
                "telegram_file_id": r[17],
                "post_link": r[19],
            }
            items.append(item)
            by_id[item["doc_id"]] = item
        return items, by_id

    async def get_library_data() -> tuple[list[dict], dict[str, dict]]:
        now = time.time()
        if state["lib_cache"] is None or (now - state["lib_cache_ts"] > 300):
            state["lib_cache"] = await asyncio.to_thread(_load_library_sync)
            state["lib_cache_ts"] = now
        return state["lib_cache"]

    async def require_approved_token(request: Request, token: str | None = None) -> tuple[int, dict]:
        auth_token = token
        if not auth_token:
            auth_hdr = request.headers.get("authorization", "")
            if auth_hdr.lower().startswith("bearer "):
                auth_token = auth_hdr[7:].strip()
        if not auth_token:
            raise HTTPException(status_code=401, detail="Missing session token")

        tg_id = verify_session_token(auth_token)
        if not tg_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        access = await get_user_access(tg_id)
        if access["status"] != "APPROVED":
            raise HTTPException(status_code=403, detail="Account not approved")
        return tg_id, access

    def content_disposition_header(disp_type: str, filename: str) -> str:
        ascii_name = filename.encode("ascii", "ignore").decode("ascii").strip().replace('"', "")
        if not ascii_name:
            ascii_name = "document.pdf"
        return f'{disp_type}; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'

    async def get_upstream_source(item: dict, variant: str):
        """Returns (url, auth_headers, filename, mime_type) for Drive or Telegram."""
        if variant == "original" and item["drive_original_id"]:
            drive_id = item["drive_original_id"]
            fname = item["file_name"]
            if fname.lower().endswith(".pdf"):
                if "PPTX" in item["format"]:
                    fname = fname[:-4] + ".pptx"
                elif "DOCX" in item["format"]:
                    fname = fname[:-4] + ".docx"
            mime = (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                if fname.lower().endswith(".pptx")
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            token = await asyncio.to_thread(get_drive_access_token)
            url = f"https://www.googleapis.com/drive/v3/files/{drive_id}?alt=media&supportsAllDrives=true"
            return url, {"Authorization": f"Bearer {token}"}, fname, mime

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
            file_url = tg_file.file_path
            if not file_url.startswith("http"):
                file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_url}"
            mime = "application/pdf" if item["file_name"].lower().endswith(".pdf") else "application/octet-stream"
            return file_url, {}, item["file_name"], mime

        raise HTTPException(status_code=404, detail="File source not found")

    # ==========================================================================
    # ROUTES
    # ==========================================================================
    @router.get("/webapp", response_class=HTMLResponse)
    async def serve_webapp():
        html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
        if not os.path.exists(html_path):
            return HTMLResponse("<h1>Mini App UI missing (static/index.html)</h1>", status_code=500)
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())

    @router.post("/api/auth")
    async def api_auth(request: Request):
        body = await request.json()
        init_data = body.get("initData", "")
        user = verify_telegram_init_data(init_data)
        if not user:
            return {"ok": False, "status": "OUTSIDE_TELEGRAM"}

        tg_id = int(user["id"])
        access = await get_user_access(tg_id)
        if access["status"] != "APPROVED":
            return {
                "ok": False,
                "status": access["status"],
                "name": access["name"] or user.get("first_name", "Student"),
            }

        token = create_session_token(tg_id)
        return {
            "ok": True,
            "status": "APPROVED",
            "name": access["name"],
            "grade": access["grade"],
            "is_admin": access["is_admin"],
            "token": token,
        }

    @router.get("/api/library")
    async def api_library(request: Request, refresh: bool = False):
        _, access = await require_approved_token(request)
        if refresh and access.get("is_admin"):
            invalidate_library_cache()
        items, _ = await get_library_data()

        # Return clean public metadata (hide internal Google Drive IDs)
        public_items = []
        for it in items:
            public_items.append({
                "doc_id": it["doc_id"],
                "file_name": it["file_name"],
                "grade": it["grade"],
                "stream": it["stream"],
                "subject": it["subject"],
                "category": it["category"],
                "year": it["year"],
                "exam_tag": it["exam_tag"],
                "round_or_code": it["round_or_code"],
                "linked_doc_id": it["linked_doc_id"],
                "has_embedded_answer": it["has_embedded_answer"],
                "format": it["format"],
                "file_size_mb": it["file_size_mb"],
                "has_pdf": bool(it["drive_pdf_id"] or (it["telegram_file_id"] and it["file_name"].lower().endswith(".pdf"))),
                "has_original_office": bool(it["drive_original_id"]),
            })
        return {"ok": True, "items": public_items}

    @router.api_route("/api/file/{doc_id}/stream", methods=["GET", "HEAD"])
    async def api_stream_file(doc_id: str, request: Request, token: str | None = None, variant: str = "pdf"):
        await require_approved_token(request, token=token)
        _, by_id = await get_library_data()
        item = by_id.get(doc_id)
        if not item:
            raise HTTPException(status_code=404, detail="Document not found")

        url, auth_headers, fname, mime_type = await get_upstream_source(item, variant)

        # Handle HEAD efficiently without streaming bytes
        if request.method == "HEAD":
            head_headers = {"Accept-Ranges": "bytes", "Content-Type": mime_type}
            if item["drive_pdf_id"] or item["drive_original_id"]:
                drive_id = item["drive_original_id"] if (variant == "original" and item["drive_original_id"]) else item["drive_pdf_id"] or item["drive_original_id"]
                async with httpx.AsyncClient(timeout=20.0) as client:
                    meta_resp = await client.get(
                        f"https://www.googleapis.com/drive/v3/files/{drive_id}?fields=size&supportsAllDrives=true",
                        headers=auth_headers,
                    )
                    if meta_resp.status_code == 200 and meta_resp.json().get("size"):
                        head_headers["Content-Length"] = str(meta_resp.json()["size"])
            return Response(status_code=200, headers=head_headers)

        upstream_headers = dict(auth_headers)
        if "range" in request.headers:
            upstream_headers["Range"] = request.headers["range"]

        client = httpx.AsyncClient(timeout=60.0)
        req = client.build_request("GET", url, headers=upstream_headers)
        upstream_resp = await client.send(req, stream=True)

        if upstream_resp.status_code >= 400:
            await upstream_resp.aclose()
            await client.aclose()
            raise HTTPException(status_code=upstream_resp.status_code, detail="Upstream storage error")

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": content_disposition_header("inline", fname),
            "Cache-Control": "private, max-age=3600",
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

    @router.get("/api/file/{doc_id}/download")
    async def api_download_file(doc_id: str, request: Request, token: str | None = None, variant: str = "pdf"):
        await require_approved_token(request, token=token)
        _, by_id = await get_library_data()
        item = by_id.get(doc_id)
        if not item:
            raise HTTPException(status_code=404, detail="Document not found")

        url, auth_headers, fname, mime_type = await get_upstream_source(item, variant)
        client = httpx.AsyncClient(timeout=120.0)
        req = client.build_request("GET", url, headers=auth_headers)
        upstream_resp = await client.send(req, stream=True)

        if upstream_resp.status_code >= 400:
            await upstream_resp.aclose()
            await client.aclose()
            raise HTTPException(status_code=upstream_resp.status_code, detail="Upstream download error")

        resp_headers = {"Content-Disposition": content_disposition_header("attachment", fname)}
        if "content-length" in upstream_resp.headers:
            resp_headers["Content-Length"] = upstream_resp.headers["content-length"]

        async def close_upstream():
            await upstream_resp.aclose()
            await client.aclose()

        return StreamingResponse(
            upstream_resp.aiter_bytes(chunk_size=65536),
            status_code=200,
            headers=resp_headers,
            media_type=mime_type,
            background=BackgroundTask(close_upstream),
        )

    @router.post("/api/file/{doc_id}/send")
    async def api_send_to_chat(doc_id: str, request: Request, variant: str = "pdf"):
        tg_id, _ = await require_approved_token(request)
        _, by_id = await get_library_data()
        item = by_id.get(doc_id)
        if not item:
            raise HTTPException(status_code=404, detail="Document not found")

        bot = get_ptb_app().bot
        caption = f"📚 <b>{item['file_name']}</b>\n🏷 {item['grade']} | {item['subject']} | {item['category']}"

        # Fast path: reuse cached Telegram_File_ID (0 Render bandwidth!)
        if variant == "pdf" and item["telegram_file_id"]:
            await bot.send_document(
                chat_id=tg_id,
                document=item["telegram_file_id"],
                caption=caption,
                parse_mode="HTML",
            )
            return {"ok": True, "cached": True}

        if item["file_size_mb"] > 48:
            return {
                "ok": False,
                "too_large_for_bot": True,
                "message": "This file is larger than Telegram's 50 MB bot upload limit. Please use Direct Save instead.",
            }

        url, auth_headers, fname, _ = await get_upstream_source(item, variant)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name

            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("GET", url, headers=auth_headers) as r:
                    r.raise_for_status()
                    with open(tmp_path, "wb") as f:
                        async for chunk in r.aiter_bytes(chunk_size=65536):
                            f.write(chunk)

            with open(tmp_path, "rb") as f:
                sent_msg = await bot.send_document(
                    chat_id=tg_id,
                    document=f,
                    filename=fname,
                    caption=caption,
                    parse_mode="HTML",
                )

            # Cache Telegram_File_ID back into Google Sheets for future zero-bandwidth sends
            if variant == "pdf" and sent_msg.document and not item["telegram_file_id"]:
                new_tg_file_id = sent_msg.document.file_id
                item["telegram_file_id"] = new_tg_file_id

                def _cache_tg_id():
                    _, pdf_sheet = get_sheets_fn()
                    pdf_sheet.update_cell(item["row_idx"], 18, new_tg_file_id)  # Col R = 18

                await asyncio.to_thread(_cache_tg_id)

            return {"ok": True, "cached": False}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    return router
