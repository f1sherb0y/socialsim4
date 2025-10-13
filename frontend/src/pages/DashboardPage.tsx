import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listSimulations, type Simulation } from "../api/simulations";

type Simulation = {
  id: string;
  name: string;
  status: string;
  created_at: string;
};

export function DashboardPage() {
  const simulationsQuery = useQuery({
    queryKey: ["simulations"],
    queryFn: () => listSimulations(),
  });

  return (
    <div className="app-container">
      <header className="app-header">
        <div>
          <h1 style={{ margin: 0 }}>Dashboard</h1>
          <p style={{ color: "#94a3b8" }}>Pick up where you left off or launch something new.</p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <Link to="/simulations/new" className="button">
            New simulation
          </Link>
          <Link to="/simulations/saved" className="button" style={{ background: "rgba(148,163,184,0.2)", color: "#e2e8f0" }}>
            Resume saved
          </Link>
        </div>
      </header>
      <main className="app-main">
        <section className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
          <div className="card">
            <div className="panel-title">Quick start</div>
            <p style={{ color: "#94a3b8" }}>Jump directly into the guided setup wizard.</p>
            <Link to="/simulations/new" className="button">
              Launch wizard
            </Link>
          </div>
          <div className="card">
            <div className="panel-title">Connect providers</div>
            <p style={{ color: "#94a3b8" }}>Add your OpenAI, Azure, or custom endpoints once and reuse them across simulations.</p>
            <Link to="/settings/providers" className="button" style={{ alignSelf: "flex-start" }}>
              Manage providers
            </Link>
          </div>
        </section>

        <section style={{ marginTop: "2rem" }}>
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">Recent simulations</div>
              <Link to="/simulations/saved" style={{ color: "#38bdf8" }}>
                View all
              </Link>
            </div>
            {simulationsQuery.isLoading && <div>Loading simulations…</div>}
            {simulationsQuery.error && <div style={{ color: "#f87171" }}>Unable to load simulations.</div>}
            <div style={{ display: "grid", gap: "0.75rem" }}>
              {(simulationsQuery.data ?? []).slice(0, 5).map((simulation) => (
                <Link key={simulation.id} to={`/simulations/${simulation.id}`} className="card" style={{ background: "rgba(30,41,59,0.6)", margin: 0 }}>
                  <div style={{ fontWeight: 600 }}>{simulation.name}</div>
                  <div style={{ color: "#94a3b8" }}>Status: {simulation.status}</div>
                  <div style={{ color: "#64748b" }}>Created {new Date(simulation.created_at).toLocaleString()}</div>
                </Link>
              ))}
              {simulationsQuery.data && simulationsQuery.data.length === 0 && (
                <div style={{ color: "#94a3b8" }}>No simulations yet. Create one to get started.</div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
