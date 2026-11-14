import re

STUDY_EXTENSIONS = (".pdf", ".pptx", ".docx")

ADMIN_EXCLUDE_KEYWORDS = (
    "list_of_registered",
    "registered_students",
    "grade report",
    "top student",
    "filenames.txt",
)


def is_excluded_file(filename: str) -> tuple[bool, str]:
    lower = filename.lower().strip()
    if not lower.endswith(STUDY_EXTENSIONS):
        return True, "unsupported extension"
    for kw in ADMIN_EXCLUDE_KEYWORDS:
        if kw in lower:
            return True, "admin/private file"
    return False, ""


def normalize_stem(filename: str) -> str:
    """Normalizes filename without extension/copy-numbers to pair .pptx/.docx with .pdf and spot duplicates."""
    stem = re.sub(r"\.(pdf|pptx|docx)$", "", filename.strip(), flags=re.IGNORECASE)
    # Remove trailing copy markers like (1), (2), _compressed
    stem = re.sub(r"(_compressed|\s*\(\d+\))+$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\s*\(\d+\)", "", stem)
    stem = re.sub(r"[_\-\s]+", " ", stem).strip().lower()
    return stem


def extract_grade(text_lower: str) -> str:
    # Multi-grade ranges first
    if re.search(r"(?:9\s*(?:-|to|and|,)\s*12|9\s*,\s*10\s*,\s*11\s*,\s*12)", text_lower):
        return "Grade 9-12"
    if re.search(r"(?:11\s*(?:&|and|-|to)\s*12)", text_lower):
        return "Grade 11-12"
    if re.search(r"(?:9\s*(?:&|and|-|to)\s*10)", text_lower):
        return "Grade 9-10"
    if re.search(r"(?:10\s*(?:&|and|-|to)\s*11)", text_lower):
        return "Grade 10-11"

    # Explicit single grades (handles G12, G-12, G.12, Grade 12, CHEM 11, etc.)
    explicit_patterns = [
        (r"(?:\bgrade|\bg)[.\-_\s]*12\b|\b(?:chem|chemistry|bio|biology|phy|physics|math|maths|geo|hist|eco|eng)\s*12\b", "Grade 12"),
        (r"(?:\bgrade|\bg)[.\-_\s]*11\b|\b(?:chem|chemistry|bio|biology|phy|physics|math|maths|geo|hist|eco|eng)\s*11\b", "Grade 11"),
        (r"(?:\bgrade|\bg)[.\-_\s]*10\b|\b(?:chem|chemistry|bio|biology|phy|physics|math|maths|geo|hist|eco|eng)\s*10\b", "Grade 10"),
        (r"(?:\bgrade|\bg)[.\-_\s]*9\b|\b(?:chem|chemistry|bio|biology|phy|physics|math|maths|geo|hist|eco|eng)\s*9\b", "Grade 9"),
        (r"(?:\bgrade|\bg)[.\-_\s]*8\b", "Grade 8"),
        (r"(?:\bgrade|\bg)[.\-_\s]*6\b", "Grade 6"),
    ]
    for pat, label in explicit_patterns:
        if re.search(pat, text_lower):
            return label

    if "remedial" in text_lower:
        return "Remedial"
    if "freshman" in text_lower or "fresh man" in text_lower:
        return "Freshman"

    # Implicit Grade 12 / Entrance materials
    if re.search(
        r"\b(?:euee|esslce|uee|matric|entrance|pilot|model|uat|astu|aastu|sat)\b",
        text_lower,
    ):
        return "Grade 12"

    return "General"


