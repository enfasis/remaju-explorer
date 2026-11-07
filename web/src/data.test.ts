import { describe, expect, it } from 'vitest'
import { compareDecimal, sortAuctions, type Summary } from './data'

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
