from __future__ import annotations

import json
import html
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from xml.etree import ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cli.graph_rag import load_vdb


DEFAULT_RAG_DIR = PROJECT_ROOT / "rag_storage"
CHAT_DIR = DEFAULT_RAG_DIR / "chat_ui"
CHAT_MEMORY_FILE = DEFAULT_RAG_DIR / "chat_memory.json"

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
class RetrievedChunk:
    score: float
    chunk_id: str
    source: str
    content: str
    search_text: str = ""


@dataclass
class CourseRow:
    course: str
    hours: str
    semester: str | None = None


def _normalize_program_key(file_name: str) -> str | None:
    base = Path(file_name).stem.upper()
    if base.startswith("2025-") or base.startswith("2024-") or base.startswith("2022-"):
        return base.split("-", 1)[1]
    return None


def _program_options(kv: dict[str, dict]) -> list[tuple[str, str]]:
    found = {}
    for row in kv.values():
        source = row.get("file_path") or row.get("full_doc_id") or ""
        key = _normalize_program_key(source)
        if key:
            found[key] = PROGRAM_LABELS.get(key, key)
    options = [("All Programs", "__all__")]
    options.extend((label, key) for key, label in sorted(
        found.items(), key=lambda item: item[1]))
    return options


def _course_keywords(text: str) -> list[str]:
    return sorted(set(re.findall(r"\b[A-Z]{2,4}\s?\d{4}\b", text.upper())))


def _question_terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _extract_semester_label(text: str) -> str | None:
    match = re.search(r"Caption:\s*([A-Za-z ]+Semester[^\\n]*)", text)
    if match:
        return " ".join(match.group(1).split())
    return None


def _extract_table_rows(text: str) -> list[CourseRow]:
    match = re.search(r"Structure:\s*(<table>.*?</table>)",
                      text, flags=re.DOTALL)
    if not match:
        return []
    table_html = html.unescape(match.group(1))
    try:
        root = ET.fromstring(table_html)
    except ET.ParseError:
        return []

    semester = _extract_semester_label(text)
    rows: list[CourseRow] = []
    for tr in root.findall(".//tr"):
        cells = [" ".join("".join(td.itertext()).split())
                 for td in tr.findall("td")]
        if len(cells) < 2:
            continue
        if cells[0].strip().lower() == "course":
            continue
        rows.append(
            CourseRow(course=cells[0], hours=cells[1], semester=semester))
    return rows


def _extract_list_items(text: str) -> list[str]:
    match = re.search(r"'list_items':\s*\[(.*?)\]", text, flags=re.DOTALL)
    if not match:
        return []
    raw = match.group(1)
    items = re.findall(r"'([^']+)'", raw)
    return [" ".join(item.split()) for item in items]


def _clean_course_text(text: str) -> str:
    text = html.unescape(" ".join(text.split()))
    text = text.replace("&", "&")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_real_course_row(row: CourseRow) -> bool:
    course = _clean_course_text(row.course)
    if "<" in course or "Structure:" in course or "Analysis:" in course:
        return False
    if len(course) < 4:
        return False
    return bool(
        re.search(r"\b[A-Z]{2,5}\s?\d{4}\b", course)
        or "elective" in course.lower()
        or "government" in course.lower()
        or "history" in course.lower()
        or "communication" in course.lower()
    )


def _score_course_row(row: CourseRow, terms: set[str], explicit_codes: list[str]) -> float:
    hay = f"{row.course} {row.semester or ''}".lower()
    score = 0.0
    for term in terms:
        if term and term in hay:
            score += 1.0
    for code in explicit_codes:
        if code.lower() in hay:
            score += 3.0
    if "spring" in terms and row.semester and "spring" in row.semester.lower():
        score += 2.0
    if "fall" in terms and row.semester and "fall" in row.semester.lower():
        score += 2.0
    return score


def _best_course_rows(question: str, chunks: list[RetrievedChunk]) -> list[CourseRow]:
    terms = _question_terms(question)
    explicit_codes = _course_keywords(question)
    rows: list[tuple[float, CourseRow]] = []
    for chunk in chunks:
        for row in _extract_table_rows(chunk.content):
            if not _is_real_course_row(row):
                continue
            row = CourseRow(
                course=_clean_course_text(row.course),
                hours=_clean_course_text(row.hours),
                semester=_clean_course_text(
                    row.semester) if row.semester else None,
            )
            score = _score_course_row(row, terms, explicit_codes)
            if score > 0 or row.semester:
                rows.append((score, row))

    rows.sort(key=lambda item: item[0], reverse=True)
    seen = set()
    picked: list[CourseRow] = []
    for _, row in rows:
        key = (row.course, row.semester)
        if key in seen:
            continue
        seen.add(key)
        picked.append(row)
        if len(picked) >= 8:
            break
    return picked


