# RAG Advisor

## Description

RAG Advisor is a student-focused advising search app built on top of a local RAG pipeline.
It reads indexed UTA advising PDFs, lets a user choose a program such as Computer Science or Software Engineering, and returns a cleaner course recommendation from the stored degree-plan content.

The current Streamlit UI is designed for fast local use:

- choose a program
- ask a question in chat style
- optionally narrow the search with a course code such as `CSE 4344`
- get a student-friendly response based on the indexed advising data

## What The Code Does

This project has two main parts.

1. Indexing and storage

The code in [src/cli/rebuild.py](/Users/rashmigowda/Downloads/RAG-Advisor/src/cli/rebuild.py) and [src/cli/add.py](/Users/rashmigowda/Downloads/RAG-Advisor/src/cli/add.py) processes PDF documents from `data/sources` and stores parsed content plus retrieval artifacts in `rag_storage`.

2. Retrieval and answering

The app in [src/ui/streamlit_app.py](/Users/rashmigowda/Downloads/RAG-Advisor/src/ui/streamlit_app.py) loads the indexed content, filters it by selected program, ranks the most relevant chunks, extracts semester tables and course rows when possible, and shows the result in a chat-style UI.

There are also CLI tools for retrieval:

- [src/cli/quick_rag.py](/Users/rashmigowda/Downloads/RAG-Advisor/src/cli/quick_rag.py): simple retrieval over stored chunks
- [src/cli/graph_rag.py](/Users/rashmigowda/Downloads/RAG-Advisor/src/cli/graph_rag.py): graph-assisted retrieval with optional OpenAI summary

## Project Flow

1. Put advising PDFs into `data/sources`
2. Build or rebuild the index
3. Launch the Streamlit app
4. Select a program and ask a question
5. The app searches the indexed chunks and formats the answer more like an advisor response

## Folder Overview

- `data/sources`: source PDFs
- `data/parsed_cache`: parsed document outputs
- `rag_storage`: retrieval artifacts and cached data
- `src/cli`: command-line indexing and retrieval tools
- `src/core`: shared config and model helpers
- `src/ui`: Streamlit UI

## What Can Be Ignored In Git

These folders are generated locally and do not need to be pushed to git:

- `.venv`: local virtual environment
- `data/parsed_cache`: generated parsing cache
- `rag_storage`: generated retrieval storage and local search artifacts
- `output`: local output files
- `__pycache__`, `.streamlit`, `.DS_Store`, logs

This does not break the code flow.
You can still keep using the same project folder locally.
The app will continue to work as long as those files exist on your machine.
They are just excluded from git so the repository stays smaller.

The current [`.gitignore`](/Users/rashmigowda/Downloads/RAG-Advisor/.gitignore) already ignores these generated folders.

## Setup

### macOS / VS Code Terminal

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows CMD

```bash
conda create -p .\.venv python=3.10 -y
conda activate .\.venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Optional OpenAI Key

The Streamlit UI does not require an OpenAI key for its current local retrieval flow.

The OpenAI key is only needed if you want to use the OpenAI-powered CLI commands such as `graph_rag` summary mode.

If needed, create a `.env` file and add:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
EMBED_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini
WORKING_DIR=./rag_storage
```

## Build The Index

Place your PDFs in `data/sources`, then run:

```bash
python -m src.cli.rebuild
```

To add one new PDF:

```bash
python -m src.cli.add data/sources/your_file.pdf
```

## Run The Streamlit UI

From the project root:

```bash
source .venv/bin/activate
streamlit run src/ui/streamlit_app.py
```

## If Git Is Still Trying To Push Large Files

If these folders were already committed in the past, `.gitignore` alone is not enough.
You need to stop tracking them once, while keeping the files in the same folder on your computer.

Run these commands from the project root:

```bash
git rm -r --cached .venv data/parsed_cache rag_storage output
git add .gitignore
git commit -m "Stop tracking generated files"
```

After that:

- the files stay in your local folder
- your app flow is unchanged
- future commits will not include those generated folders

If your old git history is already very large, you may still need to push to a fresh branch or clean old history later, but the commands above are the correct first step.

## How To Use The UI

1. Open the app in your browser
2. Choose a program such as `Computer Science`
3. Optionally enter a course filter like `CSE 3318`
4. Ask a question such as:

```text
What are the recommended spring courses for a third-year Computer Science student?
```

Example follow-up questions:

- `If I take CSE 4344 in fall, what should I take in spring?`
- `What courses are listed for junior spring in CSE?`
- `What classes need CSE 3318 as a prerequisite?`

## CLI Examples

### Quick Retrieval

```bash
python -m src.cli.quick_rag -q "What are the recommended courses for the spring semester for a third year Computer Science student?" -k 20 --with-summary
```

### Graph Retrieval

```bash
python -m src.cli.graph_rag -q "What are the recommended courses for the spring semester for a third year Computer Science student?" -k 10 --with-summary --graphml ./rag_storage/graph_chunk_entity_relation.graphml --hops 1 --graph-max-neighbors 4 --graph-weight 0.3
```

## Notes

- The UI is optimized for local advising search, not full conversational reasoning with an LLM.
- Responses depend on the documents already indexed into `rag_storage`.
- If the answer feels too broad, select the correct program and use a course code or semester phrase in the question.
- Streamlit UI works without an OpenAI key in the current local retrieval flow.
