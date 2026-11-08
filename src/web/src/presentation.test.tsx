import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { AuctionBadges } from './components/badges'
import { Prices } from './components/prices'

describe('original auction presentation', () => {
  it('preserves the colorful property, phase, status and convocatoria badges', () => {
    const markup = renderToStaticMarkup(<AuctionBadges kind="CASA" phase="Inscripción" status="En proceso" call="Primera convocatoria" />)
    for (const color of ['yellow', 'blue', 'green', 'red']) expect(markup).toContain(`badge-${color}`)
    expect(markup).toContain('Casa')
    expect(markup).toContain('Inscripción')
    expect(markup).toContain('En proceso')
  })

  it('keeps shared price formatting unchanged after removing the card component', () => {
    const markup = renderToStaticMarkup(<Prices money={{ amount: '100.00', currency: 'PEN', raw: 'S/ 100' }} currency="PEN" rate={{ penToUsd: '0.25', date: '2026-11-07', source: 'fixture' }} />)
    expect(markup).toContain('<strong>S/ 100.00</strong>')
    expect(markup).toContain('<span>≈ US$ 25.00</span>')
  })

  it('does not invent metadata or prices when data is absent', () => {
    expect(renderToStaticMarkup(<AuctionBadges />)).toBe('')
    expect(renderToStaticMarkup(<Prices money={null} currency="PEN" rate={null} />)).toContain('Precio no disponible')
  })
})
