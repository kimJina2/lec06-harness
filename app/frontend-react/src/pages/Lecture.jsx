import { useState, useRef } from 'react'
import { readSSEStream } from '../hooks/useStream'

const IMP_ORDER = { HIGH: 0, MEDIUM: 1, LOW: 2 }
const IMP_LABEL = {
  HIGH:   { icon: '🔴', label: '핵심' },
  MEDIUM: { icon: '🟡', label: '중요' },
  LOW:    { icon: '🔵', label: '참고' },
}

function formatMsg(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br />')
}

function parseKnowledge(raw) {
  let jsonStr = raw
  const m = raw.match(/```(?:json)?\s*([\s\S]*?)```/)
  if (m) jsonStr = m[1]
  else {
    const s = raw.indexOf('{'), e = raw.lastIndexOf('}')
    if (s !== -1 && e !== -1) jsonStr = raw.slice(s, e + 1)
  }
  return JSON.parse(jsonStr)
}

export default function Lecture() {
  // 입력
  const [youtubeUrl,    setYoutubeUrl]    = useState('')
  const [transcript,    setTranscript]    = useState('')
  const [videoInfo,     setVideoInfo]     = useState(null)
  const [youtubeError,  setYoutubeError]  = useState('')
  const [youtubeLoading,setYoutubeLoading]= useState(false)

  // 분석
  const [isAnalyzing,   setIsAnalyzing]   = useState(false)
  const [analyzePreview,setAnalyzePreview]= useState('')
  const [knowledge,     setKnowledge]     = useState(null)
  const [knowledgeRaw,  setKnowledgeRaw]  = useState('')
  const [lectureLoaded, setLectureLoaded] = useState(false)

  // 채팅
  const [messages,   setMessages]   = useState([])
  const [question,   setQuestion]   = useState('')
  const [isSending,  setIsSending]  = useState(false)
  const [typingText, setTypingText] = useState('')
  const [isTyping,   setIsTyping]   = useState(false)

  const chatRef     = useRef(null)
  const questionRef = useRef(null)

  function scrollChat() {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }

  // ── YouTube 자막 ──────────────────────────────────────────────────
  function extractVideoId(url) {
    try {
      url = url.trim()
      if (!/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(url)) url = 'https://' + url
      const p = new URL(url)
      if (p.hostname.endsWith('youtu.be')) return p.pathname.slice(1).split('/')[0] || null
      if (p.hostname.includes('youtube.com')) {
        if (p.searchParams.get('v')) return p.searchParams.get('v')
        const seg = p.pathname.split('/').filter(Boolean)
        if (seg[0] === 'embed' || seg[0] === 'shorts') return seg[1] || null
      }
    } catch { /* ignore */ }
    return null
  }

  function parseVtt(vtt) {
    const texts = []
    for (const raw of vtt.split('\n')) {
      const line = raw.trim()
      if (!line || line.includes('-->') || line.startsWith('WEBVTT') || /^\d+$/.test(line)) continue
      const text = line.replace(/<[^>]+>/g, '').trim()
      if (text && texts[texts.length - 1] !== text) texts.push(text)
    }
    return texts.join(' ')
  }

  async function proxyFetch(url) {
    // allorigins: JSON 래핑 방식
    const r1 = await fetch(`https://api.allorigins.win/get?url=${encodeURIComponent(url)}`)
    if (r1.ok) {
      const j = await r1.json()
      if (j?.contents) return j.contents
    }
    // corsproxy: 직접 방식
    const r2 = await fetch(`https://corsproxy.io/?url=${encodeURIComponent(url)}`)
    if (r2.ok) return r2.text()
    throw new Error(`프록시 접근 실패 (${r2.status})`)
  }

  async function fetchYoutubeClient(videoId) {
    const ytUrl = `https://www.youtube.com/watch?v=${videoId}&hl=en`
    const html  = await proxyFetch(ytUrl)

    const m = html.match(/"captionTracks":\s*(\[[\s\S]*?\])\s*,\s*"/)
    if (!m) throw new Error('이 영상에 자막이 없습니다.')

    const tracks = JSON.parse(m[1])
    const track  = tracks.find(t => t.languageCode?.startsWith('en')) || tracks[0]
    if (!track?.baseUrl) throw new Error('자막 URL을 찾을 수 없습니다.')

    const vtt = await proxyFetch(track.baseUrl + '&fmt=vtt')
    return { transcript: parseVtt(vtt), videoId }
  }

  async function fetchYoutube() {
    if (!youtubeUrl.trim()) return
    setYoutubeLoading(true)
    setYoutubeError('')

    // 1차: 서버 API (로컬에서는 동작, 클라우드에서는 IP 차단될 수 있음)
    try {
      const res  = await fetch('/api/lecture/youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: youtubeUrl }),
      })
      const data = await res.json()
      if (!data.error) {
        setTranscript(data.transcript)
        if (data.video_id) setVideoInfo({
          id: data.video_id,
          preview: data.transcript.slice(0, 200) + '...',
          length: data.transcript.length,
        })
        setYoutubeLoading(false)
        return
      }
    } catch { /* 서버 실패 시 브라우저 방식으로 폴백 */ }

    // 2차: 브라우저에서 직접 가져오기 (IP 차단 우회)
    try {
      const videoId = extractVideoId(youtubeUrl)
      if (!videoId) throw new Error('유효하지 않은 YouTube URL입니다.')
      const { transcript: t, videoId: vid } = await fetchYoutubeClient(videoId)
      setTranscript(t)
      setVideoInfo({ id: vid, preview: t.slice(0, 200) + '...', length: t.length })
    } catch (e) {
      setYoutubeError(e.message)
    }

    setYoutubeLoading(false)
  }

  // ── 강의 분석 ──────────────────────────────────────────────────────
  async function loadLecture() {
    if (!transcript.trim()) return
    setIsAnalyzing(true)
    setAnalyzePreview('')

    await readSSEStream({
      url:  '/api/lecture/analyze',
      body: { transcript },
      onChunk: chunk => setAnalyzePreview(p => p + chunk),
      onDone:  full  => renderKnowledge(full),
      onError: msg   => { setIsAnalyzing(false); setYoutubeError(msg) },
    })

    setIsAnalyzing(false)
  }

  function renderKnowledge(raw) {
    try {
      const d = parseKnowledge(raw)
      setKnowledge(d)
      setKnowledgeRaw(raw)
      setLectureLoaded(true)
      setAnalyzePreview('')
      setMessages([{
        role: 'ai',
        content: `**${d.title || '강의'}** 분석이 완료됐습니다!\n\n${d.summary || ''}\n\n핵심 개념: ${(d.key_concepts || []).slice(0, 4).map(c => c.concept).join(', ')}\n\n무엇이든 질문해보세요 😊`,
      }])
    } catch {
      setYoutubeError('강의 분석 결과 파싱 오류')
      setIsAnalyzing(false)
    }
  }

  function resetLecture() {
    setYoutubeUrl(''); setTranscript(''); setVideoInfo(null)
    setYoutubeError(''); setKnowledge(null); setKnowledgeRaw('')
    setLectureLoaded(false); setMessages([]); setAnalyzePreview('')
  }

  // ── Q&A ──────────────────────────────────────────────────────────
  async function askQuestion() {
    if (!question.trim() || !lectureLoaded || isSending) return

    const q = question.trim()
    setQuestion('')
    setIsSending(true)
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setIsTyping(true)
    setTypingText('')
    setTimeout(scrollChat, 50)

    let answer = ''
    await readSSEStream({
      url:  '/api/lecture/ask',
      body: {
        transcript,
        knowledge: knowledgeRaw,
        history:   messages.slice(-6),
        question:  q,
      },
      onChunk: chunk => {
        answer += chunk
        setTypingText(answer)
        scrollChat()
      },
      onDone: () => {
        setIsTyping(false)
        setTypingText('')
        setMessages(prev => [...prev, { role: 'ai', content: answer }])
        setTimeout(scrollChat, 50)
      },
      onError: msg => {
        setIsTyping(false)
        setMessages(prev => [...prev, { role: 'ai', content: '오류: ' + msg }])
      },
    })

    setIsSending(false)
    questionRef.current?.focus()
  }

  function fillQuestion(q) {
    if (!lectureLoaded) return
    setQuestion(q)
    questionRef.current?.focus()
  }

  const statusClass = lectureLoaded ? 'status-loaded' : isAnalyzing ? 'status-loading' : 'status-idle'
  const statusText  = lectureLoaded ? '✓ 로딩 완료'  : isAnalyzing ? '분석 중...'     : '대기 중'

  return (
    <div className="page">
      <div className="page-header">
        <span className="page-icon">🎓</span>
        <h1>강의 인터랙티브 Q&A</h1>
        <p>해외 강의·세미나 자막을 붙여넣고 질문하면 강의 내용을 근거로 답변해드립니다.</p>
      </div>

      {/* ── 입력 섹션 ── */}
      <div className="input-card">
        <div className="row-between">
          <div className="section-title">강의 자막 입력</div>
          <span className={`status-badge ${statusClass}`}>{statusText}</span>
        </div>

        {!lectureLoaded && (
          <>
            {/* YouTube URL */}
            <div className="input-row">
              <input
                className="text-input"
                type="text"
                placeholder="YouTube URL 붙여넣기 (예: https://youtube.com/watch?v=...)"
                value={youtubeUrl}
                onChange={e => setYoutubeUrl(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && fetchYoutube()}
                disabled={youtubeLoading}
              />
              <button
                className="btn btn-primary"
                onClick={fetchYoutube}
                disabled={youtubeLoading || !youtubeUrl.trim()}
              >
                {youtubeLoading ? '가져오는 중...' : '자막 가져오기'}
              </button>
            </div>

            {youtubeError && <div className="error-msg">{youtubeError}</div>}

            {/* 영상 미리보기 */}
            {videoInfo && (
              <div className="video-card">
                <img
                  className="video-thumb"
                  src={`https://img.youtube.com/vi/${videoInfo.id}/hqdefault.jpg`}
                  alt="썸네일"
                />
                <div className="video-info">
                  <div>
                    <div className="video-label">YouTube 강의</div>
                    <div className="video-prev">{videoInfo.preview}</div>
                  </div>
                  <div className="video-len">전체 자막 {videoInfo.length.toLocaleString()}자</div>
                </div>
              </div>
            )}

            <div className="or-sep">또는 직접 붙여넣기</div>

            <textarea
              className="textarea"
              style={{ minHeight: 100 }}
              placeholder="강의 자막 또는 텍스트를 직접 붙여넣으세요."
              value={transcript}
              onChange={e => setTranscript(e.target.value)}
            />

            <div className="action-row">
              <button
                className="btn btn-primary"
                onClick={loadLecture}
                disabled={isAnalyzing || !transcript.trim()}
              >
                {isAnalyzing ? '분석 중...' : '강의 분석 시작 →'}
              </button>
            </div>

            {analyzePreview && <div className="analyze-preview">{analyzePreview}</div>}
          </>
        )}

        {lectureLoaded && (
          <div className="action-row">
            <button className="btn btn-ghost" onClick={resetLecture}>새 강의 불러오기</button>
          </div>
        )}
      </div>

      {/* ── 메인 레이아웃 ── */}
      <div className="layout-split">

        {/* 왼쪽: 지식 베이스 */}
        <div className="side-panel">
          {knowledge ? (
            <div className="input-card">
              <div className="section-title">강의 요약</div>
              <div className="knowledge-summary">{knowledge.summary}</div>

              <div className="section-title" style={{ marginTop: 12 }}>핵심 개념</div>
              <div className="concept-chips">
                {(knowledge.key_concepts || []).map(c => (
                  <span
                    key={c.concept}
                    className="concept-chip"
                    title={c.definition}
                    onClick={() => fillQuestion(`${c.concept}이(가) 뭔가요?`)}
                  >
                    {c.concept}
                  </span>
                ))}
              </div>

              <div className="section-title" style={{ marginTop: 12 }}>
                자주 묻는 질문{' '}
                <span style={{ color: 'var(--pink)', fontWeight: 800 }}>
                  ({Math.min((knowledge.faq || []).length, 10)})
                </span>
              </div>
              <div className="faq-list">
                {[...(knowledge.faq || [])]
                  .slice(0, 10)
                  .sort((a, b) => (IMP_ORDER[a.importance] ?? 1) - (IMP_ORDER[b.importance] ?? 1))
                  .map((f, i) => {
                    const imp = IMP_LABEL[f.importance] || IMP_LABEL.MEDIUM
                    return (
                      <div key={i} className="faq-item" onClick={() => fillQuestion(f.question)}>
                        <span style={{ fontSize: '0.7rem', marginRight: 4 }}>{imp.icon}</span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginRight: 6 }}>
                          [{imp.label}]
                        </span>
                        {f.question}
                      </div>
                    )
                  })}
              </div>
            </div>
          ) : (
            <div className="input-card" style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-dim)' }}>
              <div style={{ fontSize: '2rem', marginBottom: 8 }}>📚</div>
              강의를 불러오면<br />지식 베이스가 여기에 표시됩니다.
            </div>
          )}
        </div>

        {/* 오른쪽: 채팅 */}
        <div className="chat-panel">
          <div className="chat-messages" ref={chatRef}>
            {messages.length === 0 && (
              <div className="empty-chat">
                <div className="empty-icon">💬</div>
                <div>강의를 불러온 후 질문하세요.</div>
                <div style={{ fontSize: '0.8rem', marginTop: 4 }}>
                  예: &quot;async/await가 뭔가요?&quot;, &quot;콜백 지옥이란?&quot;
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role === 'user' ? 'msg-user' : 'msg-ai'}`}>
                <div className="msg-avatar">{m.role === 'user' ? '나' : 'AI'}</div>
                <div
                  className="msg-bubble"
                  dangerouslySetInnerHTML={{ __html: formatMsg(m.content) }}
                />
              </div>
            ))}

            {isTyping && (
              <div className="msg msg-ai">
                <div className="msg-avatar">AI</div>
                <div
                  className="msg-bubble"
                  dangerouslySetInnerHTML={{
                    __html: typingText
                      ? formatMsg(typingText)
                      : '<div class="streaming-dots"><span/><span/><span/></div>',
                  }}
                />
              </div>
            )}
          </div>

          <div className="chat-input-row">
            <textarea
              className="chat-input"
              ref={questionRef}
              placeholder="강의 내용에 대해 질문하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
              value={question}
              disabled={!lectureLoaded}
              onChange={e => {
                setQuestion(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
              }}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); askQuestion() }
              }}
            />
            <button
              className="send-btn"
              onClick={askQuestion}
              disabled={!lectureLoaded || isSending || !question.trim()}
            >
              ↑
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
