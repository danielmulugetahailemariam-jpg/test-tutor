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
    stem = re.sub(r"\.(pdf|pptx|docx)$", "", filename.strip(), flags=re.IGNORECASE)
    stem = re.sub(r"(_compressed|\s*\(\d+\))+$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\s*\(\d+\)", "", stem)
    stem = re.sub(r"[_\-\s]+", " ", stem).strip().lower()
    return stem


def extract_grade(text_lower: str) -> str:
    if re.search(r"(?:9\s*(?:-|to|and|,)\s*12|9\s*,\s*10\s*,\s*11\s*,\s*12)", text_lower):
        return "Grade 9-12"
    if re.search(r"(?:11\s*(?:&|and|-|to)\s*12)", text_lower):
        return "Grade 11-12"
    if re.search(r"(?:9\s*(?:&|and|-|to)\s*10)", text_lower):
        return "Grade 9-10"
    if re.search(r"(?:10\s*(?:&|and|-|to)\s*11)", text_lower):
        return "Grade 10-11"

    # Check Grades 12 down to 1 so "12" never matches "1"
    for n in (12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1):
        if re.search(
            rf"(?:\bgrade|\bgr\.?|\bg|\bclass|\bkutaa)\s*[.\-_\s]*{n}(?!\d)|"
            rf"\b{n}(?:st|nd|rd|th)\s+(?:grade|gr\.?)\b|"
            rf"\b(?:chem|chemistry|bio|biology|phy|physics|math|maths|geo|geog|geography|"
            rf"hist|history|eco|econ|economics|eng|english|civics|amharic|oromo|science)[.\-_\s]*{n}(?!\d)",
            text_lower,
        ):
            return f"Grade {n}"

    if "remedial" in text_lower:
        return "Remedial"
    if "freshman" in text_lower or "fresh man" in text_lower:
        return "Freshman"

    if re.search(
        r"\b(?:euee|esslce|uee|matric|entrance|pilot|model|uat|astu|aastu|sat|"
        r"post\s*test|pre[\s\-]*entrance|analogies|analogy)\b",
        text_lower,
    ):
        return "Grade 12"

    if re.search(r"\bministry\b", text_lower):
        return "Grade 8"

    return "General"


def extract_subject(original_text: str, text_lower: str) -> str:
    num_opt = r"(?:1[0-2]|[1-9])?"
    if re.search(rf"\b(?:bio|biology){num_opt}\b|\b(?:genetics|enzymes|evolution)\b", text_lower):
        return "Biology"
    if re.search(rf"\b(?:chem|chemistry){num_opt}\b|\bthermodynamics\b|acid[\s\-_]*base|chemical\s+bonding", text_lower):
        return "Chemistry"
    if re.search(
        rf"\b(?:phy|physics){num_opt}\b|\b(?:dynamics|kinematics|vectors|satellites)\b|"
        r"fluid\s+statics|wave\s+motion|measurement\s+and\s+practical",
        text_lower,
    ):
        return "Physics"
    if re.search(
        rf"\b(?:math|maths|mathmatics|mathematics){num_opt}\b|"
        r"\b(?:logarithms|integration|trigonometry|matrices|derivative|calculus|exponential)\b|"
        r"number\s+system|relations\s+and\s+functions",
        text_lower,
    ):
        return "Mathematics"
    if re.search(r"\b(?:aptitude|uat|sat|analogies|analogy|gmat|scholastic)\b", text_lower):
        return "Aptitude (SAT)"
    if re.search(
        rf"\b(?:eng|english|englsih){num_opt}\b|\b(?:grammar|vocabulary|punctuation|tense|synonym|antonym)\b|"
        r"reading\s*comprehension|sentence\s*comp|parts\s+of\s+speech|subject\s+verb|"
        r"active\s+and\s+passive|letter\s+writing|\b[bc][12]\s+words\b|ke\s+90\s+belay",
        text_lower,
    ):
        return "English"
    if re.search(rf"\b(?:geo|geog|geogrph|geography){num_opt}\b|physical\s+environment\s+of\s+the\s+earth", text_lower):
        return "Geography"
    if re.search(rf"\b(?:hist|history){num_opt}\b", text_lower):
        return "History"
    if re.search(rf"\b(?:eco|econ|economics){num_opt}\b|aggregate\s+demand|consumer\s+theory", text_lower):
        return "Economics"
    if re.search(rf"\b(?:civics|citizenship|moral){num_opt}\b", text_lower):
        return "Civics / Citizenship"
    if re.search(rf"\b(?:amharic|amh){num_opt}\b|አማርኛ", text_lower):
        return "Amharic"
    if re.search(rf"\b(?:afaan\s*oromoo?|oromo|oromiffa){num_opt}\b", text_lower):
        return "Afaan Oromoo"
    if re.search(r"general\s+science", text_lower):
        return "General Science"
    if re.search(r"environmental\s+science", text_lower):
        return "Environmental Science"
    if re.search(r"social\s+studies", text_lower):
        return "Social Studies"
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
    m_range = re.search(r"(?<![0-9])((?:199|20[0-2])\d)\s*[-–to_]+\s*((?:199|20[0-2])\d)(?![0-9])", text_lower)
    if m_range:
        return f"{m_range.group(1)}-{m_range.group(2)}"
    m_single = re.search(r"(?<![0-9])((?:199|20[0-2])\d)(?![0-9])", text_lower)
    return m_single.group(1) if m_single else ""


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


