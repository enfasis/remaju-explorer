export function resultView(value: string): 'table' | 'map' {
  return value === 'map' ? 'map' : 'table'
}

export default function ViewSelector({ value, onChange }: { value: 'table' | 'map'; onChange: (value: 'table' | 'map') => void }) {
  return <div className="view-selector" role="group" aria-label="Vista de resultados">
    {(['table', 'map'] as const).map(view => <button key={view} type="button" aria-pressed={value === view} aria-controls="auction-list" onClick={() => onChange(view)}>{view === 'table' ? 'Tabla' : 'Mapa'}</button>)}
  </div>
}
