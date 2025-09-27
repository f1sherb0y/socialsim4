SocialSim4

Overview
- Prototype-first social simulation engine with strict, minimal interfaces and no defensive coding. Scenes define the environment and actions; agents emit actions; the simulator orchestrates turns; an ordering policy decides who acts next. A DevUI supports visual SimTree exploration with live, incremental updates.

Highlights
- Strict serialization: serialize() / deserialize() with deep-copy semantics across core types.
- Ordering policies: sequential, cycled, random, controlled, LLM‑moderated.
- SimTree: branch timelines, advance leaves/chain/multi, delete subtrees.
- DevUI: FastAPI backend + Vite/React frontend; node‑level WebSocket streams deltas (events + agent_ctx_delta).

Environment Setup
- Requirements
  - Python 3.10+ (3.13 tested)
  - Node.js 18+ (or Bun), npm/pnpm supported
- Python deps (minimal set to run DevUI + basic scenes)
  
```bash
pip install fastapi uvicorn pydantic httpx openai google-generativeai ddgs trafilatura
```

- Note: the engine fails fast; keep versions recent. No extra wrappers required.

LLM Configuration (env vars)
- Dialect selection
  - LLM_DIALECT=mock | openai | gemini (default: mock)
- Common (used by all dialects)
  - LLM_MODEL: model name (e.g., gpt-4o-mini, gemini-2.5-flash)
  - LLM_API_KEY: API key for the selected provider
  - LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_TOP_P, LLM_FREQUENCY_PENALTY, LLM_PRESENCE_PENALTY
- OpenAI specific
  - LLM_BASE_URL: optional custom base URL
- Example (OpenAI)

```bash
export LLM_DIALECT=openai
export LLM_API_KEY=sk-...
export LLM_MODEL=gpt-4o-mini
# optional:
export LLM_BASE_URL=https://api.openai.com/v1
```

- Example (Gemini)

```bash
export LLM_DIALECT=gemini
export LLM_API_KEY=your_gemini_api_key
export LLM_MODEL=gemini-2.0-flash
```

Run DevUI
- Backend (FastAPI)

```bash
uvicorn socialsim4.devui.backend.app:app --host 0.0.0.0 --port 8090 --reload
```

- Frontend (Vite/React, dev server with proxy to 8090)

```bash
cd socialsim4/devui/frontend
npm i   # or pnpm i / bun install
npm run dev   # or pnpm dev / bun run dev
```
- Open UI
  - http://localhost:5174/
  - SimTree panel: create a tree (scenario: simple_chat | council | werewolf | landlord | village), watch graph updates, run leaves/chain/multi, branch broadcasts, and view details. WebSockets stream graph/run lifecycle and per-node deltas.

Notes
- Default LLM is a deterministic mock (no network). Set LLM_DIALECT and LLM_API_KEY/LLM_MODEL to use real providers.
- The DevUI frontend proxies requests with path prefix /devui to http://localhost:8090; keep the backend on 8090 during dev.
- Core adheres to strict, no‑defensive‑coding rules; invalid inputs raise immediately.

Folder Map
- socialsim4/         Python package (core engine, devui, scripts)
- socialsim4/core/    Core engine: simulator, scenes, agents, actions, ordering, SimTree
- socialsim4/devui/   DevUI backend (FastAPI) + frontend (Vite/React)
- socialsim4/scripts/ Utilities, example builders, static assets

Docs
- See AGENTS.md for philosophy, strict coding rules, ordering model, SimTree ops, and DevUI streaming.
