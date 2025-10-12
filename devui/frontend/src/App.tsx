import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from './components/LanguageSwitcher'

export default function App() {
  const { t } = useTranslation()
  const [theme, setTheme] = useState<string>(() => localStorage.getItem('devui:theme') || 'light')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    const darkLink = document.getElementById('sl-theme-dark') as HTMLLinkElement | null
    if (darkLink) darkLink.disabled = theme !== 'dark'
    localStorage.setItem('devui:theme', theme)
  }, [theme])

  return (
    <div className="page">
      <div className="header">
        <div className="header-inner">
          <h3 className="title">{t('app.title')}</h3>
          <div className="row" style={{ gap: 10, flex: 1, marginLeft: 8 }}>
            <nav className="nav row">
              <Link to="/">{t('nav.home')}</Link>
              <Link to="/simtree">{t('nav.tree')}</Link>
              <Link to="/sim">{t('nav.sim')}</Link>
            </nav>
            <div style={{ marginLeft: 'auto' }}><LanguageSwitcher /></div>
          </div>
        </div>
      </div>

      <div style={{ padding: '16px' }}>
        <div className="row" style={{ flexWrap: 'wrap', gap: 12 }}>
          <div className="card card-pad" style={{ flex: '1 1 360px' }}>
            <div className="label" style={{ marginBottom: 6 }}>{t('home.panel')}</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{t('home.simulation.title')}</div>
            <div className="muted" style={{ marginBottom: 12 }}>{t('home.simulation.desc')}</div>
            <Link to="/sim" className="btn">{t('home.simulation.enter')}</Link>
          </div>

          <div className="card card-pad" style={{ flex: '1 1 360px' }}>
            <div className="label" style={{ marginBottom: 6 }}>{t('home.panel')}</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{t('home.simtree.title')}</div>
            <div className="muted" style={{ marginBottom: 12 }}>{t('home.simtree.desc')}</div>
            <Link to="/simtree" className="btn">{t('home.simtree.enter')}</Link>
          </div>

          <div className="card card-pad" style={{ flex: '1 1 360px' }}>
            <div className="label" style={{ marginBottom: 6 }}>{t('home.workbench')}</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{t('home.studio.title')}</div>
            <div className="muted" style={{ marginBottom: 12 }}>{t('home.studio.desc')}</div>
            <Link to="/studio" className="btn">{t('home.studio.enter')}</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
