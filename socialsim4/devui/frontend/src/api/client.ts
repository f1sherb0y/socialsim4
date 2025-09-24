export type Offsets = { events: number; mem: Record<string, { count: number; last_len: number }> }

export async function createSim(): Promise<{ id: number; names: string[] }> {
  const res = await fetch('/devui/sim', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario: 'simple_chat' }),
  })
  return res.json()
}

export async function runSim(id: number, turns: number): Promise<{ ok: boolean }> {
  const res = await fetch(`/devui/sim/${id}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ turns }),
  })
  return res.json()
}

export async function getSnapshot(id: number, offsets: Offsets): Promise<{ snapshot: any; offsets: Offsets }> {
  const res = await fetch(`/devui/sim/${id}/snapshot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ offsets }),
  })
  return res.json()
}

// --- SimTree ---

export async function createTree(): Promise<{ id: number; root: number }> {
  const res = await fetch('/devui/simtree', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario: 'simple_chat' }),
  })
  return res.json()
}

export async function getTreeGraph(id: number): Promise<{ root: number; frontier: number[]; nodes: { id: number; depth: number }[]; edges: { from: number; to: number; type: string }[] }> {
  const res = await fetch(`/devui/simtree/${id}/graph`)
  return res.json()
}

export async function treeAdvance(id: number, parent: number, turns: number): Promise<{ child: number }> {
  const res = await fetch(`/devui/simtree/${id}/advance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parent, turns }),
  })
  return res.json()
}

export async function treeAdvanceFrontier(id: number, turns: number, onlyMaxDepth = false): Promise<{ children: number[] }> {
  const res = await fetch(`/devui/simtree/${id}/advance_frontier`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ turns, only_max_depth: onlyMaxDepth }),
  })
  return res.json()
}

export async function treeBranchPublic(id: number, parent: number, text: string): Promise<{ child: number }> {
  const res = await fetch(`/devui/simtree/${id}/branch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parent, ops: [{ op: 'public_broadcast', text }] }),
  })
  return res.json()
}

export async function treeDeleteSubtree(id: number, nodeId: number): Promise<{ ok: boolean }> {
  const res = await fetch(`/devui/simtree/${id}/node/${nodeId}`, { method: 'DELETE' })
  return res.json()
}

export async function spawnSimFromTree(treeId: number, node: number): Promise<{ sim_id: number; names: string[] }> {
  const res = await fetch(`/devui/simtree/${treeId}/spawn_sim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ node }),
  })
  return res.json()
}

export async function treeAdvanceMulti(id: number, parent: number, turns: number, count: number): Promise<{ children: number[] }> {
  const res = await fetch(`/devui/simtree/${id}/advance_multi`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parent, turns, count }),
  })
  return res.json()
}

export async function treeAdvanceChain(id: number, parent: number, turns: number): Promise<{ child: number }> {
  const res = await fetch(`/devui/simtree/${id}/advance_chain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parent, turns }),
  })
  return res.json()
}
