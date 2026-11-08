import { lazy, Suspense, useCallback, useEffect, useMemo, useState, type MouseEvent, type ReactNode } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router'
import { loadDetail, loadSnapshot } from '../../cache'
import { Prices } from '../../components/prices'
import AuctionHero from '../../components/auction-hero'
import IconButton from '../../components/icon-button'
import { CloseIcon } from '../../components/icons'
import { currentPhase, formatDateTime, parseMoney, phaseState, titleCase, type AuctionDetail as Detail, type Rate, type Summary } from '../../data'
import { useRate } from '../../use-rate'
import { useTitle } from '../../use-title'

const AuctionMap = lazy(() => import('../../components/auction-map'))

const caseFields: [string, string][] = [['expediente', 'Expediente'], ['materia', 'Materia'], ['distrito_judicial', 'Distrito judicial'], ['organo_jurisdiccional', 'Órgano jurisdiccional'], ['instancia', 'Instancia'], ['resolucion', 'Resolución'], ['fecha_resolucion', 'Fecha de resolución'], ['convocatoria', 'Convocatoria'], ['nro_inscritos', 'Inscritos']]
const moneyFields: [string, string][] = [['precio_base', 'Precio base'], ['tasacion', 'Tasación'], ['incremento_entre_ofertas', 'Incremento entre ofertas'], ['oblaje', 'Oblaje'], ['arancel', 'Arancel']]
const trackingFields: [string, string][] = [['nro_convocatoria', 'Convocatoria'], ['fase_convocatoria', 'Fase'], ['estado_convocatoria', 'Estado'], ['fecha_registro', 'Registrado'], ['procesado_por', 'Procesado por'], ['reanudado', 'Reanudado'], ['fecha_desierto', 'Fecha de desierto']]

function Section({ title, variant = 'record', children }: { title: string; variant?: string; children: ReactNode }) {
  const id = `section-${title.toLocaleLowerCase('es').replace(/\W+/g, '-')}`
  return <section className={`detail-section section-${variant} reveal`} aria-labelledby={id}>
    <h2 id={id}>{title}</h2>
    {children}
  </section>
}

function Fields({ fields, values }: { fields: [string, string][]; values: Record<string, string | number | null | undefined> }) {
  const present = fields.filter(([key]) => values[key] !== null && values[key] !== undefined && values[key] !== '')
  return <dl className="detail-fields">{present.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{String(values[key])}</dd></div>)}</dl>
}

function Amounts({ values, currency, rate }: { values: Detail['remate']; currency: string; rate: Rate | null }) {
  return <dl className="detail-fields amounts">{moneyFields.filter(([key]) => values[key]).map(([key, label]) => <div key={key}><dt>{label}</dt><dd><Prices money={parseMoney(values[key])} currency={currency} rate={rate} className="prices compact" /></dd></div>)}</dl>
}

function Timeline({ phases }: { phases: Detail['cronograma'] }) {
  const current = currentPhase(phases)
  return <ol className="timeline">{phases.map(phase => {
    const state = phaseState(phase, current)
    return <li key={phase.nro} className={`timeline-step ${state}`} aria-current={state === 'current' ? 'step' : undefined}>
      <span className="timeline-dot" aria-hidden="true" />
      <div><strong>{phase.fase}</strong><span>{formatDateTime(phase.fecha_inicio)} – {formatDateTime(phase.fecha_fin)}</span>{state === 'current' && <span className="sr-only"> (fase actual según cronograma publicado)</span>}</div>
    </li>
  })}</ol>
}

