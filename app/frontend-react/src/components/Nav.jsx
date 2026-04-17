import { Link, useLocation } from 'react-router-dom'

const LINKS = [
  { to: '/introduce', icon: '📖', label: '소개' },
  { to: '/meme',      icon: '🌐', label: '밈 번역' },
  { to: '/lecture',   icon: '🎓', label: '강의 Q&A' },
]

export default function Nav() {
  const { pathname } = useLocation()

  return (
    <nav className="nav">
      <Link to="/" className="nav-logo">⚡ Harness AI</Link>
      <div className="nav-links">
        {LINKS.map(({ to, icon, label }) => (
          <Link
            key={to}
            to={to}
            className={`nav-link${pathname === to ? ' active' : ''}`}
          >
            <span>{icon}</span>
            <span className="nav-label">{label}</span>
          </Link>
        ))}
      </div>
    </nav>
  )
}
