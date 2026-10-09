# AutoSRE Shop

AutoSRE Shop pairs an Indian e-commerce demo with an admin-only, multi-agent SRE console. The storefront uses INR and a 39-item catalog. A backend-owned monitor runs continuously while FastAPI is running, independent of dashboard sessions, and evaluates service health, latency, request volume, errors, CPU, memory, and dependency impact.

## Run locally

Start the backend from the project root:

```powershell
$env:AUTOSRE_ADMIN_EMAIL = "admin@example.com"
$env:AUTOSRE_ADMIN_PASSWORD = "<your-private-password-of-12-to-128-characters>"
python -m pip install -r requirements.txt
python main.py
```

Start the storefront in another terminal:

```powershell
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173`. The API runs at `http://localhost:8000`.

The backend uses `data/autosre.db` (SQLite) locally when no database URL is set. Create a unique admin using `AUTOSRE_ADMIN_EMAIL` and `AUTOSRE_ADMIN_PASSWORD`; the password must be 12–128 characters. Regular users can register from `/login`. Admin credentials are not shipped in frontend code. Existing browser-only user accounts can be migrated on that browser's first successful login after the database is configured; the matching legacy plaintext entry is removed after the server accepts it. Other browsers migrate when their users sign in there.

Admin routes require a backend-issued token. The admin console is at `/dashboard`; alerts, logs, metrics, services, agents, incidents, and history have their own routes. The `/api/agent/status` endpoint reports the background monitor state, last cycle, service count, recovery/escalation totals, and recent activity. The simulator models frontend, authentication, cart, checkout/order, product, recommendation, payment, shipping, and database services. The chaos controls include payment crash/high latency, frontend traffic spike, database failure, targeted service stops, API error spikes, CPU/memory pressure, network timeouts, and reset.

The monitor distinguishes severity from recovery risk. Service crashes and other supported bounded actions can recover automatically even for P1 incidents. Approval is based on the proposed action, configured safety limits, blast radius, and retry outcomes. Default telemetry settings are a 300 ms warning latency, a 500 ms critical latency threshold sustained for 15 seconds, a 20% critical error rate sustained for 15 seconds, a maximum of four simulated replicas, and three automatic attempts. Set `AUTOSRE_WARNING_LATENCY_MS`, `AUTOSRE_CRITICAL_LATENCY_MS`, `AUTOSRE_CRITICAL_ERROR_RATE_PERCENT`, `AUTOSRE_CRITICAL_WINDOW_SECONDS`, `AUTOSRE_SAFE_REPLICA_LIMIT`, and `AUTOSRE_AUTOMATIC_RECOVERY_ATTEMPTS` to tune these demo values. Recovery remains simulated; this repository does not issue real Kubernetes, cloud, or payment operations. The verifier checks only the affected service set over three consecutive samples. Rejection leaves the incident open for manual action.

Orders and account records are stored in the configured database. Each order is tied to the authenticated account, and checkout retries use an idempotency key. Card, UPI, and net banking orders are recorded as `payment_pending_demo`; the app has no payment gateway and does not charge cards. Cash-on-delivery demo orders progress through the sample delivery states. Incident history, alerts, logs, and service telemetry remain in process memory and reset after a backend restart.

Automatic service-failure demos are disabled by default so a backend restart does not take the storefront offline. Use the admin console's chaos controls to start a scenario manually. To run the automatic sequence on purpose, set `AUTOSRE_DEMO_FAILURES_ENABLED=true` in the backend environment; the service order and timing can be tuned with `AUTOSRE_DEMO_FAILURE_SERVICES`, `AUTOSRE_DEMO_FAILURE_COUNT`, `AUTOSRE_DEMO_START_DELAY_SECONDS`, `AUTOSRE_DEMO_MIN_DOWN_SECONDS`, and `AUTOSRE_DEMO_RECOVERY_PAUSE_SECONDS`.

## Configure the existing deployment

The existing Vercel frontend is `https://self-evolving-assistant-zeta.vercel.app`; its build root is `dashboard`. The existing Render API is `https://autosre-api.onrender.com`. Keep `VITE_API_BASE_URL` in Vercel set to the backend origin without `/api`, for example `https://autosre-api.onrender.com`.

The current Render service has no persistent database configured. Before production signup, sign-in, or order history can work, create a managed PostgreSQL database in Render (or use a PostgreSQL provider you control) and set these values in the existing `autosre-api` web service environment. Do not commit actual values or send passwords in chat. The old backend kept orders only in process memory; they were not durable database records. A check of the live orders endpoint before deployment returned zero records.

- `DATABASE_URL`: the PostgreSQL connection URL supplied by the database provider. The app accepts `postgres://`, `postgresql://`, or `postgresql+psycopg://` URLs.
- `AUTOSRE_ADMIN_EMAIL`: the one configured administrator email.
- `AUTOSRE_ADMIN_PASSWORD`: a private password of at least 12 characters. Set a unique value in Render; it is hashed before storage.
- `AUTOSRE_CORS_ORIGINS`: `https://self-evolving-assistant-zeta.vercel.app` (comma-separate any additional exact frontend origins you use).

After adding the database and environment values, let Render restart the existing backend. Its startup creates missing tables additively and preserves existing records; it does not run a destructive reset. Keep the frontend's `VITE_API_BASE_URL` pointing at the Render service. Pushing frontend code to the connected `main` branch triggers Vercel; pushing backend code triggers Render. Until `DATABASE_URL` and the admin values are configured, auth and order APIs intentionally return HTTP 503 rather than falling back to ephemeral production storage.

The local SQLite file is ignored by Git. Admin credentials, environment values, and database URLs must stay in local environment settings or the hosting providers' secret configuration.

## Run the regression tests

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```
