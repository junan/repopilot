# RepoPilot — Autonomous Software Engineering Agent

**Project proposal and incremental implementation plan**  
**Primary language:** Python 3.13+  
**Goal:** A production-minded, demonstrable senior-level AI coding agent and recruiting portfolio project.

## 1. Purpose and product vision

RepoPilot is an AI software engineering assistant that accepts a GitHub issue or developer task, investigates a repository, proposes a plan, edits code, runs tests in a restricted environment, and prepares a draft pull request for human review.

This is not a chatbot wrapper. The goal is to demonstrate Python backend design, LLM orchestration, secure tool execution, data modeling, async processing, fault tolerance, observability, automated testing, and engineering judgment.

**Example task:** “The booking API occasionally creates duplicate reservations when clients retry requests. Investigate the cause, implement a safe fix, and add regression tests.”

**Expected user journey:**
1. Select an authorized GitHub repository and submit a task.
2. Agent inspects repository structure, related code, and tests.
3. Agent explains its findings and produces an implementation plan.
4. Agent generates a patch in an isolated workspace.
5. Agent runs approved checks and tests inside a restricted sandbox.
6. Agent uses test feedback for bounded revisions.
7. User reviews diff, logs, costs, and test evidence.
8. With explicit approval, agent pushes changes and opens a **draft** pull request.

## 2. Product scope

### Core MVP
- Create and track engineering tasks via REST API.
- Analyze a repository using safe file-listing, file-reading, and text-search tools.
- Use an LLM for a structured plan and bounded tool calls.
- Generate and review file patches.
- Run tests in an isolated environment.
- Store per-run events, errors, and usage metrics.
- Display execution timeline, diffs, and tests in a minimal dashboard.
- Request explicit approval before publishing a draft PR.

### Out of scope initially
- Automatic merges to main branches.
- Unrestricted shell access, arbitrary network access, or production credential access.
- Multi-agent teams, fine-tuning, vector databases, Kafka, Kubernetes, and complex microservices unless there is a demonstrated need.
- Claims that the agent always correctly finds and fixes bugs.

## 3. Proposed technology stack

| Layer | Choice | Rationale |
|---|---|---|
| Main language | Python 3.13+ | Core service, agents, jobs, tooling |
| HTTP API | FastAPI | Async-friendly endpoints, typed request/response handling |
| Data validation | Pydantic | Strong schemas for APIs, plans, and tool arguments |
| Persistence | PostgreSQL | Transactional task/run state and audit events |
| ORM/migrations | SQLAlchemy + Alembic | Explicit models and schema evolution |
| LLM | OpenAI API | Planning and code-generation steps |
| Agent runtime | OpenAI Agents SDK (or a small custom orchestrator) | Tool lifecycle and controlled execution |
| Jobs | Celery + Redis | Background execution and queueing |
| Sandboxing | Docker | Ephemeral restricted workspaces for code/tests |
| Version control | Git + GitHub API | Repository operations and draft PR creation |
| UI | React + TypeScript | Simple developer-facing dashboard |
| Test suite | pytest, pytest-asyncio | Unit/integration tests |
| Telemetry | OpenTelemetry | Traces and operational visibility |
| Local infra | Docker Compose | Reproducible development |
| Delivery | GitHub Actions + optionally AWS | CI/CD and deployability |

**Architecture choice:** A modular Python monolith with separate background worker processes. Avoid premature service splitting. Choose newer libraries by verifying actual compatibility at implementation time.

## 4. High-level architecture

```text
React dashboard
  |  REST APIs + SSE events
  v
Python FastAPI application
  |-- Auth and repository authorization
  |-- Task API / approval API
  |-- PostgreSQL: durable tasks, runs, events, artifacts
  |-- Queue publisher (Redis / Celery)
  |
  v
Python background worker / task orchestrator
  |-- Agent engine: plan -> act -> observe -> evaluate
  |-- OpenAI API: structured reasoning and tool selection
  |-- Repository tools: list/read/search files
  |-- GitHub integration: branches / draft pull requests
  |-- Sandbox manager: isolated patching and test execution
  |-- Traces, usage/cost accounting, progress events
```

The application, not the model, enforces permissions, allowed tools, timeouts, resource limits, approval gates, and maximum agent steps.

## 5. Engineering components

### 5.1 Task management
- API to create, list, retrieve, cancel, and inspect tasks.
- Persist state transitions in PostgreSQL.
- Example states: `PENDING -> PLANNING -> EXECUTING -> VALIDATING -> AWAITING_APPROVAL -> COMPLETED`.
- Add `FAILED` and `CANCELLED` terminal states, with explicit transition rules.
- Use request idempotency keys and concurrency controls.

