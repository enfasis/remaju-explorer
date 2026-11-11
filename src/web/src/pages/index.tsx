import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { parseAsString, useQueryStates } from 'nuqs'
import { Input } from 'tamagui'
import { loadManifest, loadSnapshot } from '../cache'
import AuctionTable from '../components/auction-table'
import type { MapFocus, MapPoint } from '../components/auction-map'
import FilterSelect, { choices } from '../components/filter-select'
import IconButton from '../components/icon-button'
import Spinner from '../components/spinner'
import { ClearFiltersIcon, DollarIcon, MapIcon, PinIcon } from '../components/icons'
import { orderAuctions, type Manifest, type Summary } from '../data'
import { facetOptions, matches, type Facet, type Filters } from '../filters'
import { useRate } from '../use-rate'
import { useTitle } from '../use-title'

const AuctionMap = lazy(() => import('../components/auction-map'))

const parsers = { q: parseAsString.withDefault(''), department: parseAsString.withDefault(''), province: parseAsString.withDefault(''), district: parseAsString.withDefault(''), propertyType: parseAsString.withDefault(''), phase: parseAsString.withDefault(''), currency: parseAsString.withDefault('PEN'), minPrice: parseAsString.withDefault(''), maxPrice: parseAsString.withDefault(''), from: parseAsString.withDefault(''), to: parseAsString.withDefault(''), mapped: parseAsString.withDefault(''), sort: parseAsString.withDefault('number-desc'), view: parseAsString.withDefault('') }

function DateField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const [focused, setFocused] = useState(false)
  return <span className="field-frame"><Input size="sm" className="field" type={value || focused ? 'date' : 'text'} placeholder={label} aria-label={label} value={value} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} onChangeText={onChange} /></span>
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
  const options = (key: Facet) => facetOptions(auctions, filters, rate, key)
  const update = (key: keyof Filters, value: string) => void setFilters({ [key]: value || null, ...(key === 'department' ? { province: null, district: null } : key === 'province' ? { district: null } : {}) }, { history: 'push' })
  const type = (key: keyof Filters, value: string) => void setFilters({ [key]: value || null }, { history: 'replace' })
  const clear = () => void setFilters(Object.fromEntries(Object.keys(parsers).filter(key => key !== 'view').map(k => [k, null])), { history: 'push' })
  const select = (label: string, key: keyof Filters, values: string[]) => <FilterSelect label={label} value={filters[key]} options={choices(values)} onChange={value => update(key, value)} />
  const resultsLabel = error ? 'Resultados no disponibles' : !manifest ? 'Consultando remates…' : `${results.length} resultados${manifest.demo ? ' · Muestra parcial del 07/11/2026' : manifest.scope === 'partial' ? ' · Muestra parcial' : ''}`
  return <>
    <h1 className="sr-only">Remates judiciales del Perú</h1>
    <section className="filters" aria-label="Filtros de remates">
      <form className="filter-grid" role="search" aria-controls="auction-list" onSubmit={event => event.preventDefault()}>
        <span className="field-frame search"><Input size="sm" className="field" type="search" placeholder="Buscar por número, ubicación o descripción" aria-label="Buscar remates" value={filters.q} onChangeText={value => type('q', value)} /></span>
        {select('Departamento', 'department', options('department'))}
        {select('Provincia', 'province', options('province'))}
        {select('Distrito', 'district', options('district'))}
        {select('Tipo de inmueble', 'propertyType', options('propertyType'))}
        {select('Fase', 'phase', options('phase'))}
        <span className="field-frame"><Input size="sm" className="field" inputMode="decimal" placeholder={`Precio mínimo (${filters.currency})`} aria-label={`Precio mínimo en ${filters.currency}`} value={filters.minPrice} onChangeText={value => type('minPrice', value)} /></span>
        <span className="field-frame"><Input size="sm" className="field" inputMode="decimal" placeholder={`Precio máximo (${filters.currency})`} aria-label={`Precio máximo en ${filters.currency}`} value={filters.maxPrice} onChangeText={value => type('maxPrice', value)} /></span>
        <DateField label="Ofertas desde" value={filters.from} onChange={value => type('from', value)} />
        <DateField label="Ofertas hasta" value={filters.to} onChange={value => type('to', value)} />
        <div className="filter-actions">
          <IconButton label="Solo remates con ubicación en el mapa" icon={<PinIcon />} pressed={filters.mapped === '1'} onPress={() => update('mapped', filters.mapped === '1' ? '' : '1')} />
          <IconButton label="Limpiar filtros" icon={<ClearFiltersIcon />} controls="auction-list" onPress={clear} />
        </div>
      </form>
    </section>
    <section className="results" aria-labelledby="results-title">
      <h2 id="results-title" className="sr-only">Resultados</h2>
      <div className="results-bar">
        <span role="status" aria-live="polite">{resultsLabel}</span>
        <div className="result-controls">
          <IconButton label="Mostrar mapa" icon={<MapIcon />} pressed={showMap} controls="auction-map" onPress={() => setShowMap(!showMap)} />
          <IconButton label="Mostrar precios en USD" icon={<DollarIcon />} pressed={filters.currency === 'USD'} controls="auction-list" onPress={() => update('currency', filters.currency === 'USD' ? '' : 'USD')} />
        </div>
      </div>
      <div className={showMap ? 'results-layout with-map' : 'results-layout'}>
        <div><AuctionTable auctions={results} currency={filters.currency} rate={rate} search={location.search} sort={filters.sort} onSort={value => update('sort', value)} onLocate={locate} loading={!manifest && !error} error={error} /></div>
        {showMap && <Suspense fallback={<Spinner label="Cargando mapa…" />}><AuctionMap points={points} focus={focus} /></Suspense>}
      </div>
    </section>
  </>
}
