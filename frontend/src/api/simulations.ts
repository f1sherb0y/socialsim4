import { apiClient } from "./client";

export type Simulation = {
  id: string;
  name: string;
  status: string;
  scene_type: string;
  latest_state?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

export type Snapshot = {
  id: number;
  label: string;
  turns: number;
  state: Record<string, unknown>;
  created_at: string;
};

export async function listSimulations(): Promise<Simulation[]> {
  const { data } = await apiClient.get<Simulation[]>("/simulations");
  return data;
}

export async function getSimulation(id: string): Promise<Simulation> {
  const { data } = await apiClient.get<Simulation>(`/simulations/${id}`);
  return data;
}

export async function createSimulation(payload: {
  scene_type: string;
  scene_config: Record<string, unknown>;
  agent_config: Record<string, unknown>;
  name?: string;
}): Promise<Simulation> {
  const { data } = await apiClient.post<Simulation>("/simulations", payload);
  return data;
}

export async function deleteSimulation(id: string): Promise<void> {
  await apiClient.delete(`/simulations/${id}`);
}

export async function copySimulation(id: string): Promise<Simulation> {
  const { data } = await apiClient.post<Simulation>(`/simulations/${id}/copy`);
  return data;
}

export async function startSimulation(id: string): Promise<void> {
  await apiClient.post(`/simulations/${id}/start`);
}

export async function resumeSimulation(id: string, snapshotId?: number): Promise<void> {
  const params = snapshotId != null ? { snapshot_id: snapshotId } : undefined;
  await apiClient.post(`/simulations/${id}/resume`, undefined, { params });
}

export async function saveSnapshot(id: string, label?: string): Promise<Snapshot> {
  const { data } = await apiClient.post<Snapshot>(`/simulations/${id}/save`, label ? { label } : {});
  return data;
}

export async function listSnapshots(id: string): Promise<Snapshot[]> {
  const { data } = await apiClient.get<Snapshot[]>(`/simulations/${id}/snapshots`);
  return data;
}

