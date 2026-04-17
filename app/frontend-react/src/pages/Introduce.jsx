import { Link } from 'react-router-dom'

const MEME_STEPS = [
  ['번역할 표현 입력', '"no cap fr fr", "it\'s giving main character energy" 등 해외 밈·슬랭을 입력합니다.'],
  ['3단계 AI 파이프라인 자동 실행', '맥락 분석 → 한국 신조어 매핑 → 적절성 검수 순으로 처리됩니다.'],
  ['결과 확인', '최종 번역, 후보 3개, 유래·감정 톤 분석, 플랫폼별 사용 가능 여부를 한눈에 확인합니다.'],
]

const LECTURE_STEPS = [
  ['YouTube URL 입력', '해외 대학 강의, 기술 세미나 영상 링크를 붙여넣으면 자막이 자동으로 불러와집니다.'],
  ['강의 분석 시작', 'AI가 자막을 구조화하고 핵심 개념·FAQ·학습 경로를 자동으로 추출합니다.'],
  ['질문하며 학습', '궁금한 개념을 채팅으로 질문하면 강의 내용을 근거로 한국어로 답변해줍니다.'],
]

const MEME_PIPE  = ['🔍 Slang Decoder', '→', '📡 Trend Monitor', '→', '✅ Sensitivity Checker']
const LEC_PIPE   = ['🎙 Transcription Agent', '→', '🧠 Knowledge Graph', '→', '💬 Q&A Agent']

const TECH = [
  { icon: '🤖', name: 'Claude AI',        desc: 'Anthropic 언어 모델' },
  { icon: '🔀', name: 'OpenRouter',        desc: '배포 환경 AI 게이트웨이' },
  { icon: '⚡', name: 'Groq',             desc: '로컬 테스트 무료 추론' },
  { icon: '🐍', name: 'FastAPI',           desc: 'Python 백엔드 서버' },
  { icon: '⚛️', name: 'React + Vite',     desc: 'SPA 프론트엔드' },
  { icon: '📡', name: 'SSE 스트리밍',      desc: '실시간 응답 전송' },
  { icon: '📹', name: 'YouTube API',       desc: '자막 자동 수집' },
]

function Pipeline({ nodes }) {
  return (
    <div className="pipeline">
      {nodes.map((n, i) =>
        n === '→'
          ? <span key={i} className="pipe-arrow">→</span>
          : <div key={i} className="pipe-node">{n}</div>
      )}
    </div>
  )
}

function FeatureBlock({ icon, title, sub, steps, pipe, ctaTo, ctaLabel }) {
  return (
    <div className="feature-block">
      <div className="feat-header">
        <div className="feat-icon">{icon}</div>
        <div>
          <div className="feat-title">{title}</div>
          <div className="feat-sub">{sub}</div>
        </div>
      </div>
      <div className="step-list">
        {steps.map(([t, d], i) => (
          <div key={i} className="step">
            <div className="step-num">{i + 1}</div>
            <div className="step-content"><strong>{t}</strong> — {d}</div>
          </div>
        ))}
      </div>
      <Pipeline nodes={pipe} />
      <div className="cta-row">
        <Link to={ctaTo} className="btn btn-primary">{ctaLabel} →</Link>
      </div>
    </div>
  )
}

