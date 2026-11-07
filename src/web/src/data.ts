export type Summary = {
  auction_id: string
  numero_remate: string
  descripcion: string | null
  departamento: string | null
  provincia: string | null
  distrito: string | null
  tipo_inmueble: string | null
  fase: string | null
  estado: string | null
  offer_date: string | null
  offer_at: string | null
  precio_base: { amount: string | null; currency: string | null; raw: string | null } | null
  detail_path: string
  coordinates?: Coordinate[]
  thumbnail_path?: string | null
  cronograma?: Phase[]
}

export type Coordinate = { latitude: number; longitude: number }
export type Rate = { penToUsd: string; date: string; source: string }
export type Property = { partida_registral: string; tipo_inmueble: string; direccion: string; carga_gravamen: string | null; porcentaje_a_remstar: string; imagenes: number; latitude?: number | null; longitude?: number | null; area_m2?: number | null }
export type Money = Summary['precio_base']
export type Phase = { nro: number; fase: string; fecha_inicio: string; fecha_fin: string }
export type Location = { departamento: string | null; provincia: string | null; distrito: string | null }
export type AuctionDetail = { numero_remate: string; ubicacion?: Location; estado?: { fase: string | null; estado: string | null }; remate: Record<string, string | number | null>; inmuebles: Property[]; cronograma: Phase[]; seguimiento: { expediente: Record<string, string>; eventos: Record<string, string | null>[] } | null; source_url: string }

export function parseMoney(raw: string | number | null | undefined): Money {
  if (raw === null || raw === undefined || raw === '') return null
  const text = String(raw).trim()
  const currency = /^S\/\.?/.test(text) ? 'PEN' : text.startsWith('$') ? 'USD' : null
  const amount = text.replace(/^(S\/\.?|\$)\s*/, '').replace(/,/g, '')
  return { raw: text, currency, amount: currency && /^\d+(\.\d+)?$/.test(amount) ? amount : null }
}

export function otherCurrency(currency: string): string {
  return currency === 'USD' ? 'PEN' : 'USD'
}

