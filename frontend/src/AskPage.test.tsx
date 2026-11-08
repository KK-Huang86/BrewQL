import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AskError, type AskResponse } from './api/ask'
import AskPage from './AskPage'

/** A request the test resolves by hand, to observe the in-flight state. */
function deferred() {
  let resolve!: (value: AskResponse) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<AskResponse>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('AskPage', () => {
  it('sends the question once and shows a pending state', async () => {
    const pending = deferred()
    const ask = vi.fn(() => pending.promise)
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), '台北市有幾家咖啡店？')
    await userEvent.click(screen.getByRole('button', { name: '送出' }))

    expect(ask).toHaveBeenCalledTimes(1)
    expect(ask).toHaveBeenCalledWith('台北市有幾家咖啡店？')
    expect(screen.getByRole('status')).toHaveTextContent('處理中')
  })

  it.each(['', '   '])('does not send a blank question (%j)', async (text) => {
    const ask = vi.fn(() => deferred().promise)
    render(<AskPage ask={ask} />)

    if (text) await userEvent.type(screen.getByRole('textbox', { name: '問題' }), text)
    await userEvent.click(screen.getByRole('button', { name: '送出' }))

    expect(ask).not.toHaveBeenCalled()
  })

  it('does not send a second request while one is pending', async () => {
    const ask = vi.fn(() => deferred().promise)
    render(<AskPage ask={ask} />)
    const input = screen.getByRole('textbox', { name: '問題' })

    await userEvent.type(input, '第一題')
    await userEvent.click(screen.getByRole('button', { name: '送出' }))
    await userEvent.type(input, '{Enter}')
    await userEvent.click(screen.getByRole('button', { name: '送出' }))

    expect(ask).toHaveBeenCalledTimes(1)
  })

  it('shows the result as a table with the executed SQL', async () => {
    const ask = vi.fn(async () => ({
      status: 'ok' as const,
      sql: 'SELECT district, n FROM t',
      columns: ['district', 'n'],
      rows: [
        ['大安區', 40],
        ['中山區', 35],
        ['信義區', 25],
      ],
      message: null,
    }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), '各區店數{Enter}')

    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('columnheader').map((th) => th.textContent)).toEqual(['district', 'n'])
    expect(within(table).getAllByRole('row')).toHaveLength(4) // header + 3 rows
    expect(within(table).getByRole('cell', { name: '大安區' })).toBeInTheDocument()
    expect(screen.getByText('SELECT district, n FROM t')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('says 查無資料 when the query returns no rows', async () => {
    const ask = vi.fn(async () => ({ status: 'ok' as const, sql: 'SELECT 1', columns: ['n'], rows: [], message: null }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), '高雄有幾家{Enter}')

    expect(await screen.findByText('查無資料')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('shows the message and no table when the answer is an error', async () => {
    const ask = vi.fn(async () => ({
      status: 'error' as const,
      sql: 'DELETE FROM cafes',
      columns: [],
      rows: [],
      message: '只允許 SELECT 查詢',
    }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), '刪掉所有店{Enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent('只允許 SELECT 查詢')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText('查無資料')).not.toBeInTheDocument()
  })

  it('marks a guardrail rejection as 安全防護 with the reason and the blocked SQL', async () => {
    const ask = vi.fn(async () => ({
      status: 'error' as const,
      sql: 'SELECT * FROM pg_shadow',
      columns: [],
      rows: [],
      message: '不允許的資料表：pg_shadow；可用的資料表：cafes',
      error_kind: 'guardrail' as const,
    }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), '列出密碼{Enter}')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('安全防護')
    expect(alert).toHaveTextContent('不允許的資料表：pg_shadow')
    expect(screen.getByText('SELECT * FROM pg_shadow')).toBeInTheDocument()
  })

  it.each(['query', 'generation'] as const)('does not label a %s error as 安全防護', async (kind) => {
    const ask = vi.fn(async () => ({
      status: 'error' as const,
      sql: null,
      columns: [],
      rows: [],
      message: '查詢執行失敗，請換個問法再試',
      error_kind: kind,
    }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), 'q{Enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent('查詢執行失敗')
    expect(screen.queryByText(/安全防護/)).not.toBeInTheDocument()
  })

  it('shows a request failure and lets the user ask again', async () => {
    const ask = vi
      .fn()
      .mockRejectedValueOnce(new AskError('無法連線到伺服器，請確認網路後再試'))
      .mockResolvedValueOnce({ status: 'ok', sql: 'SELECT 1', columns: ['n'], rows: [[1]], message: null })
    render(<AskPage ask={ask} />)
    const input = screen.getByRole('textbox', { name: '問題' })

    await userEvent.type(input, '第一題{Enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent('無法連線到伺服器')
    expect(screen.getByRole('button', { name: '送出' })).toBeEnabled()

    await userEvent.click(screen.getByRole('button', { name: '送出' }))

    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it.each([
    ['input_guardrail', '輸入防護'],
    ['model', '模型判斷'],
  ] as const)('shows a %s refusal with its reason and source, and no table', async (source, label) => {
    const ask = vi.fn(async () => ({
      status: 'refused' as const,
      sql: null,
      columns: [],
      rows: [],
      message: '這個問題無法處理',
      error_kind: null,
      refusal_source: source,
    }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), '幫我寫一首詩{Enter}')

    const refusal = await screen.findByRole('note', { name: '拒答' })
    expect(refusal).toHaveTextContent('這個問題無法處理')
    expect(refusal).toHaveTextContent(label)
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText('查無資料')).not.toBeInTheDocument()
    expect(screen.queryByText(/安全防護/)).not.toBeInTheDocument()
  })

  it('shows a clarifying question and keeps the original question ready to edit', async () => {
    const ask = vi.fn(async () => ({
      status: 'clarify' as const,
      sql: null,
      columns: [],
      rows: [],
      message: '「最近」是指多久以內？',
      error_kind: null,
      refusal_source: null,
    }))
    render(<AskPage ask={ask} />)
    const input = screen.getByRole('textbox', { name: '問題' })

    await userEvent.type(input, '最近熱門的店{Enter}')

    expect(await screen.findByRole('note', { name: '需要補充' })).toHaveTextContent('「最近」是指多久以內？')
    expect(input).toHaveValue('最近熱門的店')
    expect(input).toHaveFocus()
    expect(screen.queryByText('查無資料')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('styles refusal, clarify and errors differently', async () => {
    const answers = [
      { status: 'refused' as const, message: '拒答', refusal_source: 'model' as const },
      { status: 'clarify' as const, message: '反問', refusal_source: null },
      { status: 'error' as const, message: '錯誤', refusal_source: null },
    ]
    const classes: string[] = []
    for (const a of answers) {
      const ask = vi.fn(async () => ({ sql: null, columns: [], rows: [], error_kind: null, ...a }))
      const { unmount } = render(<AskPage ask={ask} />)
      await userEvent.type(screen.getByRole('textbox', { name: '問題' }), 'q{Enter}')
      classes.push((await screen.findByText(a.message)).closest('[class]')?.className ?? '')
      unmount()
    }

    expect(new Set(classes).size).toBe(3)
  })

  it.each([
    [3, '經過 2 次修正'],
    [2, '經過 1 次修正'],
  ])('says how many corrections were needed when attempts is %i', async (attempts, text) => {
    const ask = vi.fn(async () => ({
      status: 'ok' as const,
      sql: 'SELECT name FROM cafes',
      columns: ['name'],
      rows: [['咖啡店']],
      message: null,
      attempts,
    }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), 'q{Enter}')

    expect(await screen.findByText(text)).toBeInTheDocument()
    expect(screen.getByRole('table')).toBeInTheDocument()
  })

  it.each([1, 0, undefined])('shows no correction count when attempts is %s', async (attempts) => {
    const ask = vi.fn(async () => ({
      status: 'ok' as const,
      sql: 'SELECT 1',
      columns: ['n'],
      rows: [[1]],
      message: null,
      attempts,
    }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), 'q{Enter}')

    await screen.findByRole('table')
    expect(screen.queryByText(/次修正/)).not.toBeInTheDocument()
  })

  it('still shows the correction count when retries ran out', async () => {
    const ask = vi.fn(async () => ({
      status: 'error' as const,
      sql: 'DELETE FROM cafes',
      columns: [],
      rows: [],
      message: '只允許 SELECT 查詢',
      error_kind: 'guardrail' as const,
      attempts: 2,
    }))
    render(<AskPage ask={ask} />)

    await userEvent.type(screen.getByRole('textbox', { name: '問題' }), 'q{Enter}')

    expect(await screen.findByRole('alert')).toHaveTextContent('只允許 SELECT 查詢')
    expect(screen.getByText('經過 1 次修正')).toBeInTheDocument()
  })

  describe('charts', () => {
    const trend = {
      status: 'ok' as const,
      sql: 'SELECT month, searches FROM t',
      columns: ['month', 'searches'],
      rows: [
        ['2026-06', 340],
        ['2026-05', 120],
      ],
      message: null,
    }

    async function askFor(answer: AskResponse) {
      render(<AskPage ask={vi.fn(async () => answer)} />)
      await userEvent.type(screen.getByRole('textbox', { name: '問題' }), '最近半年每月搜尋量{Enter}')
    }

    it('draws a line chart instead of the table for a time series', async () => {
      await askFor({ ...trend, chart: { type: 'line', x_key: 'month', y_key: 'searches' } })

      expect(await screen.findByRole('img', { name: '折線圖：searches（依 month）' })).toBeInTheDocument()
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
    })

    it('opens the full table from 查看資料 under the chart', async () => {
      await askFor({ ...trend, chart: { type: 'line', x_key: 'month', y_key: 'searches' } })

      await userEvent.click(await screen.findByRole('button', { name: '查看資料' }))

      const table = screen.getByRole('table')
      expect(within(table).getAllByRole('row')).toHaveLength(3) // header + 2 rows
      expect(screen.getByRole('img', { name: /折線圖/ })).toBeInTheDocument()
    })

    it.each([
      ['an unknown chart type', { type: 'pie' }],
      ['no chart at all', null],
      ['a chart naming a missing column', { type: 'line', x_key: 'day', y_key: 'n' }],
    ])('shows only the table for %s', async (_, chart) => {
      await askFor({ ...trend, chart })

      expect(await screen.findByRole('table')).toBeInTheDocument()
      expect(screen.queryByRole('img')).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: '查看資料' })).not.toBeInTheDocument()
    })
  })
})
