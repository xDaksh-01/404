import { Activity, Gauge, Map, TrendingUp, Zap } from 'lucide-react'
import { useGrid } from '../App.jsx'
import LoadBalancerPanel from '../components/LoadBalancerPanel.jsx'

const ZONE_ORDER = ['north', 'south', 'east', 'west', 'central']

function formatNumber(value, digits = 1) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

function getLoadState(load = 0) {
  if (load > 90) return 'critical'
  if (load > 75) return 'warning'
  return 'healthy'
}

function getToneClass(tone) {
  if (tone === 'healthy') return 'status-healthy'
  if (tone === 'warning') return 'status-warning'
  if (tone === 'critical') return 'status-critical'
  if (tone === 'cyan') return 'status-cyan'
  return 'status-muted'
}

function OverviewStat({ label, value, unit, color = 'cyan' }) {
  return (
    <div className="overview-stat">
      <div className="overview-stat-label">{label}</div>
      <div className="overview-stat-value-row">
        <span className={`overview-stat-value ${color}`}>{value}</span>
        {unit ? <span className="overview-stat-unit">{unit}</span> : null}
      </div>
    </div>
  )
}

function OverviewBadge({ children, tone = 'cyan' }) {
  return <span className={`overview-badge ${tone}`}>{children}</span>
}

function PowerFactorRing({ value = 0.93 }) {
  const percent = 0
  const angle = (percent / 100) * 360

  return (
    <div className="overview-ring-block">
      <div
        className="overview-ring"
        style={{
          background: `conic-gradient(#22c55e 0deg ${angle}deg, rgba(51,65,85,0.72) ${angle}deg 360deg)`,
        }}
      >
        <div className="overview-ring-inner" />
      </div>
      <div className="overview-ring-label">
        Power
        <br />
        Factor
      </div>
    </div>
  )
}

function TapBars({ activeIndex }) {
  return (
    <div className="overview-tap-bars">
      {Array.from({ length: 9 }).map((_, index) => {
        const active = index === activeIndex || (activeIndex === 6 && index === 5)
        return (
          <div
            key={index}
            className={`overview-tap-segment ${active ? 'active' : ''}`}
          />
        )
      })}
    </div>
  )
}

