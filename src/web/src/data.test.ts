import { describe, expect, it } from 'vitest'
import { compareDecimal, convertedAmount, currentPhase, orderAuctions, parseMoney, phaseState, place, siteUrl, sortAuctions, type Summary } from './data'

describe('display conversion', () => {
  const rate = { penToUsd: '0.25', date: '2026-11-07', source: 'fixture' }
  it('converts both ways without altering source prices', () => {
    const money = { amount: '100.00', currency: 'PEN', raw: 'S/ 100' }
    expect(convertedAmount(money, 'USD', rate)).toBe('25.00')
    expect(convertedAmount({ ...money, currency: 'USD' }, 'PEN', rate)).toBe('400.00')
    expect(money.amount).toBe('100.00')
  })
  it('never invents a rate or treats missing prices as zero', () => {
    expect(convertedAmount({ amount: '10', currency: 'USD', raw: '$10' }, 'PEN', null)).toBeNull()
    expect(convertedAmount(null, 'PEN', rate)).toBeNull()
    expect(convertedAmount({ amount: '0', currency: 'PEN', raw: '0' }, 'USD', rate)).toBe('0.00')
  })
})

describe('site paths', () => {
  it('resolves data and assets under the configured base', () => {
    expect(siteUrl('/demo/manifest.json')).toBe(`${import.meta.env.BASE_URL}demo/manifest.json`)
  })
})

describe('result ordering', () => {
  it('sorts precise prices and keeps missing values last', () => {
    const items = [{ auction_id: '1', precio_base: { amount: '9007199254740993' } }, { auction_id: '2', precio_base: null }, { auction_id: '3', precio_base: { amount: '9' } }] as Summary[]
    expect(orderAuctions(items, 'price-asc').map(a => a.auction_id)).toEqual(['3', '1', '2'])
    expect(orderAuctions(items, 'price-desc').map(a => a.auction_id)).toEqual(['1', '3', '2'])
  })
})

describe('decimal comparison', () => {
  it('compares large values without floating point conversion', () => {
    expect(compareDecimal('9007199254740993.01', '9007199254740993.00')).toBeGreaterThan(0)
    expect(compareDecimal('12.00', '12')).toBe(0)
    expect(compareDecimal('bad', '12')).toBeNull()
  })
})

describe('date ordering', () => {
  it('sorts source dates descending and unknown dates last', () => {
    const auctions = [{ auction_id: 'remaju:3', offer_date: null }, { auction_id: 'remaju:1', offer_date: '2026-01-01' }, { auction_id: 'remaju:2', offer_date: '2026-02-01' }] as Summary[]
    expect(sortAuctions(auctions).map(a => a.auction_id)).toEqual(['remaju:2', 'remaju:1', 'remaju:3'])
  })
})

describe('detail helpers', () => {
  const phases = [
    { nro: 1, fase: 'Publicación', fecha_inicio: '2026-11-07 00:00:00', fecha_fin: '2026-11-16 23:59:59' },
    { nro: 2, fase: 'Ofertas', fecha_inicio: '2026-11-20 12:00:00', fecha_fin: '2026-11-21 11:59:59' },
  ]
  it('parses source money with currency', () => {
    expect(parseMoney('S/. 1,163,355.99')).toEqual({ raw: 'S/. 1,163,355.99', currency: 'PEN', amount: '1163355.99' })
    expect(parseMoney('$ 40,066.67')?.currency).toBe('USD')
    expect(parseMoney('')).toBeNull()
  })
  it('formats locations without repeating names', () => {
    expect(place({ distrito: null, provincia: 'CUSCO', departamento: 'CUSCO' })).toBe('Cusco')
    expect(place({ distrito: 'CHINCHA ALTA', provincia: 'CHINCHA', departamento: 'ICA' })).toBe('Chincha Alta, Chincha, Ica')
  })
  it('finds the current phase in Lima time', () => {
    const during = Date.parse('2026-11-10T12:00:00-05:00')
    const gap = Date.parse('2026-11-18T12:00:00-05:00')
    expect(currentPhase(phases, during)?.nro).toBe(1)
    expect(phaseState(phases[0], currentPhase(phases, during), during)).toBe('current')
    expect(phaseState(phases[1], currentPhase(phases, gap), gap)).toBe('upcoming')
    expect(currentPhase(phases, Date.parse('2027-01-01T00:00:00-05:00'))?.nro).toBe(2)
  })
})
