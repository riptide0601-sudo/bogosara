import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import CompareApp from './CompareApp.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CompareApp />
  </StrictMode>,
)
