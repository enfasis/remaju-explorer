import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()

function response(value: unknown): Response {
  return new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } })
}

async function hash(value: unknown): Promise<string> {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(value)))
  return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('')
}

beforeEach(() => {
  vi.resetModules()
  fetchMock.mockReset()
  const storage = new Map<string, string>()
  vi.stubGlobal('localStorage', { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value), removeItem: (key: string) => storage.delete(key) })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => vi.unstubAllGlobals())

describe('flat publication cache', () => {
  it('recovers a cached legacy detail link after old objects are removed', async () => {
    const legacy = { schema_version: 1, dataset_version: 'old', availability: { path: 'data/releases/old/availability.json' } }
    const auction = { numero_remate: '123', list_data: {}, seguimiento: null, detail: { remate_tab: {}, inmuebles_tab: { inmuebles: [] }, cronograma_tab: { fases: [] } } }
    const available = { dataset_version: 'v2', auctions: [auction] }
    const modern = { schema_version: 2, dataset_version: 'v2', available: { path: 'available.json', sha256: await hash(available) } }
    fetchMock.mockResolvedValueOnce(response(legacy)).mockResolvedValueOnce(new Response('', { status: 404 })).mockResolvedValueOnce(response(modern)).mockResolvedValueOnce(response(available))
    const cache = await import('./cache')
    expect((await cache.loadDetail('/data/releases/old/auctions/123.json')).numero_remate).toBe('123')
  })
  it('reads full available records and opens details without another download', async () => {
    const auction = { numero_remate: '123', list_data: { descripcion: 'House', fase: 'Ofertas' }, seguimiento: null, detail: { remate_tab: { precio_base: '$ 10' }, inmuebles_tab: { departamento: 'LIMA', provincia: 'LIMA', distrito: 'LIMA', inmuebles: [] }, cronograma_tab: { fases: [] } } }
    const available = { dataset_version: 'v1', auctions: [auction] }
    const manifest = { schema_version: 2, dataset_version: 'v1', available: { path: 'available.json', sha256: await hash(available) } }
    fetchMock.mockResolvedValueOnce(response(manifest)).mockResolvedValueOnce(response(available))
    const cache = await import('./cache')
    const snapshot = await cache.loadSnapshot()
    expect(snapshot.auctions[0].descripcion).toBe('House')
    expect(snapshot.auctions[0].detail?.remate.precio_base).toBe('$ 10')
    expect((await cache.loadDetail('remaju:123')).numero_remate).toBe('123')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
  it('loads daily available data and gets all details from one history file', async () => {
    const snapshot = { dataset_version: 'v1', auctions: [{ auction_id: 'remaju:123', numero_remate: '123', coordinates: [] }] }
    const history = { dataset_version: 'v1', records: { 'remaju:123': { present: true, document: { numero_remate: '123', list_data: {}, seguimiento: null, detail: { remate_tab: { precio_base: '$ 10' }, inmuebles_tab: { inmuebles: [] }, cronograma_tab: { fases: [] } } } } } }
    const manifest = { schema_version: 2, dataset_version: 'v1', available: { path: 'available.json', sha256: await hash(snapshot) }, history: { path: 'history.json', sha256: await hash(history) } }
    fetchMock.mockResolvedValueOnce(response(manifest)).mockResolvedValueOnce(response(snapshot)).mockResolvedValueOnce(response(history))
    const cache = await import('./cache')
    expect((await cache.loadSnapshot()).auctions).toHaveLength(1)
    expect((await cache.loadDetail('remaju:123')).remate.precio_base).toBe('$ 10')
    await cache.loadDetail('remaju:123')
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[2][0]).toContain('history.json')
  })

  it('refreshes the manifest rather than mixing versions during an upload', async () => {
    const first = { dataset_version: 'v1', auctions: [] }
    const second = { dataset_version: 'v2', auctions: [] }
    const oldManifest = { schema_version: 2, dataset_version: 'v1', available: { path: 'available.json', sha256: await hash(first) } }
    const newManifest = { schema_version: 2, dataset_version: 'v2', available: { path: 'available.json', sha256: await hash(second) } }
    fetchMock.mockResolvedValueOnce(response(oldManifest)).mockResolvedValueOnce(response(second)).mockResolvedValueOnce(response(newManifest)).mockResolvedValueOnce(response(second))
    const cache = await import('./cache')
    expect((await cache.loadSnapshot()).dataset_version).toBe('v2')
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it('rejects a checksum mismatch instead of displaying unverified data', async () => {
    const manifest = { schema_version: 2, dataset_version: 'v1', available: { path: 'available.json', sha256: '0'.repeat(64) } }
    fetchMock.mockImplementation(async (path: string) => response(path.includes('manifest') ? manifest : { dataset_version: 'v1', auctions: [] }))
    const cache = await import('./cache')
    await expect(cache.loadSnapshot()).rejects.toThrow('publicación se está actualizando')
  })
})
