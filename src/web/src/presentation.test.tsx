import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuctionBadges } from './components/badges'
import { Prices } from './components/prices'
import Brand from './components/brand'
import Footer from './components/footer'
import Spinner from './components/spinner'
import { PinIcon } from './components/icons'

describe('original auction presentation', () => {
  it('uses lighter strokes for interface icons', () => {
    expect(renderToStaticMarkup(<PinIcon />)).toContain('stroke-width="1.5"')
  })
  it('announces reusable loading indicators with a hidden decorative spinner', () => {
    const markup = renderToStaticMarkup(<Spinner label="Cargando publicación…" />)
    expect(markup).toContain('role="status"')
    expect(markup).toContain('class="spinner" aria-hidden="true"')
    expect(markup).toContain('Cargando publicación…')
  })
  it('keeps the integrated footer navigation and source disclaimer', () => {
    const markup = renderToStaticMarkup(<MemoryRouter><Footer /></MemoryRouter>)
    expect(markup).toContain('role="contentinfo"')
    expect(markup).toContain('href="/downloads"')
    expect(markup).toContain('no afiliada al Poder Judicial')
    expect(markup).not.toContain('class="weave"')
  })
  it('shares the multicolor wordmark with an accessible home link and separate mm', () => {
    const markup = renderToStaticMarkup(<MemoryRouter><Brand /></MemoryRouter>)
    expect(markup).toContain('aria-label="remaju mm, ir al inicio"')
    expect(markup).toContain('class="brand-word"')
    expect(markup).toContain('<span>r</span><span>e</span><span>m</span><span>a</span><span>j</span><span>u</span>')
    expect(markup).toContain('<sup aria-hidden="true">mm</sup>')
  })
  it('preserves the colorful property, phase, status and convocatoria badges', () => {
    const markup = renderToStaticMarkup(<AuctionBadges kind="CASA" phase="Inscripción" status="En proceso" call="Primera convocatoria" />)
    for (const color of ['blue', 'green', 'red']) expect(markup).toContain(`badge-${color}`)
    expect(markup).not.toContain('badge-yellow')
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
