# RepoPilot — implementation steps

Working queue for this repository. Source of truth for “next step.”

The product goal is in `RepoPilot_Project_Plan.md`: an AI coding agent that takes a task, inspects an authorized repo, plans, patches in isolation, runs tests in a sandbox, and opens a **draft** pull request only after explicit approval.

## How we work

When you say **next step**:

1. Implement only the first unchecked step below.
2. Run that step’s tests (and the existing suite).
3. Commit that step if tests pass.
4. Check the box here in the same commit.
5. Stop. Do not start the following step.

Rules:

- Python 3.13+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, pytest, Ruff.
- `pyproject.toml` is the dependency source of truth.
- The application enforces permissions, limits, and approval. The model never does.
- Repository contents and tool output are untrusted input.
- No LLM, Celery, Docker sandbox, GitHub writes, or React until the step that introduces them.
- Each step stays demoable: tests pass on a clean checkout of that commit.

Locked choices for early steps:

- Task id is a UUID.
- Idempotency uses an `Idempotency-Key` header.
- Status changes go through an explicit transition map.
- Integration tests that need Postgres are marked and use `DATABASE_URL`. Unit tests stay free of Docker.

## Iteration 1 — Python service foundation

Acceptance for the whole iteration: documented commands start the app, migrations apply on a fresh database, create/list/get task endpoints pass tests, and invalid input returns a useful error.

### Step 1 — Package skeleton and tooling

- [x] `backend/pyproject.toml` for a `repopilot` package on Python 3.13+.
- [x] Runtime deps reserved for later steps are not required yet; include what this step needs to import a package and run Ruff and pytest.
- [x] `backend/app/__init__.py`, `backend/tests/unit/`.
- [x] Ruff configuration and a root `.gitignore`.
- [x] Smoke test that imports the package.

**Test:** `ruff check` and `pytest` pass.  
**Commit:** `chore: add Python package skeleton`

### Step 2 — Environment configuration

- [x] `app/core/config.py` using pydantic-settings.
- [x] Settings for app name, environment, and `database_url`.
- [x] `.env.example` with the local Postgres URL and no secrets.
- [x] Unit tests for defaults and invalid or missing database URL.

**Test:** settings tests pass without a running database.  
**Commit:** `feat: load service configuration from the environment`

### Step 3 — FastAPI app and health check

- [x] Application factory in `app/main.py`.
- [x] `GET /health` returns a small JSON payload.
- [x] Tests through the ASGI test client.

**Test:** health endpoint returns 200. Unknown routes return 404.  
**Commit:** `feat: add FastAPI app and health endpoint`

### Step 4 — Local PostgreSQL

- [x] Root `docker-compose.yml` with PostgreSQL 16, a named volume, and a healthcheck.
- [x] Credentials match `.env.example`.
- [x] README section with the compose command and the resulting connection string.

**Test:** `docker compose config` is valid. Postgres becomes healthy with the documented command.  
**Commit:** `chore: add local PostgreSQL compose stack`

### Step 5 — Database session and Task model

- [x] SQLAlchemy 2 engine and session factory wired to settings.
- [x] `tasks` model: id, description, status, idempotency key, timestamps.
- [x] Unique constraint on the idempotency key.
- [x] Status values include `PENDING`, `PLANNING`, `EXECUTING`, `VALIDATING`, `AWAITING_APPROVAL`, `COMPLETED`, `FAILED`, and `CANCELLED`.
- [x] Model tests cover required fields and the unique key.

**Test:** model tests pass on PostgreSQL.  
**Commit:** `feat: add task persistence model`

### Step 6 — Alembic migrations

- [x] Alembic reads the same metadata and database URL as the app.
- [x] Initial revision creates `tasks`.
- [x] Test upgrades a fresh database to head and checks the table exists.
- [x] Downgrade drops what the revision created.

**Test:** upgrade and downgrade succeed on an empty database.  
**Commit:** `feat: add initial tasks migration`

### Step 7 — Task service

- [x] Create, list, and get tasks.
- [x] New tasks start as `PENDING`.
- [x] Repeating the same idempotency key and same body returns the original task.
- [x] The same key with a different body is rejected.
- [x] Missing task is a typed not-found error.
- [x] A pure transition function encodes legal status changes, with tests. No endpoint exposes transitions yet.

**Test:** service tests cover create, replay, conflict, not found, and illegal transitions.  
**Commit:** `feat: add task service with idempotency`

### Step 8 — Task HTTP API

- [ ] `POST /tasks`, `GET /tasks`, `GET /tasks/{id}`.
- [ ] Request and response schemas. Description is required and length-limited.
- [ ] `201` on create, `200` on replay of the same idempotency key, `404` on missing id, `422` on invalid input, `409` on an idempotency conflict.
- [ ] Errors use one JSON shape with a stable code and a human-readable message.

