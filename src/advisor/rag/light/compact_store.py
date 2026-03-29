from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_KV_PATH = PROJECT_ROOT / "storage" / "rag_storage" / "kv_store_text_chunks.json"
DEFAULT_STORE_PATH = PROJECT_ROOT / "data" / "light_rag" / "course_catalog.json"
STORE_FORMAT_VERSION = 3
GREETING_TERMS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}

PROGRAM_LABELS = {
    "AE": "Aerospace Engineering",
    "AREN": "Architectural Engineering",
    "BE": "Bioengineering",
    "BEC": "Biomedical Engineering",
    "BE-IMAGING": "Bioengineering Imaging",
    "CIVILE": "Civil Engineering",
    "CM": "Construction Management",
    "COMPE": "Computer Engineering",
    "CSE": "Computer Science",
    "EE": "Electrical Engineering",
    "IE": "Industrial Engineering",
    "ME": "Mechanical Engineering",
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


def _normalize_program_key(file_name: str) -> str | None:
    base = Path(file_name).stem.upper()
    if base.startswith(("2025-", "2024-", "2022-")):
        return base.split("-", 1)[1]
    return None


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
    return re.findall(r"\b[A-Z]{2,5}\s?\d{4}\b", question.upper())


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


def _is_greeting(question: str) -> bool:
    cleaned = _clean_text(question).lower().strip("!.?")
    return cleaned in GREETING_TERMS


def _looks_like_after_course(question: str) -> bool:
    q = question.lower()
    return "after" in q or "if i take" in q or "what can i take next" in q


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

    matches: list[dict[str, Any]] = []
    for note in notes:
        text = note.get("text", "")
        lowered = text.lower()
        if "pre-req" not in lowered and "co-req" not in lowered:
            continue
        score = _score_text(question, text)
        for code in codes:
            if code.lower() in lowered:
                score += 8.0
        if score <= 0:
            continue
        course_match = re.match(r"([A-Z]{2,5}\s?\d{4})", text)
        title = text.split(" pre-reqs:", 1)[0].split(" co-req", 1)[0]
        matches.append(
            {
                "course": course_match.group(1) if course_match else title,
                "title": title,
                "hours": "",
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


def _infer_program_from_question(question: str) -> str:
    lowered = _clean_text(question).lower()
    for key, label in PROGRAM_LABELS.items():
        if label.lower() in lowered:
            return key
    for key in PROGRAM_LABELS:
        if re.search(rf"\b{re.escape(key.lower())}\b", lowered):
            return key
    return ""


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


def build_compact_store(
    kv_path: Path = DEFAULT_KV_PATH,
    output_path: Path = DEFAULT_STORE_PATH,
) -> Path:
    if not kv_path.exists():
        raise FileNotFoundError(f"Missing source chunks file: {kv_path}")

    with kv_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if isinstance(raw, dict) and "data" in raw:
        rows = raw.get("data", [])
    elif isinstance(raw, dict):
        rows = []
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
                program_bucket["notes"].append(
                    {
                        "text": item,
                        "source": source,
                        "chunk_id": row.get("_id") or row.get("id"),
                        "search_text": item,
                    }
                )

        plain_text = _extract_plain_chunk_text(content)
        if plain_text:
            program_bucket["notes"].append(
                {
                    "text": plain_text[:700],
                    "source": source,
                    "chunk_id": row.get("_id") or row.get("id"),
                    "search_text": plain_text[:700],
                }
            )

    for bucket in programs.values():
        _normalize_semester_plans(bucket)

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
        if not should_rebuild:
            return current

    if should_rebuild:
        if DEFAULT_KV_PATH.exists():
            build_compact_store(DEFAULT_KV_PATH, store_path)
        else:
            raise FileNotFoundError(
                f"Missing compact store: {store_path}. Also could not find {DEFAULT_KV_PATH} to build it."
            )
    return json.loads(store_path.read_text(encoding="utf-8"))


def query_compact_store(
    program: str,
    question: str,
    course_filter: str = "",
    store_path: Path = DEFAULT_STORE_PATH,
) -> dict[str, Any]:
    if _is_greeting(question):
        return {
            "summary": "Hi! I can help with UTA degree plans, semester planning, course sequencing, and prerequisite questions.",
            "recommendations": [],
            "notes": [
                "You can leave program empty and ask naturally.",
                "Try questions like 'third-year spring courses for CSE' or 'what can I take after CSE 4344?'.",
            ],
            "sources": [],
            "mode": "light-rag",
        }

    data = load_compact_store(store_path)
    programs = data.get("programs", {})
    course_filter = _clean_text(course_filter).lower()
    scoped_programs = _build_program_scope(programs, program or _infer_program_from_question(question))

    candidate_plans: list[dict[str, Any]] = []
    candidate_notes: list[dict[str, Any]] = []
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
    follow_up_courses = _match_follow_up_courses(question, candidate_notes) if _looks_like_after_course(question) else []
    prereq_matches = _match_courses_by_prereq(question, candidate_notes)
    explicit_course_plans = _match_plan_by_course_code(question, candidate_plans)

    sources: list[str] = []
    for item in [best_plan, *follow_up_courses, *prereq_matches, *candidate_notes[:3]]:
        if not item:
            continue
        source = item.get("source")
        if source and source not in sources:
            sources.append(source)

    top_note_texts = [_format_note_snippet(note["text"]) for note in candidate_notes[:3]]

    if follow_up_courses:
        target_code = _extract_codes(question)[0] if _extract_codes(question) else "that course"
        related_plan = explicit_course_plans[0] if explicit_course_plans else None
        plan_hint = ""
        if related_plan:
            plan_hint = (
                f" {target_code} appears in {related_plan['semester']} for {related_plan['program_label']}."
            )
        summary = (
            f"Based on the prerequisite notes in the advising PDFs, these are strong follow-up options after {target_code}."
            f"{plan_hint}"
        )
        recommendations = [
            {"course": item["course"], "title": item["title"], "hours": item.get("season_note", "")}
            for item in follow_up_courses
        ]
        notes_out = [
            "These matches come from prerequisite and co-requisite lists extracted from the source PDFs.",
            "Add a semester like fall or spring if you want the list narrowed further.",
        ]
    elif "prereq" in question.lower() or "prerequisite" in question.lower() or "need " in question.lower():
        summary = "These courses mention your target course in the extracted prerequisite notes from the advising PDFs."
        recommendations = prereq_matches
        notes_out = [
            "Each result comes from a prerequisite line in the source degree-planning material.",
            "Use a follow-up question like 'which of these are offered in spring?' to narrow it down.",
        ] if prereq_matches else (top_note_texts[:2] or [
            "I did not find a clear prerequisite match yet. Try adding an exact course code like CSE 3318.",
        ])
    elif explicit_course_plans:
        target_code = _extract_codes(question)[0]
        matching_plan = explicit_course_plans[0]
        summary = (
            f"{target_code} shows up in {matching_plan['semester']} for {matching_plan['program_label']} "
            f"in the advising PDF sequence."
        )
        recommendations = matching_plan["courses"][:6]
        notes_out = top_note_texts[:2] or [
            "This semester plan comes directly from the extracted course table in the source PDF.",
        ]
    elif best_plan:
        summary = (
            f"The closest match I found in the advising PDFs is {best_plan['semester']} "
            f"for {best_plan['program_label']}."
        )
        if best_plan.get("year"):
            summary = (
                f"The closest match I found is {best_plan['semester']} for year {best_plan['year']} "
                f"in {best_plan['program_label']}."
            )
        recommendations = best_plan["courses"][:6]
        notes_out = top_note_texts[:2] or [
            "This answer is pulled from the extracted semester-plan tables in the source PDF.",
            "Add a course code or a semester for an even tighter answer.",
        ]
    else:
        summary = (
            "I searched the extracted advising content but did not find a confident match yet. "
            "Try adding a program name, a semester, or an exact course code."
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
