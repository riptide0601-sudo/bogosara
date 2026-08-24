import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // base를 상대경로로 지정 — 빌드 결과(dist/index.html)를 서버 없이
  // file://로 더블클릭해서 열어도 JS/CSS 경로가 깨지지 않게 하기 위함
  base: './',
})
