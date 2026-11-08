import { displayMoney, otherCurrency, type Money, type Rate } from '../data'

export function Prices({ money, currency, rate, className = 'prices' }: { money: Money; currency: string; rate: Rate | null; className?: string }) {
  const primary = displayMoney(money, currency, rate)
  const secondary = displayMoney(money, otherCurrency(currency), rate)
  return <p className={className}>
    <strong>{primary}</strong>
    {primary !== money?.raw && secondary !== primary && secondary !== money?.raw && <span>{secondary}</span>}
  </p>
}
