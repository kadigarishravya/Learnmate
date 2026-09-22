# LearnMate

Local PDF tutor with a Flask API, Streamlit frontend, SQLite, Chroma, and Cohere.

## Setup (Windows PowerShell)

Use Python 3.12 from the repository directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `COHERE_API_KEY` in `.env` to your Cohere key. `TAVILY_API_KEY` is optional,
for web search. Keep `.env` private. If it already exists, edit it instead of
copying over it.

## Run

Start the API:

```powershell
.\.venv\Scripts\python.exe run_api.py
```

In another terminal, start the UI:

```powershell
.\.venv\Scripts\python.exe -m streamlit run run_ui.py --server.address 127.0.0.1
```

Open http://127.0.0.1:8501, register, log in, upload a text-based PDF with a
title and subject, then ask the tutor about it. The first upload downloads the
embedding model and may take a few minutes; internet access is needed. Scanned
image-only PDFs need OCR before uploading.

SQLite tables are created automatically on first database use. Data lives in
`storage/`. Relative storage paths in `.env` resolve from the repository root.
The UI waits up to 300 seconds for processing; adjust
`LEARNMATE_API_TIMEOUT_SECONDS` if needed. Restart both processes after changing
configuration. API restarts expire login sessions.

AI answers, reranking, and quizzes require a valid Cohere key. Without matching
uploaded content, the tutor explains that it has insufficient information.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe -m pip check
```

The default suite uses test doubles for external AI services. Optional real
Chroma and embedding checks use `RUN_CHROMA_TESTS=1` and `RUN_EMBEDDING_TESTS=1`.
