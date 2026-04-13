from __future__ import annotations

# --- path bootstrap (safe for python -m and direct) ---
if __name__ == "__main__" and __package__ is None:
    import sys, pathlib
    project_root = str(pathlib.Path(__file__).resolve().parents[4])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    src_root = str(pathlib.Path(__file__).resolve().parents[3])
    if src_root not in sys.path:
        sys.path.insert(0, src_root)

import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from raganything import RAGAnything, RAGAnythingConfig
from raganything.parser import MineruParser

from ..core.models import embedding_func, llm_model_func, vision_model_func


PROJECT_ROOT = Path(__file__).resolve().parents[4]
HEARTBEAT_SECS = int(os.getenv("PROGRESS_HEARTBEAT_SECS", "30"))


def _prefer_current_working_dir(raw_value: str | None) -> str:
    value = (raw_value or "").strip()
    if not value or value == "./rag_storage":
        return "./storage/rag_storage"
    return value


def _progress_bar(i: int, n: int, width: int = 28) -> str:
    done = int(width * (i / max(1, n)))
    return "[" + "#" * done + "." * (width - done) + f"] {i}/{n}"


async def _await_with_heartbeat(coro, label: str):
    task = asyncio.create_task(coro)
    start = time.perf_counter()
    while not task.done():
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=HEARTBEAT_SECS)
        except asyncio.TimeoutError:
            elapsed = time.perf_counter() - start
            print(f"[{label}] still working... elapsed {elapsed:0.0f}s")
    return await task


def _find_cached_output(pdf_path: Path, parsed_dir: Path) -> tuple[list[dict], str]:
    stem = pdf_path.stem
    method_hint = os.getenv("PARSE_METHOD", "ocr")
    candidate_roots = [parsed_dir]
    output_dir = Path(os.getenv("MINERU_OUTPUT_DIR", "./output"))
    if output_dir not in candidate_roots:
        candidate_roots.append(output_dir)

    for root in candidate_roots:
        content_list, md_content = MineruParser._read_output_files(root, stem, method=method_hint)
        if content_list:
            return content_list, md_content

        matches = sorted(root.glob(f"{stem}_*/**/{stem}_content_list.json"))
        for match in matches:
            subdir = match.parent.parent if match.parent.name in {"ocr", "auto", "txt", "hybrid_auto"} else match.parent
            content_list, md_content = MineruParser._read_output_files(subdir, stem, method=method_hint)
            if content_list:
                return content_list, md_content

    raise FileNotFoundError(
        f"No parsed MinerU output found for {pdf_path.name} in {parsed_dir} or {output_dir}"
    )


async def main():
    load_dotenv()
    sources = Path(os.getenv("SOURCES_DIR", "./data/sources"))
    parsed = Path(os.getenv("PARSED_DIR", "./data/parsed_cache"))
    working_dir = _prefer_current_working_dir(os.getenv("WORKING_DIR"))
    working_dir_path = Path(working_dir)

    rag = RAGAnything(
        config=RAGAnythingConfig(
            working_dir=str(working_dir_path),
            parser=os.getenv("PARSER", "mineru"),
            parse_method=os.getenv("PARSE_METHOD", "ocr"),
            enable_image_processing=True,
            enable_table_processing=True,
            enable_equation_processing=True,
        ),
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )

    files = sorted(path for path in sources.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    if not files:
        print(f"No PDF files found in {sources}")
        return

    parsed.mkdir(parents=True, exist_ok=True)
    working_dir_path.mkdir(parents=True, exist_ok=True)
    print(f"Using parsed cache: {parsed}")
    print(f"Using working directory: {working_dir_path}")
    print(f"Found {len(files)} file(s) in {sources}")

    ok = 0
    failed: list[tuple[str, str]] = []

    for index, pdf_path in enumerate(files, start=1):
        bar = _progress_bar(index, len(files))
        print(f"\n{bar}  Inserting from parsed cache: {pdf_path.name}")
        started = time.perf_counter()
        try:
            content_list, _ = _find_cached_output(pdf_path, parsed)
            await _await_with_heartbeat(
                rag.insert_content_list(
                    content_list=content_list,
                    file_path=str(pdf_path),
                ),
                label=pdf_path.name,
            )
            elapsed = time.perf_counter() - started
            print(f"OK Inserted: {pdf_path.name} in {elapsed:0.1f}s")
            ok += 1
        except Exception as exc:
            elapsed = time.perf_counter() - started
            print(f"FAILED: {pdf_path.name} after {elapsed:0.1f}s")
            print(f"   -> {exc}")
            failed.append((pdf_path.name, str(exc)))

    print("\n=== Summary ===")
    print(f"Successful: {ok}")
    print(f"Failed:     {len(failed)}")
    if failed:
        print("Failures:")
        for name, message in failed:
            print(f"  - {name}: {message}")


if __name__ == "__main__":
    asyncio.run(main())