### 5.2 Agent orchestration
- Convert task into structured, auditable implementation plans.
- Register typed tools, validate inputs, and record results.
- Cap steps, runtime, retries, context size, token usage, and cost.
- Summarize prior context safely rather than sending unlimited file contents.
- Treat repository content and tool output as untrusted input; prevent prompt-injection instructions from overriding tool permissions.

### 5.3 Repository intelligence
- Clone explicitly authorized repositories at pinned commits.
- Provide bounded file-tree discovery, text search, and file reading.
- Exclude secret files and large or irrelevant directories as needed.
- Start with deterministic search; consider semantic retrieval only after evaluation shows a benefit.

### 5.4 Safe patch and test execution
- Maintain per-task isolated workspace.
- Apply limited, reviewable patches and create unified diffs.
- Use short-lived containers with resource limits, restricted privileges, and no host-mounted secrets or Docker socket.
- Disable outbound network by default; permit only tightly controlled dependencies when essential.
- Restrict executable commands and capture stdout, stderr, exit codes, and timeouts.
- Do not claim Docker alone is a complete sandbox against hostile code; evaluate stronger isolation before exposing the service to untrusted public repositories.

### 5.5 GitHub workflow
- Scoped repository access and least-privilege credentials.
- Create branches, commits, and **draft** PRs only following approval.
- Implement rate-limit handling, backoff, and safe retries.
- Audit every external write action.

### 5.6 Observability and quality
- Collect state transitions, tool activity, errors, durations, token counts, and cost.
- Use structured logs and OpenTelemetry traces; avoid recording secrets or unnecessarily sensitive code.
- Benchmark against fixed tasks with known expected outcomes.
- Track task completion, valid patch rates, test pass rates, cost, and failure classes.

## 6. Initial data model

| Table | Core fields/responsibility |
|---|---|
| `repositories` | ID, URL, authorization metadata, default branch |
| `tasks` | ID, repository ID, description, status, idempotency key, created time |
| `agent_runs` | ID, task ID, attempt, status, checkpoint, token/cost usage, timestamps |
| `run_steps` | ID, run ID, sequence, tool/action, status, sanitized result, timing |
| `artifacts` | ID, run ID, type, storage reference, content hash |
| `approvals` | ID, task/run ID, user decision, reviewed commit or patch hash, time |
| `evaluations` | ID, scenario, run ID, expected/observed outcome, metrics |

Design considerations: schema migrations, transactions, unique constraints, optimistic concurrency or row locks, append-only execution events where appropriate, and reliable recovery from crashes.

## 7. Implementation roadmap — one small iteration at a time

Each iteration ends in a runnable, testable, demonstrable deliverable. Do not start the next until basic acceptance tests pass.

