import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Zap, Activity, Bot, Cpu, BarChart3, ExternalLink } from 'lucide-react'

export default function Sidebar() {
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
          href="/grafana/d/smart-grid-overview/smart-grid-overview?orgId=1"
          className="nav-link nav-link-external"
          target="_blank"
          rel="noreferrer"
        >
          <BarChart3 size={18} />
          <span>Grafana</span>
          <ExternalLink size={14} style={{ marginLeft: 'auto', opacity: 0.8 }} />
        </a>
      </nav>

      <div className="sidebar-footer">
        <div className="system-version">SCADA v2.0.4</div>
        <div className="system-status mono">NODE-ACTIVE</div>
      </div>
    </aside>
  )
}
