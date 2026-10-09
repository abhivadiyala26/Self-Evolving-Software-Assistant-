# AutoSRE backend

The backend provides the FastAPI API, account and order persistence, logical service simulator, telemetry monitor, incident workflow, and recovery policy. The API entry point is [`app.py`](app.py). `main.py` at the repository root re-exports this app so the existing Render start command remains valid.

## Modules

- `agents/`: threshold detection, log analysis, root-cause classification, remediation recommendation, and simulated deployment actions
- `services/`: authentication and sessions, optional SQLAlchemy storage, e-commerce service simulation, incident tracking, and risk policy
- `app.py`: API endpoints, process lifecycle, background monitor/simulator tasks, orchestration, and order operations
- `tests/`: authentication, authorization, storage, order, and recovery-policy regression tests

The monitor runs in the FastAPI process and observes the in-process service simulator. Higher-risk recovery actions require admin approval; approved recovery still changes only simulated service state and is checked against telemetry afterward.

The API is currently grouped in `app.py`: `/api/auth/*` handles sign-in and sessions; `/api/status`, `/api/metrics`, `/api/services/*`, and `/api/logs` expose telemetry; `/api/incidents/*`, `/api/alerts/*`, `/api/agents`, `/api/agent/status`, and `/api/chaos/*` support the admin console; `/api/orders` handles the signed-in user's order history and checkout. Incident, alert, agent, chaos, and recovery operations enforce the admin role on the backend.

## Configuration

See [`.env.example`](.env.example) for supported variable names and safe sample values. The application reads process environment variables; it does not load `.env` files automatically. Locally, SQLite is created at `data/autosre.db` by default. `DATABASE_URL` (or `AUTOSRE_DATABASE_URL`) can point to PostgreSQL for persistent accounts and orders. When running on Render without a database URL, persistent accounts and orders are unavailable and demo state is temporary.

Important settings include `AUTOSRE_ADMIN_EMAIL`/`AUTOSRE_ADMIN_PASSWORD`, `DEMO_USER_EMAIL`/`DEMO_USER_PASSWORD`, `AUTOSRE_CORS_ORIGINS`, monitoring thresholds, and recovery limits. Do not commit credentials or database URLs.

## Install and run

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app:app --reload --port 8000
```

For development and tests, install `backend/requirements-dev.txt` instead. The root `requirements.txt` forwards to the production backend requirements for Render compatibility.

## Test

```powershell
python -m unittest discover -s backend/tests -v
```

The suite covers registration and admin role separation, session revocation, temporary demo authentication, order authorization/idempotency, and bounded recovery decisions.

## Limitations

Service health, metrics, incident history, logs, alerts, and recovery are simulated or held in process memory. User/session/order records use the configured SQL database; without one, new accounts are temporary and order endpoints report storage unavailable. No real infrastructure or payment operations are performed.
