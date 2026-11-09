import { useEffect, useState, type CSSProperties, type ReactElement } from 'react'
import { loadManifest, loadSnapshot } from '../cache'
import { DownloadIcon, FileIcon } from '../components/icons'
import Spinner from '../components/spinner'
import { availableReference, dataPath, dataUrl, partialData, siteUrl, type Manifest, type Snapshot } from '../data'
import { useTitle } from '../use-title'

type Resource = { title: string; format: string; description: string; href: string; action: string; download?: boolean; icon: ReactElement }

function resources(manifest: Manifest, snapshot: Snapshot | null): Resource[] {
  const count = snapshot ? `${snapshot.auctions.length} remates` : 'todos los remates'
  return [
    { title: 'Remates disponibles', format: 'JSON', description: `Datos completos de ${count}: montos, inmuebles, cronograma y seguimiento. Se actualiza diariamente e incluye remates con fecha de cierre de fase 3 aún vigente.`, href: dataUrl(availableReference(manifest).path), action: 'Descargar listado', download: true, icon: <DownloadIcon /> },
    ...(manifest.history && manifest.schema_version === 2 ? [{ title: 'Archivo histórico', format: 'JSON', description: 'Último contenido conocido de cada remate, con sus detalles, fecha de primera y última observación y presencia en el último recorrido completo. No es un índice de publicaciones.', href: dataUrl(manifest.history.path), action: 'Descargar historial', download: true, icon: <DownloadIcon /> }] : []),
    ...(manifest.ids ? [{ title: 'Números de remate', format: 'TXT', description: 'Un código por línea, en el orden del último recorrido completo. Se usa para comparar colecciones.', href: dataUrl(manifest.ids.path), action: 'Descargar códigos', download: true, icon: <DownloadIcon /> }] : []),
    { title: 'Manifiesto', format: 'JSON', description: 'Punto de entrada para automatizar descargas: indica la versión vigente, la fecha de generación y la ruta de cada archivo.', href: dataUrl(dataPath), action: 'Ver manifiesto', icon: <FileIcon /> },
    { title: 'Guía de acceso a los datos', format: 'Markdown', description: 'Descripción de los campos, reglas de uso y advertencias para analistas y agentes de IA.', href: siteUrl('data-access.md'), action: 'Leer guía', icon: <FileIcon /> },
  ]
}

export default function Downloads() {
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [error, setError] = useState(false)
  useTitle('Datos y descargas')
  useEffect(() => {
    loadManifest().then(setManifest).catch(() => setError(true))
    loadSnapshot().then(setSnapshot).catch(() => {})
  }, [])
  const generated = manifest ? new Intl.DateTimeFormat('es-PE', { dateStyle: 'long', timeZone: 'America/Lima' }).format(new Date(manifest.generated_at)) : ''
  return <article className="downloads" aria-labelledby="downloads-title">
    <header className="page-hero reveal">
      <p className="eyebrow">Datos abiertos</p>
      <h1 id="downloads-title">Datos y descargas</h1>
      <p>Todo lo que ves en el explorador está disponible como archivos abiertos. No necesitas cuenta ni clave, y puedes descargarlos o consultarlos desde tus propios programas.</p>
      {manifest && <ul className="publication-meta" aria-label="Publicación">
        <li><span>Versión</span>{manifest.dataset_version}</li>
        <li><span>Generado el</span>{generated}</li>
        {snapshot && <li><span>Contenido</span>{snapshot.auctions.length} remates</li>}
        {partialData(manifest) && <li><span>Alcance</span>Muestra parcial</li>}
      </ul>}
      {manifest?.demo && <p className="muted">Esta es una muestra parcial extraída el 7 de noviembre de 2026. No es un listado completo ni garantiza disponibilidad.</p>}
      {manifest?.scope === 'partial' && <p className="muted">Esta publicación recorre solo algunas páginas de REMAJU. No es un listado completo ni garantiza disponibilidad.</p>}
    </header>
    {error ? <p role="alert" className="message">No hay una publicación disponible todavía.</p> : !manifest ? <Spinner label="Cargando publicación…" /> : <ul className="resources" aria-label="Archivos disponibles">
      {resources(manifest, snapshot).map((resource, index) => <li key={resource.title} className="resource reveal" style={{ '--i': index + 1 } as CSSProperties}>
        <div className="resource-head"><h2>{resource.title}</h2><span className="resource-format">{resource.format}</span></div>
        <p>{resource.description}</p>
        <a href={resource.href} download={resource.download ? '' : undefined} target={resource.download ? undefined : '_blank'} rel="noreferrer" aria-label={`${resource.action}: ${resource.title} (${resource.format})`} className="resource-action field-frame">{resource.icon}{resource.action}{!resource.download && <span className="sr-only"> (abre en otra pestaña)</span>}</a>
      </li>)}
    </ul>}
    <p className="source-note">Los datos son una fotografía de REMAJU en la fecha indicada. Que un remate no aparezca no significa que se haya vendido. Consulta siempre la fuente oficial.</p>
  </article>
}
