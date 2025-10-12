import { useEffect, useMemo, useRef, useState, JSX } from 'react'
import { getSimEvents, getSimState } from '../api/client'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '../components/LanguageSwitcher'

export default function Simulation() {
  const params = useParams()
  const { t } = useTranslation()
  const [theme, setTheme] = useState<string>(() => localStorage.getItem('devui:theme') || 'light')
  const treeNav = params.treeId ? `/simtree/${params.treeId}` : '/simtree'
  const [names, setNames] = useState<string[]>([])
  const [timeline, setTimeline] = useState<any[]>([])
  const [selected, setSelected] = useState<string>('')
  // SimTree controls execution; this page is read-only view

  // no local create

  // If route has :treeId, spawn a sim from that tree (optionally with ?node=)
  useEffect(() => {
    const init = async () => {
      if (params.treeId == null) return
      const tid = Number(params.treeId)
      if (Number.isNaN(tid)) return
      const qs = new URLSearchParams(location.search)
      const simParam = qs.get('sim') || qs.get('node')
      const nid = simParam ? Number(simParam) : 0
      // Logs: keep raw shape; formatting is done in render via formatEvent
      const logs = await getSimEvents(tid, nid)
      // Node state for agents/plan/memory
      const st = await getSimState(tid, nid)
      const agentNames = st.agents.map((a: any) => a.name)
      setNames(agentNames)
      setSelected(agentNames[0] || "")
      // Build a single timeline frame compatible with renderer
      const frame = {
        events_delta: logs || [],
        agents: st.agents.map((a: any) => ({ name: a.name, role: a.role, emotion: a.emotion, plan_state: a.plan_state, context_delta: a.short_memory })),
        turns: st.turns,
      }
      setTimeline([frame])
    }
    init()
  }, [params.treeId])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    const darkLink = document.getElementById('sl-theme-dark') as HTMLLinkElement | null
    if (darkLink) darkLink.disabled = theme !== 'dark'
    localStorage.setItem('devui:theme', theme)
  }, [theme])

  // no local step

  // no offsets needed

  // format a single backend log item to a compact line; null to hide
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

  const agentEmotion = useMemo(() => {
    if (!selected) return ''
    const last = timeline.length ? (timeline[timeline.length - 1] as any) : null
    if (!last) return ''
    const ag = ((last.agents as any[]) || []).find((a) => a.name === selected)
    return ag?.emotion || ''
  }, [timeline, selected])

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
    <div className="page">
      <div className="header">
        <div className="header-inner">
          <h3 className="title">{t('sim.title')}</h3>
          <div className="row" style={{ gap: 10, flex: 1, marginLeft: 8 }}>
            <nav className="nav row">
              <Link to="/">{t('nav.home')}</Link>
              <Link to={treeNav}>{t('nav.tree')}</Link>
            </nav>
            <div style={{ marginLeft: 'auto' }}><LanguageSwitcher /></div>
          </div>
        </div>
      </div>

      <div className="content-grid">
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <h4 className="section-title">{t('sim.events')}</h4>
          <div ref={eventsRef} className="card card-pad scroll text-prewrap text-break" style={{ lineHeight: 1.55, flex: 1 }}>
            {(() => {
              const last = timeline.length ? (timeline[timeline.length - 1] as any) : null
              const evs = (last?.events_delta as any[]) || []
              const formatted = evs.map((e, i) => formatEvent(e, i)).filter(Boolean)
              return formatted.length ? formatted : <div className="muted">{t('common.noEvents')}</div>
            })()}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h4 className="section-title" style={{ margin: 0 }}>{t('sim.agent')}</h4>
            <label className="label row" style={{ gap: 6 }}>
              <input type="checkbox" checked={stickBottom} onChange={(e) => setStickBottom(e.target.checked)} />
              <span>{t('common.stickBottom')}</span>
            </label>
          </div>
          <CompactSelect options={names} value={selected} onChange={setSelected} />
          {agentEmotion && <div className="card-pad" style={{ marginBottom: 8 }}><b>Emotion:</b> {agentEmotion}</div>}
          <div ref={agentRef} className="card card-pad scroll text-prewrap text-break" style={{ lineHeight: 1.55, flex: 1 }}>
            {agentDelta.length ? (
              <ul className="list-compact">
                {agentDelta.map((m, i) => (
                  <li key={i}><span className="muted">[{m.role}]</span> {m.content}</li>
                ))}
              </ul>
            ) : (
              <div className="muted">{t('common.empty')}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function CompactSelect({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)
  const { t } = useTranslation()
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      const el = ref.current
      if (!el) return
      const target = e.target as Node
      if (!el.contains(target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])
  const label = value || (options[0] || '') || t('common.none')
  return (
    <div className="select" ref={ref} style={{ marginBottom: 8 }}>
      <button type="button" className="input select-btn" onClick={() => setOpen((v) => !v)} aria-haspopup="listbox" aria-expanded={open}>
        <span>{label}</span>
        <span className="select-caret">▾</span>
      </button>
      {open && (
        <div className="select-menu card" role="listbox">
          {options.length ? options.map((opt) => (
            <div key={opt} role="option" aria-selected={opt === value} className={"select-item" + (opt === value ? " select-item-active" : "")} onClick={() => { onChange(opt); setOpen(false) }}>
              {opt}
            </div>
          )) : (
            <div className="select-item muted" aria-disabled>{t('common.noOptions')}</div>
          )}
        </div>
      )}
    </div>
  )
}
