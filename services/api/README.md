# MemoryOps AI — API

FastAPI service implementing the memory governance write + read path.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
MEMORYOPS_STORAGE=memory uvicorn app.main:app --reload   # http://localhost:8000/docs
pytest -q                                                # invariant tests
```

For Postgres: `pip install -r requirements-postgres.txt` and set
`MEMORYOPS_STORAGE=postgres` + `DATABASE_URL`.

Layout: `app/core` (config, logging, reliability, redaction, embeddings, llm),
`app/db` (repository + memory/postgres backends), `app/services` (extractor,
policy broker, write service, gateway, retriever, ranker, composer, audit,
eval harness), `app/routes` (chat, memories, audit, evals, health).
