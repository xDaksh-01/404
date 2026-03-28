import { Activity, Zap, Thermometer, TrendingUp } from 'lucide-react'
import { useGrid } from '../App.jsx'

function Metric({ label, value, unit, color = 'var(--blue)' }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div className="label" style={{ marginBottom: 3 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span className="metric-value" style={{ color, fontSize: '1.5rem' }}>{value ?? '—'}</span>
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
    </div>
  )
}

function LoadBar({ percent }) {
  const pct = Math.min(100, Math.max(0, percent || 0))
  const color = pct > 90 ? 'red' : pct > 75 ? 'amber' : 'green'
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span className="label">Grid Load</span>
        <span className="mono" style={{ fontSize: '0.75rem', color: pct > 90 ? 'var(--red)' : pct > 75 ? 'var(--amber)' : 'var(--green)' }}>
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="progress-bar">
        <div className={`progress-fill ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function GridOverview() {
  const { summary: s } = useGrid()
  
  if (!s) return <div className="card loading-placeholder">Loading Grid Summary...</div>

  const loadMW  = s.grid_total_load_mw?.toFixed(0) ?? '—'
  const capMW   = s.grid_capacity_mw?.toFixed(0) ?? '5240'
  const loadPct = s.grid_load_percent ?? 0
  const avgTemp = s.avg_transformer_temp?.toFixed(1) ?? '—'
  const risk    = s.overload_risk ?? 'LOW'
  const onlineNodes = s.services_online_count ?? '—'

  const riskColor = { LOW: 'var(--green)', MEDIUM: 'var(--blue)', HIGH: 'var(--amber)', CRITICAL: 'var(--red)' }[risk] || 'var(--muted)'

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <Activity size={13} />
          System Overview
        </div>
        <span className="badge" style={{
          background: `${riskColor}22`, color: riskColor,
          border: `1px solid ${riskColor}44`
        }}>
          {risk} RISK
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
        <Metric label="Total Load" value={loadMW} unit="MW" />
        <Metric label="Capacity" value={capMW} unit="MW" color="var(--muted)" />
        <Metric label="Avg Transformer Temp"
                value={avgTemp} unit="°C"
                color={avgTemp > 85 ? 'var(--red)' : avgTemp > 75 ? 'var(--amber)' : 'var(--blue)'} />
        <Metric label="Nodes Online" value={onlineNodes} unit="/5"
                color={onlineNodes >= 4 ? 'var(--green)' : 'var(--amber)'} />
      </div>

      <LoadBar percent={loadPct} />

      <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.68rem', color: 'var(--muted)' }}>
          <Zap size={11} color="var(--blue)" />
          {(loadMW / capMW * 100 || 0).toFixed(1)}% utilization
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.68rem', color: 'var(--muted)' }}>
          <TrendingUp size={11} color="var(--green)" />
          Latency {s.last_poll_latency_ms?.toFixed(0) ?? '—'}ms
        </div>
      </div>
    </div>
  )
}
