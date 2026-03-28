import GridOverview from '../components/GridOverview.jsx'
import VoltagePanel from '../components/VoltagePanel.jsx'
import ZonePanel from '../components/ZonePanel.jsx'
import LoadBalancerPanel from '../components/LoadBalancerPanel.jsx'
import { useGrid } from '../App.jsx'

export default function SystemOverview() {
  const { summary } = useGrid()

  return (
    <div className="page-content grid-layout">
      {/* Overview stats */}
      <GridOverview summary={summary} className="span-2" />
      <VoltagePanel />
      
      {/* Zone Status */}
      <ZonePanel className="span-3" />
      
      {/* Load balancing stats */}
      <LoadBalancerPanel className="span-2" />
    </div>
  )
}
