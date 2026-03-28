import { Map } from 'lucide-react'
import { useGrid } from '../App.jsx'

const ZONES = [
  { key: 'north',   label: 'NORTH',   peak: 950 },
  { key: 'south',   label: 'SOUTH',   peak: 780 },
  { key: 'east',    label: 'EAST',    peak: 1100 },
  { key: 'west',    label: 'WEST',    peak: 820 },
  { key: 'central', label: 'CENTRAL', peak: 1050 },
]

function ZoneRow({ zone, data }) {
  if (!data) return (
    <div className="zone-row">
      <div className="zone-name" style={{ color: 'var(--muted)' }}>{zone.label}</div>
      <div style={{ fontSize: '0.68rem', color: 'var(--muted)' }}>offline</div>
      <div></div>
    </div>
  )
  const pct     = data.load_percent || 0
  const color   = pct > 90 ? 'red' : pct > 80 ? 'amber' : 'green'
  const textCol = pct > 90 ? 'var(--red)' : pct > 80 ? 'var(--amber)' : 'var(--green)'
  const tripped = data.substation_status === 'tripped'
  const freqOk  = Math.abs((data.frequency_hz || 50) - 50) < 0.3
  const freq    = (data.frequency_hz || 50).toFixed(3)

  return (
    <div className="zone-row">
      <div>
        <div className="zone-name" style={{ color: tripped ? 'var(--red)' : 'var(--white)' }}>
          {zone.label}
        </div>
        {tripped && <div style={{ fontSize: '0.6rem', color: 'var(--red)' }}>TRIPPED</div>}
      </div>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: textCol, fontWeight: 600
          }}>{pct.toFixed(1)}%</span>
          <span style={{ fontSize: '0.62rem', color: 'var(--muted)' }}>
            {data.current_load_mw?.toFixed(0)}MW
          </span>
        </div>
        <div className="progress-bar" style={{ height: '5px' }}>
          <div className={`progress-fill ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
        </div>
      </div>
      <div className="zone-stats">
        <div style={{ color: freqOk ? 'var(--muted)' : 'var(--amber)' }}>{freq}Hz</div>
        <div style={{ color: (data.voltage_avg_v || 230) < 215 ? 'var(--amber)' : 'var(--muted)' }}>
          {data.voltage_avg_v?.toFixed(1)}V
        </div>
        <div style={{ color: (data.active_events || 0) > 0 ? 'var(--amber)' : 'var(--muted)' }}>
          {data.active_events || 0} events
        </div>
      </div>
    </div>
  )
}

export default function ZonePanel({ className }) {
  const { zones } = useGrid()

  const activeZones = Object.values(zones).filter(Boolean)
  const totalLoad   = activeZones.reduce((s, z) => s + (z.current_load_mw || 0), 0)
  const overloaded  = activeZones.filter(z => (z.load_percent || 0) > 85).length

  return (
    <div className={`card ${className || ''}`}>
      <div className="card-header">
        <div className="card-title">
          <Map size={13} />
          Zone Status
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {overloaded > 0 && (
            <span className="badge warning">{overloaded} overloaded</span>
          )}
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--muted)' }}>
            {totalLoad.toFixed(0)} MW total
          </span>
        </div>
      </div>

      {ZONES.map(zone => (
        <ZoneRow key={zone.key} zone={zone} data={zones[zone.key]} />
      ))}
    </div>
  )
}
