# This script checks for the presence of a specific phrase in the text chunks stored in the
# JSON file at "storage/rag_storage/kv_store_text_chunks.json". It reads the JSON data,
# iterates through the text chunks, and counts how many times the specified phrase appears.
# If it finds a hit, it prints the key and a snippet of the text.
# Finally, it prints the total number of hits found.
import json
import re
import pathlib

PHRASE = "If an employee is injured because he or she trips on the family dog while rushing to answer a work phone call, the case is not considered work-related.".lower()

p = pathlib.Path("storage/rag_storage/kv_store_text_chunks.json")
data = json.loads(p.read_text(encoding="utf-8"))

hits = 0
for k, v in data.items():
    # v might be dict or str depending on LightRAG version
    text = ""
    if isinstance(v, dict):
        text = (v.get("text") or v.get("content") or "")
    elif isinstance(v, str):
        text = v
    if PHRASE in text.lower():
        hits += 1
        print("\n--- HIT KEY:", k)
        print(text[:600])
        if hits >= 3:
            break

print("\nTOTAL HITS:", hits)
