import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './context/AuthContext'

// BrowserRouter는 실제 URL 경로(/product/xxx 등)를 쓰는데, 이 앱이 서빙되는 경로가
// 환경마다 다르다 — dev는 사내 devenv codeserver 프록시(.../codeserver/proxy/5173/)
// 하위경로, 로컬 직접 접속은 루트, build 산출물은 상대경로(base:'./')로 어디에 놓일지
// 모른다. BrowserRouter+basename으로 이걸 다 맞추려다 build에서는 basename을 못 구해
// 라우트가 하나도 안 매칭되는(=화면이 통째로 안 뜨는) 문제가 있었다.
// HashRouter는 실제 경로는 항상 그대로 두고 #/product/xxx처럼 해시로만 라우팅해서,
// 서버가 어떤 경로 밑에서 정적 파일을 서빙하든(+ SPA 폴백 설정 없이도) 항상 동작한다.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </HashRouter>
  </StrictMode>,
)
