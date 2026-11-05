# RepoPilot

Autonomous software engineering agent. See `RepoPilot_Project_Plan.md` and `docs/implementation-steps.md` for the full plan.

## Local development

### PostgreSQL

Start the local database with Docker Compose:

```bash
docker compose up -d postgres
```

Wait until the service is healthy:

```bash
docker compose ps
```

Connection string (matches `.env.example`):

```text
postgresql://repopilot:repopilot@localhost:5432/repopilot
```

Stop the database with:

```bash
docker compose down
```