### Iteration 1 — Python service foundation
**Build:** FastAPI setup, environment-based config, PostgreSQL, SQLAlchemy models, Alembic, `POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, Docker Compose, pytest, lint/format checks.

**Acceptance:** Start locally with documented commands; migrations work on fresh DB; create/read/list endpoints pass tests; invalid inputs return useful errors.

**Demo:** Create a task via API and retrieve its persisted record.

### Iteration 2 — Repository analysis
**Build:** Validate repository URLs and permissions, clone into a controlled workspace, file tree, safe read/search tools, path restrictions, structured search responses.

**Acceptance:** Agent tooling can identify relevant source files in a demo repo; path traversal and unauthorized file access are blocked.

**Demo:** Search a repo for the booking handler and related tests.

### Iteration 3 — LLM planning and tool calling
**Build:** OpenAI integration, structured task plan, typed tool schemas, bounded agent loop, plan and tool-run logging, usage accounting.

**Acceptance:** From a task description, the agent produces a structured plan grounded in repository files, with a hard limit on tool calls and spend.

**Demo:** Submit a bug description and inspect the resulting investigation plan.

### Iteration 4 — Code editing
**Build:** Patch generation, isolated worktrees, validation, diff generation, persistent patch artifact, rollback/discard behavior.

**Acceptance:** Agent produces a valid, reviewable patch on a known sample task; the original default branch remains untouched.

**Demo:** Show generated diff and explanation.

### Iteration 5 — Sandbox tests and repair loop
**Build:** Restricted container execution, approved test commands, output capture, timeouts, feedback-driven bounded retries.

**Acceptance:** Tests run safely against the modified workspace; failures are visible; maximum attempts are respected; test results are attached to the run.

**Demo:** Fix a known defect and display a regression test passing.

### Iteration 6 — Durable background jobs
**Build:** Celery worker, async task dispatch, stored checkpoints, retries, cancellation, duplicate-run prevention, SSE event streaming.

**Acceptance:** API responds without blocking; restart and failure cases are handled predictably; progress can be observed; side effects are not duplicated.

**Demo:** Start a task, follow its live state, and inspect a recovered or cancelled run.

### Iteration 7 — GitHub integration and dashboard
**Build:** React UI, run timeline, diff/test log viewer, approval gate, GitHub branch/commit/draft PR integration.

**Acceptance:** A user can review the patch before approving a draft PR; denied approval causes no GitHub write.

**Demo:** End-to-end issue-to-draft-PR workflow on a safe sample repository.

### Iteration 8 — Production hardening and benchmark
**Build:** OpenTelemetry, documented error taxonomy, cost limits, security review, concurrency/integration tests, reproducible benchmark scenarios, CI/CD and deployment, architecture decision records.

**Acceptance:** Automated tests and benchmark scripts run in CI; basic operational metrics are available; README contains honest measured results and known limitations.

**Demo:** Production-oriented architecture walkthrough with real benchmark report.

## 8. Senior-level engineering problems to demonstrate

| Scenario | Engineering response |
|---|---|
| Worker crashes mid-run | Durable checkpoints and explicit restart/recovery rules |
| Duplicate task submission | Idempotency and unique/transactional state transitions |
| Repeated LLM tool loops | Budgets, max-step caps, cancellation, timeouts |
| Malicious repository content | Treat files as untrusted; enforce permissions in Python; sandbox execution |
| Unsafe generated changes | Isolated tests, diff review, explicit approval |
| GitHub rate limiting | Bounded retries with exponential backoff and jitter |
| Excess token spend | Context management, cost caps, usage metrics |
| Concurrent runs | Isolation, locks/leases, state transition validation |
| Misleading agent conclusions | Evidence-linked plans, tests, benchmark comparisons |
| Operational failure | Health checks, logs, traces, alertable errors, rollback plan |

## 9. Suggested repository structure

```text
repopilot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── tools/
│   │   ├── repositories/
│   │   ├── execution/
│   │   ├── jobs/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── core/
│   ├── migrations/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── evaluations/
│   └── pyproject.toml
├── frontend/
├── infrastructure/
├── docs/
│   ├── architecture.md
│   ├── decisions/
│   ├── security.md
│   └── benchmarks.md
├── examples/
├── docker-compose.yml
└── README.md
```

## 10. Recruiter-facing deliverables

1. **Public GitHub repository:** Clear README, architecture, setup, security tradeoffs, tests, and measurable results.
2. **Live/safe demo:** Preconfigured public sample repo and reproducible issue so viewers do not need GitHub credentials.
3. **Short walkthrough video:** Show issue submission, investigation, patch, tests, and review.
4. **Architecture explanation:** Explain why modular monolith, why restricted tools, why durable state, and how recovery works.
5. **CV project entry (use only once implemented):**

> **RepoPilot — AI Software Engineering Agent | Python, FastAPI, OpenAI, PostgreSQL, Docker**  
> Designed and developed an AI-powered coding agent that analyzes GitHub repositories, generates code changes, runs tests in isolated environments, and prepares reviewable pull requests. Implemented typed LLM tool calling, async orchestration, security safeguards, execution tracking, and automated evaluation.

Show actual benchmark outcomes, not invented success percentages.

## 11. Definition of done

- [ ] Tasks are stored transactionally and can be inspected via API.
- [ ] Repository reading is authorized and path-restricted.
- [ ] Agent actions have typed inputs and hard resource/step budgets.
- [ ] Generated changes remain isolated until reviewed.
- [ ] Test execution cannot access host secrets or unrestricted resources.
- [ ] Worker interruptions have tested recovery behavior.
- [ ] GitHub writes require explicit human approval.
- [ ] All meaningful actions have timestamps, outcomes, and sanitized logs.
- [ ] Unit, integration, and reproducible evaluation suites run successfully.
- [ ] Project has an accessible end-to-end portfolio demo.

## 12. Immediate next milestone

**Start with Iteration 1 only.** Build the Python FastAPI task API, PostgreSQL persistence, schema migration, Docker Compose, and pytest tests. Keep the first release small, complete, and operational before adding LLM functionality.

**Working principle:** Small verified iterations; favor sound engineering choices over unnecessary technology; use demonstrable outcomes to show seniority.
