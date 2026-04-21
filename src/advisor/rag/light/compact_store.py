from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_KV_PATH = PROJECT_ROOT / "storage" / "rag_storage" / "kv_store_text_chunks.json"
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "light_rag" / "course_catalog.json"
DEFAULT_SOURCES_DIR = PROJECT_ROOT / "data" / "sources"
DEFAULT_PARSED_CACHE_DIR = PROJECT_ROOT / "data" / "parsed_cache"
STORE_FORMAT_VERSION = 3
GREETING_TERMS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
ABUSIVE_TERMS = {
    "fuck",
    "fucking",
    "shit",
    "bitch",
    "asshole",
    "bastard",
    "damn you",
    "stupid",
    "idiot",
    "moron",
}

PROGRAM_LABELS = {
    "AE": "Aerospace Engineering",
    "AECERT": "Autonomous Engineering Certificate",
    "AICERT": "Artificial Intelligence Certificate",
    "AREN": "Architectural Engineering",
    "BE": "Bioengineering",
    "BEC": "Biomedical Engineering",
    "BE-IMAGING": "Bioengineering Imaging",
    "CIVILE": "Civil Engineering",
    "CM": "Construction Management",
    "COMPE": "Computer Engineering",
    "CSE": "Computer Science",
    "DSCERT": "Data Science Certificate",
    "EE": "Electrical Engineering",
    "IE": "Industrial Engineering",
    "ME": "Mechanical Engineering",
    "MEAE": "Master of Engineering in Aerospace Engineering",
    "MEME": "Master of Engineering in Mechanical Engineering",
    "MSAE": "Master of Science in Aerospace Engineering",
    "MSCOMPE": "Master of Science in Computer Engineering",
    "MSCS": "Master of Science in Computer Science",
    "MSDATAS": "Master of Science in Data Science",
    "MSME": "Master of Science in Mechanical Engineering",
    "MSSE": "Master of Science in Software Engineering",
    "PHDCOMPE": "PhD in Computer Engineering",
    "PHDCS": "PhD in Computer Science",
    "SE": "Software Engineering",
}


@dataclass
class CourseRow:
    course: str
    title: str
    hours: str


YEAR_WORDS = {
    1: {"first", "freshman", "1st"},
    2: {"second", "sophomore", "2nd"},
    3: {"third", "junior", "3rd"},
    4: {"fourth", "senior", "4th"},
}

GRADUATE_HINTS = {
    "ms",
    "m.s",
    "master",
    "masters",
    "graduate",
    "thesis",
    "non-thesis",
    "phd",
    "ph.d",
    "doctoral",
    "certificate",
}

TRENDING_TOPIC_HINTS = [
    "machine learning",
    "data mining",
    "cloud",
    "artificial intelligence",
    "neural",
    "computer vision",
    "robotics",
    "search engines",
    "social networks",
    "distributed systems",
    "parallel processing",
    "database",
    "security",
]

INTEREST_KEYWORDS = {
    "ai": ["artificial intelligence", "machine learning", "neural", "pattern recognition", "computer vision", "robotics", "intelligent systems", "unmanned vehicle"],
    "ml": ["machine learning", "neural", "pattern recognition", "data mining"],
    "cloud": ["cloud", "distributed systems", "database", "big data", "search engines"],
    "security": ["security", "secure", "privacy"],
    "systems": ["distributed systems", "parallel processing", "architecture", "operating systems", "embedded"],
    "data": ["data mining", "database", "web data", "big data", "machine learning"],
}

SECTION_HINTS = {
    "ai": ["intellegent systems/robotics", "intelligent systems", "artificial intelligence", "machine learning"],
    "ml": ["machine learning", "data analytics", "intelligent systems"],
    "cloud": ["cloud computing", "big data management/databases/cloud computing", "systems/architecture/languages"],
    "security": ["security/privacy", "information security"],
    "systems": ["systems/architecture/languages", "embedded systems"],
    "data": ["data analytics/algorithms/theory", "big data management/databases/cloud computing"],
}

COURSE_ALIASES = {
    "AI 1": "CSE 5360",
    "AI I": "CSE 5360",
    "AI 2": "CSE 5361",
    "AI II": "CSE 5361",
    "DAMT": "CSE 5301",
}


def _normalize_program_key(file_name: str) -> str | None:
    base = Path(file_name).stem.upper()
    if base.startswith(("2025-", "2024-", "2022-")):
        base = base.split("-", 1)[1]
    if base in PROGRAM_LABELS:
        return base
    normalized = re.sub(r"[^A-Z0-9-]", "", base)
    if normalized in PROGRAM_LABELS:
        return normalized
    synonyms = {
        "COMPE": "COMPE",
        "COMPUTERENGINEERING": "COMPE",
        "CSE": "CSE",
        "COMPUTERSCIENCE": "CSE",
        "SE": "SE",
        "SOFTWAREENGINEERING": "SE",
        "MSCOMPE": "MSCOMPE",
        "PHDCOMPE": "PHDCOMPE",
        "AI": "AICERT",
        "DS": "DSCERT",
        "AECERTIFICATE": "AECERT",
        "AICERTIFICATE": "AICERT",
        "DATASCIENCECERTIFICATE": "DSCERT",
    }
    return synonyms.get(normalized)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def _extract_semester_label(text: str) -> str | None:
    match = re.search(r"Caption:\s*([^\n]+)", text)
    if not match:
        return None
    label = _clean_text(match.group(1))
    if "Structure:" in label:
        label = _clean_text(label.split("Structure:", 1)[0])
    return label or None


def _extract_table_rows(text: str) -> list[CourseRow]:
    match = re.search(r"Structure:\s*(<table>.*?</table>)", text, flags=re.DOTALL)
    if not match:
        return []
    try:
        root = ET.fromstring(match.group(1))
    except ET.ParseError:
        return []

    rows: list[CourseRow] = []
    for tr in root.findall(".//tr"):
        cells = [_clean_text("".join(td.itertext())) for td in tr.findall("td")]
        if len(cells) < 2:
            continue
        if cells[0].lower() == "course":
            continue
        course_text = cells[0]
        hours_text = cells[1]
        code_match = re.search(r"\b[A-Z]{2,5}\s?\d{4}\b", course_text)
        course_code = code_match.group(0).replace("  ", " ") if code_match else course_text
        title = course_text
        if " - " in course_text:
            title = course_text.split(" - ", 1)[1]
        elif " – " in course_text:
            title = course_text.split(" – ", 1)[1]
        rows.append(CourseRow(course=course_code, title=_clean_text(title), hours=hours_text))
    return rows


