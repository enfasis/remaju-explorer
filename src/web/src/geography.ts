import boundary from '../../shared/peru.json'

function inRing(x: number, y: number, ring: number[][]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [ax, ay] = ring[i]
    const [bx, by] = ring[j]
    const cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
    if (Math.abs(cross) < 1e-10 && x >= Math.min(ax, bx) && x <= Math.max(ax, bx) && y >= Math.min(ay, by) && y <= Math.max(ay, by)) return true
    if ((ay > y) !== (by > y) && x < (bx - ax) * (y - ay) / (by - ay) + ax) inside = !inside
  }
  return inside
}

export function inPeru(latitude: number | null | undefined, longitude: number | null | undefined): boolean {
  if (typeof latitude !== 'number' || typeof longitude !== 'number' || !Number.isFinite(latitude) || !Number.isFinite(longitude)) return false
  if (latitude < -19 || latitude > 1 || longitude < -82 || longitude > -68) return false
  return boundary.coordinates.some(polygon => inRing(longitude, latitude, polygon[0]) && !polygon.slice(1).some(hole => inRing(longitude, latitude, hole)))
}
