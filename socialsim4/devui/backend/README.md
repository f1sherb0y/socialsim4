DevUI Backend (FastAPI)

Entry
- uvicorn socialsim4.devui.backend.app:app --host 0.0.0.0 --port 8090 --reload

Key Routes (prototype)
- POST /devui/simtree                      create a SimTree: scenario ∈ {simple_chat|council|werewolf|landlord|village}
- GET  /devui/simtree                      list existing trees
- GET  /devui/simtree/{id}/graph           attached nodes + edges + running
- GET  /devui/simtree/{id}/summaries       compact summaries
- POST /devui/simtree/{id}/advance_frontier  body: {turns, only_max_depth}
- POST /devui/simtree/{id}/advance_multi     body: {parent, turns, count}
- POST /devui/simtree/{id}/advance_chain     body: {parent, turns} (stepwise, each step = 1 turn)
- POST /devui/simtree/{id}/branch            body: {parent, ops: [...]} (strict ops only)
- DELETE /devui/simtree/{id}/node/{node}     delete subtree
- WS   /devui/simtree/{id}/events            tree‑level lifecycle stream
- WS   /devui/simtree/{id}/sim/{node}/events node‑level delta stream

Notes
- In‑memory only; strict models; fail fast.
- Node deltas include agent_ctx_delta for appended agent memory.

