import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Zap, Activity, BarChart3, Bot, Cpu } from 'lucide-react'

export default function Sidebar() {
  const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
  const dockerBase = `http://${host}:3000`

  const observabilityLinks = import.meta.env.DEV
    ? {
        prometheus: 'http://localhost:9090',
        grafana: 'http://localhost:3001/d/smart-grid-overview/smart-grid-overview?orgId=1&refresh=5s',
      }
    : {
        prometheus: `http://localhost:3000/prometheus/targets?search=`,
        grafana: `http://localhost:3000/grafana/d/smart-grid-overview/smart-grid-overview?orgId=1&refresh=5s`,
      }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">⚡</div>
        <div className="brand-text">POWERGRID</div>
      </div>
      
      <nav className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
          <Zap size={18} />
          <span>City View</span>
        </NavLink>

        <NavLink to="/overview" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={18} />
          <span>System Overview</span>
        </NavLink>

        <NavLink to="/transformer-info" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Cpu size={18} />
          <span>Transformer Info</span>
        </NavLink>
        
        <NavLink to="/zones" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Activity size={18} />
          <span>Zone Details</span>
        </NavLink>
        
        <NavLink to="/logs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Bot size={18} />
          <span>Logs & Fixes</span>
        </NavLink>


        <a
          href={observabilityLinks.grafana}
          className="nav-link nav-link-external"
          target="_blank"
          rel="noopener noreferrer"
        >
          <BarChart3 size={18} />
          <span>Grafana</span>
        </a>
      </nav>

      <div className="sidebar-footer">
        <div className="system-version">SCADA v2.0.4</div>
        <div className="system-status mono">NODE-ACTIVE</div>
      </div>
    </aside>
  )
}
