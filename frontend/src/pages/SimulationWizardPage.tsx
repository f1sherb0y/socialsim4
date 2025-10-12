import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiClient } from "../api/client";

type SceneOption = {
  type: string;
  name: string;
  config_schema: Record<string, unknown>;
};

type Step = "scene" | "scene-config" | "agents" | "review";

export function SimulationWizardPage() {
  const navigate = useNavigate();
  const scenesQuery = useQuery({
    queryKey: ["scenes"],
    queryFn: async () => {
      const response = await apiClient.get<SceneOption[]>("/scenes");
      return response.data;
    },
  });

  const [step, setStep] = useState<Step>("scene");
  const [sceneType, setSceneType] = useState<string | null>(null);
  const [sceneConfig, setSceneConfig] = useState<Record<string, string>>({});
  const [agents, setAgents] = useState([
    { name: "Alice", profile: "Analyst", action_space: ["send_message"] },
  ]);

  const createSimulation = useMutation({
    mutationFn: async () => {
      if (!sceneType) throw new Error("scene required");
      const response = await apiClient.post("/simulations", {
        scene_type: sceneType,
        scene_config: sceneConfig,
        agent_config: { agents },
      });
      return response.data as { id: number };
    },
    onSuccess: (data) => {
      navigate(`/simulations/${data.id}`);
    },
  });

  const currentScene = useMemo(
    () => scenesQuery.data?.find((scene) => scene.type === sceneType),
    [sceneType, scenesQuery.data],
  );

  const nextStep = () => {
    if (step === "scene") setStep("scene-config");
    else if (step === "scene-config") setStep("agents");
    else if (step === "agents") setStep("review");
  };

  const previousStep = () => {
    if (step === "scene-config") setStep("scene");
    else if (step === "agents") setStep("scene-config");
    else if (step === "review") setStep("agents");
  };

  const handleAddAgent = () => {
    setAgents((prev) => [...prev, { name: `Agent ${prev.length + 1}`, profile: "", action_space: ["send_message"] }]);
  };

  const handleAgentChange = (index: number, field: string, value: string) => {
    setAgents((prev) =>
      prev.map((agent, i) => (i === index ? { ...agent, [field]: value } : agent)),
    );
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    createSimulation.mutate();
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div>
          <h1 style={{ margin: 0 }}>Simulation wizard</h1>
          <p style={{ color: "#94a3b8" }}>Configure your environment, agents, and review before launch.</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {step !== "scene" && (
            <button type="button" className="button" style={{ background: "rgba(148,163,184,0.2)", color: "#e2e8f0" }} onClick={previousStep}>
              Back
            </button>
          )}
          {step !== "review" && (
            <button type="button" className="button" onClick={nextStep} disabled={step === "scene" && !sceneType}>
              Continue
            </button>
          )}
        </div>
      </header>
      <main className="app-main">
        <form onSubmit={handleSubmit} className="panel" style={{ gap: "1.5rem" }}>
          {step === "scene" && (
            <div>
              <div className="panel-title">Select scene</div>
              {scenesQuery.isLoading && <div>Loading scenes…</div>}
              {scenesQuery.error && <div style={{ color: "#f87171" }}>Unable to fetch scenes.</div>}
              <div style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
                {(scenesQuery.data ?? []).map((scene) => (
                  <label key={scene.type} className="card" style={{ cursor: "pointer", border: scene.type === sceneType ? "1px solid #38bdf8" : undefined }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{scene.name}</div>
                        <div style={{ color: "#94a3b8" }}>{scene.type}</div>
                      </div>
                      <input
                        type="radio"
                        name="scene"
                        checked={scene.type === sceneType}
                        onChange={() => setSceneType(scene.type)}
                      />
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {step === "scene-config" && (
            <div>
              <div className="panel-title">Configure scene</div>
              {currentScene ? (
                <div style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
                  {Object.keys(currentScene.config_schema ?? {}).length === 0 && (
                    <div style={{ color: "#94a3b8" }}>This scene has no additional configuration.</div>
                  )}
                  {Object.entries(currentScene.config_schema ?? {}).map(([key, value]) => (
                    <label key={key}>
                      {key}
                      <input
                        value={sceneConfig[key] ?? String(value ?? "")}
                        onChange={(event) => setSceneConfig((prev) => ({ ...prev, [key]: event.target.value }))}
                        style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
                      />
                    </label>
                  ))}
                </div>
              ) : (
                <div style={{ color: "#94a3b8" }}>Select a scene first.</div>
              )}
            </div>
          )}

          {step === "agents" && (
            <div>
              <div className="panel-title">Define agents</div>
              <div style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
                {agents.map((agent, index) => (
                  <div key={index} className="card" style={{ gap: "0.75rem" }}>
                    <label>
                      Name
                      <input
                        value={agent.name}
                        onChange={(event) => handleAgentChange(index, "name", event.target.value)}
                        style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
                      />
                    </label>
                    <label>
                      Profile
                      <input
                        value={agent.profile}
                        onChange={(event) => handleAgentChange(index, "profile", event.target.value)}
                        style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
                      />
                    </label>
                  </div>
                ))}
                <button type="button" className="button" onClick={handleAddAgent} style={{ width: "fit-content" }}>
                  Add agent
                </button>
              </div>
            </div>
          )}

          {step === "review" && (
            <div style={{ display: "grid", gap: "1rem" }}>
              <div className="panel-title">Review</div>
              <div className="card" style={{ background: "rgba(30,41,59,0.6)" }}>
                <div style={{ fontWeight: 600 }}>Scene</div>
                <div>{sceneType}</div>
              </div>
              <div className="card" style={{ background: "rgba(30,41,59,0.6)" }}>
                <div style={{ fontWeight: 600 }}>Configuration</div>
                <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0 }}>{JSON.stringify(sceneConfig, null, 2)}</pre>
              </div>
              <div className="card" style={{ background: "rgba(30,41,59,0.6)" }}>
                <div style={{ fontWeight: 600 }}>Agents</div>
                <ul>
                  {agents.map((agent, index) => (
                    <li key={index}>{agent.name} — {agent.profile || "No profile"}</li>
                  ))}
                </ul>
              </div>
              <button type="submit" className="button" disabled={createSimulation.isLoading}>
                {createSimulation.isLoading ? "Creating…" : "Start simulation"}
              </button>
              {createSimulation.error && <div style={{ color: "#f87171" }}>Failed to create simulation.</div>}
            </div>
          )}
        </form>
      </main>
    </div>
  );
}
