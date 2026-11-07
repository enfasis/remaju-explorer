import { useEffect, useState } from 'react'
import { dataPath, fetchJson, siteUrl, type Manifest } from '../data'

export default function Downloads() {
  const [manifest, setManifest] = useState<Manifest | null>(null)
  useEffect(() => { fetchJson<Manifest>(dataPath).then(setManifest).catch(() => {}) }, [])
  return <section className="detail"><h1>Datos y descargas</h1>{manifest?.demo ? <p>Esta demostración contiene únicamente datos ficticios, no remates disponibles.</p> : <p>La ausencia de un remate en una publicación no significa que se haya vendido.</p>}{manifest ? <ul><li><a href={siteUrl(manifest.availability.path)}>Descargar {manifest.demo ? 'ejemplos' : 'datos'} (JSON)</a></li>{manifest.archive && <li><a href={siteUrl(manifest.archive.path)}>Índice del archivo histórico</a></li>}<li><a href={siteUrl(dataPath)}>Manifiesto y versión</a></li></ul> : <p>No hay una publicación disponible todavía.</p>}<p><a href={siteUrl('data-access.md')}>Instrucciones para agentes y análisis</a></p></section>
}
