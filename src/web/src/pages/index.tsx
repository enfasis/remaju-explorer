import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { parseAsString, useQueryStates } from 'nuqs'
import { ButtonFrame, ButtonText } from '@tamagui/button'
import { compareDecimal, convertedAmount, dataPath, displayMoney, fetchJson, orderAuctions, siteUrl, type Manifest, type Rate, type Snapshot, type Summary } from '../data'
import { useRate } from '../use-rate'

const AuctionMap = lazy(() => import('../components/auction-map'))

const parsers = { q: parseAsString.withDefault(''), department: parseAsString.withDefault(''), province: parseAsString.withDefault(''), district: parseAsString.withDefault(''), propertyType: parseAsString.withDefault(''), phase: parseAsString.withDefault(''), currency: parseAsString.withDefault('PEN'), minPrice: parseAsString.withDefault(''), maxPrice: parseAsString.withDefault(''), from: parseAsString.withDefault(''), to: parseAsString.withDefault(''), sort: parseAsString.withDefault('date-desc') }
type Filters = { [K in keyof typeof parsers]: string }

function matches(a: Summary, f: Filters, rate: Rate | null): boolean {
  const text = [a.numero_remate, a.descripcion, a.departamento, a.provincia, a.distrito].join(' ').toLocaleLowerCase('es')
  if (f.q && !text.includes(f.q.toLocaleLowerCase('es'))) return false
  for (const [filter, value] of [[f.department, a.departamento], [f.province, a.provincia], [f.district, a.distrito], [f.propertyType, a.tipo_inmueble], [f.phase, a.fase]]) if (filter && filter !== value) return false
  const date = a.offer_date ?? a.offer_at?.slice(0, 10)
  if ((f.from || f.to) && (!date || (f.from && date < f.from) || (f.to && date > f.to))) return false
  if (f.minPrice || f.maxPrice) {
    const amount = convertedAmount(a.precio_base, f.currency, rate)
    if (!f.currency || !amount) return false
    const min = f.minPrice ? compareDecimal(amount, f.minPrice) : 0
    const max = f.maxPrice ? compareDecimal(amount, f.maxPrice) : 0
    if (min === null || max === null || min < 0 || max > 0) return false
  }
  return true
}

