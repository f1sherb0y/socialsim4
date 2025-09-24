// --- SimTree ---

export async function createTree(): Promise<{ id: number; root: number }> {
  const res = await fetch('/devui/simtree', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario: 'simple_chat' }),
  })
  return res.json()
}

export type Graph = { root: number; frontier: number[]; running?: number[]; nodes: { id: number; depth: number }[]; edges: { from: number; to: number; type: string }[] }

export async function getTreeGraph(id: number): Promise<Graph | null> {
  const res = await fetch(`/devui/simtree/${id}/graph`)
  if (res.status === 404) return null
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

// Sim-scoped (alias of node) endpoints: use treeId + simId and return full results
export async function getSimEvents(treeId: number, simId: number): Promise<any[]> {
  const res = await fetch(`/devui/simtree/${treeId}/sim/${simId}/events`)
  return res.json()
}

export async function getSimState(treeId: number, simId: number): Promise<{ turns: number; agents: { name: string; role?: string; plan_state: any; short_memory: { role: string; content: string }[] }[] }>{
  const res = await fetch(`/devui/simtree/${treeId}/sim/${simId}/state`)
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
