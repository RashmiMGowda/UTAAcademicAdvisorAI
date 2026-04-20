from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "data" / "sources"
PARSED_DIR = PROJECT_ROOT / "data" / "parsed_cache"
SUMMARY_PATH = PARSED_DIR / "batch_mineru_summary.json"
MINERU_BIN = Path(
    sys.prefix) / ("Scripts" if sys.platform.startswith("win") else "bin") / "mineru"


def run_one(pdf_path: Path, method: str, backend: str) -> dict[str, object]:
    cmd = [
        str(MINERU_BIN),
        "-p",
        str(pdf_path),
        "-o",
        str(PARSED_DIR),
        "-b",
        backend,
        "-m",
        method,
    ]
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, check=False)
        elapsed = round(time.perf_counter() - start, 2)
        return {
            "file": pdf_path.name,
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "elapsed_seconds": elapsed,
            "stdout_tail": completed.stdout[-3000:],
            "stderr_tail": completed.stderr[-3000:],
        }
    except Exception as exc:
        elapsed = round(time.perf_counter() - start, 2)
        return {
            "file": pdf_path.name,
            "ok": False,
            "returncode": None,
            "elapsed_seconds": elapsed,
            "stdout_tail": "",
            "stderr_tail": str(exc),
        }


def main() -> int:
    method = os.getenv("MINERU_METHOD", "ocr")
    backend = os.getenv("MINERU_BACKEND", "pipeline")

    if not SOURCE_DIR.exists():
        print(f"Missing source directory: {SOURCE_DIR}")
        return 1

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(path for path in SOURCE_DIR.iterdir()
                  if path.is_file() and path.suffix.lower() == ".pdf")
    if not pdfs:
        print(f"No PDFs found in {SOURCE_DIR}")
        return 1

    print(f"Parsing {len(pdfs)} PDF(s) from {SOURCE_DIR}")
    print(f"Output directory: {PARSED_DIR}")
    print(f"MinerU backend={backend} method={method}")
    print(f"MinerU binary: {MINERU_BIN}")

    if not MINERU_BIN.exists():
        print(f"Missing MinerU binary: {MINERU_BIN}")
        return 1

    results = []
    for index, pdf_path in enumerate(pdfs, start=1):
        print(f"\n[{index}/{len(pdfs)}] {pdf_path.name}")
        result = run_one(pdf_path, method, backend)
        results.append(result)
        status = "OK" if result["ok"] else "FAILED"
        print(f"{status} in {result['elapsed_seconds']}s")
        if not result["ok"] and result["stderr_tail"]:
            print(result["stderr_tail"])

    SUMMARY_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok_count = sum(1 for item in results if item["ok"])
    failed = [item["file"] for item in results if not item["ok"]]

    print("\nSummary")
    print(f"Successful: {ok_count}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failed files:")
        for name in failed:
            print(f" - {name}")
    print(f"Detailed log: {SUMMARY_PATH}")
    return 0 if ok_count == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
