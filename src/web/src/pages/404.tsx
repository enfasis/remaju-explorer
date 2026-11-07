import { Link } from 'react-router'
import { useTitle } from '../use-title'

export default function NotFound() {
  useTitle('Página no encontrada')
  return <section className="page glass"><h1>Página no encontrada</h1><Link to="/">Volver al inicio</Link></section>
}
