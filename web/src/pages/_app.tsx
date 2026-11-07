import { Outlet, Link } from 'react-router'
import { NuqsAdapter } from 'nuqs/adapters/react-router/v7'

export default function App() {
  return <NuqsAdapter>
    <a className="skip" href="#content">Ir al contenido</a>
    <header className="header"><div className="wrap header-inner"><Link className="brand" to="/"><img src="/logo.png" alt="" />RemaJu <span>Explorer</span></Link><nav aria-label="Navegación"><Link to="/downloads">Descargar datos</Link><a href="/data-access.md">Para agentes</a></nav></div></header>
    <main id="content" className="wrap"><Outlet /></main>
    <footer className="wrap footer">Una herramienta independiente. Consulta siempre las condiciones en REMAJU.</footer>
  </NuqsAdapter>
}
