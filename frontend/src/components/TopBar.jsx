import { Play, Square, Activity, Clock } from 'lucide-react'
import { api } from '../services/api.js'
import { useState, useEffect } from 'react'

function StatusBadge({ online }) {
  const s = online ? "ONLINE" : "READY"
  const cls = online ? 'healthy' : 'warning'
  const dot = online ? 'green' : 'amber'
  return (
    <span className={`badge ${cls}`} style={{ padding: '4px 12px', fontSize: '0.75rem', letterSpacing: '0.05em' }}>
      <span className={`dot ${dot}`} style={{ width: 8, height: 8 }} />
      {s}
    </span>
  )
}

function UptimeClock({ seconds }) {
  if (!seconds || seconds < 0) return null
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  const parts = [
    hrs > 0 ? String(hrs).padStart(2, '0') : null,
    String(mins).padStart(2, '0'),
    String(secs).padStart(2, '0')
  ].filter(Boolean)
  
  return (
    <div className="uptime-clock text-blue mono" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', fontWeight: 600 }}>
      <Clock size={12} />
      <span>{parts.join(':')}</span>
    </div>
  )
}

export default function TopBar({ summary, lastUpdated }) {
  const [loading, setLoading] = useState(false)
  const [localUptime, setLocalUptime] = useState(0)
  
  const isSimulating = summary?.is_simulating || false
  const serverUptime = summary?.simulation_uptime_s || 0

  // Sync local timer with server uptime
  useEffect(() => {
    setLocalUptime(serverUptime)
  }, [serverUptime])

  // Tick the clock locally for smoothness
  useEffect(() => {
    if (!isSimulating) {
      setLocalUptime(0)
      return
    }
    const timer = setInterval(() => {
      setLocalUptime(u => u + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [isSimulating])

  const handleStart = () => {} // Removed
  const handleStop = () => {} // Removed

  const systemStatus = summary?.status_text || 'UNKNOWN'
  const activeAlerts = summary?.active_alerts_count || 0
  const servicesOnline = summary?.services_online_count || 0
  const isOnline = !!summary

  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <div className="top-bar-stat">
          <span className="stat-label">SYSTEM STATUS</span>
          <StatusBadge online={isOnline} />
        </div>

        {isOnline && (
          <>
            <div className="top-bar-divider" />
            <div className="top-bar-stat">
              <span className="stat-label">LIVE UPTIME</span>
              <UptimeClock seconds={localUptime} />
            </div>
          </>
        )}
      </div>

      <div className="top-bar-right">
        <div className="top-bar-stat">
          <span className="stat-label">ALERTS</span>
          <span className={`stat-value mono ${activeAlerts > 0 ? 'status-critical' : 'status-healthy'}`}>
            {activeAlerts}
          </span>
        </div>
        
        <div className="time-indicator mono">
          {lastUpdated}
        </div>
      </div>
    </header>
  )
}
