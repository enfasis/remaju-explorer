export default function Spinner({ label = 'Cargando datos…' }: { label?: string }) {
  return <div className="loading" role="status"><span className="spinner" aria-hidden="true" /><span>{label}</span></div>
}