**Test:** API tests hit a real database and cover the cases above.  
**Commit:** `feat: expose task create, list, and get endpoints`

### Step 9 — Local run workflow

- [ ] Document install, compose, migrate, serve, test, and lint commands in the README.
- [ ] A single check command runs Ruff and pytest.
- [ ] README demo: create a task with curl and fetch it back by id.

**Test:** the documented check command passes. The curl demo works against the compose database.  
**Commit:** `docs: document the iteration 1 task API workflow`

Iteration 1 is done when step 9 is checked and the iteration acceptance above holds.

## Iteration 2 — Repository analysis

Acceptance: tooling finds relevant files in a demo repo. Path traversal and reads outside the workspace fail.

### Step 10 — Sample repository fixture

- [ ] Small Python fixture under `examples/` with a booking handler and a failing or missing idempotency test.
- [ ] The fixture is the only repo used by tool tests.

**Commit:** `test: add booking sample repository`

### Step 11 — Path policy

- [ ] Resolve paths inside a workspace root.
- [ ] Reject absolute paths, `..`, symlink escapes, secret-like filenames, and oversized files.
- [ ] Unit tests for each rejection.

**Commit:** `feat: restrict repository paths to the workspace`

### Step 12 — Clone authorized repositories

- [ ] Allowlist of repository URLs.
- [ ] Clone at a pinned commit into a per-task workspace directory.
- [ ] Refuse URLs that are not allowlisted.
- [ ] Tests use the local fixture via a file URL or a copied tree so they do not need GitHub credentials.

**Commit:** `feat: clone allowlisted repositories at a pinned commit`

### Step 13 — List, read, and search tools

- [ ] Typed tools: file tree, read file, text search.
- [ ] Bounded results: depth, file count, bytes, and match count.
- [ ] Structured responses, no raw shell.
- [ ] Tests find the booking handler and its tests, and prove traversal is blocked.

**Commit:** `feat: add bounded repository list, read, and search tools`

## Iteration 3 — LLM planning and tool calling

Acceptance: a task description yields a structured plan grounded in files, with a hard cap on tool calls and spend. Tests use a fake model.

### Step 14 — Run and step tables

- [ ] Migration for `agent_runs` and `run_steps`.
- [ ] A run belongs to a task. Steps are append-only and ordered.
- [ ] Store status, timestamps, and token or cost fields.

**Commit:** `feat: persist agent runs and steps`

### Step 15 — Model client and plan schema

- [ ] Narrow client interface for a structured plan call.
- [ ] Production implementation calls OpenAI. Tests use a fake.
- [ ] Plan schema: findings, files to change, steps, and risks. Extra model fields are ignored.

**Commit:** `feat: add structured planning with a fake model in tests`

### Step 16 — Tool registry

- [ ] Tools from step 13 registered with Pydantic argument schemas.
- [ ] Unknown tools and invalid arguments fail before execution.
- [ ] Every call and result is stored as a run step. Results are size-limited.

**Commit:** `feat: validate and record typed tool calls`

### Step 17 — Bounded agent loop

- [ ] Loop is plan, then a limited number of tool calls, then a final plan or summary.
- [ ] Caps for steps, runtime, and token or cost budget.
- [ ] Hitting a cap stops the run as `FAILED` with a recorded reason.
- [ ] Tool output is data for the model, never new permissions.
- [ ] API or service method returns the stored plan and steps for a task.

**Commit:** `feat: run a budgeted planning loop`

## Iteration 4 — Code editing

Acceptance: a known sample task produces a reviewable patch. The fixture’s default branch stays unchanged.

### Step 18 — Patch artifacts

- [ ] Artifact record with type, storage path, and content hash.
- [ ] Unified diff stored for the run.
- [ ] Apply and validate a patch inside a git worktree created from the pinned commit.
- [ ] Discard deletes the worktree and leaves the source checkout unchanged.

**Commit:** `feat: apply patches in an isolated worktree`

### Step 19 — Patch step in the agent loop

- [ ] Model proposes a patch through a typed tool. Tests use the fake model and a known edit.
- [ ] Invalid patches are rejected and recorded.
- [ ] The run stores the diff and a short explanation.

**Commit:** `feat: record a reviewable patch from the agent loop`

## Iteration 5 — Sandbox tests and repair

Acceptance: tests run against the modified workspace, failures are visible, attempt limits hold, and results attach to the run.

### Step 20 — Command allowlist

- [ ] Only configured test commands can run. Arguments are structured, not a free shell string.
- [ ] Timeout and output byte caps.

