import { apiClient } from "./client";

export type Provider = {
  id: number;
  name: string;
  provider: string;
  model: string;
  base_url: string | null;
  last_test_status?: string | null;
  last_tested_at?: string | null;
  has_api_key: boolean;
};

export async function listProviders(): Promise<Provider[]> {
  const { data } = await apiClient.get<Provider[]>("/providers");
  return data;
}

export async function createProvider(payload: {
  name: string;
  provider: string;
  model: string;
  base_url?: string | null;
  api_key?: string | null;
}): Promise<Provider> {
  const { data } = await apiClient.post<Provider>("/providers", payload);
  return data;
}

export async function testProvider(providerId: number): Promise<{ message: string }> {
  const { data } = await apiClient.post<{ message: string }>(`/providers/${providerId}/test`);
  return data;
}

