import TransformerPanel from '../components/TransformerPanel.jsx'
import { useGrid } from '../App.jsx'

export default function TransformerInfo() {
  const { transformers } = useGrid()

  const criticalCount = transformers.filter((t) => (t.load_percent || 0) > 85).length
  const warningCount = transformers.filter((t) => (t.load_percent || 0) > 75 && (t.load_percent || 0) <= 85).length
  const avgLoad = transformers.length
    ? transformers.reduce((sum, t) => sum + (t.load_percent || 0), 0) / transformers.length
    : 0
  const hottest = transformers.length
    ? Math.max(...transformers.map((t) => t.temperature_c || 0))
    : 0

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Transformer Information</h1>
        <p className="page-subtitle">
          Full transformer inventory with load, temperature, voltage, and live health status.
        </p>
      </div>

      <div className="logs-summary-bar" style={{ marginBottom: 24 }}>
        <div className="log-stat-card">
          <div className="stat-label">TOTAL TRANSFORMERS</div>
          <div className="stat-number mono text-blue">{transformers.length}</div>
        </div>
        <div className="log-stat-card">
          <div className="stat-label">AVERAGE LOAD</div>
          <div className="stat-number mono text-amber">{avgLoad.toFixed(1)}%</div>
        </div>
        <div className="log-stat-card">
          <div className="stat-label">HOTTEST UNIT</div>
          <div className="stat-number mono text-red">{hottest.toFixed(1)}°C</div>
        </div>
      </div>

      <div className="logs-summary-bar" style={{ marginBottom: 24 }}>
        <div className="log-stat-card">
          <div className="stat-label">CRITICAL</div>
          <div className="stat-number mono text-red">{criticalCount}</div>
        </div>
        <div className="log-stat-card">
          <div className="stat-label">WARNING</div>
          <div className="stat-number mono text-amber">{warningCount}</div>
        </div>
        <div className="log-stat-card">
          <div className="stat-label">HEALTHY</div>
          <div className="stat-number mono text-green">
            {Math.max(transformers.length - criticalCount - warningCount, 0)}
          </div>
        </div>
      </div>

      <TransformerPanel />
    </div>
  )
}
