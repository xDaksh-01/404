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
  return (
    <div className="tap-indicator">
      {steps.map(s => (
        <div key={s} className={`tap-step ${s === 0 ? 'center' : ''} ${
          (position > 0 && s > 0 && s <= position) ? 'active pos' :
          (position < 0 && s < 0 && s >= position) ? 'active neg' : ''
        }`} />
      ))}
      <span style={{ marginLeft: 4, fontSize: '0.68rem', fontFamily: 'var(--font-mono)',
                     color: position === 0 ? 'var(--muted)' : position > 0 ? 'var(--blue)' : 'var(--amber)' }}>
        {position > 0 ? `+${position}` : position}
      </span>
    </div>
  )
}

export default function VoltagePanel({ className }) {
  const { summary } = useGrid()
  // Data is nested in summary
  const data = summary?.voltage_regulator
  const hasData = data && Object.keys(data).length > 0

  if (!hasData) return (
    <div className={`card ${className || ''}`}>
      <div className="card-header">
        <div className="card-title"><Gauge size={13} />Voltage Regulator</div>
      </div>
      <div style={{ color: 'var(--muted)', fontSize: '0.75rem', padding: '20px 0', textAlign: 'center' }}>
        Connecting to voltage-regulator...
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

  const pfColor  = pf < 0.85 ? 'var(--red)' : pf < 0.90 ? 'var(--amber)' : 'var(--green)'
  const voltColor= avgV < 218 ? 'var(--red)' : avgV < 225 ? 'var(--amber)' : 'var(--blue)'

  return (
    <div className={`card ${className || ''}`}>
      <div className="card-header">
        <div className="card-title"><Gauge size={13} />Voltage Regulator</div>
        {locked && <span className="badge warning">TAP LOCKED</span>}
        {viols > 0 && <span className="badge critical">{viols} violations</span>}
      </div>

      {/* Main gauges */}
      <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: 14 }}>
        <CircularGauge value={pf} max={1} label="Power Factor" color={pfColor} size={64} />
        <div style={{ textAlign: 'center' }}>
          <div className="label" style={{ marginBottom: 4 }}>Avg Voltage</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem',
                       fontWeight: 600, color: voltColor }}>
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
            <span style={{
              fontFamily: 'var(--font-mono)',
              color: (zp.avg_v || 230) < 218 ? 'var(--amber)' : 'var(--muted)',
            }}>
              {(zp.avg_v || 0).toFixed(1)}V
            </span>
            <TapIndicator position={zp.tap_position || 0} />
            {zp.capacitor_bank_active && (
              <span style={{ fontSize: '0.6rem', color: 'var(--blue)' }}>⚡CAP</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
