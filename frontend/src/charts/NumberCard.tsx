import { formatNumber } from './format'

type Props = { label: string; value: number }

/** A single answer such as a count or an average, shown large with its column name. */
export function NumberCard({ label, value }: Props) {
  return (
    <figure aria-label={label} className="number-card">
      <strong>{formatNumber(value)}</strong>
      <figcaption>{label}</figcaption>
    </figure>
  )
}