export default function AuctionDetail() {
  const { auctionId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [detail, setDetail] = useState<Detail | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [error, setError] = useState('')
  const rate = useRate()
  useTitle(detail ? `Remate ${detail.numero_remate}` : null)
  const currency = new URLSearchParams(location.search).get('currency') === 'USD' ? 'USD' : 'PEN'
  const close = useCallback(() => {
    if ((location.state as { fromList?: boolean } | null)?.fromList) navigate(-1)
    else navigate(`/${location.search}`)
  }, [location, navigate])
  const jump = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return
    event.preventDefault()
    const hash = event.currentTarget.hash
    void navigate(hash, { replace: true, state: location.state, preventScrollReset: true })
    document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' })
  }
  useEffect(() => {
    let active = true
    setDetail(null); setSummary(null); setError('')
    loadSnapshot().then(snapshot => {
      const item = snapshot.auctions.find(a => a.auction_id === auctionId)
      if (!item) throw new Error('Remate no disponible.')
      if (active) setSummary(item)
      return item.detail ?? loadDetail(item.detail_path ?? item.auction_id)
    }).then(value => { if (active) setDetail(value) }).catch((e: Error) => { if (active) setError(e.message) })
    return () => { active = false }
  }, [auctionId])
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape' && !document.querySelector('[role="dialog"]')) close() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [close])
  const points = useMemo(() => (detail?.inmuebles || []).flatMap(p => p.latitude != null && p.longitude != null ? [{ id: p.partida_registral || p.direccion, latitude: p.latitude, longitude: p.longitude, label: titleCase(p.tipo_inmueble) }] : []), [detail])
  return <article className="detail" aria-busy={!detail && !error} aria-labelledby="detail-title">

    {error ? <p role="alert" className="message glass">{error}</p> : !detail ? <p role="status" className="message glass">Cargando detalle…</p> : <>
      <header className="detail-hero reveal">
        <div className="hero-top">
          <span className="metadata-label">Remates judiciales / Registro del inmueble</span>
          <IconButton label="Cerrar y volver a los resultados (Esc)" icon={<CloseIcon />} onPress={close} />
        </div>
        <AuctionHero detail={detail} summary={summary} currency={currency} rate={rate} />
      </header>
      <nav className="detail-navigation" aria-label="En esta ficha"><a href="#section-montos" onClick={jump}>Montos</a><a href="#section-cronograma" onClick={jump}>Cronograma</a><a href="#section-proceso-judicial" onClick={jump}>Proceso judicial</a></nav>
      <div className="detail-grid">
        <Section title="Montos" variant="financial"><Amounts values={detail.remate} currency={currency} rate={rate} />{rate && <p className="muted">Conversión referencial con 1 USD = {(1 / Number(rate.penToUsd)).toFixed(3)} PEN ({rate.date}).</p>}</Section>
        <Section title="Cronograma" variant="timeline"><Timeline phases={detail.cronograma} /><p className="muted">Cronograma publicado · Hora de Perú. Confirma los plazos y el estado en REMAJU.</p></Section>
      </div>
      {detail.remate.descripcion && <Section title="Descripción" variant="editorial"><p className="legal-text">{String(detail.remate.descripcion)}</p></Section>}
      <Section title={detail.inmuebles.length === 1 ? 'Inmueble' : `Inmuebles (${detail.inmuebles.length})`} variant="property">
        {detail.inmuebles.map((property, index) => <article className="property" key={property.partida_registral || index} aria-label={`${property.tipo_inmueble}, partida ${property.partida_registral}`}>
          <h3>{titleCase(property.tipo_inmueble)}</h3>
          <dl className="detail-fields">
            <div><dt>Partida registral</dt><dd>{property.partida_registral}</dd></div>
            {property.area_m2 != null && <div><dt>Área</dt><dd>{property.area_m2.toLocaleString('es-PE')} m²</dd></div>}
            {property.porcentaje_a_remstar && <div><dt>Porcentaje a rematar</dt><dd>{property.porcentaje_a_remstar}</dd></div>}
            <div><dt>Imágenes en REMAJU</dt><dd>{property.imagenes}</dd></div>
          </dl>
          <h4>Dirección</h4><p className="legal-text">{property.direccion}</p>
          {property.carga_gravamen && <><h4>Cargas y gravámenes</h4><p className="legal-text">{property.carga_gravamen}</p></>}
        </article>)}
      </Section>
      {points.length > 0 && <Section title="Ubicación" variant="map"><Suspense fallback={<p role="status">Cargando mapa…</p>}><AuctionMap points={points} /></Suspense></Section>}
      <Section title="Proceso judicial"><Fields fields={caseFields} values={{ ...detail.remate, ...(detail.seguimiento?.expediente || {}) }} /></Section>
      {detail.seguimiento && detail.seguimiento.eventos.length > 0 && <Section title="Seguimiento" variant="history">
        <p className="muted">Antecedentes por convocatoria. Estos registros pueden corresponder a convocatorias anteriores al estado del listado.</p>
        <ol className="events">{detail.seguimiento.eventos.map((event, index) => <li key={index}><Fields fields={trackingFields} values={event} /></li>)}</ol>
      </Section>}
      <p className="source-note reveal">Para verificar, busca el remate <strong>{detail.numero_remate}</strong> en <a href={detail.source_url} target="_blank" rel="noreferrer">REMAJU<span className="sr-only"> (abre en otra pestaña)</span></a>.</p>
    </>}
  </article>
}
