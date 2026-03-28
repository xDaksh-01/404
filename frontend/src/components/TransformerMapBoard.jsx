import { useEffect, useMemo, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'
import { useGrid } from '../App.jsx'

const ZONES = [
  {
    key: 'north',
    name: 'North Zone',
    description: 'Upper Bangalore belt toward the airport corridor',
    areas: [
      'Yelahanka',
      'Hebbal',
      'Jakkur',
      'Thanisandra',
      'Hennur',
      'Bagalur',
      'Devanahalli',
      'Sahakar Nagar',
      'RT Nagar',
    ],
    coords: [
      [13.18, 77.38],
      [13.1550, 77.6400],
      [13.1200, 77.7200],
      [13.0900, 77.7800],
      [13.0200, 77.8280],
      [12.9950, 77.7350],
      [12.9850, 77.6600],
      [12.9750, 77.6050],
      [12.9550, 77.5550],
      [13.0200, 77.3800],
    ],
    labelLatLng: [13.08, 77.64],
  },
  {
    key: 'west',
    name: 'West Zone',
    description: 'Older residential and industrial belt',
    areas: [
      'Rajajinagar',
      'Vijayanagar',
      'Nagarbhavi',
      'Basaveshwar Nagar',
      'Kengeri',
      'Magadi Road',
      'Peenya',
      'Yeshwanthpur',
    ],
    coords: [
      [13.0200, 77.3800],
      [12.9550, 77.5550],
      [12.9150, 77.5600],
      [12.8650, 77.5950],
      [12.8350, 77.6250],
      [12.7343, 77.5800],
      [12.7600, 77.3400],
      [12.8800, 77.3450],
      [12.9485, 77.3450],
      [13.0200, 77.3800],
    ],
    labelLatLng: [12.89, 77.49],
  },
  {
    key: 'central',
    name: 'Central Zone',
    description: 'Core city CBD with dense commercial load',
    areas: [
      'MG Road',
      'Brigade Road',
      'Shivajinagar',
      'Cubbon Park',
      'Vidhana Soudha',
      'Richmond Town',
      'Ulsoor',
      'Majestic',
    ],
    coords: [
      [12.9150, 77.5600],
      [12.9550, 77.5550],
      [12.9750, 77.6050],
      [12.9850, 77.6600],
      [12.9550, 77.6950],
      [12.9300, 77.7050],
      [12.8750, 77.6650],
      [12.8650, 77.6200],
      [12.8650, 77.5950],
    ],
    labelLatLng: [12.93, 77.63],
  },
  {
    key: 'east',
    name: 'East Zone',
    description: 'Tech and IT corridor, the highest-priority zone',
    areas: [
      'Whitefield',
      'Marathahalli',
      'KR Puram',
      'Mahadevapura',
      'Indiranagar',
      'CV Raman Nagar',
      'Brookefield',
      'Bellandur',
    ],
    coords: [
      [13.0200, 77.8280],
      [12.9500, 77.8200],
      [12.8800, 77.8000],
      [12.8000, 77.7500],
      [12.8400, 77.6900],
      [12.8750, 77.6650],
      [12.9300, 77.7050],
      [12.9550, 77.6950],
      [12.9850, 77.6600],
      [12.9950, 77.7350],
    ],
    labelLatLng: [12.95, 77.75],
  },
  {
    key: 'south',
    name: 'South Zone',
    description: 'Residential, startup, and education belt',
    areas: [
      'Jayanagar',
      'JP Nagar',
      'Banashankari',
      'BTM Layout',
      'Electronic City',
      'Bannerghatta Road',
      'Kanakapura Road',
      'Koramangala',
    ],
    coords: [
      [12.8650, 77.5950],
      [12.8650, 77.6200],
      [12.8750, 77.6650],
      [12.8400, 77.6900],
      [12.8000, 77.7500],
      [12.7343, 77.5800],
      [12.7900, 77.6000],
    ],
    labelLatLng: [12.81, 77.645],
  },
]

const TRANSFORMER_POINTS = {
  north: [
    { lat: 13.04, lng: 77.59 },
    { lat: 13.08, lng: 77.60 },
    { lat: 13.03, lng: 77.65 },
    { lat: 13.01, lng: 77.57 },
  ],
  west: [
    { lat: 12.98, lng: 77.53 },
    { lat: 12.95, lng: 77.50 },
    { lat: 12.93, lng: 77.56 },
  ],
  central: [
    { lat: 12.97, lng: 77.61 },
    { lat: 12.95, lng: 77.59 },
    { lat: 12.96, lng: 77.64 },
    { lat: 12.99, lng: 77.60 },
  ],
  east: [
    { lat: 12.98, lng: 77.73 },
    { lat: 12.95, lng: 77.67 },
    { lat: 13.00, lng: 77.76 },
  ],
  south: [
    { lat: 12.90, lng: 77.60 },
    { lat: 12.87, lng: 77.65 },
    { lat: 12.84, lng: 77.61 },
    { lat: 12.89, lng: 77.69 },
  ],
}

function normalizeZone(zone = '') {
  const lower = String(zone).toLowerCase()
  if (lower.includes('north')) return 'north'
  if (lower.includes('south')) return 'south'
  if (lower.includes('east')) return 'east'
  if (lower.includes('west')) return 'west'
  if (lower.includes('central') || lower.includes('center')) return 'central'
  return 'central'
}

function getStatus(load, tripped = false) {
  if (tripped || load > 90) return 'critical'
  if (load > 75) return 'warning'
  return 'healthy'
}

function getZoneColor(status) {
  if (status === 'critical') return '#ef4444'
  if (status === 'warning') return '#f59e0b'
  return '#22c55e'
}

function buildZoneData(zoneKey, zoneData, transformers) {
  const assigned = transformers.filter((t) => normalizeZone(t.zone) === zoneKey)
  const load = zoneData?.load_percent ?? (
    assigned.length
      ? assigned.reduce((sum, t) => sum + (t.load_percent || 0), 0) / assigned.length
      : 0
  )
  const voltage = zoneData?.voltage_avg_v ?? (
    assigned.length
      ? assigned.reduce((sum, t) => sum + (t.voltage_output_v || 0), 0) / assigned.length
      : 220
  )
  const status = getStatus(load, zoneData?.substation_status === 'tripped')

  return { load, voltage, status, assigned }
}

function buildZoneLabelHtml(name, load, voltage) {
  return `
    <div class="zone-label">
      <div class="zone-label-name">${name}</div>
      <div class="zone-label-metric">Load: ${load.toFixed(0)}%</div>
      <div class="zone-label-metric">Voltage: ${voltage.toFixed(0)}V</div>
    </div>
  `
}

function buildZonePopupHtml(zone) {
  return `
    <div class="zone-popup">
      <div class="zone-popup-title">${zone.name}</div>
      <div class="zone-popup-copy">${zone.description}</div>
      <div class="zone-popup-metrics">
        <div>Status: ${zone.status}</div>
        <div>Load: ${zone.load.toFixed(0)}%</div>
        <div>Voltage: ${zone.voltage.toFixed(0)}V</div>
      </div>
      <div class="zone-popup-subtitle">Covered Areas</div>
      <div class="zone-popup-areas">${zone.areas.join(' • ')}</div>
    </div>
  `
}

export default function TransformerMapBoard() {
  const { zones, transformers } = useGrid()
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const layersRef = useRef([])
  const hasFitBoundsRef = useRef(false)
  const resizeHandlerRef = useRef(null)

  const zoneViews = useMemo(
    () => ZONES.map((zone) => ({
      ...zone,
      ...buildZoneData(zone.key, zones[zone.key], transformers),
    })),
    [zones, transformers]
  )

  useEffect(() => {
    let intervalId = null

    const initMap = () => {
      if (!mapRef.current || mapInstanceRef.current || !window.L) return false

      const map = window.L.map(mapRef.current, {
        zoomControl: true,
        dragging: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        boxZoom: true,
        keyboard: true,
        zoomAnimation: true,
      }).setView([12.9716, 77.5946], 11)

      map.createPane('zoneLabelsPane')
      map.getPane('zoneLabelsPane').style.zIndex = '650'

      map.createPane('transformerPane')
      map.getPane('transformerPane').style.zIndex = '660'

      window.L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        {
          attribution: '&copy; OpenStreetMap &copy; CARTO',
          subdomains: 'abcd',
          maxZoom: 19,
        }
      ).addTo(map)

      const invalidateMapSize = () => {
        if (!mapInstanceRef.current) return
        mapInstanceRef.current.invalidateSize(false)
      }

      resizeHandlerRef.current = invalidateMapSize
      window.addEventListener('resize', invalidateMapSize)

      map.whenReady(() => {
        window.requestAnimationFrame(invalidateMapSize)
        window.setTimeout(invalidateMapSize, 120)
      })

      mapInstanceRef.current = map
      return true
    }

    if (!initMap()) {
      intervalId = window.setInterval(() => {
        if (initMap() && intervalId) {
          window.clearInterval(intervalId)
        }
      }, 100)
    }

    return () => {
      if (intervalId) window.clearInterval(intervalId)
      layersRef.current.forEach((layer) => layer.remove())
      layersRef.current = []
      if (resizeHandlerRef.current) {
        window.removeEventListener('resize', resizeHandlerRef.current)
        resizeHandlerRef.current = null
      }
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || !window.L) return

    layersRef.current.forEach((layer) => layer.remove())
    layersRef.current = []

    const allCoords = []

    zoneViews.forEach((zone) => {
      const color = getZoneColor(zone.status)
      allCoords.push(...zone.coords)

      const polygon = window.L.polygon(zone.coords, {
        color: '#46f2b7',
        weight: 2,
        fillColor: '#46f2b7',
        fillOpacity: 0.12,
        noClip: true,
        smoothFactor: 1,
      })
        .addTo(map)
        .bindPopup(buildZonePopupHtml(zone))

      const label = window.L.marker(zone.labelLatLng, {
        pane: 'zoneLabelsPane',
        icon: window.L.divIcon({
          html: buildZoneLabelHtml(zone.name, zone.load, zone.voltage),
          className: 'zone-label-wrapper',
          iconSize: [170, 92],
          iconAnchor: [85, 46],
        }),
      }).addTo(map)

      layersRef.current.push(polygon, label)

      zone.assigned.forEach((transformer, index) => {
        const fallbackPoint = TRANSFORMER_POINTS[zone.key][index % TRANSFORMER_POINTS[zone.key].length]
        const status = getStatus(transformer.load_percent || 0)
        const markerColor = getZoneColor(status)

        const marker = window.L.circleMarker([fallbackPoint.lat, fallbackPoint.lng], {
          pane: 'transformerPane',
          radius: 7,
          color: '#ffffff',
          weight: 2,
          fillColor: markerColor,
          fillOpacity: 1,
          opacity: 1,
        })
          .addTo(map)
          .bindPopup(`
            <b>${transformer.id}</b><br>
            Zone: ${transformer.zone}<br>
            Health: ${status}<br>
            Load: ${(transformer.load_percent || 0).toFixed(1)}%<br>
            Voltage: ${(transformer.voltage_output_v || 0).toFixed(1)}V
          `)

        marker.bringToFront()

        layersRef.current.push(marker)
      })
    })

    if (allCoords.length && !hasFitBoundsRef.current) {
      map.fitBounds(window.L.latLngBounds(allCoords), {
        padding: [24, 24],
      })
      hasFitBoundsRef.current = true
    }
  }, [zoneViews])

  const totalCritical = transformers.filter((t) => (t.load_percent || 0) > 85).length

  return (
    <section className="transformer-map-board">
      <div className="transformer-map-titlebar">
        <div>
          <div className="mono title-small">City Grid Geospatial Overlay</div>
          <h2 className="transformer-map-heading">Smart City Power Grid Dashboard</h2>
        </div>
        <div className="transformer-map-alert-box">
          <div className="transformer-map-alert-label">
            <AlertTriangle size={14} />
            Live Alert Window
          </div>
          <div className="transformer-map-alert-value">
            {totalCritical > 0 ? `${totalCritical} transformers above threshold` : 'All transformers nominal'}
          </div>
        </div>
      </div>

      <div className="transformer-map-stage">
        <div ref={mapRef} className="transformer-map-canvas" />

        <div className="transformer-zone-directory">
          {zoneViews.map((zone) => (
            <div key={zone.key} className="transformer-zone-directory-card">
              <div className="transformer-zone-directory-top">
                <div className="transformer-zone-directory-heading">{zone.name}</div>
                <span className={`badge ${zone.status === 'critical' ? 'critical' : zone.status === 'warning' ? 'warning' : 'healthy'}`}>
                  {zone.status}
                </span>
              </div>
              <div className="transformer-zone-directory-copy">{zone.description}</div>
              <div className="transformer-zone-directory-list">
                {zone.areas.join(' • ')}
              </div>
            </div>
          ))}
        </div>

        <div className="transformer-map-legend">
          <div><span className="dot green" /> Healthy</div>
          <div><span className="dot amber" /> Warning</div>
          <div><span className="dot red" /> Critical</div>
        </div>
      </div>
    </section>
  )
}
