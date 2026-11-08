import { Link } from 'react-router'
import { activePhase, formatDeadline, place, titleCase, type Rate, type Summary } from '../data'
import { AuctionStatus } from './auction-status'
import { Prices } from './prices'
import IconButton from './icon-button'
import { PinIcon } from './icons'

export const tableColumns = [
  { key: 'number', label: 'Remate' },
  { key: 'department', label: 'Ubicación' },
  { key: 'type', label: 'Inmueble' },
  { key: 'price', label: 'Precio base' },
  { key: 'phase', label: 'Fase' },
  { key: 'date', label: 'Fecha de ofertas' },
  { key: 'status', label: 'Estado en listado' },
] as const

type Props = { auctions: Summary[]; currency: string; rate: Rate | null; search: string; sort: string; onSort: (sort: string) => void; onLocate: (auction: Summary) => void }

export default function AuctionTable({ auctions, currency, rate, search, sort, onSort, onLocate }: Props) {
  return <div className="table-scroll glass" role="region" aria-label="Tabla de remates" tabIndex={0}>
    <table id="auction-list" className="auction-table">
      <caption className="sr-only">{auctions.length} remates. Pulsa un encabezado para ordenar la columna.</caption>
      <thead><tr>{tableColumns.map(column => {
        const ascending = sort === `${column.key}-asc`
        const descending = sort === `${column.key}-desc`
        return <th key={column.key} scope="col" aria-sort={ascending ? 'ascending' : descending ? 'descending' : 'none'}>
          <button type="button" onClick={() => onSort(`${column.key}-${ascending ? 'desc' : 'asc'}`)} aria-label={`Ordenar por ${column.label.toLocaleLowerCase('es')}, ${ascending ? 'descendente' : 'ascendente'}`}>
            {column.label}<span aria-hidden="true">{ascending ? '↑' : descending ? '↓' : '↕'}</span>
          </button>
        </th>
      })}<th scope="col"><span className="sr-only">Mapa</span></th></tr></thead>
      <tbody>{auctions.map(auction => {
        const phase = activePhase(auction)
        const date = auction.offer_date ?? auction.offer_at?.slice(0, 10)
        return <tr key={auction.auction_id}>
          <th scope="row"><Link className="table-auction-link" to={`/auctions/${encodeURIComponent(auction.auction_id)}${search}`} state={{ fromList: true }}><span className="record-prefix">N.º</span> {auction.numero_remate}<span className="record-open">Ver ficha <span aria-hidden="true">↗</span></span></Link></th>
          <td className="table-location"><strong>{titleCase(auction.departamento) || 'Ubicación no publicada'}</strong><span>{place({ provincia: auction.provincia, distrito: auction.distrito })}</span></td>
          <td className="table-kind">{titleCase(auction.tipo_inmueble) || '—'}</td>
          <td className="table-price"><Prices money={auction.precio_base} currency={currency} rate={rate} className="prices compact" /></td>
          <td className="table-phase">{phase.fase || '—'}</td>
          <td className="table-date">{date ? <time dateTime={date}>{formatDeadline(`${date}T12:00:00`).date}</time> : <span className="muted">Sin fecha de ofertas</span>}{phase.until && <span className="phase-deadline">Fin de fase: <time dateTime={phase.until}>{formatDeadline(phase.until).date}</time></span>}</td>
          <td><AuctionStatus value={auction.estado} /></td>
          <td>{Boolean(auction.coordinates?.length) && <IconButton label={`Ver remate ${auction.numero_remate} en el mapa`} icon={<PinIcon />} controls="auction-map" onPress={() => onLocate(auction)} />}</td>
        </tr>
      })}</tbody>
    </table>
  </div>
}
