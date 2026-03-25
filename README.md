# RAG Advisor

## What This Project Is

RAG Advisor is a UTA advising assistant project.
It combines:

- a React frontend for a student-friendly chat experience
- a lightweight Python backend for fast course-plan retrieval
- a larger RAG pipeline for parsing and indexing advising documents when needed

The current recommended app flow is:

1. Run the lightweight backend
2. Run the React frontend
3. Ask advising questions such as semester planning, prerequisites, and follow-up course choices

## Project Modes

### 1. Lightweight React + API Mode

This is the easiest and fastest way to run the project.

- frontend: `frontend/`
- backend: `src/api/light_rag_api.py`
- compact data store: `data/light_rag/course_catalog.json`

This mode is best for:

- demos
- UI development
- advisor-style chat flow
- smaller storage
- faster local development

### 2. Full RAG Build Mode

This uses the heavier parsing and indexing pipeline.

- parser/build tools: `src/cli/rebuild.py`, `src/cli/add.py`
- heavier storage: `rag_storage/`
- parsed cache: `data/parsed_cache/`

This mode is useful when you want:

- full document parsing
- richer retrieval artifacts
- experiments with graph/vector-based RAG
- deeper AI-project functionality

## Important Note About `.gitignore`

The `.gitignore` is intentional and should not break the code flow.

These folders are ignored because they are generated locally and can become very large:

- `.venv/`
- `data/parsed_cache/`
- `rag_storage/`
- `output/`
- `frontend/node_modules/`
- `frontend/dist/`

Why this is okay:

- these are build/cache/runtime folders
- they do not need to be committed to git
- they can be recreated locally
- the lightweight app can still work if `data/light_rag/course_catalog.json` is present

If a teammate clones the repo and those ignored folders are missing, they just need to follow the setup steps below.

## Folder Overview

- `frontend/`: React UI
- `src/api/`: lightweight API backend
- `src/light_rag/`: compact retrieval logic
- `src/cli/`: heavier RAG build/index commands
- `data/sources/`: UTA advising PDFs
- `data/light_rag/`: compact lightweight retrieval store
- `data/parsed_cache/`: generated parsing cache
- `rag_storage/`: generated heavy RAG storage

## Full Setup From Scratch

### Step 1: Install Python Environment

From the project root:

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 2: Install Homebrew on Mac

If `brew` is missing:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then add it to your shell:

```bash
echo >> /Users/rashmigowda/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv zsh)"' >> /Users/rashmigowda/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv zsh)"
```

### Step 3: Install Node.js

```bash
brew install node
```

Verify:

```bash
node -v
npm -v
```

## Run The Recommended Lightweight App

### Terminal 1: Start Backend

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
python -m uvicorn src.api.light_rag_api:app --reload
```

Backend URL:

```text
http://localhost:8000
```

### Terminal 2: Start React Frontend

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor/frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

The frontend is already configured to call:

```text
http://localhost:8000
```

by default.

## How The Lightweight Backend Works

The lightweight backend uses:

- `src/light_rag/compact_store.py`
- `data/light_rag/course_catalog.json`

This compact store is much smaller than full `rag_storage`.
It is designed for:

- semester recommendations
- year/semester questions like `junior spring`
- course-follow-up questions like `after CSE 4344`
- faster UI responses

## If `data/light_rag/course_catalog.json` Is Missing

If the lightweight store is missing but `rag_storage/kv_store_text_chunks.json` exists, the backend can build the compact store automatically.

You can also build it manually:

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
python - <<'PY'
from src.light_rag.compact_store import build_compact_store
print(build_compact_store())
PY
```

## If You Want To Use The Full RAG Pipeline

The full build pipeline still exists, but it is heavier.

Run:

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
python -m src.cli.rebuild
```

This creates large generated folders such as:

- `data/parsed_cache/`
- `rag_storage/`

These are intentionally ignored by git.

## OpenAI Key

The lightweight React + API mode does not depend on the heavy OpenAI graph/vector retrieval flow for every request.

But some heavier build commands still need the API key, especially:

- `python -m src.cli.rebuild`

Put your key in:

```text
.env
```

Example:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
EMBED_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini
WORKING_DIR=./rag_storage
```

## Frontend API Contract

The React frontend sends:

```text
POST /advisor/query
```

Request body:

```json
{
  "program": "CSE",
  "question": "What are the recommended spring courses for a third-year Computer Science student?",
  "course_filter": "CSE 4344"
}
```

Response body:

```json
{
  "summary": "Student-friendly answer here",
  "recommendations": [
    {
      "course": "CSE 3380",
      "title": "Linear Algebra for CSE",
      "hours": "3"
    }
  ],
  "notes": ["Helpful note"],
  "sources": ["2025-CSE.pdf"],
  "mode": "light-rag"
}
```

## Suggested Next Project Steps

If you are building this for an AI project, a good next roadmap is:

1. Keep the React frontend
2. Keep the lightweight backend for fast advisor UX
3. Keep the full RAG pipeline as your advanced retrieval layer
4. Add user login and chat history storage
5. Add evaluation and comparison between lightweight mode and full RAG mode

## Troubleshooting

### `npm: command not found`

Install Node first:

```bash
brew install node
```

### `FileNotFoundError: ... rag_storage/vdb_chunks.json`

That means the heavy index is missing.
Either:

- use the lightweight React backend flow instead
- or rebuild the heavy index with `python -m src.cli.rebuild`

### Frontend loads but answers are demo-like

Make sure the backend is running:

```bash
python -m uvicorn src.api.light_rag_api:app --reload
```

### Backend starts but compact store is missing

Build it manually with:

```bash
python - <<'PY'
from src.light_rag.compact_store import build_compact_store
print(build_compact_store())
PY
```
