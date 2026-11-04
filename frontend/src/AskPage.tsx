import { useState } from 'react'
import type { AskResponse } from './api/ask'

type Props = { ask: (question: string) => Promise<AskResponse> }

export default function AskPage({ ask }: Props) {
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = question.trim()
    // Enter still submits while the button is disabled, so guard here too.
    if (!trimmed || pending) return
    setPending(true)
    await ask(trimmed)
  }

  return (
    <main>
      <form onSubmit={handleSubmit}>
        <label>
          問題
          <input value={question} onChange={(e) => setQuestion(e.target.value)} />
        </label>
        <button type="submit" disabled={pending}>
          送出
        </button>
      </form>
      {pending && <p role="status">處理中…</p>}
    </main>
  )
}
