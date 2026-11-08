import { availableReference, cleanDetail, cleanSnapshot, dataPath, fetchJson, historyDetail, HttpError, summaryFromAuction, type AuctionDetail, type FileReference, type FullSnapshot, type History, type Manifest, type Snapshot } from './data'

const prefix = 'remaju:'
const manifestKey = `${prefix}manifest:${dataPath}`
const manifestMaxAge = 5 * 60 * 1000
const memory = new Map<string, Promise<unknown>>()

type Entry<T> = { at: number; value: T }

function read<T>(key: string): Entry<T> | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) as Entry<T> : null
  } catch {
    return null
  }
}

function write<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify({ at: Date.now(), value }))
  } catch {
    return
  }
}

function prune(version: string): void {
  const keep = `${prefix}${version}:`
  for (const key of Object.keys(localStorage)) if (key.startsWith(prefix) && key !== manifestKey && !key.startsWith(keep)) localStorage.removeItem(key)
}

function once<T>(key: string, load: () => Promise<T>): Promise<T> {
  const existing = memory.get(key)
  if (existing) return existing as Promise<T>
  const pending = load().catch(error => { memory.delete(key); throw error })
  memory.set(key, pending)
  return pending
}

async function fetchManifest(fresh = false): Promise<Manifest> {
  const cached = read<Manifest>(manifestKey)
  if (!fresh && cached && Date.now() - cached.at < manifestMaxAge) return cached.value
  try {
    let manifest: Manifest
    try {
      manifest = await fetchJson<Manifest>(dataPath, undefined, true)
    } catch (error) {
      if (!(error instanceof HttpError) || error.status !== 404 || dataPath !== 'manifest.json') throw error
      manifest = await fetchJson<Manifest>('data/manifest.json', undefined, true)
    }
    if (![1, 2].includes(manifest.schema_version)) throw new Error('Versión de datos incompatible.')
    write(manifestKey, manifest)
    prune(manifest.dataset_version)
    return manifest
  } catch (error) {
    if (!fresh && cached) return cached.value
    throw error
  }
}

export function loadManifest(): Promise<Manifest> {
  return once(manifestKey, fetchManifest)
}

async function loadDocument<T extends { dataset_version?: string }>(reference: (manifest: Manifest) => FileReference): Promise<T> {
  for (let attempt = 0; attempt < 3; attempt++) {
    const manifest = await loadManifest()
    const file = reference(manifest)
    const key = `${prefix}${manifest.dataset_version}:${file.path}`
    try {
      return await once(key, async () => {
        const cached = read<T>(key)
        if (cached) return cached.value
        const value = await fetchJson<T>(file.path, file.sha256, true)
        if (manifest.schema_version === 2 && value.dataset_version !== manifest.dataset_version) throw new Error('Versión de datos incompatible.')
        write(key, value)
        return value
      })
    } catch (error) {
      if (attempt === 2) throw error
      const fresh = await fetchManifest(true)
      memory.set(manifestKey, Promise.resolve(fresh))
    }
  }
  throw new Error('No se pudieron cargar los datos.')
}

export async function loadSnapshot(): Promise<Snapshot> {
  const document = await loadDocument<Snapshot | FullSnapshot>(availableReference)
  return cleanSnapshot({ ...document, auctions: document.auctions.map(item => 'list_data' in item ? summaryFromAuction(item) : item) })
}

export async function loadDetail(idOrPath: string): Promise<AuctionDetail> {
  const manifest = await loadManifest()
  if (manifest.schema_version === 1) return cleanDetail(await fetchJson<AuctionDetail>(idOrPath))
  const snapshot = await loadSnapshot()
  const available = snapshot.auctions.find(item => item.auction_id === idOrPath)
  if (available?.detail) return available.detail
  const history = await loadDocument<History>(manifest => {
    if (!manifest.history) throw new Error('Publicación sin historial.')
    return manifest.history
  })
  const record = history.records[idOrPath]
  if (!record) throw new Error('Remate no disponible.')
  return historyDetail(record.document)
}
