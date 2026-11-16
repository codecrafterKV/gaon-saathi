import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import PublicLayout from './components/PublicLayout'
import ScrollManager from './components/ScrollManager'
import { LoadingBlock } from './components/ui'
import Home from './pages/Home'
import Report from './pages/Report'
import ReportSuccess from './pages/ReportSuccess'
import Track from './pages/Track'
import About from './pages/About'
import HowItWorks from './pages/HowItWorks'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'
import Contact from './pages/Contact'
import NotFound from './pages/NotFound'

// The admin area is loaded only when needed, keeping the public site light
// for slow rural connections.
const AdminApp = lazy(() => import('./admin/AdminApp'))

export default function App() {
  return (
    <>
      <ScrollManager />
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<Home />} />
          <Route path="report" element={<Report />} />
          <Route path="report/success" element={<ReportSuccess />} />
          <Route path="track" element={<Track />} />
          <Route path="about" element={<About />} />
          <Route path="how-it-works" element={<HowItWorks />} />
          <Route path="privacy" element={<Privacy />} />
          <Route path="terms" element={<Terms />} />
          <Route path="contact" element={<Contact />} />
          <Route path="*" element={<NotFound />} />
        </Route>
        <Route path="admin/*" element={<Suspense fallback={<LoadingBlock />}><AdminApp /></Suspense>} />
      </Routes>
    </>
  )
}
