import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { JSX } from "react";
import { useParams } from "react-router-dom";
import ReactFlow, { Background, Controls, MiniMap, type Edge as RFEdge, type Node as RFNode } from "reactflow";
import { graphlib, layout } from "dagre";
import "reactflow/dist/style.css";

import { apiClient } from "../api/client";
import {
  AgentInfo,
  Graph,
  SimEvent,
  connectNodeEvents,
  connectTreeEvents,
  getSimEvents,
  getSimState,
  getTreeGraph,
  treeAdvanceChain,
  treeAdvanceFrontier,
  treeAdvanceMulti,
  treeBranchPublic,
  treeDeleteSubtree,
} from "../api/simulationTree";
import { useAuthStore } from "../store/auth";
import { useTranslation } from "react-i18next";
import { AppSelect } from "../components/AppSelect";

type Simulation = {
  id: string;
  name: string;
  status: string;
  scene_type: string;
  latest_state?: Record<string, unknown> | null;
};

// SimEvent type is provided by ../api/simulationTree

type ToastMessage = {
  id: number;
  text: string;
};

// WS helpers are provided by ../api/simulationTree

export function SimulationPage() {
  const params = useParams();
  const simulationSlug = (params.id ?? "").toUpperCase();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((state) => state.accessToken);
  const { t } = useTranslation();

  const treeWsRef = useRef<WebSocket | null>(null);
  const nodeWsRef = useRef<WebSocket | null>(null);
  const treeIdRef = useRef<string | null>(null);
  const selectedRef = useRef<number | null>(null);

  const [graph, setGraph] = useState<Graph | null>(null);
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [turns, setTurns] = useState<number>(0);
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [eventsAutoScroll, setEventsAutoScroll] = useState(true);
  const [agentsAutoScroll, setAgentsAutoScroll] = useState(true);

  // Resizable columns
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [colWidths, setColWidths] = useState<[number, number, number]>([33, 34, 33]);
  const gridCols = `${colWidths[0]}fr 2px ${colWidths[1]}fr 2px ${colWidths[2]}fr`;
  const dragRef = useRef<{ index: 0 | 1; startX: number; widths: [number, number, number] } | null>(null);
  const minPct = 15;

  const onResizerMouseDown = (index: 0 | 1, event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragRef.current = { index, startX: event.clientX, widths: [...colWidths] as [number, number, number] };
    document.addEventListener("mousemove", onDragMove);
    document.addEventListener("mouseup", onDragEnd);
    document.body.style.cursor = "col-resize";
    (document.body.style as any).userSelect = "none";
  };

  const onDragMove = (ev: MouseEvent) => {
    const d = dragRef.current;
    const el = containerRef.current;
    if (!d || !el) return;
    const rect = el.getBoundingClientRect();
    const total = rect.width || 1;
    const deltaPx = ev.clientX - d.startX;
    const deltaPct = (deltaPx / total) * 100;
    let [w0, w1, w2] = d.widths;
    if (d.index === 0) {
      const sum = w0 + w1;
      let nw0 = Math.max(minPct, Math.min(sum - minPct, w0 + deltaPct));
      let nw1 = sum - nw0;
      setColWidths([nw0, nw1, w2]);
    } else {
      const sum = w1 + w2;
      let nw1 = Math.max(minPct, Math.min(sum - minPct, w1 + deltaPct));
      let nw2 = sum - nw1;
      setColWidths([w0, nw1, nw2]);
    }
  };

  const onDragEnd = () => {
    dragRef.current = null;
    document.removeEventListener("mousemove", onDragMove);
    document.removeEventListener("mouseup", onDragEnd);
    document.body.style.cursor = "";
    (document.body.style as any).userSelect = "";
  };

  const eventsRef = useRef<HTMLDivElement | null>(null);
  const agentRef = useRef<HTMLDivElement | null>(null);

  const [multiTurns, setMultiTurns] = useState("1");
  const [multiCount, setMultiCount] = useState("2");
  const [chainTurns, setChainTurns] = useState("5");
  const [frontierTurns, setFrontierTurns] = useState("1");
  const [broadcastText, setBroadcastText] = useState("(announcement)");

  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const toastSeq = useRef(0);

  const simulationQuery = useQuery({
    queryKey: ["simulation", simulationSlug],
    enabled: simulationSlug.length > 0,
    queryFn: async () => {
      const response = await apiClient.get<Simulation>(`/simulations/${simulationSlug}`);
      return response.data;
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/simulations/${simulationSlug}/save`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simulation", simulationSlug, "snapshots"] });
      queryClient.invalidateQueries({ queryKey: ["simulation", simulationSlug] });
    },
  });

  const addToast = useCallback((text: string) => {
    const id = ++toastSeq.current;
    setToasts((prev) => [...prev, { id, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 4000);
  }, []);

  const multiTurnsNum = Math.max(1, parseInt(multiTurns || "1", 10) || 1);
  const multiCountNum = Math.max(1, parseInt(multiCount || "2", 10) || 1);
  const chainTurnsNum = Math.max(1, parseInt(chainTurns || "5", 10) || 1);
  const frontierTurnsNum = Math.max(1, parseInt(frontierTurns || "1", 10) || 1);

  const closeTreeWs = useCallback(() => {
    if (treeWsRef.current) {
      treeWsRef.current.close();
      treeWsRef.current = null;
    }
  }, []);

  const closeNodeWs = useCallback(() => {
    if (nodeWsRef.current) {
      nodeWsRef.current.close();
      nodeWsRef.current = null;
    }
  }, []);

  const refreshSelected = useCallback(async (treeOverride?: string | null, nodeOverride?: number | null) => {
    const tree = treeOverride ?? treeIdRef.current;
    const node = nodeOverride ?? selectedRef.current;
    if (tree == null || node == null) return;
    const [logs, state] = await Promise.all([getSimEvents(tree, node), getSimState(tree, node)]);
    setEvents(logs || []);
    setAgents(state.agents || []);
    setTurns(state.turns || 0);
    const agentNames = (state.agents || []).map((agent) => agent.name);
    setSelectedAgent((prev) => (prev && agentNames.includes(prev) ? prev : agentNames[0] || ""));
  }, []);

  const connectNodeWs = useCallback(
    (tree: string, node: number | null) => {
      closeNodeWs();
      if (node == null) {
        return;
      }
      const ws = connectNodeEvents(tree, node, accessToken, (payload: SimEvent) => {
        if (payload.type === "agent_ctx_delta") {
          const data = payload.data ?? {};
          const agentName = String(data.agent ?? "");
          const role = String(data.role ?? "");
          const content = String(data.content ?? "");
          setAgents((prev) => {
            const idx = prev.findIndex((agent) => agent.name === agentName);
            if (idx === -1) return prev;
            const copy = [...prev];
            const target = copy[idx]!;
            const memory = Array.isArray(target.short_memory) ? target.short_memory : [];
            copy[idx] = { ...target, short_memory: [...memory, { role, content }] };
            return copy;
          });
          return;
        }
        if (payload.type === "emotion_update") {
          const data = payload.data ?? {};
          const agentName = String(data.agent ?? "");
          const emotion = String(data.emotion ?? "");
          setAgents((prev) => {
            const idx = prev.findIndex((agent) => agent.name === agentName);
            if (idx === -1) return prev;
            const copy = [...prev];
            const target = copy[idx]!;
            copy[idx] = { ...target, emotion } as any;
            return copy;
          });
          setEvents((prev) => [...prev, payload]);
          return;
        }
        if (payload.type === "plan_update") {
          const data = payload.data ?? {};
          const agentName = String(data.agent ?? "");
          const plan = (data.plan ?? {}) as any;
          setAgents((prev) => {
            const idx = prev.findIndex((agent) => agent.name === agentName);
            if (idx === -1) return prev;
            const copy = [...prev];
            const target = copy[idx]!;
            copy[idx] = { ...target, plan_state: plan } as any;
            return copy;
          });
          setEvents((prev) => [...prev, payload]);
          return;
        }
        setEvents((prev) => [...prev, payload]);
      });
      nodeWsRef.current = ws;
    },
    [accessToken, closeNodeWs],
  );

  const onTreeWsMessage = useCallback(
    (ev: MessageEvent) => {
      const message = JSON.parse(ev.data);
      setGraph((current) => {
        const data = message.data ?? {};
        if (!current) {
          if (message.type === "attached") {
            const node = Number(data.node);
            const depth = Number(data.depth ?? 0);
            return { root: node, frontier: [], nodes: [{ id: node, depth }], edges: [], running: [] };
          }
          return current;
        }

        if (message.type === "attached") {
          const node = Number(data.node);
          const parentVal = data.parent;
          const parent = parentVal == null ? null : Number(parentVal);
          const depth = Number(data.depth ?? 0);
          const edgeType = String(data.edge_type ?? "advance");
          const nodes = current.nodes.some((n) => n.id === node)
            ? current.nodes
            : [...current.nodes, { id: node, depth }];
          const edges = parent == null ? current.edges : [...current.edges, { from: parent, to: node, type: edgeType }];
          if (selectedRef.current === node) {
            refreshSelected(treeIdRef.current, node);
          }
          return { ...current, nodes, edges };
        }

        if (message.type === "run_start") {
          const node = Number(data.node);
          const running = new Set(current.running || []);
          running.add(node);
          addToast(`Node ${node} started`);
          return { ...current, running: Array.from(running) };
        }

        if (message.type === "run_finish") {
          const node = Number(data.node);
          const running = new Set(current.running || []);
          running.delete(node);
          addToast(`Node ${node} finished`);
          if (selectedRef.current === node) refreshSelected(treeIdRef.current, node);
          return { ...current, running: Array.from(running) };
        }

        if (message.type === "deleted") {
          const rootDel = Number(data.node);
          if (selectedRef.current === rootDel) {
            setEvents([]);
            setAgents([]);
            setSelectedAgent("");
          }
          const toDelete = new Set<number>();
          const children = new Map<number, number[]>();
          for (const edge of current.edges) {
            if (!children.has(edge.from)) children.set(edge.from, []);
            children.get(edge.from)!.push(edge.to);
          }
          const stack = [rootDel];
          while (stack.length) {
            const next = stack.pop()!;
            if (toDelete.has(next)) continue;
            toDelete.add(next);
            const ch = children.get(next) || [];
            for (const child of ch) stack.push(child);
          }
          const nodes = current.nodes.filter((node) => !toDelete.has(node.id));
          const edges = current.edges.filter((edge) => !toDelete.has(edge.from) && !toDelete.has(edge.to));
          const running = (current.running || []).filter((node) => !toDelete.has(node));
          if (current?.root && toDelete.has(current.root)) {
            setSelectedNode(null);
            selectedRef.current = null;
          }
          return { ...current, nodes, edges, running };
        }

        return current;
      });
      // Side-effects outside setGraph: auto-focus newest attached node
      if (message.type === "attached") {
        const data = message.data ?? {};
        const node = Number(data.node);
        if (!Number.isNaN(node)) {
          setSelectedNode(node);
          selectedRef.current = node;
          const tree = treeIdRef.current;
          if (tree != null) {
            refreshSelected(tree, node);
            connectNodeWs(tree, node);
          }
        }
      }
    },
    [addToast, refreshSelected, connectNodeWs],
  );

  const connectToTree = useCallback(
    async (id: string) => {
      closeTreeWs();
      closeNodeWs();
      setGraph(null);
      setSelectedNode(null);
      treeIdRef.current = id;

      const fetchWithRetry = async () => {
        for (let attempt = 0; attempt < 6; attempt += 1) {
          const g = await getTreeGraph(id);
          if (g) return g;
          await new Promise((resolve) => setTimeout(resolve, 300));
        }
        return null;
      };

      const initialGraph = await fetchWithRetry();
      if (initialGraph) {
        setGraph(initialGraph);
        const rootNode = initialGraph.root ?? null;
        setSelectedNode(rootNode);
        selectedRef.current = rootNode;
        if (typeof rootNode === "number") {
          const numericRoot = rootNode as number;
          refreshSelected(id, numericRoot);
          connectNodeWs(id, numericRoot);
        }
      }

      const ws = connectTreeEvents(id, accessToken, (ev) => onTreeWsMessage({ data: JSON.stringify(ev) } as MessageEvent));
      treeWsRef.current = ws;
    },
    [accessToken, closeNodeWs, closeTreeWs, connectNodeWs, onTreeWsMessage, refreshSelected],
  );

  useEffect(() => {
    if (simulationSlug) {
      treeIdRef.current = simulationSlug;
      connectToTree(simulationSlug);
    } else {
      treeIdRef.current = null;
    }
  }, [connectToTree, simulationSlug]);

  useEffect(() => () => {
    closeTreeWs();
    closeNodeWs();
  }, [closeNodeWs, closeTreeWs]);

  useEffect(() => {
    selectedRef.current = selectedNode;
  }, [selectedNode]);

  useEffect(() => {
    if (eventsAutoScroll && eventsRef.current) {
      const el = eventsRef.current;
      el.scrollTop = el.scrollHeight;
    }
  }, [events, eventsAutoScroll]);

  useEffect(() => {
    if (agentsAutoScroll && agentRef.current) {
      const el = agentRef.current;
      el.scrollTop = el.scrollHeight;
    }
  }, [agents, selectedAgent, agentsAutoScroll]);

  useEffect(() => {
    const tree = treeIdRef.current;
    if (tree != null && typeof selectedNode === "number") {
      const node = selectedNode as number;
      refreshSelected(tree, node);
      connectNodeWs(tree, node);
    }
  }, [connectNodeWs, refreshSelected, selectedNode]);

  const rfGraph = useMemo(() => {
    if (!graph) return { nodes: [] as RFNode[], edges: [] as RFEdge[] };
    const dagreGraph = new graphlib.Graph();
    dagreGraph.setGraph({ rankdir: "TB", nodesep: 30, ranksep: 60 });
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    const WIDTH = 28;
    const HEIGHT = 28;

    for (const node of graph.nodes) {
      dagreGraph.setNode(String(node.id), { width: WIDTH, height: HEIGHT });
    }
    for (const edge of graph.edges) {
      dagreGraph.setEdge(String(edge.from), String(edge.to));
    }
    layout(dagreGraph);

    const parentSet = new Set(graph.edges.map((edge) => edge.from));
    const running = new Set(graph.running || []);

    const rfNodes: RFNode[] = graph.nodes.map((node) => {
      const pos = dagreGraph.node(String(node.id));
      const isLeaf = !parentSet.has(node.id);
      const isSelected = selectedNode === node.id;
      const background = node.id === graph.root ? "#67a6ff" : isLeaf ? "#7ac68d" : "#ffffff";
      return {
        id: String(node.id),
        data: { label: String(node.id) },
        position: { x: pos.x - WIDTH / 2, y: pos.y - HEIGHT / 2 },
        style: {
          width: WIDTH,
          height: HEIGHT,
          borderRadius: 14,
          border: isSelected ? "2px solid #fb7185" : "1px solid #94a3b8",
          background,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 11,
          fontWeight: 600,
          color: "#1f2933",
          animation: running.has(node.id) ? "simulation-running 0.9s ease-in-out infinite" : undefined,
        },
      } satisfies RFNode;
    });

    const colorByType = (type: string) => {
      switch (type) {
        case "advance":
          return "#1f2933";
        case "agent_ctx":
          return "#15803d";
        case "agent_plan":
          return "#ea580c";
        case "agent_props":
          return "#6d28d9";
        case "scene_state":
          return "#7c2d12";
        case "public_event":
          return "#1d4ed8";
        default:
          return "#64748b";
      }
    };

    const rfEdges: RFEdge[] = graph.edges.map((edge) => ({
      id: `e${edge.from}-${edge.to}`,
      source: String(edge.from),
      target: String(edge.to),
      style: { stroke: colorByType(edge.type) },
    }));

    return { nodes: rfNodes, edges: rfEdges };
  }, [graph, selectedNode]);

  const agentMessages = useMemo(() => {
    if (!selectedAgent) return [] as { role: string; content: string }[];
    const agent = agents.find((a) => a.name === selectedAgent);
    const memory = agent?.short_memory ?? [];
    return memory.map((entry) => ({ role: String(entry.role ?? ""), content: String(entry.content ?? "") }));
  }, [agents, selectedAgent]);

  const selectedAgentInfo = useMemo(() => agents.find((a) => a.name === selectedAgent), [agents, selectedAgent]);
  const selectedEmotion = selectedAgentInfo?.emotion || "neutral";
  const selectedPlan = selectedAgentInfo?.plan_state as any;

  const formattedEvents = useMemo(() => {
    return (events || []).map((event, idx) => formatEvent(event, idx, t)).filter(Boolean) as JSX.Element[];
  }, [events, t]);

  if (!simulationSlug) {
    return <div className="panel">{t('sim.invalidId')}</div>;
  }

  return (
    <>
      <style>{`
        @keyframes simulation-running {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
      `}</style>
      <main className="app-main" style={{ display: "grid", gridTemplateRows: "auto 1fr", height: "100%", minHeight: 0, rowGap: "0.5rem" }}>
        <div className="panel compact-panel" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexDirection: "row" }}>
          <div>
            <div className="panel-title">{simulationQuery.data?.name ?? t('brand')}</div>
            <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
              {simulationQuery.isFetching ? t('sim.syncing') : `${t('sim.status')}: ${simulationQuery.data?.status ?? "unknown"}`}
            </div>
          </div>
          <div style={{ display: "flex", gap: "0.35rem" }}>
            <button
              type="button"
              className="button small"
              onClick={() => queryClient.invalidateQueries({ queryKey: ["simulation", simulationSlug] })}
            >
              {t('sim.refreshMeta')}
            </button>
            <button
              type="button"
              className="button small"
              onClick={() => refreshSelected()}
              disabled={treeIdRef.current == null || selectedNode == null}
            >
              {t('sim.refreshNode')}
            </button>
            <button
              type="button"
              className="button small"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? t('sim.saving') : t('sim.saveSnapshot')}
            </button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: gridCols, width: "100%", height: "100%", minHeight: 0 }} ref={containerRef}>
          <section className="panel compact-panel" style={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%" }}>
            <div className="panel-title">{t('sim.tree')}</div>
            <div className="card" style={{ flex: 1, minHeight: 0, padding: 0, overflow: "hidden", position: "relative" }}>
              <ReactFlow
                style={{ width: "100%", height: "100%" }}
                nodes={rfGraph.nodes}
                edges={rfGraph.edges}
                fitView
                onNodeClick={(_, node) => {
                  const parsed = Number(node.id);
                  if (!Number.isNaN(parsed)) {
                    setSelectedNode(parsed);
                    selectedRef.current = parsed;
                  }
                }}
              >
                {(() => {
                  const root = typeof document !== 'undefined' ? document.documentElement : null;
                  const cs = root ? getComputedStyle(root) : null;
                  const panel = (cs?.getPropertyValue('--panel') || '').trim() || 'rgba(255,255,255,0.9)';
                  const muted = (cs?.getPropertyValue('--muted') || '').trim() || '#475569';
                  const accentB = (cs?.getPropertyValue('--accent-b') || '').trim() || '#6366f1';
                  return (
                    <>
                      <MiniMap
                        pannable
                        zoomable
                        maskColor={panel}
                        nodeColor={() => muted}
                        nodeStrokeColor={accentB}
                      />
                      <Controls className="rf-controls" position="bottom-left" />
                    </>
                  );
                })()}
                <Background />
              </ReactFlow>
              {graph && (
                <div
                  style={{
                    position: "absolute",
                    top: 8,
                    left: 8,
                    fontSize: "0.8rem",
                    background: "var(--panel)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: "0.2rem 0.5rem",
                    opacity: 0.95,
                    whiteSpace: "nowrap",
                    pointerEvents: "none",
                  }}
                >
                  {t('sim.selectedNode')}: {selectedNode ?? "-"}
                  {" · "}{t('sim.nodes')}: {graph.nodes.length}
                  {" · "}{t('sim.edges')}: {graph.edges.length}
                  {" · "}{t('sim.running')}: {(graph.running || []).length}
                  {" · "}{t('sim.turnsAt')}: {turns}
                </div>
              )}
            </div>
            <div className="card" style={{ marginTop: "0.5rem", display: "grid", gap: "0.5rem" }}>
              <div>
                <div className="panel-subtitle">{t('sim.frontier')}</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "0.35rem", alignItems: "center" }}>
                  <input
                    className="input small"
                    type="number"
                    min={1}
                    value={frontierTurns}
                    onChange={(event) => setFrontierTurns(event.target.value)}
                  />
                  <button
                    type="button"
                    className="button small"
                    onClick={async () => {
                      const tree = treeIdRef.current;
                      if (tree == null) return;
                      await treeAdvanceFrontier(tree, frontierTurnsNum);
                      await refreshSelected();
                    }}
                    disabled={treeIdRef.current == null}
                  >
                    {t('sim.run')}
                  </button>
                </div>
              </div>

              <div>
                <div className="panel-subtitle">{t('sim.parallel')}</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "0.35rem", alignItems: "center" }}>
                  <input className="input small" type="number" min={1} value={multiTurns} onChange={(event) => setMultiTurns(event.target.value)} />
                  <input className="input small" type="number" min={1} value={multiCount} onChange={(event) => setMultiCount(event.target.value)} />
                  <button
                    type="button"
                    className="button small"
                    onClick={async () => {
                      const tree = treeIdRef.current;
                      if (tree == null || selectedNode == null) return;
                      await treeAdvanceMulti(tree, selectedNode, multiTurnsNum, multiCountNum);
                      await refreshSelected(tree, selectedNode);
                    }}
                    disabled={treeIdRef.current == null || selectedNode == null}
                  >
                    {t('sim.run')}
                  </button>
                </div>
              </div>

              <div>
                <div className="panel-subtitle">{t('sim.chain')}</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "0.35rem", alignItems: "center" }}>
                  <input className="input small" type="number" min={1} value={chainTurns} onChange={(event) => setChainTurns(event.target.value)} />
                  <button
                    type="button"
                    className="button small"
                    onClick={async () => {
                      const tree = treeIdRef.current;
                      if (tree == null || selectedNode == null) return;
                      await treeAdvanceChain(tree, selectedNode, chainTurnsNum);
                      await refreshSelected(tree, selectedNode);
                    }}
                    disabled={treeIdRef.current == null || selectedNode == null}
                  >
                    {t('sim.run')}
                  </button>
                </div>
              </div>

              <div>
                <div className="panel-subtitle">{t('sim.broadcast')}</div>
                <textarea className="input" value={broadcastText} onChange={(event) => setBroadcastText(event.target.value)} rows={2} />
                <button
                  type="button"
                  className="button"
                  onClick={async () => {
                    const tree = treeIdRef.current;
                    if (tree == null || selectedNode == null) return;
                    await treeBranchPublic(tree, selectedNode, broadcastText);
                    await refreshSelected(tree, selectedNode);
                  }}
                  disabled={treeIdRef.current == null || selectedNode == null}
                >
                  {t('sim.apply')}
                </button>
              </div>

              <div>
                <div className="panel-subtitle">{t('sim.deleteSubtree')}</div>
                <button
                  type="button"
                  className="button button-danger small"
                  onClick={async () => {
                    const tree = treeIdRef.current;
                    if (tree == null || selectedNode == null || !graph || selectedNode === graph.root) return;
                    await treeDeleteSubtree(tree, selectedNode);
                    await refreshSelected();
                  }}
                  disabled={!graph || selectedNode == null || (graph && selectedNode === graph.root)}
                >
                  {t('sim.delete')}
                </button>
              </div>
            </div>
          </section>

          <div className="resizer" onMouseDown={(e) => onResizerMouseDown(0, e)} />

          <section className="panel compact-panel" style={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%" }}>
            <div className="panel-title" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>{t('sim.events')}</span>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem" }}>
                <input type="checkbox" checked={eventsAutoScroll} onChange={(event) => setEventsAutoScroll(event.target.checked)} />
                {t('sim.autoScroll')}
              </label>
            </div>
            <div
              ref={eventsRef}
              className="card scroll-panel"
              style={{
                flex: 1,
                minHeight: 0,
                overflow: "auto",
                padding: "0.75rem",
                wordBreak: "break-word",
                overflowWrap: "anywhere",
                whiteSpace: "pre-wrap",
              }}
            >
              {formattedEvents.length ? formattedEvents : <div style={{ color: "#94a3b8" }}>{t('sim.noEvents')}</div>}
            </div>
          </section>

          <div className="resizer" onMouseDown={(e) => onResizerMouseDown(1, e)} />

          <section className="panel compact-panel" style={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%" }}>
            <div className="panel-title" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>{t('sim.agents')}</span>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem" }}>
                <input type="checkbox" checked={agentsAutoScroll} onChange={(event) => setAgentsAutoScroll(event.target.checked)} />
                {t('sim.autoScroll')}
              </label>
            </div>
            <AppSelect
              options={agents.map((agent) => ({ value: agent.name, label: agent.name }))}
              value={selectedAgent}
              placeholder={t('sim.noAgents')}
              onChange={setSelectedAgent}
              size="small"
            />
            <div className="card" style={{ marginTop: "0.5rem", padding: "0.5rem 0.6rem", display: "grid", gap: "0.25rem" }}>
              <div className="panel-subtitle" style={{ margin: 0 }}>{t('sim.agentStatus.title')}</div>
              {(() => {
                const plan: any = selectedPlan;
                const goals = Array.isArray(plan?.goals) ? plan.goals : [];
                const milestones = Array.isArray(plan?.milestones) ? plan.milestones : [];
                const goalsText = goals.length
                  ? goals
                      .map((g: any) => `[${String(g.id)}] ${String(g.desc)} (${t('sim.agentStatus.priority')}: ${String(g.priority)}, ${t('sim.status').toLowerCase()}: ${String(g.status)})`)
                      .join(' · ')
                  : t('common.none');
                const msText = milestones.length
                  ? milestones.map((m: any) => `[${String(m.id)}] ${String(m.desc)} (${t('sim.status')}: ${String(m.status)})`).join(' · ')
                  : t('common.none');
                const cellLabel = { color: 'var(--muted)', fontSize: '0.8rem', whiteSpace: 'nowrap' } as const;
                const gridStyle = { display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: '0.5rem', rowGap: '0.2rem', alignItems: 'baseline', fontSize: '0.9rem', lineHeight: 1.25 } as const;
                return (
                  <div style={gridStyle}>
                    <div style={cellLabel}>{t('sim.agentStatus.emotion')}</div>
                    <div>{String(selectedEmotion)}</div>
                    <div style={cellLabel}>{t('sim.agentStatus.goals')}</div>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{goalsText}</div>
                    <div style={cellLabel}>{t('sim.agentStatus.milestones')}</div>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{msText}</div>
                    <div style={cellLabel}>{t('sim.agentStatus.strategy')}</div>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{String(plan?.strategy || '') || t('common.none')}</div>
                    <div style={cellLabel}>{t('sim.agentStatus.notes')}</div>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{String(plan?.notes || '') || t('common.none')}</div>
                  </div>
                );
              })()}
            </div>
            <div
              ref={agentRef}
              className="card scroll-panel"
              style={{
                flex: 1,
                minHeight: 0,
                overflow: "auto",
                padding: "0.75rem",
                wordBreak: "break-word",
                overflowWrap: "anywhere",
                whiteSpace: "pre-wrap",
              }}
            >
              {agentMessages.length ? (
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {agentMessages.map((message, index) => (
                    <li key={`${message.role}-${index}`} style={{ wordBreak: "break-word", overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>
                      <span style={{ color: "#94a3b8" }}>[{message.role}]</span> {message.content}
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: "#94a3b8" }}>{t('sim.noAgentMsgs')}</div>
              )}
            </div>
          </section>
        </div>

        <div style={{ position: "fixed", bottom: "1.5rem", right: "1.5rem", display: "flex", flexDirection: "column", gap: "0.75rem", zIndex: 1000 }}>
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className="card"
              style={{
                padding: "0.75rem 1rem",
                background: "var(--overlay-bg)",
                border: "1px solid rgba(148,163,184,0.4)",
                boxShadow: "0 12px 24px rgba(15,23,42,0.32)",
                color: "#e2e8f0",
                minWidth: "220px",
                backdropFilter: "blur(var(--overlay-blur))",
                WebkitBackdropFilter: "blur(var(--overlay-blur))",
              }}
            >
              {toast.text}
            </div>
          ))}
        </div>
      </main>
    </>
  );
}

// (Radix-based AppSelect used instead of inline CompactSelect)

function formatEvent(event: SimEvent, key: number, t: (k: string) => string): JSX.Element | null {
  if (!event) return null;
  const type = event.type;
  const data = event.data ?? {};

  if (type === "system_broadcast") {
    if (data.type === "PublicEvent") {
      return (
        <div key={key} style={{ lineHeight: 1.5 }}>
          <span style={{ color: "#38bdf8", fontWeight: 600 }}>[{t('sim.eventTag') || 'Event'}]</span> {String(data.text ?? "")}
        </div>
      );
    }
    return null;
  }

  if (type === "action_end") {
    const action = (data.action ?? {}) as Record<string, unknown>;
    const actionName = String(action.action ?? "");
    if (actionName === "send_message") {
      const name = String(data.agent ?? "");
      const message = String(((data.result as Record<string, unknown> | undefined)?.message) ?? action.message ?? data.summary ?? "");
      return (
        <div key={key} style={{ lineHeight: 1.5 }}>
          <span style={{ color: "#22c55e", fontWeight: 600 }}>[{t('sim.messageTag') || 'Message'}]</span>{" "}
          <span style={{ color: "var(--text)", fontWeight: 600 }}>{name}:</span> {message}
        </div>
      );
    }
    if (actionName && actionName !== "yield") {
      return (
        <div key={key} style={{ lineHeight: 1.5 }}>
          <span style={{ color: "var(--accent-b)", fontWeight: 600 }}>[{t('sim.actionTag') || 'Action'} {actionName}]</span>{" "}
          {String(data.summary ?? "")}
        </div>
      );
    }
    return null;
  }

  if (type === "landlord_deal") {
    const bottom = (data.bottom as string[]) ?? [];
    return (
      <div key={key} style={{ lineHeight: 1.5 }}>
        <span style={{ color: "#0ea5e9", fontWeight: 600 }}>[{t('sim.dealTag') || 'Deal'}]</span> {t('sim.bottom') || 'Bottom'}: {bottom.join(" ")}
      </div>
    );
  }

  return null;
}
