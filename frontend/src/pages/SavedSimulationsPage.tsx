import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { copySimulation as apiCopySimulation, listSimulations, resumeSimulation as apiResumeSimulation, type Simulation } from "../api/simulations";

type Simulation = {
  id: string;
  name: string;
  status: string;
  created_at: string;
};

export function SavedSimulationsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const simulationsQuery = useQuery({
    queryKey: ["simulations"],
    queryFn: () => listSimulations(),
  });

  const copySimulation = useMutation({
    mutationFn: async (simulationSlug: string) => apiCopySimulation(simulationSlug),
    onSuccess: (simulation) => {
      queryClient.invalidateQueries({ queryKey: ["simulations"] });
      navigate(`/simulations/${simulation.id}`);
    },
  });

  const resumeSimulation = useMutation({
    mutationFn: async (simulationSlug: string) => apiResumeSimulation(simulationSlug),
    onSuccess: (_, simulationSlug) => {
      navigate(`/simulations/${simulationSlug}`);
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
                    disabled={resumeSimulation.isPending}
                  >
                    Resume
                  </button>
                  <button
                    type="button"
                    className="button"
                    style={{ flex: 1, background: "rgba(148,163,184,0.2)", color: "#e2e8f0" }}
                    onClick={() => copySimulation.mutate(simulation.id)}
                    disabled={copySimulation.isPending}
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
