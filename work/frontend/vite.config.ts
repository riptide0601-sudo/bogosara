import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 사내 devenv 프록시 경로 — 로컬 개발에서는 쓰지 않는다.
// 그 환경에서 돌릴 때만 VITE_DEV_BASE 환경변수로 넘긴다.
const DEVENV_BASE = process.env.VITE_DEV_BASE

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  // build(dist/index.html을 file://로 더블클릭)에서는 상대경로가 필요하다.
  // dev는 기본 '/'(로컬), 사내 devenv에서는 VITE_DEV_BASE로 프록시 경로를 준다 —
  // 그래야 /@vite/client, /src/main.tsx 같은 절대경로 요청이 그 경로 밑으로 나간다.
  base: command === 'build' ? './' : (DEVENV_BASE ?? '/'),
  server: {
    // Host 헤더가 devenv-demo.svc.oneflowai.io로 오는데, Vite는 기본적으로 DNS 리바인딩
    // 방지를 위해 localhost류 호스트만 허용한다 — 이 도메인을 명시적으로 허용해줘야 함.
    allowedHosts: ['devenv-demo.svc.oneflowai.io'],
    // 백엔드(uvicorn, 8000)가 서빙하는 경로들을 dev 서버에서 그대로 넘긴다.
    // 제품 사진은 DB에 '/images/products/...'로 저장돼 있고, 백엔드가 app/static을
    // 루트에 마운트해서(app/main.py) 8000 쪽에만 있다 — 프록시가 없으면 5173에서
    // 찾다가 404가 난다.
    proxy: {
      '/images': 'http://127.0.0.1:8000',
    },
  },
  preview: {
    allowedHosts: ['devenv-demo.svc.oneflowai.io'],
  },
}))