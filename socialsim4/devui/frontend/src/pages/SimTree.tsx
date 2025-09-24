import { useEffect, useMemo, useState } from 'react'
import { createTree, getTreeGraph, treeAdvance, treeAdvanceFrontier, treeBranchPublic, treeDeleteSubtree } from '../api/client'
import ReactFlow, { Background, Controls, MiniMap, Node, Edge } from 'reactflow'
import 'reactflow/dist/style.css'

type Graph = { root: number; frontier: number[]; nodes: { id: number; depth: number }[]; edges: { from: number; to: number; type: string }[] }

export default function SimTree() {
  const [treeId, setTreeId] = useState<number | null>(null)
  const [graph, setGraph] = useState<Graph | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [text, setText] = useState('(announcement)')

  async function create() {
    const r = await createTree()
    setTreeId(r.id)
    setSelected(r.root)
    const g = await getTreeGraph(r.id)
    setGraph(g)
  }

  async function refresh() {
    if (treeId == null) return
    const g = await getTreeGraph(treeId)
    setGraph(g)
  }

  async function advanceSel() {
    if (treeId == null || selected == null) return
    await treeAdvance(treeId, selected, 1)
    await refresh()
  }

  async function advanceFrontier() {
    if (treeId == null) return
    await treeAdvanceFrontier(treeId, 1)
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
    const byDepth: Record<number, number[]> = {}
    for (const n of graph.nodes) {
      if (!byDepth[n.depth]) byDepth[n.depth] = []
      byDepth[n.depth].push(n.id)
    }
    const nodes: Node[] = []
    const edges: Edge[] = []
    const dx = 80
    const dy = 100
    for (const n of graph.nodes) {
      const idx = byDepth[n.depth].indexOf(n.id)
      const x = idx * dx
      const y = n.depth * dy
      const bg = n.id === graph.root ? '#69f' : graph.frontier.includes(n.id) ? '#7c7' : '#fff'
      nodes.push({
        id: String(n.id),
        data: { label: String(n.id) },
        position: { x, y },
        style: {
          width: 40,
          height: 40,
          borderRadius: 20,
          background: selected === n.id ? '#f66' : bg,
          border: '1px solid #999',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
        },
      })
    }
    const color = (t: string) => {
      if (t === 'advance') return '#000'
      if (t === 'agent_ctx') return '#1b5e20'
      if (t === 'agent_plan') return '#e65100'
      if (t === 'agent_props') return '#5e35b1'
      if (t === 'scene_state') return '#6d4c41'
      if (t === 'public_event') return '#1e4976'
      return '#888'
    }
    for (const e of graph.edges) {
      edges.push({ id: `e${e.from}-${e.to}`, source: String(e.from), target: String(e.to), style: { stroke: color(e.type) } })
    }
    return { nodes, edges }
  }, [graph, selected])

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h3>SimTree Panel</h3>
      <div style={{ display: 'flex', gap: 16 }}>
        <button onClick={create} disabled={treeId != null}>Create (simple_chat)</button>
        <button onClick={refresh} disabled={treeId == null}>Refresh</button>
      </div>

      {graph && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginTop: 16 }}>
          <div>
            <h4>Graph</h4>
            <div style={{ width: '100%', height: 420, border: '1px solid #ddd' }}>
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
              <button onClick={advanceFrontier} disabled={treeId == null}>Advance frontier</button>
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
