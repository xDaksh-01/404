import ZonePanel from '../components/ZonePanel.jsx'
import LoadBalancerPanel from '../components/LoadBalancerPanel.jsx'
import { useGrid } from '../App.jsx'

export default function ZoneDetails() {
  const { summary } = useGrid()

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Distribution Zones & Feeders</h1>
        <p className="page-subtitle">Real-time load balancing and zone-specific metrics.</p>
      </div>

      <div className="zone-grid-full">
        <ZonePanel className="span-3" />
        <LoadBalancerPanel className="span-1" />
      </div>

      <div className="zone-map-placeholder">
        <div className="mono title-small" style={{ color: summary?.system_status > 0 ? 'var(--amber)' : 'var(--blue)' }}>
          GEOSPATIAL DISTRIBUTION OVERVIEW
        </div>
        <div className="map-mock">
          {/* A simple ASCII map of zones */}
          <pre style={{ color: 'var(--text-dim)', fontSize: '10px' }}>
{`
      [ NORTH ]
          |
[ WEST ]--[ CENTRAL ]--[ EAST ]
          |
      [ SOUTH ]
`}
          </pre>
        </div>
      </div>
    </div>
  )
}
