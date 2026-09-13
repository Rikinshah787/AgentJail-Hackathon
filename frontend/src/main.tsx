import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import AgentJailApp from './agentjail/AgentJailApp.tsx'

// Arena CSS has global element selectors — keep it on its own route so it
// never bleeds into the AgentJail product shell.
const ArenaApp = lazy(() => import('./App.tsx'))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Suspense fallback={null}>
        <Routes>
          <Route path="/" element={<Navigate to="/ariai-logic" replace />} />
          <Route path="/ariai-logic/*" element={<AgentJailApp />} />
          <Route path="/arena" element={<ArenaApp />} />
          <Route path="*" element={<Navigate to="/ariai-logic" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  </StrictMode>,
)
