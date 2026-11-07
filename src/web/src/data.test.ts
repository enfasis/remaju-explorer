import { describe, expect, it } from 'vitest'
import { compareDecimal, convertedAmount, orderAuctions, siteUrl, sortAuctions, type Summary } from './data'

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