def _extract_list_items(text: str) -> list[str]:
    match = re.search(r"'list_items':\s*\[(.*?)\]", text, flags=re.DOTALL)
    if not match:
        return []
    return [_clean_text(item) for item in re.findall(r"'([^']+)'", match.group(1))]


def _extract_plain_chunk_text(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    markers = [
        "Table Analysis:",
        "Image Content Analysis:",
        "Header Content Analysis:",
        "List Content Analysis:",
        "Analysis:",
    ]
    if any(marker in cleaned for marker in markers):
        return ""
    if len(cleaned.split()) < 20:
        return ""
    return cleaned


def _score_text(question: str, text: str) -> float:
    terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    score = 0.0
    lowered = text.lower()
    for term in terms:
        if len(term) > 2 and term in lowered:
            score += 1.0
    codes = re.findall(r"\b[A-Z]{2,5}\s?\d{4}\b", question.upper())
    for code in codes:
        if code.lower() in lowered:
            score += 5.0
    if "spring" in terms and "spring" in lowered:
        score += 2.0
    if "fall" in terms and "fall" in lowered:
        score += 2.0
    return score


def _question_terms(question: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", question.lower()))


def _extract_codes(question: str) -> list[str]:
    codes = re.findall(r"\b[A-Z]{2,5}\s?\d{4}\b", question.upper())
    normalized = [code.replace("  ", " ") for code in codes]
    upper = question.upper()
    for alias, code in COURSE_ALIASES.items():
        if alias in upper and code not in normalized:
            normalized.append(code)
    return normalized


def _detect_year(question: str) -> int | None:
    terms = _question_terms(question)
    for year, aliases in YEAR_WORDS.items():
        if terms.intersection(aliases):
            return year
    return None


def _detect_semester(question: str) -> str | None:
    terms = _question_terms(question)
    if "spring" in terms:
        return "spring"
    if "fall" in terms:
        return "fall"
    return None


def _is_graduate_program_key(program_key: str) -> bool:
    return program_key.startswith(("MS", "PHD")) or program_key in {"MEAE", "MEME", "AECERT", "AICERT", "DSCERT"}


def _is_graduate_intent(question: str) -> bool:
    lowered = _clean_text(question).lower()
    return (
        any(hint in lowered for hint in GRADUATE_HINTS)
        or bool(re.search(r"\b[A-Z]{2,5}\s?[56]\d{3}\b", question.upper()))
        or "damt" in lowered
        or "ai 1" in lowered
        or "ai i" in lowered
    )


def _is_course_discovery_question(question: str) -> bool:
    lowered = _clean_text(question).lower()
    discovery_terms = {"good", "best", "trending", "popular", "recommend", "recommended", "interesting", "smart"}
    course_terms = {"course", "courses", "class", "classes", "elective", "electives"}
    return any(term in lowered for term in discovery_terms) and any(term in lowered for term in course_terms)


def _is_topic_course_query(question: str) -> bool:
    lowered = _clean_text(question).lower()
    course_terms = {"course", "courses", "class", "classes", "elective", "electives"}
    return bool(_extract_interest_topics(question)) and any(term in lowered for term in course_terms)


def _is_admissions_query(question: str) -> bool:
    lowered = _clean_text(question).lower()
    admissions_terms = {
        "admission",
        "admissions",
        "admit",
        "admitted",
        "criteria",
        "requirements",
        "requirement",
        "gpa",
        "gre",
        "statement of purpose",
        "letters of recommendation",
        "recommendation letters",
    }
    return any(term in lowered for term in admissions_terms)


def _needs_clarification(question: str) -> bool:
    lowered = _clean_text(question).lower()
    if len(lowered.split()) <= 4:
        return lowered in {
            "not master's",
            "not masters",
            "this is not master's",
            "this is not masters",
            "wrong answer",
            "this is wrong",
        }
    return False


def _is_greeting(question: str) -> bool:
    cleaned = _clean_text(question).lower().strip("!.?")
    return cleaned in GREETING_TERMS


def _is_offtopic_or_abusive(question: str) -> bool:
    cleaned = _clean_text(question).lower().strip("!.?,")
    if not cleaned:
        return True
    if any(term in cleaned for term in ABUSIVE_TERMS):
        return True

    if _extract_codes(question):
        return False
    if _infer_program_from_question(question):
        return False
    if _is_admissions_query(question):
        return False
    if _is_topic_course_query(question):
        return False
    if _is_course_discovery_question(question):
        return False
    if _looks_like_after_course(question):
        return False

    academic_terms = {
        "course",
        "courses",
        "class",
        "classes",
        "semester",
        "spring",
        "fall",
        "prereq",
        "prerequisite",
        "admission",
        "degree",
        "program",
        "catalog",
        "advisor",
        "advising",
        "graduation",
        "elective",
        "thesis",
        "graduate",
        "undergraduate",
        "requirement",
        "requirements",
    }
    terms = _question_terms(question)
    return not bool(terms.intersection(academic_terms))


def _is_low_signal_query(question: str) -> bool:
    cleaned = _clean_text(question).lower().strip("!.?,")
    if not cleaned:
        return True

    low_signal_terms = {
        "k",
        "kk",
        "ok",
        "okay",
        "okk",
        "cool",
        "fine",
        "hmm",
        "hmmm",
        "huh",
        "yes",
        "no",
        "maybe",
        "sure",
        "thanks",
        "thank you",
        "got it",
    }
    if cleaned in low_signal_terms:
        return True

    if _extract_codes(question):
        return False
    if _infer_program_from_question(question):
        return False
    if _is_admissions_query(question):
        return False
    if _is_topic_course_query(question):
        return False
    if _is_course_discovery_question(question):
        return False
    if _looks_like_after_course(question):
        return False

    academic_terms = {
        "course",
        "courses",
        "class",
        "classes",
        "semester",
        "spring",
        "fall",
        "prereq",
        "prerequisite",
        "admission",
        "degree",
        "program",
        "catalog",
        "advisor",
        "graduation",
        "elective",
        "thesis",
        "graduate",
        "undergraduate",
    }
    terms = _question_terms(question)
    if terms.intersection(academic_terms):
        return False

    return len(terms) <= 2


def _looks_like_after_course(question: str) -> bool:
    q = question.lower()
    return "after" in q or "if i take" in q or "what can i take next" in q or "next semester" in q


def _extract_interest_topics(question: str) -> list[str]:
    lowered = _clean_text(question).lower()
    topics = []
    for topic, hints in INTEREST_KEYWORDS.items():
        if topic in lowered or any(hint in lowered for hint in hints):
            topics.append(topic)
    return topics


def _topic_label(topics: list[str]) -> str:
    if not topics:
        return "this topic"
    labels = {
        "ai": "AI",
        "ml": "machine learning",
        "cloud": "cloud",
        "security": "security",
        "systems": "systems",
        "data": "data",
    }
    return labels.get(topics[0], topics[0].upper())


def _estimate_year_from_courses(courses: list[dict[str, Any]]) -> int | None:
    levels = []
    for course in courses:
        match = re.search(r"\b[A-Z]{2,5}\s?(\d{4})\b", course.get("course", ""))
        if match:
            levels.append(int(match.group(1)))
    if not levels:
        return None
    avg = sum(levels) / len(levels)
    if avg < 2000:
        return 1
    if avg < 3000:
        return 2
    if avg < 4000:
        return 3
    return 4


def _normalize_semester_plans(program_bucket: dict[str, Any]) -> None:
    plans = program_bucket.get("semester_plans", [])
    ordered = []
    fall_count = 0
    spring_count = 0
    for plan in plans:
        semester_label = (plan.get("semester") or "").lower()
        season = "spring" if "spring" in semester_label else "fall" if "fall" in semester_label else "unknown"
        if season == "fall":
            fall_count += 1
            year = fall_count
        elif season == "spring":
            spring_count += 1
            year = spring_count
        else:
            year = None
        estimated_year = _estimate_year_from_courses(plan.get("courses", []))
        if estimated_year:
            year = estimated_year
        plan["season"] = season
        plan["year"] = year
        ordered.append(plan)
    program_bucket["semester_plans"] = ordered


def _match_plans(question: str, plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    season = _detect_semester(question)
    year = _detect_year(question)

    ranked: list[tuple[float, dict[str, Any]]] = []
    for plan in plans:
        score = _score_text(question, plan.get("search_text", ""))
        if season and plan.get("season") == season:
            score += 9.0
        elif season:
            score -= 6.0
        if year and plan.get("year") == year:
            score += 4.0
        elif year and plan.get("year") is not None:
            score -= 1.0
        ranked.append((score, plan))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [plan for score, plan in ranked if score > 0] or [plan for _, plan in ranked]


def _match_follow_up_courses(question: str, notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    codes = _extract_codes(question)
    if not codes:
        return []

    matches: list[dict[str, Any]] = []
    for note in notes:
        text = note.get("text", "")
        lowered = text.lower()
        if "pre-req" not in lowered and "co-req" not in lowered:
            continue
        score = _score_text(question, lowered)
        mentions_target = False
        for code in codes:
            if code.lower() in lowered:
                score += 8.0
                mentions_target = True
        if not mentions_target:
            continue
        if score <= 0:
            continue
        course_match = re.match(r"([A-Z]{2,5}\s?\d{4})", text)
        if not course_match:
            continue
        if course_match.group(1).replace("  ", " ") in codes:
            continue
        semester_match = re.search(r"\(([^)]+)\)", text)
        matches.append(
            {
                "course": course_match.group(1),
                "title": text,
                "hours": "",
                "season_note": semester_match.group(1) if semester_match else "",
                "score": score,
                "source": note.get("source"),
            }
        )

    matches.sort(key=lambda item: item["score"], reverse=True)
    deduped = []
    seen = set()
    for item in matches:
        if item["course"] in seen:
            continue
        seen.add(item["course"])
        deduped.append(item)
        if len(deduped) >= 5:
            break
    return deduped


def _match_courses_by_prereq(question: str, notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    codes = _extract_codes(question)
    if not codes:
        return []

    entry_pattern = re.compile(
        r"\b([A-Z]{2,5}\s?\d{4})\s*[–-]?\s*([^.;\n()]{3,90})"
        r"(?:\s*\(([^)]*(?:pre-req|co-req|prerequisite)[^)]*)\)|\s+(pre-reqs?:[^.;\n]+|co-req[^.;\n]+|prerequisite[s]?:[^.;\n]+))",
        flags=re.IGNORECASE,
    )

    matches: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for note in notes:
        text = note.get("text", "")
        lowered = text.lower()
        if "pre-req" not in lowered and "co-req" not in lowered and "prerequisite" not in lowered:
            continue

        for match in entry_pattern.finditer(text):
            course = match.group(1).replace("  ", " ")
            title = _clean_text(match.group(2)).strip(" -,:;")
            prereq_text = _clean_text(match.group(3) or match.group(4) or "")
            if not prereq_text:
                continue

            title = re.split(r"\b[A-Z]{2,5}\s?\d{4}\b", title)[0].strip(" -,:;")
            prereq_text = prereq_text.split("•", 1)[0].strip()
            prereq_text = re.split(r"\b[A-Z]{2,5}\s?\d{4}\b\s*[–-]", prereq_text)[0].strip(" -,:;")
            if not title:
                continue

            prereq_lower = prereq_text.lower()
            if not any(code.lower() in prereq_lower for code in codes):
                continue

            signature = (course, prereq_text[:120].lower())
            if signature in seen_pairs:
                continue
            seen_pairs.add(signature)

            score = _score_text(question, f"{course} {title} {prereq_text}") + 10.0
            if title.lower().startswith(course.lower()):
                title = title[len(course) :].strip(" -,:;")
            if not title:
                title = course

            matches.append(
                {
                    "course": course,
                    "title": title,
                    "hours": "",
                    "prereq": prereq_text,
                    "source": note.get("source"),
                    "score": score,
                }
            )

    matches.sort(key=lambda item: item["score"], reverse=True)
    deduped = []
    seen = set()
    for item in matches:
        if item["course"] in seen:
            continue
        seen.add(item["course"])
        deduped.append(item)
        if len(deduped) >= 6:
            break
    return deduped


def _match_plan_by_course_code(question: str, plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    codes = _extract_codes(question)
    if not codes:
        return []
    matches: list[tuple[float, dict[str, Any]]] = []
    for plan in plans:
        text = plan.get("search_text", "")
        score = _score_text(question, text)
        for code in codes:
            if code.lower() in text.lower():
                score += 10.0
        if score > 0:
            matches.append((score, plan))
    matches.sort(key=lambda item: item[0], reverse=True)
    return [plan for _, plan in matches[:3]]


def _normalize_program_query(program: str) -> str:
    cleaned = _clean_text(program).upper().replace(" ", "")
    if not cleaned:
        return ""
    if cleaned in PROGRAM_LABELS:
        return cleaned
    for key, label in PROGRAM_LABELS.items():
        if cleaned == label.upper().replace(" ", ""):
            return key
    return cleaned


def _infer_program_from_codes(question: str) -> str:
    codes = _extract_codes(question)
    if not codes:
        return ""

    code = codes[0]
    match = re.match(r"\b([A-Z]{2,5})\s?(\d{4})\b", code)
    if not match:
        return ""

    prefix = match.group(1)
    level = int(match.group(2))
    if prefix == "CSE":
        return "MSCS" if level >= 5000 else "CSE"
    if prefix == "SE":
        return "MSSE" if level >= 5000 else "SE"
    if prefix == "COMPE":
        return "MSCOMPE" if level >= 5000 else "COMPE"
    return ""


def _infer_program_from_question(question: str) -> str:
    lowered = _clean_text(question).lower()
    upper = question.upper()
    if re.search(r"\bCSE\s?[56]\d{3}\b", upper) or "damt" in lowered or "ai 1" in lowered or "ai i" in lowered:
        return "MSCS"
    if "computer science" in lowered and re.search(r"\b(ms|m\.s\.|master|masters|thesis|non-thesis|graduate)\b", lowered):
        return "MSCS"
    if "software engineering" in lowered and re.search(r"\b(ms|m\.s\.|master|masters|graduate)\b", lowered):
        return "MSSE"
    if "computer engineering" in lowered and re.search(r"\b(ms|m\.s\.|master|masters|phd|ph\.d\.|graduate)\b", lowered):
        return "MSCOMPE" if "phd" not in lowered and "ph.d." not in lowered else "PHDCOMPE"
    phrase_map = {
        "ms cs": "MSCS",
        "masters cse": "MSCS",
        "master cse": "MSCS",
        "masters in cse": "MSCS",
        "graduate cse": "MSCS",
        "ms in computer science": "MSCS",
        "ms computer science": "MSCS",
        "masters computer science": "MSCS",
        "master of science in computer science": "MSCS",
        "ms se": "MSSE",
        "ms software engineering": "MSSE",
        "ms data science": "MSDATAS",
        "ms computer engineering": "MSCOMPE",
        "phd cs": "PHDCS",
        "phd computer science": "PHDCS",
        "phd computer engineering": "PHDCOMPE",
        "ai certificate": "AICERT",
        "data science certificate": "DSCERT",
        "ae certificate": "AECERT",
    }
    for phrase, key in phrase_map.items():
        if phrase in lowered:
            return key
    for key, label in PROGRAM_LABELS.items():
        if label.lower() in lowered:
            return key
    for key in PROGRAM_LABELS:
        if re.search(rf"\b{re.escape(key.lower())}\b", lowered):
            return key
    return ""


def _resolve_program_scope(program: str, question: str) -> str:
    selected_key = _normalize_program_query(program)
    code_inferred = _infer_program_from_codes(question)
    if code_inferred:
        return code_inferred
    if selected_key:
        return selected_key
    return _infer_program_from_question(question)


def _build_program_scope(programs: dict[str, Any], selected_program: str) -> list[tuple[str, dict[str, Any]]]:
    selected_key = _normalize_program_query(selected_program)
    if selected_key and selected_key in programs:
        return [(selected_key, programs[selected_key])]
    return list(programs.items())


def _format_note_snippet(text: str, limit: int = 220) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    truncated = cleaned[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{truncated}..."


def _extract_admission_points(notes: list[dict[str, Any]], limit: int = 6) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()
    for note in notes:
        text = _clean_text(note.get("text", ""))
        if not text:
            continue
        lowered = text.lower()
        if "admissions criteria" in lowered:
            idx = lowered.find("admissions criteria")
            text = text[idx:]
            lowered = text.lower()
        if not any(
            term in lowered
            for term in [
                "admissions criteria",
                "admission criteria",
                "unconditional admission",
                "probationary admission",
                "denied",
                "gpa",
                "gre",
                "letters of recommendation",
                "statements of purpose",
                "statement of purpose",
            ]
        ):
            continue

        fragments = re.split(r"(?<=[.!?])\s+|\.\s+(?=[A-Z])", text)
        for fragment in fragments:
            cleaned = _clean_text(fragment).strip(" -")
            if len(cleaned.split()) < 5:
                continue
            lowered_fragment = cleaned.lower()
            if not any(
                term in lowered_fragment
                for term in [
                    "undergraduate degree",
                    "gpa",
                    "computer science",
                    "computer engineering",
                    "software engineering",
                    "gre",
                    "letters of recommendation",
                    "statement of purpose",
                    "deferred/denied",
                    "unconditional admission",
                    "probationary admission",
                    "advanced admission",
                    "math deficiencies",
                ]
            ):
                continue
            signature = lowered_fragment[:180]
            if signature in seen:
                continue
            seen.add(signature)
            points.append(cleaned.rstrip(".") + ".")
            if len(points) >= limit:
                return points
    return points


def _append_note(bucket: dict[str, Any], text: str, source: str, chunk_id: str) -> None:
    cleaned = _clean_text(text)
    if len(cleaned.split()) < 8:
        return
    seen = bucket.setdefault("_note_seen", set())
    signature = cleaned[:240].lower()
    if signature in seen:
        return
    seen.add(signature)
    bucket["notes"].append(
        {
            "text": cleaned[:1200],
            "source": source,
            "chunk_id": chunk_id,
            "search_text": cleaned[:1200],
        }
    )


def _sanitize_catalog_text_for_course_extraction(text: str) -> str:
    cleaned = _clean_text(text)
    cleaned = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2},\s*\d{1,2}:\d{2}\s*[AP]M\b.*", "", cleaned)
    cleaned = re.sub(r"https?://\S+", "", cleaned)
    cleaned = re.sub(r"\bMaster of Science in Computer Science \(Thesis\)\s*\|\s*University of Texas at Arlington.*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bUniversity Catalog\b.*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bAnother course approved by advisor\.\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\b(Networks/IoT/Communications|Systems/Architecture/Languages|Data Analytics/Algorithms/Theory|Security/Privacy|Software Engineering|Embedded Systems|Imaging/Health Informatics/Bioinformation|Intellegent Systems/Robotics|Intelligent Systems/Robotics)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return _clean_text(cleaned)


def _find_parsed_markdown(pdf_path: Path, parsed_cache_dir: Path) -> Path | None:
    stem = pdf_path.stem
    for mode in ("hybrid_auto", "ocr", "auto", "txt"):
        direct = parsed_cache_dir / stem / mode / f"{stem}.md"
        if direct.exists():
            return direct
    matches = sorted(parsed_cache_dir.glob(f"{stem}_*/**/{stem}.md"))
    return matches[0] if matches else None


def _extract_text_chunks_from_pdf(pdf_path: Path, chunk_words: int = 180, overlap_words: int = 40) -> list[str]:
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return []

    page_texts: list[str] = []
    for page in reader.pages:
        text = _clean_text(page.extract_text() or "")
        if text:
            page_texts.append(text)

    if not page_texts:
        return []

    raw_text = "\n\n".join(page_texts)
    paragraphs = [chunk for chunk in re.split(r"\n{2,}", raw_text) if len(chunk.split()) >= 20]
    if paragraphs:
        return paragraphs[:80]

    words = raw_text.split()
    if not words:
        return []

    chunks: list[str] = []
    step = max(1, chunk_words - overlap_words)
    for start in range(0, len(words), step):
        segment = words[start : start + chunk_words]
        if len(segment) < 25:
            continue
        chunks.append(" ".join(segment))
        if len(chunks) >= 80:
            break
    return chunks


def _extract_course_mentions(texts: list[str], limit: int = 6) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    pattern = re.compile(r"\b([A-Z]{2,5}\s?\d{4})\b(?:\s*[–-]\s*|\s+)([^.;\n]{3,90})")
    for text in texts:
        for match in pattern.finditer(text):
            course = match.group(1).replace("  ", " ")
            if course in seen:
                continue
            seen.add(course)
            title = _clean_text(match.group(2))
            results.append({"course": course, "title": title, "hours": ""})
            if len(results) >= limit:
                return results
    return results


def _extract_ranked_course_mentions(question: str, texts: list[str], limit: int = 6) -> list[dict[str, str]]:
    pattern = re.compile(r"\b([A-Z]{2,5}\s?\d{4})\b(?:\s*[–-]\s*|\s+)(.{3,120}?)(?=\s+[A-Z]{2,5}\s?\d{4}\b|$)")
    scored: dict[str, dict[str, Any]] = {}
    topics = _extract_interest_topics(question)

    for text in texts:
        sanitized = _sanitize_catalog_text_for_course_extraction(text)
        for match in pattern.finditer(sanitized):
            course = match.group(1).replace("  ", " ")
            title = _clean_text(match.group(2))
            title = re.sub(r"\b\d+\b.*$", "", title).strip(" -,:;")
            title = re.sub(r"\s{2,}", " ", title)
            if len(title) < 3:
                continue
            prereq = ""
            prereq_match = re.search(r"(pre-reqs?:.*|co-req:.*|co-req .*|prerequisite[s]?:.*)", title, flags=re.IGNORECASE)
            if prereq_match:
                prereq = _clean_text(prereq_match.group(1))
                title = _clean_text(title[: prereq_match.start()]).strip(" -,:;")
                if len(title) < 3:
                    continue
            haystack = f"{course} {title}"
            score = _score_text(question, haystack)
            lowered_title = title.lower()
            for topic in topics:
                for hint in INTEREST_KEYWORDS.get(topic, []):
                    if hint in lowered_title:
                        score += 3.0
            if _is_course_discovery_question(question):
                for hint in TRENDING_TOPIC_HINTS:
                    if hint in lowered_title:
                        score += 3.0
            if _is_graduate_intent(question) and re.search(r"\b[56]\d{3}\b", course):
                score += 2.0
            existing = scored.get(course)
            if not existing or score > existing["score"]:
                scored[course] = {"course": course, "title": title, "hours": "", "prereq": prereq, "score": score}

    ranked = sorted(scored.values(), key=lambda item: item["score"], reverse=True)
    return [{k: v for k, v in item.items() if k != "score"} for item in ranked[:limit] if item["score"] > 0]


def _recommend_next_graduate_courses(question: str, notes: list[dict[str, Any]], limit: int = 6) -> list[dict[str, str]]:
    taken_codes = set(_extract_codes(question))
    topics = _extract_interest_topics(question)
    candidate_courses = _extract_ranked_course_mentions(question, [note.get("text", "") for note in notes], limit=18)
    ranked: list[tuple[float, dict[str, str]]] = []

    for course in candidate_courses:
        code = course.get("course", "")
        title = course.get("title", "")
        lowered = f"{code} {title}".lower()
        if code in taken_codes:
            continue
        score = _score_text(question, lowered)
        if re.search(r"\b[56]\d{3}\b", code):
            score += 2.0
        if topics:
            topic_match = False
            for topic in topics:
                for hint in INTEREST_KEYWORDS.get(topic, []):
                    if hint in lowered:
                        score += 3.0
                        topic_match = True
            if "ai" in topics and any(term in lowered for term in ["artificial intelligence", "machine learning", "neural", "pattern recognition", "robotics", "computer vision"]):
                score += 4.0
                topic_match = True
            if not topic_match:
                score -= 4.0
        ranked.append((score, course))

    ranked.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for score, course in ranked:
        if score <= 0 or course["course"] in seen:
            continue
        seen.add(course["course"])
        results.append(course)
        if len(results) >= limit:
            break
    return results


def _recommend_topic_courses(question: str, notes: list[dict[str, Any]], limit: int = 12) -> list[dict[str, str]]:
    topics = _extract_interest_topics(question)
    if not topics:
        return []

    filtered_notes = notes
    preferred_notes: list[dict[str, Any]] = []
    for topic in topics:
        for note in notes:
            lowered = note.get("text", "").lower()
            if any(hint in lowered for hint in SECTION_HINTS.get(topic, [])):
                preferred_notes.append(note)
    if preferred_notes:
        deduped = []
        seen_chunks = set()
        for note in preferred_notes:
            chunk_id = note.get("chunk_id") or note.get("text", "")[:80]
            if chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)
            deduped.append(note)
        filtered_notes = deduped

    candidate_courses = _extract_ranked_course_mentions(
        question,
        [note.get("text", "") for note in filtered_notes],
        limit=40,
    )
    ranked: list[tuple[float, dict[str, str]]] = []
    for course in candidate_courses:
        text = f"{course.get('course', '')} {course.get('title', '')}".lower()
        score = 0.0
        for topic in topics:
            for hint in INTEREST_KEYWORDS.get(topic, []):
                if hint in text:
                    score += 4.0
            if any(section_hint in text for section_hint in SECTION_HINTS.get(topic, [])):
                score += 2.0
        if score <= 0:
            continue
        ranked.append((score, course))

    ranked.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for _, course in ranked:
        if course["course"] in seen:
            continue
        seen.add(course["course"])
        results.append(course)
        if len(results) >= limit:
            break
    return results


def _build_prereq_lookup(notes: list[dict[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for note in notes:
        text = note.get("text", "")
        lowered = text.lower()
        if "pre-req" not in lowered and "co-req" not in lowered and "prerequisite" not in lowered:
            continue
        course_match = re.match(r"([A-Z]{2,5}\s?\d{4})", text)
        if not course_match:
            continue
        code = course_match.group(1).replace("  ", " ")
        prereq_match = re.search(r"(pre-reqs?:.*|co-req:.*|co-req .*|prerequisite[s]?:.*)", text, flags=re.IGNORECASE)
        if prereq_match:
            lookup[code] = _clean_text(prereq_match.group(1))
    return lookup


def build_compact_store(
    kv_path: Path = DEFAULT_KV_PATH,
    output_path: Path = DEFAULT_STORE_PATH,
) -> Path:
    rows = []
    if kv_path.exists():
        with kv_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

        if isinstance(raw, dict) and "data" in raw:
            rows = raw.get("data", [])
        elif isinstance(raw, dict):
            for chunk_id, value in raw.items():
                if isinstance(value, dict):
                    row = dict(value)
                    row.setdefault("_id", chunk_id)
                    rows.append(row)
        else:
            rows = raw
    programs: dict[str, dict[str, Any]] = {}

    for row in rows:
        source = row.get("file_path") or row.get("full_doc_id") or "unknown"
        program_key = _normalize_program_key(source)
        if not program_key:
            continue

        program_bucket = programs.setdefault(
            program_key,
            {
                "label": PROGRAM_LABELS.get(program_key, program_key),
                "semester_plans": [],
                "notes": [],
            },
        )

        content = row.get("content") or ""
        semester = _extract_semester_label(content)
        table_rows = _extract_table_rows(content)
        if semester and table_rows:
            program_bucket["semester_plans"].append(
                {
                    "semester": semester,
                    "courses": [course.__dict__ for course in table_rows],
                    "source": source,
                    "chunk_id": row.get("_id") or row.get("id"),
                    "search_text": _clean_text(
                        " ".join(
                            [semester]
                            + [f"{course.course} {course.title} {course.hours}" for course in table_rows]
                        )
                    ),
                }
            )

        for item in _extract_list_items(content):
            if re.search(r"\b[A-Z]{2,5}\s?\d{4}\b", item):
                _append_note(program_bucket, item, source, row.get("_id") or row.get("id") or source)

        plain_text = _extract_plain_chunk_text(content)
        if plain_text:
            _append_note(program_bucket, plain_text[:700], source, row.get("_id") or row.get("id") or source)

    for pdf_path in sorted(DEFAULT_SOURCES_DIR.glob("*.pdf")):
        source = pdf_path.name
        program_key = _normalize_program_key(source)
        if not program_key:
            continue

        program_bucket = programs.setdefault(
            program_key,
            {
                "label": PROGRAM_LABELS.get(program_key, program_key),
                "semester_plans": [],
                "notes": [],
            },
        )

        parsed_md = _find_parsed_markdown(pdf_path, DEFAULT_PARSED_CACHE_DIR)
        if parsed_md and parsed_md.exists():
            md_text = parsed_md.read_text(encoding="utf-8", errors="ignore")
            semester_matches = re.findall(
                r"(Spring Semester.*?<table>.*?</table>|Fall Semester.*?<table>.*?</table>)",
                md_text,
                flags=re.DOTALL,
            )
            for idx, section in enumerate(semester_matches):
                semester = _extract_semester_label(f"Caption: {section.split('<table>', 1)[0]}")
                table_rows = _extract_table_rows(f"Structure: <table>{section.split('<table>', 1)[1]}")
                if semester and table_rows:
                    search_text = _clean_text(
                        " ".join(
                            [semester]
                            + [f"{course.course} {course.title} {course.hours}" for course in table_rows]
                        )
                    )
                    if not any(plan.get("search_text") == search_text for plan in program_bucket["semester_plans"]):
                        program_bucket["semester_plans"].append(
                            {
                                "semester": semester,
                                "courses": [course.__dict__ for course in table_rows],
                                "source": source,
                                "chunk_id": f"{source}-md-plan-{idx}",
                                "search_text": search_text,
                            }
                        )
            for block in re.split(r"\n# ", md_text):
                cleaned = _clean_text(block)
                if cleaned:
                    _append_note(program_bucket, cleaned, source, f"{source}-md-note")

        for idx, chunk in enumerate(_extract_text_chunks_from_pdf(pdf_path)):
            _append_note(program_bucket, chunk, source, f"{source}-pdf-{idx}")

    for bucket in programs.values():
        _normalize_semester_plans(bucket)
        bucket.pop("_note_seen", None)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format_version": STORE_FORMAT_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "programs": programs,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def load_compact_store(store_path: Path = DEFAULT_STORE_PATH) -> dict[str, Any]:
    should_rebuild = not store_path.exists()
    if not should_rebuild and store_path.exists():
        current = json.loads(store_path.read_text(encoding="utf-8"))
        should_rebuild = current.get("format_version") != STORE_FORMAT_VERSION
        if not should_rebuild and DEFAULT_KV_PATH.exists():
            should_rebuild = DEFAULT_KV_PATH.stat().st_mtime > store_path.stat().st_mtime
        if not should_rebuild and DEFAULT_SOURCES_DIR.exists():
            latest_source = max((path.stat().st_mtime for path in DEFAULT_SOURCES_DIR.glob("*.pdf")), default=0)
            should_rebuild = latest_source > store_path.stat().st_mtime
        if not should_rebuild:
            return current

    if should_rebuild:
        build_compact_store(DEFAULT_KV_PATH, store_path)
    return json.loads(store_path.read_text(encoding="utf-8"))


def query_compact_store(
    program: str,
    question: str,
    course_filter: str = "",
    store_path: Path = DEFAULT_STORE_PATH,
) -> dict[str, Any]:
    if _is_greeting(question):
        return {
            "summary": "Hello! I'm your UTA Academic Advisor AI. How can I assist you with your academic planning today?",
            "recommendations": [],
            "notes": [],
            "sources": [],
            "mode": "light-rag",
        }
    if _is_offtopic_or_abusive(question):
        return {
            "summary": "I'm sorry, but I specialize in UTA academic advising. I can help with questions about courses, programs, semester plans, prerequisites, admissions, and other topics from our advising PDFs.",
            "recommendations": [],
            "notes": [],
            "sources": [],
            "mode": "light-rag",
        }
    if _is_low_signal_query(question):
        return {
            "summary": "I'd be happy to help! I can assist with questions about UTA courses, programs, semester plans, prerequisites, admissions details, and other academic advising topics from our PDF resources.",
            "recommendations": [],
            "notes": [],
            "sources": [],
            "mode": "light-rag",
        }
    if _needs_clarification(question):
        return {
            "summary": "I understand. To provide the most accurate information, could you please specify the exact program name, such as MSCS, MSSE, or PhD CS? I'll then pull the relevant details from the matching PDF.",
            "recommendations": [],
            "notes": [
                "Examples: 'good courses for MSCS' or 'admission criteria for MS Computer Science'.",
            ],
            "sources": [],
            "mode": "light-rag",
        }

    data = load_compact_store(store_path)
    programs = data.get("programs", {})
    course_filter = _clean_text(course_filter).lower()
    inferred_program = _resolve_program_scope(program, question)
    scoped_programs = _build_program_scope(programs, inferred_program)

    candidate_plans: list[dict[str, Any]] = []
    candidate_notes: list[dict[str, Any]] = []
    all_scoped_notes: list[dict[str, Any]] = []
    for program_key, bucket in scoped_programs:
        semester_plans = list(bucket.get("semester_plans", []))
        notes = list(bucket.get("notes", []))
        if course_filter:
            semester_plans = [
                item for item in semester_plans if course_filter in item.get("search_text", "").lower()
            ] or semester_plans
            notes = [
                item for item in notes if course_filter in item.get("search_text", "").lower()
            ] or notes
        for note in notes:
            score = _score_text(question, note.get("search_text", ""))
            all_scoped_notes.append(
                {
                    **note,
                    "program_key": program_key,
                    "program_label": bucket.get("label", program_key),
                    "_rank_score": score,
                }
            )
        ranked_plans = _match_plans(question, semester_plans)
        for idx, plan in enumerate(ranked_plans[:3]):
            candidate_plans.append(
                {
                    **plan,
                    "program_key": program_key,
                    "program_label": bucket.get("label", program_key),
                    "_rank_score": 100 - idx + _score_text(question, plan.get("search_text", "")),
                }
            )
        ranked_notes = sorted(
            notes,
            key=lambda item: _score_text(question, item.get("search_text", "")),
            reverse=True,
        )
        for idx, note in enumerate(ranked_notes[:6]):
            score = _score_text(question, note.get("search_text", ""))
            if score <= 0:
                continue
            candidate_notes.append(
                {
                    **note,
                    "program_key": program_key,
                    "program_label": bucket.get("label", program_key),
                    "_rank_score": 100 - idx + score,
                }
            )

    candidate_plans.sort(key=lambda item: item["_rank_score"], reverse=True)
    candidate_notes.sort(key=lambda item: item["_rank_score"], reverse=True)
    best_plan = candidate_plans[0] if candidate_plans else None
    if best_plan and _is_graduate_intent(question) and not _is_graduate_program_key(best_plan.get("program_key", "")):
        best_plan = None
    admissions_query = _is_admissions_query(question)
    admission_points = _extract_admission_points(candidate_notes + all_scoped_notes) if admissions_query else []
    topic_courses = _recommend_topic_courses(question, all_scoped_notes) if _is_topic_course_query(question) else []
    graduate_next_courses = (
        _recommend_next_graduate_courses(question, all_scoped_notes)
        if _is_graduate_intent(question) and ("next semester" in question.lower() or "suggest" in question.lower())
        else []
    )
    follow_up_courses = _match_follow_up_courses(question, candidate_notes) if _looks_like_after_course(question) else []
    prereq_matches = _match_courses_by_prereq(question, candidate_notes)
    explicit_course_plans = _match_plan_by_course_code(question, candidate_plans)
    if _is_graduate_intent(question):
        explicit_course_plans = [plan for plan in explicit_course_plans if _is_graduate_program_key(plan.get("program_key", ""))]

    sources: list[str] = []
    for item in [best_plan, *follow_up_courses, *prereq_matches, *candidate_notes[:3]]:
        if not item:
            continue
        source = item.get("source")
        if source and source not in sources:
            sources.append(source)

    top_note_texts = [_format_note_snippet(note["text"]) for note in candidate_notes[:3]]
    graduate_intent = _is_graduate_intent(question)
    course_discovery = _is_course_discovery_question(question)

    if _looks_like_after_course(question) and not follow_up_courses and _extract_codes(question):
        target_code = _extract_codes(question)[0]
        if _is_graduate_intent(question):
            summary = (
                f"I found {target_code} in the graduate PDF scope, but I couldn't identify clear prerequisite-based next-course recommendations from the extracted notes."
            )
            notes_out = [
                "Try specifying your area of interest, for example 'After CSE 5301, what AI-related courses should I consider next semester?'",
            ]
        else:
            summary = (
                f"I found {target_code} in the advising PDFs, but I couldn't find specific follow-up course recommendations in the prerequisite notes."
            )
            notes_out = [
                "Try including the program name, for example 'After CSE 4344 in CSE, what can I take next?'",
            ]
        recommendations = []
    elif admissions_query and admission_points:
        if program or inferred_program:
            program_label = programs.get(inferred_program, {}).get("label", inferred_program or "the selected program")
            summary = f"Based on the information from {program_label}, here are the admission criteria:"
        else:
            summary = "Based on the matching graduate PDF, here are the admission criteria:"
        recommendations = [{"course": "", "title": point, "hours": ""} for point in admission_points]
        notes_out = []
    elif topic_courses:
        source_name = all_scoped_notes[0]["source"] if all_scoped_notes else "the selected PDF"
        topic_name = _topic_label(_extract_interest_topics(question))
        prereq_lookup = _build_prereq_lookup(all_scoped_notes)
        topic_courses = [
            {**course, "prereq": prereq_lookup.get(course.get("course", ""), course.get("prereq", ""))}
            for course in topic_courses
        ]
        if program or inferred_program:
            program_label = programs.get(inferred_program, {}).get("label", inferred_program or "the selected program")
            summary = f"Based on {program_label}, here are some recommended courses for {topic_name}:"
        else:
            summary = f"Across the advising PDFs, here are some courses related to {topic_name}:"
        if "prereq" in question.lower() or "prerequisite" in question.lower():
            summary += " Please note that prerequisites are not detailed in this section of the PDF."
        recommendations = topic_courses
        notes_out = []
    elif graduate_next_courses:
        source_name = candidate_notes[0]["source"] if candidate_notes else "the graduate catalog PDF"
        topics = _extract_interest_topics(question)
        topic_note = ""
        if topics:
            topic_note = f" with your interest in {topics[0].upper()}"
        summary = (
            f"From {source_name}, here are some excellent graduate courses to consider for your upcoming semester{topic_note}."
        )
        recommendations = graduate_next_courses
        notes_out = [
            f"I based this on the graduate course and specialization lists in {source_name}, not the undergraduate semester plans.",
            "Please note that course offerings can vary by semester, so check the current schedule.",
            "For personalized semester planning, consult with your academic advisor.",
        ]
    elif follow_up_courses:
        target_code = _extract_codes(question)[0] if _extract_codes(question) else "that course"
        related_plan = explicit_course_plans[0] if explicit_course_plans else None
        plan_hint = ""
        if related_plan:
            plan_hint = (
                f" {target_code} appears in {related_plan['semester']} for {related_plan['program_label']}."
            )
        summary = (
            f"Based on the prerequisite information in our advising PDFs, here are some strong follow-up courses after {target_code}.{plan_hint}"
        )
        recommendations = [
            {"course": item["course"], "title": item["title"], "hours": item.get("season_note", "")}
            for item in follow_up_courses
        ]
        notes_out = []
    elif "prereq" in question.lower() or "prerequisite" in question.lower() or "need " in question.lower():
        summary = "Based on our advising PDFs, here are courses that mention your target course in their prerequisite notes."
        recommendations = prereq_matches
        notes_out = [] if prereq_matches else (top_note_texts[:2] or [
            "I couldn't find a clear prerequisite match. Try including an exact course code like CSE 3318.",
        ])
    elif explicit_course_plans:
        target_code = _extract_codes(question)[0]
        matching_plan = explicit_course_plans[0]
        if matching_plan.get("semester"):
            summary = (
                f"According to the advising PDF, {target_code} is scheduled in {matching_plan['semester']} for the {matching_plan['program_label']} program."
            )
        else:
            summary = f"{target_code} appears in the course list for {matching_plan['program_label']} in our advising PDFs."
        recommendations = matching_plan["courses"][:6]
        notes_out = []
    elif best_plan:
        summary = (
            f"The closest match I found in our advising PDFs is {best_plan['semester']} "
            f"for the {best_plan['program_label']} program."
        )
        if best_plan.get("year"):
            summary = (
                f"The closest match I found is {best_plan['semester']} for year {best_plan['year']} "
                f"in the {best_plan['program_label']} program."
            )
        recommendations = best_plan["courses"][:6]
        notes_out = []
    elif candidate_notes:
        top_note = candidate_notes[0]
        lowered_question = question.lower()
        should_suggest_courses = any(
            term in lowered_question for term in ["course", "courses", "class", "classes", "take", "elective", "recommend"]
        )
        extracted_courses = (
            _extract_ranked_course_mentions(question, [note["text"] for note in candidate_notes[:6]])
            if should_suggest_courses
            else []
        )
        if course_discovery and extracted_courses:
            summary = (
                f"Based on the course options in {top_note['source']} for {top_note['program_label']}, "
                "here are some excellent courses to consider."
            )
            notes_out = []
        else:
            summary = (
                f"I found the most relevant information in {top_note['source']} for {top_note['program_label']} "
                "and pulled the answer from the latest PDF content."
            )
        recommendations = extracted_courses
        if not (course_discovery and extracted_courses):
            notes_out = []
    else:
        if graduate_intent:
            summary = (
                "I couldn't find a confident match in the graduate program PDFs. "
                "Please try specifying the exact program name like MSCS, MSSE, MS Data Science, or PhD CS."
            )
        else:
            summary = (
                "I searched through the advising content but couldn't find a confident match. "
                "Try including a program name, semester, or exact course code for better results."
            )
        recommendations = []
        notes_out = top_note_texts[:2] or [
            "Examples: 'junior spring courses for CSE' or 'what can I take after CSE 4344?'",
        ]

    return {
        "summary": summary,
        "recommendations": recommendations,
        "notes": notes_out[:3],
        "sources": sources[:3],
        "mode": "light-rag",
    }