export default function Introduce() {
  return (
    <div className="page">
      <div className="page-header">
        <span className="page-icon">📖</span>
        <h1>서비스 소개</h1>
        <p>해외 콘텐츠의 언어 장벽을 AI로 허무는 두 가지 도구를 소개합니다.</p>
      </div>

      <div className="intro-container">

        {/* WHY */}
        <div className="intro-section">
          <div className="section-label">WHY</div>
          <h2>왜 만들었나요?</h2>
          <p>
            해외의 좋은 기술 강의, 유머 넘치는 밈 콘텐츠는 넘쳐나지만 언어 장벽 때문에 제대로
            즐기지 못하는 경우가 많습니다. 단순히 번역하는 것만으로는 부족합니다.
            밈은 감정 톤까지 살려야 웃기고, 강의는 이해가 되어야 배울 수 있습니다.
          </p>
          <p>
            Harness AI는 Claude와 OpenRouter를 활용한 <strong>에이전트 파이프라인</strong>으로,
            번역을 넘어 <strong>문화적 맥락까지 이해</strong>하는 AI 도구입니다.
          </p>

          <div className="problem-grid">
            <div className="problem-box box-before">
              <div className="box-label">기존 방식의 문제</div>
              <ul>
                <li>구글 번역은 밈의 뉘앙스를 살리지 못함</li>
                <li>해외 강의 메모·정리에 시간 낭비</li>
                <li>모르는 개념이 나와도 혼자 검색해야 함</li>
                <li>자막이 빠르게 지나가면 따라가기 어려움</li>
              </ul>
            </div>
            <div className="problem-box box-after">
              <div className="box-label">Harness AI의 해결</div>
              <ul>
                <li>감정 톤이 같은 한국 신조어로 초월번역</li>
                <li>YouTube URL 하나로 강의 내용 즉시 분석</li>
                <li>강의 내용 기반으로 질문하면 바로 답변</li>
                <li>핵심 개념·FAQ 자동 추출로 빠른 복습</li>
              </ul>
            </div>
          </div>
        </div>

        <hr className="divider" />

        {/* FEATURES */}
        <div className="intro-section">
          <div className="section-label">FEATURES</div>
          <h2>두 가지 핵심 기능</h2>

          <FeatureBlock
            icon="🌐"
            title="밈 초월번역기"
            sub="해외 밈·슬랭 → 한국 신조어 초월번역"
            steps={MEME_STEPS}
            pipe={MEME_PIPE}
            ctaTo="/meme"
            ctaLabel="밈 번역기 사용하기"
          />
          <FeatureBlock
            icon="🎓"
            title="강의 인터랙티브 Q&A"
            sub="YouTube 강의 → AI 러닝 파트너"
            steps={LECTURE_STEPS}
            pipe={LEC_PIPE}
            ctaTo="/lecture"
            ctaLabel="강의 Q&A 사용하기"
          />
        </div>

        <hr className="divider" />

        {/* TECH STACK */}
        <div className="intro-section">
          <div className="section-label">TECH STACK</div>
          <h2>사용된 기술</h2>
          <p>에이전트 파이프라인 아키텍처로 각 단계를 전문 AI 에이전트가 담당합니다.</p>
          <div className="tech-grid">
            {TECH.map(t => (
              <div key={t.name} className="tech-item">
                <div className="t-icon">{t.icon}</div>
                <div className="t-name">{t.name}</div>
                <div className="t-desc">{t.desc}</div>
              </div>
            ))}
          </div>
        </div>

        <hr className="divider" />

        {/* GUIDE */}
        <div className="intro-section">
          <div className="section-label">GUIDE</div>
          <h2>사용 환경 안내</h2>

          <div className="usage-grid">
            <div className="usage-box">
              <div className="usage-label">🖥 로컬 테스트 (무료)</div>
              <div className="usage-content">
                Groq API를 사용합니다. 무료이며 분당 요청 제한이 있습니다.<br /><br />
                실행: <code>APP_ENV=local GROQ_API_KEY=... uvicorn main:app</code>
              </div>
            </div>
            <div className="usage-box">
              <div className="usage-label">🚀 배포 (OpenRouter)</div>
              <div className="usage-content">
                OpenRouter + Claude Haiku를 사용합니다. 요청당 약 $0.001~0.02 과금됩니다.<br /><br />
                실행: <code>APP_ENV=production OPENROUTER_API_KEY=... uvicorn main:app</code>
              </div>
            </div>
          </div>

          <div className="cta-row">
            <Link to="/meme"    className="btn btn-primary">🌐 밈 번역 시작</Link>
            <Link to="/lecture" className="btn btn-ghost">🎓 강의 Q&A 시작</Link>
          </div>
        </div>

      </div>
    </div>
  )
}
