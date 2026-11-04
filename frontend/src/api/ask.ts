export type AskResponse = {
  status: 'ok' | 'error'
  sql: string | null
  columns: string[]
  rows: unknown[][]
  message: string | null
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  return response.json()
}
