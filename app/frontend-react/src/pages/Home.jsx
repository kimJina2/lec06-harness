import { Link } from 'react-router-dom'

const CARDS = [
  {
    to: '/meme',
    icon: '🌐',
    title: '밈 초월번역기',
    desc: '해외 밈·인터넷 슬랭·유행어를 단순 번역이 아닌 한국 최신 신조어로 감정 톤까지 살려 번역합니다. Slang-Decoder → Trend-Monitor → Sensitivity-Checker 파이프라인.',
    tag: '3단계 파이프라인',
    tagClass: 'tag-pink',
  },
  {
    to: '/lecture',
    icon: '🎓',
    title: '강의 인터랙티브 Q&A',
    desc: '해외 대학 강의·기술 세미나 YouTube URL만 넣으면 자막을 자동 분석하고, 질문하면 강의 근거로 답변해주는 AI 러닝 파트너입니다.',
    tag: '자막 자동 분석 + 대화형 Q&A',
    tagClass: 'tag-lavender',
  },
]

export default function Home() {
  return (
    <div className="home-wrap">
      <div className="hero">
        <span className="hero-deco">🌸</span>
        <span className="hero-deco">🌿</span>
        <div className="hero-badge">🌸 Spring 2025</div>
        <h1 className="hero-title">Harness AI</h1>
        <p className="hero-desc">
          해외 밈·슬랭을 한국 신조어로 초월번역하고,<br />
          해외 강의·세미나를 AI 러닝 파트너로 변환합니다.
        </p>
      </div>

      <div className="cards-grid">
        {CARDS.map(c => (
          <Link key={c.to} to={c.to} className="card">
            <div className="card-icon-wrap">{c.icon}</div>
            <h2 className="card-title">{c.title}</h2>
            <p className="card-desc">{c.desc}</p>
            <span className={`card-tag ${c.tagClass}`}>{c.tag}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
