import { useState } from 'react'
import type { AskResponse } from './api/ask'

type Props = { ask: (question: string) => Promise<AskResponse> }

export default function AskPage({ ask }: Props) {
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)
  const [answer, setAnswer] = useState<AskResponse | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = question.trim()
    // Enter still submits while the button is disabled, so guard here too.
    if (!trimmed || pending) return
    setPending(true)
    setAnswer(null)
    try {
      setAnswer(await ask(trimmed))
    } finally {
      setPending(false)
    }
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
      {answer && <Answer answer={answer} />}
    </main>
  )
}

function Answer({ answer }: { answer: AskResponse }) {
  return (
    <section>
      {answer.sql && <pre>{answer.sql}</pre>}
      <table>
        <thead>
          <tr>
            {answer.columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {answer.rows.map((row, i) => (
            <tr key={i}>
              {row.map((value, j) => (
                <td key={j}>{String(value ?? '')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
