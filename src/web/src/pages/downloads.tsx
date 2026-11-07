import { useEffect, useState, type CSSProperties, type ReactElement } from 'react'
import { Button } from 'tamagui'
import { loadManifest, loadSnapshot } from '../cache'
import { DownloadIcon, FileIcon } from '../components/icons'
import { dataPath, siteUrl, type Manifest, type Snapshot } from '../data'
import { useTitle } from '../use-title'

type Resource = { title: string; format: string; description: string; href: string; action: string; download?: boolean; icon: ReactElement }

function resources(manifest: Manifest, snapshot: Snapshot | null): Resource[] {
  const count = snapshot ? `${snapshot.auctions.length} remates` : 'todos los remates'
  const example = snapshot?.auctions[0]?.detail_path
  const release = manifest.availability.path.replace(/[^/]+$/, '')
  return [
    { title: 'Listado de remates', format: 'JSON', description: `Un resumen por remate (${count}): número, ubicación, tipo de inmueble, fase, estado, precio base y cronograma. Es el mismo archivo que usa el buscador.`, href: manifest.availability.path, action: 'Descargar listado', download: true, icon: <DownloadIcon /> },
    ...(manifest.demo ? [] : [{ title: 'Listado para hojas de cálculo', format: 'CSV', description: 'Los remates disponibles en columnas, listo para Excel, Google Sheets o LibreOffice.', href: `${release}available.csv`, action: 'Descargar CSV', download: true, icon: <DownloadIcon /> }]),
    ...(example ? [{ title: 'Detalle de cada remate', format: 'JSON', description: 'Un archivo por remate con montos, inmuebles, cargas y gravámenes, cronograma y seguimiento judicial. Cada resumen del listado indica su ruta en el campo detail_path.', href: example, action: 'Ver un ejemplo', icon: <FileIcon /> }] : []),
    { title: 'Manifiesto', format: 'JSON', description: 'Punto de entrada para automatizar descargas: indica la versión vigente, la fecha de generación y la ruta de cada archivo.', href: dataPath, action: 'Ver manifiesto', icon: <FileIcon /> },
    ...(manifest.archive ? [{ title: 'Archivo histórico', format: 'JSON', description: 'Índice de publicaciones anteriores y de los cambios observados entre ellas.', href: manifest.archive.path, action: 'Ver archivo', icon: <FileIcon /> }] : []),
    { title: 'Guía de acceso a los datos', format: 'Markdown', description: 'Descripción de los campos, reglas de uso y advertencias para analistas y agentes de IA.', href: 'data-access.md', action: 'Leer guía', icon: <FileIcon /> },
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
    <header className="page-hero glass reveal">
      <p className="eyebrow">Datos abiertos</p>
      <h1 id="downloads-title">Datos y descargas</h1>
      <p>Todo lo que ves en el explorador está disponible como archivos abiertos. No necesitas cuenta ni clave, y puedes descargarlos o consultarlos desde tus propios programas.</p>
      {manifest && <ul className="badges" aria-label="Publicación">
        <li className="badge badge-blue"><span className="sr-only">Versión: </span>{manifest.dataset_version}</li>
        <li className="badge badge-green">Generado el {generated}</li>
        {snapshot && <li className="badge badge-yellow">{snapshot.auctions.length} remates</li>}
        {manifest.demo && <li className="badge badge-red">Muestra parcial</li>}
      </ul>}
      {manifest?.demo && <p className="muted">Esta es una muestra parcial extraída el 7 de noviembre de 2026. No es un listado completo ni garantiza disponibilidad.</p>}
    </header>
    {error ? <p role="alert" className="message glass">No hay una publicación disponible todavía.</p> : !manifest ? <p role="status" className="message glass">Cargando publicación…</p> : <ul className="resources" aria-label="Archivos disponibles">
      {resources(manifest, snapshot).map((resource, index) => <li key={resource.title} className="resource glass reveal" style={{ '--i': index + 1 } as CSSProperties}>
        <div className="resource-head"><h2>{resource.title}</h2><span className="badge badge-blue">{resource.format}</span></div>
        <p>{resource.description}</p>
        <Button size="sm" icon={resource.icon} render={<a href={siteUrl(resource.href)} download={resource.download ? '' : undefined} target={resource.download ? undefined : '_blank'} rel="noreferrer" />} aria-label={`${resource.action}: ${resource.title} (${resource.format})`} className="resource-action">{resource.action}</Button>
      </li>)}
    </ul>}
    <p className="source-note">Los datos son una fotografía de REMAJU en la fecha indicada. Que un remate no aparezca no significa que se haya vendido. Consulta siempre la fuente oficial.</p>
  </article>
}
