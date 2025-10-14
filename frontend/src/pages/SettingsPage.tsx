import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProvider as apiCreateProvider, listProviders, testProvider as apiTestProvider, updateProvider, type Provider } from "../api/providers";
import { listSearchProviders, createSearchProvider, updateSearchProvider, type SearchProvider } from "../api/searchProviders";
import { useAuthStore } from "../store/auth";
import { useTranslation } from "react-i18next";
import { TitleCard } from "../components/TitleCard";
import { AppSelect } from "../components/AppSelect";

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

  const searchProvidersQuery = useQuery({
    queryKey: ["searchProviders"],
    enabled: activeTab === "providers",
    queryFn: () => listSearchProviders(),
  });

  const searchProvider = useMemo(() => {
    const items = searchProvidersQuery.data || [];
    return items[0] || null;
  }, [searchProvidersQuery.data]);

  const [providerDraft, setProviderDraft] = useState({
    name: "",
    provider: "openai",
    model: "gpt-4",
    base_url: "https://api.openai.com/v1",
    api_key: "",
  });
  const [keyVisible, setKeyVisible] = useState(false);

  const [searchDraft, setSearchDraft] = useState({
    provider: "ddg",
    base_url: "",
    api_key: "",
    config: { region: "", safesearch: "moderate" } as Record<string, any>,
  });

  useEffect(() => {
    if (!searchProvider) return;
    setSearchDraft({
      provider: searchProvider.provider || "ddg",
      base_url: String(searchProvider.base_url || ""),
      api_key: "",
      config: (searchProvider as any).config || {},
    });
  }, [searchProvider]);

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

  const upsertSearch = useMutation({
    mutationFn: async () => {
      if (searchProvider) {
        return updateSearchProvider(searchProvider.id, {
          provider: searchDraft.provider,
          base_url: searchDraft.base_url || null,
          api_key: searchDraft.api_key || null,
          config: searchDraft.config,
        });
      }
      return createSearchProvider({
        provider: searchDraft.provider,
        base_url: searchDraft.base_url || "",
        api_key: searchDraft.api_key || "",
        config: searchDraft.config,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["searchProviders"] });
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
          <div className="panel-title">{t('settings.tabs.profile')}</div>
          <div className="card">
            <div><strong>{t('settings.profile.email')}:</strong> {String(user?.email ?? "")}</div>
            <div><strong>{t('settings.profile.username')}:</strong> {String(user?.username ?? "")}</div>
            <div><strong>{t('settings.profile.fullName')}:</strong> {String(user?.full_name ?? "")}</div>
            <div><strong>{t('settings.profile.organization')}:</strong> {String(user?.organization ?? "")}</div>
          </div>
        </div>
      );
    }

    if (activeTab === "security") {
      return (
        <div className="panel" style={{ gap: "0.5rem" }}>
          <div className="panel-title">{t('settings.tabs.security')}</div>
          <div className="card">
            <p>{t('settings.security.placeholder')}</p>
            <button type="button" className="button button-danger" style={{ alignSelf: "flex-start" }} onClick={() => clearSession()}>
              {t('settings.security.signoutAll')}
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="panel" style={{ gap: "0.75rem" }}>
        <div className="panel-header">
          <div className="panel-title">{t('settings.providers.title')}</div>
        </div>

        <div className="card" style={{ gap: "0.5rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.125rem" }}>Search Provider</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <label>
              Provider
              <AppSelect
                value={searchDraft.provider}
                options={[
                  { value: "ddg", label: "DuckDuckGo" },
                  { value: "serpapi", label: "SerpAPI" },
                  { value: "serper", label: "Serper" },
                  { value: "tavily", label: "Tavily" },
                  { value: "mock", label: "Mock" },
                ]}
                onChange={(val) => setSearchDraft((p) => ({ ...p, provider: val }))}
              />
            </label>
            {(searchDraft.provider === "serpapi" || searchDraft.provider === "serper" || searchDraft.provider === "tavily") && (
              <>
                <label>
                  Base URL
                  <input className="input" value={searchDraft.base_url} onChange={(e) => setSearchDraft((p) => ({ ...p, base_url: e.target.value }))} />
                </label>
                <label>
                  API Key
                  <input className="input" value={searchDraft.api_key} onChange={(e) => setSearchDraft((p) => ({ ...p, api_key: e.target.value }))} />
                </label>
              </>
            )}
            {searchDraft.provider === "ddg" && (
              <>
                <label>
                  Region
                  <input className="input" value={String((searchDraft.config as any).region || "")} onChange={(e) => setSearchDraft((p) => ({ ...p, config: { ...(p.config || {}), region: e.target.value } }))} />
                </label>
                <label>
                  SafeSearch
                  <input className="input" value={String((searchDraft.config as any).safesearch || "moderate")} onChange={(e) => setSearchDraft((p) => ({ ...p, config: { ...(p.config || {}), safesearch: e.target.value } }))} />
                </label>
              </>
            )}
            {searchDraft.provider === "tavily" && (
              <>
                <label>
                  Search Depth
                  <AppSelect
                    value={String((searchDraft.config as any).search_depth || "basic")}
                    options={[
                      { value: "basic", label: "basic" },
                      { value: "advanced", label: "advanced" },
                    ]}
                    onChange={(val) => setSearchDraft((p) => ({ ...p, config: { ...(p.config || {}), search_depth: val } }))}
                  />
                </label>
                <label>
                  Include Answer
                  <input
                    type="checkbox"
                    checked={Boolean((searchDraft.config as any).include_answer || false)}
                    onChange={(e) => setSearchDraft((p) => ({ ...p, config: { ...(p.config || {}), include_answer: e.target.checked } }))}
                  />
                </label>
                <label>
                  Topic
                  <input
                    className="input"
                    value={String((searchDraft.config as any).topic || "")}
                    onChange={(e) => setSearchDraft((p) => ({ ...p, config: { ...(p.config || {}), topic: e.target.value } }))}
                  />
                </label>
                <label>
                  Days (time range)
                  <input
                    className="input"
                    type="number"
                    min={1}
                    value={Number((searchDraft.config as any).days || 7)}
                    onChange={(e) => setSearchDraft((p) => ({ ...p, config: { ...(p.config || {}), days: Number(e.target.value || 0) } }))}
                  />
                </label>
                <label>
                  Include Domains (comma-separated)
                  <input
                    className="input"
                    value={String((searchDraft.config as any).include_domains || "")}
                    onChange={(e) => setSearchDraft((p) => ({ ...p, config: { ...(p.config || {}), include_domains: e.target.value } }))}
                  />
                </label>
                <label>
                  Exclude Domains (comma-separated)
                  <input
                    className="input"
                    value={String((searchDraft.config as any).exclude_domains || "")}
                    onChange={(e) => setSearchDraft((p) => ({ ...p, config: { ...(p.config || {}), exclude_domains: e.target.value } }))}
                  />
                </label>
              </>
            )}
            {searchDraft.provider === "mock" && (
              <>
                <div />
                <div />
              </>
            )}
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <button type="button" className="button" onClick={() => upsertSearch.mutate()} disabled={upsertSearch.isPending}>
              Save Search Provider
            </button>
            {searchProvider && (
              <div style={{ color: "#94a3b8", lineHeight: 1 }}>
                Active: {searchProvider.provider}
              </div>
            )}
          </div>
        </div>

        <form onSubmit={handleCreateProvider} className="card" style={{ gap: "0.5rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.125rem" }}>{t('settings.providers.add')}</h2>
          <label>
            {t('settings.providers.fields.label')}
            <input className="input"
              required
              value={providerDraft.name}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, name: event.target.value }))}
            />
          </label>
          <label>
            {t('settings.providers.fields.provider')}
            <input className="input"
              required
              value={providerDraft.provider}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, provider: event.target.value }))}
            />
          </label>
          <label>
            {t('settings.providers.fields.model')}
            <input className="input"
              required
              value={providerDraft.model}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, model: event.target.value }))}
            />
          </label>
          <label>
            {t('settings.providers.fields.baseUrl')}
            <input className="input"
              required
              value={providerDraft.base_url}
              onChange={(event) => setProviderDraft((prev) => ({ ...prev, base_url: event.target.value }))}
            />
          </label>
          <label>
            {t('settings.providers.fields.apiKey')}
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
                {keyVisible ? t('common.hide') : t('common.show')}
              </button>
            </div>
          </label>
          {createProvider.error && <div style={{ color: "#f87171" }}>Failed to add provider.</div>}
          <button type="submit" className="button" disabled={createProvider.isPending}>
            {createProvider.isPending ? t('settings.providers.save') + '…' : t('settings.providers.save')}
          </button>
        </form>

        <div className="card" style={{ gap: "0.5rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.125rem" }}>{t('settings.providers.title')}</h2>
          {providersQuery.isLoading && <div>{t('settings.providers.loading')}</div>}
          {providersQuery.error && <div style={{ color: "#f87171" }}>{t('settings.providers.error')}</div>}
          <div style={{ display: "grid", gap: "1rem" }}>
            {(providersQuery.data ?? []).map((provider) => (
              <div key={provider.id} className="panel" style={{ gap: "0.5rem" }}>
                <div style={{ fontWeight: 600 }}>{provider.name}</div>
                <div style={{ color: "#94a3b8" }}>{provider.provider} · {provider.model}</div>
                <div style={{ color: "#94a3b8" }}>Base URL: {provider.base_url ?? "-"}</div>
                <div style={{ color: provider.last_test_status === "success" ? "#34d399" : "#f87171" }}>
                  {t('dashboard.status')}: {provider.last_test_status ?? t('settings.providers.neverTested')}
                </div>
                <div style={{ color: "#94a3b8" }}>{t('settings.providers.hasKey')}: {provider.has_api_key ? t('common.yes') : t('common.no')}</div>
                {provider.model !== 'search' && provider.name !== 'search' && (
                  <button
                    type="button"
                    className="button"
                    style={{ width: "fit-content", padding: "0.4rem 0.7rem" }}
                    onClick={() => testProvider.mutate(provider.id)}
                    disabled={testProvider.isPending}
                  >
                    {testProvider.isPending ? t('settings.providers.test') + '…' : t('settings.providers.test')}
                  </button>
                )}
              </div>
            ))}
            {(providersQuery.data ?? []).length === 0 && <div style={{ color: "#94a3b8" }}>{t('settings.providers.none')}</div>}
          </div>
        </div>
      </div>
    );
  }, [activeTab, user, providerDraft, providersQuery, createProvider, testProvider, clearSession, keyVisible]);

  return (
    <div style={{ height: "100%", overflow: "auto" }}>
      <TitleCard title={t('settings.title')} />
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
    </div>
  );
}

// (Radix-based AppSelect replaces local FancySelect)
