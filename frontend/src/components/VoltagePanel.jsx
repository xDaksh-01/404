import { Gauge } from 'lucide-react'
import { useGrid } from '../App.jsx'

function CircularGauge({ value, max = 1, label, color = 'var(--blue)', size = 60 }) {
  const pct = Math.min(1, Math.max(0, value / max))
  const r = size / 2 - 6
  const circ = 2 * Math.PI * r
  const dash = circ * pct
  const gap  = circ - dash

  return (
    <div className="gauge-container">
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none"
                stroke="rgba(255,255,255,0.07)" strokeWidth={5} />
        <circle cx={size/2} cy={size/2} r={r} fill="none"
                stroke={color} strokeWidth={5}
                strokeDasharray={`${dash} ${gap}`}
                strokeLinecap="round"
                style={{ transition: 'stroke-dasharray 0.4s ease' }} />
      </svg>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600,
        color, textAlign: 'center', marginTop: -2,
      }}>
        {typeof value === 'number' ? value.toFixed(2) : value}
      </div>
      <div className="label" style={{ textAlign: 'center' }}>{label}</div>
    </div>
  )
}

function TapIndicator({ position }) {
  const steps = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
  const toneClass = position === 0 ? 'status-muted' : position > 0 ? 'status-cyan' : 'status-warning'
  return (
    <div className="tap-indicator">
      {steps.map(s => (
        <div key={s} className={`tap-step ${s === 0 ? 'center' : ''} ${
          (position > 0 && s > 0 && s <= position) ? 'active pos' :
          (position < 0 && s < 0 && s >= position) ? 'active neg' : ''
        }`} />
      ))}
      <span className={toneClass} style={{ marginLeft: 4, fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
        {position > 0 ? `+${position}` : position}
      </span>
    </div>
  )
}

export default function VoltagePanel() {
  const { summary } = useGrid()
  const data = summary?.voltage_regulator

  if (!data) return (
    <div className="card">
      <div className="card-header">
        <div className="card-title"><Gauge size={13} />Voltage Regulator</div>
      </div>
      <div style={{ color: 'var(--muted)', fontSize: '0.75rem', padding: '20px 0', textAlign: 'center' }}>
        Connecting...
      </div>
    </div>
  )

  const pf      = data.grid_power_factor_avg || 0.94
  const avgV    = data.grid_voltage_avg_v || 230
  const minV    = data.grid_voltage_min_v || 228
  const taps    = data.tap_changes_per_hour || 0
  const caps    = data.capacitor_banks_active_count || 0
  const viols   = data.voltage_violations_count || 0
  const locked  = data.tap_changer_locked
  const profiles= data.zone_voltage_profiles || {}

  const pfClass  = pf < 0.85 ? 'status-critical' : pf < 0.90 ? 'status-warning' : 'status-healthy'
  const voltClass = avgV < 218 ? 'status-critical' : avgV < 225 ? 'status-warning' : 'status-cyan'

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title"><Gauge size={13} />Voltage Regulator</div>
        {locked && <span className="badge warning">TAP LOCKED</span>}
        {viols > 0 && <span className="badge critical">{viols} violations</span>}
      </div>

      {/* Main gauges */}
      <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 14 }}>
        <CircularGauge value={pf} max={1} label="Power Factor" color={pf < 0.85 ? 'var(--red)' : pf < 0.90 ? 'var(--amber)' : 'var(--green)'} size={64} />
        <div style={{ textAlign: 'center' }}>
          <div className="label" style={{ marginBottom: 4 }}>Avg Voltage</div>
          <div className={voltClass} style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem',
                       fontWeight: 600 }}>
            {avgV.toFixed(1)}
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--muted)' }}>V (min {minV.toFixed(1)})</div>
          <div style={{ marginTop: 4, fontSize: '0.65rem', color: 'var(--muted)' }}>
            {caps} banks active · {taps.toFixed(1)} taps/hr
          </div>
        </div>
      </div>

      {/* Per-zone voltage + tap */}
      <div className="scroll-panel" style={{ maxHeight: 120 }}>
        {Object.entries(profiles).map(([zone, zp]) => (
          <div key={zone} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
            fontSize: '0.68rem',
          }}>
            <span style={{ color: 'var(--white)', textTransform: 'capitalize', minWidth: 55 }}>
              {zone}
            </span>
            <span className={(zp.avg_v || 230) < 218 ? 'status-warning' : 'status-muted'} style={{
              fontFamily: 'var(--font-mono)',
            }}>
              {(zp.avg_v || 0).toFixed(1)}V
            </span>
            <TapIndicator position={zp.tap_position || 0} />
            {zp.capacitor_bank_active && (
              <span className="status-cyan" style={{ fontSize: '0.6rem' }}>⚡CAP</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
