# This script is designed to inspect the available methods in the RAGAnything class.
# It initializes a RAGAnything instance with dummy functions for the language model, vision model, and embedding functions,

import os
from dotenv import load_dotenv
from raganything import RAGAnything, RAGAnythingConfig

# Mock functions for initialization


def dummy_func(*args, **kwargs): return None


load_dotenv()
rag = RAGAnything(
    config=RAGAnythingConfig(working_dir="./storage/rag_storage"),
    llm_model_func=dummy_func,
    vision_model_func=dummy_func,
    embedding_func=dummy_func,
)

print("--- Available Methods in your RAGAnything version ---")
for method in dir(rag):
    if not method.startswith("__"):
        print(method)
