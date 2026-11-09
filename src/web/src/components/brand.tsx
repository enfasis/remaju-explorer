import { Link } from 'react-router'

export default function Brand() {
  return <Link className="brand" to="/" aria-label="remaju mm, ir al inicio"><span className="brand-word" aria-hidden="true">{[...'remaju'].map((letter, index) => <span key={index}>{letter}</span>)}</span><sup aria-hidden="true">mm</sup></Link>
}
