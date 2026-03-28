import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { api } from './services/api.js'
import { useInterval } from './hooks/useInterval.js'

// Components
import Sidebar from './components/Sidebar.jsx'
import TopBar from './components/TopBar.jsx'

// Pages
import SystemOverview from './pages/SystemOverview.jsx'
import AllTransformers from './pages/AllTransformers.jsx'
import ZoneDetails from './pages/ZoneDetails.jsx'
import LogsFixes from './pages/LogsFixes.jsx'

// Create Context
const GridContext = createContext()

export function useGrid() {
  return useContext(GridContext)
}

function GridProvider({ children }) {
  const [data, setData] = useState({
    summary: null,
    transformers: [],
    zones: {},
    remediationLog: [],
    alerts: [],
    lastUpdated: '-',
    connected: false,
  })

  const refresh = useCallback(async () => {
    try {
      const results = await Promise.allSettled([
        api.gridSummary(),
        api.transformers(),
        api.allZones(),
        api.remediationLog(50),
        api.alerts(100)
      ])

      const s = results[0].status === 'fulfilled' && results[0].value ? results[0].value : null
      const t = results[1].status === 'fulfilled' && results[1].value ? results[1].value : null
      const z = results[2].status === 'fulfilled' && results[2].value ? results[2].value : null
      const l = results[3].status === 'fulfilled' && results[3].value ? results[3].value : null
      const a = results[4].status === 'fulfilled' && results[4].value ? results[4].value : null

      // Preserve existing data — only update fields when we got a valid response
      setData(prev => ({
        summary:        s !== null ? s : prev.summary,
        transformers:   t !== null ? (t?.transformers || []) : prev.transformers,
        zones:          z !== null ? z : prev.zones,
        remediationLog: l !== null ? l : prev.remediationLog,
        alerts:         a !== null ? a : prev.alerts,
        lastUpdated:    s !== null ? new Date().toLocaleTimeString() : prev.lastUpdated,
        connected:      s !== null,
      }))
    } catch (error) {
      console.error('GridProvider refresh error:', error)
      // Keep ALL existing data on error
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  useInterval(refresh, 3000) // 3s for real-time feel

  return (
    <GridContext.Provider value={data}>
      {children}
    </GridContext.Provider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <GridProvider>
        <AppContent />
      </GridProvider>
    </BrowserRouter>
  )
}

function AppContent() {
  const { summary, lastUpdated } = useGrid()
  
  return (
    <div className="app-container">
      <Sidebar />
      
      <main className="main-content">
        <TopBar summary={summary} lastUpdated={lastUpdated} />
        
        <Routes>
          <Route path="/" element={<SystemOverview />} />
          <Route path="/transformers" element={<AllTransformers />} />
          <Route path="/zones" element={<ZoneDetails />} />
          <Route path="/logs" element={<LogsFixes />} />
        </Routes>
      </main>
    </div>
  )
}
