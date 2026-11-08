import { describe, expect, it } from 'vitest'
import { toLineData } from './lineData'

const chart = { type: 'line' as const, x_key: 'month', y_key: 'searches' }

describe('toLineData', () => {
  it('turns rows into one object per point, keyed by column name', () => {
    expect(toLineData(['month', 'searches'], [['2026-05', 120], ['2026-06', 340]], chart)).toEqual([
      { month: '2026-05', searches: 120 },
      { month: '2026-06', searches: 340 },
    ])
  })

  it('orders points from oldest to newest whatever order the SQL used', () => {
    const rows = [['2026-07', 3], ['2026-05', 1], ['2026-06', 2]]

    expect(toLineData(['month', 'searches'], rows, chart).map((p) => p.month)).toEqual([
      '2026-05',
      '2026-06',
      '2026-07',
    ])
  })

  it('orders timestamps by time, not by text', () => {
    // 03:00+08:00 on the 2nd is 19:00Z on the 1st: earlier in time, later as text.
    const rows = [
      ['2026-05-01T20:00:00Z', 2],
      ['2026-05-02T03:00:00+08:00', 1],
    ]

    expect(toLineData(['day', 'n'], rows, { type: 'line', x_key: 'day', y_key: 'n' }).map((p) => p.n)).toEqual([
      1, 2,
    ])
  })

  it('follows the chart keys, not the column order', () => {
    const data = toLineData(['searches', 'month'], [[120, '2026-05']], chart)

    expect(data).toEqual([{ month: '2026-05', searches: 120 }])
  })

  it('keeps a missing value as null so the line shows a gap', () => {
    expect(toLineData(['month', 'searches'], [['2026-05', null]], chart)).toEqual([
      { month: '2026-05', searches: null },
    ])
  })

  it('gives no points when the chart names a column the result does not have', () => {
    expect(toLineData(['month', 'n'], [['2026-05', 1]], chart)).toEqual([])
  })

  it('leaves the rows it was given untouched', () => {
    const rows = [['2026-06', 2], ['2026-05', 1]]

    toLineData(['month', 'searches'], rows, chart)

    expect(rows).toEqual([['2026-06', 2], ['2026-05', 1]])
  })
})
