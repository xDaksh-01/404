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
    lastUpdated: '-'
  })

  const refresh = useCallback(async () => {
    const [s, t, z, l, a] = await Promise.all([
      api.gridSummary(),
      api.transformers(),
      api.allZones(),
      api.remediationLog(50),
      api.alerts(100)
    ])

    setData({
      summary: s,
      transformers: t?.transformers || [],
      zones: z || {},
      remediationLog: l || [],
      alerts: a || [],
      lastUpdated: new Date().toLocaleTimeString()
    })
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
