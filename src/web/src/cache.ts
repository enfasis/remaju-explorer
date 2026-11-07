import { dataPath, fetchJson, type AuctionDetail, type Manifest, type Snapshot } from './data'

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

async function fetchManifest(): Promise<Manifest> {
  const cached = read<Manifest>(manifestKey)
  if (cached && Date.now() - cached.at < manifestMaxAge) return cached.value
  try {
    const manifest = await fetchJson<Manifest>(dataPath)
    if (manifest.schema_version !== 1) throw new Error('Versión de datos incompatible.')
    write(manifestKey, manifest)
    prune(manifest.dataset_version)
    return manifest
  } catch (error) {
    if (cached) return cached.value
    throw error
  }
}

export function loadManifest(): Promise<Manifest> {
  return once(manifestKey, fetchManifest)
}

async function loadRelease<T>(path: string): Promise<T> {
  const manifest = await loadManifest()
  const key = `${prefix}${manifest.dataset_version}:${path}`
  return once(key, async () => {
    const cached = read<T>(key)
    if (cached) return cached.value
    const value = await fetchJson<T>(path)
    write(key, value)
    return value
  })
}

export async function loadSnapshot(): Promise<Snapshot> {
  const manifest = await loadManifest()
  return loadRelease<Snapshot>(manifest.availability.path)
}

export function loadDetail(path: string): Promise<AuctionDetail> {
  return loadRelease<AuctionDetail>(path)
}
