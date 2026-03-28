import { Share2 } from 'lucide-react'
import { useGrid } from '../App.jsx'

export default function LoadBalancerPanel({ className }) {
  const { summary } = useGrid()
  
  // Use summary from context which contains LB data
  const data = summary?.load_balancer
  
  if (!data) return (
    <div className={`card ${className || ''}`}>
      <div className="card-header">
        <div className="card-title"><Share2 size={13} />Load Balancer</div>
      </div>
      <div style={{ color: 'var(--muted)', fontSize: '0.75rem', padding: '20px 0', textAlign: 'center' }}>
        Awaiting LB metrics...
      </div>
    </div>
  )

  const demand    = data.total_demand_mw    || 0
  const allocated = data.total_allocated_mw || 0
  const balance   = demand > 0 ? (allocated / demand * 100) : 100
  const overloaded= data.zones_overloaded_count || 0
  const shedding  = data.load_shedding_active || false
  const mode      = data.transmission_mode || 'normal'
  const rebalances= data.rebalance_count_session || 0
  const paths     = data.transmission_paths || {}

  const modeColor = mode === 'normal' ? 'var(--green)'  :
                    mode === 'bottleneck' ? 'var(--amber)':
                    mode === 'split' ? 'var(--red)' : 'var(--muted)'

  return (
    <div className={`card ${className || ''}`}>
      <div className="card-header">
        <div className="card-title"><Share2 size={13} />Load Balancer</div>
        <div style={{ display: 'flex', gap: 6 }}>
          {shedding && <span className="badge warning">SHEDDING</span>}
          {overloaded > 0 && <span className="badge critical">{overloaded} overloaded</span>}
        </div>
      </div>

      {/* Supply/Demand */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
        {[
          { label: 'Demand',    value: demand.toFixed(0),    unit: 'MW' },
          { label: 'Allocated', value: allocated.toFixed(0), unit: 'MW' },
          { label: 'Balance',   value: balance.toFixed(1),   unit: '%',
            color: balance < 90 ? 'var(--amber)' : 'var(--green)' },
        ].map(m => (
          <div key={m.label} style={{ textAlign: 'center' }}>
            <div className="label" style={{ marginBottom: 3 }}>{m.label}</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '1.0rem', fontWeight: 600,
              color: m.color || 'var(--blue)'
            }}>{m.value}<span style={{ fontSize: '0.65rem', color: 'var(--muted)', marginLeft: 2 }}>{m.unit}</span></div>
          </div>
        ))}
      </div>

      {/* Transmission paths */}
      <div className="label" style={{ marginBottom: 5 }}>Transmission Paths</div>
      <div style={{ maxHeight: 120, overflowY: 'auto' }}>
        {Object.entries(paths).map(([name, p]) => {
          const ratio = p.current_mw / p.rating_mw
          const pColor = p.status === 'overloaded' ? 'var(--red)' :
                         p.status === 'warning'    ? 'var(--amber)' : 'var(--green)'
          return (
            <div key={name} className="feeder-item"
                 style={p.status === 'overloaded' ? { borderColor: 'rgba(239,68,68,0.3)' } : {}}>
              <span style={{ color: 'var(--white)', fontSize: '0.65rem' }}>{name}</span>
              <div style={{ flex: 1, margin: '0 8px' }}>
                <div className="progress-bar" style={{ height: '3px' }}>
                  <div style={{
                    width: `${Math.min(100, ratio * 100)}%`, height: '100%',
                    background: pColor, borderRadius: 2,
                    transition: 'width 0.4s',
                  }} />
                </div>
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.63rem', color: pColor }}>
                {p.current_mw?.toFixed(0)}/{p.rating_mw}MW
              </span>
            </div>
          )
        })}
      </div>

      {/* Footer stats */}
      <div style={{ display: 'flex', gap: 12, marginTop: 8, fontSize: '0.65rem', color: 'var(--muted)' }}>
        <span>Mode: <span style={{ color: modeColor, fontFamily: 'var(--font-mono)' }}>{mode.toUpperCase()}</span></span>
        <span>Rebalances: <span style={{ color: 'var(--blue)', fontFamily: 'var(--font-mono)' }}>{rebalances}</span></span>
        {shedding && (
          <span>Industrial: <span style={{ color: 'var(--red)', fontFamily: 'var(--font-mono)' }}>
            {(data.shed_mw_industrial || 0).toFixed(0)}MW
          </span></span>
        )}
      </div>
    </div>
  )
}
