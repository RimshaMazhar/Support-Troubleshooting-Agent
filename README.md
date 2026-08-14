# ParcelPilot Support Troubleshooting Agent

A chatbot that answers support questions about ParcelPilot, a fictional shipment-tracking app.

It uses two types of information. The docs explain how ParcelPilot works, what the services do, what error codes mean, and how problems are normally investigated. The system data shows what is happening in the system right now: service status, carrier data, logs, and past incidents.

A router decides which one a question needs, or if it's just conversation, and answers using that evidence instead of guessing.

## Project structure

```
app/
  ingest.py      - loads and chunks the PDF docs
  retrieval.py   - vector store + semantic search
  tools.py       - live system-data tools
  agent.py       - router + handlers
  main.py        - FastAPI app
data/
  docs/          - product docs (RAG source)
  system_data/   - live status, logs, incidents (tool source)
tests/           - pytest suite
```

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and try `POST /chat`:

```json
{
  "conversation_id": "demo",
  "message": "why is the orders service degraded right now?"
}
```

## Tests

```bash
pytest tests/ -v
```

## Stack

FastAPI, Groq (Llama 3.1/3.3), sentence-transformers, ChromaDB, pytest, GitHub Actions.