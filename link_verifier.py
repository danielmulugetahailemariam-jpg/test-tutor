import io
import re
import json
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
    year = ""
    m_yr = re.search(r"(?<![0-9])(20[0-2]\d)(?![0-9])", low)
    if m_yr:
        year = m_yr.group(1)

    code = ""
    m_code = re.search(r"\b(?:booklet|subject|exam)\s*(?:code|no\.?)?\s*[:\-]?\s*0*(\d{1,3})\b", low)
    if m_code:
        code = m_code.group(1)

    return year, code


def extract_sections(full_text: str) -> list[str]:
    low = full_text.lower()
    found = []
    for kw in SECTION_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", low):
            found.append(kw)
    return found


def parse_answer_key(full_text: str) -> dict[str, str]:
    """Extracts question->choice map like {'1': 'B', '2': 'D'} and keeps the valid sequential run."""
    candidates = {}

    # Pattern 1: 1. B | 1) B | 1: B | 1 - B | 1. Answer: B
    for m in re.finditer(r"(?<!\d)(\d{1,3})\s*[.):\-–]\s*(?:answer\s*[:\-]?\s*)?([A-Ea-e])\b", full_text, re.IGNORECASE):
        q = int(m.group(1))
        ans = m.group(2).upper()
        if 1 <= q <= 200 and q not in candidates:
            candidates[q] = ans

    # Pattern 2: Compact grid rows like "1 B 2 A 3 D"
    if len(candidates) < 15:
        for m in re.finditer(r"(?<!\d)(\d{1,3})\s+([A-Da-d])(?=\s|$)", full_text):
            q = int(m.group(1))
            ans = m.group(2).upper()
            if 1 <= q <= 200 and q not in candidates:
                candidates[q] = ans

    if not candidates:
        return {}

    # Validate it's a real answer key (starts near 1 and covers sequential numbers)
    max_q = max(candidates.keys())
    if max_q < 10:
        return {}
    coverage = len(candidates) / max_q
    if coverage < 0.55 or 1 not in candidates and 2 not in candidates:
        return {}

    return {str(k): candidates[k] for k in sorted(candidates.keys())}


def analyze_exam_pdf(pdf_bytes: bytes) -> dict:
    total_pages, pages = extract_pdf_pages_text(pdf_bytes)
    full_text = "\n".join(pages)
    if len(full_text.strip()) < 120:
        return {"is_scanned": True, "total_pages": total_pages}

    year, code = extract_internal_year_and_code("\n".join(pages[:2]))
    sections = extract_sections(full_text)

    # Count choice options (A., B., C., D.)
    choice_hits = len(re.findall(r"(?m)(?:^|\s)[A-D][.)]\s+\S", full_text))

    # Find highest sequential question number
    q_nums = set()
    for m in re.finditer(r"(?m)^\s*(\d{1,3})\s*[.)]\s+\S", full_text):
        val = int(m.group(1))
        if 1 <= val <= 200:
            q_nums.add(val)

    # Clean max_q: ignore stray numbers far above the main sequence
    sorted_q = sorted(q_nums)
    max_q = 0
    for q in sorted_q:
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
    """
    Returns:
      status: 'AUTO_VERIFIED' | 'REJECTED_MISMATCH' | 'NEEDS_REVIEW'
      reason: human-readable explanation
      answers: dict {'1':'B',...} if extracted
      total_q: int
      sections: list[str]
    """
    ex = analyze_exam_pdf(exam_bytes)
    ans = analyze_answer_pdf(answer_bytes)

    if ex["is_scanned"] or ans["is_scanned"]:
        return {
            "status": "NEEDS_REVIEW",
            "reason": "Scanned PDF (no selectable text to verify automatically)",
            "answers": ans.get("answers", {}),
            "total_q": ans.get("max_ans") or 0,
            "sections": ex.get("sections", []),
        }

    # 1. Role sanity: ensure answer file actually contains an answer key & exam has choices
    if ans["max_ans"] < 10:
        return {
            "status": "NEEDS_REVIEW",
            "reason": "Could not detect numbered answer list inside Answer PDF",
            "answers": {},
            "total_q": ex["max_q"],
            "sections": ex["sections"],
        }

    if ex["choice_hits"] < 15 and ans["choice_hits"] < 15:
        return {
            "status": "REJECTED_MISMATCH",
            "reason": "Neither file looks like a multiple-choice question paper",
            "answers": {},
            "total_q": 0,
            "sections": [],
        }

    # 2. Internal Year conflict check
    if ex["year"] and ans["year"] and ex["year"] != ans["year"]:
        return {
            "status": "REJECTED_MISMATCH",
            "reason": f"Year mismatch inside PDFs (Exam={ex['year']} vs Answer={ans['year']})",
            "answers": {},
            "total_q": 0,
            "sections": [],
        }

    # 3. Internal Booklet / Subject Code conflict check
    if ex["code"] and ans["code"] and ex["code"] != ans["code"]:
        return {
            "status": "REJECTED_MISMATCH",
            "reason": f"Booklet code mismatch inside PDFs (Exam={ex['code']} vs Answer={ans['code']})",
            "answers": {},
            "total_q": 0,
            "sections": [],
        }

    # 4. Question count alignment
    if ex["max_q"] >= 15 and abs(ex["max_q"] - ans["max_ans"]) > 4:
        return {
            "status": "REJECTED_MISMATCH",
            "reason": f"Question count mismatch (Exam={ex['max_q']} Qs vs Answer={ans['max_ans']} Qs)",
            "answers": {},
            "total_q": 0,
            "sections": [],
        }

    # 5. Section/instruction overlap check (if both have named sections)
    if len(ex["sections"]) >= 2 and len(ans["sections"]) >= 2:
        overlap = set(ex["sections"]) & set(ans["sections"])
        if not overlap:
            return {
                "status": "REJECTED_MISMATCH",
                "reason": "Instruction/section headings inside Exam and Answer do not match",
                "answers": {},
                "total_q": 0,
                "sections": [],
            }

    return {
        "status": "AUTO_VERIFIED",
        "reason": f"Verified ({ans['max_ans']} questions matched)",
        "answers": ans["answers"],
        "total_q": ans["max_ans"],
        "sections": ex["sections"] or ans["sections"],
    }
