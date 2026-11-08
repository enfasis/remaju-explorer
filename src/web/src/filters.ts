import { compareDecimal, convertedAmount, type Rate, type Summary } from './data'

export type Filters = Record<'q' | 'department' | 'province' | 'district' | 'propertyType' | 'phase' | 'currency' | 'minPrice' | 'maxPrice' | 'from' | 'to' | 'mapped' | 'sort', string>
export type Facet = 'department' | 'province' | 'district' | 'propertyType' | 'phase'

const fields = { department: 'departamento', province: 'provincia', district: 'distrito', propertyType: 'tipo_inmueble', phase: 'fase' } as const

export function matches(a: Summary, f: Filters, rate: Rate | null): boolean {
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

export function facetOptions(auctions: Summary[], filters: Filters, rate: Rate | null, facet: Facet): string[] {
  const other = { ...filters, [facet]: '' }
  if (facet === 'department') { other.province = ''; other.district = '' }
  if (facet === 'province') other.district = ''
  return [...new Set(auctions.filter(auction => matches(auction, other, rate)).map(auction => auction[fields[facet]]).filter((value): value is string => Boolean(value)))].sort((a, b) => a.localeCompare(b, 'es'))
}
