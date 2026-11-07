import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import { dataPath, fetchJson, type Manifest, type Snapshot, type Summary } from '../../data'

export default function AuctionDetail() {
  const { auctionId } = useParams()
  const location = useLocation()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [detail, setDetail] = useState<unknown>(null)
  const [demo, setDemo] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { fetchJson<Manifest>(dataPath).then(m => { setDemo(!!m.demo); return fetchJson<Snapshot>(m.availability.path) }).then(snapshot => { const item = snapshot.auctions.find(a => a.auction_id === auctionId); if (!item) throw new Error('Remate no disponible.'); setSummary(item); return fetchJson<unknown>(item.detail_path) }).then(setDetail).catch((e: Error) => setError(e.message)) }, [auctionId])
  return <section className="detail"><Link to={`/${location.search}`}>← Volver a resultados</Link>{demo && <p className="demo-notice">Datos ficticios. Este remate no existe.</p>}{error ? <p role="alert">{error}</p> : !summary ? <p>Cargando…</p> : <><p className="eyebrow">REMATE N.º {summary.numero_remate}</p><h1>{summary.descripcion || 'Detalle del remate'}</h1><p>Precio base: {summary.precio_base?.raw || 'No disponible'}</p><p>Fecha de ofertas: {summary.offer_date || 'No disponible'}</p>{!demo && <p>Consulta el remate por número en <a href="https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml" target="_blank" rel="noreferrer">REMAJU</a>.</p>}<h2>Datos disponibles</h2>{detail ? <pre>{JSON.stringify(detail, null, 2)}</pre> : <p>Cargando detalle…</p>}</>}</section>
}
