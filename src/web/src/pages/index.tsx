import { lazy, Suspense, useEffect, useId, useMemo, useState } from 'react'
import { parseAsString, useQueryStates } from 'nuqs'
import { Input, Label, Switch } from 'tamagui'
import { loadManifest, loadSnapshot } from '../cache'
import ViewSelector, { resultView } from '../components/view-selector'
import AuctionTable, { tableColumns } from '../components/auction-table'
import type { MapFocus, MapPoint } from '../components/auction-map'
import FilterSelect, { choices } from '../components/filter-select'
import IconButton from '../components/icon-button'
import { ClearFiltersIcon } from '../components/icons'
import { orderAuctions, type Manifest, type Summary } from '../data'
import { facetOptions, matches, type Facet, type Filters } from '../filters'
import { useRate } from '../use-rate'
import { useTitle } from '../use-title'

const AuctionMap = lazy(() => import('../components/auction-map'))

const parsers = { q: parseAsString.withDefault(''), department: parseAsString.withDefault(''), province: parseAsString.withDefault(''), district: parseAsString.withDefault(''), propertyType: parseAsString.withDefault(''), phase: parseAsString.withDefault(''), currency: parseAsString.withDefault('PEN'), minPrice: parseAsString.withDefault(''), maxPrice: parseAsString.withDefault(''), from: parseAsString.withDefault(''), to: parseAsString.withDefault(''), mapped: parseAsString.withDefault(''), sort: parseAsString.withDefault('date-desc'), view: parseAsString.withDefault('') }

