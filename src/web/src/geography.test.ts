import { describe, expect, it } from 'vitest'
import { inPeru } from './geography'
import { cleanSnapshot, historyDetail, type HistoricalAuction, type Summary } from './data'

describe('Peru boundary', () => {
  it.each([[-12.0464, -77.0428, true], [-3.75, -73.25, true], [-18.01, -70.25, true], [-13.53, -71.97, true], [37.77, -122.42, false], [40, 70, false], [-16.5, -68.15, false], [-0.18, -78.47, false], [-12, -81, false], [NaN, -77, false]])('checks %s, %s', (lat, lon, expected) => {
    expect(inPeru(lat, lon)).toBe(expected)
  })
  it('filters old cached map coordinates as well as new data', () => {
    const snapshot = cleanSnapshot({ auctions: [{ coordinates: [{ latitude: -12.0464, longitude: -77.0428 }, { latitude: 40, longitude: 70 }] } as Summary] })
    expect(snapshot.auctions[0].coordinates).toHaveLength(1)
  })
  it('builds an auction detail directly from history', () => {
    const auction = { numero_remate: '123', list_data: { fase: 'Publicación', estado: 'En proceso' }, seguimiento: null, detail: { remate_tab: { precio_base: '$ 10' }, inmuebles_tab: { departamento: 'LIMA', provincia: 'LIMA', distrito: 'LIMA', inmuebles: [{ direccion: 'Address', latitude: 40, longitude: 70 }] }, cronograma_tab: { fases: [] } } } as unknown as HistoricalAuction
    const detail = historyDetail(auction)
    expect(detail.numero_remate).toBe('123')
    expect(detail.remate.precio_base).toBe('$ 10')
    expect(detail.inmuebles[0].latitude).toBeNull()
  })
})
