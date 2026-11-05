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
})
