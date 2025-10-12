import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { useAuthStore } from "../store/auth";

type Tab = "profile" | "security" | "providers";

type Provider = {
  id: number;
  name: string;
  provider: string;
  model: string;
  base_url: string | null;
  last_test_status?: string | null;
  last_tested_at?: string | null;
  has_api_key: boolean;
};

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const queryClient = useQueryClient();

  const providersQuery = useQuery({
    queryKey: ["providers"],
    enabled: activeTab === "providers",
    queryFn: async () => {
      const response = await apiClient.get<Provider[]>("/providers");
      return response.data;
    },
  });

  const [providerDraft, setProviderDraft] = useState({
    name: "",
    provider: "openai",
    model: "gpt-4",
    base_url: "https://api.openai.com/v1",
    api_key: "",
  });
  const [keyVisible, setKeyVisible] = useState(false);

  const createProvider = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<Provider>("/providers", {
        name: providerDraft.name,
        provider: providerDraft.provider,
        model: providerDraft.model,
        base_url: providerDraft.base_url,
        api_key: providerDraft.api_key,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["providers"] });
      setProviderDraft({ name: "", provider: "openai", model: "gpt-4", base_url: "https://api.openai.com/v1", api_key: "" });
      setKeyVisible(false);
    },
  });

  const testProvider = useMutation({
    mutationFn: async (providerId: number) => {
      const response = await apiClient.post<{ message: string }>(`/providers/${providerId}/test`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["providers"] });
    },
  });

  const handleCreateProvider = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createProvider.mutate();
  };

  const tabContent = useMemo(() => {
    if (activeTab === "profile") {
      return (
        <div className="panel" style={{ gap: "1rem" }}>
          <div className="panel-title">Profile</div>
          <div className="card" style={{ background: "rgba(30,41,59,0.6)" }}>
            <div><strong>Email:</strong> {String(user?.email ?? "")}</div>
            <div><strong>Username:</strong> {String(user?.username ?? "")}</div>
            <div><strong>Full name:</strong> {String(user?.full_name ?? "")}</div>
            <div><strong>Organization:</strong> {String(user?.organization ?? "")}</div>
          </div>
        </div>
      );
    }

    if (activeTab === "security") {
      return (
        <div className="panel" style={{ gap: "1rem" }}>
          <div className="panel-title">Security</div>
          <div className="card" style={{ background: "rgba(30,41,59,0.6)" }}>
            <p>Two-factor authentication and password reset flows will appear here.</p>
            <button type="button" className="button" style={{ alignSelf: "flex-start" }} onClick={() => clearSession()}>
              Sign out of all sessions
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="panel" style={{ gap: "1.5rem" }}>
        <div className="panel-header">
          <div className="panel-title">Provider integrations</div>
        </div>
        <form onSubmit={handleCreateProvider} className="card" style={{ gap: "1rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.125rem" }}>Add provider</h2>
          <label>
            Label
            <input
              required
              value={providerDraft.name}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, name: event.target.value }))}
              style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
            />
          </label>
          <label>
            Provider
            <input
              required
              value={providerDraft.provider}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, provider: event.target.value }))}
              style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
            />
          </label>
          <label>
            Model
            <input
              required
              value={providerDraft.model}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, model: event.target.value }))}
              style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
            />
          </label>
          <label>
            Base URL
            <input
              required
              value={providerDraft.base_url}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, base_url: event.target.value }))}
              style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
            />
          </label>
          <label>
            API key
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.5rem" }}>
              <input
                required
                type={keyVisible ? "text" : "password"}
                value={providerDraft.api_key}
                onChange={(event) => setProviderDraft((prev) => ({ ...prev, api_key: event.target.value }))}
                style={{ flex: 1, padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
              />
              <button
                type="button"
                className="button"
                onClick={() => setKeyVisible((prev) => !prev)}
                style={{ width: "fit-content", background: "rgba(148,163,184,0.2)", color: "#e2e8f0" }}
              >
                {keyVisible ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          {createProvider.error && <div style={{ color: "#f87171" }}>Failed to add provider.</div>}
          <button type="submit" className="button" disabled={createProvider.isLoading}>
            {createProvider.isLoading ? "Saving…" : "Save provider"}
          </button>
        </form>

        <div className="card" style={{ gap: "1rem", background: "rgba(30,41,59,0.6)" }}>
          <h2 style={{ margin: 0, fontSize: "1.125rem" }}>Configured providers</h2>
          {providersQuery.isLoading && <div>Loading…</div>}
          {providersQuery.error && <div style={{ color: "#f87171" }}>Unable to load providers.</div>}
          <div style={{ display: "grid", gap: "1rem" }}>
            {(providersQuery.data ?? []).map((provider) => (
              <div key={provider.id} className="panel" style={{ gap: "0.5rem", background: "rgba(15,23,42,0.5)" }}>
                <div style={{ fontWeight: 600 }}>{provider.name}</div>
                <div style={{ color: "#94a3b8" }}>{provider.provider} · {provider.model}</div>
                <div style={{ color: "#94a3b8" }}>Base URL: {provider.base_url ?? "-"}</div>
                <div style={{ color: provider.last_test_status === "success" ? "#34d399" : "#f87171" }}>
                  Status: {provider.last_test_status ?? "never tested"}
                </div>
                <div style={{ color: "#94a3b8" }}>Key stored: {provider.has_api_key ? "Yes" : "No"}</div>
                <button
                  type="button"
                  className="button"
                  style={{ width: "fit-content" }}
                  onClick={() => testProvider.mutate(provider.id)}
                  disabled={testProvider.isLoading}
                >
                  {testProvider.isLoading ? "Testing…" : "Test connectivity"}
                </button>
              </div>
            ))}
            {(providersQuery.data ?? []).length === 0 && <div style={{ color: "#94a3b8" }}>No providers added yet.</div>}
          </div>
        </div>
      </div>
    );
  }, [activeTab, user, providerDraft, providersQuery, createProvider, testProvider, clearSession, keyVisible]);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 style={{ margin: 0 }}>Settings</h1>
      </header>
      <main className="app-main">
        <div className="tab-layout">
          <nav className="tab-nav">
            <button type="button" className={`tab-button ${activeTab === "profile" ? "active" : ""}`} onClick={() => setActiveTab("profile")}>
              Profile
            </button>
            <button type="button" className={`tab-button ${activeTab === "security" ? "active" : ""}`} onClick={() => setActiveTab("security")}>
              Security
            </button>
            <button type="button" className={`tab-button ${activeTab === "providers" ? "active" : ""}`} onClick={() => setActiveTab("providers")}>
              Providers
            </button>
          </nav>
          <section>{tabContent}</section>
        </div>
      </main>
    </div>
  );
}
