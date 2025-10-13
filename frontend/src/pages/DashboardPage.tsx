import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listSimulations, type Simulation } from "../api/simulations";
import { listProviders } from "../api/providers";
import { useTranslation } from "react-i18next";

// Use Simulation type from API (includes scene_type)

export function DashboardPage() {
  const { t } = useTranslation();
  const simulationsQuery = useQuery({
    queryKey: ["simulations"],
    queryFn: () => listSimulations(),
  });
  const providersQuery = useQuery({
    queryKey: ["providers"],
    queryFn: () => listProviders(),
  });
  const hasProvider = (providersQuery.data ?? []).length > 0;

  return (
    <div className="app-container">
      <header className="app-header">
        <div>
          <h1 style={{ margin: 0 }}>{t('dashboard.title')}</h1>
          <p style={{ color: "#94a3b8" }}>{t('dashboard.subtitle')}</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <Link to={hasProvider ? "/simulations/new" : "/settings/providers"} className={`button ${!hasProvider ? 'button-ghost' : ''}`}
            aria-disabled={!hasProvider}
            onClick={(e) => { if (!hasProvider) e.preventDefault(); }}
          >
            {t('dashboard.new')}
          </Link>
          <Link to="/simulations/saved" className="button button-ghost">{t('dashboard.resume')}</Link>
        </div>
      </header>
      <main className="app-main">
        {!hasProvider && (
          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <div className="panel-title"><span className="badge-warning" aria-hidden>!</span>{t('settings.providers.title')}</div>
            <div style={{ color: "var(--muted)" }}>{t('dashboard.providerRequired')}</div>
            <div style={{ color: "var(--muted)" }}>{t('dashboard.providersHint')}</div>
            <Link to="/settings/providers" className="button button-danger" style={{ marginTop: '0.5rem', width: 'fit-content' }}>
              {t('dashboard.manageProviders')}
            </Link>
          </div>
        )}
        <section className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
          <div className="card">
            <div className="panel-title">{t('dashboard.quick')}</div>
            <p style={{ color: "#94a3b8" }}>{t('dashboard.subtitle')}</p>
            <Link
              to={hasProvider ? "/simulations/new" : "/settings/providers"}
              className={`button ${!hasProvider ? 'button-ghost' : ''}`}
              aria-disabled={!hasProvider}
              onClick={(e) => { if (!hasProvider) e.preventDefault(); }}
            >
              {t('dashboard.launchWizard')}
            </Link>
          </div>
          <div className="card">
            <div className="panel-title">{t('dashboard.providers')}</div>
            <p style={{ color: "#94a3b8" }}>{t('dashboard.providersHint')}</p>
            <Link to="/settings/providers" className="button button-ghost" style={{ alignSelf: "flex-start" }}>{t('dashboard.manageProviders')}</Link>
          </div>
        </section>

        <section style={{ marginTop: "2rem" }}>
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">{t('dashboard.recent')}</div>
              <Link to="/simulations/saved" className="link">{t('dashboard.viewAll')}</Link>
            </div>
            {simulationsQuery.isLoading && <div>{t('dashboard.loading')}</div>}
            {simulationsQuery.error && <div style={{ color: "#f87171" }}>{t('dashboard.error')}</div>}
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {(simulationsQuery.data ?? []).slice(0, 5).map((simulation) => (
                <Link key={simulation.id} to={`/simulations/${simulation.id}`} className="card" style={{ margin: 0 }}>
                  <div style={{ fontWeight: 600 }}>{simulation.name}</div>
                  <div style={{ color: "#94a3b8" }}>{t('dashboard.status')}: {simulation.status}</div>
                  <div style={{ color: "#94a3b8" }}>{t('dashboard.sceneType') || 'Scene'}: {simulation.scene_type}</div>
                  <div style={{ color: "#64748b" }}>{t('dashboard.created')} {new Date(simulation.created_at).toLocaleString()}</div>
                </Link>
              ))}
              {simulationsQuery.data && simulationsQuery.data.length === 0 && (
                <div style={{ color: "#94a3b8" }}>{t('dashboard.empty')}</div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
