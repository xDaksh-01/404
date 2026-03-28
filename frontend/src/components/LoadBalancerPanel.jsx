import { Share2 } from 'lucide-react'
import { useGrid } from '../App.jsx'

function formatValue(value, digits = 0) {
  return typeof value === 'number' && !Number.isNaN(value) ? value.toFixed(digits) : '—'
}

export default function LoadBalancerPanel({ className }) {
  const { summary } = useGrid()
  
  // Use summary from context which contains LB data
  const data = summary?.load_balancer || {
    total_demand_mw: 0,
    total_allocated_mw: 0,
    zones_overloaded_count: 0,
    load_shedding_active: false,
    transmission_mode: 'normal',
    rebalance_count_session: 0,
    transmission_paths: {}
  }
  const isConnected = !!(summary?.load_balancer && Object.keys(summary.load_balancer).length > 0)

  const demand    = data.total_demand_mw    || 0
  const allocated = data.total_allocated_mw || 0
  const balance   = demand > 0 ? (allocated / demand * 100) : 100
  const overloaded= data.zones_overloaded_count || 0
  const shedding  = data.load_shedding_active || false
  const mode      = data.transmission_mode || 'normal'
  const rebalances= data.rebalance_count_session || 0
  const paths     = data.transmission_paths || {}

  const demand = data?.total_demand_mw
  const allocated = data?.total_allocated_mw
  const balance = typeof demand === 'number' && demand > 0 && typeof allocated === 'number'
    ? (allocated / demand) * 100
    : null
  const overloaded = data?.zones_overloaded_count || 0
  const shedding = !!data?.load_shedding_active
  const mode = data?.transmission_mode ? String(data.transmission_mode).toUpperCase() : 'PENDING'
  const rebalances = data?.rebalance_count_session
  const paths = Object.entries(data?.transmission_paths || {})
  const modeClass = mode === 'NORMAL' ? 'status-healthy' : mode === 'BOTTLENECK' ? 'status-warning' : mode === 'SPLIT' ? 'status-critical' : 'status-muted'

  return (
    <div className={`${className || ''}`.trim()}>
      <div className="overview-card-header">
        <div className="overview-card-title">
          <Share2 size={16} />
          <span>Load Balancer</span>
        </div>
        <div className="overview-zone-status-meta">
          {shedding ? <span className="overview-badge amber">Shedding</span> : null}
          {overloaded > 0 ? (
            <span className="overview-badge red">{overloaded} Overloaded</span>
          ) : (
            <span className="overview-badge cyan">Awaiting Data</span>
          )}
        </div>
      </div>

      <div className="overview-load-balancer-stats">
        {[
          { label: 'Demand', value: formatValue(demand, 0), unit: 'MW', tone: 'cyan' },
          { label: 'Allocated', value: formatValue(allocated, 0), unit: 'MW', tone: 'cyan' },
          { label: 'Balance', value: balance === null ? '—' : balance.toFixed(1), unit: '%', tone: balance !== null && balance < 90 ? 'amber' : 'cyan' },
        ].map((item) => (
          <div key={item.label} className="overview-load-balancer-stat">
            <div className="overview-stat-label">{item.label}</div>
            <div className="overview-load-balancer-value-row">
              <span className={`overview-load-balancer-value ${item.tone}`}>{item.value}</span>
              <span className="overview-stat-unit">{item.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="overview-load-balancer-label">Transmission Paths</div>
      <div className="overview-load-balancer-paths">
        {paths.length === 0 ? (
          <div className="overview-load-balancer-empty">Awaiting transmission path data...</div>
        ) : paths.map(([name, path]) => {
          const current = path?.current_mw
          const rating = path?.rating_mw
          const ratio = typeof current === 'number' && typeof rating === 'number' && rating > 0 ? (current / rating) * 100 : 0
          const state = path?.status === 'overloaded' ? 'critical' : path?.status === 'warning' ? 'warning' : 'healthy'

          return (
            <div key={name} className="overview-load-balancer-path-row">
              <div className="overview-load-balancer-path-name">{name}</div>
              <div className="overview-load-balancer-path-bar">
                <div className="overview-load-balancer-track">
                  <div
                    className={`overview-load-balancer-fill ${state}`}
                    style={{ width: `${Math.min(100, ratio)}%` }}
                  />
                </div>
              </div>
              <div className={`overview-load-balancer-path-value ${state}`}>
                {typeof current === 'number' && typeof rating === 'number'
                  ? `${current.toFixed(0)}/${rating}MW`
                  : '—'}
              </div>
            </div>
          )
        })}
      </div>

      <div className="overview-load-balancer-footer">
        <span>Mode: <span className={`overview-load-balancer-footer-value ${modeClass}`}>{mode}</span></span>
        <span>Rebalances: <span className="overview-load-balancer-footer-accent">
          {typeof rebalances === 'number' ? rebalances : '—'}
        </span></span>
      </div>
    </div>
  )
}
