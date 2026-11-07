import { useRef } from 'react'

const terms = [
  ['Precio base', 'Monto mínimo para iniciar las ofertas. Puede corresponder a varios inmuebles.'],
  ['Tasación', 'Valor de referencia usado para valorar el bien. No garantiza su precio de mercado.'],
  ['Oblaje', 'Depósito exigido para participar. Revisa el monto y las condiciones en las bases.'],
  ['Arancel', 'Pago por el derecho a participar, distinto del oblaje.'],
  ['Convocatoria', 'Llamado del remate. Puede haber más de uno.'],
  ['Cargas y gravámenes', 'Hipotecas, embargos u otras afectaciones inscritas. Requieren revisión legal.'],
  ['Partida registral', 'Identificador del inmueble en los Registros Públicos.'],
  ['Cronograma', 'Plazos para inscripción, ofertas y pagos. Verifica siempre la hora en REMAJU.'],
  ['Tipo de cambio', 'Conversión referencial para comparar precios. La obligación conserva la moneda original.'],
]

export default function Glossary() {
  const dialog = useRef<HTMLDialogElement>(null)
  return <><button className="icon-button" type="button" aria-label="Abrir glosario" onClick={() => dialog.current?.showModal()}>?</button><dialog ref={dialog} aria-labelledby="glossary-title"><div className="section-heading"><h2 id="glossary-title">Guía rápida</h2><button className="icon-button" type="button" aria-label="Cerrar glosario" onClick={() => dialog.current?.close()}>×</button></div><dl>{terms.map(([term, description]) => <div key={term}><dt>{term}</dt><dd>{description}</dd></div>)}</dl><p className="muted">Guía orientativa para Perú. No reemplaza las bases del remate ni la asesoría legal.</p><a href="https://remaju.pj.gob.pe/doc/remaju_manual_postor.pdf" target="_blank" rel="noreferrer">Manual oficial para postores</a></dialog></>
}
