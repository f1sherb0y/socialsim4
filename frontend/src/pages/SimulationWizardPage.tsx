import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listScenes, type SceneOption } from "../api/scenes";
import { createSimulation } from "../api/simulations";
import { useTranslation } from "react-i18next";

type Step = "scene" | "scene-config" | "agents" | "review";

export function SimulationWizardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const scenesQuery = useQuery({
    queryKey: ["scenes"],
    queryFn: () => listScenes(),
  });

  const [step, setStep] = useState<Step>("scene");
  const [sceneType, setSceneType] = useState<string | null>(null);
  const [sceneConfig, setSceneConfig] = useState<Record<string, string>>({});
  const [lastSceneType, setLastSceneType] = useState<string | null>(null);
  const [agents, setAgents] = useState([
    { name: "Alice", profile: "Analyst", action_space: ["send_message"] },
  ]);

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!sceneType) throw new Error("scene required");
      const effectiveConfig = { ...defaultConfig, ...sceneConfig };
      const sim = await createSimulation({
        scene_type: sceneType,
        scene_config: effectiveConfig,
        agent_config: { agents },
      });
      return sim;
    },
    onSuccess: (simulation) => navigate(`/simulations/${simulation.id}`),
  });

  const currentScene = useMemo(
    () => scenesQuery.data?.find((scene) => scene.type === sceneType),
    [sceneType, scenesQuery.data],
  );

  const defaultConfig = useMemo(() => {
    const schema = (currentScene?.config_schema ?? {}) as Record<string, unknown>;
    const entries = Object.entries(schema).map(([k, v]) => [k, String(v ?? "")]);
    return Object.fromEntries(entries) as Record<string, string>;
  }, [currentScene]);

  const SIMPLE_CHAT_SCENE = "simple_chat_scene";
  const defaultSimpleAgents = useMemo(
    () => [
      {
        name: "Host",
        profile:
          "You are the Host of a chat room. Facilitate conversation, ask clarifying questions, and remain neutral to keep the discussion productive.",
        action_space: ["send_message"],
      },
      {
        name: "Alice",
        profile:
          "You are Alice, optimistic and curious about technology; you ask insightful questions, synthesize viewpoints, and keep the discussion constructive.",
        action_space: ["send_message"],
      },
      {
        name: "Bob",
        profile:
          "You are Bob, pragmatic and skeptical; you challenge assumptions, request evidence, and help the group converge on practical conclusions.",
        action_space: ["send_message"],
      },
    ],
    []
  );

  useEffect(() => {
    if (sceneType && sceneType !== lastSceneType) {
      setSceneConfig(defaultConfig);
      if (sceneType === SIMPLE_CHAT_SCENE) {
        setAgents(defaultSimpleAgents);
      }
      setLastSceneType(sceneType);
    }
  }, [sceneType, lastSceneType, defaultConfig, defaultSimpleAgents]);

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
    createMutation.mutate();
  };

  return (
    <form onSubmit={handleSubmit} className="panel" style={{ gap: "0.75rem" }}>
      <div className="panel-header">
        <div className="panel-title">{t('wizard.title')}</div>
        <div style={{ display: "flex", gap: "0.4rem" }}>
          {step !== "scene" && (
            <button type="button" className="button" onClick={previousStep}>{t('wizard.back')}</button>
          )}
          {step !== "review" && (
            <button type="button" className="button" onClick={nextStep} disabled={step === "scene" && !sceneType}>{t('wizard.continue')}</button>
          )}
        </div>
      </div>
      {step === "scene" && (
        <div>
          <div className="panel-title">{t('wizard.selectScene')}</div>
          {scenesQuery.isLoading && <div>{t('wizard.loadingScenes')}</div>}
          {scenesQuery.error && <div style={{ color: "#f87171" }}>{t('wizard.fetchScenesError')}</div>}
          <div style={{ display: "grid", gap: "0.5rem", marginTop: "0.5rem" }}>
            {(scenesQuery.data ?? []).map((scene) => (
              <label key={scene.type} className="card" style={{ cursor: "pointer", border: scene.type === sceneType ? "1px solid #38bdf8" : undefined, padding: "0.75rem" }}>
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
          <div className="panel-title">{t('wizard.configureScene')}</div>
          {currentScene ? (
            <div style={{ display: "grid", gap: "0.5rem", marginTop: "0.5rem" }}>
              {Object.keys(currentScene.config_schema ?? {}).length === 0 && (
                <div style={{ color: "#94a3b8" }}>{t('wizard.noExtraConfig')}</div>
              )}
              {Object.entries(currentScene.config_schema ?? {}).map(([key, value]) => (
                <label key={key}>
                  {key}
                  <input
                    className="input"
                    value={sceneConfig[key] ?? String(value ?? "")}
                    onChange={(event) => setSceneConfig((prev) => ({ ...prev, [key]: event.target.value }))}
                  />
                </label>
              ))}
            </div>
          ) : (
            <div style={{ color: "#94a3b8" }}>{t('wizard.selectPrompt')}</div>
          )}
        </div>
      )}

      {step === "agents" && (
        <div>
          <div className="panel-title">{t('wizard.defineAgents')}</div>
          <div style={{ display: "grid", gap: "0.5rem", marginTop: "0.5rem" }}>
            {agents.map((agent, index) => (
              <div key={index} className="card" style={{ gap: "0.5rem" }}>
                <label>
                  {t('wizard.name')}
                  <input
                    className="input"
                    value={agent.name}
                    onChange={(event) => handleAgentChange(index, "name", event.target.value)}
                  />
                </label>
                <label>
                  {t('wizard.profile')}
                  <input
                    className="input"
                    value={agent.profile}
                    onChange={(event) => handleAgentChange(index, "profile", event.target.value)}
                  />
                </label>
              </div>
            ))}
            <button type="button" className="button" onClick={handleAddAgent} style={{ width: "fit-content" }}>{t('wizard.addAgent')}</button>
          </div>
        </div>
      )}

      {step === "review" && (
        <div style={{ display: "grid", gap: "0.5rem" }}>
          <div className="panel-title">{t('wizard.review')}</div>
          <div className="card">
            <div style={{ fontWeight: 600 }}>{t('wizard.scene') || 'Scene'}</div>
            <div>{sceneType}</div>
          </div>
          <div className="card">
            <div style={{ fontWeight: 600 }}>{t('wizard.config')}</div>
            <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0 }}>{JSON.stringify(sceneConfig, null, 2)}</pre>
          </div>
          <div className="card">
            <div style={{ fontWeight: 600 }}>{t('wizard.agents')}</div>
            <ul>
              {agents.map((agent, index) => (
                <li key={index}>{agent.name} — {agent.profile || t('wizard.noProfile')}</li>
              ))}
            </ul>
          </div>
          <button type="submit" className="button" disabled={createMutation.isPending}>{createMutation.isPending ? t('wizard.start') + '…' : t('wizard.start')}</button>
          {createMutation.error && <div style={{ color: "#f87171" }}>{t('wizard.createFailed')}</div>}
        </div>
      )}
    </form>
  );
}
