import { API_BASE_URL, apiClient } from "./client";

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
    const { data } = await apiClient.get<Graph>(`simulations/${id}/tree/graph`);
    return data;
  } catch (error: any) {
    if (error?.response?.status === 404) return null;
    throw error;
  }
}

export type SimEvent = { type: string; data?: Record<string, unknown> | null; node?: number };

export function buildWsUrl(path: string, token?: string): string {
  const base = (API_BASE_URL || "http://localhost:8000/api").replace(/\/$/, "");
  const url = new URL(base);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  const wsBase = url.toString();
  const full = new URL(`${wsBase}${path}`);
  if (token) full.searchParams.set("token", token);
  return full.toString();
}

export function connectTreeEvents(
  simulationId: string,
  accessToken: string | null | undefined,
  onMessage: (event: SimEvent) => void,
): WebSocket {
  const ws = new WebSocket(buildWsUrl(`/simulations/${simulationId}/tree/events`, accessToken || undefined));
  ws.onopen = () => ws.send("ready");
  ws.onmessage = (ev) => onMessage(JSON.parse(ev.data));
  return ws;
}

export function connectNodeEvents(
  simulationId: string,
  nodeId: number,
  accessToken: string | null | undefined,
  onMessage: (event: SimEvent) => void,
): WebSocket {
  const ws = new WebSocket(buildWsUrl(`/simulations/${simulationId}/tree/${nodeId}/events`, accessToken || undefined));
  ws.onopen = () => ws.send("ready");
  ws.onmessage = (ev) => onMessage(JSON.parse(ev.data));
  return ws;
}

export async function treeAdvanceFrontier(
  id: string,
  turns: number,
  onlyMaxDepth = false,
): Promise<{ children: number[] }> {
  const { data } = await apiClient.post<{ children: number[] }>(`simulations/${id}/tree/advance_frontier`, {
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
  const { data } = await apiClient.post<{ children: number[] }>(`simulations/${id}/tree/advance_multi`, {
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
  const { data } = await apiClient.post<{ child: number }>(`simulations/${id}/tree/advance_chain`, {
    parent,
    turns,
  });
  return data;
}

export async function treeBranchPublic(id: string, parent: number, text: string): Promise<{ child: number }> {
  const { data } = await apiClient.post<{ child: number }>(`simulations/${id}/tree/branch`, {
    parent,
    ops: [{ op: "public_broadcast", text }],
  });
  return data;
}

export async function treeDeleteSubtree(id: string, nodeId: number): Promise<{ ok: boolean }> {
  const { data } = await apiClient.delete<{ ok: boolean }>(`simulations/${id}/tree/node/${nodeId}`);
  return data;
}

export async function getSimEvents(id: string, node: number): Promise<any[]> {
  const { data } = await apiClient.get<any[]>(`simulations/${id}/tree/sim/${node}/events`);
  return data;
}

export type AgentMemory = { role: string; content: string };

export type PlanGoal = { id: string; desc: string; priority: string; status: string };
export type PlanMilestone = { id: string; desc: string; status: string };
export type PlanState = {
  goals: PlanGoal[];
  milestones: PlanMilestone[];
  strategy: string;
  notes: string;
};

export type AgentInfo = {
  name: string;
  role?: string;
  emotion?: string;
  plan_state: PlanState;
  short_memory: AgentMemory[];
};

export type SimState = {
  turns: number;
  agents: AgentInfo[];
};

export async function getSimState(id: string, node: number): Promise<SimState> {
  const { data } = await apiClient.get<SimState>(`simulations/${id}/tree/sim/${node}/state`);
  return data;
}
