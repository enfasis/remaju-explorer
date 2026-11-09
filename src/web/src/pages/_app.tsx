import { useEffect, useState } from 'react'
import { Outlet, ScrollRestoration } from 'react-router'
import { NuqsAdapter } from 'nuqs/adapters/react-router/v7'
import { TamaguiProvider } from 'tamagui'
import Footer from '../components/footer'
import Brand from '../components/brand'
import Glossary from '../components/glossary'
import IconButton from '../components/icon-button'
import { GitHubIcon, MoonIcon, SunIcon } from '../components/icons'
import { config } from '../theme'
import { usdInPen, useRate } from '../use-rate'

function initialDark(): boolean {
  const stored = localStorage.getItem('theme')
  return stored ? stored === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
}

function ExchangeRate() {
  const rate = useRate()
  if (!rate) return <span className="rate" aria-live="polite">Tipo de cambio no disponible</span>
  return <span className="rate" aria-live="polite" aria-label={`Tipo de cambio referencial: 1 dólar equivale a ${usdInPen(rate)} soles, ${rate.date}, fuente ${rate.source}`} title={`${rate.date} · ${rate.source}`}>1 USD = {usdInPen(rate)} PEN</span>
}

export default function App() {
  const [dark, setDark] = useState(initialDark)
  useEffect(() => {
    const positions = { x1: 10 + Math.random() * 30, y1: 10 + Math.random() * 30, x2: 60 + Math.random() * 30, y2: 60 + Math.random() * 30 }
    for (const [key, value] of Object.entries(positions)) document.documentElement.style.setProperty(`--pattern-${key}`, `${value}%`)
  }, [])
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])
  return <TamaguiProvider config={config} defaultTheme={dark ? 'dark' : 'light'}>
    <NuqsAdapter>
      <a className="skip" href="#content">Ir al contenido</a>
      <header className="header" role="banner">
        <nav className="wrap header-inner" aria-label="Principal">
          <ExchangeRate />
          <Brand />
          <div className="header-actions" role="toolbar" aria-label="Preferencias y enlaces">
            <IconButton label={dark ? 'Activar modo claro' : 'Activar modo oscuro'} icon={dark ? <SunIcon /> : <MoonIcon />} onPress={() => setDark(!dark)} />
            <Glossary />
            <IconButton label="Ver código en GitHub" icon={<GitHubIcon />} href="https://github.com/enfasis/remaju-explorer" />
          </div>
        </nav>
      </header>
      <main id="content" className="wrap"><Outlet /></main>
      <ScrollRestoration />
      <Footer />
    </NuqsAdapter>
  </TamaguiProvider>
}
