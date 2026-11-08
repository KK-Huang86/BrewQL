const formatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })

/** Thousands separator and at most 2 decimals: 12345 → "12,345", 4.256 → "4.26" (design D5). */
export function formatNumber(value: number): string {
  return formatter.format(value)
}
