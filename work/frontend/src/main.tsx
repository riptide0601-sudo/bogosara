import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './context/AuthContext'

// dev 서버는 사내 devenv codeserver 프록시(.../codeserver/proxy/5173/) 하위경로로 접속하므로
// (vite.config.ts의 base 참고), BrowserRouter도 그 경로를 basename으로 알려줘야 라우트가
// 매칭된다 — 안 주면 실제 접속 경로가 어떤 <Route>와도 안 맞아서 화면이 통째로 안 뜬다.
// build(base: './')에서는 BASE_URL이 상대경로라 그대로 basename으로 못 쓰므로 그때만 뺀다.
const basename = import.meta.env.BASE_URL.startsWith('/') ? import.meta.env.BASE_URL : undefined;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
