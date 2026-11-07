import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import { dataPath, displayMoney, fetchJson, siteUrl, type AuctionDetail as Detail, type Manifest, type Snapshot, type Summary } from '../../data'
import { useRate } from '../../use-rate'

const AuctionMap = lazy(() => import('../../components/auction-map'))
const labels: Record<string, string> = { expediente: 'Expediente', distrito_judicial: 'Distrito judicial', organo_jurisdiccional: 'Órgano jurisdiccional', instancia: 'Instancia', materia: 'Materia', resolucion: 'Resolución', fecha_resolucion: 'Fecha de resolución', convocatoria: 'Convocatoria', tasacion: 'Tasación', precio_base: 'Precio base', incremento_entre_ofertas: 'Incremento entre ofertas', arancel: 'Arancel', oblaje: 'Oblaje', nro_inscritos: 'Inscritos', nro_expediente: 'Expediente', especialidad: 'Especialidad', nro_convocatoria: 'Convocatoria', fecha_registro: 'Fecha de registro', procesado_por: 'Procesado por', reanudado: 'Reanudado', fase_convocatoria: 'Fase', estado_convocatoria: 'Estado', fecha_desierto: 'Fecha de desierto' }

function Fields({ values }: { values: Record<string, string | number | null> }) {
  return <dl className="detail-fields">{Object.entries(values).filter(([key]) => key !== 'descripcion').map(([key, value]) => <div key={key}><dt>{labels[key] || key}</dt><dd>{value === null || value === '' ? 'No disponible' : value}</dd></div>)}</dl>
}

export default function AuctionDetail() {
  const { auctionId } = useParams()
  const location = useLocation()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [detail, setDetail] = useState<Detail | null>(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('Remate')
  const rate = useRate()
  const currency = new URLSearchParams(location.search).get('currency') === 'USD' ? 'USD' : 'PEN'
  useEffect(() => {
    let active = true
    setSummary(null); setDetail(null); setError(''); setTab('Remate')
    fetchJson<Manifest>(dataPath).then(m => fetchJson<Snapshot>(m.availability.path)).then(snapshot => {
      const item = snapshot.auctions.find(a => a.auction_id === auctionId)
      if (!item) throw new Error('Remate no disponible.')
      if (active) setSummary(item)
      return fetchJson<Detail>(item.detail_path)
    }).then(value => { if (active) setDetail(value) }).catch((e: Error) => { if (active) setError(e.message) })
    return () => { active = false }
  }, [auctionId])
  const points = useMemo(() => (detail?.inmuebles || []).flatMap(p => p.latitude != null && p.longitude != null ? [{ latitude: p.latitude, longitude: p.longitude, label: p.tipo_inmueble }] : []), [detail])
  return <section className="detail">
    <Link to={`/${location.search}`}>← Volver a resultados</Link>
    {error ? <p role="alert">{error}</p> : !summary || !detail ? <p>Cargando detalle…</p> : <>
      <p className="eyebrow">REMATE N.º {summary.numero_remate}</p>
      <h1>{summary.tipo_inmueble || 'Inmueble'} · {[summary.provincia, summary.departamento].filter(Boolean).join(', ')}</h1>
      {summary.thumbnail_path && <img className="detail-image" src={siteUrl(summary.thumbnail_path)} alt="Imagen del inmueble publicada en REMAJU" />}
      <p className="detail-price">{displayMoney(summary.precio_base, currency, rate)}</p>
      <p className="muted">Precio base de todo el remate · Original: {summary.precio_base?.raw || 'No disponible'}{rate && ` · Cambio referencial ${rate.date} (${rate.source})`}</p>
      <div className="detail-tabs" aria-label="Secciones del remate">{['Remate', 'Inmuebles', 'Cronograma', 'Seguimiento', 'Documentos'].map(name => <button type="button" key={name} aria-pressed={name === tab} onClick={() => setTab(name)}>{name}</button>)}</div>
      <section className="detail-section" aria-label={tab}>
        <h2>{tab}</h2>
        {tab === 'Remate' && <><Fields values={detail.remate} /><h3>Descripción</h3><p className="legal-text">{detail.remate.descripcion || 'No disponible'}</p></>}
        {tab === 'Inmuebles' && <>{detail.inmuebles.map((p, index) => <article className="property-detail" key={index}><h3>{index + 1}. {p.tipo_inmueble}</h3><dl className="detail-fields"><div><dt>Partida registral</dt><dd>{p.partida_registral}</dd></div><div><dt>Porcentaje a rematar</dt><dd>{p.porcentaje_a_remstar}</dd></div><div><dt>Área</dt><dd>{p.area_m2 == null ? 'No disponible' : `${p.area_m2} m²`}</dd></div><div><dt>Imágenes en la fuente</dt><dd>{p.imagenes} (la extracción no conservó enlaces)</dd></div></dl><h4>Dirección</h4><p className="legal-text">{p.direccion}</p><h4>Cargas y gravámenes</h4><p className="legal-text">{p.carga_gravamen || 'No disponible'}</p></article>)}{points.length ? <Suspense fallback={<p>Cargando mapa…</p>}><AuctionMap points={points} /></Suspense> : <p className="muted">Ubicación sin coordenadas verificadas. No se ha realizado geocodificación de pago.</p>}</>}
        {tab === 'Cronograma' && <><p className="muted">Horario de Perú (America/Lima). Fechas extraídas; confirma los plazos en la fuente.</p><div className="table-scroll"><table><thead><tr><th>Fase</th><th>Inicio</th><th>Fin</th></tr></thead><tbody>{detail.cronograma.map(p => <tr key={p.nro}><td>{p.fase}</td><td>{p.fecha_inicio}</td><td>{p.fecha_fin}</td></tr>)}</tbody></table></div></>}
        {tab === 'Seguimiento' && (detail.seguimiento ? <><Fields values={detail.seguimiento.expediente} />{detail.seguimiento.eventos.map((event, index) => <Fields key={index} values={event} />)}</> : <p>No hay seguimiento extraído.</p>)}
        {tab === 'Documentos' && <>{detail.documents.length ? <ul>{detail.documents.filter(d => /^https:\/\/remaju\.pj\.gob\.pe\//.test(d.url)).map(d => <li key={d.url}><a href={d.url} target="_blank" rel="noreferrer">{d.label}</a></li>)}</ul> : <p>La resolución y el aviso requieren navegación en REMAJU. No se obtuvo un enlace público estable; no se han descargado ni alojado estos archivos.</p>}</>}
      </section>
      <p className="source-note">Muestra parcial. Para verificar o ver archivos, busca el remate <strong>{summary.numero_remate}</strong> en <a href="https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml" target="_blank" rel="noreferrer">REMAJU</a> y abre Detalle o Aviso. Este enlace abre el buscador, no el remate directamente.</p>
    </>}
  </section>
}
