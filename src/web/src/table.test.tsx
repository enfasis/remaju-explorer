import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AuctionTable from './components/auction-table'
import { orderAuctions, type Summary } from './data'

const auctions = [{ auction_id: 'remaju:2', numero_remate: '2', departamento: 'LIMA', provincia: 'LIMA', distrito: 'LIMA', tipo_inmueble: 'Casa', fase: 'Ofertas', estado: 'En proceso', precio_base: { amount: '10', currency: 'PEN', raw: 'S/ 10' }, coordinates: [] }, { auction_id: 'remaju:10', numero_remate: '10', departamento: 'ICA', provincia: null, coordinates: [] }] as unknown as Summary[]

describe('auction table', () => {
  afterEach(() => vi.useRealTimers())
  it('sorts auction numbers numerically in both directions', () => {
    expect(orderAuctions(auctions, 'number-asc').map(a => a.numero_remate)).toEqual(['2', '10'])
    expect(orderAuctions(auctions, 'number-desc').map(a => a.numero_remate)).toEqual(['10', '2'])
  })
  it('sorts text columns and keeps missing fields last', () => {
    expect(orderAuctions(auctions, 'department-asc').map(a => a.departamento)).toEqual(['ICA', 'LIMA'])
    expect(orderAuctions(auctions, 'province-desc').map(a => a.provincia)).toEqual(['LIMA', null])
  })
  it('uses semantic headers and preserves filters in detail links', () => {
    const markup = renderToStaticMarkup(<MemoryRouter><AuctionTable auctions={auctions} currency="PEN" rate={null} search="?view=table&department=LIMA" sort="number-asc" onSort={() => {}} onLocate={() => {}} /></MemoryRouter>)
    expect(markup).toContain('aria-sort="ascending"')
    expect(markup).toContain('Ordenar por remate, descendente')
    expect(markup).toContain('view=table&amp;department=LIMA')
    expect(markup).toContain('scope="row"')
  })
  it('shows a single regular price, plain phase and no number prefix or status badge', () => {
    const markup = renderToStaticMarkup(<MemoryRouter><AuctionTable auctions={[auctions[0]]} currency="USD" rate={{ penToUsd: '0.25', date: '2026-11-09', source: 'fixture' }} search="" sort="date-desc" onSort={() => {}} onLocate={() => {}} /></MemoryRouter>)
    expect(markup).toContain('≈ US$ 2.50')
    expect(markup).not.toContain('S/ 10')
    expect(markup).not.toContain('<strong>')
    expect(markup).not.toContain('N.º')
    expect(markup).not.toContain('En proceso')
    expect(markup).not.toContain('class="badge')
    expect(markup).toContain('>Ofertas</td>')
  })
  it('shows and sorts the current phase end, not the offers date, including at the Lima boundary', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-10T12:00:00-05:00'))
    const items = [
      { ...auctions[0], offer_date: '2026-12-20', cronograma: [{ nro: 1, fase: 'Publicación', fecha_inicio: '2026-11-07 00:00:00', fecha_fin: '2026-11-16 23:59:59' }, { nro: 2, fase: 'Ofertas', fecha_inicio: '2026-11-20 12:00:00', fecha_fin: '2026-11-21 11:59:59' }] },
      { ...auctions[1], offer_date: '2026-12-01', cronograma: [{ nro: 1, fase: 'Publicación', fecha_inicio: '2026-11-07 00:00:00', fecha_fin: '2026-11-17 23:59:59' }] },
      { ...auctions[0], auction_id: 'missing', cronograma: [] },
    ]
    const markup = renderToStaticMarkup(<MemoryRouter><AuctionTable auctions={items} currency="PEN" rate={null} search="" sort="date-desc" onSort={() => {}} onLocate={() => {}} /></MemoryRouter>)
    expect(markup).toContain('>Fecha<')
    expect(markup).not.toContain('Fecha de ofertas')
    expect(markup).toContain('dateTime="2026-11-16T23:59:59-05:00"')
    expect(markup).toContain('16 nov')
    expect(markup).not.toContain('20 dic')
    expect(orderAuctions(items, 'date-asc').map(a => a.auction_id)).toEqual(['remaju:2', 'remaju:10', 'missing'])
    expect(orderAuctions(items, 'date-desc').map(a => a.auction_id)).toEqual(['remaju:10', 'remaju:2', 'missing'])
    vi.setSystemTime(new Date('2026-11-17T00:00:00-05:00'))
    expect(orderAuctions(items, 'date-desc')[0].auction_id).toBe('remaju:2')
  })
})
