import { Routes, Route } from 'react-router-dom'
import Nav from './components/Nav'
import Home from './pages/Home'
import Meme from './pages/Meme'
import Lecture from './pages/Lecture'
import Introduce from './pages/Introduce'

export default function App() {
  return (
    <>
      <div className="blob blob-1" />
      <div className="blob blob-2" />
      <Nav />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/meme" element={<Meme />} />
          <Route path="/lecture" element={<Lecture />} />
          <Route path="/introduce" element={<Introduce />} />
        </Routes>
      </main>
    </>
  )
}
