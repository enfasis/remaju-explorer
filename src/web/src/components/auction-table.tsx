import { Link } from 'react-router'
import { activePhase, formatShortDate, titleCase, type Rate, type Summary } from '../data'
import { AuctionBadges } from './badges'
import { Prices } from './auction-card'
import IconButton from './icon-button'
import { PinIcon } from './icons'

export const tableColumns = [
  { key: 'number', label: 'Remate' },
  { key: 'department', label: 'Departamento' },
  { key: 'province', label: 'Provincia' },
  { key: 'district', label: 'Distrito' },
  { key: 'type', label: 'Inmueble' },
  { key: 'price', label: 'Precio base' },
  { key: 'phase', label: 'Fase' },
  { key: 'date', label: 'Fecha de ofertas' },
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
          <th scope="row"><Link className="table-auction-link" to={`/auctions/${encodeURIComponent(auction.auction_id)}${search}`} state={{ fromList: true }}>N.º {auction.numero_remate}</Link></th>
          <td>{titleCase(auction.departamento) || '—'}</td>
          <td>{titleCase(auction.provincia) || '—'}</td>
          <td>{titleCase(auction.distrito) || '—'}</td>
          <td>{titleCase(auction.tipo_inmueble) || '—'}</td>
          <td className="table-price"><Prices money={auction.precio_base} currency={currency} rate={rate} className="prices compact" /></td>
          <td><AuctionBadges phase={phase.fase} until={phase.until} status={auction.estado} /></td>
          <td>{date ? <time dateTime={date}>{formatShortDate(`${date}T12:00:00`)}</time> : '—'}</td>
          <td>{Boolean(auction.coordinates?.length) && <IconButton label={`Ver remate ${auction.numero_remate} en el mapa`} icon={<PinIcon />} controls="auction-map" onPress={() => onLocate(auction)} />}</td>
        </tr>
      })}</tbody>
    </table>
  </div>
}
