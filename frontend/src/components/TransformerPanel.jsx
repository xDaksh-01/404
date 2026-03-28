import { useState } from 'react'
import { Cpu } from 'lucide-react'
import { useGrid } from '../App.jsx'

function getColor(pct) {
  if (pct > 95) return { text: 'var(--red)',   cls: 'critical' }
  if (pct > 85) return { text: 'var(--red)',   cls: 'critical' }
  if (pct > 75) return { text: 'var(--amber)', cls: 'warning'  }
  return               { text: 'var(--green)', cls: 'healthy'  }
}

function TransformerCard({ t }) {
  const col = getColor(t.load_percent)
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className={`tx-card ${col.cls === 'critical' ? 'critical' : col.cls === 'warning' ? 'warning' : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title={`${t.id} | Zone: ${t.zone} | Temp: ${t.temperature_c?.toFixed(1)}°C | Voltage: ${t.voltage_output_v?.toFixed(1)}V | PF: ${t.power_factor?.toFixed(2)}`}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div>
          <div className="tx-id">{t.id}</div>
          <div className="tx-zone">{t.zone}</div>
        </div>
        <span className={`dot ${col.cls === 'critical' ? 'red' : col.cls === 'warning' ? 'amber' : 'green'}`}
              style={{ marginTop: 2 }} />
      </div>
      <div className="tx-load" style={{ color: col.text }}>
        {t.load_percent?.toFixed(0)}%
      </div>
      <div className="tx-temp">{t.temperature_c?.toFixed(1)}°C</div>
      <div className="progress-bar" style={{ height: '3px', marginTop: 4 }}>
        <div
          className={`progress-fill ${col.cls === 'critical' ? 'red' : col.cls === 'warning' ? 'amber' : 'green'}`}
          style={{ width: `${Math.min(100, t.load_percent || 0)}%` }}
        />
      </div>
      {hovered && (
        <div style={{
          position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
          background: 'var(--bg-card)', border: '1px solid var(--border-bright)',
          borderRadius: 6, padding: '6px 10px', zIndex: 10, whiteSpace: 'nowrap',
          fontSize: '0.65rem', boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
          pointerEvents: 'none',
        }}>
          <div style={{ color: 'var(--blue)', fontFamily: 'var(--font-mono)', marginBottom: 2 }}>
            {t.id} – {t.zone}
          </div>
          <div>Load: <span style={{ color: col.text }}>{t.load_percent?.toFixed(1)}%</span></div>
          <div>Temp: {t.temperature_c?.toFixed(1)}°C</div>
          <div>Voltage: {t.voltage_output_v?.toFixed(1)}V</div>
          <div>PF: {t.power_factor?.toFixed(3)}</div>
          <div>Oil: {t.oil_level_percent?.toFixed(1)}%</div>
        </div>
      )}
    </div>
  )
}

export default function TransformerPanel({ className = '' }) {
  const { transformers: ts } = useGrid()

  const critCount = ts.filter(t => t.load_percent > 85).length
  const maxTemp   = ts.length ? Math.max(...ts.map(t => t.temperature_c || 0)) : 0

  return (
    <div className={`card ${className}`.trim()}>
      <div className="card-header">
        <div className="card-title">
          <Cpu size={13} />
          Transformers ({ts.length})
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {critCount > 0 && <span className="badge critical">{critCount} ⚠</span>}
          <span style={{ fontSize: '0.65rem', color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>
            max {maxTemp.toFixed(1)}°C
          </span>
        </div>
      </div>

      {ts.length === 0 ? (
        <div style={{ color: 'var(--muted)', fontSize: '0.75rem', textAlign: 'center', padding: '20px 0' }}>
          Connecting to transformer service...
        </div>
      ) : (
        <div className="transformer-grid">
          {ts.map(t => (
            <TransformerCard key={t.id} t={t} />
          ))}
        </div>
      )}
    </div>
  )
}
