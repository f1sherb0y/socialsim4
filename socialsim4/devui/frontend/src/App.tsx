import { Link } from 'react-router-dom'

export default function App() {
  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h2>SocialSim4 DevUI</h2>
      <ul>
        <li><Link to="/sim">Simulation Panel</Link></li>
        <li><Link to="/simtree">SimTree Panel</Link></li>
      </ul>
    </div>
  )
}