export default function Home() {
  const [filters, setFilters] = useQueryStates(parsers)
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [auctions, setAuctions] = useState<Summary[]>([])
  const [error, setError] = useState('')
  const [showMap, setShowMap] = useState(false)
  const rate = useRate()
  useEffect(() => { fetchJson<Manifest>(dataPath).then(async m => { if (m.schema_version !== 1) throw new Error('Versión de datos incompatible.'); const data = await fetchJson<Snapshot>(m.availability.path); setManifest(m); setAuctions(data.auctions) }).catch((e: Error) => setError(e.message)) }, [])
  const results = useMemo(() => orderAuctions(auctions.filter(a => matches(a, filters, rate)), filters.sort, filters.currency, rate), [auctions, filters, rate])
  const points = useMemo(() => results.flatMap(a => (a.coordinates || []).map(p => ({ ...p, label: `Remate ${a.numero_remate}`, path: `auctions/${encodeURIComponent(a.auction_id)}${location.search}` }))), [results, filters])
  const options = (key: keyof Summary) => [...new Set(auctions.map(a => a[key]).filter((value): value is string => typeof value === 'string' && value.length > 0))].sort()
  const select = (label: string, key: keyof Filters, values: string[]) => <label>{label}<select value={filters[key]} onChange={e => void setFilters({ [key]: e.target.value || null, ...(key === 'department' ? { province: null, district: null } : key === 'province' ? { district: null } : {}) }, { history: 'push' })}>{key !== 'currency' && <option value="">Todos</option>}{values.map(value => <option key={value}>{value}</option>)}</select></label>
  return <>
    <h1 className="sr-only">Remates judiciales del Perú</h1>
    <section className="filters" aria-label="Filtros de remates">
      <div className="filter-grid"><label className="search">Buscar<input type="search" value={filters.q} placeholder="Número, ubicación o descripción" onChange={e => void setFilters({ q: e.target.value || null }, { history: 'replace' })} /></label>
      {select('Departamento', 'department', options('departamento'))}{select('Provincia', 'province', options('provincia'))}{select('Distrito', 'district', options('distrito'))}{select('Tipo de inmueble', 'propertyType', options('tipo_inmueble'))}{select('Fase', 'phase', options('fase'))}{select('Ver precios en', 'currency', ['PEN', 'USD'])}
      {(['minPrice', 'maxPrice', 'from', 'to'] as const).map(key => <label key={key}>{{ minPrice: 'Precio mínimo', maxPrice: 'Precio máximo', from: 'Desde', to: 'Hasta' }[key]}<input type={key === 'from' || key === 'to' ? 'date' : 'text'} inputMode={key.includes('Price') ? 'decimal' : undefined} value={filters[key]} onChange={e => void setFilters({ [key]: e.target.value || null }, { history: 'replace' })} /></label>)}</div>
      <p className="rate-note">{rate ? `Cambio referencial: 1 PEN = ${rate.penToUsd} USD · ${rate.date} · ${rate.source}.` : 'Sin tipo de cambio disponible: se muestran precios originales.'} Los rangos y el orden por precio usan la moneda seleccionada; sin conversión, los importes no comparables quedan fuera del rango y al final del orden.</p>
      <div className="filter-footer"><ButtonFrame cursor="pointer" onPress={() => void setFilters(Object.fromEntries(Object.keys(parsers).map(k => [k, null])), { history: 'push' })}><ButtonText>Limpiar filtros</ButtonText></ButtonFrame></div>
    </section>
    <section className="results"><div className="section-heading"><div><h2>Remates</h2><span>{results.length} resultados{manifest?.demo ? ' · Muestra parcial del 07/11/2026' : ''}</span></div><div className="result-controls"><label className="map-switch"><input type="checkbox" checked={showMap} onChange={e => setShowMap(e.target.checked)} /> Mostrar mapa</label><label className="sort">Ordenar por<select value={filters.sort} onChange={e => void setFilters({ sort: e.target.value }, { history: 'push' })}><option value="date-desc">Fecha: reciente primero</option><option value="date-asc">Fecha: antigua primero</option><option value="price-asc">Precio: menor primero</option><option value="price-desc">Precio: mayor primero</option></select></label></div></div>
      <div className={showMap ? 'results-layout with-map' : 'results-layout'}><div>{error ? <div role="alert" className="message">{error} Todavía no hay una publicación disponible.</div> : !manifest ? <div className="message">Cargando datos…</div> : results.length === 0 ? <div className="message">No hay remates que coincidan con los filtros.</div> : <div className="list">{results.map(a => <Link className="item" key={a.auction_id} to={`/auctions/${encodeURIComponent(a.auction_id)}${location.search}`} aria-label={`Ver remate ${a.numero_remate}`}><article>{a.thumbnail_path && <img className="thumbnail" src={siteUrl(a.thumbnail_path)} alt="Imagen del inmueble publicada en REMAJU" loading="lazy" />}<p className="eyebrow">REMATE N.º {a.numero_remate}</p><h3>{a.tipo_inmueble || 'Inmueble'} · {[a.distrito, a.provincia].filter(Boolean).join(', ')}</h3><p className="card-description">{a.descripcion || 'Detalle del remate'}</p><p>{[a.provincia, a.departamento].filter(Boolean).join(', ') || 'Ubicación no disponible'}</p>{a.fase && <span className="badge">{a.fase}</span>}<div className="amount"><span>PRECIO BASE DEL REMATE</span><strong>{displayMoney(a.precio_base, filters.currency, rate)}</strong>{a.precio_base?.currency !== filters.currency && <small>Original: {a.precio_base?.raw}</small>}<small>Ofertas: {a.offer_date || a.offer_at?.slice(0, 10) || 'Fecha no verificada'}</small></div></article></Link>)}</div>}</div>{showMap && <Suspense fallback={<p>Cargando mapa…</p>}><AuctionMap points={points} /></Suspense>}</div>
    </section>
  </>
}
