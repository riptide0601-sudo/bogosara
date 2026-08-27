"""dist/를 서빙하는 초단순 정적 서버.

- codeserver 프록시 접두사(BASE_PREFIX)가 붙어 오든 안 붙어 오든(로컬 직접 테스트) 그
  접두사를 벗겨내고 dist/ 기준 상대경로로 매칭한다.
- 진짜 존재하는 정적 파일(js/css/...)은 그 파일 그대로 서빙한다 — 없으면 진짜 404.
- 그 외(확장자 없는 경로, 예: 트레일링 슬래시 없는 루트)만 index.html로 폴백한다.
  (이 앱은 react-router 없이 클라이언트 상태로만 화면을 전환하므로, URL 경로가 여러 개인
  라우팅은 애초에 없다 — 폴백은 "루트 진입점"만 커버하면 된다.)
- 루트 진입점을 index.html로 항상 200 처리하는 이유: 앞단 프록시가 트레일링 슬래시 없는
  요청에 404를 받으면 자체적으로 리다이렉트하다 경로를 중복시키는 문제가 있었기 때문.
"""
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

DIST = Path(__file__).resolve().parent / "dist"
BASE_PREFIX = "/user/dmstnwjd77/ai-wave-team3-my-name-is/codeserver/proxy/5173"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path.startswith(BASE_PREFIX):
            path = path[len(BASE_PREFIX):]
        rel = path.lstrip("/")

        candidate = DIST / rel if rel else DIST / "index.html"
        if not candidate.is_file():
            last_segment = rel.rsplit("/", 1)[-1]
            if "." in last_segment:
                # assets/foo.js 처럼 확장자가 있는데 실제로 없는 파일 — 진짜 404.
                self.send_response(404)
                self.end_headers()
                return
            candidate = DIST / "index.html"

        data = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(candidate.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"serving {DIST} on 127.0.0.1:{port} (no-404 SPA fallback)")
    server.serve_forever()