**Commit:** `feat: allowlist sandbox test commands`

### Step 21 — Container test runner

- [ ] Short-lived container, read-only root where practical, no host secrets, no Docker socket, memory and CPU limits.
- [ ] Network disabled by default.
- [ ] Capture stdout, stderr, exit code, and duration onto the run.
- [ ] Tests assert a passing command and a timeout.

**Commit:** `feat: run tests in a restricted container`

### Step 22 — Bounded repair loop

- [ ] On test failure, allow a limited number of new patch attempts.
- [ ] Stop on success, attempt cap, or budget cap.
- [ ] Each attempt keeps its own diff and test log.

**Commit:** `feat: retry patches from test feedback within a cap`

## Iteration 6 — Durable background jobs

Acceptance: the API returns without waiting for the agent. Restart, duplicate dispatch, and cancellation behave predictably.

### Step 23 — Celery and Redis

- [ ] Redis in Compose. Worker process targets the same app code.
- [ ] Creating a task enqueues a run instead of executing inline.
- [ ] A sync path remains available for tests.

**Commit:** `feat: dispatch agent runs on a Celery worker`

### Step 24 — Checkpoints, duplicates, and cancellation

- [ ] Checkpoint after each step so a crashed run can resume without repeating finished side effects.
- [ ] One active run per task.
- [ ] Cancel moves the task to `CANCELLED` and the worker stops at the next step boundary.
- [ ] Tests kill or simulate a crash between steps and assert recovery.

**Commit:** `feat: checkpoint, deduplicate, and cancel agent runs`

### Step 25 — Progress events

- [ ] `GET /tasks/{id}/events` streams step updates with server-sent events.
- [ ] Events come from stored rows, so a reconnect does not invent history.

**Commit:** `feat: stream task progress over SSE`

## Iteration 7 — GitHub integration and dashboard

Acceptance: a person can review the patch. Approval opens a draft PR. Denial performs no GitHub write.

### Step 26 — Approval gate

- [ ] `approvals` table and `POST /tasks/{id}/approval`.
- [ ] Approval records the reviewed patch hash.
- [ ] The task reaches `AWAITING_APPROVAL` only after a patch and test evidence exist.
- [ ] Denial stores the decision and does not call GitHub.

**Commit:** `feat: require explicit approval before publication`

### Step 27 — Draft pull request

- [ ] GitHub client creates a branch, commit, and draft PR only after an approval whose hash matches the current patch.
- [ ] Retries use backoff and jitter. Writes are audited as run steps.
- [ ] Tests use a fake GitHub client. Denied and hash-mismatch cases perform zero write calls.

**Commit:** `feat: open a draft pull request after approval`

### Step 28 — React dashboard

- [ ] Frontend lists tasks and shows one task’s timeline, diff, test log, and token or cost summary.
- [ ] Approve and deny buttons call the approval API.
- [ ] Empty, pending, failed, and awaiting-approval states render.

**Commit:** `feat: add a dashboard for review and approval`

### Step 29 — End-to-end demo

- [ ] Document the sample booking bug from task creation through draft PR using the fake or a recorded run, so viewers do not need GitHub credentials.
- [ ] One automated test covers that path against fakes and the fixture repo.

**Commit:** `test: cover the issue-to-draft-pr demo path`

## Iteration 8 — Production hardening and benchmark

Acceptance: CI runs tests and the benchmark. README states measured results and known limits.

### Step 30 — Traces, errors, and cost caps

- [ ] OpenTelemetry spans around API requests, runs, tool calls, and sandbox commands.
- [ ] Documented error codes for budget, timeout, tool failure, sandbox failure, and GitHub failure.
- [ ] A run stops when projected cost crosses the configured cap.
- [ ] Logs omit secrets and truncate file contents.

**Commit:** `feat: add traces, error codes, and cost caps`

### Step 31 — Evaluation suite

- [ ] Fixed scenarios with expected files or expected test outcomes.
- [ ] Script reports completion, patch validity, test pass, cost, and failure class.
- [ ] Results are produced by the script. The README quotes a real run and lists limits.

**Commit:** `test: add reproducible benchmark scenarios`

### Step 32 — CI and architecture notes

- [ ] GitHub Actions runs Ruff, unit tests, and integration tests that do not need paid APIs.
- [ ] Short ADRs for the modular monolith, restricted tools, and durable run state.
- [ ] `docs/security.md` states the sandbox limits and what this service does not protect against.

**Commit:** `ci: run checks and document architecture decisions`

## Definition of done

The project is complete when every step above is checked and section 11 of `RepoPilot_Project_Plan.md` is true, with benchmark numbers taken from step 31 rather than estimated.
