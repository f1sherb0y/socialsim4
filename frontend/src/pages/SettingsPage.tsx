import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createProvider as apiCreateProvider, listProviders, testProvider as apiTestProvider, updateProvider, deleteProvider as apiDeleteProvider, activateProvider as apiActivateProvider, type Provider } from "../api/providers";
import { listSearchProviders, createSearchProvider, updateSearchProvider, type SearchProvider } from "../api/searchProviders";
import { useAuthStore } from "../store/auth";
import { useTranslation } from "react-i18next";
import { TitleCard } from "../components/TitleCard";
import { AppSelect } from "../components/AppSelect";
import { Icon } from "../components/Icon";

type Tab = "profile" | "security" | "providers_llm" | "providers_search";

// Provider type comes from ../api/providers

export function SettingsPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const queryClient = useQueryClient();
  const [testHints, setTestHints] = useState<Record<number, { ok: boolean; msg: string }>>({});
  const [testingId, setTestingId] = useState<number | null>(null);


  const providersQuery = useQuery({
    queryKey: ["providers"],
    enabled: activeTab === "providers_llm",
    queryFn: () => listProviders(),
  });

  const searchProvidersQuery = useQuery({
    queryKey: ["searchProviders"],
    enabled: activeTab === "providers_search",
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
    onMutate: (providerId: number) => {
      setTestingId(providerId);
    },
    onSuccess: (_data, providerId) => {
      setTestHints((prev) => ({ ...prev, [providerId]: { ok: true, msg: t('settings.providers.testOk') || 'OK' } }));
      setTimeout(() => {
        setTestHints((prev) => {
          const copy = { ...prev } as Record<number, { ok: boolean; msg: string }>;
          delete copy[providerId];
          return copy;
        });
      }, 3000);
      queryClient.invalidateQueries({ queryKey: ["providers"] });
    },
    onError: (_err, providerId) => {
      setTestHints((prev) => ({ ...prev, [providerId]: { ok: false, msg: t('settings.providers.testFail') || 'Failed' } }));
      setTimeout(() => {
        setTestHints((prev) => {
          const copy = { ...prev } as Record<number, { ok: boolean; msg: string }>;
          delete copy[providerId];
          return copy;
        });
      }, 3000);
    },
    onSettled: () => {
      setTestingId(null);
    },
  });

  const activateProvider = useMutation({
    mutationFn: async (providerId: number) => apiActivateProvider(providerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["providers"] });
    },
  });

  const deleteProvider = useMutation({
    mutationFn: async (providerId: number) => apiDeleteProvider(providerId),
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
        <div className="panel-header" style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <div className="panel-title">{t('settings.providers.title')}</div>
          {activeTab === 'providers_llm' && (
            (() => {
              const activeProv = (providersQuery.data || []).find((p) => Boolean((p.config as any)?.active));
              const name = activeProv ? activeProv.name : '-';
              return (
                <div style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>
                  {t('settings.providers.current', { name })}
                </div>
              );
            })()
          )}
        </div>

        {/* LLM Providers: list above, add form below */}
        {activeTab === 'providers_llm' && (
          <>
            {/* List (no outer card) */}
            <div className="card" style={{ display: 'grid', gap: 0, padding: '0.2rem 0.6rem' }}>
              {providersQuery.isLoading && <div>{t('settings.providers.loading')}</div>}
              {providersQuery.error && <div style={{ color: "#f87171" }}>{t('settings.providers.error')}</div>}
              {(providersQuery.data ?? []).map((provider, idx) => {
                const active = Boolean((provider.config as any)?.active);
                return (
                  <div key={provider.id} style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', padding: '0.5rem 0' }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis' }}>{provider.name}</div>
                      <div style={{ color: 'var(--muted)', fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {provider.provider} · {provider.model} · {provider.base_url || '-'}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                      {testHints[provider.id] && (
                        <span style={{ fontSize: '0.8rem', color: testHints[provider.id].ok ? '#22c55e' : '#f87171' }}>
                          {testHints[provider.id].ok ? '✓' : '✕'} {testHints[provider.id].msg}
                        </span>
                      )}
                      <button
                        type="button"
                        className="icon-button square"
                        title={t('settings.providers.test')}
                        aria-label={t('settings.providers.test')}
                        onClick={() => testProvider.mutate(provider.id)}
                        disabled={testingId !== null}
                        style={{ borderColor: 'var(--border)', color: '#2563eb' }}
                      >
                        {testingId === provider.id ? <span className="spinner" aria-hidden /> : <Icon name="test" />}
                      </button>
                      <button
                        type="button"
                        className="icon-button square"
                        title={active ? (t('settings.providers.activeTag') || 'Active') : (t('settings.providers.makeActive') || 'Use')}
                        aria-label={active ? (t('settings.providers.activeTag') || 'Active') : (t('settings.providers.makeActive') || 'Use')}
                        onClick={() => !active && activateProvider.mutate(provider.id)}
                        disabled={active || activateProvider.isPending}
                        style={{ borderColor: 'var(--border)', color: '#f59e0b' }}
                      >
                        {active ? <Icon name="star-solid" /> : <Icon name="star" />}
                      </button>
                      <button
                        type="button"
                        className="icon-button square"
                        title={t('saved.delete')}
                        aria-label={t('saved.delete')}
                        onClick={() => {
                          if (active) {
                            const msg = t('settings.providers.deleteActiveConfirm') || 'This provider is active. Delete anyway?';
                            if (!window.confirm(msg)) return;
                          }
                          deleteProvider.mutate(provider.id);
                        }}
                        disabled={deleteProvider.isPending}
                        style={{ borderColor: 'var(--border)', color: '#ef4444' }}
                      >
                        <Icon name="delete" />
                      </button>
                    </div>
                    {idx < (providersQuery.data?.length || 0) - 1 && <div style={{ gridColumn: '1 / -1', borderTop: '1px solid var(--border)', margin: '0.4rem 0 0 0', opacity: 0.8 }} />}
                  </div>
                );
              })}
              {(providersQuery.data ?? []).length === 0 && <div style={{ color: "#94a3b8" }}>{t('settings.providers.none')}</div>}
            </div>

            {/* Add form */}
            <form onSubmit={handleCreateProvider} className="card" style={{ gap: "0.3rem", padding: '0.5rem 0.6rem', marginTop: '0.6rem', fontSize: '0.95rem' }}>
              <h2 style={{ margin: 0, fontSize: "0.95rem" }}>{t('settings.providers.add')}</h2>
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
                <AppSelect
                  value={providerDraft.provider}
                  options={[
                    { value: 'openai', label: 'OpenAI-compatible' },
                    { value: 'gemini', label: 'Gemini' },
                  ]}
                  onChange={(val) => setProviderDraft((prev) => ({ ...prev, provider: val, base_url: val === 'openai' ? 'https://api.openai.com/v1' : '' }))}
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
                    className="icon-button square"
                    title={keyVisible ? (t('common.hide') || 'Hide') : (t('common.show') || 'Show')}
                    aria-label={keyVisible ? (t('common.hide') || 'Hide') : (t('common.show') || 'Show')}
                    onClick={() => setKeyVisible((prev) => !prev)}
                  >
                    {keyVisible ? (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <path d="M17.94 17.94L6.06 6.06"/>
                        <path d="M10.58 10.58a3 3 0 004.24 4.24"/>
                        <path d="M9.88 4.12A9.91 9.91 0 0121 12c-1.64 2.9-4.88 5-9 5a9.91 9.91 0 01-4.12-.88"/>
                        <path d="M3 3l18 18"/>
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    )}
                  </button>
                </div>
              </label>
              {createProvider.error && <div style={{ color: "#f87171" }}>{t('settings.providers.createFailed') || 'Failed to add provider.'}</div>}
              <button
                type="submit"
                className="icon-button square"
                title={t('settings.providers.save')}
                aria-label={t('settings.providers.save')}
                disabled={createProvider.isPending}
                style={{ color: '#16a34a' }}
              >
                {createProvider.isPending ? <span className="spinner" aria-hidden /> : <Icon name="save" />}
              </button>
            </form>
          </>
        )}

        {/* Search Providers */}
        {activeTab === 'providers_search' && (
          <>
            <div className="card" style={{ padding: '0.6rem 0.7rem', display: 'grid', gap: '0.25rem' }}>
              <div className="panel-subtitle" style={{ margin: 0 }}>{t('settings.providers.searchTab') || 'Search providers'}</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: '0.5rem', rowGap: '0.2rem', alignItems: 'baseline', fontSize: '0.9rem', lineHeight: 1.25 }}>
                <div style={{ color: 'var(--muted)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{t('settings.providers.fields.provider')}</div>
                <div>{searchProvider ? (searchProvider.provider || '-') : '-'}</div>
                <div style={{ color: 'var(--muted)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{t('settings.providers.fields.baseUrl')}</div>
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{searchProvider ? (searchProvider.base_url || '-') : '-'}</div>
              </div>
            </div>
            <div className="card" style={{ gap: "0.35rem", padding: '0.6rem 0.7rem' }}>
              <h2 style={{ margin: 0, fontSize: "1rem" }}>Search Provider</h2>
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
                <button
                  type="button"
                  className="icon-button square"
                  title={t('settings.providers.save')}
                  aria-label={t('settings.providers.save')}
                  onClick={() => upsertSearch.mutate()}
                  disabled={upsertSearch.isPending}
                  style={{ color: '#16a34a' }}
                >
                  {upsertSearch.isPending ? (
                    <span className="spinner" aria-hidden />
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                      <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
                      <path d="M17 21v-8H7v8"/>
                      <path d="M7 3v5h8"/>
                    </svg>
                  )}
                </button>
                {searchProvider && (
                  <div style={{ color: "#94a3b8", lineHeight: 1 }}>
                    Active: {searchProvider.provider}
                  </div>

                )}
              </div>
            </div>
          </>)
        }
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
          <button type="button" className={`tab-button ${activeTab === "providers_llm" ? "active" : ""}`} onClick={() => setActiveTab("providers_llm")}>
            {t('settings.tabs.llmProviders') || t('settings.providers.llmTab')}
          </button>
          <button type="button" className={`tab-button ${activeTab === "providers_search" ? "active" : ""}`} onClick={() => setActiveTab("providers_search")}>
            {t('settings.tabs.searchProviders') || t('settings.providers.searchTab')}
          </button>
        </nav>
        <section>{tabContent}</section>
      </div>
    </div>
  );
}

// (Radix-based AppSelect replaces local FancySelect)
