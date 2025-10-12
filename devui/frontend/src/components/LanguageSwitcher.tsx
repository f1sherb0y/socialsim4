import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const [lang, setLang] = useState(() => (i18n.language || 'en').startsWith('zh') ? 'zh' : 'en')
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const el = ref.current
      if (!el) return
      const target = e.target as Node
      if (!el.contains(target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [ref])

  useEffect(() => {
    const code = lang === 'zh' ? 'zh' : 'en'
    i18n.changeLanguage(code)
    localStorage.setItem('devui:i18n-lang', code)
  }, [lang, i18n])

  const label = useMemo(() => (lang === 'zh' ? '中文' : 'EN'), [lang])

  return (
    <div className="select" ref={ref} style={{ minWidth: 84 }}>
      <button type="button" className="btn" onClick={() => setOpen(v => !v)} aria-haspopup="listbox" aria-expanded={open}>
        {label}
        <span className="select-caret">▾</span>
      </button>
      {open && (
        <div className="select-menu card" role="listbox">
          {(['en','zh'] as const).map((opt) => (
            <div
              key={opt}
              role="option"
              aria-selected={opt === lang}
              className={"select-item" + (opt === lang ? " select-item-active" : "")}
              onClick={() => { setLang(opt) ; setOpen(false) }}
            >
              {opt === 'en' ? 'English' : '中文'}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
