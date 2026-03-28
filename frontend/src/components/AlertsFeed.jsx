import { Bell } from 'lucide-react'
import { useGrid } from '../App.jsx'

const SEV_ICON = { CRITICAL: '🔴', WARNING: '🟡', INFO: '🔵' }

export default function AlertsFeed({ className }) {
  const { alerts } = useGrid()

  const critCount = alerts.filter(a => a.severity === 'CRITICAL').length

  return (
    <div className={`card ${className || ''}`}>
      <div className="card-header">
        <div className="card-title">
          <Bell size={13} />
          Live Alerts Feed
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {critCount > 0 && <span className="badge critical">{critCount} critical</span>}
          <span style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>
            {alerts.length} total
          </span>
        </div>
      </div>

      <div className="scroll-panel">
        {alerts.length === 0 ? (
          <div style={{ color: 'var(--muted)', fontSize: '0.72rem', padding: '12px 0', textAlign: 'center' }}>
            No alerts — system nominal
          </div>
        ) : alerts.map(a => (
          <div key={a.id} className={`alert-item ${a.severity || 'INFO'}`}>
            <div className="alert-meta">
              {SEV_ICON[a.severity] || '🔵'} {a.timestamp_display}
            </div>
            <div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 2 }}>
                <span className="alert-service">{a.service}</span>
                {a.zone && (
                  <span style={{ fontSize: '0.62rem', color: 'var(--purple)', textTransform: 'capitalize' }}>
                    [{a.zone}]
                  </span>
                )}
                {a.component && (
                  <span style={{ fontSize: '0.62rem', color: 'var(--muted)' }}>
                    {a.component}
                  </span>
                )}
              </div>
              <div className="alert-msg">{a.message}</div>
              {a.fault_type && (
                <div style={{ fontSize: '0.62rem', color: 'var(--amber)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
                  {a.fault_type}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
