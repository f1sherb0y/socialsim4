import { useEffect, useMemo, useRef, useState } from 'react'
import { createTree, getTreeGraph, treeAdvance, treeAdvanceFrontier, treeAdvanceMulti, treeAdvanceChain, treeBranchPublic, treeDeleteSubtree } from '../api/client'
import { Link, useNavigate } from 'react-router-dom'
import ReactFlow, { Background, Controls, MiniMap, Node, Edge } from 'reactflow'
import { graphlib, layout } from 'dagre'
import 'reactflow/dist/style.css'

type Graph = { root: number; frontier: number[]; running?: number[]; nodes: { id: number; depth: number }[]; edges: { from: number; to: number; type: string }[] }

export default function SimTree() {
  const navigate = useNavigate()
  const [treeId, setTreeId] = useState<number | null>(null)
  const [graph, setGraph] = useState<Graph | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [text, setText] = useState('(announcement)')
  const [wsReady, setWsReady] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const [multiTurns, setMultiTurns] = useState(1)
  const [multiCount, setMultiCount] = useState(2)
  const [chainTurns, setChainTurns] = useState(5)

  async function create() {
    const r = await createTree()
    setTreeId(r.id)
    setSelected(r.root)
    const g = await getTreeGraph(r.id)
    setGraph(g)
    // open WS
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    const ws = new WebSocket(`ws://localhost:8090/devui/simtree/${r.id}/events`)
    ws.onopen = () => {
      setWsReady(true)
      ws.send('ready')
    }
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data)
      setGraph(data)
    }
    wsRef.current = ws
  }

  async function refresh() {
    if (treeId == null) return
    const g = await getTreeGraph(treeId)
    setGraph(g)
  }

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  async function advanceSel() {
    if (treeId == null || selected == null) return
    await treeAdvance(treeId, selected, 1)
    await refresh()
  }

  async function advanceFrontier() {
    if (treeId == null) return
    await treeAdvanceFrontier(treeId, 1, false)
    await refresh()
  }

  async function branchPublic() {
    if (treeId == null || selected == null) return
    await treeBranchPublic(treeId, selected, text)
    await refresh()
  }

  async function delSubtree() {
    if (treeId == null || selected == null) return
    if (graph && selected === graph.root) return
    await treeDeleteSubtree(treeId, selected)
    // after deletion, pick root as selected
    await refresh()
    if (graph) setSelected(graph.root)
  }

  const rf = useMemo(() => {
    if (!graph) return { nodes: [] as Node[], edges: [] as Edge[] }
    const g = new graphlib.Graph()
    g.setGraph({ rankdir: 'TB', nodesep: 30, ranksep: 60 })
    g.setDefaultEdgeLabel(() => ({}))
    const W = 40, H = 40
    for (const n of graph.nodes) g.setNode(String(n.id), { width: W, height: H })
    for (const e of graph.edges) g.setEdge(String(e.from), String(e.to))
    layout(g)

    const nodes: Node[] = []
    const edges: Edge[] = []
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
      const bg = n.id === graph.root ? '#69f' : graph.frontier.includes(n.id) ? '#7c7' : '#fff'
      const running = (graph.running || []).includes(n.id)
      nodes.push({
        id: String(n.id),
        data: { label: String(n.id) },
        position: { x: pos.x - W / 2, y: pos.y - H / 2 },
        style: {
          width: W,
          height: H,
          borderRadius: 20,
          background: selected === n.id ? '#f66' : bg,
          border: '1px solid #999',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          animation: running ? 'pulse 1s ease-in-out infinite alternate' : undefined,
        },
      })
    }
    for (const e of graph.edges) edges.push({ id: `e${e.from}-${e.to}`, source: String(e.from), target: String(e.to), style: { stroke: color(e.type) } })
    return { nodes, edges }
  }, [graph, selected])

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif', width: '100%', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>SimTree Panel</h3>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/">首页</Link>
          <Link to="/simtree">树</Link>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 16 }}>
        <button onClick={create} disabled={treeId != null}>Create (simple_chat)</button>
        <button onClick={refresh} disabled={treeId == null}>Refresh</button>
      </div>

      {graph && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginTop: 16 }}>
          <div>
            <h4>Graph</h4>
            <div style={{ width: '100%', height: 420, border: '1px solid #ddd' }}>
              <style>{'@keyframes pulse{from{box-shadow:0 0 0 0 rgba(255,0,0,.4)}to{box-shadow:0 0 8px 4px rgba(255,0,0,.2)}}'}</style>
              <ReactFlow nodes={rf.nodes} edges={rf.edges} fitView onNodeClick={(_, n) => setSelected(Number(n.id))}>
                <MiniMap pannable zoomable />
                <Controls />
                <Background />
              </ReactFlow>
            </div>
            <div style={{ marginTop: 8, color: '#666' }}>Selected: {selected ?? '-'} | Edges: {graph.edges.length} | Frontier: [{graph.frontier.join(', ')}]</div>
          </div>
          <div>
            <h4>Ops</h4>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button onClick={advanceSel} disabled={treeId == null || selected == null}>Advance selected</button>
              <button onClick={advanceFrontier} disabled={treeId == null}>Advance leaves</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 12, alignItems: 'end' }}>
              <div>
                <label>Multi turns</label>
                <input type="number" min={1} value={multiTurns} onChange={(e) => setMultiTurns(Number(e.target.value))} style={{ width: '100%' }} />
              </div>
              <div>
                <label>Count</label>
                <input type="number" min={1} value={multiCount} onChange={(e) => setMultiCount(Number(e.target.value))} style={{ width: '100%' }} />
              </div>
              <button onClick={() => treeId != null && selected != null && treeAdvanceMulti(treeId, selected, multiTurns, multiCount)} disabled={treeId == null || selected == null}>Advance N copies</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 12, alignItems: 'end' }}>
              <div>
                <label>Chain turns</label>
                <input type="number" min={1} value={chainTurns} onChange={(e) => setChainTurns(Number(e.target.value))} style={{ width: '100%' }} />
              </div>
              <button onClick={() => treeId != null && selected != null && treeAdvanceChain(treeId, selected, chainTurns)} disabled={treeId == null || selected == null}>Advance chain</button>
            </div>
            <div style={{ marginTop: 12 }}>
              <div>进入 /sim 页面（基于此树）</div>
              <button onClick={() => treeId != null && selected != null && navigate(`/sim/${treeId}?node=${selected}`)} disabled={treeId == null || selected == null}>进入</button>
            </div>
            <div style={{ marginTop: 12 }}>
              <div>public_broadcast:</div>
              <input value={text} onChange={(e) => setText(e.target.value)} style={{ width: '100%' }} />
              <button onClick={branchPublic} style={{ marginTop: 6 }} disabled={treeId == null || selected == null}>Apply</button>
            </div>
            <div style={{ marginTop: 12 }}>
              <div>Delete subtree (root disabled)</div>
              <button onClick={delSubtree} disabled={!graph || selected == null || selected === graph.root}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
