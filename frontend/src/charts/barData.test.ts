import { describe, expect, it } from 'vitest'
import { toBarData } from './barData'

const chart = { type: 'bar' as const, x_key: 'district', y_key: 'rate' }

describe('toBarData', () => {
  it('keeps the query order, since the SQL usually sorts by value already', () => {
    const rows = [
      ['內湖區', 0.54],
      ['新店區', 0.16],
      ['大安區', 0.05],
    ]

    expect(toBarData(['district', 'rate'], rows, chart).map((p) => p.district)).toEqual(['內湖區', '新店區', '大安區'])
  })

  it('keeps a NULL value as an empty bar', () => {
    expect(toBarData(['district', 'rate'], [['內湖區', null]], chart)).toEqual([{ district: '內湖區', rate: null }])
  })

  it('returns nothing when the chart names a missing column', () => {
    expect(toBarData(['city', 'rate'], [['台北市', 1]], chart)).toEqual([])
  })
})
