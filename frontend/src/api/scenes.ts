import { apiClient } from "./client";

export type SceneOption = {
  type: string;
  name: string;
  config_schema: Record<string, unknown>;
};

export async function listScenes(): Promise<SceneOption[]> {
  const { data } = await apiClient.get<SceneOption[]>("/scenes");
  return data;
}

