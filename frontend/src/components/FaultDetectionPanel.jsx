import { useCallback, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { api } from '../services/api.js'
import { useInterval } from '../hooks/useInterval.js'

function FaultGauge({ value, label, max = 1, dangerThreshold = 0.5 }) {
  const pct  = Math.min(100, (value / max) * 100)
  const color = value >= dangerThreshold ? 'var(--red)' :
                value >= dangerThreshold * 0.6 ? 'var(--amber)' : 'var(--green)'
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span className="label">{label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color }}>
          {value.toFixed(3)}
        </span>
      </div>
      <div className="progress-bar">
        <div style={{
          width: `${pct}%`, height: '100%', borderRadius: '3px',
          background: `linear-gradient(90deg, ${color}88, ${color})`,
          boxShadow: value > dangerThreshold ? `0 0 8px ${color}66` : 'none',
          transition: 'width 0.4s ease, background 0.3s',
        }} />
      </div>
    </div>
  )
}

export default function FaultDetectionPanel() {
  const [data, setData] = useState(null)

  const refresh = useCallback(async () => {
    const d = await api.faultDetection()
    if (d) setData(d)
  }, [])

  useInterval(refresh, 3000)

  if (!data) return (
    <div className="card">
      <div className="card-header">
        <div className="card-title"><AlertTriangle size={13} />Fault Detection</div>
      </div>
      <div style={{ color: 'var(--muted)', fontSize: '0.75rem', padding: '20px 0', textAlign: 'center' }}>
        Connecting...
      </div>
    </div>
  )

  const arcScore  = data.arc_signature_score_max || 0
  const faultProb = data.fault_probability_max   || 0
  const residual  = data.residual_current_ma_max || 0
  const thd       = data.current_thd_percent_avg || 0
  const insul     = data.insulation_resistance_min_mohm || 90
  const active    = data.active_faults || []
  const count     = data.active_faults_count || 0

  const isHighAlert = arcScore > 0.5 || faultProb > 0.5 || residual > 300

  return (
    <div className="card" style={{
      borderColor: isHighAlert ? 'rgba(239,68,68,0.4)' : 'var(--border)',
    }}>
      <div className="card-header">
        <div className="card-title" style={{ color: isHighAlert ? 'var(--red)' : 'var(--blue)' }}>
          <AlertTriangle size={13} />
          Fault Detection
        </div>
        {count > 0 ? (
          <span className="badge critical">{count} ACTIVE</span>
        ) : (
          <span className="badge healthy">CLEAR</span>
        )}
      </div>

      <FaultGauge value={faultProb} label="Fault Probability" dangerThreshold={0.4} />
      <FaultGauge value={arcScore}  label="Arc Signature Score" dangerThreshold={0.45} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 10 }}>
        <div>
          <div className="label" style={{ marginBottom: 3 }}>Residual Current</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600,
            color: residual > 300 ? 'var(--red)' : residual > 100 ? 'var(--amber)' : 'var(--green)',
          }}>
            {residual.toFixed(0)} <span style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>mA</span>
          </div>
        </div>
        <div>
          <div className="label" style={{ marginBottom: 3 }}>Min Insulation</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600,
            color: insul < 10 ? 'var(--red)' : insul < 50 ? 'var(--amber)' : 'var(--green)',
          }}>
            {insul.toFixed(1)} <span style={{ fontSize: '0.65rem', color: 'var(--muted)' }}>MΩ</span>
          </div>
        </div>
        <div>
          <div className="label" style={{ marginBottom: 3 }}>Current THD</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600,
            color: thd > 20 ? 'var(--red)' : thd > 10 ? 'var(--amber)' : 'var(--muted)',
          }}>
            {thd.toFixed(1)}<span style={{ fontSize: '0.65rem' }}>%</span>
          </div>
        </div>
        <div>
          <div className="label" style={{ marginBottom: 3 }}>Total Detected</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 600, color: 'var(--blue)' }}>
            {data.total_faults_detected || 0}
          </div>
        </div>
      </div>

      {active.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="label" style={{ marginBottom: 5 }}>Active Faults</div>
          {active.slice(0, 3).map((f, i) => (
            <div key={i} className="feeder-item fault">
              <span style={{ color: 'var(--red)', fontSize: '0.65rem' }}>⚡ {f.feeder_id}</span>
              <span style={{ color: 'var(--amber)', textTransform: 'uppercase', fontSize: '0.6rem' }}>
                {f.fault_type}
              </span>
              <span style={{ color: 'var(--muted)' }}>
                {(f.probability * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
