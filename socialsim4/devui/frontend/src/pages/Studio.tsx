import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import ReactFlow, { Background, Controls, MiniMap, type Node as RFNode, type Edge as RFEdge } from 'reactflow'
import * as Toast from '@radix-ui/react-toast'
import { graphlib, layout } from 'dagre'
import 'reactflow/dist/style.css'

import {
  createTree,
  getTreeGraph,
  treeAdvanceFrontier,
  treeAdvanceMulti,
  treeBranchPublic,
  treeDeleteSubtree,
  getSimEvents,
  getSimState,
  Graph,
  listTrees,
} from '../api/client'

export default function Studio() {
  const params = useParams()
  const navigate = useNavigate()

  const [treeId, setTreeId] = useState<number | null>(null)
  const [trees, setTrees] = useState<{ id: number; root: number }[]>([])
  const [graph, setGraph] = useState<Graph | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Events/agents state for selected node
  const [events, setEvents] = useState<any[]>([])
  const [agents, setAgents] = useState<{ name: string; role?: string; plan_state: any; short_memory: { role: string; content: string }[] }[]>([])
  const [turns, setTurns] = useState<number>(0)
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [stickBottom, setStickBottom] = useState(true)
  const eventsRef = useRef<HTMLDivElement | null>(null)
  const agentRef = useRef<HTMLDivElement | null>(null)

  // Ops state
  const [multiTurns, setMultiTurns] = useState<string>('1')
  const [multiCount, setMultiCount] = useState<string>('2')
  const [text, setText] = useState('(announcement)')
  const multiTurnsNum = Math.max(1, parseInt(multiTurns || '1', 10) || 1)
  const multiCountNum = Math.max(1, parseInt(multiCount || '2', 10) || 1)

  // Toasts
  const [toasts, setToasts] = useState<{ id: number; text: string }[]>([])
  const toastSeq = useRef(0)
  function addToast(text: string) {
    const id = ++toastSeq.current
    setToasts((ts) => [...ts, { id, text }])
    setTimeout(() => setToasts((ts) => ts.filter((t) => t.id !== id)), 2500)
  }

  // Format backend event for middle panel
  function formatEvent(it: any, idx: number): JSX.Element | null {
    if (!it) return null
    const t = it.type
    const d = it.data || {}
    if (t === 'system_broadcast') {
      if (d.type === 'PublicEvent') {
        return (
          <div key={idx} className="event-line">
            <span className="event-label" style={{ color: '#2563eb' }}>[Event]</span>{' '}
            {String(d.text || '')}
          </div>
        )
      }
      return null
    }
    if (t === 'action_end') {
      const action = d.action || {}
      if (action.action === 'send_message') {
        const name = String(d.agent || '')
        const msg = String((d.result && d.result.message) || action.message || d.summary || '')
        return (
          <div key={idx} className="event-line">
            <span className="event-label" style={{ color: '#059669' }}>[Action]</span>{' '}
            <span style={{ color: 'var(--brand)', fontWeight: 600 }}>{name}:</span>{' '}
            {msg}
          </div>
        )
      }
      return null
    }
    return null
  }

  // Scroll to bottom behavior
  useEffect(() => {
    if (stickBottom && eventsRef.current) {
      const el = eventsRef.current
      el.scrollTop = el.scrollHeight
    }
  }, [events, stickBottom])
  useEffect(() => {
    if (stickBottom && agentRef.current) {
      const el = agentRef.current
      el.scrollTop = el.scrollHeight
    }
  }, [selectedAgent, agents, stickBottom])

  async function create() {
    const r = await createTree()
    localStorage.setItem('devui:lastTreeId', String(r.id))
    navigate(`/studio/${r.id}`)
    await connectToTree(r.id)
    await refreshTrees()
  }

  async function refreshGraph() {
    if (treeId == null) return
    const g = await getTreeGraph(treeId)
    if (g) setGraph(g)
  }

  async function refreshSelected() {
    if (treeId == null || selected == null) return
    const logs = await getSimEvents(treeId, selected)
    const st = await getSimState(treeId, selected)
    setEvents(logs || [])
    setAgents(st.agents || [])
    setTurns(st.turns || 0)
    const nms = (st.agents || []).map((a) => a.name)
    setSelectedAgent((prev) => (prev && nms.includes(prev) ? prev : (nms[0] || '')))
  }

  function onWsMessage(ev: MessageEvent) {
    const msg = JSON.parse(ev.data)
    setGraph((g) => {
      if (!g) {
        if (msg.type === 'attached') {
          const d = msg.data || {}
          const node = Number(d.node)
          const depth = Number(d.depth)
          return { root: node, frontier: [], nodes: [{ id: node, depth }], edges: [], running: [] }
        }
        return g
      }
      const type = msg.type
      const d = msg.data || {}
      if (type === 'attached') {
        const node = Number(d.node)
        const parentVal = d.parent
        const parent = (parentVal === null || parentVal === undefined) ? null : Number(parentVal)
        const depth = Number(d.depth)
        const edge_type = String(d.edge_type || 'advance')
        const nodes = g.nodes.some((n) => n.id === node) ? g.nodes : [...g.nodes, { id: node, depth }]
        const edges = parent == null ? g.edges : [...g.edges, { from: parent, to: node, type: edge_type }]
        // If the new node is our current selection, refresh its events
        if (selected !== null && node === selected) refreshSelected()
        return { ...g, nodes, edges }
      }
      if (type === 'run_start') {
        const node = Number(d.node)
        const running = new Set(g.running || [])
        running.add(node)
        addToast(`Node ${node} started`)
        return { ...g, running: Array.from(running) }
      }
      if (type === 'run_finish') {
        const node = Number(d.node)
        const running = new Set(g.running || [])
        running.delete(node)
        addToast(`Node ${node} finished`)
        if (selected !== null && node === selected) refreshSelected()
        return { ...g, running: Array.from(running) }
      }
      if (type === 'deleted') {
        const rootDel = Number(d.node)
        if (selected !== null && rootDel === selected) {
          // Clear middle/right if the selected node got deleted
          setEvents([])
          setAgents([])
          setSelectedAgent('')
        }
        const toDelete = new Set<number>()
        const children = new Map<number, number[]>()
        for (const e of g.edges) {
          if (!children.has(e.from)) children.set(e.from, [])
          children.get(e.from)!.push(e.to)
        }
        const stack = [rootDel]
        while (stack.length) {
          const cur = stack.pop()!
          if (toDelete.has(cur)) continue
          toDelete.add(cur)
          const ch = children.get(cur) || []
          for (const c of ch) stack.push(c)
        }
        const nodes = g.nodes.filter((n) => !toDelete.has(n.id))
        const edges = g.edges.filter((e) => !toDelete.has(e.from) && !toDelete.has(e.to))
        const running = (g.running || []).filter((r) => !toDelete.has(r))
        return { ...g, nodes, edges, running }
      }
      return g
    })
  }

  async function fetchGraphWithRetry(id: number, tries = 6, delayMs = 300): Promise<Graph | null> {
    for (let i = 0; i < tries; i++) {
      const g = await getTreeGraph(id)
      if (g) return g
      await new Promise((r) => setTimeout(r, delayMs))
    }
    return null
  }

  async function connectToTree(id: number) {
    setTreeId(id)
    const g = await fetchGraphWithRetry(id)
    if (!g) {
      // Graph doesn't exist yet; don't open WS
      return
    }
    setGraph(g)
    setSelected(g.root)
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    const ws = new WebSocket(`ws://localhost:8090/devui/simtree/${id}/events`)
    ws.onopen = () => ws.send('ready')
    ws.onmessage = onWsMessage
    wsRef.current = ws
  }

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  // Auto-connect on route param or last id
  useEffect(() => {
    const idStr = params.treeId || localStorage.getItem('devui:lastTreeId')
    if (!idStr) return
    const id = Number(idStr)
    if (Number.isNaN(id)) return
    connectToTree(id)
  }, [params.treeId])

  async function refreshTrees() {
    const ts = await listTrees()
    setTrees(ts)
  }

  useEffect(() => {
    refreshTrees()
  }, [])

  // Refresh middle/right when selected changes
  useEffect(() => {
    if (treeId != null && selected != null) refreshSelected()
  }, [treeId, selected])

  async function advanceFrontier() {
    if (treeId == null) return
    await treeAdvanceFrontier(treeId, 1, false)
    await refreshGraph()
  }
  async function branchPublic() {
    if (treeId == null || selected == null) return
    await treeBranchPublic(treeId, selected, text)
    await refreshGraph()
  }
  async function delSubtree() {
    if (treeId == null || selected == null) return
    if (graph && selected === graph.root) return
    await treeDeleteSubtree(treeId, selected)
    await refreshGraph()
  }

  // Compute ReactFlow nodes/edges
  const rf = useMemo(() => {
    if (!graph) return { nodes: [] as RFNode[], edges: [] as RFEdge[] }
    const g = new graphlib.Graph()
    g.setGraph({ rankdir: 'TB', nodesep: 30, ranksep: 60 })
    g.setDefaultEdgeLabel(() => ({}))
    const W = 28, H = 28
    for (const n of graph.nodes) g.setNode(String(n.id), { width: W, height: H })
    for (const e of graph.edges) g.setEdge(String(e.from), String(e.to))
    layout(g)
    const nodes: RFNode[] = []
    const edges: RFEdge[] = []
    const fromSet = new Set(graph.edges.map((e) => e.from))
    const color = (t: string) => {
      if (t === 'advance') return '#000'
      if (t === 'agent_ctx') return '#1b5e20'
      if (t === 'agent_plan') return '#e65100'
      if (t === 'agent_props') return '#5e35b1'
      if (t === 'scene_state') return '#6d4c41'
      if (t === 'public_event') return '#1e4976'
      return '#888'
    }
    for (const n of graph.nodes) {
      const pos = g.node(String(n.id))
      const isLeaf = !fromSet.has(n.id)
      const bg = n.id === graph.root ? '#69f' : isLeaf ? '#7c7' : '#fff'
      const running = (graph.running || []).includes(n.id)
      nodes.push({
        id: String(n.id),
        data: { label: String(n.id) },
        position: { x: pos.x - W / 2, y: pos.y - H / 2 },
        style: {
          width: W,
          height: H,
          borderRadius: 14,
          background: selected === n.id ? '#f66' : bg,
          border: '1px solid #999',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 11,
          animation: running ? 'pulse 1s ease-in-out infinite alternate' : undefined,
        },
      })
    }
    for (const e of graph.edges) edges.push({ id: `e${e.from}-${e.to}`, source: String(e.from), target: String(e.to), style: { stroke: color(e.type) } })
    return { nodes, edges }
  }, [graph, selected])

  // Agent delta for right panel
  const agentDelta = useMemo(() => {
    if (!selectedAgent) return [] as { role: string; content: string }[]
    const ag = agents.find((a) => a.name === selectedAgent)
    const msgs = (ag?.short_memory as any[]) || []
    return msgs.map((m: any) => ({ role: String(m.role || ''), content: String(m.content || '') }))
  }, [agents, selectedAgent])

  return (
    <Toast.Provider swipeDirection="right">
      <div className="page">
        <div className="header">
          <div className="header-inner">
            <h3 className="title">Studio</h3>
            <nav className="nav row">
              <Link to="/">首页</Link>
              <Link to={treeId != null ? `/studio/${treeId}` : '/studio'}>工作台</Link>
            </nav>
          </div>
        </div>

        <div style={{ padding: 12, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, alignItems: 'stretch', overflow: 'hidden', height: '100%', boxSizing: 'border-box' }}>
          {/* Left: Graph + Ops */}
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <h4 className="section-title">Graph</h4>
            <div className="card" style={{ width: '100%', flex: 1, minHeight: 0 }}>
              <style>{`@keyframes pulse{from{box-shadow:0 0 0 0 rgba(255,0,0,.4)}to{box-shadow:0 0 8px 4px rgba(255,0,0,.2)}}`}</style>
              <ReactFlow nodes={rf.nodes} edges={rf.edges} fitView onNodeClick={(_, n) => setSelected(Number(n.id))}>
                <MiniMap pannable zoomable />
                <Controls position="bottom-left" />
                <Background />
              </ReactFlow>
            </div>
            {graph && (
              <div className="stats">
                <div>Selected: {selected ?? '-'}</div>
                <div>Nodes: {graph.nodes.length} · Edges: {graph.edges.length} · Running: {(graph.running || []).length}</div>
              </div>
            )}
            <div className="legend" style={{ marginTop: 8 }}>
              {([
                ['advance', '#000'],
                ['agent_ctx', '#1b5e20'],
                ['agent_plan', '#e65100'],
                ['agent_props', '#5e35b1'],
                ['scene_state', '#6d4c41'],
                ['public_event', '#1e4976'],
              ] as const).map(([label, color]) => (
                <span key={label} className="badge">
                  <span className="dot" style={{ background: color }} />
                  {label}
                </span>
              ))}
            </div>

            {/* Ops */}
            <div className="card card-pad" style={{ marginTop: 8 }}>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                <CompactSelect
                  options={trees.map((t) => String(t.id))}
                  value={treeId == null ? '' : String(treeId)}
                  onOpen={refreshTrees}
                  onChange={(v) => {
                    const id = parseInt(v || '0', 10)
                    if (!Number.isNaN(id)) {
                      localStorage.setItem('devui:lastTreeId', String(id))
                      navigate(`/studio/${id}`)
                      connectToTree(id)
                    }
                  }}
                />
                <button className="btn" onClick={create}>Create</button>
                <button className="btn" onClick={refreshGraph} disabled={treeId == null}>Refresh</button>
              </div>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                <button className="btn" onClick={advanceFrontier} disabled={treeId == null}>Advance leaves</button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gridTemplateRows: 'auto auto', columnGap: 8, rowGap: 6, marginTop: 12 }}>
                <label className="label" style={{ alignSelf: 'end' }}>Multi turns</label>
                <label className="label" style={{ alignSelf: 'end' }}>Count</label>
                <label style={{ visibility: 'hidden' }}>&nbsp;</label>
                <input className="input" type="number" min={1} value={multiTurns} onChange={(e) => setMultiTurns(e.target.value)} style={{ width: '100%' }} />
                <input className="input" type="number" min={1} value={multiCount} onChange={(e) => setMultiCount(e.target.value)} style={{ width: '100%' }} />
                <div className="row" style={{ justifyContent: 'flex-end' }}>
                  <button className="btn" onClick={() => treeId != null && selected != null && treeAdvanceMulti(treeId, selected, multiTurnsNum, multiCountNum)} disabled={treeId == null || selected == null}>Advance N copies</button>
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <div className="label">public_broadcast:</div>
                <input className="input" value={text} onChange={(e) => setText(e.target.value)} style={{ width: '100%' }} />
                <button className="btn" onClick={branchPublic} style={{ marginTop: 6 }} disabled={treeId == null || selected == null}>Apply</button>
              </div>
              <div style={{ marginTop: 12 }}>
                <div className="label">Delete subtree (root disabled)</div>
                <button className="btn" onClick={delSubtree} disabled={!graph || selected == null || selected === graph.root}>Delete</button>
              </div>
            </div>
          </div>

          {/* Middle: Events */}
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <h4 className="section-title">Events</h4>
            <div ref={eventsRef} className="card card-pad scroll text-prewrap text-break" style={{ lineHeight: 1.55, flex: 1 }}>
              {(() => {
                const formatted = (events || []).map((e, i) => formatEvent(e, i)).filter(Boolean)
                return formatted.length ? formatted : <div className="muted">(no events yet)</div>
              })()}
            </div>
          </div>

          {/* Right: Agents */}
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h4 className="section-title" style={{ margin: 0 }}>Agents</h4>
              <label className="label row" style={{ gap: 6 }}>
                <input type="checkbox" checked={stickBottom} onChange={(e) => setStickBottom(e.target.checked)} />
                <span>Stick to bottom</span>
              </label>
            </div>
            <CompactSelect options={agents.map((a) => a.name)} value={selectedAgent} onChange={setSelectedAgent} />
            <div ref={agentRef} className="card card-pad scroll text-prewrap text-break" style={{ lineHeight: 1.55, flex: 1 }}>
              {agentDelta.length ? (
                <ul className="list-compact">
                  {agentDelta.map((m, i) => (
                    <li key={i}><span className="muted">[{m.role}]</span> {m.content}</li>
                  ))}
                </ul>
              ) : (
                <div className="muted">(empty)</div>
              )}
            </div>
          </div>
        </div>

        {/* Toasts */}
        <Toast.Viewport style={{ position: 'fixed', right: 16, bottom: 16, display: 'flex', flexDirection: 'column', gap: 8, zIndex: 1000 }} />
        {toasts.map((t) => (
          <Toast.Root key={t.id} duration={2500} style={{ background: 'var(--panel)', border: '0.75px solid var(--border)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)' }}>
            <Toast.Title style={{ fontSize: 12 }}>{t.text}</Toast.Title>
          </Toast.Root>
        ))}
      </div>
    </Toast.Provider>
  )
}

function CompactSelect({ options, value, onChange, onOpen }: { options: string[]; value: string; onChange: (v: string) => void; onOpen?: () => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      const el = ref.current
      if (!el) return
      const target = e.target as unknown as globalThis.Node
      if (!el.contains(target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])
  const label = value || (options[0] || '')
  return (
    <div className="select" ref={ref} style={{ marginBottom: 8 }}>
      <button
        type="button"
        className="input select-btn"
        onClick={() => setOpen((v) => { const nv = !v; if (nv && onOpen) onOpen(); return nv })}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span>{label || '(none)'}</span>
        <span className="select-caret">▾</span>
      </button>
      {open && (
        <div className="select-menu card" role="listbox">
          {options.length ? options.map((opt) => (
            <div key={opt} role="option" aria-selected={opt === value} className={"select-item" + (opt === value ? " select-item-active" : "")} onClick={() => { onChange(opt); setOpen(false) }}>
              {opt}
            </div>
          )) : (
            <div className="select-item muted" aria-disabled>无可选项</div>
          )}
        </div>
      )}
    </div>
  )
}
