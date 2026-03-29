# RAG Advisor

## Overview

RAG Advisor is a UTA advising assistant with:

- a React frontend for student interaction
- a FastAPI backend for auth, chat history, and retrieval
- a heavy RAG pipeline for parsing PDFs and building rich indexes
- a lightweight retrieval layer for fast, grounded frontend answers

The current frontend does not use hardcoded fallback replies. It calls the backend, and the backend answers from the extracted UTA advising PDF content.

## Architecture

```text
UTA PDFs (data/sources)
        |
        v
Heavy parsing + indexing
        |
        +--> data/parsed_cache/          intermediate parser output
        |
        +--> storage/rag_storage/        chunk, vector, graph, and cache files
                    |
                    v
        lightweight compact builder
                    |
                    v
        data/light_rag/course_catalog.json
                    |
                    v
FastAPI backend (src/advisor/api/)
        |
        +--> Google OAuth login
        +--> SQLite chat/user storage
        +--> real retrieval from extracted PDF data
                    |
                    v
React frontend (frontend/)
```

## Folder Structure

```text
RAG-Advisor/
├── frontend/                  React app
├── src/
│   └── advisor/
│       ├── api/               FastAPI routes, OAuth, SQLite app storage helpers
│       └── rag/
│           ├── core/          shared heavy RAG config and model wiring
│           ├── heavy/         rebuild, quick_rag, graph_rag, add
│           └── light/         compact retrieval for the frontend
├── data/
│   ├── sources/               original UTA PDFs
│   ├── parsed_cache/          generated parser cache
│   └── light_rag/             compact JSON built from extracted chunks
├── storage/
│   ├── rag_storage/           heavy generated RAG files
│   └── app_state/             local SQLite database for login/chat state
├── configs/                   YAML config files
├── eval/                      evaluation scripts
├── scripts/                   helper scripts
├── .venv/                     local Python environment
└── README.md
```

## What The Main Code Does

### `frontend/`

Student-facing React application.

- `frontend/src/App.jsx`
  Main login and chat UI. Handles Google login, optional program selection, chat history loading, and sending questions to the backend.
- `frontend/src/lib/api.js`
  Frontend API client for login, session validation, chat history, logout, and advisor queries.
- `frontend/src/styles.css`
  UTA-style layout and visual treatment.

### `src/advisor/api/`

Backend API layer.

- `src/advisor/api/light_rag_api.py`
  FastAPI app. Exposes health, Google auth, chat history, logout, and advisor query endpoints.
- `src/advisor/api/google_auth.py`
  Verifies Google OAuth ID tokens on the backend.
- `src/advisor/api/auth_store.py`
  Stores users, sessions, and chat history in SQLite under `storage/app_state/advisor.db`.

### `src/advisor/rag/heavy/`

Full RAG pipeline.

- `rebuild.py`
  Parses all PDFs and builds the heavy storage.
- `add.py`
  Adds a single PDF to the heavy storage.
- `quick_rag.py`
  Runs vector-based retrieval on the heavy store.
- `graph_rag.py`
  Runs graph-aware retrieval using the heavy graph and chunk structure.

### `src/advisor/rag/light/`

Fast frontend retrieval.

- `compact_store.py`
  Reads `storage/rag_storage/kv_store_text_chunks.json`, extracts semester-plan tables and prerequisite lists, builds a small compact store, and answers user questions from that data.

### `data/`

- `data/sources/`
  The real PDF source documents.
- `data/parsed_cache/`
  Parser-generated intermediate files. Large, generated, and safe to ignore in git.
- `data/light_rag/course_catalog.json`
  Lightweight store used by the frontend backend path. Rebuilt automatically when needed.

### `storage/rag_storage/`

Heavy generated RAG output.

Important files:

- `kv_store_text_chunks.json`
  Extracted text chunks from the PDFs. This is the main source the lightweight frontend backend reads from.
- `vdb_chunks.json`
  Chunk embeddings for vector retrieval.
- `vdb_entities.json`
  Entity embeddings.
- `vdb_relationships.json`
  Relationship embeddings.
- `graph_chunk_entity_relation.graphml`
  Graph structure for graph-based retrieval.

### `configs/`

YAML files are used for configuration because they are easier to edit than hardcoding settings in Python.

- `prompts.yaml`
- `raganything.yaml`

### `eval/`

Evaluation code for testing retrieval or response quality.

## Setup

### 1. Python

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Node

If `brew` is not installed on Mac:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo >> /Users/rashmigowda/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv zsh)"' >> /Users/rashmigowda/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv zsh)"
```

Then install Node:

```bash
brew install node
node -v
npm -v
```

## Google OAuth Configuration

Create a Google OAuth Web Client in Google Cloud, then set the client ID in both backend and frontend config.

Project root `.env`:

```env
GOOGLE_CLIENT_ID=your-google-web-client-id.apps.googleusercontent.com
OPENAI_API_KEY=sk-your-openai-key
```

Frontend `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your-google-web-client-id.apps.googleusercontent.com
```

Notes:

- `GOOGLE_CLIENT_ID` is needed for backend token verification.
- `VITE_GOOGLE_CLIENT_ID` is needed to render the Google sign-in button in React.
- `OPENAI_API_KEY` is only needed when you run the heavy rebuild/indexing flow.

## Run The App

### Terminal 1: Backend

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
python -m uvicorn src.advisor.api.light_rag_api:app --reload
```

### Terminal 2: Frontend

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor/frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## How The Frontend Answers Questions

1. User signs in with Google.
2. Backend verifies the Google token.
3. Backend stores the user and session in SQLite.
4. User asks a question.
5. Backend searches the extracted PDF chunk data and compact semester/prerequisite store.
6. Backend returns a student-friendly answer grounded in the source PDFs.
7. Backend saves the chat turn for that user.

The backend also handles:

- simple greetings like `hi`
- optional program selection
- course-code questions like `after CSE 4344`
- prerequisite questions like `what courses need CSE 3318`

## Heavy RAG Commands

Rebuild the full heavy index:

```bash
cd /Users/rashmigowda/Downloads/RAG-Advisor
source .venv/bin/activate
python -m src.advisor.rag.heavy.rebuild
```

Add one document:

```bash
python -m src.advisor.rag.heavy.add data/sources/your_file.pdf
```

Quick vector retrieval:

```bash
python -m src.advisor.rag.heavy.quick_rag -q "What are the recommended spring courses for a third-year Computer Science student?" -k 20 --with-summary
```

Graph retrieval:

```bash
python -m src.advisor.rag.heavy.graph_rag -q "What are the recommended spring courses for a third-year Computer Science student?" -k 10 --with-summary --graphml ./storage/rag_storage/graph_chunk_entity_relation.graphml --hops 1 --graph-max-neighbors 4 --graph-weight 0.3
```

## About `.gitignore`

These ignored folders are generated or local-only and can be recreated:

- `.venv/`
- `data/parsed_cache/`
- `storage/rag_storage/`
- `storage/app_state/`
- `output/`
- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/.env.local`

Ignoring them does not break the project. It only means each machine needs to rebuild or reinstall local/generated assets.

## OpenAI Key

Some heavy build/retrieval commands need OpenAI.

Put your key in `.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
EMBED_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini
WORKING_DIR=./storage/rag_storage
```

## Suggested Project Explanation

For presentations, the easiest explanation is:

1. `data/sources` holds the original UTA PDFs
2. the heavy pipeline parses and indexes them into `storage/rag_storage`
3. the lightweight layer builds a compact advisor store in `data/light_rag`
4. FastAPI serves advisor answers
5. React gives the student-facing chat UI
