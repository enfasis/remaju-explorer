import { describe, expect, it } from 'vitest'
import { facetOptions, type Filters } from './filters'
import type { Summary } from './data'

const defaults: Filters = { q: '', department: '', province: '', district: '', propertyType: '', phase: '', currency: 'PEN', minPrice: '', maxPrice: '', from: '', to: '', mapped: '', sort: 'number-desc' }
const auctions = [
  { numero_remate: '1', departamento: 'LIMA', provincia: 'LIMA', distrito: 'MIRAFLORES', tipo_inmueble: 'Casa', fase: 'Ofertas', descripcion: 'Parque', precio_base: { amount: '100', currency: 'PEN' }, offer_date: '2026-11-10', coordinates: [{ latitude: -12.12, longitude: -77.03 }] },
  { numero_remate: '2', departamento: 'LIMA', provincia: 'HUAURA', distrito: 'HUACHO', tipo_inmueble: 'Terreno', fase: 'Publicación', descripcion: 'Campo', precio_base: { amount: '200', currency: 'PEN' }, offer_date: '2026-11-20', coordinates: [] },
  { numero_remate: '3', departamento: 'ICA', provincia: 'CHINCHA', distrito: 'SUNAMPE', tipo_inmueble: 'Casa', fase: 'Publicación', descripcion: 'Parque', precio_base: { amount: '300', currency: 'PEN' }, offer_date: '2026-11-30', coordinates: [] },
] as Summary[]

describe('dependent filter options', () => {
  it('narrows provinces and districts to the department', () => {
    const filters = { ...defaults, department: 'LIMA' }
    expect(facetOptions(auctions, filters, null, 'province')).toEqual(['HUAURA', 'LIMA'])
    expect(facetOptions(auctions, filters, null, 'district')).toEqual(['HUACHO', 'MIRAFLORES'])
  })
  it('lets parent locations change without being locked by their descendants', () => {
    const filters = { ...defaults, department: 'LIMA', province: 'LIMA', district: 'MIRAFLORES' }
    expect(facetOptions(auctions, filters, null, 'department')).toEqual(['ICA', 'LIMA'])
    expect(facetOptions(auctions, filters, null, 'province')).toEqual(['HUAURA', 'LIMA'])
  })
  it('ignores its own selection while respecting the other filters', () => {
    const filters = { ...defaults, department: 'LIMA', propertyType: 'Casa' }
    expect(facetOptions(auctions, filters, null, 'propertyType')).toEqual(['Casa', 'Terreno'])
    expect(facetOptions(auctions, filters, null, 'phase')).toEqual(['Ofertas'])
  })
  it('updates options for search, price, date and map filters', () => {
    expect(facetOptions(auctions, { ...defaults, q: 'Campo' }, null, 'propertyType')).toEqual(['Terreno'])
    expect(facetOptions(auctions, { ...defaults, minPrice: '250' }, null, 'department')).toEqual(['ICA'])
    expect(facetOptions(auctions, { ...defaults, to: '2026-11-15' }, null, 'phase')).toEqual(['Ofertas'])
    expect(facetOptions(auctions, { ...defaults, mapped: '1' }, null, 'district')).toEqual(['MIRAFLORES'])
  })
  it('does not invent options for an empty result set or mutate URL state', () => {
    const filters = { ...defaults, q: 'missing' }
    expect(facetOptions(auctions, filters, null, 'department')).toEqual([])
    expect(filters.q).toBe('missing')
  })
})
