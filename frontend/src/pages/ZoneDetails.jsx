import ZonePanel from '../components/ZonePanel.jsx'
import LoadBalancerPanel from '../components/LoadBalancerPanel.jsx'

export default function ZoneDetails() {
  return (
    <div className="page-content control-page">
      <div className="page-header">
        <div className="page-eyebrow">Distribution Layer</div>
        <h1 className="page-title">Distribution Zones & Feeders</h1>
        <p className="page-subtitle">Real-time load balancing and zone-specific metrics.</p>
      </div>

      <div className="zone-grid-full">
        <ZonePanel className="span-3" />
        <LoadBalancerPanel className="span-1" />
      </div>
    </div>
  )
}