def extract_subject(original_text: str, text_lower: str) -> str:
    # Check specific subjects first (order matters for e.g. "501-GMAT" vs "501-Synonym")
    if re.search(r"\b(?:bio|biology|genetics|enzymes|evolution)\b", text_lower):
        return "Biology"
    if re.search(r"\b(?:chem|chemistry|thermodynamics)\b|acid[\s\-_]*base|chemical\s+bonding", text_lower):
        return "Chemistry"
    if re.search(
        r"\b(?:phy|physics|dynamics|kinematics|vectors|satellites)\b|fluid\s+statics|wave\s+motion|measurement\s+and\s+practical",
        text_lower,
    ):
        return "Physics"
    if re.search(
        r"\b(?:math|maths|mathmatics|mathematics|logarithms|integration|trigonometry|matrices|derivative|calculus|exponential)\b|number\s+system|relations\s+and\s+functions",
        text_lower,
    ):
        return "Mathematics"
    if re.search(
        r"\b(?:aptitude|uat|sat|analogies|analogy|gmat|scholastic)\b",
        text_lower,
    ):
        return "Aptitude (SAT)"
    if re.search(
        r"\b(?:eng|english|englsih|grammar|vocabulary|punctuation|tense|synonym|antonym)\b|"
        r"reading\s*comprehension|sentence\s*comp|parts\s+of\s+speech|subject\s+verb|active\s+and\s+passive|letter\s+writing|"
        r"\b[bc][12]\s+words\b|ke\s+90\s+belay",
        text_lower,
    ):
        return "English"
    if re.search(r"\b(?:geo|geogrph|geography)\b|physical\s+environment\s+of\s+the\s+earth", text_lower):
        return "Geography"
    if re.search(r"\b(?:hist|history)\b", text_lower):
        return "History"
    if re.search(r"\b(?:eco|econ|economics)\b|aggregate\s+demand|consumer\s+theory", text_lower):
        return "Economics"
    if re.search(r"(?<![a-zA-Z])IT(?![a-zA-Z])", original_text) or re.search(
        r"information\s+technology|computer\s+networking", text_lower
    ):
        return "IT"
    if "agriculture" in text_lower:
        return "Agriculture"
    if "psychology" in text_lower:
        return "Psychology"

    if re.search(r"all\s+natural|natural\s+subjects|natural\s+science", text_lower):
        return "All Subjects (Natural)"
    if re.search(r"all\s+social|social\s+subjects|social\s+science", text_lower):
        return "All Subjects (Social)"

    return "General"


def extract_stream(text_lower: str, subject: str) -> str:
    if "natural" in text_lower or subject in ("Biology", "Chemistry", "Physics", "Agriculture"):
        return "Natural"
    if "social" in text_lower or subject in ("Geography", "History", "Economics"):
        return "Social"
    return "General"


def extract_year(text_lower: str) -> str:
    # Year ranges like 2000-2011, 1995-2014, 2012-13
    m_range = re.search(r"(?<![0-9])((?:199|20[0-2])\d)\s*[-–to_]+\s*((?:199|20[0-2])\d)(?![0-9])", text_lower)
    if m_range:
        return f"{m_range.group(1)}-{m_range.group(2)}"

    m_single = re.search(r"(?<![0-9])((?:199|20[0-2])\d)(?![0-9])", text_lower)
    if m_single:
        return m_single.group(1)

    return ""


def extract_round_or_code(text_lower: str) -> str:
    parts = []
    if re.search(r"\b(?:1st|first)\s+round", text_lower):
        parts.append("Round 1")
    elif re.search(r"\b(?:2nd|second)\s+round", text_lower):
        parts.append("Round 2")
    elif re.search(r"\b(?:3rd|third)\s+round(?:el)?", text_lower):
        parts.append("Round 3")

    m_code = re.search(r"\b(?:b\.?\s*code|code|booklet)\s*0*(\d+)", text_lower)
    if m_code:
        parts.append(f"Code {m_code.group(1)}")

    if "oromia" in text_lower:
        parts.append("Oromia")
    elif re.search(r"\baaeb\b", text_lower):
        parts.append("AAEB")

    if re.search(r"\b(?:1st|first)\s+semester", text_lower):
        parts.append("Sem 1")
    elif re.search(r"\b(?:2nd|second)\s+semester", text_lower):
        parts.append("Sem 2")

    return " ".join(parts)


