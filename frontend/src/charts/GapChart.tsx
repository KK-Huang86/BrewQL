import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatTooltipValue } from './format'
import type { BarPoint } from './barData'

type Props = { data: BarPoint[]; xKey: string; yKey: string }

/** One value per category, e.g. searches or zero-result rate by district. */
export function GapChart({ data, xKey, yKey }: Props) {
  return (
    <figure role="img" aria-label={`長條圖：${yKey}（依 ${xKey}）`} className="chart">
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          {/* interval 0: show every category name, the comparison is the point. */}
          <XAxis dataKey={xKey} interval={0} />
          <YAxis />
          <Tooltip formatter={formatTooltipValue} />
          <Bar dataKey={yKey} fill="#8a5a2b" />
        </BarChart>
      </ResponsiveContainer>
    </figure>
  )
}
