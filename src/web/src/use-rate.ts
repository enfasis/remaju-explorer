import { useEffect, useState } from 'react'
import type { Rate } from './data'

let request: Promise<Rate | null> | null = null

function fetchRate(): Promise<Rate | null> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 8000)
  return fetch('https://api.exchangerate-api.com/v4/latest/PEN', { signal: controller.signal }).then(async response => {
    if (!response.ok) return null
    const data = await response.json()
    const valid = data.base === 'PEN' && /^\d+(\.\d+)?$/.test(String(data.rates?.USD)) && Number(data.rates.USD) > 0 && /^\d{4}-\d{2}-\d{2}$/.test(data.date)
    return valid ? { penToUsd: String(data.rates.USD), date: data.date, source: 'ExchangeRate-API' } : null
  }).catch(() => null).finally(() => clearTimeout(timer))
}

export function useRate() {
  const [rate, setRate] = useState<Rate | null>(null)
  useEffect(() => {
    let active = true
    request ??= fetchRate()
    request.then(value => { if (active) setRate(value) })
    return () => { active = false }
  }, [])
  return rate
}

export function usdInPen(rate: Rate): string {
  return (1 / Number(rate.penToUsd)).toFixed(3)
}
