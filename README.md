# RepoPilot

Autonomous software engineering agent. See `RepoPilot_Project_Plan.md` and
`docs/implementation-steps.md` for the full plan.

## Prerequisites

- Python 3.13+
- Docker Compose

## Setup

From the repository root:

```bash
cp .env.example backend/.env
docker compose up -d postgres
docker compose ps
```

Host port `55432` avoids clashes with a local Postgres on `5432`. The connection
string matches `.env.example`:

```text
postgresql://repopilot:repopilot@localhost:55432/repopilot
```

Install the backend package (including dev tools) in a virtualenv:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Apply database migrations:

```bash
cd backend
alembic upgrade head
```

Stop the database with:

```bash
docker compose down
```

## Run the API

With `backend/.env` present and the virtualenv activated:

```bash
cd backend
uvicorn app.main:create_app --factory --reload --port 8000
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
```

## Demo: create and fetch a task

With the API running on port 8000:

```bash
curl -s -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-1' \
  -d '{"description":"Investigate duplicate bookings"}'
```

Copy the returned `id`, then:

```bash
curl -s "http://127.0.0.1:8000/tasks/<task-id>"
```

List tasks:

```bash
curl -s http://127.0.0.1:8000/tasks
```

## Lint and test

From `backend/` with Postgres running and the virtualenv activated, one command
runs Ruff and pytest:

```bash
cd backend
./scripts/check
```

Or run them separately:

```bash
cd backend
ruff check app tests migrations
pytest
```

Integration tests need `DATABASE_URL` (defaults to the Compose URL above when
unset).
