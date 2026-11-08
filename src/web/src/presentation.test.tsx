import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { AuctionStatus, statusTone } from './components/auction-status'
import ViewSelector, { resultView } from './components/view-selector'
import { Prices } from './components/prices'

describe('result views', () => {
  it('defaults to the table, including legacy card links', () => {
    for (const value of ['', 'table', 'cards', 'unknown']) expect(resultView(value)).toBe('table')
    expect(resultView('map')).toBe('map')
  })

  it.each(['table', 'map'] as const)('shows one selected view for %s', value => {
    const markup = renderToStaticMarkup(<ViewSelector value={value} onChange={() => {}} />)
    expect(markup).toContain('aria-label="Vista de resultados"')
    expect(markup.match(/aria-pressed="true"/g)).toHaveLength(1)
    expect(markup).toContain(`aria-pressed="true" aria-controls="auction-list">${value === 'table' ? 'Tabla' : 'Mapa'}`)
    expect(markup).not.toContain('Tarjetas')
  })
})

describe('auction status', () => {
  it('communicates ongoing state through text as well as color', () => {
    const markup = renderToStaticMarkup(<AuctionStatus value="En proceso" />)
    expect(markup).toContain('status-green')
    expect(markup).toContain('En proceso')
  })

  it('reserves warning emphasis for interrupted auctions', () => {
    const markup = renderToStaticMarkup(<AuctionStatus value="Suspendido" />)
    expect(markup).toContain('status-red')
    expect(markup).not.toContain('status-green')
  })

  it('does not mark finished or unknown statuses as ongoing', () => {
    for (const status of ['Finalizado', 'Adjudicado', 'Inactivo', 'No disponible', 'Unknown', '', null]) expect(statusTone(status)).toBe('neutral')
    expect(statusTone('En proceso')).toBe('green')
    expect(statusTone('Pendiente')).toBe('warning')
  })
})

describe('price presentation', () => {
  it('does not repeat the native currency when a conversion rate is unavailable', () => {
    const markup = renderToStaticMarkup(<Prices money={{ raw: '$ 40,066.67', currency: 'USD', amount: '40066.67' }} currency="PEN" rate={null} />)
    expect(markup).toContain('$ 40,066.67')
    expect(markup).not.toContain('<span>')
  })
})
