import { Outlet, Link } from 'react-router'
import { NuqsAdapter } from 'nuqs/adapters/react-router/v7'
import { siteUrl } from '../data'
import { useEffect, useState } from 'react'
import Glossary from '../components/glossary'

export default function App() {
  const [dark, setDark] = useState(() => localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches))
  useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('theme', dark ? 'dark' : 'light') }, [dark])
  return <NuqsAdapter>
    <a className="skip" href="#content">Ir al contenido</a>
    <div className="glossary-control"><Glossary /></div>
    <header className="header"><div className="wrap header-inner"><Link className="brand" to="/">remaju^mm</Link><div className="header-actions"><button className="icon-button" type="button" aria-label={dark ? 'Activar modo claro' : 'Activar modo oscuro'} onClick={() => setDark(!dark)}>{dark ? '☀' : '☾'}</button><a className="icon-button" href="https://github.com/enfasis/remaju-explorer" aria-label="Ver código en GitHub"><svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M12 .8a11.2 11.2 0 0 0-3.54 21.83c.56.1.76-.24.76-.54v-2.1c-3.11.67-3.77-1.32-3.77-1.32-.51-1.3-1.25-1.65-1.25-1.65-1.02-.7.08-.69.08-.69 1.13.08 1.73 1.16 1.73 1.16 1 1.72 2.63 1.22 3.27.93.1-.73.39-1.22.7-1.5-2.49-.28-5.11-1.24-5.11-5.54 0-1.23.44-2.23 1.15-3.02-.11-.28-.5-1.42.11-2.97 0 0 .94-.3 3.08 1.15a10.7 10.7 0 0 1 5.6 0c2.14-1.45 3.07-1.15 3.07-1.15.61 1.55.23 2.69.12 2.97.71.79 1.14 1.79 1.14 3.02 0 4.31-2.62 5.25-5.12 5.53.4.35.76 1.03.76 2.08v3.09c0 .3.2.65.77.54A11.2 11.2 0 0 0 12 .8Z" /></svg></a></div></div></header>
    <main id="content" className="wrap"><Outlet /></main>
    <footer className="wrap footer"><p>© {new Date().getFullYear()} remaju^mm · Herramienta independiente, no afiliada al Poder Judicial.</p><p>Consulta las condiciones y la información oficial en <a href="https://remaju.pj.gob.pe/remaju/">REMAJU</a>. Los datos no constituyen asesoría legal.</p><p><Link to="/downloads">Datos y descargas</Link> · <a href={siteUrl('data-access.md')}>Información para agentes</a></p></footer>
  </NuqsAdapter>
}
