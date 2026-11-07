import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { parseAsString, useQueryStates } from 'nuqs'
import { Button } from '../components/ui/button'
import { compareDecimal, dataPath, fetchJson, sortAuctions, type Manifest, type Snapshot, type Summary } from '../data'

const parsers = { q: parseAsString.withDefault(''), department: parseAsString.withDefault(''), province: parseAsString.withDefault(''), district: parseAsString.withDefault(''), propertyType: parseAsString.withDefault(''), phase: parseAsString.withDefault(''), currency: parseAsString.withDefault(''), minPrice: parseAsString.withDefault(''), maxPrice: parseAsString.withDefault(''), from: parseAsString.withDefault(''), to: parseAsString.withDefault('') }
type Filters = { [K in keyof typeof parsers]: string }

function matches(a: Summary, f: Filters): boolean {
  const text = [a.numero_remate, a.descripcion, a.departamento, a.provincia, a.distrito].join(' ').toLocaleLowerCase('es')
  if (f.q && !text.includes(f.q.toLocaleLowerCase('es'))) return false
  for (const [filter, value] of [[f.department, a.departamento], [f.province, a.provincia], [f.district, a.distrito], [f.propertyType, a.tipo_inmueble], [f.phase, a.fase], [f.currency, a.precio_base?.currency]]) if (filter && filter !== value) return false
  const date = a.offer_date ?? a.offer_at?.slice(0, 10)
  if ((f.from || f.to) && (!date || (f.from && date < f.from) || (f.to && date > f.to))) return false
  if (f.minPrice || f.maxPrice) {
    const amount = a.precio_base?.amount
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
  useEffect(() => { fetchJson<Manifest>(dataPath).then(async m => { if (m.schema_version !== 1) throw new Error('Versión de datos incompatible.'); const data = await fetchJson<Snapshot>(m.availability.path); setManifest(m); setAuctions(data.auctions) }).catch((e: Error) => setError(e.message)) }, [])
  const results = useMemo(() => sortAuctions(auctions.filter(a => matches(a, filters))), [auctions, filters])
  const options = (key: keyof Summary) => [...new Set(auctions.map(a => a[key]).filter((value): value is string => typeof value === 'string' && value.length > 0))].sort()
  const select = (label: string, key: keyof Filters, values: string[]) => <label>{label}<select value={filters[key]} onChange={e => void setFilters({ [key]: e.target.value || null, ...(key === 'department' ? { province: null, district: null } : key === 'province' ? { district: null } : {}) }, { history: 'push' })}><option value="">Todos</option>{values.map(value => <option key={value}>{value}</option>)}</select></label>
  return <>
    <h1 className="sr-only">Remates judiciales del Perú</h1>
    {manifest?.demo && <p className="demo-notice" role="status">Datos de ejemplo ficticios. No representan remates reales ni disponibles.</p>}
    <section className="filters" aria-label="Filtros de remates">
      <div className="filter-grid"><label className="search">Buscar<input type="search" value={filters.q} placeholder="Número, ubicación o descripción" onChange={e => void setFilters({ q: e.target.value || null }, { history: 'replace' })} /></label>
      {select('Departamento', 'department', options('departamento'))}{select('Provincia', 'province', options('provincia'))}{select('Distrito', 'district', options('distrito'))}{select('Tipo de inmueble', 'propertyType', options('tipo_inmueble'))}{select('Fase', 'phase', options('fase'))}{select('Moneda', 'currency', ['PEN', 'USD'])}
      {(['minPrice', 'maxPrice', 'from', 'to'] as const).map(key => <label key={key}>{{ minPrice: 'Precio mínimo', maxPrice: 'Precio máximo', from: 'Desde', to: 'Hasta' }[key]}<input type={key === 'from' || key === 'to' ? 'date' : 'text'} inputMode={key.includes('Price') ? 'decimal' : undefined} value={filters[key]} onChange={e => void setFilters({ [key]: e.target.value || null }, { history: 'replace' })} /></label>)}</div>
      {(filters.minPrice || filters.maxPrice) && !filters.currency && <p className="notice">Selecciona una moneda para filtrar por precio.</p>}
      <div className="filter-footer"><Button variant="ghost" onClick={() => void setFilters(Object.fromEntries(Object.keys(parsers).map(k => [k, null])), { history: 'push' })}>Limpiar filtros</Button></div>
    </section>
    <section className="results"><div className="section-heading"><h2>{manifest?.demo ? 'Remates de ejemplo' : 'Remates disponibles'}</h2><span>{results.length} resultados · Fecha de ofertas: más reciente primero</span></div>
      {error ? <div role="alert" className="message">{error} Todavía no hay una publicación disponible.</div> : !manifest ? <div className="message">Cargando datos…</div> : results.length === 0 ? <div className="message">No hay remates que coincidan con los filtros.</div> : <div className="list">{results.map(a => <article className="item" key={a.auction_id}><div><p className="eyebrow">REMATE N.º {a.numero_remate}</p><h3><Link to={`/auctions/${encodeURIComponent(a.auction_id)}${location.search}`}>{a.descripcion || 'Detalle del remate'}</Link></h3><p>{[a.distrito, a.provincia, a.departamento].filter(Boolean).join(', ') || 'Ubicación no disponible'}</p><span className="badge">{a.fase || 'Fase no disponible'}</span></div><div className="amount"><span>PRECIO BASE</span><strong>{a.precio_base?.raw || 'No disponible'}</strong><small>Ofertas: {a.offer_date || a.offer_at?.slice(0, 10) || 'Fecha no disponible'}</small></div></article>)}</div>}
    </section>
  </>
}
