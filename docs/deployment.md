# Deployment Guide — GPS Target Calculating System

## Current Setup: Localhost

Both servers run locally during development and defense demos:

| Service | Command | URL |
|---------|---------|-----|
| Backend (FastAPI) | `uv run uvicorn app.main:app --reload --port 8000` (from `backend/`) | http://localhost:8000/docs |
| Frontend (Vite) | `npm run dev` (from `frontend/`) | http://localhost:5173 |

Vite proxies `/api` and `/ws` to the backend, so only the frontend URL is needed in the browser.

## Free-Tier Deployment (Student Budget)

If a shareable link is needed for the defense (teacher opens a URL without cloning), these free options were evaluated:

| Platform | Free Tier | WebSocket | Verdict |
|----------|-----------|-----------|---------|
| **Render** | 750 h/month, sleeps after 15 min idle | Yes (native) | **Recommended** — no credit card, supports Python + Node in one service or two linked services, WebSocket works out of the box |
| **Railway** | $5 credit/month (expires) | Yes | Good, but credit is temporary — not ideal for a thesis that must stay up through review |
| **Vercel** | Hobby free forever | No (serverless functions don't hold WS) | Frontend only — would need a separate backend host, adds complexity |

### Recommended: Render (Two Services)

1. **Backend** — Web Service, runtime Python 3.11, build `pip install -r requirements.txt` or `uv sync`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
2. **Frontend** — Static Site, build `npm ci && npm run build`, publish `frontend/dist`, set `VITE_API_URL` to the backend's Render URL and remove the Vite proxy.

> Note: The free tier sleeps after inactivity; the first request after sleep takes ~30 s to wake. Mention this during the demo.

### Not Pushed to GitHub

- `Simulation_Results/` — local simulation traces for comparison; not needed on the server.
- `data/` large files (Geolife 1.7 GB, AMIT 1.1 GB) — the deployed backend uses the HCM City road network (`hcmc_roads.graphml`, 103 MB via LFS) and Geolife cache (`_cached_segments.npz`, 4 MB). Full raw datasets can be linked as a separate download if the reviewer needs them.

## Dashboard

The live dashboard is at **`/tracking`** (labelled TRACK in the navigation bar) — the primary demo page. It shows the Leaflet map with trajectory layers, RMSE timeline chart, altitude chart (drone), and real-time position/error panels. See `frontend/src/pages/TrackingPage.jsx` and `docs/04-frontend.md` for details.
