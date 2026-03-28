import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Zap, Activity, Info, BarChart3, Bot, Settings } from 'lucide-react'

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">⚡</div>
        <div className="brand-text">POWERGRID</div>
      </div>
      
      <nav className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
          <LayoutDashboard size={18} />
          <span>System Overview</span>
        </NavLink>
        
        <NavLink to="/transformers" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Zap size={18} />
          <span>All Transformers</span>
        </NavLink>
        
        <NavLink to="/zones" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Activity size={18} />
          <span>Zone Details</span>
        </NavLink>
        
        <NavLink to="/logs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Bot size={18} />
          <span>Logs & Fixes</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div className="system-version">SCADA v2.0.4</div>
        <div className="system-status mono">NODE-ACTIVE</div>
      </div>
    </aside>
  )
}