const sorts = [
  { value: 'date-desc', label: 'Fecha: reciente primero' },
  { value: 'date-asc', label: 'Fecha: antigua primero' },
  { value: 'price-asc', label: 'Precio: menor primero' },
  { value: 'price-desc', label: 'Precio: mayor primero' },
  { value: 'province-asc', label: 'Provincia: ascendente' },
  { value: 'province-desc', label: 'Provincia: descendente' },
  { value: 'district-asc', label: 'Distrito: ascendente' },
  { value: 'district-desc', label: 'Distrito: descendente' },
  ...tableColumns.filter(column => column.key !== 'date' && column.key !== 'price').flatMap(column => [{ value: `${column.key}-asc`, label: `${column.label}: ascendente` }, { value: `${column.key}-desc`, label: `${column.label}: descendente` }]),
]

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
  const view = resultView(filters.view)
  const [focus, setFocus] = useState<MapFocus | null>(null)
  const rate = useRate()
  useTitle()
  useEffect(() => { Promise.all([loadManifest(), loadSnapshot()]).then(([m, data]) => { setManifest(m); setAuctions(data.auctions) }).catch((e: Error) => setError(e.message)) }, [])
  const results = useMemo(() => orderAuctions(auctions.filter(a => matches(a, filters, rate)), filters.sort, filters.currency, rate), [auctions, filters, rate])
  const points = useMemo<MapPoint[]>(() => results.flatMap(a => (a.coordinates || []).map((p, index) => ({ ...p, id: index ? `${a.auction_id}:${index}` : a.auction_id, label: `Remate ${a.numero_remate}`, path: `auctions/${encodeURIComponent(a.auction_id)}${location.search}` }))), [results, filters])
  const locate = (auction: Summary) => { void setFilters({ view: 'map' }, { history: 'push' }); setFocus({ id: auction.auction_id, at: Date.now() }) }
  const options = (key: Facet) => facetOptions(auctions, filters, rate, key)
  const update = (key: keyof Filters, value: string) => void setFilters({ [key]: value || null, ...(key === 'department' ? { province: null, district: null } : key === 'province' ? { district: null } : {}) }, { history: 'push' })
  const type = (key: keyof Filters, value: string) => void setFilters({ [key]: value || null }, { history: 'replace' })
  const clear = () => void setFilters(Object.fromEntries(Object.keys(parsers).filter(key => key !== 'view').map(k => [k, null])), { history: 'push' })
  const select = (label: string, key: keyof Filters, values: string[]) => <FilterSelect label={label} value={filters[key]} options={choices(values)} onChange={value => update(key, value)} />
  const resultsLabel = `${results.length} resultados${manifest?.demo ? ' · Muestra parcial del 07/11/2026' : manifest?.scope === 'partial' ? ' · Muestra parcial' : ''}`
  const advancedCount = ['province', 'district', 'phase', 'minPrice', 'maxPrice', 'from', 'to', 'mapped'].filter(key => filters[key as keyof Filters]).length
  return <>
    <header className="catalogue-heading">
      <div><p className="eyebrow">Perú / Consulta pública</p><h1>Remates judiciales</h1></div>
      <p>Inmuebles, montos y plazos.<br />La información para comparar, en un solo registro.</p>
    </header>
    <section className="filters" aria-label="Filtros de remates">
      <form role="search" aria-controls="auction-list" onSubmit={event => event.preventDefault()}>
        <label className="search-label" htmlFor="auction-search">Encuentra un remate</label>
        <Input id="auction-search" size="lg" className="field search" type="search" placeholder="Número de remate, ubicación o descripción…" aria-label="Buscar remates" value={filters.q} onChangeText={value => type('q', value)} />
        <div className="essential-filters">
          <div className="filter-field"><span>Departamento</span>{select('Departamento', 'department', options('department'))}</div>
          <div className="filter-field"><span>Inmueble</span>{select('Tipo de inmueble', 'propertyType', options('propertyType'))}</div>
          <div className="filter-actions">
            <Toggle label="USD" checked={filters.currency === 'USD'} onChange={checked => update('currency', checked ? 'USD' : '')} />
            <IconButton label="Limpiar filtros" icon={<ClearFiltersIcon />} controls="auction-list" onPress={clear} />
          </div>
        </div>
        <details className="advanced-filters" open={advancedCount > 0 || undefined}>
          <summary>Filtros avanzados <span>{advancedCount ? `${advancedCount} activos` : 'Ubicación, precio y fechas'}</span></summary>
          <div className="filter-grid">
            <div className="filter-field"><span>Provincia</span>{select('Provincia', 'province', options('province'))}</div>
            <div className="filter-field"><span>Distrito</span>{select('Distrito', 'district', options('district'))}</div>
            <div className="filter-field"><span>Fase</span>{select('Fase', 'phase', options('phase'))}</div>
            <div className="filter-field"><span>Precio mínimo · {filters.currency}</span><Input size="sm" className="field" inputMode="decimal" placeholder="Sin mínimo" aria-label={`Precio mínimo en ${filters.currency}`} value={filters.minPrice} onChangeText={value => type('minPrice', value)} /></div>
            <div className="filter-field"><span>Precio máximo · {filters.currency}</span><Input size="sm" className="field" inputMode="decimal" placeholder="Sin máximo" aria-label={`Precio máximo en ${filters.currency}`} value={filters.maxPrice} onChangeText={value => type('maxPrice', value)} /></div>
            <div className="filter-field"><span>Ofertas desde</span><DateField label="Ofertas desde" value={filters.from} onChange={value => type('from', value)} /></div>
            <div className="filter-field"><span>Ofertas hasta</span><DateField label="Ofertas hasta" value={filters.to} onChange={value => type('to', value)} /></div>
            <Toggle label="Solo con ubicación" checked={filters.mapped === '1'} onChange={checked => update('mapped', checked ? '1' : '')} />
          </div>
        </details>
      </form>
    </section>
    <section className="results" aria-labelledby="results-title">
      <h2 id="results-title" className="sr-only">Resultados</h2>
      <div className="results-bar">
        <span role="status" aria-live="polite">{resultsLabel}</span>
        <div className="result-controls">
          <ViewSelector value={view} onChange={value => void setFilters({ view: value === 'table' ? null : value }, { history: 'push' })} />
          <FilterSelect label="Ordenar por" value={filters.sort} options={sorts} onChange={value => update('sort', value || 'date-desc')} />
        </div>
      </div>
      <div className="results-layout">
        <div>{error ? <div role="alert" className="message glass">{error} Todavía no hay una publicación disponible.</div> : !manifest ? <div className="message glass" role="status">Cargando datos…</div> : results.length === 0 ? <div className="message glass" role="status">No hay remates que coincidan con los filtros.</div> : view === 'table' ? <AuctionTable auctions={results} currency={filters.currency} rate={rate} search={location.search} sort={filters.sort} onSort={value => update('sort', value)} onLocate={locate} /> : <div id="auction-list"><Suspense fallback={<p role="status">Cargando mapa…</p>}><AuctionMap points={points} focus={focus} /></Suspense></div>}</div>
      </div>
    </section>
  </>
}
