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
}

export type Manifest = { schema_version: number; generated_at: string; dataset_version: string; availability: { path: string }; archive?: { path: string } }
export type Snapshot = { auctions: Summary[] }

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
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