def _best_prereq_items(question: str, chunks: list[RetrievedChunk]) -> list[str]:
    explicit_codes = _course_keywords(question)
    terms = _question_terms(question)
    items: list[tuple[float, str]] = []
    for chunk in chunks:
        for item in _extract_list_items(chunk.content):
            low = item.lower()
            score = 0.0
            for code in explicit_codes:
                if code.lower() in low:
                    score += 4.0
            for term in terms:
                if term in low:
                    score += 0.4
            if score > 0:
                items.append((score, item))
    items.sort(key=lambda item: item[0], reverse=True)
    seen = set()
    result = []
    for _, item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= 4:
            break
    return result


def _question_looks_like_masters(question: str) -> bool:
    q = question.lower()
    return bool(re.search(r"\b(ms|m\.s\.|masters|master's|graduate)\b", q))


def _build_chunk_records(kv: dict[str, dict], program_filter: str, course_filter: str) -> list[RetrievedChunk]:
    records: list[RetrievedChunk] = []
    course_filter = course_filter.strip().lower()
    for chunk_id, row in kv.items():
        source = row.get("file_path") or row.get("full_doc_id") or "unknown"
        program_key = _normalize_program_key(source)
        if program_filter != "__all__" and program_key != program_filter:
            continue

        content = (row.get("content") or "").strip()
        if not content:
            continue

        if course_filter and course_filter not in content.lower():
            continue

        search_text = content
        if "Structure:" in content:
            rows = _extract_table_rows(content)
            if rows:
                search_text = " ".join(
                    f"{row.semester or ''} {row.course} {row.hours}"
                    for row in rows
                )
        elif "list_items" in content:
            items = _extract_list_items(content)
            if items:
                search_text = " ".join(items)

        records.append(
            RetrievedChunk(
                score=0.0,
                chunk_id=chunk_id,
                source=source,
                content=content,
                search_text=search_text,
            )
        )
    return records


@st.cache_data(show_spinner=False)
def _get_program_records(program_filter: str) -> list[RetrievedChunk]:
    _, _, kv = _load_index()
    return _build_chunk_records(kv, program_filter, "")


def _candidate_records(question: str, records: list[RetrievedChunk], limit: int = 120) -> list[RetrievedChunk]:
    terms = _question_terms(question)
    codes = _course_keywords(question)
    scored: list[tuple[float, RetrievedChunk]] = []
    for record in records:
        hay = record.search_text.lower() if record.search_text else record.content.lower()
        score = 0.0
        for code in codes:
            if code.lower() in hay:
                score += 6.0
        for term in terms:
            if len(term) > 2 and term in hay:
                score += 1.0
        if "spring" in terms and "spring" in hay:
            score += 2.0
        if "fall" in terms and "fall" in hay:
            score += 2.0
        scored.append((score, record))

    scored.sort(key=lambda item: item[0], reverse=True)
    picked = [record for score, record in scored[:limit] if score > 0]
    return picked or [record for _, record in scored[: min(limit, len(scored))]]


def _retrieve_chunks(question: str, records: list[RetrievedChunk], topk: int) -> list[RetrievedChunk]:
    if not records:
        return []

    candidates = _candidate_records(question, records, limit=80)
    docs = [record.search_text or record.content for record in candidates]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=12000)
    matrix = vectorizer.fit_transform(docs)
    query_vec = vectorizer.transform([question])
    scores = linear_kernel(query_vec, matrix).ravel()

    ranked = sorted(
        (
            RetrievedChunk(
                score=float(scores[idx]),
                chunk_id=record.chunk_id,
                source=record.source,
                content=record.content,
                search_text=record.search_text,
            )
            for idx, record in enumerate(candidates)
        ),
        key=lambda item: item.score,
        reverse=True,
    )
    return [item for item in ranked[:topk] if item.score > 0]


@st.cache_data(show_spinner=False)
def _load_index():
    return load_vdb(str(DEFAULT_RAG_DIR))


def _chat_file() -> Path:
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    if "chat_file" not in st.session_state:
        st.session_state.chat_file = CHAT_DIR / f"{uuid.uuid4()}.jsonl"
    return Path(st.session_state.chat_file)


def _load_memory() -> list[dict]:
    if CHAT_MEMORY_FILE.exists():
        return json.loads(CHAT_MEMORY_FILE.read_text(encoding="utf-8"))
    return []


