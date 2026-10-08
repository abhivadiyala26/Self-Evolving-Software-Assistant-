# AutoSRE Shop

AutoSRE Shop pairs an Indian e-commerce demo with an admin-only, multi-agent SRE console. The storefront uses INR and a 39-item catalog. A backend-owned monitor runs continuously while FastAPI is running, independent of dashboard sessions, and evaluates service health, latency, request volume, errors, CPU, memory, and dependency impact.

## Run locally

Start the backend from the project root:

```powershell
python -m pip install fastapi uvicorn pydantic
python main.py
```

Start the storefront in another terminal:

```powershell
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173`. The API runs at `http://localhost:8000`.

## Demo accounts

- Admin: `admin@technogear.com` / `password`
- Storefront user: create an account at `/login`, or use the demo data shortcut on that page.

Admin routes require a backend-issued token. The admin console is at `/dashboard`; alerts, logs, metrics, services, agents, incidents, and history have their own routes. The `/api/agent/status` endpoint reports the background monitor state, last cycle, service count, recovery/escalation totals, and recent activity. The simulator models frontend, authentication, cart, checkout/order, product, recommendation, payment, shipping, and database services. The chaos controls include payment crash/high latency, frontend traffic spike, database failure, targeted service stops, API error spikes, CPU/memory pressure, network timeouts, and reset.

The monitor waits for sustained threshold signals before starting analysis. Low- and medium-risk incidents use bounded simulated recovery and post-recovery verification automatically. High- and critical-risk actions wait for admin approval; three failed automatic attempts escalate to approval. Rejection leaves the incident open for manual action. Store orders are blocked while checkout or payment is unhealthy. The admin console and storefront use a light, compact layout with horizontal console navigation.

## Demo data and limits

This repository does not configure a database or real payment, cloud, or Kubernetes integrations. Service telemetry, alerts, incidents, logs, orders, and admin sessions are in memory and reset when the backend process restarts. The product catalog and customer cart, wishlist, and demo user profile are local frontend data. Admin credentials are fixed demo credentials; user signup stores demo credentials in browser local storage. Use this setup for local demonstration, not production accounts or payments.
