import { useEffect, useState } from 'react'
import type { Rate } from './data'

export function useRate() {
  const [rate, setRate] = useState<Rate | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), 8000)
    fetch('https://api.exchangerate-api.com/v4/latest/PEN', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('Tipo de cambio no disponible')
      const data = await response.json()
      if (data.base === 'PEN' && /^\d+(\.\d+)?$/.test(String(data.rates?.USD)) && Number(data.rates.USD) > 0 && /^\d{4}-\d{2}-\d{2}$/.test(data.date)) setRate({ penToUsd: String(data.rates.USD), date: data.date, source: 'ExchangeRate-API' })
    }).catch(() => {}).finally(() => clearTimeout(timer))
    return () => { clearTimeout(timer); controller.abort() }
  }, [])
  return rate
}
