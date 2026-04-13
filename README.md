# RAG Advisor

## Overview

RAG Advisor is a UTA academic advising assistant built with:

- a React frontend
- a FastAPI backend
- a heavy RAG pipeline for parsing and indexing PDFs
- a lightweight retrieval layer for fast student-facing responses
- Supabase auth and per-user chat history

The app answers from official UTA advising PDFs rather than hardcoded chatbot text.

## Architecture

```text
UTA PDFs (data/sources)
        |
        v
MinerU parsing
        |
        +--> data/parsed_cache/          generated parser output
        |
        +--> heavy RAG build             chunks, vectors, graph, caches
                    |
                    v
           storage/rag_storage/
                    |
                    v
        compact store builder
                    |
                    v
      data/light_rag/course_catalog.json
                    |
                    v
      FastAPI backend (src/advisor/api/)
                    |
                    v
          Supabase auth + chat DB
                    |
                    v
        React frontend (frontend/)
```

## Repo Layout

```text
RAG-Advisor/
├── frontend/                  React app
├── src/advisor/api/           FastAPI endpoints
├── src/advisor/rag/core/      shared model/config wiring
├── src/advisor/rag/heavy/     rebuild, add, vector, graph flows
├── src/advisor/rag/light/     compact retrieval for web app
├── data/sources/              source PDFs
├── data/parsed_cache/         generated parse output
├── data/light_rag/            compact JSON store
├── storage/rag_storage/       heavy generated RAG storage
├── scripts/                   helper scripts
├── eval/                      evaluation scripts
├── supabase/                  SQL for chat history tables
└── docs/                      final report and presentation outputs
```

## Important Git-Ignored Files And Folders

These are intentionally **not** in git and must be created locally:

- `.venv/`
- `.env`
- `.env.local`
- `frontend/.env.local`
- `data/parsed_cache/`
- `storage/rag_storage/`
- `storage/app_state/`
- `output/`
- `frontend/node_modules/`
- `frontend/dist/`

If someone clones the repo and these are missing, that is expected.

## Fresh Clone Setup

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd RAG-Advisor
```

### 2. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Install Node.js if needed

Check first:

```bash
node -v
npm -v
```

If Node is missing on macOS and Homebrew is not installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv zsh)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv zsh)"
```

Then install Node:

```bash
brew install node
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Create backend environment file

Create `/.env` with:

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
WORKING_DIR=./storage/rag_storage
PARSED_DIR=./data/parsed_cache
```

Notes:

- `OPENAI_API_KEY` is needed for the heavy indexing flow.
- If you only want to run the lightweight app from an already-built compact store, the backend can still start without a successful heavy rebuild, but heavy indexing will not work.

### 6. Create frontend environment file

Create [`frontend/.env.local`](/Users/rashmigowda/Downloads/RAG-Advisor/frontend/.env.local) with:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY=your-supabase-publishable-key
```

Notes:

- use the **publishable** Supabase key, not the secret key
- the frontend reads `frontend/.env.local`, not the root `.env`

### 7. Set up Supabase chat tables

Open Supabase SQL Editor and run:

[`supabase/chat_history.sql`](/Users/rashmigowda/Downloads/RAG-Advisor/supabase/chat_history.sql)

This creates:

- `chat_sessions`
- `chat_messages`

with row-level security so each user only sees their own chats.

## Run The App

### Terminal 1: backend

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
python -m uvicorn src.advisor.api.light_rag_api:app --reload
```

### Terminal 2: frontend

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor/frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

## Rebuild The Lightweight Store

If the source PDFs were updated, rebuild the light store:

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
python - <<'PY'
from src.advisor.rag.light.compact_store import build_compact_store
print(build_compact_store())
PY
```

This regenerates:

- `data/light_rag/course_catalog.json`

## Refresh Parsing For All PDFs

To parse the full PDF folder with MinerU:

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
rm -rf output
mkdir output
mineru -p ./data/sources -o output -b pipeline -m ocr
```

If you want those outputs copied into the project cache:

```bash
cp -R output/* data/parsed_cache/
```

## Heavy RAG Build

### Preferred current flow

On this machine, the safest heavy flow is:

1. parse with MinerU
2. build heavy RAG from parsed cache

Run:

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
python -m src.advisor.rag.heavy.rebuild_from_parsed_cache
```

Why this path exists:

- MinerU parsing works reliably as a separate step
- the original `rebuild.py` reparses PDFs internally
- `rebuild_from_parsed_cache.py` reuses successful parse output and then performs heavy indexing

### Original heavy rebuild

You can still try the all-in-one path:

```bash
python -m src.advisor.rag.heavy.rebuild
```

But the parsed-cache path is the recommended one for this repo right now.

## What The App Supports

- greeting handling such as `hi`
- optional program selection
- undergraduate and graduate routing
- semester-plan questions
- prerequisite questions
- topic-based course discovery such as AI, data, systems, cloud, and security
- saved chat history per logged-in user
- new chat creation

## Known Practical Limits

- full heavy RAG rebuild depends on OpenAI API quota
- if your OpenAI account has no credits, heavy embeddings and multimodal descriptions will fail
- lightweight retrieval can still be rebuilt from parsed data and used for the frontend

## Main Files

### Frontend

- [`frontend/src/App.jsx`](/Users/rashmigowda/Downloads/RAG-Advisor/frontend/src/App.jsx)
- [`frontend/src/lib/api.js`](/Users/rashmigowda/Downloads/RAG-Advisor/frontend/src/lib/api.js)
- [`frontend/src/lib/chatHistory.js`](/Users/rashmigowda/Downloads/RAG-Advisor/frontend/src/lib/chatHistory.js)
- [`frontend/src/utils/supabase.js`](/Users/rashmigowda/Downloads/RAG-Advisor/frontend/src/utils/supabase.js)

### Backend

- [`src/advisor/api/light_rag_api.py`](/Users/rashmigowda/Downloads/RAG-Advisor/src/advisor/api/light_rag_api.py)

### Heavy RAG

- [`src/advisor/rag/heavy/rebuild.py`](/Users/rashmigowda/Downloads/RAG-Advisor/src/advisor/rag/heavy/rebuild.py)
- [`src/advisor/rag/heavy/rebuild_from_parsed_cache.py`](/Users/rashmigowda/Downloads/RAG-Advisor/src/advisor/rag/heavy/rebuild_from_parsed_cache.py)
- [`src/advisor/rag/heavy/quick_rag.py`](/Users/rashmigowda/Downloads/RAG-Advisor/src/advisor/rag/heavy/quick_rag.py)
- [`src/advisor/rag/heavy/graph_rag.py`](/Users/rashmigowda/Downloads/RAG-Advisor/src/advisor/rag/heavy/graph_rag.py)

### Light RAG

- [`src/advisor/rag/light/compact_store.py`](/Users/rashmigowda/Downloads/RAG-Advisor/src/advisor/rag/light/compact_store.py)

## Final Deliverables

Generated project deliverables are kept in:

- [`docs/AI_Academic_Advisor_Final_Report.docx`](/Users/rashmigowda/Downloads/RAG-Advisor/docs/AI_Academic_Advisor_Final_Report.docx)
- [`docs/AI_Academic_Advisor_Final_Presentation.pptx`](/Users/rashmigowda/Downloads/RAG-Advisor/docs/AI_Academic_Advisor_Final_Presentation.pptx)
