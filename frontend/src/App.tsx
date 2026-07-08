import { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

const BACKEND = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

type Step = { step: string; content: string; meta?: Record<string, string | number> }
type Mode = 'analyze' | 'cuda_rocm' | 'compliance'

const MODE_LABELS: Record<Mode, string> = {
  analyze:    '🔍 Codebase Analysis',
  cuda_rocm:  '⚡ CUDA → ROCm Migration',
  compliance: '🔒 Compliance Scan',
}

const STEP_COLORS: Record<string, string> = {
  fetch:   '#7dd3c8',
  triage:  '#f0abfc',
  routing: '#a78bfa',
  plan:    '#60a5fa',
  call:    '#fbbf24',
  observe: '#94a3b8',
  think:   '#c4b5fd',
  answer:  '#4ade80',
  error:   '#f87171',
}

const STEP_LABELS: Record<string, string> = {
  fetch:   'FETCH',
  triage:  'GEMMA TRIAGE',
  routing: 'ROUTE',
  plan:    'PLAN',
  call:    'CALL',
  observe: 'OBSERVE',
  think:   'THINK',
  answer:  'ANSWER',
  error:   'ERROR',
}

export default function App() {
  const [urls, setUrls] = useState<string[]>([''])
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<Mode>('analyze')
  const [steps, setSteps] = useState<Step[]>([])
  const [running, setRunning] = useState(false)
  const [answer, setAnswer] = useState('')
  const [costInfo, setCostInfo] = useState<{cost: string; model: string; calls: number} | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const addUrl = () => setUrls(u => [...u, ''])
  const removeUrl = (i: number) => setUrls(u => u.filter((_, idx) => idx !== i))
  const setUrl = (i: number, v: string) => setUrls(u => u.map((x, idx) => idx === i ? v : x))

  const run = async () => {
    const validUrls = urls.filter(u => u.includes('github.com'))
    if (!validUrls.length) return
    if (mode === 'analyze' && !question.trim()) return

    setRunning(true)
    setSteps([])
    setAnswer('')
    setCostInfo(null)

    const controller = new AbortController()
    abortRef.current = controller
    const body = JSON.stringify({ repo_urls: validUrls, question: question || '...', mode })

    try {
      const resp = await fetch(`${BACKEND}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        signal: controller.signal,
      })

      const reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''  // holds a partial SSE frame that spans TCP chunks

      const handle = (raw: string) => {
        if (!raw) return
        const parsed = JSON.parse(raw) as Step
        if (parsed.step === 'answer') {
          setAnswer(parsed.content)
          setCostInfo({
            cost: (parsed.meta?.total_cost as string) || '$0',
            model: (parsed.meta?.model as string) || 'unknown',
            calls: (parsed.meta?.tool_calls as number) || 0,
          })
        }
        setSteps(prev => [...prev, parsed])
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        // SSE frames are separated by a blank line ("\n\n"); keep the trailing partial.
        const frames = buffer.split('\n\n')
        buffer = frames.pop() ?? ''
        for (const frame of frames) {
          const dataLine = frame.split('\n').find(l => l.startsWith('data:'))
          if (!dataLine) continue
          const raw = dataLine.replace(/^data:\s*/, '').trim()
          try { handle(raw) } catch {}
        }
      }
      // flush any final buffered frame
      const tail = buffer.split('\n').find(l => l.startsWith('data:'))
      if (tail) { try { handle(tail.replace(/^data:\s*/, '').trim()) } catch {} }
    } catch (e) {
      setSteps(prev => [...prev, { step: 'error', content: String(e) }])
    } finally {
      setRunning(false)
    }
  }

  const stop = () => {
    abortRef.current?.abort()
    setRunning(false)
  }

  return (
    <div style={s.page}>
      {/* Header */}
      <header style={s.header}>
        <div style={s.logoRow}>
          <h1 style={s.logo}>REPOMIND v3</h1>
          <span style={s.badge}>AMD MI300X · 256K Context</span>
        </div>
        <p style={s.tagline}>
          Apple banned Copilot. JP Morgan banned Cursor.
          <span style={{ color: '#14b8a6' }}> This is what they deploy instead.</span>
        </p>
      </header>

      {/* Mode selector */}
      <div style={s.modeRow}>
        {(Object.keys(MODE_LABELS) as Mode[]).map(m => (
          <button key={m} onClick={() => setMode(m)} style={{
            ...s.modeBtn,
            ...(mode === m ? s.modeBtnActive : {})
          }}>
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>

      {/* Repo URLs */}
      <section style={s.inputSection}>
        {urls.map((url, i) => (
          <div key={i} style={s.urlRow}>
            <input
              type="text"
              placeholder={`https://github.com/owner/repo${i > 0 ? ` (repo ${i + 1})` : ''}`}
              value={url}
              onChange={e => setUrl(i, e.target.value)}
              style={s.input}
              disabled={running}
            />
            {i > 0 && (
              <button onClick={() => removeUrl(i)} style={s.removeBtn}>✕</button>
            )}
          </div>
        ))}
        <button onClick={addUrl} style={s.addBtn} disabled={running}>
          + Add repo (multi-repo analysis)
        </button>
      </section>

      {/* Question (only for analyze mode) */}
      {mode === 'analyze' && (
        <textarea
          placeholder="Ask anything about the codebase... e.g. 'Find all auth vulnerabilities' or 'Explain the data pipeline'"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          style={s.textarea}
          disabled={running}
          rows={3}
        />
      )}

      {/* Action button */}
      <button
        onClick={running ? stop : run}
        disabled={!urls.some(u => u.includes('github.com')) || (mode === 'analyze' && !question.trim())}
        style={{ ...s.runBtn, ...(running ? s.runBtnStop : {}) }}
      >
        {running ? '⏹ Stop' : mode === 'analyze' ? '▶ Analyze' : mode === 'cuda_rocm' ? '⚡ Migrate to ROCm' : '🔒 Scan Compliance'}
      </button>

      {/* Live Agent Loop */}
      {steps.length > 0 && (
        <section style={s.agentPanel}>
          <div style={s.agentHeader}>
            SC-TIR Agent Loop
            {running && <span style={s.liveDot}>● LIVE</span>}
          </div>
          <div style={s.agentLog}>
            {steps.map((step, i) => (
              <div key={i} style={s.stepRow}>
                <span style={{ ...s.stepLabel, color: STEP_COLORS[step.step] || '#e8eaf0' }}>
                  [{STEP_LABELS[step.step] || step.step.toUpperCase()}]
                </span>
                {step.step === 'routing' && (
                  <div style={s.routingCard}>
                    <span style={{ color: STEP_COLORS.routing }}>{step.content}</span>
                    {step.meta && (
                      <div style={s.routingMeta}>
                        <span>Est. cost: {step.meta.est_cost}</span>
                        <span>Est. time: {step.meta.est_latency}</span>
                        <span>Tokens: {Number(step.meta.tokens).toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                )}
                {step.step !== 'routing' && step.step !== 'answer' && (
                  <span style={s.stepContent}>{step.content}</span>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </section>
      )}

      {/* Answer */}
      {answer && (
        <section style={s.answerPanel}>
          <div style={s.answerHeader}>
            <span style={{ color: '#4ade80' }}>◆ ANSWER</span>
            {costInfo && (
              <div style={s.costBadges}>
                <span style={s.costBadge}>{costInfo.model}</span>
                <span style={s.costBadge}>Total: {costInfo.cost}</span>
                <span style={s.costBadge}>{costInfo.calls} tool calls</span>
              </div>
            )}
          </div>
          <div style={s.answerContent}>
            <ReactMarkdown>{answer}</ReactMarkdown>
          </div>
        </section>
      )}

      <footer style={s.footer}>
        REPOMIND v3 · AMD MI300X 192GB HBM3 · Qwen3-Coder-Next-FP8 256K · Gemma 27B via Fireworks AI
        <br />
        ACT I Winner (1st Place AI Agents) · ACT II Build · MIT License · github.com/SRKRZ23/repomind-v3
      </footer>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: 'radial-gradient(ellipse at top, #0d1230 0%, #050810 60%)', color: '#e8eaf0', fontFamily: '"IBM Plex Mono","SF Mono",Menlo,monospace', padding: '2rem 1.5rem', maxWidth: '1100px', margin: '0 auto' },
  header: { textAlign: 'center', marginBottom: '2rem' },
  logoRow: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', marginBottom: '0.5rem' },
  logo: { fontSize: '2.5rem', background: 'linear-gradient(90deg,#14b8a6 0%,#8b5cf6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', fontWeight: 700 },
  badge: { fontSize: '0.7rem', padding: '0.3rem 0.6rem', background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.3)', borderRadius: '0.4rem', color: '#a78bfa' },
  tagline: { color: '#7a86a3', fontSize: '0.85rem' },
  modeRow: { display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' },
  modeBtn: { padding: '0.5rem 1rem', background: 'rgba(20,25,50,0.5)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '0.5rem', color: '#7a86a3', cursor: 'pointer', fontSize: '0.85rem', fontFamily: 'inherit' },
  modeBtnActive: { background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.5)', color: '#c4b5fd' },
  inputSection: { marginBottom: '0.75rem' },
  urlRow: { display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' },
  input: { flex: 1, padding: '0.85rem 1rem', background: 'rgba(20,25,50,0.6)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '0.5rem', color: '#e8eaf0', fontSize: '0.9rem', fontFamily: 'inherit', outline: 'none' },
  removeBtn: { padding: '0.5rem 0.75rem', background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '0.5rem', color: '#f87171', cursor: 'pointer' },
  addBtn: { background: 'none', border: '1px dashed rgba(139,92,246,0.3)', borderRadius: '0.5rem', color: '#7a86a3', cursor: 'pointer', padding: '0.5rem 1rem', fontSize: '0.8rem', fontFamily: 'inherit' },
  textarea: { width: '100%', padding: '0.85rem 1rem', background: 'rgba(20,25,50,0.6)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '0.5rem', color: '#e8eaf0', fontSize: '0.9rem', fontFamily: 'inherit', outline: 'none', resize: 'vertical', marginBottom: '0.75rem' },
  runBtn: { width: '100%', padding: '0.95rem', background: 'linear-gradient(90deg,#14b8a6 0%,#8b5cf6 100%)', border: 'none', borderRadius: '0.6rem', color: 'white', fontWeight: 700, cursor: 'pointer', fontSize: '1rem', fontFamily: 'inherit', marginBottom: '1.5rem' },
  runBtnStop: { background: 'linear-gradient(90deg,#ef4444,#dc2626)' },
  agentPanel: { background: 'rgba(10,14,30,0.8)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '0.75rem', marginBottom: '1.5rem', overflow: 'hidden' },
  agentHeader: { padding: '0.75rem 1rem', borderBottom: '1px solid rgba(139,92,246,0.15)', fontSize: '0.8rem', color: '#7a86a3', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  liveDot: { color: '#4ade80', animation: 'pulse 1.5s ease-in-out infinite', fontSize: '0.75rem' },
  agentLog: { padding: '0.75rem 1rem', maxHeight: '400px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.4rem' },
  stepRow: { display: 'flex', flexDirection: 'column', gap: '0.15rem' },
  stepLabel: { fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.05em' },
  stepContent: { fontSize: '0.82rem', color: '#cbd5e1', paddingLeft: '0.5rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word' },
  routingCard: { padding: '0.5rem 0.75rem', background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.15)', borderRadius: '0.4rem', fontSize: '0.82rem' },
  routingMeta: { display: 'flex', gap: '1.5rem', marginTop: '0.3rem', fontSize: '0.75rem', color: '#64748b' },
  answerPanel: { background: 'rgba(10,20,20,0.8)', border: '1px solid rgba(20,184,166,0.25)', borderRadius: '0.75rem', marginBottom: '1.5rem', overflow: 'hidden' },
  answerHeader: { padding: '0.75rem 1rem', borderBottom: '1px solid rgba(20,184,166,0.15)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' },
  costBadges: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap' },
  costBadge: { fontSize: '0.7rem', padding: '0.2rem 0.5rem', background: 'rgba(20,184,166,0.1)', border: '1px solid rgba(20,184,166,0.2)', borderRadius: '0.3rem', color: '#7dd3c8' },
  answerContent: { padding: '1.25rem 1.5rem', lineHeight: 1.7, fontSize: '0.9rem' },
  footer: { textAlign: 'center', color: '#334155', fontSize: '0.72rem', marginTop: '2rem', lineHeight: 1.8 },
}
