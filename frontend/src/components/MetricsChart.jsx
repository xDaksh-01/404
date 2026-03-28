import { useCallback, useState, useRef, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts'
import { TrendingUp } from 'lucide-react'
import { api } from '../services/api.js'
import { useInterval } from '../hooks/useInterval.js'

const MAX_POINTS = 60

const LINES = [
  { key: 'load_pct',    label: 'Load %',          color: '#00d4ff', unit: '%'  },
  { key: 'max_temp',    label: 'Max Temp (°C)',    color: '#f59e0b', unit: '°C' },
  { key: 'voltage',     label: 'Avg Voltage (V)',  color: '#22c55e', unit: 'V',  yAxisId: 'v' },
  { key: 'fault_prob',  label: 'Fault Prob ×100',  color: '#ef4444', unit: '',  },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border-bright)',
      borderRadius: 8, padding: '8px 12px', fontSize: '0.68rem',
    }}>
      <div style={{ color: 'var(--muted)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color, fontFamily: 'var(--font-mono)', marginBottom: 2 }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  )
}

export default function MetricsChart({ className }) {
  const dataRef = useRef([])
  const [data, setData] = useState([])
  const [anomalyTimes, setAnomalyTimes] = useState([])

  const refresh = useCallback(async () => {
    try {
      const [summary, transformers, fd] = await Promise.all([
        api.gridSummary(),
        api.transformers(),
        api.faultDetection(),
      ])

      const now = new Date().toLocaleTimeString('en', { hour12: false,
        hour: '2-digit', minute: '2-digit', second: '2-digit' })

      const ts  = transformers?.transformers || []
      const maxTemp = ts.length ? Math.max(...ts.map(t => t.temperature_c || 0)) : 0
      const faultProb = (fd?.fault_probability_max || 0) * 100

      const point = {
        time:       now,
        load_pct:   summary?.grid_load_percent || 0,
        max_temp:   maxTemp,
        voltage:    summary?.grid_voltage_avg || 230,
        fault_prob: parseFloat(faultProb.toFixed(2)),
      }

      // Track anomaly times (fault_prob > 40)
      if (faultProb > 40) {
        setAnomalyTimes(prev => [...prev.slice(-10), now])
      }

      dataRef.current = [...dataRef.current.slice(-(MAX_POINTS - 1)), point]
      setData([...dataRef.current])
    } catch (error) {
      console.error('MetricsChart refresh error:', error)
    }
  }, [])

  useInterval(refresh, 5000)

  // Initial load
  useEffect(() => { refresh() }, [refresh])

  return (
    <div className={`chart-container ${className || ''}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="card-title">
          <TrendingUp size={13} style={{ color: 'var(--blue)' }} />
          <span style={{ color: 'var(--blue)' }}>Live Metrics Chart</span>
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          {LINES.map(l => (
            <div key={l.key} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.65rem' }}>
              <div style={{ width: 20, height: 2, background: l.color, borderRadius: 1 }} />
              <span style={{ color: 'var(--muted)' }}>{l.label}</span>
            </div>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="time"
            tick={{ fill: 'var(--muted)', fontSize: '0.58rem', fontFamily: 'var(--font-mono)' }}
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            interval="preserveStartEnd"
          />
          <YAxis
            yAxisId="default"
            tick={{ fill: 'var(--muted)', fontSize: '0.6rem', fontFamily: 'var(--font-mono)' }}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
          />
          <YAxis
            yAxisId="v"
            orientation="right"
            tick={{ fill: 'var(--muted)', fontSize: '0.6rem', fontFamily: 'var(--font-mono)' }}
            tickLine={false}
            axisLine={false}
            domain={[180, 250]}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Anomaly reference lines */}
          {anomalyTimes.map((t, i) => (
            <ReferenceLine key={i} x={t} yAxisId="default"
                          stroke="rgba(239,68,68,0.5)" strokeWidth={1.5}
                          strokeDasharray="4 2" />
          ))}

          <Line yAxisId="default" type="monotone" dataKey="load_pct"
                stroke="#00d4ff" strokeWidth={1.5} dot={false}
                name="Load %" animationDuration={300} />
          <Line yAxisId="default" type="monotone" dataKey="max_temp"
                stroke="#f59e0b" strokeWidth={1.5} dot={false}
                name="Max Temp °C" animationDuration={300} />
          <Line yAxisId="v" type="monotone" dataKey="voltage"
                stroke="#22c55e" strokeWidth={1.5} dot={false}
                name="Voltage V" animationDuration={300} />
          <Line yAxisId="default" type="monotone" dataKey="fault_prob"
                stroke="#ef4444" strokeWidth={1.5} dot={false}
                name="Fault Prob ×100" animationDuration={300}
                strokeDasharray="4 2" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
