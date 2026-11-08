export type Tone = 'red' | 'green' | 'warning' | 'neutral'

export function statusTone(status: string | null | undefined): Tone {
  if (/desiert|suspend|cancel|nul/i.test(status || '')) return 'red'
  if (/pendiente|espera/i.test(status || '')) return 'warning'
  return /^(en proceso|vigente|activ[oa]|disponible|confirmad[oa])$/i.test(status?.trim() || '') ? 'green' : 'neutral'
}

export function AuctionStatus({ value }: { value: string | null | undefined }) {
  return <span className={`auction-status status-${statusTone(value)}`}>{value || 'Sin estado publicado'}</span>
}
