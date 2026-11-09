import { describe, expect, it } from 'vitest'
import { formatNumber, formatTooltipValue } from './format'

describe('formatNumber', () => {
  it.each([
    [12345, '12,345'],
    [4.256, '4.26'],
    [4.2, '4.2'],
    [0, '0'],
    [-1234.5, '-1,234.5'],
    [1000000, '1,000,000'],
    [0.005, '0.01'],
  ])('shows %s as %s (thousands separator, at most 2 decimals)', (value, text) => {
    expect(formatNumber(value)).toBe(text)
  })
})

describe('formatTooltipValue', () => {
  it.each([
    [0.5401909068073348, '0.54'],
    [8961, '8,961'],
    ['內湖區', '內湖區'],
    [null, ''],
    [undefined, ''],
  ])('shows %s as %s on chart tooltips', (value, text) => {
    expect(formatTooltipValue(value)).toBe(text)
  })
})