export default function SystemOverview() {
  const { summary, zones } = useGrid()
  const voltage = summary?.voltage_regulator || {}

  const loadMW = summary?.grid_total_load_mw
  const capMW = summary?.grid_capacity_mw
  const avgTemp = summary?.avg_transformer_temp
  const onlineNodes = summary?.services_online_count
  const risk = String(summary?.overload_risk || 'PENDING').toUpperCase()
  const riskTone = risk === 'CRITICAL' ? 'red' : risk === 'HIGH' ? 'amber' : risk === 'MEDIUM' ? 'cyan' : 'green'
  const gridLoadPercent = summary?.grid_load_percent
  const latency = summary?.last_poll_latency_ms

  const pf = voltage.grid_power_factor_avg
  const avgVoltage = voltage.grid_voltage_avg_v
  const minVoltage = voltage.grid_voltage_min_v
  const tapLocked = !!voltage.tap_changer_locked
  const violations = voltage.voltage_violations_count || 0
  const activeBanks = voltage.capacitor_banks_active_count || 0
  const tapsPerHour = voltage.tap_changes_per_hour || 0
  const profiles = voltage.zone_voltage_profiles || {}

  const zoneVoltageData = [
    { name: 'Central', key: 'central' },
    { name: 'East', key: 'east' },
    { name: 'North', key: 'north' },
    { name: 'South', key: 'south' },
    { name: 'West', key: 'west' },
  ].map((zone) => {
    const profile = profiles[zone.key] || {}
    const tapPosition = profile.tap_position
    return {
      ...zone,
      voltage: profile.avg_v,
      taps: typeof tapPosition === 'number' ? tapPosition : null,
      activeIndex: typeof tapPosition === 'number'
        ? tapPosition > 0
          ? Math.min(8, 4 + tapPosition)
          : tapPosition < 0
            ? Math.max(0, 4 + tapPosition)
            : -1
        : -1,
    }
  })

  const zoneStatusData = ZONE_ORDER.map((key) => {
    const zone = zones[key] || {}
    const load = zone.load_percent
    return {
      key,
      name: key.toUpperCase(),
      load,
      mw: zone.current_load_mw,
      freq: typeof zone.frequency_hz === 'number' ? `${formatNumber(zone.frequency_hz, 3)}Hz` : '—',
      voltage: typeof zone.voltage_avg_v === 'number' ? `${formatNumber(zone.voltage_avg_v, 0)}V` : '—',
      events: zone.active_events || 0,
      overloaded: typeof load === 'number' ? load > 85 || zone.substation_status === 'tripped' : false,
    }
  })

  const overloadedCount = zoneStatusData.filter((zone) => zone.overloaded).length
  const totalZoneMW = zoneStatusData.reduce((sum, zone) => sum + (zone.mw || 0), 0)

  return (
    <div className="page-content system-overview-page">
      <div className="system-overview-top-grid">
        <section className="overview-panel overview-card">
          <div className="overview-card-header">
            <div className="overview-card-title">
              <Activity size={16} />
              <span>System Overview</span>
            </div>
            <div className="overview-card-sidecopy">
              <div>{risk}</div>
              <div>Risk</div>
            </div>
          </div>

          <div className="overview-stats-grid">
            <OverviewStat label="Total Load" value={formatNumber(loadMW, 0)} unit="MW" />
            <OverviewStat label="Capacity" value={formatNumber(capMW, 0)} unit="MW" color="muted" />
            <OverviewStat label={<>Avg Transformer<br />Temp</>} value={formatNumber(avgTemp, 1)} unit="°C" />
            <OverviewStat label="Nodes Online" value={onlineNodes} unit="/5" color="green" />
          </div>

          <div className="overview-load-section">
            <div className="overview-load-head">
              <div className="overview-stat-label">Grid Load</div>
              <div className={`overview-load-percent ${getToneClass(getLoadState(gridLoadPercent || 0))}`}>
                {typeof gridLoadPercent === 'number' ? `${gridLoadPercent.toFixed(1)}%` : '—'}
              </div>
            </div>
            <div className="overview-load-track">
              <div
                className={`overview-load-fill ${getLoadState(gridLoadPercent || 0)}`}
                style={{ width: `${Math.min(100, gridLoadPercent || 0)}%` }}
              />
            </div>
            <div className="overview-meta-row">
              <div className="overview-meta-item">
                <Zap size={12} />
                <span>{typeof gridLoadPercent === 'number' ? `${gridLoadPercent.toFixed(1)}% utilization` : 'Awaiting utilization data'}</span>
              </div>
              <div className="overview-meta-item success">
                <TrendingUp size={12} />
                <span>{typeof latency === 'number' ? `Latency ${formatNumber(latency, 1)}ms` : 'Latency pending'}</span>
              </div>
            </div>
          </div>
        </section>

        <section className="overview-panel overview-card">
          <div className="overview-card-header voltage">
            <div className="overview-card-title">
              <Gauge size={16} />
              <span>Voltage Regulator</span>
            </div>
            <div className="overview-badge-row">
              {tapLocked ? <OverviewBadge tone="amber">Tap Locked</OverviewBadge> : null}
              {violations > 0 ? <OverviewBadge tone="red">{violations} Violations</OverviewBadge> : null}
              {!tapLocked && violations === 0 ? <OverviewBadge tone={riskTone}>{risk} Risk</OverviewBadge> : null}
            </div>
          </div>

          <div className="overview-voltage-hero">
            <PowerFactorRing value={pf} />
            <div className="overview-voltage-summary">
              <div className="overview-stat-label">Avg Voltage</div>
              <div className="overview-voltage-number">{formatNumber(avgVoltage, 1)}</div>
              <div className="overview-voltage-subcopy">
                {typeof avgVoltage === 'number' ? `V (min ${formatNumber(minVoltage, 1)})` : 'Voltage data pending'}
              </div>
              <div className="overview-voltage-subcopy">
                {typeof avgVoltage === 'number'
                  ? `${activeBanks} banks active · ${formatNumber(tapsPerHour, 1)} taps/hr`
                  : 'Tap and capacitor data pending'}
              </div>
            </div>
          </div>

          <div className="overview-zone-voltage-list">
            {zoneVoltageData.map((zone) => (
              <div key={zone.name} className="overview-zone-voltage-row">
                <div className="overview-zone-voltage-name">{zone.name}</div>
                <div className="overview-zone-voltage-reading">{formatNumber(zone.voltage, 1)}V</div>
                <TapBars activeIndex={zone.activeIndex} />
                <div className="overview-zone-voltage-taps">
                  {typeof zone.taps === 'number' ? (zone.taps === 0 ? '0' : `${zone.taps > 0 ? '+' : ''}${zone.taps}`) : '—'}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="overview-panel overview-card overview-zone-status-panel">
        <div className="overview-card-header">
          <div className="overview-card-title">
            <Map size={16} />
            <span>Zone Status</span>
          </div>
          <div className="overview-zone-status-meta">
            {overloadedCount > 0 ? (
              <OverviewBadge tone="amber">{overloadedCount} Overloaded</OverviewBadge>
            ) : (
              <OverviewBadge tone="green">Nominal</OverviewBadge>
            )}
            <div className="overview-total-mw">
              {totalZoneMW > 0 ? formatNumber(totalZoneMW, 0) : '—'} <span>MW total</span>
            </div>
          </div>
        </div>

        <div className="overview-zone-status-list">
          {zoneStatusData.map((zone) => (
            <div key={zone.key} className="overview-zone-status-row">
              <div className="overview-zone-name">{zone.name}</div>
              <div className="overview-zone-load-block">
                <div className="overview-zone-load-head">
                  <span className={`overview-zone-load-value ${getToneClass(zone.overloaded ? 'critical' : 'healthy')}`}>
                    {formatNumber(zone.load, 1)}
                  </span>
                  <span className="overview-zone-load-mw">
                    {typeof zone.mw === 'number' ? `${formatNumber(zone.mw, 0)}MW` : '—'}
                  </span>
                </div>
                <div className="overview-zone-load-track">
                  <div
                    className={`overview-zone-load-fill ${zone.overloaded ? 'critical' : 'healthy'}`}
                    style={{ width: `${Math.min(100, zone.load || 0)}%` }}
                  />
                </div>
              </div>
              <div className="overview-zone-side-stats">
                <div className="status-warning">{zone.freq}</div>
                <div className="status-muted">{zone.voltage}</div>
                <div className="status-warning">{zone.events} events</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <LoadBalancerPanel className="overview-panel overview-card overview-load-balancer-panel" />
    </div>
  )
}