# RepoPilot

RepoPilot is an AI software engineering agent that accepts a developer task,
inspects an authorized repository with restricted tools, produces a structured
plan, and (in later stages) prepares a reviewable draft pull request.

The application — not the model — enforces permissions, path boundaries, tool
allowlists, budgets, and approval gates.

## Current status

Iteration-focused backend foundation is in place:

- FastAPI task API with idempotent create/list/get
- PostgreSQL persistence for tasks, agent runs, and ordered run steps
- Allowlisted repository clone at a pinned commit
- Path-restricted list/read/search tools over a workspace
- Structured planning client (`OpenAI` + test fake)

Still ahead: a budgeted agent loop, sandboxed test execution, GitHub draft PRs,
and a review dashboard.

## Stack

Python 3.13 · FastAPI · SQLAlchemy · Alembic · PostgreSQL · OpenAI API · Docker Compose · pytest · Ruff

## Prerequisites

- Python 3.13+
- Docker Compose

## Quick start

```bash
cp .env.example backend/.env
docker compose up -d postgres

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:create_app --factory --reload --port 8000
```

Postgres listens on host port `55432`:

```text
postgresql://repopilot:repopilot@localhost:55432/repopilot
```

## API demo

```bash
curl -s http://127.0.0.1:8000/health

curl -s -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-1' \
  -d '{"description":"Investigate duplicate bookings"}'

curl -s "http://127.0.0.1:8000/tasks/<task-id>"
curl -s http://127.0.0.1:8000/tasks
```

## Sample repository

`examples/booking-sample` is a tiny booking service with an intentional
idempotency bug. Repository-tool and agent tests use this fixture so demos do
not require GitHub credentials.

## Checks

```bash
cd backend
./scripts/check
```

That runs Ruff and pytest. Integration tests expect Postgres (Compose URL by
default via `DATABASE_URL`).

## Design notes

- Tools receive structured arguments and return structured results — no raw shell
- Workspace paths reject traversal, symlink escapes, secret-like names, and oversized files
- Agent activity is stored as append-only run steps for auditability
- Draft GitHub writes will require explicit human approval (not implemented yet)

## License

No license file is attached yet; treat the repository as source-available until
one is added.
