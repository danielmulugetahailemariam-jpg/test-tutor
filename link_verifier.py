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


def extract_internal_metadata(first_pages_text: str) -> dict:
    low = first_pages_text.lower()
    m_yr = re.search(r"(?<![0-9])(20[0-2]\d)(?![0-9])", low)
    m_code = re.search(r"\b(?:booklet|subject|exam)\s*(?:code|no\.?)?\s*[:\-]?\s*0*(\d{1,3})\b", low)

    rnd = ""
    if re.search(r"\b(?:1st|first)\s+round", low):
        rnd = "Round 1"
    elif re.search(r"\b(?:2nd|second)\s+round", low):
        rnd = "Round 2"
    elif re.search(r"\b(?:3rd|third)\s+round", low):
        rnd = "Round 3"

    has_ans_title = bool(re.search(r"answer\s*(?:key|sheet)|answers\b|solutions?\b", low))
    return {
        "year": m_yr.group(1) if m_yr else "",
        "code": m_code.group(1) if m_code else "",
        "round": rnd,
        "has_answer_title": has_ans_title,
    }


def extract_sections(full_text: str) -> list[str]:
    low = full_text.lower()
    return [kw for kw in SECTION_KEYWORDS if re.search(rf"\b{re.escape(kw)}\b", low)]


def parse_answer_key(full_text: str) -> dict[str, str]:
    candidates = {}

    # Format 1: 1. B | 1) B | 1: B | 1 - B | Q1. B | 1. Answer: B
    for m in re.finditer(
        r"(?<!\d)(?:Q\.?\s*)?(\d{1,3})\s*[.):\-–]\s*(?:answer\s*[:\-]?\s*)?([A-Ea-e])\b",
        full_text,
        re.IGNORECASE,
    ):
        q = int(m.group(1))
        ans = m.group(2).upper()
        if 1 <= q <= 200 and q not in candidates:
            candidates[q] = ans

    # Format 2: Multi-column / grid tables like "1 B  21 D  41 A"
    if len(candidates) < 15:
        for m in re.finditer(r"(?<!\d)(\d{1,3})\s+([A-Da-d])(?=\s|$|\d)", full_text):
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

    meta = extract_internal_metadata("\n".join(pages[:2]))
    sections = extract_sections(full_text)
    choice_hits = len(re.findall(r"(?m)(?:^|\s)[A-D][.)]\s+\S", full_text))

    q_nums = set()
    for m in re.finditer(r"(?m)^\s*(?:Q\.?\s*)?(\d{1,3})\s*[.)]\s+\S", full_text):
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
        "year": meta["year"],
        "code": meta["code"],
        "round": meta["round"],
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

    meta = extract_internal_metadata("\n".join(pages[:2]))
    sections = extract_sections(full_text)
    choice_hits = len(re.findall(r"(?m)(?:^|\s)[A-D][.)]\s+\S", full_text))
    answers = parse_answer_key(full_text)
    max_ans = max((int(k) for k in answers.keys()), default=0)

    # Guard against accidentally treating a Question Paper as an Answer Sheet
    looks_like_question_paper = (choice_hits >= 50) and (not meta["has_answer_title"]) and (max_ans < 20)

    return {
        "is_scanned": False,
        "total_pages": total_pages,
        "year": meta["year"],
        "code": meta["code"],
        "round": meta["round"],
        "has_answer_title": meta["has_answer_title"],
        "looks_like_question_paper": looks_like_question_paper,
        "sections": sections,
        "choice_hits": choice_hits,
        "answers": answers,
        "max_ans": max_ans,
    }


def score_exam_answer_match(ex: dict, ans: dict, same_round_hint: bool = False) -> dict:
    """Compares analyzed Exam & Answer dicts and returns status, score, and reason."""
    if ex.get("is_scanned") or ans.get("is_scanned"):
        return {
            "status": "NEEDS_REVIEW",
            "score": 10,
            "reason": "Scanned PDF (no selectable text)",
            "answers": ans.get("answers", {}),
            "total_q": ans.get("max_ans") or 0,
            "sections": ex.get("sections", []),
        }

    if ans.get("looks_like_question_paper"):
        return {"status": "REJECTED_MISMATCH", "score": -100, "reason": "Answer file actually looks like a question paper", "answers": {}, "total_q": 0, "sections": []}

    if ans["max_ans"] < 10:
        return {"status": "NEEDS_REVIEW", "score": 5, "reason": "No numbered answer list detected", "answers": {}, "total_q": ex["max_q"], "sections": ex["sections"]}

    if ex["choice_hits"] < 15:
        return {"status": "REJECTED_MISMATCH", "score": -100, "reason": "Exam file has too few multiple-choice questions", "answers": {}, "total_q": 0, "sections": []}

    score = 0

    # 1. Year check inside PDFs
    if ex["year"] and ans["year"]:
        if ex["year"] != ans["year"]:
            return {"status": "REJECTED_MISMATCH", "score": -100, "reason": f"Year mismatch ({ex['year']} vs {ans['year']})", "answers": {}, "total_q": 0, "sections": []}
        score += 35

    # 2. Booklet / Subject code check inside PDFs
    if ex["code"] and ans["code"]:
        if ex["code"] != ans["code"]:
            return {"status": "REJECTED_MISMATCH", "score": -100, "reason": f"Code mismatch ({ex['code']} vs {ans['code']})", "answers": {}, "total_q": 0, "sections": []}
        score += 30

    # 3. Round check inside PDFs
    if ex["round"] and ans["round"]:
        if ex["round"] != ans["round"]:
            return {"status": "REJECTED_MISMATCH", "score": -100, "reason": f"Round mismatch ({ex['round']} vs {ans['round']})", "answers": {}, "total_q": 0, "sections": []}
        score += 20

    # 4. Question count alignment
    if ex["max_q"] >= 15:
        diff = abs(ex["max_q"] - ans["max_ans"])
        if diff > 4:
            return {"status": "REJECTED_MISMATCH", "score": -100, "reason": f"Question count mismatch ({ex['max_q']} vs {ans['max_ans']})", "answers": {}, "total_q": 0, "sections": []}
        score += 30 if diff <= 1 else 20

    # 5. Section/instruction overlap
    if len(ex["sections"]) >= 2 and len(ans["sections"]) >= 2:
        overlap = set(ex["sections"]) & set(ans["sections"])
        if not overlap:
            return {"status": "REJECTED_MISMATCH", "score": -100, "reason": "Section headings do not match", "answers": {}, "total_q": 0, "sections": []}
        score += 20

    if same_round_hint:
        score += 15

    if score >= 35:
        return {
            "status": "AUTO_VERIFIED",
            "score": score,
            "reason": f"Verified ({ans['max_ans']} Qs, score {score})",
            "answers": ans["answers"],
            "total_q": ans["max_ans"],
            "sections": ex["sections"] or ans["sections"],
        }

    return {
        "status": "NEEDS_REVIEW",
        "score": score,
        "reason": "Low confidence — please confirm in /review_links",
        "answers": ans["answers"],
        "total_q": ans["max_ans"],
        "sections": ex["sections"] or ans["sections"],
    }


def verify_exam_answer_pair(exam_bytes: bytes, answer_bytes: bytes) -> dict:
    ex = analyze_exam_pdf(exam_bytes)
    ans = analyze_answer_pdf(answer_bytes)
    return score_exam_answer_match(ex, ans)
