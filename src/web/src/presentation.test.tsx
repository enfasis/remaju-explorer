import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { AuctionBadges } from './components/badges'
import ViewSelector, { resultView } from './components/view-selector'

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

describe('auction metadata', () => {
  it('keeps categories and process information neutral and exposes the deadline', () => {
    const markup = renderToStaticMarkup(<AuctionBadges kind="CASA" phase="Inscripción" until="2026-11-09T12:00:00" status="En proceso" call="Primera convocatoria" />)
    expect(markup.match(/badge-neutral/g)).toHaveLength(3)
    expect(markup).toContain('badge-green')
    expect(markup).toContain('<time dateTime="2026-11-09T12:00:00">')
    expect(markup).not.toContain('badge-yellow')
    expect(markup).not.toContain('badge-blue')
  })

  it('reserves warning emphasis for interrupted auctions', () => {
    const markup = renderToStaticMarkup(<AuctionBadges status="Suspendido" />)
    expect(markup).toContain('badge-red')
    expect(markup).not.toContain('badge-green')
  })
})
