import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  // build(dist/index.html을 file://로 더블클릭)에서는 상대경로가 필요하지만,
  // dev 서버는 사내 devenv codeserver 프록시(.../codeserver/proxy/5173/) 하위경로로
  // 접속하므로 base가 '/'로 풀리면 안 되고 그 프록시 경로 자체를 base로 줘야
  // /@vite/client, /src/main.tsx 같은 절대경로 요청이 그 경로 밑으로 나간다.
  base:
    command === 'build'
      ? './'
      : '/user/dmstnwjd77/ai-wave-team3-my-name-is/codeserver/proxy/5173/',
  server: {
    // Host 헤더가 devenv-demo.svc.oneflowai.io로 오는데, Vite는 기본적으로 DNS 리바인딩
    // 방지를 위해 localhost류 호스트만 허용한다 — 이 도메인을 명시적으로 허용해줘야 함.
    allowedHosts: ['devenv-demo.svc.oneflowai.io'],
  },
  preview: {
    allowedHosts: ['devenv-demo.svc.oneflowai.io'],
  },
}))
