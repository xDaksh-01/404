import GridOverview from '../components/GridOverview.jsx'
import VoltagePanel from '../components/VoltagePanel.jsx'
import LoadBalancerPanel from '../components/LoadBalancerPanel.jsx'

export default function SystemOverview() {
  return (
    <div className="page-content grid-layout">
      {/* Overview stats — spans left 2 cols */}
      <GridOverview className="span-2" />

      {/* Voltage Regulator — spans right 2 cols */}
      <VoltagePanel className="span-2" />

      {/* Load Balancer — full width row */}
      <LoadBalancerPanel className="span-4" />
    </div>
  )
}
