import { useState } from 'react'
import { readSSEStream } from '../hooks/useStream'

const GRADE_CLASS = { '통과': 'grade-pass', '주의': 'grade-caution', '수정됨': 'grade-modified' }
const GRADE_ICON  = { '통과': '✅', '주의': '⚠️', '수정됨': '🔄' }

const PLATFORMS = [
  { key: 'youtube_general',   label: 'YouTube 일반' },
  { key: 'youtube_adult',     label: 'YouTube 성인' },
  { key: 'tiktok_instagram',  label: '틱톡/인스타' },
]

function MemeResult({ data }) {
  const grade = data.final?.grade || '통과'
  return (
    <>
      {/* 메인 번역 */}
      <div className="translation-main">
        <div className="original-text">{data.original}</div>
        <div className="trans-arrow">↓</div>
        <div className="final-translation">{data.final?.translation}</div>
        <span className={`grade-badge ${GRADE_CLASS[grade] || 'grade-pass'}`}>
          {GRADE_ICON[grade] || '✅'} {grade}
        </span>
      </div>

      {/* 맥락 분석 */}
      <div className="meme-section">
        <div className="section-title">맥락 분석</div>
        <div className="analysis-grid">
          {[
            { label: '직역',      value: data.analysis?.literal },
            { label: '감정 톤',   value: data.analysis?.tone },
            { label: '실제 의미', value: data.analysis?.real_meaning },
            { label: '유래',      value: data.analysis?.origin },
          ].filter(i => i.value).map(item => (
            <div key={item.label} className="analysis-item">
              <div className="a-label">{item.label}</div>
              <div className="a-value">{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* 번역 후보 */}
      {data.candidates?.length > 0 && (
        <div className="meme-section">
          <div className="section-title">번역 후보</div>
          <div className="candidates">
            {data.candidates.map((c, i) => (
              <div key={i} className="candidate">
                <div className="cand-rank">{i + 1}</div>
                <div>
                  <div className="cand-text">{c.text}</div>
                  <div className="cand-reason">{c.reason}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 검수 노트 */}
      {data.final?.note && (
        <div className="analysis-item">
          <div className="a-label">검수 노트</div>
          <div className="a-value">{data.final.note}</div>
        </div>
      )}

      {/* 플랫폼별 사용 가능 여부 */}
      {data.final?.platforms && (
        <div className="meme-section">
          <div className="section-title">플랫폼별 사용 가능 여부</div>
          <div className="platform-row">
            {PLATFORMS.map(p => {
              const ok = data.final.platforms[p.key]
              return (
                <span key={p.key} className={`platform-tag ${ok ? 'platform-ok' : 'platform-no'}`}>
                  {ok ? '✓' : '✗'} {p.label}
                </span>
              )
            })}
          </div>
        </div>
      )}
    </>
  )
}

function parseJSON(raw) {
  let jsonStr = raw
  const m = raw.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (m) jsonStr = m[1]
  else {
    const s = raw.indexOf('{'), e = raw.lastIndexOf('}')
    if (s !== -1 && e !== -1) jsonStr = raw.slice(s, e + 1)
  }
  return JSON.parse(jsonStr)
}

export default function Meme() {
  const [input,     setInput]     = useState('')
  const [loading,   setLoading]   = useState(false)
  const [streaming, setStreaming] = useState('')
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState('')
  const [showResult, setShowResult] = useState(false)

  async function handleTranslate() {
    if (!input.trim() || loading) return

    setLoading(true)
    setShowResult(true)
    setStreaming('')
    setResult(null)
    setError('')

    await readSSEStream({
      url: '/api/meme-translate',
      body: { text: input.trim() },
      onChunk: chunk => setStreaming(p => p + chunk),
      onDone: full => {
        try {
          setResult(parseJSON(full))
          setStreaming('')
        } catch {
          setError('응답 파싱 오류가 발생했습니다.')
        }
      },
      onError: msg => setError(msg),
    })

    setLoading(false)
  }

  return (
    <div className="page">
      <div className="page-header">
        <span className="page-icon">🌐</span>
        <h1>밈 초월번역기</h1>
        <p>해외 밈·슬랭을 한국 최신 신조어로 번역합니다.<br />Slang-Decoder → Trend-Monitor → Sensitivity-Checker 파이프라인.</p>
      </div>

      {/* 입력 */}
      <div className="input-card">
        <div className="section-title">번역할 표현 입력</div>
        <textarea
          className="textarea"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleTranslate() }}
          placeholder={`예시: "it's giving main character energy" 또는 "no cap fr fr"\n여러 줄의 자막 텍스트도 가능합니다.`}
          rows={4}
          disabled={loading}
        />
        <button
          className="btn btn-primary"
          onClick={handleTranslate}
          disabled={loading || !input.trim()}
          style={{ alignSelf: 'flex-start' }}
        >
          {loading ? '번역 중...' : '번역 시작 →'}
        </button>
      </div>

      {/* 결과 */}
      {showResult && (
        <div className="result-card">
          <div className="result-header">
            <span>번역 결과</span>
            {loading && (
              <div className="streaming-dots">
                <span /><span /><span />
                <span className="dots-label">Claude가 분석 중...</span>
              </div>
            )}
          </div>
          <div className="result-body">
            {error && <div className="error-msg">{error}</div>}
            {streaming && !result && <pre className="stream-preview">{streaming}</pre>}
            {result && <MemeResult data={result} />}
          </div>
        </div>
      )}
    </div>
  )
}
