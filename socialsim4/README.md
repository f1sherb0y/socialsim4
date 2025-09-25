SocialSim4 Package

Contents
- core/      Simulator, scenes, agents, actions, ordering, SimTree
- devui/     Prototype DevUI: backend (FastAPI) + frontend (Vite/React)
- scripts/   Example builders and helpers

Install (local)
- The package is used in-place; no wheel required. Ensure Python 3.10+ (3.13 tested) and run the DevUI backend via uvicorn:
  - uvicorn socialsim4.devui.backend.app:app --host 0.0.0.0 --port 8090 --reload

Key Concepts
- serialize()/deserialize(): Deep‑copy snapshots for Simulator, Scene, Agent, Ordering.
- Ordering: sequential | cycled | random | controlled | llm_moderated.
- SimTree: advance, branch, advance_frontier, advance_multi, advance_chain, delete_subtree.
- Streaming: node‑level WS pushes per‑node deltas (events + agent_ctx_delta).

See also
- ../AGENTS.md for strict coding rules and architectural notes.

