import type { LineChartSpec } from '../api/ask'

export type LinePoint = Record<string, unknown>

/** Rows as Recharts points (one object per row, keyed by column), oldest first. */
export function toLineData(columns: string[], rows: unknown[][], chart: LineChartSpec): LinePoint[] {
  const xIndex = columns.indexOf(chart.x_key)
  const yIndex = columns.indexOf(chart.y_key)
  if (xIndex < 0 || yIndex < 0) return []

  const points = rows.map((row) => ({ [chart.x_key]: row[xIndex], [chart.y_key]: row[yIndex] ?? null }))
  // The SQL may order newest first; a time axis always reads left to right.
  return points.sort((a, b) => compareTime(a[chart.x_key], b[chart.x_key]))
}

function compareTime(a: unknown, b: unknown): number {
  const ta = Date.parse(String(a))
  const tb = Date.parse(String(b))
  // ISO text the backend sends always parses; fall back to text order just in case.
  if (Number.isNaN(ta) || Number.isNaN(tb)) return String(a).localeCompare(String(b))
  return ta - tb
}
