import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../api/client";

type Simulation = {
  id: number;
  name: string;
  status: string;
  created_at: string;
};

export function SavedSimulationsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const simulationsQuery = useQuery({
    queryKey: ["simulations"],
    queryFn: async () => {
      const response = await apiClient.get<Simulation[]>("/simulations");
      return response.data;
    },
  });

  const copySimulation = useMutation({
    mutationFn: async (simulationId: number) => {
      const response = await apiClient.post<Simulation>(`/simulations/${simulationId}/copy`);
      return response.data;
    },
    onSuccess: (simulation) => {
      queryClient.invalidateQueries({ queryKey: ["simulations"] });
      navigate(`/simulations/${simulation.id}`);
    },
  });

  const resumeSimulation = useMutation({
    mutationFn: async (simulationId: number) => {
      await apiClient.post(`/simulations/${simulationId}/resume`);
    },
    onSuccess: (_, simulationId) => {
      navigate(`/simulations/${simulationId}`);
    },
  });

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 style={{ margin: 0 }}>Saved simulations</h1>
      </header>
      <main className="app-main">
        <div className="panel" style={{ gap: "1rem" }}>
          {simulationsQuery.isLoading && <div>Loading…</div>}
          {simulationsQuery.error && <div style={{ color: "#f87171" }}>Unable to load simulations.</div>}
          <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
            {(simulationsQuery.data ?? []).map((simulation) => (
              <div key={simulation.id} className="card">
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{simulation.name}</div>
                    <div style={{ color: "#94a3b8" }}>{simulation.status}</div>
                  </div>
                  <div style={{ color: "#64748b" }}>{new Date(simulation.created_at).toLocaleDateString()}</div>
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    type="button"
                    className="button"
                    style={{ flex: 1 }}
                    onClick={() => resumeSimulation.mutate(simulation.id)}
                    disabled={resumeSimulation.isLoading}
                  >
                    Resume
                  </button>
                  <button
                    type="button"
                    className="button"
                    style={{ flex: 1, background: "rgba(148,163,184,0.2)", color: "#e2e8f0" }}
                    onClick={() => copySimulation.mutate(simulation.id)}
                    disabled={copySimulation.isLoading}
                  >
                    Copy
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
