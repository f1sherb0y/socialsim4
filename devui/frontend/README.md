DevUI Frontend (Vite/React)

Dev
- cd socialsim4/devui/frontend
- npm install (or bun install)
- npm run dev

Pages
- /studio        Combined view: Graph + Ops | Events | Agents
- /simtree       SimTree graph + ops
- /sim/:treeId?node=:nodeId  Simulation viewer for a specific node

Conventions
- Uses node‑level WS for live deltas (events + agent_ctx_delta).
- Strict inputs; errors surface in console.

