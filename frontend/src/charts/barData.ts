import type { BarChartSpec } from '../api/ask'

export type BarPoint = Record<string, unknown>

/** Rows as Recharts bars, in the query's order (design D4); [] when a named column is missing. */
export function toBarData(columns: string[], rows: unknown[][], chart: BarChartSpec): BarPoint[] {
  const xIndex = columns.indexOf(chart.x_key)
  const yIndex = columns.indexOf(chart.y_key)
  if (xIndex < 0 || yIndex < 0) return []
  return rows.map((row) => ({ [chart.x_key]: row[xIndex], [chart.y_key]: row[yIndex] ?? null }))
}
