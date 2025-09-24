import { useEffect, useMemo, useRef, useState } from 'react'
import { createSim, runSim, type Offsets } from '../api/client'

export default function Simulation() {
  const [simId, setSimId] = useState<number | null>(null)
  const [names, setNames] = useState<string[]>([])
  const [offsets, setOffsets] = useState<Offsets | null>(null)
  const [timeline, setTimeline] = useState<any[]>([])
  const [selected, setSelected] = useState<string>('')

  const initOffsets = useMemo<Offsets | null>(() => {
    if (!names.length) return null
    const mem: Offsets['mem'] = {}
    names.forEach((n) => (mem[n] = { count: 0, last_len: 0 }))
    return { events: 0, mem }
  }, [names])

  async function create() {
    const r = await createSim()
    setSimId(r.id)
    setNames(r.names)
    setSelected(r.names[0])
    const off: Offsets = { events: 0, mem: {} as any }
    r.names.forEach((n) => (off.mem[n] = { count: 0, last_len: 0 }))
    setOffsets(off)
  }

  async function step(n: number) {
    if (simId == null || offsets == null) return
    await runSim(simId, n)
  }

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
    if (!selected) return [] as string[]
    const lines: string[] = []
    for (const frame of timeline) {
      const m = (frame.agents as any[]).find((a) => a.name === selected)
      if (!m) continue
      for (const msg of m.context_delta as any[]) {
        lines.push(`[${msg.role}] ${msg.content}`)
      }
    }
    return lines
  }, [timeline, selected])

  // WebSocket live updates
  const wsRef = useRef<WebSocket | null>(null)
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
    }
    wsRef.current = ws
    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [simId, offsets])

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h3>Simulation Panel</h3>
      <div style={{ display: 'flex', gap: 16 }}>
        <button onClick={create} disabled={simId != null}>Create simple_chat</button>
        <button onClick={() => step(1)} disabled={simId == null}>Run 1 turn</button>
        <button onClick={() => step(10)} disabled={simId == null}>Run 10 turns</button>
        <button onClick={() => step(50)} disabled={simId == null}>Run 50 turns</button>
      </div>

      {simId != null && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginTop: 16 }}>
          <div>
            <h4>Events</h4>
            <pre style={{ background: '#111', color: '#0f0', padding: 12, height: 360, overflow: 'auto' }}>{events.join('\n')}</pre>
          </div>
          <div>
            <h4>Agent</h4>
            <select value={selected} onChange={(e) => setSelected(e.target.value)}>
              {names.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <pre style={{ background: '#f5f5f5', padding: 12, height: 320, overflow: 'auto' }}>{agentDelta.join('\n')}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
