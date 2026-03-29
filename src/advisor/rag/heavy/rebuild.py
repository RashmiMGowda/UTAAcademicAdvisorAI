# --- path bootstrap (safe for python -m and direct) ---
if __name__ == "__main__" and __package__ is None:
    import os, sys, pathlib
    project_root = str(pathlib.Path(__file__).resolve().parents[4])
    if project_root not in sys.path: sys.path.insert(0, project_root)
    src_root = str(pathlib.Path(__file__).resolve().parents[3])
    if src_root not in sys.path: sys.path.insert(0, src_root)

import os, sys, time, asyncio
from dotenv import load_dotenv

# Windows event loop fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# show mineru’s internal logs (INFO→DEBUG if you want more)
os.environ.setdefault("MINERU_LOGLEVEL", "INFO")

from raganything import RAGAnything, RAGAnythingConfig
from ..core.models import llm_model_func, vision_model_func, embedding_func

HEARTBEAT_SECS = int(os.getenv("PROGRESS_HEARTBEAT_SECS", "30"))

def _progress_bar(i, n, width=28):
    done = int(width * (i / max(1, n)))
    return "[" + "#"*done + "."*(width-done) + f"] {i}/{n}"

async def _await_with_heartbeat(coro, label: str):
    """
    Await a long task but print a heartbeat every HEARTBEAT_SECS.
    """
    task = asyncio.create_task(coro)
    start = time.perf_counter()
    last = start
    while not task.done():
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=HEARTBEAT_SECS)
        except asyncio.TimeoutError:
            now = time.perf_counter()
            elapsed = now - start
            print(f"[{label}] still working… elapsed {elapsed:0.0f}s")
    # raise if it failed
    return await task

async def main():
    load_dotenv()
    sources = os.getenv("SOURCES_DIR","./data/sources")
    parsed  = os.getenv("PARSED_DIR","./data/parsed_cache")

    rag = RAGAnything(
        config=RAGAnythingConfig(
            working_dir=os.getenv("WORKING_DIR","./storage/rag_storage"),
            parser=os.getenv("PARSER","mineru"),
            parse_method=os.getenv("PARSE_METHOD","auto"),
            enable_image_processing=True,
            enable_table_processing=True,
            enable_equation_processing=True,
        ),
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )

    # enumerate files ourselves so we can print progress per file
    files = []
    for name in sorted(os.listdir(sources)):
        p = os.path.join(sources, name)
        if os.path.isfile(p) and os.path.splitext(p)[1].lower() in {".pdf", ".docx", ".pptx"}:
            files.append(p)

    if not files:
        print(f"No files found in {sources}")
        return

    total = len(files)
    ok = 0
    failed = []

    print(f"Found {total} file(s) in {sources}")
    os.makedirs(parsed, exist_ok=True)

    for i, fpath in enumerate(files, 1):
        bar = _progress_bar(i, total)
        print(f"\n{bar}  Parsing & indexing: {os.path.basename(fpath)}")
        t0 = time.perf_counter()
        try:
            # this wraps RAG-Anything’s full end-to-end for ONE file (parse + index)
            await _await_with_heartbeat(
                rag.process_document_complete(
                    file_path=fpath,
                    output_dir=parsed,
                    parse_method=os.getenv("PARSE_METHOD","auto")
                ),
                label=os.path.basename(fpath)
            )
            ok += 1
            dt = time.perf_counter() - t0
            print(f"✅ Done: {os.path.basename(fpath)} in {dt:0.1f}s")
        except Exception as e:
            dt = time.perf_counter() - t0
            print(f"❌ Failed: {os.path.basename(fpath)} after {dt:0.1f}s\n   → {e}")
            failed.append((fpath, str(e)))

    print("\n=== Summary ===")
    print(f"Successful: {ok}")
    print(f"Failed:     {len(failed)}")
    if failed:
        print("Failures:")
        for p, msg in failed:
            print(f"  - {p}: {msg}")

if __name__ == "__main__":
    asyncio.run(main())
