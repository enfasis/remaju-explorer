import type { ReactNode } from 'react'
import { formatDateTime, titleCase } from '../data'

export type Tone = 'red' | 'green' | 'neutral'

export function Badge({ tone, label, children }: { tone: Tone; label: string; children: ReactNode }) {
  return <li className={`badge badge-${tone}`}><span className="sr-only">{label}: </span>{children}</li>
}

export function statusTone(status: string | null | undefined): Tone {
  return /desiert|suspend|cancel|nul/i.test(status || '') ? 'red' : 'green'
}

type Props = { phase?: string | null; until?: string | null; status?: string | null; kind?: string | null; call?: string | null; label?: string }

export function AuctionBadges({ phase, until, status, kind, call, label = 'Estado del remate' }: Props) {
  if (!phase && !status && !kind && !call) return null
  return <ul className="badges" aria-label={label}>
    {kind && <Badge tone="neutral" label="Tipo de inmueble">{titleCase(kind)}</Badge>}
    {phase && <Badge tone="neutral" label="Fase actual">{phase}</Badge>}
    {status && <Badge tone={statusTone(status)} label="Estado">{status}</Badge>}
    {call && <Badge tone="neutral" label="Convocatoria">{titleCase(call)}</Badge>}
    {phase && until && <li className="badge-until">Hasta <time dateTime={until}>{formatDateTime(until)}</time></li>}
  </ul>
}
