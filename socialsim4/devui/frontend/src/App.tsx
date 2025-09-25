import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

export default function App() {
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
          <h3 className="title">SocialSim4 DevUI</h3>
          <nav className="nav row">
            <Link to="/">首页</Link>
            <Link to="/simtree">树</Link>
            <Link to="/sim">模拟</Link>
          </nav>
        </div>
      </div>

      <div style={{ padding: '16px' }}>
        <div className="row" style={{ flexWrap: 'wrap', gap: 12 }}>
          <div className="card card-pad" style={{ flex: '1 1 360px' }}>
            <div className="label" style={{ marginBottom: 6 }}>面板</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Simulation</div>
            <div className="muted" style={{ marginBottom: 12 }}>查看某个 SimTree 节点的事件流与 Agent 上下文。</div>
            <Link to="/sim" className="btn">进入</Link>
          </div>

          <div className="card card-pad" style={{ flex: '1 1 360px' }}>
            <div className="label" style={{ marginBottom: 6 }}>面板</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>SimTree</div>
            <div className="muted" style={{ marginBottom: 12 }}>创建、运行与分支时间线，图形化浏览节点。</div>
            <Link to="/simtree" className="btn">进入</Link>
          </div>

          <div className="card card-pad" style={{ flex: '1 1 360px' }}>
            <div className="label" style={{ marginBottom: 6 }}>工作台</div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Studio</div>
            <div className="muted" style={{ marginBottom: 12 }}>左：SimTree 图与操作；中：所选节点 Events；右：Agents。</div>
            <Link to="/studio" className="btn">进入</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
