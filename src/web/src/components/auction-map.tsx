import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { siteUrl, type Coordinate } from '../data'

type Point = Coordinate & { label: string; path?: string }

export default function AuctionMap({ points }: { points: Point[] }) {
  const element = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const [message, setMessage] = useState('')
  useEffect(() => {
    if (!element.current) return
    const instance = L.map(element.current).setView([-9.19, -75.0152], 5)
    map.current = instance
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 18 }).addTo(instance)
    const valid = points.filter(p => Number.isFinite(p.latitude) && Number.isFinite(p.longitude) && Math.abs(p.latitude) <= 90 && Math.abs(p.longitude) <= 180)
    for (const point of valid) {
      const label = document.createElement(point.path ? 'a' : 'span')
      label.textContent = point.label
      if (label instanceof HTMLAnchorElement && point.path) label.href = siteUrl(point.path)
      L.circleMarker([point.latitude, point.longitude], { radius: 7, color: '#b63860', fillOpacity: .8 }).bindPopup(label).addTo(instance)
    }
    if (valid.length) instance.fitBounds(L.latLngBounds(valid.map(p => [p.latitude, p.longitude])), { padding: [30, 30], maxZoom: 14 })
    return () => { instance.remove(); map.current = null }
  }, [points])
  function locate() {
    if (!navigator.geolocation) { setMessage('Tu navegador no ofrece ubicación.'); return }
    navigator.geolocation.getCurrentPosition(position => {
      map.current?.setView([position.coords.latitude, position.coords.longitude], 11)
      setMessage('Centrado en tu ubicación. No se guarda en la aplicación; el mapa usa OpenStreetMap.')
    }, () => setMessage('No se pudo obtener tu ubicación. El mapa sigue disponible.'), { timeout: 10000 })
  }
  return <section className="map-panel" aria-label="Mapa de inmuebles"><button type="button" className="text-button" onClick={locate}>Centrar en mi ubicación</button><div className="map" ref={element} role="region" aria-label="Mapa de Perú" /><p className="muted">{points.length ? `${points.length} ubicaciones registradas.` : 'No hay coordenadas registradas para estos resultados.'} {message}</p></section>
}
