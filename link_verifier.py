import io
import re
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

SECTION_KEYWORDS = [
    "comprehension", "reading", "vocabulary", "grammar", "language focus",
    "communicative", "writing", "analogy", "analogies", "synonym", "antonym",
    "sentence completion", "quantitative", "verbal", "analytical", "part i",
    "part ii", "part iii", "part iv", "section i", "section ii", "section iii",
]


def extract_pdf_pages_text(pdf_bytes: bytes, max_pages: int = 45) -> tuple[int, list[str]]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)
    pages_text = []
    for i in range(min(total_pages, max_pages)):
        try:
            pages_text.append(reader.pages[i].extract_text() or "")
        except Exception:
            pages_text.append("")
    return total_pages, pages_text


def extract_internal_year_and_code(first_pages_text: str) -> tuple[str, str]:
    low = first_pages_text.lower()
    m_yr = re.search(r"(?<![0-9])(20[0-2]\d)(?![0-9])", low)
    year = m_yr.group(1) if m_yr else ""

    m_code = re.search(r"\b(?:booklet|subject|exam)\s*(?:code|no\.?)?\s*[:\-]?\s*0*(\d{1,3})\b", low)
    code = m_code.group(1) if m_code else ""
    return year, code


def extract_sections(full_text: str) -> list[str]:
    low = full_text.lower()
    return [kw for kw in SECTION_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", low)]


def parse_answer_key(full_text: str) -> dict[str, str]:
    candidates = {}
    for m in re.finditer(r"(?<!\d)(\d{1,3})\s*[.):\-–]\s*(?:answer\s*[:\-]?\s*)?([A-Ea-e])\b", full_text, re.IGNORECASE):
        q = int(m.group(1))
        ans = m.group(2).upper()
        if 1 <= q <= 200 and q not in candidates:
            candidates[q] = ans

    if len(candidates) < 15:
        for m in re.finditer(r"(?<!\d)(\d{1,3})\s+([A-Da-d])(?=\s|$)", full_text):
            q = int(m.group(1))
            ans = m.group(2).upper()
            if 1 <= q <= 200 and q not in candidates:
                candidates[q] = ans

    if not candidates:
        return {}
    max_q = max(candidates.keys())
    if max_q < 10:
        return {}
    if (len(candidates) / max_q) < 0.55 or (1 not in candidates and 2 not in candidates):
        return {}
    return {str(k): candidates[k] for k in sorted(candidates.keys())}


def analyze_exam_pdf(pdf_bytes: bytes) -> dict:
    total_pages, pages = extract_pdf_pages_text(pdf_bytes)
    full_text = "\n".join(pages)
    if len(full_text.strip()) < 120:
        return {"is_scanned": True, "total_pages": total_pages}

    year, code = extract_internal_year_and_code("\n".join(pages[:2]))
    sections = extract_sections(full_text)
    choice_hits = len(re.findall(r"(?m)(?:^|\s)[A-D][.)]\s+\S", full_text))

    q_nums = set()
    for m in re.finditer(r"(?m)^\s*(\d{1,3})\s*[.)]\s+\S", full_text):
        val = int(m.group(1))
        if 1 <= val <= 200:
            q_nums.add(val)

    max_q = 0
    for q in sorted(q_nums):
        if q <= max_q + 10 or q <= 20:
            max_q = q

    embedded_answers = parse_answer_key("\n".join(pages[-5:])) if len(pages) >= 3 else {}
    return {
        "is_scanned": False,
        "total_pages": total_pages,
        "year": year,
        "code": code,
        "sections": sections,
        "choice_hits": choice_hits,
        "max_q": max_q,
        "embedded_answers": embedded_answers,
    }


def analyze_answer_pdf(pdf_bytes: bytes) -> dict:
    total_pages, pages = extract_pdf_pages_text(pdf_bytes)
    full_text = "\n".join(pages)
    if len(full_text.strip()) < 80:
        return {"is_scanned": True, "total_pages": total_pages}

    year, code = extract_internal_year_and_code("\n".join(pages[:2]))
    sections = extract_sections(full_text)
    choice_hits = len(re.findall(r"(?m)(?:^|\s)[A-D][.)]\s+\S", full_text))
    answers = parse_answer_key(full_text)
    max_ans = max((int(k) for k in answers.keys()), default=0)

    return {
        "is_scanned": False,
        "total_pages": total_pages,
        "year": year,
        "code": code,
        "sections": sections,
        "choice_hits": choice_hits,
        "answers": answers,
        "max_ans": max_ans,
    }


def verify_exam_answer_pair(exam_bytes: bytes, answer_bytes: bytes) -> dict:
    ex = analyze_exam_pdf(exam_bytes)
    ans = analyze_answer_pdf(answer_bytes)

    if ex["is_scanned"] or ans["is_scanned"]:
        return {
            "status": "NEEDS_REVIEW",
            "reason": "Scanned PDF (no selectable text)",
            "answers": ans.get("answers", {}),
            "total_q": ans.get("max_ans") or 0,
            "sections": ex.get("sections", []),
        }

    if ans["max_ans"] < 10:
        return {
            "status": "NEEDS_REVIEW",
            "reason": "No numbered answer list detected",
            "answers": {},
            "total_q": ex["max_q"],
            "sections": ex["sections"],
        }

    if ex["choice_hits"] < 15 and ans["choice_hits"] < 15:
        return {"status": "REJECTED_MISMATCH", "reason": "Neither file looks like an MCQ exam", "answers": {}, "total_q": 0, "sections": []}

    if ex["year"] and ans["year"] and ex["year"] != ans["year"]:
        return {"status": "REJECTED_MISMATCH", "reason": f"Year conflict ({ex['year']} vs {ans['year']})", "answers": {}, "total_q": 0, "sections": []}

    if ex["code"] and ans["code"] and ex["code"] != ans["code"]:
        return {"status": "REJECTED_MISMATCH", "reason": f"Booklet code conflict ({ex['code']} vs {ans['code']})", "answers": {}, "total_q": 0, "sections": []}

    if ex["max_q"] >= 15 and abs(ex["max_q"] - ans["max_ans"]) > 4:
        return {"status": "REJECTED_MISMATCH", "reason": f"Question count mismatch ({ex['max_q']} vs {ans['max_ans']})", "answers": {}, "total_q": 0, "sections": []}

    if len(ex["sections"]) >= 2 and len(ans["sections"]) >= 2:
        if not (set(ex["sections"]) & set(ans["sections"])):
            return {"status": "REJECTED_MISMATCH", "reason": "Section headings do not match", "answers": {}, "total_q": 0, "sections": []}

    return {
        "status": "AUTO_VERIFIED",
        "reason": f"Verified ({ans['max_ans']} questions matched)",
        "answers": ans["answers"],
        "total_q": ans["max_ans"],
        "sections": ex["sections"] or ans["sections"],
    }
