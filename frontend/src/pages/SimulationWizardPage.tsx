import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import TextareaAutosize from 'react-textarea-autosize';
import { useNavigate } from "react-router-dom";

import { listScenes, type SceneOption } from "../api/scenes";
import { createSimulation } from "../api/simulations";
import { useTranslation } from "react-i18next";
import { TitleCard } from "../components/TitleCard";

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
  const [sceneConfig, setSceneConfig] = useState<Record<string, any>>({});
  const [lastSceneType, setLastSceneType] = useState<string | null>(null);
  const [agents, setAgents] = useState([
    { name: "Alice", profile: "Analyst", action_space: ["send_message"] },
  ]);
  const [selectedAgentIdx, setSelectedAgentIdx] = useState(0);

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
    return { ...schema } as Record<string, any>;
  }, [currentScene]);

  const SIMPLE_CHAT_SCENE = "simple_chat_scene";
  const EMOTIONAL_CONFLICT_SCENE = "emotional_conflict_scene";
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

  // Default agents per scene (lightweight templates for quick start)
  const defaultAgentsForScene = (type: string) => {
    if (type === SIMPLE_CHAT_SCENE) return defaultSimpleAgents;
    if (type === EMOTIONAL_CONFLICT_SCENE) return [
      {
        name: "Host",
        profile:
          "You are the host of the emotional dialogue room. Your role is to maintain order, keep the conversation balanced, and help both sides express their true feelings and find understanding.",
        action_space: ["send_message"],
      },
      {
        name: "Lily",
        profile:
          "You are Lily, a straightforward and emotional person. You feel your partner Alex has been distant lately — always on the phone, not replying to your messages. You easily swing between anger, sadness, and a fragile hope that Alex still cares.",
        action_space: ["send_message"],
      },
      {
        name: "Alex",
        profile:
          "You are Alex, Lily’s partner. You are introverted and tend to avoid conflict. Recently you’ve been under work pressure, but you haven’t explained it clearly to Lily, causing misunderstandings. In the conversation, you may start defensive or cold, but gradually show regret and a wish to reconcile.",
        action_space: ["send_message"],
      },
    ];
    if (type === "council_scene") return [
      { name: "Host", profile: "Neutral chair of the council.", action_space: ["send_message"] },
      { name: "Rep. Chen Wei", profile: "Centrist economist.", action_space: ["send_message"] },
      { name: "Rep. Li Na", profile: "Progressive voice.", action_space: ["send_message"] },
      { name: "Rep. Zhang Rui", profile: "Conservative representative.", action_space: ["send_message"] },
      { name: "Rep. Wang Mei", profile: "Business-aligned representative.", action_space: ["send_message"] },
    ];
    if (type === "village_scene") return [
      { name: "Elias Thorne", profile: "Reclusive scholar.", action_space: ["send_message"] },
      { name: "Seraphina", profile: "Village herbalist.", action_space: ["send_message"] },
      { name: "Kaelen", profile: "Village blacksmith.", action_space: ["send_message"] },
      { name: "Lyra", profile: "Adventurous cartographer.", action_space: ["send_message"] },
    ];
    if (type === "werewolf_scene") return [
      { name: "Moderator", profile: "Neutral moderator.", action_space: ["send_message"] },
      { name: "Elena", profile: "Villager.", action_space: ["send_message"] },
      { name: "Bram", profile: "Villager.", action_space: ["send_message"] },
      { name: "Ronan", profile: "Villager.", action_space: ["send_message"] },
      { name: "Mira", profile: "Villager.", action_space: ["send_message"] },
      { name: "Pia", profile: "Villager.", action_space: ["send_message"] },
      { name: "Taro", profile: "Villager.", action_space: ["send_message"] },
      { name: "Ava", profile: "Villager.", action_space: ["send_message"] },
      { name: "Niko", profile: "Villager.", action_space: ["send_message"] },
    ];
    if (type === "landlord_scene") return [
      { name: "Alice", profile: "Aggressive player.", action_space: ["send_message"] },
      { name: "Bob", profile: "Cautious player.", action_space: ["send_message"] },
      { name: "Carol", profile: "Combo-focused player.", action_space: ["send_message"] },
      { name: "Dave", profile: "Power player.", action_space: ["send_message"] },
    ];
    return [{ name: "Alice", profile: "", action_space: [] }];
  };

  // Helper: select a scene and immediately reset to its defaults
  const handleSelectScene = (scene: SceneOption) => {
    setSceneType(scene.type);
    const cfg = { ...(scene.config_schema || {}) } as Record<string, any>;
    // Emotional conflict scene custom defaults
    if (scene.type === EMOTIONAL_CONFLICT_SCENE) {
      cfg.emotion_enabled = true;
      cfg.initial_events = [
        "Participants: Host, Lily, Alex",
        "Scene start: Lily feels Alex has become emotionally distant, while Alex thinks Lily is overreacting. The host will guide them to express their emotions and seek resolution.",
      ];
    }
    if (cfg.emotion_enabled === undefined) cfg.emotion_enabled = false;
    setSceneConfig(cfg);
    setAgents(defaultAgentsForScene(scene.type));
    setLastSceneType(scene.type);
  };

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

  const stepsOrder: Step[] = ["scene", "scene-config", "agents", "review"];
  const canGo = (target: Step) => {
    if (target === "scene") return true;
    // Require a selected scene to proceed to any later step
    return Boolean(sceneType);
  };
  const goStep = (target: Step) => {
    if (canGo(target)) setStep(target);
  };

  const handleAddAgent = () => {
    setAgents((prev) => {
      const next = [...prev, { name: `Agent ${prev.length + 1}`, profile: "", action_space: [] }];
      setSelectedAgentIdx(next.length - 1);
      return next;
    });
  };

  const handleRemoveAgent = (index: number) => {
    setAgents((prev) => {
      if (prev.length <= 1) return prev;
      const next = prev.filter((_, i) => i !== index);
      const newIdx = Math.max(0, Math.min(selectedAgentIdx, next.length - 1));
      setSelectedAgentIdx(newIdx);
      return next;
    });
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

  // (No wrapper needed: use TextareaAutosize directly where needed)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <TitleCard
        title={t('wizard.title')}
        center={(
          <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', justifyContent: 'center', width: '100%', marginTop: 4 }}>
            {(() => {
              const idx = stepsOrder.indexOf(step);
              return stepsOrder.map((s, i) => {
                const allowed = canGo(s);
                const active = i === idx;
                const done = i < idx;
                const labelColor = active ? 'var(--text)' : 'var(--muted)';
                const labelText = s === 'scene' ? (t('wizard.selectScene') || 'Scene') : s === 'scene-config' ? (t('wizard.configureScene') || 'Config') : s === 'agents' ? (t('wizard.defineAgents') || 'Agents') : (t('wizard.review') || 'Review');
                return (
                  <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, minWidth: 40 }}>
                    <button
                      type="button"
                      aria-label={labelText}
                      title={labelText}
                      onClick={() => goStep(s)}
                      disabled={!allowed}
                      style={{
                        position: 'relative',
                        width: '100%',
                        height: 8,
                        borderRadius: 9999,
                        background: 'var(--border)',
                        border: 'none',
                        cursor: allowed ? 'pointer' : 'not-allowed',
                        opacity: allowed ? 1 : 0.6,
                        overflow: 'hidden',
                      }}
                    >
                      <span
                        style={{
                          position: 'absolute',
                          inset: 0,
                          width: done || active ? '100%' : '0%',
                          background: done ? 'var(--accent-a)' : active ? 'var(--accent-b)' : 'transparent',
                          transition: 'width 260ms ease',
                        }}
                      />
                    </button>
                    <button
                      type="button"
                      onClick={() => goStep(s)}
                      disabled={!allowed}
                      style={{
                        marginTop: 2,
                        fontSize: '0.75rem',
                        color: labelColor,
                        background: 'transparent',
                        border: 'none',
                        cursor: allowed ? 'pointer' : 'not-allowed',
                        opacity: allowed ? 1 : 0.6,
                      }}
                    >
                      {labelText}
                    </button>
                  </div>
                );
              });
            })()}
          </div>
        )}
        actions={(
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {step !== "scene" && (
              <button
                type="button"
                className="icon-button"
                aria-label={t('wizard.back')}
                title={t('wizard.back')}
                onClick={previousStep}
                style={{
                  height: 36,
                  width: 'calc(36px * 1.618)',
                  fontSize: '1.25rem',
                  padding: 0,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  lineHeight: 1,
                }}
              >
                ←
              </button>
            )}
            {step !== "review" && (
              <button
                type="button"
                className="button"
                aria-label={t('wizard.continue')}
                title={t('wizard.continue')}
                onClick={nextStep}
                disabled={step === "scene" && !sceneType}
                style={{
                  height: 36,
                  width: 'calc(36px * 1.618)',
                  fontSize: '1.25rem',
                  padding: 0,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  lineHeight: 1,
                }}
              >
                →
              </button>
            )}
          </div>
        )}
      />
      <div className="scroll-panel" style={{ height: '100%', overflow: 'auto' }}>
        <form onSubmit={handleSubmit} className="panel" style={{ gap: "0.75rem" }}>
          {step === "scene" && (
            <div>
              <div className="panel-title">{t('wizard.selectScene')}</div>
              {scenesQuery.isLoading && <div>{t('wizard.loadingScenes')}</div>}
              {scenesQuery.error && <div style={{ color: "#f87171" }}>{t('wizard.fetchScenesError')}</div>}
              <div style={{ display: "grid", gap: "0.5rem", marginTop: "0.5rem" }}>
                {(scenesQuery.data ?? []).map((scene, idx) => (
                  <label key={idx} className="card" style={{ cursor: "pointer", border: scene.type === sceneType ? "1px solid #38bdf8" : undefined, padding: "0.75rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontWeight: 600 }}>{scene.name}</div>
                        <div style={{ color: "#94a3b8" }}>{scene.type}</div>
                        {scene.description && <div style={{ color: "var(--muted)", marginTop: 4, fontSize: '0.9rem' }}>{scene.description}</div>}
                      </div>
                      <input
                        type="radio"
                        name="scene"
                        checked={scene.type === sceneType}
                        onChange={() => handleSelectScene(scene)}
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
                <div style={{ display: "grid", gap: "0.75rem", marginTop: "0.5rem" }}>
                  {/* Emotional features (only for Emotional Conflict Scene) */}
                  <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
                    <div>
                      <div className="panel-subtitle">{t('wizard.emotionEnabled')}</div>
                      <div style={{ color: 'var(--muted)', fontSize: '0.9rem' }}>{t('wizard.emotionHint')}</div>
                    </div>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(sceneConfig.emotion_enabled)}
                        onChange={(e) => setSceneConfig((prev) => ({ ...prev, emotion_enabled: e.target.checked }))}
                      />
                      {Boolean(sceneConfig.emotion_enabled) ? t('common.show') : t('common.hide')}
                    </label>
                  </div>
                  {/* Events configuration */}
                  <div className="card" style={{ display: "grid", gap: "0.5rem" }}>
                    <div className="panel-subtitle">{t('wizard.events') || 'Initial events'}</div>
                    <div style={{ display: "grid", gap: "0.35rem" }}>
                      {((sceneConfig.initial_events as any[]) || []).map((ev, idx) => (
                        <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.5rem', alignItems: 'center' }}>
                          <TextareaAutosize
                            className="input"
                            value={String(ev)}
                            onChange={(e) => {
                              setSceneConfig((prev) => {
                                const list = Array.isArray(prev.initial_events) ? [...prev.initial_events] : [];
                                list[idx] = e.target.value;
                                return { ...prev, initial_events: list };
                              })
                            }}
                            minRows={1}
                            maxRows={999}
                            style={{ resize: 'none' }}
                          />
                          <button type="button" className="icon-button" aria-label={t('wizard.deleteAgent') || 'Delete agent'} title={t('wizard.deleteAgent') || 'Delete agent'} onClick={() => {
                            setSceneConfig((prev) => {
                              const list = Array.isArray(prev.initial_events) ? [...prev.initial_events] : [];
                              list.splice(idx, 1);
                              return { ...prev, initial_events: list };
                            })
                          }}>🗑</button>
                        </div>
                      ))}
                    </div>
                    <button type="button" className="button" onClick={() => setSceneConfig((prev) => ({ ...prev, initial_events: [...(prev.initial_events || []), ""] }))} style={{ width: 'fit-content' }}>{t('wizard.addEvent') || 'Add event'}</button>
                  </div>

                  {/* Scene specific configuration */}
                  <div className="card" style={{ display: "grid", gap: "0.5rem" }}>
                    <div className="panel-subtitle">{t('wizard.sceneSpecific') || 'Scene configuration'}</div>
                    {Object.keys(currentScene.config_schema ?? {}).filter((k) => k !== 'initial_events').length === 0 && (
                      <div style={{ color: "#94a3b8" }}>{t('wizard.noExtraConfig')}</div>
                    )}
                    {Object.entries(currentScene.config_schema ?? {}).filter(([key]) => key !== 'initial_events').map(([key, value]) => {
                      const initial = sceneConfig[key] ?? value;
                      const type = typeof value;
                      if (type === 'boolean') {
                        return (
                          <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <input
                              type="checkbox"
                              className="checkbox"
                              checked={Boolean(initial)}
                              onChange={(e) => setSceneConfig((prev) => ({ ...prev, [key]: e.target.checked }))}
                            />
                            {key}
                          </label>
                        );
                      }
                      if (type === 'number') {
                        return (
                          <label key={key}>
                            {key}
                            <input
                              className="input"
                              type="number"
                              value={Number(initial) as number}
                              onChange={(e) => setSceneConfig((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                            />
                          </label>
                        );
                      }
                      if (type === 'object' && value !== null) {
                        const json = JSON.stringify(initial, null, 2);
                        return (
                          <label key={key}>
                            {key}
                            <TextareaAutosize
                              className="input"
                              value={json}
                              onChange={(e) => {
                                try {
                                  const parsed = JSON.parse(e.target.value);
                                  setSceneConfig((prev) => ({ ...prev, [key]: parsed }));
                                } catch {
                                  // ignore invalid JSON edits
                                }
                              }}
                              minRows={6}
                              maxRows={999}
                              style={{ resize: 'none' }}
                            />
                          </label>
                        );
                      }
                      return (
                        <label key={key}>
                          {key}
                          <TextareaAutosize
                            className="input"
                            value={String(initial ?? '')}
                            onChange={(e) => setSceneConfig((prev) => ({ ...prev, [key]: e.target.value }))}
                            minRows={2}
                            maxRows={999}
                            style={{ resize: 'none' }}
                          />
                        </label>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div style={{ color: "#94a3b8" }}>{t('wizard.selectPrompt')}</div>
              )}
            </div>
          )}

          {step === "agents" && (
            <div>
              <div className="panel-title">{t('wizard.defineAgents')}</div>
              <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: "0.75rem", marginTop: "0.5rem", alignItems: "start" }}>
                <div className="card" style={{ padding: 0 }}>
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    {agents.map((ag, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setSelectedAgentIdx(i)}
                        className="button-ghost"
                        style={{
                          textAlign: "left",
                          border: "none",
                          borderRadius: 0,
                          padding: "0.6rem 0.75rem",
                          background: i === selectedAgentIdx ? "rgba(148,163,184,0.18)" : "transparent",
                        }}
                      >
                        {i + 1}. {ag.name || t('wizard.name')}
                      </button>
                    ))}
                    <div style={{ padding: "0.5rem" }}>
                      <button type="button" className="button" onClick={handleAddAgent} style={{ width: "100%" }}>{t('wizard.addAgent')}</button>
                    </div>
                  </div>
                </div>

                <div className="card" style={{ gap: "0.5rem" }}>
                  {agents[selectedAgentIdx] ? (
                    <>
                      <label>
                        {t('wizard.name')}
                        <TextareaAutosize
                          className="input"
                          value={agents[selectedAgentIdx].name}
                          onChange={(e) => handleAgentChange(selectedAgentIdx, "name", e.target.value)}
                          minRows={1}
                          maxRows={999}
                          style={{ resize: 'none' }}
                        />
                      </label>
                      <label>
                        {t('wizard.profile')}
                        <TextareaAutosize
                          className="input"
                          value={agents[selectedAgentIdx].profile}
                          onChange={(e) => handleAgentChange(selectedAgentIdx, "profile", e.target.value)}
                          minRows={2}
                          maxRows={999}
                          style={{ resize: 'none' }}
                        />
                      </label>
                      <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button type="button" className="button button-danger" onClick={() => handleRemoveAgent(selectedAgentIdx)} disabled={agents.length <= 1}>
                          {t('wizard.deleteAgent') || 'Delete agent'}
                        </button>
                      </div>
                      {currentScene && (
                        <div>
                          <div style={{ color: "var(--muted)", fontSize: "0.85rem", marginBottom: "0.25rem" }}>{t('wizard.basicActions') || 'Basic actions'}</div>
                          <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
                            {(currentScene.basic_actions || []).filter((a) => a !== 'yield').map((a) => (
                              <span key={a} className="card" style={{ padding: "0.2rem 0.4rem", fontSize: "0.85rem" }}>{a}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {currentScene && (
                        <div>
                          <div style={{ color: "var(--muted)", fontSize: "0.85rem", margin: "0.25rem 0" }}>{t('wizard.allowedActions') || 'Allowed actions'}</div>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.35rem" }}>
                            {(currentScene.allowed_actions || []).map((action) => (
                              <label key={action} style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                                <input
                                  type="checkbox"
                                  className="checkbox"
                                  checked={(agents[selectedAgentIdx].action_space || []).includes(action)}
                                  onChange={(e) => {
                                    const checked = e.target.checked;
                                    setAgents((prev) => prev.map((ag, i) => i === selectedAgentIdx ? {
                                      ...ag,
                                      action_space: checked ? [...(ag.action_space || []), action] : (ag.action_space || []).filter((a) => a !== action)
                                    } : ag));
                                  }}
                                />
                                <span>{action}</span>
                              </label>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div style={{ color: "#94a3b8" }}>{t('wizard.selectAgent') || 'Select an agent'}</div>
                  )}
                </div>
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
      </div>
    </div >
  );
}
