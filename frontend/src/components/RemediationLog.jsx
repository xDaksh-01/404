import { useState, useEffect } from 'react'
import { Bot } from 'lucide-react'
import { useGrid } from '../App.jsx'
import { api } from '../services/api.js'

function RemItem({ entry }) {
  const [expanded, setExpanded] = useState(false)
  const status = (entry.status || 'EXECUTING').toUpperCase()
  const actions = entry.actions_taken || []

  return (
    <div className="rem-item" onClick={() => setExpanded(!expanded)}
         style={{ cursor: 'pointer' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: 6 }}>
        <div>
          <div className="rem-fault-type">{entry.fault_type || '?'}</div>
          <div style={{ fontSize: '0.62rem', color: 'var(--muted)', marginTop: 2 }}>
            {entry.timestamp_display}
            {entry.zone && ` · ${entry.zone}`}
            {entry.transformer_id && ` · ${entry.transformer_id}`}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexShrink: 0 }}>
          <span className={`rem-status ${status}`}>{status}</span>
          {entry.total_time_s && (
            <span style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)',
                           color: entry.total_time_s <= 15 ? 'var(--green)' : 'var(--amber)' }}>
              {entry.total_time_s}s {entry.total_time_s <= 15 ? '✓' : '⚠'}
            </span>
          )}
        </div>
      </div>

      {expanded && actions.length > 0 && (
        <div className="rem-actions" style={{ marginTop: 8, paddingTop: 8,
                                              borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          {actions.map((a, i) => (
            <div key={i} className="rem-action">
              <span className={a.success ? 'ok' : 'fail'}>
                {a.success ? '✓' : '✗'}
              </span>
              <span style={{ color: 'var(--blue)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem' }}>
                {a.action}
              </span>
              {a.target && <span>→ {a.target}</span>}
            </div>
          ))}
          {entry.verify_details && (
            <div style={{ marginTop: 6, padding: '4px 8px',
                         background: 'rgba(255,255,255,0.04)', borderRadius: 4 }}>
              <div className="label" style={{ marginBottom: 3 }}>Verification</div>
              {Object.entries(entry.verify_details).map(([k,v]) => (
                <div key={k} style={{ fontSize: '0.63rem', color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>
                  {k}: <span style={{ color: v === true ? 'var(--green)' : v === false ? 'var(--red)' : 'var(--white)' }}>
                    {String(v)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function RemediationLog({ className }) {
  const [entries, setEntries] = useState([])
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true

    const refreshLog = async () => {
      try {
        const liveEntries = await api.remediationLog(50)
        if (!mounted) return

        if (liveEntries && Array.isArray(liveEntries)) {
          setEntries(liveEntries)
          setError(null)
        } else {
          setError('No remediation entries received')
        }
        setLastUpdated(new Date())
      } catch (err) {
        if (!mounted) return
        console.error('RemediationLog refresh failed', err)
        setError(err.message || 'Refresh error')
      }
    }

    refreshLog()
    const intervalId = setInterval(refreshLog, 2000)
    return () => { mounted = false; clearInterval(intervalId) }
  }, [])

  const resolved   = entries.filter(e => e.status === 'RESOLVED').length
  const under15    = entries.filter(e => e.total_time_s && e.total_time_s <= 15).length

  return (
    <div className={`card ${className || ''}`}>
      <div className="card-header">
        <div className="card-title">
          <Bot size={13} />
          ML Remediation Log
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {entries.length > 0 && (
            <>
              <span className="badge healthy">{resolved}/{entries.length} resolved</span>
              <span style={{ fontSize: '0.62rem', color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>
                {under15} under 15s
              </span>
            </>
          )}
          {lastUpdated && (
            <span style={{ fontSize: '0.62rem', color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          {error && (
            <span style={{ fontSize: '0.62rem', color: 'var(--red)', fontFamily: 'var(--font-mono)' }}>
              {error}
            </span>
          )}
        </div>
      </div>

      <div className="scroll-panel">
        {entries.length === 0 ? (
          <div style={{ color: 'var(--muted)', fontSize: '0.72rem', padding: '12px 0', textAlign: 'center' }}>
            Awaiting ML anomaly detection...
          </div>
        ) : entries.map((e, i) => (
          <RemItem key={`${e.id}-${i}`} entry={e} />
        ))
      }
      </div>
    </div>
  )
}
