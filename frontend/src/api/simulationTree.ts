import { apiClient } from "./client";

export type GraphNode = { id: number; depth: number };
export type GraphEdge = { from: number; to: number; type: string; ops?: unknown[] };

export type Graph = {
  root: number | null;
  frontier: number[];
  running?: number[];
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export async function getTreeGraph(id: string): Promise<Graph | null> {
  try {
    const { data } = await apiClient.get<Graph>(`/simulations/${id}/tree/graph`);
    return data;
  } catch (error: any) {
    if (error?.response?.status === 404) return null;
    throw error;
  }
}

export async function treeAdvanceFrontier(
  id: string,
  turns: number,
  onlyMaxDepth = false,
): Promise<{ children: number[] }> {
  const { data } = await apiClient.post<{ children: number[] }>(`/simulations/${id}/tree/advance_frontier`, {
    turns,
    only_max_depth: onlyMaxDepth,
  });
  return data;
}

export async function treeAdvanceMulti(
  id: string,
  parent: number,
  turns: number,
  count: number,
): Promise<{ children: number[] }> {
  const { data } = await apiClient.post<{ children: number[] }>(`/simulations/${id}/tree/advance_multi`, {
    parent,
    turns,
    count,
  });
  return data;
}

export async function treeAdvanceChain(
  id: string,
  parent: number,
  turns: number,
): Promise<{ child: number }> {
  const { data } = await apiClient.post<{ child: number }>(`/simulations/${id}/tree/advance_chain`, {
    parent,
    turns,
  });
  return data;
}

export async function treeBranchPublic(id: string, parent: number, text: string): Promise<{ child: number }> {
  const { data } = await apiClient.post<{ child: number }>(`/simulations/${id}/tree/branch`, {
    parent,
    ops: [{ op: "public_broadcast", text }],
  });
  return data;
}

export async function treeDeleteSubtree(id: string, nodeId: number): Promise<{ ok: boolean }> {
  const { data } = await apiClient.delete<{ ok: boolean }>(`/simulations/${id}/tree/node/${nodeId}`);
  return data;
}

export async function getSimEvents(id: string, node: number): Promise<any[]> {
  const { data } = await apiClient.get<any[]>(`/simulations/${id}/tree/sim/${node}/events`);
  return data;
}

export type AgentMemory = { role: string; content: string };

export type AgentInfo = {
  name: string;
  role?: string;
  plan_state: unknown;
  short_memory: AgentMemory[];
};

export type SimState = {
  turns: number;
  agents: AgentInfo[];
};

export async function getSimState(id: string, node: number): Promise<SimState> {
  const { data } = await apiClient.get<SimState>(`/simulations/${id}/tree/sim/${node}/state`);
  return data;
}
