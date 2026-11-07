import { lazy, Suspense, useEffect, useId, useMemo, useState, type CSSProperties } from 'react'
import { parseAsString, useQueryStates } from 'nuqs'
import { Input, Label, Switch } from 'tamagui'
import { loadManifest, loadSnapshot } from '../cache'
import AuctionCard from '../components/auction-card'
import type { MapFocus, MapPoint } from '../components/auction-map'
import FilterSelect, { choices } from '../components/filter-select'
import IconButton from '../components/icon-button'
import { ClearFiltersIcon } from '../components/icons'
import { compareDecimal, convertedAmount, orderAuctions, type Manifest, type Rate, type Summary } from '../data'
import { useRate } from '../use-rate'
import { useTitle } from '../use-title'

const AuctionMap = lazy(() => import('../components/auction-map'))

const parsers = { q: parseAsString.withDefault(''), department: parseAsString.withDefault(''), province: parseAsString.withDefault(''), district: parseAsString.withDefault(''), propertyType: parseAsString.withDefault(''), phase: parseAsString.withDefault(''), currency: parseAsString.withDefault('PEN'), minPrice: parseAsString.withDefault(''), maxPrice: parseAsString.withDefault(''), from: parseAsString.withDefault(''), to: parseAsString.withDefault(''), mapped: parseAsString.withDefault(''), sort: parseAsString.withDefault('date-desc') }
type Filters = { [K in keyof typeof parsers]: string }

const sorts = [
  { value: 'date-desc', label: 'Fecha: reciente primero' },
  { value: 'date-asc', label: 'Fecha: antigua primero' },
  { value: 'price-asc', label: 'Precio: menor primero' },
  { value: 'price-desc', label: 'Precio: mayor primero' },
]

function matches(a: Summary, f: Filters, rate: Rate | null): boolean {
  const text = [a.numero_remate, a.descripcion, a.departamento, a.provincia, a.distrito].join(' ').toLocaleLowerCase('es')
  if (f.mapped && !a.coordinates?.length) return false
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

function DateField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const [focused, setFocused] = useState(false)
  return <Input size="sm" className="field" type={value || focused ? 'date' : 'text'} placeholder={label} aria-label={label} value={value} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} onChangeText={onChange} />
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  const id = useId()
  return <div className="toggle">
    <Label htmlFor={id} size="sm">{label}</Label>
    <Switch id={id} size="sm" checked={checked} onCheckedChange={onChange} aria-label={label}>
      <Switch.Thumb transition="quick" />
    </Switch>
  </div>
}

