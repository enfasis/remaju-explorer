import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { siteUrl, type Coordinate } from '../data'
import { chavin } from '../theme'

export type MapPoint = Coordinate & { id: string; label: string; path?: string }
export type MapFocus = { id: string; at: number }

const locateIcon = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>'

function valid(point: MapPoint): boolean {
  return Number.isFinite(point.latitude) && Number.isFinite(point.longitude) && Math.abs(point.latitude) <= 90 && Math.abs(point.longitude) <= 180
}

function locateControl(onLocate: () => void): L.Control {
  const control = new L.Control({ position: 'topleft' })
  control.onAdd = () => {
    const button = L.DomUtil.create('button', 'map-locate leaflet-bar')
    button.type = 'button'
    button.innerHTML = locateIcon
    button.title = 'Centrar en mi ubicación'
    button.setAttribute('aria-label', 'Centrar el mapa en mi ubicación')
    L.DomEvent.disableClickPropagation(button)
    L.DomEvent.on(button, 'click', onLocate)
    return button
  }
  return control
}

export default function AuctionMap({ points, focus }: { points: MapPoint[]; focus?: MapFocus | null }) {
  const element = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const markers = useRef(new Map<string, L.CircleMarker>())
  const [message, setMessage] = useState('')
  const located = points.filter(valid)
  useEffect(() => {
    if (!element.current) return
    const instance = L.map(element.current).setView([-9.19, -75.0152], 5)
    map.current = instance
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 18 }).addTo(instance)
    locateControl(() => {
      if (!navigator.geolocation) { setMessage('Tu navegador no ofrece ubicación.'); return }
      navigator.geolocation.getCurrentPosition(position => {
        instance.flyTo([position.coords.latitude, position.coords.longitude], 11)
        setMessage('Centrado en tu ubicación. No se guarda.')
      }, () => setMessage('No se pudo obtener tu ubicación.'), { timeout: 10000 })
    }).addTo(instance)
    markers.current.clear()
    for (const point of located) {
      const label = document.createElement(point.path ? 'a' : 'span')
      label.textContent = point.label
      if (label instanceof HTMLAnchorElement && point.path) label.href = siteUrl(point.path)
      markers.current.set(point.id, L.circleMarker([point.latitude, point.longitude], { radius: 8, color: chavin.red, weight: 2, fillColor: chavin.red, fillOpacity: .75 }).bindPopup(label).addTo(instance))
    }
    if (located.length) instance.fitBounds(L.latLngBounds(located.map(p => [p.latitude, p.longitude])), { padding: [30, 30], maxZoom: 14 })
    return () => { instance.remove(); map.current = null }
  }, [points])
  useEffect(() => {
    const marker = focus ? markers.current.get(focus.id) : undefined
    if (!marker || !map.current) return
    element.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    map.current.flyTo(marker.getLatLng(), 16, { duration: .8 })
    marker.openPopup()
  }, [focus])
  return <section id="auction-map" className="map-panel" aria-label="Mapa de inmuebles">
    <div className="map" ref={element} role="region" aria-label="Mapa de Perú" />
    <p className="map-status muted" role="status">{located.length ? `${located.length} ${located.length === 1 ? 'ubicación registrada' : 'ubicaciones registradas'}.` : 'No hay coordenadas registradas para estos resultados.'} {message}</p>
  </section>
}
