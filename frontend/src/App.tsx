import { askQuestion } from './api/ask'
import AskPage from './AskPage'

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>BrewQL</h1>
        <p>Find Coffee 營運數據助理：用中文提問，查看實際執行的 SQL 與結果</p>
      </header>
      <AskPage ask={askQuestion} />
    </div>
  )
}
