import { currentPhase, formatDateTime, formatDeadline, parseMoney, phaseState, place, titleCase, type AuctionDetail, type Rate, type Summary } from '../data'
import { AuctionStatus } from './auction-status'
import AuctionPhase from './auction-phase'
import { Prices } from './prices'

export default function AuctionHero({ detail, summary, currency, rate }: { detail: AuctionDetail; summary: Summary | null; currency: string; rate: Rate | null }) {
  const kind = [...new Set(detail.inmuebles.map(property => property.tipo_inmueble).filter(Boolean))].map(titleCase).join(' · ')
  const location = place(detail.ubicacion || summary || {})
  const phase = currentPhase(detail.cronograma)
  const state = phase ? phaseState(phase, phase) : null
  const deadline = phase ? formatDeadline(phase.fecha_fin) : null
  const status = summary?.estado || detail.estado?.estado
  const event = detail.seguimiento?.eventos.at(-1)
  const recordedEvent = event?.estado_convocatoria && event.estado_convocatoria !== status ? event : null
  const recorded = recordedEvent?.estado_convocatoria || (detail.estado?.estado !== status ? detail.estado?.estado : null)
  return <>
    <div className="hero-composition">
      <div className="hero-identity">
        <p className="eyebrow">Remate N.º {detail.numero_remate}</p>
        <h1 id="detail-title">{kind || 'Inmueble'}{location && <> en {location}</>}</h1>
        <div className="hero-meta">
          <div className="hero-status"><span className="metadata-label">{summary?.estado ? 'Estado en listado' : 'Estado publicado'}</span><AuctionStatus value={status} /></div>
          <span className="hero-call">{detail.remate.convocatoria ? titleCase(String(detail.remate.convocatoria)) : 'Convocatoria no publicada'}</span>
        </div>
      </div>
      <div className="hero-price"><span className="metadata-label">Precio base</span><Prices money={parseMoney(detail.remate.precio_base) || summary?.precio_base || null} currency={currency} rate={rate} /></div>
    </div>
    <div className="hero-facts">
      <AuctionPhase value={phase?.fase || summary?.fase || detail.estado?.fase} />
      <div className="hero-deadline">
        <span className="metadata-label">{state === 'done' ? 'Último plazo publicado' : 'Plazo publicado'}</span>
        {phase && deadline ? <time dateTime={phase.fecha_fin}><strong>{deadline.date}</strong><span>{deadline.time} · Hora de Perú</span></time> : <span>Sin cronograma publicado.</span>}
      </div>
      {phase && <span className="hero-deadline-note muted">{state === 'upcoming' ? 'Próxima fase según cronograma.' : state === 'done' ? 'El cronograma publicado ha concluido.' : 'Verifica la vigencia del plazo en REMAJU.'}</span>}
    </div>
    {recorded && <aside className="recorded-status" aria-label="Estado registrado en antecedentes"><strong>{recordedEvent ? 'Seguimiento registrado:' : 'Estado registrado en ficha:'}</strong> {recorded}{recordedEvent?.nro_convocatoria && <> · {titleCase(recordedEvent.nro_convocatoria)}</>}{recordedEvent?.fecha_registro && <> · {formatDateTime(recordedEvent.fecha_registro)}</>}<span>No sustituye al estado del listado. Consulta el historial y confirma en REMAJU.</span></aside>}
  </>
}