def _save_memory(memory_rows: list[dict]) -> None:
    CHAT_MEMORY_FILE.write_text(json.dumps(
        memory_rows, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_chat_log(role: str, content: str, meta: dict | None = None) -> None:
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "role": role,
        "content": content,
        "meta": meta or {},
    }
    with _chat_file().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _remember_message(program: str, role: str, content: str) -> None:
    memory_rows = _load_memory()
    memory_rows.append(
        {
            "program": program,
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    _save_memory(memory_rows[-200:])


def _retrieve_memory(question: str, program: str, limit: int = 3) -> list[dict]:
    rows = _load_memory()
    scoped = [row for row in rows if row.get(
        "program") in {program, "__all__"}]
    if not scoped:
        return []

    docs = [row["content"] for row in scoped]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(docs)
    query_vec = vectorizer.transform([question])
    scores = linear_kernel(query_vec, matrix).ravel()
    ranked = sorted(
        ((float(scores[idx]), row) for idx, row in enumerate(scoped)),
        key=lambda item: item[0],
        reverse=True,
    )
    return [row for score, row in ranked[:limit] if score > 0]


def _format_answer(question: str, chunks: list[RetrievedChunk], memories: list[dict]) -> str:
    if _question_looks_like_masters(question):
        return (
            "I could not find a clear master's course plan in the current search results. "
            "Try narrowing the question by program and semester, for example "
            "`MS Computer Science fall courses` or `graduate AI electives`."
        )

    if not chunks:
        return (
            "I couldn't find a strong match in the selected program documents. "
            "Try choosing a different program or add a course code like `CSE 3318`."
        )

    rows = _best_course_rows(question, chunks)
    prereqs = _best_prereq_items(question, chunks)

    lines = ["Here is a clearer course recommendation:"]
    if rows:
        semester = rows[0].semester or "Recommended semester"
        lines.append("")
        lines.append(f"{semester}")
        for row in rows[:6]:
            lines.append(f"- {row.course} ({row.hours} hrs)")
    else:
        return (
            "I found related content, but not a clean semester plan for that question. "
            "Try asking in a more specific way, for example: "
            "`What are the spring courses for third-year Computer Science?` "
            "or enter a course filter like `CSE 4344`."
        )

    if prereqs:
        lines.append("")
        lines.append("Helpful notes:")
        for item in prereqs[:3]:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("Double-check prerequisites and catalog notes before you register.")
    return "\n".join(lines)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #f5f9ff 0%, #ffffff 38%, #eef5ff 100%);
        }
        .uta-header {
            margin-bottom: 1rem;
            padding: 20px 22px;
            border-radius: 20px;
            background: white;
            border: 1px solid rgba(0, 83, 155, 0.12);
            box-shadow: 0 8px 24px rgba(0, 83, 155, 0.08);
        }
        .uta-brand {
            color: #00539b;
            font-size: 2.5rem;
            font-weight: 900;
            line-height: 1;
            margin: 0 0 10px 0;
            letter-spacing: 0.5px;
        }
        .uta-title {
            color: #0f2747;
            font-size: 1.35rem;
            font-weight: 800;
            margin: 0 0 4px 0;
        }
        .uta-subtitle {
            color: #49627d;
            margin: 0;
            font-size: 0.96rem;
        }
        .stButton > button,
        .stDownloadButton > button,
        div[data-testid="stChatInput"] button {
            background: #00539b !important;
            color: white !important;
            border: 1px solid #00539b !important;
            border-radius: 10px !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover,
        div[data-testid="stChatInput"] button:hover {
            background: #003f78 !important;
            border-color: #003f78 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="RAG Advisor", page_icon="📚", layout="wide")
    _inject_styles()
    st.markdown(
        """
        <div class="uta-header">
          <div>
            <p class="uta-brand">UTA</p>
            <p class="uta-title">RAG Advisor</p>
            <p class="uta-subtitle">Student-friendly degree plan search for UTA advising documents</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Ask about a degree plan, semester, or course sequence. I'll search the selected program documents and keep the chat history here.",
                "sources": [],
            }
        ]

    _, _, kv = _load_index()
    program_options = _program_options(kv)
    labels = [label for label, _ in program_options]
    selected_label = st.selectbox("Select program", labels, index=labels.index(
        "Computer Science") if "Computer Science" in labels else 0)
    selected_program = dict(program_options)[selected_label]
    course_filter = st.text_input(
        "Optional course code or keyword", placeholder="Example: CSE 3318 or junior spring")
    topk = 5

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask your advising question")
    if not prompt:
        return

    records = list(_get_program_records(selected_program))
    if course_filter:
        course_filter_lower = course_filter.lower()
        records = [
            record for record in records
            if course_filter_lower in record.content.lower()
            or course_filter_lower in record.search_text.lower()
        ]
    if selected_program == "__all__" and not course_filter:
        course_codes = _course_keywords(prompt)
        if course_codes:
            records = [
                record for record in records if any(
                    code.lower() in record.content.lower()
                    or code.lower() in record.search_text.lower()
                    for code in course_codes
                )
            ] or records

    memories = []
    chunks = _retrieve_chunks(prompt, records, topk)
    answer = _format_answer(prompt, chunks, memories)

    user_message = {"role": "user", "content": prompt, "sources": []}
    assistant_message = {"role": "assistant",
                         "content": answer, "sources": chunks}
    st.session_state.messages.extend([user_message, assistant_message])

    _append_chat_log("user", prompt, {
                     "program": selected_program, "course_filter": course_filter})
    _append_chat_log(
        "assistant",
        answer,
        {
            "program": selected_program,
            "course_filter": course_filter,
            "source_chunk_ids": [chunk.chunk_id for chunk in chunks],
        },
    )
    _remember_message(selected_program, "user", prompt)
    _remember_message(selected_program, "assistant", answer)
    st.rerun()


if __name__ == "__main__":
    main()
