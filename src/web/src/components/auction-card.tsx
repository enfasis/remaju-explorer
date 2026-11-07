import { Link } from 'react-router'
import { Card } from 'tamagui'
import { activePhase, displayMoney, otherCurrency, place, siteUrl, titleCase, type Money, type Rate, type Summary } from '../data'
import { AuctionBadges } from './badges'
import IconButton from './icon-button'
import { PinIcon } from './icons'

export function Prices({ money, currency, rate, className = 'prices' }: { money: Money; currency: string; rate: Rate | null; className?: string }) {
  const primary = displayMoney(money, currency, rate)
  const secondary = displayMoney(money, otherCurrency(currency), rate)
  return <p className={className}>
    <strong>{primary}</strong>
    {secondary !== primary && secondary !== money?.raw && <span>{secondary}</span>}
  </p>
}

type Props = { auction: Summary; currency: string; rate: Rate | null; search: string; onLocate?: () => void }

export default function AuctionCard({ auction, currency, rate, search, onLocate }: Props) {
  const location = place(auction) || 'Ubicación no disponible'
  const phase = activePhase(auction)
  return <>
    <Link className="item" to={`/auctions/${encodeURIComponent(auction.auction_id)}${search}`} state={{ fromList: true }}>
      <Card size="md" className="card glass" render="article" rounded={16}>
        {auction.thumbnail_path && <img className="thumbnail" src={siteUrl(auction.thumbnail_path)} alt="" loading="lazy" />}
        <div className="card-top">
          <p className="eyebrow"><span className="sr-only">Remate </span>N.º {auction.numero_remate}</p>
          {auction.tipo_inmueble && <span className="badge badge-yellow"><span className="sr-only">Tipo de inmueble: </span>{titleCase(auction.tipo_inmueble)}</span>}
        </div>
        <h3 className="card-location">{location}</h3>
        <Prices money={auction.precio_base} currency={currency} rate={rate} />
        <AuctionBadges phase={phase.fase} until={phase.until} status={auction.estado} />
      </Card>
    </Link>
    {onLocate && <div className="card-locate"><IconButton label={`Ver remate ${auction.numero_remate} en el mapa`} icon={<PinIcon />} controls="auction-map" onPress={onLocate} /></div>}
  </>
}
