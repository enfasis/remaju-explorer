import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import AuctionTable from './components/auction-table'
import { orderAuctions, type Summary } from './data'

const auctions = [{ auction_id: 'remaju:2', numero_remate: '2', departamento: 'LIMA', provincia: 'LIMA', distrito: 'LIMA', tipo_inmueble: 'Casa', fase: 'Ofertas', estado: 'En proceso', precio_base: { amount: '10', currency: 'PEN', raw: 'S/ 10' }, coordinates: [] }, { auction_id: 'remaju:10', numero_remate: '10', departamento: 'ICA', provincia: null, coordinates: [] }] as unknown as Summary[]

describe('auction table', () => {
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
    expect(markup).toContain('Ver ficha')
    expect(markup).toContain('Estado en listado')
    expect(markup).toContain('status-green">En proceso')
  })
  it('sorts published states and keeps missing states last', () => {
    const values = [...auctions, { auction_id: 'remaju:3', numero_remate: '3', estado: 'Desierto' } as Summary]
    expect(orderAuctions(values, 'status-asc').map(a => a.estado)).toEqual(['Desierto', 'En proceso', undefined])
  })
})
