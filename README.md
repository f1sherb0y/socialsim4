SocialSim4

Overview
- Prototype-first social simulation engine with strict, minimal interfaces and no defensive coding. Scenes define the environment and actions; agents emit actions; the simulator orchestrates turns; an ordering policy decides who acts next. A DevUI supports visual SimTree exploration with live, incremental updates.

Highlights
- Strict serialization: serialize() / deserialize() with deep-copy semantics across core types.
- Ordering policies: sequential, cycled, random, controlled, LLM‑moderated.
- SimTree: branch timelines, advance leaves/chain/multi, delete subtrees.
- DevUI: FastAPI backend + Vite/React frontend; node‑level WebSocket streams deltas (events + agent_ctx_delta).

Quick Start
- Backend (DevUI API)
  - uvicorn socialsim4.devui.backend.app:app --host 0.0.0.0 --port 8090 --reload
- Frontend (DevUI)
  - cd socialsim4/devui/frontend
  - npm install (or bun install)
  - npm run dev

Folder Map
- socialsim4/         Python package (core engine, devui, scripts)
- socialsim4/core/    Core engine: simulator, scenes, agents, actions, ordering, SimTree
- socialsim4/devui/   DevUI backend (FastAPI) + frontend (Vite/React)
- socialsim4/scripts/ Utilities, example builders, static assets

Docs
- See AGENTS.md for philosophy, strict coding rules, ordering model, SimTree ops, and DevUI streaming.