export default function Home() {
  const [filters, setFilters] = useQueryStates(parsers)
  const [manifest, setManifest] = useState<Manifest | null>(null)
  const [auctions, setAuctions] = useState<Summary[]>([])
  const [error, setError] = useState('')
  const [showMap, setShowMap] = useState(false)
  const [focus, setFocus] = useState<MapFocus | null>(null)
  const rate = useRate()
  useTitle()
  useEffect(() => { Promise.all([loadManifest(), loadSnapshot()]).then(([m, data]) => { setManifest(m); setAuctions(data.auctions) }).catch((e: Error) => setError(e.message)) }, [])
  const results = useMemo(() => orderAuctions(auctions.filter(a => matches(a, filters, rate)), filters.sort, filters.currency, rate), [auctions, filters, rate])
  const points = useMemo<MapPoint[]>(() => results.flatMap(a => (a.coordinates || []).map((p, index) => ({ ...p, id: index ? `${a.auction_id}:${index}` : a.auction_id, label: `Remate ${a.numero_remate}`, path: `auctions/${encodeURIComponent(a.auction_id)}${location.search}` }))), [results, filters])
  const locate = (auction: Summary) => { setShowMap(true); setFocus({ id: auction.auction_id, at: Date.now() }) }
  const options = (key: keyof Summary) => [...new Set(auctions.map(a => a[key]).filter((value): value is string => typeof value === 'string' && value.length > 0))].sort()
  const update = (key: keyof Filters, value: string) => void setFilters({ [key]: value || null, ...(key === 'department' ? { province: null, district: null } : key === 'province' ? { district: null } : {}) }, { history: 'push' })
  const type = (key: keyof Filters, value: string) => void setFilters({ [key]: value || null }, { history: 'replace' })
  const clear = () => void setFilters(Object.fromEntries(Object.keys(parsers).map(k => [k, null])), { history: 'push' })
  const select = (label: string, key: keyof Filters, values: string[]) => <FilterSelect label={label} value={filters[key]} options={choices(values)} onChange={value => update(key, value)} />
  const resultsLabel = `${results.length} resultados${manifest?.demo ? ' · Muestra parcial del 07/11/2026' : ''}`
  return <>
    <h1 className="sr-only">Remates judiciales del Perú</h1>
    <section className="filters glass" aria-label="Filtros de remates">
      <form className="filter-grid" role="search" aria-controls="auction-list" onSubmit={event => event.preventDefault()}>
        <Input size="sm" className="field search" type="search" placeholder="Buscar por número, ubicación o descripción" aria-label="Buscar remates" value={filters.q} onChangeText={value => type('q', value)} />
        {select('Departamento', 'department', options('departamento'))}
        {select('Provincia', 'province', options('provincia'))}
        {select('Distrito', 'district', options('distrito'))}
        {select('Tipo de inmueble', 'propertyType', options('tipo_inmueble'))}
        {select('Fase', 'phase', options('fase'))}
        <Input size="sm" className="field" inputMode="decimal" placeholder={`Precio mínimo (${filters.currency})`} aria-label={`Precio mínimo en ${filters.currency}`} value={filters.minPrice} onChangeText={value => type('minPrice', value)} />
        <Input size="sm" className="field" inputMode="decimal" placeholder={`Precio máximo (${filters.currency})`} aria-label={`Precio máximo en ${filters.currency}`} value={filters.maxPrice} onChangeText={value => type('maxPrice', value)} />
        <DateField label="Ofertas desde" value={filters.from} onChange={value => type('from', value)} />
        <DateField label="Ofertas hasta" value={filters.to} onChange={value => type('to', value)} />
        <div className="filter-actions">
          <Toggle label="Con mapa" checked={filters.mapped === '1'} onChange={checked => update('mapped', checked ? '1' : '')} />
          <Toggle label="USD" checked={filters.currency === 'USD'} onChange={checked => update('currency', checked ? 'USD' : '')} />
          <IconButton label="Limpiar filtros" icon={<ClearFiltersIcon />} controls="auction-list" onPress={clear} />
        </div>
      </form>
    </section>
    <section className="results" aria-labelledby="results-title">
      <h2 id="results-title" className="sr-only">Resultados</h2>
      <div className="results-bar">
        <span role="status" aria-live="polite">{resultsLabel}</span>
        <div className="result-controls">
          <Toggle label="Mapa" checked={showMap} onChange={setShowMap} />
          <FilterSelect label="Ordenar por" value={filters.sort} options={sorts} onChange={value => update('sort', value || 'date-desc')} />
        </div>
      </div>
      <div className={showMap ? 'results-layout with-map' : 'results-layout'}>
        <div>{error ? <div role="alert" className="message glass">{error} Todavía no hay una publicación disponible.</div> : !manifest ? <div className="message glass" role="status">Cargando datos…</div> : results.length === 0 ? <div className="message glass" role="status">No hay remates que coincidan con los filtros.</div> : <ul id="auction-list" className="list" aria-label="Lista de remates">{results.map((a, index) => <li key={a.auction_id} className="list-item" style={{ '--i': Math.min(index, 12) } as CSSProperties}>
          <AuctionCard auction={a} currency={filters.currency} rate={rate} search={location.search} onLocate={a.coordinates?.length ? () => locate(a) : undefined} />
        </li>)}</ul>}</div>
        {showMap && <Suspense fallback={<p role="status">Cargando mapa…</p>}><AuctionMap points={points} focus={focus} /></Suspense>}
      </div>
    </section>
  </>
}
