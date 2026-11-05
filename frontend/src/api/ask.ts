export type AskResponse = {
  status: 'ok' | 'error'
  sql: string | null
  columns: string[]
  rows: unknown[][]
  message: string | null
}

/** A failed request; `message` is safe to show the user. */
export class AskError extends Error {}

export async function askQuestion(question: string): Promise<AskResponse> {
  let response: Response
  try {
    response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
  } catch {
    throw new AskError('無法連線到伺服器，請確認網路後再試')
  }

  if (!response.ok) {
    // The backend sends {message} on 5xx; 422 carries FastAPI's {detail}.
    const body = await response.json().catch(() => null)
    const message = typeof body?.message === 'string' ? body.message : `請求失敗（HTTP ${response.status}）`
    throw new AskError(message)
  }
  return response.json()
}
