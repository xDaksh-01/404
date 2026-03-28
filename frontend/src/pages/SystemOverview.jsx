import GridOverview from '../components/GridOverview.jsx'
import VoltagePanel from '../components/VoltagePanel.jsx'
import ZonePanel from '../components/ZonePanel.jsx'
import LoadBalancerPanel from '../components/LoadBalancerPanel.jsx'
import { useGrid } from '../App.jsx'

export default function SystemOverview() {
  const { summary } = useGrid()

  return (
    <div className="page-content grid-layout">
      {/* Overview stats - Main Grid Summary */}
      <GridOverview className="span-2" />
      
      {/* Voltage Regulator - Stability Metrics */}
      <VoltagePanel className="span-1" />
      
      {/* Load Balancing - Redistribution Logic */}
      <LoadBalancerPanel className="span-1" />
    </div>
  )
}
