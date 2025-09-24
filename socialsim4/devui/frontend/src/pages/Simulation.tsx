import { useEffect, useMemo, useRef, useState } from 'react'
import { getSnapshot, type Offsets, spawnSimFromTree } from '../api/client'
import { Link, useNavigate, useParams } from 'react-router-dom'

export default function Simulation() {
  const params = useParams()
  const navigate = useNavigate()
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
    for (const frame of timeline) {
      for (const it of frame.events_delta as any[]) {
        const t = it.type
        const d = it.data
        if (t === 'system_broadcast') {
          if (!d.sender) lines.push(`[Public Event] ${d.text}`)
        } else if (t === 'action_end') {
          const action = d.action
          if (action.action !== 'yield') lines.push(`[${action.action}] ${d.summary}`)
        }
      }
    }
    return lines
  }, [timeline])

  const agentDelta = useMemo(() => {
    if (!selected) return [] as { role: string; content: string }[]
    const out: { role: string; content: string }[] = []
    for (const frame of timeline) {
      const m = (frame.agents as any[]).find((a) => a.name === selected)
      if (!m) continue
      for (const msg of m.context_delta as any[]) {
        out.push({ role: msg.role, content: msg.content })
      }
    }
    return out
  }, [timeline, selected])

  // WebSocket live updates + running spinner settle
  const wsRef = useRef<WebSocket | null>(null)
  // passive WS (optional)
  useEffect(() => {
    if (simId == null || offsets == null) return
    if (wsRef.current) return
    const ws = new WebSocket(`ws://localhost:8090/devui/sim/${simId}/events`)
    ws.onopen = () => {
      ws.send(JSON.stringify({ offsets }))
    }
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data)
      setTimeline((t) => [...t, msg.snapshot])
      setOffsets(msg.offsets)
      // passive stream only
    }
    wsRef.current = ws
    return () => {
      ws.close()
      wsRef.current = null
      // no timers
    }
  }, [simId, offsets])

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
    <div
      style={{
        padding: 24,
        fontFamily: 'sans-serif',
        width: '100%',
        boxSizing: 'border-box',
        overflowX: 'hidden',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <h3 style={{ margin: 0 }}>Simulation Panel</h3>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/">首页</Link>
          <Link to="/simtree">树</Link>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center', justifyContent: 'flex-end' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <label style={{ fontSize: 12, color: '#555' }}>
            <input type="checkbox" checked={stickBottom} onChange={(e) => setStickBottom(e.target.checked)} /> stick to bottom
          </label>
        </div>
      </div>

      {simId != null && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)', gap: 16, marginTop: 16, alignItems: 'stretch', minHeight: 'calc(100vh - 160px)' }}>
          <div>
            <h4>Events</h4>
            <div ref={eventsRef}
              style={{
                background: '#0b0b0b',
                color: '#c7f7c7',
                padding: 12,
                height: '100%',
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
          <div>
            <h4>Agent</h4>
            <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ maxWidth: '100%' }}>
              {names.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <div ref={agentRef}
              style={{
                background: '#f5f5f5',
                padding: 12,
                height: '100%',
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
      )}
    </div>
  )
}
