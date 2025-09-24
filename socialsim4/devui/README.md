SocialSim4 DevUI (Prototype)

A minimal developer UI for SocialSim4 using a modern B/S stack.

Goals (prototype stage)
- Replace Streamlit prototypes with a web app.
- Two panels to start:
  - Simulation: per-event snapshots, run turns, agent view.
  - SimTree: visualize branches; advance/branch/delete.

Architecture
- Backend: FastAPI (Python), in-memory stores, strict inputs, fail fast.
- Frontend: Vite + React + TypeScript.

Run (dev)
1) Backend
   - Install deps: fastapi, uvicorn
   - Run: uvicorn socialsim4.devui.backend.app:app --host 0.0.0.0 --port 8090 --reload

2) Frontend
   - cd socialsim4/devui/frontend
   - pnpm i (or npm i / bun install)
   - pnpm dev (or npm run dev / bun run dev)

Notes
- Prototype only; no persistence; multiple scenarios can be added later.
- The API is intentionally strict; invalid payloads will raise.

