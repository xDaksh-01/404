import { Download } from 'lucide-react'
import AlertsFeed from '../components/AlertsFeed.jsx'
import RemediationLog from '../components/RemediationLog.jsx'
import { useGrid } from '../App.jsx'

export default function LogsFixes() {
  const { remediationLog: entries } = useGrid()

  const handleDownload = () => {
    if (!entries.length) return
    const headers = ['ID', 'Timestamp', 'Zone', 'Fault', 'Status', 'MTTR_s', 'Success']
    const csvContent = [
      headers.join(','),
      ...entries.map(e => [
        e.id,
        e.timestamp_display,
        e.zone || 'N/A',
        e.fault_type,
        e.status,
        e.total_time_s || '-',
        e.status === 'RESOLVED' ? 'YES' : 'NO'
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.setAttribute('href', url)
    link.setAttribute('download', `grid_remediation_report_${new Date().getTime()}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Calculate live stats
  const total = entries.length
  const resolved = entries.filter(e => e.status === 'RESOLVED')
  const times = resolved.map(e => e.total_time_s).filter(Boolean)
  const avgMTTR = times.length ? (times.reduce((a, b) => a + b, 0) / times.length).toFixed(1) : '0.0'
  const slaComp = total > 0 ? ((resolved.filter(e => e.total_time_s <= 15).length / total) * 100).toFixed(0) : '100'

  return (
    <div className="page-content control-page">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div>
          <div className="page-eyebrow">Remediation Layer</div>
          <h1 className="page-title">Fault Logs & Remediation Engine</h1>
          <p className="page-subtitle">Real-time MTTR tracking and session persistence.</p>
        </div>
        <button className="btn btn-outline" onClick={handleDownload} disabled={!entries.length}>
          <Download size={14} />
          <span>DOWNLOAD REPORT</span>
        </button>
      </div>

      <div className="logs-layout-side">
        <AlertsFeed title="System Logs & Anomalies" />
        <RemediationLog title="Remediation Statistics & Solutions" />
      </div>

      <div className="logs-summary-bar">
        <div className="log-stat-card">
          <div className="stat-label">TOTAL FAULTS DETECTED</div>
          <div className="stat-number mono text-blue">{total}</div>
        </div>
        <div className="log-stat-card">
          <div className="stat-label">AVG MTTR (Mean Time To Resolve)</div>
          <div className="stat-number mono text-amber">{avgMTTR}s</div>
        </div>
        <div className="log-stat-card">
          <div className="stat-label">SLA COMPLIANCE (15s Window)</div>
          <div className="stat-number mono text-green">{slaComp}%</div>
        </div>
      </div>
    </div>
  )
}
