import TransformerPanel from '../components/TransformerPanel.jsx'
import { useGrid } from '../App.jsx'

export default function TransformerInfo() {
  const { transformers } = useGrid()

  return (
    <div className="page-content control-page transformer-info-page">
      <div className="transformer-info-header">
        <div className="page-eyebrow">Transformer Layer</div>
        <h1 className="transformer-info-title">City-Wide Transformer Status</h1>
        <p className="transformer-info-subtitle">
          Real-time health monitoring for all distribution transformers.
        </p>
      </div>

      <TransformerPanel className="transformer-info-board" />

      <div className="transformer-info-legend">
        <div className="transformer-info-legend-item">
          <span className="dot green" />
          <span>Healthy (45-75%)</span>
        </div>
        <div className="transformer-info-legend-item">
          <span className="dot amber" />
          <span>Warning (75-85%)</span>
        </div>
        <div className="transformer-info-legend-item">
          <span className="dot red" />
          <span>Critical (&gt;90% or &gt;90°C)</span>
        </div>
      </div>
    </div>
  )
}
