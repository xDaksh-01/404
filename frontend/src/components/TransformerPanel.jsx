import { useState } from 'react'
import { Cpu } from 'lucide-react'
import { useGrid } from '../App.jsx'

function getColor(pct) {
  if (typeof pct !== 'number' || Number.isNaN(pct)) return { text: 'var(--muted)', cls: 'healthy' }
  if (pct > 95) return { text: 'var(--red)',   cls: 'critical' }
  if (pct > 85) return { text: 'var(--red)',   cls: 'critical' }
  if (pct > 75) return { text: 'var(--amber)', cls: 'warning'  }
  return               { text: 'var(--green)', cls: 'healthy'  }
}

function TransformerCard({ t }) {
  const col = getColor(t.load_percent)
  const [hovered, setHovered] = useState(false)
  const loadText = typeof t.load_percent === 'number' ? `${t.load_percent.toFixed(0)}%` : '—'
  const tempText = typeof t.temperature_c === 'number' ? `${t.temperature_c.toFixed(1)}°C` : '—'
  const zoneText = t.zone || 'Pending'

  return (
    <div
      className={`tx-card ${col.cls === 'critical' ? 'critical' : col.cls === 'warning' ? 'warning' : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title={`${t.id || 'Transformer'} | Zone: ${zoneText} | Temp: ${tempText}`}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div>
          <div className="tx-id">{t.id || '—'}</div>
          <div className="tx-zone">{zoneText}</div>
        </div>
        <span className={`dot ${col.cls === 'critical' ? 'red' : col.cls === 'warning' ? 'amber' : 'green'}`}
              style={{ marginTop: 2 }} />
      </div>
      <div className="tx-load" style={{ color: col.text }}>
        {loadText}
      </div>
      <div className="tx-temp">{tempText}</div>
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
            {t.id || '—'} – {zoneText}
          </div>
          <div>Load: <span style={{ color: col.text }}>{typeof t.load_percent === 'number' ? `${t.load_percent.toFixed(1)}%` : '—'}</span></div>
          <div>Temp: {tempText}</div>
          <div>Voltage: {typeof t.voltage_output_v === 'number' ? `${t.voltage_output_v.toFixed(1)}V` : '—'}</div>
          <div>PF: {typeof t.power_factor === 'number' ? t.power_factor.toFixed(3) : '—'}</div>
          <div>Oil: {typeof t.oil_level_percent === 'number' ? `${t.oil_level_percent.toFixed(1)}%` : '—'}</div>
        </div>
      )}
    </div>
  )
}

export default function TransformerPanel({ className = '' }) {
  const { transformers: ts } = useGrid()

  const critCount = ts.filter(t => (t.load_percent || 0) > 85).length
  const tempValues = ts.map(t => t.temperature_c).filter((value) => typeof value === 'number')
  const maxTemp = tempValues.length ? Math.max(...tempValues) : null

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
            {typeof maxTemp === 'number' ? `max ${maxTemp.toFixed(1)}°C` : 'temp pending'}
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