export function titleCase(value: string | null | undefined): string {
  return (value || '').toLocaleLowerCase('es').replace(/(^|[\s(-])(\p{L})/gu, (_, space: string, letter: string) => space + letter.toLocaleUpperCase('es'))
}

export function place(location: Partial<Location>): string {
  return [location.distrito, location.provincia, location.departamento].filter((value, index, all) => value && all.indexOf(value) === index).map(titleCase).join(', ')
}

function limaTime(value: string): number {
  return Date.parse(`${value.replace(' ', 'T')}-05:00`)
}

export function currentPhase(phases: Phase[], now = Date.now()): Phase | null {
  return phases.find(phase => now <= limaTime(phase.fecha_fin)) ?? phases.at(-1) ?? null
}

export function phaseState(phase: Phase, current: Phase | null, now = Date.now()): 'done' | 'current' | 'upcoming' {
  if (current && phase.nro === current.nro && now >= limaTime(phase.fecha_inicio)) return 'current'
  return now > limaTime(phase.fecha_fin) ? 'done' : 'upcoming'
}

export function formatDateTime(value: string): string {
  const time = limaTime(value)
  return Number.isNaN(time) ? value : new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima' }).format(time)
}

export function convertedAmount(money: Summary['precio_base'], currency: string, rate: Rate | null): string | null {
  if (!money?.amount || !money.currency || !/^\d+(\.\d+)?$/.test(money.amount)) return null
  if (money.currency === currency) return money.amount
  if (!rate || !/^\d+(\.\d+)?$/.test(rate.penToUsd) || Number(rate.penToUsd) <= 0) return null
  if (!['PEN', 'USD'].includes(currency) || !['PEN', 'USD'].includes(money.currency)) return null
  const [whole, fraction = ''] = money.amount.split('.')
  const [rw, rf = ''] = rate.penToUsd.split('.')
  const amount = BigInt(whole + fraction)
  const factor = BigInt(rw + rf)
  const numerator = currency === 'USD' ? amount * factor * 100n : amount * 10n ** BigInt(rf.length) * 100n
  const denominator = currency === 'USD' ? 10n ** BigInt(fraction.length + rf.length) : 10n ** BigInt(fraction.length) * factor
  const cents = (numerator + denominator / 2n) / denominator
  return `${cents / 100n}.${(cents % 100n).toString().padStart(2, '0')}`
}

export function displayMoney(money: Summary['precio_base'], currency: string, rate: Rate | null): string {
  const amount = convertedAmount(money, currency, rate)
  if (!amount) return money?.raw || 'Precio no disponible'
  const [whole, fraction = ''] = amount.split('.')
  return `${money?.currency !== currency ? '≈ ' : ''}${currency === 'PEN' ? 'S/' : 'US$'} ${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${fraction.padEnd(2, '0').slice(0, 2)}`
}

export type Manifest = { schema_version: number; generated_at: string; dataset_version: string; availability: { path: string }; archive?: { path: string }; demo?: boolean }
export type Snapshot = { auctions: Summary[] }

export const dataPath = import.meta.env.DEV || import.meta.env.VITE_DEMO === 'true' ? 'demo/manifest.json' : 'data/manifest.json'

export function siteUrl(path: string): string {
  return `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(siteUrl(path))
  if (!response.ok || !response.headers.get('content-type')?.includes('json')) throw new Error('No se pudieron cargar los datos.')
  return response.json() as Promise<T>
}

export function sortAuctions(items: Summary[]): Summary[] {
  return [...items].sort((a, b) => {
    const ad = a.offer_date ?? a.offer_at?.slice(0, 10) ?? ''
    const bd = b.offer_date ?? b.offer_at?.slice(0, 10) ?? ''
    return bd.localeCompare(ad) || (b.offer_at ?? '').localeCompare(a.offer_at ?? '') || a.auction_id.localeCompare(b.auction_id)
  })
}

export function compareDecimal(left: string, right: string): number | null {
  if (!/^\d+(\.\d+)?$/.test(left) || !/^\d+(\.\d+)?$/.test(right)) return null
  const [li, lf = ''] = left.split('.')
  const [ri, rf = ''] = right.split('.')
  const l = li.replace(/^0+(?=\d)/, '')
  const r = ri.replace(/^0+(?=\d)/, '')
  const scale = Math.max(lf.length, rf.length)
  return l.length - r.length || l.localeCompare(r) || lf.padEnd(scale, '0').localeCompare(rf.padEnd(scale, '0'))
}

export function orderAuctions(items: Summary[], order: string, currency?: string, rate: Rate | null = null): Summary[] {
  const sorted = sortAuctions(items)
  if (order === 'date-asc') return sorted.sort((a, b) => {
    const left = a.offer_date ?? a.offer_at?.slice(0, 10) ?? ''
    const right = b.offer_date ?? b.offer_at?.slice(0, 10) ?? ''
    return !left ? (right ? 1 : 0) : !right ? -1 : left.localeCompare(right)
  })
  if (order === 'price-asc' || order === 'price-desc') return sorted.sort((a, b) => {
    const left = currency ? convertedAmount(a.precio_base, currency, rate) : a.precio_base?.amount
    const right = currency ? convertedAmount(b.precio_base, currency, rate) : b.precio_base?.amount
    if (!left || !right) return left ? -1 : right ? 1 : 0
    return (compareDecimal(left, right) ?? 0) * (order === 'price-desc' ? -1 : 1)
  })
  return sorted
}

export function formatShortDate(value: string): string {
  const time = limaTime(value)
  return Number.isNaN(time) ? value : new Intl.DateTimeFormat('es-PE', { day: 'numeric', month: 'short', timeZone: 'America/Lima' }).format(time).replace('.', '')
}

export function activePhase(summary: Pick<Summary, 'fase' | 'cronograma'>, now = Date.now()): { fase: string | null; until: string | null } {
  const phase = currentPhase(summary.cronograma || [], now)
  return phase ? { fase: phase.fase, until: phase.fecha_fin } : { fase: summary.fase, until: null }
}
