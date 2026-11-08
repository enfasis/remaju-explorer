import { Link } from 'react-router'
import { siteUrl } from '../data'

export default function Footer() {
  return <footer className="footer" role="contentinfo">
    <div className="wrap footer-inner">
      <div className="footer-brand">
        <Link className="brand" to="/" aria-label="remaju mm, ir al inicio">remaju<sup aria-hidden="true">mm</sup></Link>
        <p>Remates judiciales del Perú, más fáciles de explorar.</p>
      </div>
      <nav aria-label="Enlaces del sitio">
        <ul className="footer-links">
          <li><Link to="/downloads">Datos y descargas</Link></li>
          <li><a href={siteUrl('data-access.md')}>Para agentes</a></li>
          <li><a href="https://remaju.pj.gob.pe/remaju/" target="_blank" rel="noreferrer">REMAJU oficial<span className="sr-only"> (abre en otra pestaña)</span></a></li>
          <li><a href="https://github.com/enfasis/remaju-explorer" target="_blank" rel="noreferrer">GitHub<span className="sr-only"> (abre en otra pestaña)</span></a></li>
        </ul>
      </nav>
      <p className="footer-note">© {new Date().getFullYear()} · Herramienta independiente, no afiliada al Poder Judicial. Datos referenciales; no constituyen asesoría legal.</p>
    </div>
  </footer>
}