def classify_material(filename: str, caption: str = "") -> dict:
    raw = f"{filename} {caption}".strip()
    # Replace underscores, dots, slashes, brackets with spaces for cleaner word matching
    cleaned = re.sub(r"[_\[\]()@]+", " ", raw)
    cleaned_no_ext = re.sub(r"\.(pdf|pptx|docx)$", "", cleaned, flags=re.IGNORECASE)
    text_lower = cleaned_no_ext.lower()

    grade = extract_grade(text_lower)
    subject = extract_subject(raw, text_lower)
    stream = extract_stream(text_lower, subject)
    year = extract_year(text_lower)
    round_or_code = extract_round_or_code(text_lower)

    has_embedded = bool(
        re.search(
            r"with\s+answers?|with\s+solutions?|with\s+explanations?|solved\s+problems",
            text_lower,
        )
    )

    # Category classification (strict priority order!)
    if re.search(
        r"related\s+(?:content|ontents)|common\s+related\s+chapters|common\s+chapters|matching\s+chapters|"
        r"entrance\s+exam\s+contents?|entrance\s+\w+\s+contents?|study\s+link|\blink\b|uee\s+analysis|"
        r"minimum\s+learning\s+competency|\bmlc\b|table\s+of\s+contents?|contents\s+of",
        text_lower,
    ):
        category = "Related Contents / Guide"
    elif re.search(
        r"study\s+plan|reading\s+plan|reading\s+program|preparation\s+challenge|reading\s+challenge|"
        r"days?\s+challenge|study\s+schedule|study\s+program|academic\s+calendar|orientation|user\s+guide|information\s+by|"
        r"\bfana\s+aptitude\b",
        text_lower,
    ):
        category = "Study Plan / Schedule"
    elif (not has_embedded) and re.search(
        r"answer\s*key|key\s*answer|answer\s*sheet|answersheet|answer\s+of|answer\s+calculation|\banswers?\b",
        text_lower,
    ):
        category = "Answer Sheet"
    elif re.search(
        r"extreme|exam\s+book|dictionary|serway|principles\s+of\s+physics|\bjee\b|gruber|\b501\b|"
        r"advanced\s+worldwide|best\s+sat\s+guide|mental\s+math\s+tricks|secret\s+of\s+uee",
        text_lower,
    ):
        category = "Supplementary Book"
    elif re.search(r"text\s*book|textbook|laboratory\s+manual", text_lower):
        category = "Textbook"
    elif "pilot" in text_lower:
        category = "Pilot Exam"
    elif re.search(r"model|\baaeb\b|oromia\s+201", text_lower):
        category = "Model Exam"
    elif re.search(r"pre[\s\-]*entrance|weekly\s+exam|post\s+test|\bmock\b", text_lower):
        category = "Practice / Weekly Exam"
    elif re.search(r"\b(?:uat|astu|aastu)\b", text_lower):
        category = "University Admission"
    elif re.search(r"entrance|\beuee\b|\besslce\b|\buee\b|\begsece\b|matric", text_lower):
        category = "Entrance Exam"
    elif re.search(r"work\s*sheet|work\s*book|workbook|practice\s+questions|common\s+questions|revision\s+questions|\bquestions\b|\bw$", text_lower):
        category = "Worksheet / Questions"
    elif re.search(
        r"short\s*note|full\s*note|\bnote\b|\bppt\b|live\s+revision|live\s+class|module|competency\s+based|"
        r"chapter|chap|unit|uint|lesson|tense|\bwords\b|part\s+\d|analogy|analogies|special\s+tuitorial",
        text_lower,
    ):
        category = "Short Note / Lesson"
    else:
        category = "Other"

    # Determine Exam_Tag for linking Exams <-> Answer Sheets
    exam_tag = ""
    if category in ("Pilot Exam",):
        exam_tag = "Pilot"
    elif category in ("Model Exam",):
        exam_tag = "Model"
    elif category in ("Practice / Weekly Exam",):
        exam_tag = "Practice"
    elif category in ("University Admission",):
        exam_tag = "UAT"
    elif category in ("Entrance Exam",):
        exam_tag = "Entrance"
    elif category == "Answer Sheet":
        if "pilot" in text_lower:
            exam_tag = "Pilot"
        elif "model" in text_lower or "aaeb" in text_lower or "oromia" in text_lower:
            exam_tag = "Model"
        elif "weekly" in text_lower or "pre-entrance" in text_lower:
            exam_tag = "Practice"
        else:
            exam_tag = "Entrance"

    if category == "Answer Sheet":
        has_embedded = True

    # Build Link Keys for automatic Exam <-> Answer Sheet matching
    base_link_key = ""
    link_key = ""
    if exam_tag and subject != "General" and (category == "Answer Sheet" or not has_embedded):
        yr = year if year else "NOYEAR"
        base_link_key = f"{yr}|{subject}|{exam_tag}"
        link_key = f"{base_link_key}|{round_or_code}" if round_or_code else base_link_key

    return {
        "grade": grade,
        "stream": stream,
        "subject": subject,
        "category": category,
        "year": year,
        "exam_tag": exam_tag,
        "round_or_code": round_or_code,
        "link_key": link_key,
        "base_link_key": base_link_key,
        "has_embedded_answer": "Yes" if has_embedded else "No",
        "normalized_stem": normalize_stem(filename),
    }
