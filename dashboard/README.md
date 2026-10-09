# AutoSRE frontend

This React/Vite application contains the ShopSphere storefront and the AutoSRE admin console. It uses React Router for routes, Recharts for telemetry charts, and Lucide icons. The existing `dashboard/` path is retained because it is the root directory configured for the Vercel project.

## Pages and API

- `src/components/ShopSphere.jsx` renders the public e-commerce experience and account flows.
- `src/components/Login.jsx` handles user/admin sign-in and demo account suggestions.
- `src/components/Dashboard.jsx` and related components render the protected SRE console, incidents, services, metrics, alerts, logs, and agent activity.
- `src/api.js` builds the API URL from `VITE_API_BASE_URL` and appends `/api`.

## Configure and run

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Set `VITE_API_BASE_URL` in `.env.local` to the backend origin without `/api`. Vite loads this file automatically. For the deployed frontend, set it to the Render API origin, such as `https://autosre-api.onrender.com`.

## Build and lint

```powershell
npm run build
npm run lint
```
