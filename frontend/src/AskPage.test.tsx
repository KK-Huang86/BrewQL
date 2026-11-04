import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { AskResponse } from './api/ask'
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
})
