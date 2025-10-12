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
- WebSockets:
  - Tree‑level: /devui/simtree/{id}/events → graph/lifecycle updates (attached/run_start/run_finish/deleted)
  - Node‑level: /devui/simtree/{id}/sim/{node}/events → per‑node deltas: core events + agent_ctx_delta (appended memory)

IDs and API (prototype)
- Every SimTree has a unique `tree_id` assigned at creation (`POST /devui/simtree`).
- List existing trees: `GET /devui/simtree` → `[ { id, root } ]`.
- Within a tree, each simulation corresponds 1:1 to a SimTree node. The simulation id is the node id (`sim_id == node_id`).
- To fetch a simulation’s data, use tree-scoped endpoints that return full state (no deltas):
  - `GET /devui/simtree/{tree_id}/sim/{sim_id}/events` → full event list accumulated from root to that node.
  - `GET /devui/simtree/{tree_id}/sim/{sim_id}/state` → full agent state: `turns`, and for each agent `{ name, role, plan_state, short_memory }`.
  - Node-scoped aliases remain available: `/devui/simtree/{tree_id}/node/{node_id}/logs` and `/state`.
  - In the UI, `/sim/:treeId?sim=:simId` (or `?node=`) opens the Simulation view for a given tree + sim.

Run (dev)
1) Backend
   - Install deps: fastapi, uvicorn
   - Set environment variable: 
```bash
export GEMINI_API_KEY=[your_gemini_api_key]
export LLM_DIALECT=gemini
```
   - Run: 
```bash
uvicorn socialsim4.devui.backend.app:app --host 0.0.0.0 --port 8090 --reload
```

2) Frontend
   - cd socialsim4/devui/frontend
   - pnpm i (or npm i / bun install)
   - pnpm dev (or npm run dev / bun run dev)

Notes
- Prototype only; no persistence; multiple scenarios can be added later.
- The API is intentionally strict; invalid payloads will raise.
