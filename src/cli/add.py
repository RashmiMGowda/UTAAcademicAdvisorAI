# --- path bootstrap ---
if __name__ == "__main__" and __package__ is None:
    import os, sys, pathlib
    project_root = str(pathlib.Path(__file__).resolve().parents[2])
    if project_root not in sys.path: sys.path.insert(0, project_root)
    src_root = str(pathlib.Path(__file__).resolve().parents[1])
    if src_root not in sys.path: sys.path.insert(0, src_root)

import os, sys, time, asyncio
from dotenv import load_dotenv
from raganything import RAGAnything, RAGAnythingConfig
from ..core.models import llm_model_func, vision_model_func, embedding_func

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

os.environ.setdefault("MINERU_LOGLEVEL", "INFO")
HEARTBEAT_SECS = int(os.getenv("PROGRESS_HEARTBEAT_SECS", "30"))

async def _await_with_heartbeat(coro, label: str):
    task = asyncio.create_task(coro)
    start = time.perf_counter()
    while not task.done():
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=HEARTBEAT_SECS)
        except asyncio.TimeoutError:
            print(f"[{label}] still working… elapsed {time.perf_counter()-start:0.0f}s")
    return await task

async def main():
    load_dotenv()
    if len(sys.argv) < 2:
        print("Usage: python -m src.cli.add path\\to\\new.pdf")
        sys.exit(1)
    fpath = sys.argv[1]

    rag = RAGAnything(
        config=RAGAnythingConfig(
            working_dir=os.getenv("WORKING_DIR","./rag_storage"),
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

    t0 = time.perf_counter()
    print(f"Adding {os.path.basename(fpath)} …")
    await _await_with_heartbeat(
        rag.process_document_complete(
            file_path=fpath,
            output_dir=os.getenv("PARSED_DIR","./data/parsed_cache"),
            parse_method=os.getenv("PARSE_METHOD","auto")
        ),
        label=os.path.basename(fpath)
    )
    print(f"✅ Added & indexed in {time.perf_counter()-t0:0.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
