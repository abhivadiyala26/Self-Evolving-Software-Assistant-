# AutoSRE Shop

AutoSRE Shop pairs an Indian e-commerce demo with an admin-only, multi-agent SRE console. The storefront uses INR and a 39-item catalog. A backend-owned monitor runs continuously while FastAPI is running, independent of dashboard sessions, and evaluates service health, latency, request volume, errors, CPU, memory, and dependency impact.

## Run locally

Start the backend from the project root:

```powershell
$env:AUTOSRE_ADMIN_EMAIL = "admin@example.com"
$env:AUTOSRE_ADMIN_PASSWORD = "<your-private-password-of-12-to-128-characters>"
$env:DEMO_USER_EMAIL = "demo@example.com"
$env:DEMO_USER_PASSWORD = "<your-private-password-of-8-to-128-characters>"
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

The backend uses `data/autosre.db` (SQLite) locally when no database URL is set. The configured admin uses `AUTOSRE_ADMIN_EMAIL` and `AUTOSRE_ADMIN_PASSWORD` (12–128 characters); the optional fixed demo user uses `DEMO_USER_EMAIL` and `DEMO_USER_PASSWORD` (8–128 characters). Credentials are checked and hashed by the backend; no demo passwords are shipped in frontend code. When no database is available, signups create temporary server-side demo accounts that disappear when the backend restarts. When local SQLite or another database is ready, signups are persistent. The login page states which mode is active and reports missing demo account configuration.

Admin routes require a backend-issued token. The admin console is at `/dashboard`; alerts, logs, metrics, services, agents, incidents, and history have their own routes. The `/api/agent/status` endpoint reports the background monitor state, last cycle, service count, recovery/escalation totals, and recent activity. The simulator models frontend, authentication, cart, checkout/order, product, recommendation, payment, shipping, and database services. The chaos controls include payment crash/high latency, frontend traffic spike, database failure, targeted service stops, API error spikes, CPU/memory pressure, network timeouts, and reset.

The monitor distinguishes severity from recovery risk. Service crashes and other supported bounded actions can recover automatically even for P1 incidents. Approval is based on the proposed action, configured safety limits, blast radius, and retry outcomes. Default telemetry settings are a 300 ms warning latency, a 500 ms critical latency threshold sustained for 15 seconds, a 20% critical error rate sustained for 15 seconds, a maximum of four simulated replicas, and three automatic attempts. Set `AUTOSRE_WARNING_LATENCY_MS`, `AUTOSRE_CRITICAL_LATENCY_MS`, `AUTOSRE_CRITICAL_ERROR_RATE_PERCENT`, `AUTOSRE_CRITICAL_WINDOW_SECONDS`, `AUTOSRE_SAFE_REPLICA_LIMIT`, and `AUTOSRE_AUTOMATIC_RECOVERY_ATTEMPTS` to tune these demo values. Recovery remains simulated; this repository does not issue real Kubernetes, cloud, or payment operations. The verifier checks only the affected service set over three consecutive samples. Rejection leaves the incident open for manual action.

Persistent orders and account records require a configured database. Each order is tied to the authenticated account, and checkout retries use an idempotency key. In database-free demo mode, authentication still works with the fixed environment-configured demo accounts and temporary signups; order endpoints return a clear storage-unavailable response instead of claiming an order was placed. With a database, card, UPI, and net banking orders are recorded as `payment_pending_demo`; the app has no payment gateway and does not charge cards. Cash-on-delivery demo orders progress through the sample delivery states. Incident history, alerts, logs, service telemetry, and temporary accounts remain in process memory and reset after a backend restart.

Automatic service-failure demos are disabled by default so a backend restart does not take the storefront offline. Use the admin console's chaos controls to start a scenario manually. To run the automatic sequence on purpose, set `AUTOSRE_DEMO_FAILURES_ENABLED=true` in the backend environment; the service order and timing can be tuned with `AUTOSRE_DEMO_FAILURE_SERVICES`, `AUTOSRE_DEMO_FAILURE_COUNT`, `AUTOSRE_DEMO_START_DELAY_SECONDS`, `AUTOSRE_DEMO_MIN_DOWN_SECONDS`, and `AUTOSRE_DEMO_RECOVERY_PAUSE_SECONDS`.

## Configure the existing deployment

The existing Vercel frontend is `https://self-evolving-assistant-zeta.vercel.app`; its build root is `dashboard`. The existing Render API is `https://autosre-api.onrender.com`. Keep `VITE_API_BASE_URL` in Vercel set to the backend origin without `/api`, for example `https://autosre-api.onrender.com`.

The current Render service can run without a database for the college-project demo. In the existing `autosre-api` service's Environment settings, configure these values; use private values and never commit them:

- `AUTOSRE_ADMIN_EMAIL`: the admin demo account email.
- `AUTOSRE_ADMIN_PASSWORD`: its private password, at least 12 characters.
- `DEMO_USER_EMAIL`: the user demo account email, different from the admin email.
- `DEMO_USER_PASSWORD`: its private password, at least 8 characters.
- `AUTOSRE_CORS_ORIGINS`: `https://self-evolving-assistant-zeta.vercel.app` (comma-separate any additional exact frontend origins you use).

Render will restart the existing backend after environment changes. Keep the frontend's `VITE_API_BASE_URL` pointing at the Render service. Pushing frontend code to the connected `main` branch triggers Vercel; pushing backend code triggers Render. `DATABASE_URL` is optional for demo sign-in and admin controls. It is needed only for persistent new accounts and order history; those features return an explicit unavailable response in database-free mode. Temporary signups and sessions are in process memory and can disappear on restart or when Render replaces the instance.

The local SQLite file is ignored by Git. Admin credentials, environment values, and database URLs must stay in local environment settings or the hosting providers' secret configuration.

## Run the regression tests

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```
