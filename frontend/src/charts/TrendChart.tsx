import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatTooltipValue } from './format'
import type { LinePoint } from './lineData'

type Props = { data: LinePoint[]; xKey: string; yKey: string }

/** One series over time. The label names both columns so screen readers know what is plotted. */
export function TrendChart({ data, xKey, yKey }: Props) {
  return (
    <figure role="img" aria-label={`折線圖：${yKey}（依 ${xKey}）`} className="chart">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip formatter={formatTooltipValue} />
          {/* connectNulls off: a missing value shows as a gap, not as a made-up line. */}
          <Line type="monotone" dataKey={yKey} stroke="#8a5a2b" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </figure>
  )
}
