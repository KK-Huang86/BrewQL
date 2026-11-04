import { afterEach, describe, expect, it, vi } from 'vitest'
import { AskError, askQuestion } from './ask'

function mockFetch(impl: () => Promise<Response>) {
  const fn = vi.fn(impl)
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('askQuestion', () => {
  it('posts the question and returns the parsed answer', async () => {
    const answer = { status: 'ok', sql: 'SELECT 1', columns: ['n'], rows: [[1]], message: null }
    const fetch = mockFetch(async () => Response.json(answer))

    await expect(askQuestion('台北市有幾家咖啡店？')).resolves.toEqual(answer)

    expect(fetch).toHaveBeenCalledWith('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: '台北市有幾家咖啡店？' }),
    })
  })

  it.each([422, 500, 502])('turns HTTP %i into an AskError', async (status) => {
    mockFetch(async () => Response.json({ detail: 'x' }, { status }))

    await expect(askQuestion('q')).rejects.toThrow(AskError)
  })

  it('uses the server message when the error body has one', async () => {
    mockFetch(async () => Response.json({ status: 'error', message: '模型服務暫時無法使用，請稍後再試' }, { status: 502 }))

    await expect(askQuestion('q')).rejects.toThrow('模型服務暫時無法使用，請稍後再試')
  })

  it('turns a network failure into an error with a readable message', async () => {
    mockFetch(async () => {
      throw new TypeError('Failed to fetch')
    })

    await expect(askQuestion('q')).rejects.toThrow('無法連線到伺服器')
  })
})
