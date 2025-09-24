import { useEffect, useMemo, useRef, useState } from 'react'
import { getSnapshot, type Offsets, spawnSimFromTree } from '../api/client'
import { Link, useParams } from 'react-router-dom'

export default function Simulation() {
  const params = useParams()
  const [simId, setSimId] = useState<number | null>(null)
  const [names, setNames] = useState<string[]>([])
  const [offsets, setOffsets] = useState<Offsets | null>(null)
  const [timeline, setTimeline] = useState<any[]>([])
  const [selected, setSelected] = useState<string>('')
  // SimTree controls execution; this page is read-only view

  const initOffsets = useMemo<Offsets | null>(() => {
    if (!names.length) return null
    const mem: Offsets['mem'] = {}
    names.forEach((n) => (mem[n] = { count: 0, last_len: 0 }))
    return { events: 0, mem }
  }, [names])

  // no local create

  // If route has :treeId, spawn a sim from that tree (optionally with ?node=)
  useEffect(() => {
    const init = async () => {
      const tid = params.treeId ? Number(params.treeId) : null
      if (!tid || simId != null) return
      const node = new URLSearchParams(location.search).get('node')
      const r = await spawnSimFromTree(tid, node ? Number(node) : 0)
      setSimId(r.sim_id)
      setNames(r.names)
      setSelected(r.names[0] || "")
      const off: Offsets = { events: 0, mem: {} as any }
      r.names.forEach((n) => (off.mem[n] = { count: 0, last_len: 0 }))
      // fetch one snapshot immediately for initial view
      const s = await getSnapshot(r.sim_id, off)
      setTimeline((t) => [...t, s.snapshot])
      setOffsets(s.offsets)
    }
    init()
  }, [params.treeId])

  // no local step

  useEffect(() => {
    if (offsets == null && initOffsets) setOffsets(initOffsets)
  }, [initOffsets, offsets])

  const events = useMemo(() => {
    const lines: string[] = []
    const last = timeline.length ? (timeline[timeline.length - 1] as any) : null
    if (last) {
      for (const it of (last.events_delta as any[]) || []) {
        const t = it.type
        const d = it.data
        if (t === 'system_broadcast') {
          if (!d.sender) lines.push(`[Public Event] ${d.text}`)
        } else if (t === 'action_end') {
          const action = d.action
          if (action.action !== 'yield') lines.push(`[${action.action}] ${d.summary}`)
        }
      }
      if (lines.length === 0) {
        const ags = (last.agents as any[]) || []
        if (ags.length > 0) {
          const msgs = (ags[0].context_delta as any[]) || []
          for (const m of msgs) {
            const c = String(m.content || '')
            if (c.startsWith('[Public Event]')) lines.push(c)
          }
        }
      }
    }
    return lines
  }, [timeline])

  const agentDelta = useMemo(() => {
    if (!selected) return [] as { role: string; content: string }[]
    const last = timeline.length ? (timeline[timeline.length - 1] as any) : null
    if (!last) return []
    const ag = ((last.agents as any[]) || []).find((a) => a.name === selected)
    const msgs = (ag?.context_delta as any[]) || []
    return msgs.map((m: any) => ({ role: String(m.role || ''), content: String(m.content || '') }))
  }, [timeline, selected])

  // No WebSocket: this viewer is static after initial snapshot

  // Auto-stick to bottom when new content arrives
  const [stickBottom, setStickBottom] = useState(true)
  const eventsRef = useRef<HTMLDivElement | null>(null)
  const agentRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (stickBottom && eventsRef.current) {
      const el = eventsRef.current
      el.scrollTop = el.scrollHeight
    }
  }, [timeline, stickBottom])
  useEffect(() => {
    if (stickBottom && agentRef.current) {
      const el = agentRef.current
      el.scrollTop = el.scrollHeight
    }
  }, [agentDelta, selected, stickBottom])

  return (
    <div style={{ height: '100vh', width: '100%', display: 'grid', gridTemplateRows: 'auto 1fr', boxSizing: 'border-box', overflow: 'hidden', fontFamily: 'sans-serif' }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 10, background: '#fff', borderBottom: '1px solid #eee' }}>
        <div style={{ padding: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Simulation Panel</h3>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <Link to="/">首页</Link>
            <Link to="/simtree">树</Link>
          </div>
        </div>
      </div>

      <div style={{ padding: '0 16px 16px 16px', display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)', gap: 16, alignItems: 'stretch', overflow: 'hidden' }}>
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <h4 style={{ margin: '8px 0 8px 0' }}>Events</h4>
          <div ref={eventsRef}
            style={{
              background: '#0b0b0b',
              color: '#c7f7c7',
              padding: 12,
              flex: 1,
              minHeight: 0,
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              overflowWrap: 'anywhere',
              lineHeight: 1.4,
              borderRadius: 6,
              maxWidth: '100%',
            }}
          >
            {events.length ? events.map((line, i) => (
              <div key={i} style={{ padding: '2px 0', borderBottom: '1px dashed #223', opacity: 0.95 }}>
                {line}
              </div>
            )) : <div style={{ opacity: 0.6 }}>(no events yet)</div>}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '8px 0 8px 0' }}>
            <h4 style={{ margin: 0 }}>Agent</h4>
            <label style={{ fontSize: 12, color: '#555' }}>
              <input type="checkbox" checked={stickBottom} onChange={(e) => setStickBottom(e.target.checked)} /> stick to bottom
            </label>
          </div>
          <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ maxWidth: '100%', marginBottom: 8 }}>
            {names.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
          <div ref={agentRef}
            style={{
              background: '#f5f5f5',
              padding: 12,
              flex: 1,
              minHeight: 0,
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              overflowWrap: 'anywhere',
              borderRadius: 6,
              maxWidth: '100%',
            }}
          >
            {agentDelta.length ? (
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                {agentDelta.map((m, i) => (
                  <li key={i}><span style={{ opacity: 0.7 }}>[{m.role}]</span> {m.content}</li>
                ))}
              </ul>
            ) : (
              <div style={{ opacity: 0.6 }}>(empty)</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
