import { afterEach, describe, expect, it, vi } from 'vitest'
import { askQuestion } from './ask'

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
})
