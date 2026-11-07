import { useEffect, useState } from 'react'
import { fetchJson, type Manifest } from '../data'

export default function Downloads() {
  const [manifest, setManifest] = useState<Manifest | null>(null)
  useEffect(() => { fetchJson<Manifest>('/data/manifest.json').then(setManifest).catch(() => {}) }, [])
  return <section className="detail"><p className="eyebrow">DATOS PARA TODOS</p><h1>Descargar datos</h1><p>El conjunto actual contiene los remates observados como disponibles en la última actualización. El historial conserva observaciones anteriores; ausencia no significa venta.</p>{manifest ? <ul><li><a href={manifest.availability.path}>Descargar disponibilidad actual (JSON)</a></li>{manifest.archive && <li><a href={manifest.archive.path}>Índice del archivo histórico</a></li>}<li><a href="/data/manifest.json">Manifiesto y versión</a></li></ul> : <p>No hay una publicación disponible todavía.</p>}<p><a href="/data-access.md">Instrucciones para agentes y análisis</a></p></section>
}
