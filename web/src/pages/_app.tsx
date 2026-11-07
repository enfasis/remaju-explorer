import { Outlet, Link } from 'react-router'
import { NuqsAdapter } from 'nuqs/adapters/react-router/v7'
import { siteUrl } from '../data'

export default function App() {
  return <NuqsAdapter>
    <a className="skip" href="#content">Ir al contenido</a>
    <header className="header"><div className="wrap header-inner"><Link className="brand" to="/"><img src={siteUrl('logo.png')} alt="" />RemaJu <span>Explorer</span></Link><nav aria-label="Navegación"><Link to="/downloads">Datos</Link><a href={siteUrl('data-access.md')}>Para agentes</a></nav></div></header>
    <main id="content" className="wrap"><Outlet /></main>
    <footer className="wrap footer"><p>© {new Date().getFullYear()} RemaJu Explorer · Herramienta independiente, no afiliada al Poder Judicial.</p><p>Consulta las condiciones y la información oficial en <a href="https://remaju.pj.gob.pe/remaju/">REMAJU</a>. Los datos no constituyen asesoría legal.</p><p><Link to="/downloads">Datos y descargas</Link> · <a href={siteUrl('data-access.md')}>Información para agentes</a></p></footer>
  </NuqsAdapter>
}
