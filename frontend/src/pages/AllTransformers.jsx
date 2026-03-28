import TransformerPanel from '../components/TransformerPanel.jsx'

export default function AllTransformers() {
  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">City-Wide Transformer Status</h1>
        <p className="page-subtitle">Real-time health monitoring for all 16 distribution transformers.</p>
      </div>
      
      {/* 
        The TransformerPanel currently handles 16. 
        I'll wrap it in a container that allows it to span the full width 
        now that it's on its own page.
      */}
      <div className="full-width-panel">
        <TransformerPanel className="no-card-header" />
      </div>
      
      <div className="legend-strip mono">
        <div className="legend-item"><span className="dot green" /> Healthy (45-75%)</div>
        <div className="legend-item"><span className="dot amber" /> Warning (75-85%)</div>
        <div className="legend-item"><span className="dot red" /> Critical (&gt;90% or &gt;90°C)</div>
      </div>
    </div>
  )
}