def classify_material(filename: str, caption: str = "", folder_path: str = "") -> dict:
    raw = f"{filename} {caption}".strip()
    cleaned = re.sub(r"[_\[\]()@]+", " ", raw)
    cleaned_no_ext = re.sub(r"\.(pdf|pptx|docx)$", "", cleaned, flags=re.IGNORECASE)
    text_lower = cleaned_no_ext.lower()

    folder_cleaned = re.sub(r"[_\[\]()@/\\]+", " ", folder_path or "").strip()
    folder_lower = folder_cleaned.lower()

    grade = extract_grade(text_lower)
    if grade == "General" and folder_lower:
        grade = extract_grade(folder_lower)

    subject = extract_subject(raw, text_lower)
    if subject == "General" and folder_lower:
        subject = extract_subject(folder_cleaned, folder_lower)

    stream = extract_stream(text_lower, subject)
    if stream == "General" and folder_lower:
        stream = extract_stream(folder_lower, subject)

    year = extract_year(text_lower)
    if not year and folder_lower:
        year = extract_year(folder_lower)

    round_or_code = extract_round_or_code(text_lower)

    has_embedded = bool(
        re.search(r"with\s+answers?|with\s+solutions?|with\s+explanations?|solved\s+problems", text_lower)
    )

    if re.search(
        r"related\s+(?:content|ontents)|common\s+related\s+chapters|common\s+chapters|matching\s+chapters|"
        r"entrance\s+exam\s+contents?|entrance\s+\w+\s+contents?|study\s+link|\blink\b|uee\s+analysis|"
        r"minimum\s+learning\s+competency|\bmlc\b|table\s+of\s+contents?|contents\s+of",
        text_lower,
    ):
        category = "Related Contents / Guide"
    elif re.search(
        r"study\s+plan|reading\s+plan|reading\s+program|preparation\s+challenge|reading\s+challenge|"
        r"days?\s+challenge|study\s+schedule|study\s+program|academic\s+calendar|orientation|user\s+guide|information\s+by|\bfana\s+aptitude\b",
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

    exam_tag = ""
    if category == "Pilot Exam":
        exam_tag = "Pilot"
    elif category == "Model Exam":
        exam_tag = "Model"
    elif category == "Practice / Weekly Exam":
        exam_tag = "Practice"
    elif category == "University Admission":
        exam_tag = "UAT"
    elif category == "Entrance Exam":
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
