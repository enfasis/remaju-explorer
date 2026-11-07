import { useState } from 'react'
import { Dialog } from 'tamagui'
import IconButton from './icon-button'
import { CloseIcon, HelpIcon } from './icons'

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
  const [open, setOpen] = useState(false)
  return <Dialog modal open={open} onOpenChange={setOpen}>
    <IconButton label="Abrir glosario" icon={<HelpIcon />} haspopup="dialog" onPress={() => setOpen(true)} />
    <Dialog.Portal>
      <Dialog.Overlay key="overlay" className="dialog-overlay" bg="rgba(28, 24, 20, 0.42)" opacity="1 enter:0 exit:0" transition="quick" />
      <Dialog.Content key="content" className="dialog-content" bg="transparent" borderWidth={0} p="0" boxShadow="none" opacity="1 enter:0 exit:0" y="0 enter:12px exit:8px" scale="1 enter:0.98 exit:0.98" transition="quick">
        <div className="dialog-panel">
          <div className="dialog-heading">
            <Dialog.Title className="dialog-title">Guía rápida</Dialog.Title>
            <IconButton label="Cerrar glosario" icon={<CloseIcon />} onPress={() => setOpen(false)} />
          </div>
          <Dialog.Description className="muted">Términos frecuentes en los remates judiciales del Perú. No reemplaza las bases del remate ni la asesoría legal.</Dialog.Description>
          <dl className="glossary">{terms.map(([term, description]) => <div key={term}><dt>{term}</dt><dd>{description}</dd></div>)}</dl>
          <a href="https://remaju.pj.gob.pe/doc/remaju_manual_postor.pdf" target="_blank" rel="noreferrer">Manual oficial para postores<span className="sr-only"> (abre en otra pestaña)</span></a>
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog>
}
