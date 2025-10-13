import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProvider as apiCreateProvider, listProviders, testProvider as apiTestProvider, type Provider } from "../api/providers";
import { useAuthStore } from "../store/auth";
import { useTranslation } from "react-i18next";

type Tab = "profile" | "security" | "providers";

// Provider type comes from ../api/providers

export function SettingsPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const queryClient = useQueryClient();

  const providersQuery = useQuery({
    queryKey: ["providers"],
    enabled: activeTab === "providers",
    queryFn: () => listProviders(),
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
    mutationFn: async () =>
      apiCreateProvider({
        name: providerDraft.name,
        provider: providerDraft.provider,
        model: providerDraft.model,
        base_url: providerDraft.base_url,
        api_key: providerDraft.api_key,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["providers"] });
      setProviderDraft({ name: "", provider: "openai", model: "gpt-4", base_url: "https://api.openai.com/v1", api_key: "" });
      setKeyVisible(false);
    },
  });

  const testProvider = useMutation({
    mutationFn: async (providerId: number) => apiTestProvider(providerId),
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
        <div className="panel" style={{ gap: "0.5rem" }}>
          <div className="panel-title">Profile</div>
          <div className="card">
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
        <div className="panel" style={{ gap: "0.5rem" }}>
          <div className="panel-title">Security</div>
          <div className="card">
            <p>Two-factor authentication and password reset flows will appear here.</p>
            <button type="button" className="button" style={{ alignSelf: "flex-start" }} onClick={() => clearSession()}>
              Sign out of all sessions
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="panel" style={{ gap: "0.75rem" }}>
        <div className="panel-header">
          <div className="panel-title">Provider integrations</div>
        </div>
        <form onSubmit={handleCreateProvider} className="card" style={{ gap: "0.5rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.125rem" }}>Add provider</h2>
          <label>
            Label
            <input className="input"
              required
              value={providerDraft.name}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, name: event.target.value }))}
            />
          </label>
          <label>
            Provider
            <input className="input"
              required
              value={providerDraft.provider}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, provider: event.target.value }))}
            />
          </label>
          <label>
            Model
            <input className="input"
              required
              value={providerDraft.model}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, model: event.target.value }))}
            />
          </label>
          <label>
            Base URL
            <input className="input"
              required
              value={providerDraft.base_url}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, base_url: event.target.value }))}
            />
          </label>
          <label>
            API key
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.5rem" }}>
              <input
                required
                type={keyVisible ? "text" : "password"}
                className="input"
                value={providerDraft.api_key}
                onChange={(event) => setProviderDraft((prev) => ({ ...prev, api_key: event.target.value }))}
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="button"
                onClick={() => setKeyVisible((prev) => !prev)}
                style={{ width: "fit-content" }}
              >
                {keyVisible ? "Hide" : "Show"}
              </button>
            </div>
          </label>
          {createProvider.error && <div style={{ color: "#f87171" }}>Failed to add provider.</div>}
          <button type="submit" className="button" disabled={createProvider.isPending}>
            {createProvider.isPending ? "Saving…" : "Save provider"}
          </button>
        </form>

        <div className="card" style={{ gap: "0.5rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.125rem" }}>Configured providers</h2>
          {providersQuery.isLoading && <div>Loading…</div>}
          {providersQuery.error && <div style={{ color: "#f87171" }}>Unable to load providers.</div>}
          <div style={{ display: "grid", gap: "1rem" }}>
            {(providersQuery.data ?? []).map((provider) => (
              <div key={provider.id} className="panel" style={{ gap: "0.5rem" }}>
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
                  style={{ width: "fit-content", padding: "0.4rem 0.7rem" }}
                  onClick={() => testProvider.mutate(provider.id)}
                  disabled={testProvider.isPending}
                >
                  {testProvider.isPending ? "Testing…" : "Test connectivity"}
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
        <h1 style={{ margin: 0 }}>{t('settings.title')}</h1>
      </header>
      <main className="app-main">
        <div className="tab-layout">
          <nav className="tab-nav">
            <button type="button" className={`tab-button ${activeTab === "profile" ? "active" : ""}`} onClick={() => setActiveTab("profile")}>
              {t('settings.tabs.profile')}
            </button>
            <button type="button" className={`tab-button ${activeTab === "security" ? "active" : ""}`} onClick={() => setActiveTab("security")}>
              {t('settings.tabs.security')}
            </button>
            <button type="button" className={`tab-button ${activeTab === "providers" ? "active" : ""}`} onClick={() => setActiveTab("providers")}>
              {t('settings.tabs.providers')}
            </button>
          </nav>
          <section>{tabContent}</section>
        </div>
      </main>
    </div>
  );
}
