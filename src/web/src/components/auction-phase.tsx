export default function AuctionPhase({ value }: { value: string | null | undefined }) {
  return value ? <span className="phase-chip" aria-label={`Fase publicada: ${value}`}>{value}</span> : null
}
