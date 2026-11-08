const formatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

/** Thousands separator and at most 2 decimals: 12345 → "12,345", 4.256 → "4.26" (design D5). */
export function formatNumber(value: number): string {
  return formatter.format(value)
}

/** Tooltip text: numbers formatted like the number card, anything else as is, missing as empty. */
export function formatTooltipValue(value: unknown): string {
  if (typeof value === 'number') return formatNumber(value)
  return value == null ? '' : String(value)
}
