import { Link } from 'react-router-dom'

export default function App() {
  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif', width: '100%', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>SocialSim4 DevUI</h2>
        <div style={{ display: 'flex', gap: 12 }}>
          <Link to="/">首页</Link>
          <Link to="/simtree">树</Link>
          <Link to="/sim">模拟</Link>
        </div>
      </div>
      <div>
        <p>选择面板：</p>
        <ul>
          <li><Link to="/sim">Simulation Panel</Link></li>
          <li><Link to="/simtree">SimTree Panel</Link></li>
        </ul>
      </div>
    </div>
  )
}
