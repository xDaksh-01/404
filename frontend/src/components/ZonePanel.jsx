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
      <div className="zone-name status-muted">{zone.label}</div>
      <div className="status-muted" style={{ fontSize: '0.68rem' }}>offline</div>
      <div></div>
    </div>
  )
  const pct     = data.load_percent || 0
  const color   = pct > 90 ? 'red' : pct > 80 ? 'amber' : 'green'
  const textClass = pct > 90 ? 'status-critical' : pct > 80 ? 'status-warning' : 'status-healthy'
  const tripped = data.substation_status === 'tripped'
  const freqOk  = Math.abs((data.frequency_hz || 50) - 50) < 0.3
  const freq    = (data.frequency_hz || 50).toFixed(3)

  return (
    <div className="zone-row">
      <div>
        <div className={`zone-name ${tripped ? 'status-critical' : ''}`}>
          {zone.label}
        </div>
        {tripped && <div className="status-critical" style={{ fontSize: '0.6rem' }}>TRIPPED</div>}
      </div>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
          <span className={textClass} style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600
          }}>{pct.toFixed(1)}%</span>
          <span className="status-muted" style={{ fontSize: '0.62rem' }}>
            {data.current_load_mw?.toFixed(0)}MW
          </span>
        </div>
        <div className="progress-bar" style={{ height: '5px' }}>
          <div className={`progress-fill ${color}`} style={{ width: `${Math.min(100, pct)}%` }} />
        </div>
      </div>
      <div className="zone-stats">
        <div className={freqOk ? 'status-muted' : 'status-warning'}>{freq}Hz</div>
        <div className={(data.voltage_avg_v || 230) < 215 ? 'status-warning' : 'status-muted'}>
          {data.voltage_avg_v?.toFixed(1)}V
        </div>
        <div className={(data.active_events || 0) > 0 ? 'status-warning' : 'status-muted'}>
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
          <span className="status-muted" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem' }}>
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
