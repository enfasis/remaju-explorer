import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AuctionHero from './components/auction-hero'
import type { AuctionDetail, Summary } from './data'

const detail: AuctionDetail = {
  numero_remate: '123', ubicacion: { departamento: 'AREQUIPA', provincia: null, distrito: null }, estado: { estado: 'Desierto', fase: 'Ofertas' },
  remate: { precio_base: 'S/. 269,947.37', convocatoria: 'SEGUNDA CONVOCATORIA' },
  inmuebles: [{ tipo_inmueble: 'CASA', partida_registral: '123', direccion: 'Arequipa', carga_gravamen: null, porcentaje_a_remstar: '100%', imagenes: 0 }],
  cronograma: [{ nro: 1, fase: 'Publicación e inscripción', fecha_inicio: '2026-11-07 00:00:00', fecha_fin: '2026-11-17 23:59:59' }],
  seguimiento: { expediente: {}, eventos: [{ estado_convocatoria: 'Desierto', nro_convocatoria: 'PRIMERA CONVOCATORIA', fecha_registro: '2026-10-01' }] },
  source_url: 'https://example.invalid',
}
const summary = { estado: 'En proceso' } as Summary

afterEach(() => vi.useRealTimers())

describe('auction hero', () => {
  it('distinguishes the published status from a recorded convocatoria', () => {
    const markup = renderToStaticMarkup(<AuctionHero detail={detail} summary={summary} currency="PEN" rate={null} />)
    expect(markup).toContain('Estado en listado')
    expect(markup).toContain('status-green">En proceso')
    expect(markup).toContain('Seguimiento registrado:')
    expect(markup).toContain('Desierto')
    expect(markup).toContain('Primera Convocatoria')
    expect(markup).toContain('Segunda Convocatoria')
    expect(markup).toContain('S/ 269,947.37')
    expect(markup).toContain('Hora de Perú')
  })

  it('labels concluded schedules instead of suggesting a live deadline', () => {
    vi.useFakeTimers().setSystemTime(new Date('2027-01-01T12:00:00Z'))
    const markup = renderToStaticMarkup(<AuctionHero detail={detail} summary={summary} currency="PEN" rate={null} />)
    expect(markup).toContain('Último plazo publicado')
    expect(markup).toContain('El cronograma publicado ha concluido.')
  })

  it('does not add an alarming history notice when the published and recorded states agree', () => {
    const matching = { ...detail, estado: { estado: 'En proceso', fase: 'Inscripción' }, seguimiento: { expediente: {}, eventos: [{ estado_convocatoria: 'En proceso' }] } }
    const markup = renderToStaticMarkup(<AuctionHero detail={matching} summary={summary} currency="PEN" rate={null} />)
    expect(markup).not.toContain('recorded-status')
    expect(markup).not.toContain('badge')
  })

  it('handles missing prices, locations, statuses and schedules without invented facts', () => {
    const markup = renderToStaticMarkup(<AuctionHero detail={{ ...detail, ubicacion: undefined, estado: undefined, remate: {}, inmuebles: [], cronograma: [], seguimiento: null }} summary={null} currency="PEN" rate={null} />)
    expect(markup).toContain('Sin estado publicado')
    expect(markup).toContain('Precio no disponible')
    expect(markup).toContain('Sin cronograma publicado.')
    expect(markup).not.toContain('Seguimiento registrado')
  })
})
