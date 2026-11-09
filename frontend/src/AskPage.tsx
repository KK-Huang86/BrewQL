import { useRef, useState } from 'react'
import { AskError, type AskResponse, isBarChart, isLineChart, isNumberChart } from './api/ask'
import { CategoryChart } from './charts/CategoryChart'
import { NumberCard } from './charts/NumberCard'
import { TrendChart } from './charts/TrendChart'
import { toBarData } from './charts/barData'
import { toLineData } from './charts/lineData'

type Props = { ask: (question: string) => Promise<AskResponse> }

export default function AskPage({ ask }: Props) {
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)
  const [answer, setAnswer] = useState<AskResponse | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = question.trim()
    // Enter still submits while the button is disabled, so guard here too.
    if (!trimmed || pending) return
    setPending(true)
    setAnswer(null)
    setFailure(null)
    try {
      const result = await ask(trimmed)
      setAnswer(result)
      // The question stays in the box; focus it so the user can add what was asked for.
      if (result.status === 'clarify') inputRef.current?.focus()
    } catch (error) {
      setFailure(error instanceof AskError ? error.message : '發生未預期的錯誤，請稍後再試')
    } finally {
      setPending(false)
    }
  }

  return (
    <main>
      <form onSubmit={handleSubmit}>
        <label>
          問題
          <input ref={inputRef} value={question} onChange={(e) => setQuestion(e.target.value)} />
        </label>
        <button type="submit" disabled={pending}>
          送出
        </button>
      </form>
      {pending && <p role="status">處理中…</p>}
      {failure && <p role="alert">{failure}</p>}
      {answer && <Answer answer={answer} />}
    </main>
  )
}

function Answer({ answer }: { answer: AskResponse }) {
  const corrections = (answer.attempts ?? 1) - 1
  return (
    <section>
      {answer.sql && <pre>{answer.sql}</pre>}
      {/* A corrected answer was not the model's first guess: worth a second look at the SQL. */}
      {corrections > 0 && <p className="corrections">經過 {corrections} 次修正</p>}
      {answer.status === 'refused' ? (
        // A decision, not a failure: say who refused so users know whether rewording helps.
        <div role="note" aria-label="拒答" className="refused">
          <strong>拒答・{answer.refusal_source === 'input_guardrail' ? '輸入防護' : '模型判斷'}</strong>
          <p>{answer.message}</p>
        </div>
      ) : answer.status === 'clarify' ? (
        <div role="note" aria-label="需要補充" className="clarify">
          <strong>需要補充</strong>
          <p>{answer.message}</p>
        </div>
      ) : answer.status === 'error' && answer.error_kind === 'guardrail' ? (
        // Blocked on purpose, not broken: a distinct look so users don't just retry.
        <div role="alert" className="guardrail">
          <strong>安全防護</strong>
          <p>{answer.message}</p>
        </div>
      ) : answer.status === 'error' ? (
        <p role="alert" className="error">
          {answer.message}
        </p>
      ) : answer.rows.length === 0 ? (
        <p>查無資料</p>
      ) : (
        <Result answer={answer} />
      )}
    </section>
  )
}

function Result({ answer }: { answer: AskResponse }) {
  const [showData, setShowData] = useState(false)
  const chart = answer.chart
  // Anything the page cannot draw (unknown type, missing column, non-number) falls back to the table.
  if (isNumberChart(chart)) {
    const value = answer.rows[0]?.[answer.columns.indexOf(chart.value_key)]
    if (typeof value !== 'number') return <ResultTable answer={answer} />
    return <NumberCard label={chart.value_key} value={value} />
  }
  let drawing: React.ReactNode = null
  if (isLineChart(chart)) {
    const points = toLineData(answer.columns, answer.rows, chart)
    if (points.length > 0) drawing = <TrendChart data={points} xKey={chart.x_key} yKey={chart.y_key} />
  } else if (isBarChart(chart)) {
    const bars = toBarData(answer.columns, answer.rows, chart)
    if (bars.length > 0) drawing = <CategoryChart data={bars} xKey={chart.x_key} yKey={chart.y_key} />
  }
  if (!drawing) return <ResultTable answer={answer} />
  return (
    <>
      {drawing}
      <button type="button" aria-expanded={showData} onClick={() => setShowData((v) => !v)}>
        查看資料
      </button>
      {showData && <ResultTable answer={answer} />}
    </>
  )
}

function ResultTable({ answer }: { answer: AskResponse }) {
  return (
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
  )
}
