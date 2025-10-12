import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { apiClient } from "../api/client";

type Simulation = {
  id: number;
  name: string;
  status: string;
  latest_state?: Record<string, unknown> | null;
};

type LogEntry = {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export function WorkspacePage() {
  const { id } = useParams();
  const simulationId = Number(id);
  const queryClient = useQueryClient();

  const simulationQuery = useQuery({
    queryKey: ["simulation", simulationId],
    enabled: Number.isFinite(simulationId),
    queryFn: async () => {
      const response = await apiClient.get<Simulation>(`/simulations/${simulationId}`);
      return response.data;
    },
  });

  const logsQuery = useQuery({
    queryKey: ["simulation", simulationId, "logs"],
    enabled: Number.isFinite(simulationId),
    queryFn: async () => {
      const response = await apiClient.get<LogEntry[]>(`/simulations/${simulationId}/logs`);
      return response.data;
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/simulations/${simulationId}/save`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simulation", simulationId, "snapshots"] });
    },
  });

  const events = useMemo(() => logsQuery.data ?? [], [logsQuery.data]);

  return (
    <div className="app-container">
      <header className="app-header">
        <div>
          <h1 style={{ margin: 0 }}>{simulationQuery.data?.name ?? "Simulation"}</h1>
          <p style={{ color: "#94a3b8" }}>Live view of your social simulation.</p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button type="button" className="button" onClick={() => queryClient.invalidateQueries({ queryKey: ["simulation", simulationId, "logs"] })}>
            Refresh
          </button>
          <button type="button" className="button" onClick={() => saveMutation.mutate()} disabled={saveMutation.isLoading}>
            {saveMutation.isLoading ? "Saving…" : "Save"}
          </button>
        </div>
      </header>
      <main className="app-main">
        <div className="three-column-grid">
          <aside className="panel">
            <div className="panel-title">Simulation tree</div>
            <div style={{ color: "#94a3b8" }}>Tree visualization will appear here. Branch nodes after saving snapshots or creating forks.</div>
          </aside>
          <section className="panel">
            <div className="panel-title">Events</div>
            <div style={{ display: "grid", gap: "0.75rem", maxHeight: "70vh", overflowY: "auto" }}>
              {events.map((event) => (
                <article key={event.id} className="card" style={{ margin: 0, background: "rgba(30,41,59,0.5)" }}>
                  <div style={{ fontSize: "0.85rem", color: "#64748b" }}>{new Date(event.created_at).toLocaleTimeString()}</div>
                  <div style={{ fontWeight: 600 }}>{event.event_type}</div>
                  <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(event.payload, null, 2)}</pre>
                </article>
              ))}
              {events.length === 0 && <div style={{ color: "#94a3b8" }}>No events yet.</div>}
            </div>
          </section>
          <aside className="panel">
            <div className="panel-title">Agents</div>
            <div style={{ display: "grid", gap: "0.75rem", maxHeight: "70vh", overflowY: "auto" }}>
              {Object.entries((simulationQuery.data?.latest_state?.agents as Record<string, unknown>) ?? {}).map(([agentName, details]) => (
                <div key={agentName} className="card" style={{ margin: 0, background: "rgba(30,41,59,0.5)" }}>
                  <div style={{ fontWeight: 600 }}>{agentName}</div>
                  <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(details, null, 2)}</pre>
                </div>
              ))}
              {!simulationQuery.data?.latest_state && (
                <div style={{ color: "#94a3b8" }}>No agent context loaded yet.</div>
              )}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
