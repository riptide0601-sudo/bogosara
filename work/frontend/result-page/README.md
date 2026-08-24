# 보고사라 — 스캔 결과 페이지 (mock)

검색/스캔 후 보여지는 "화장품 전성분 분석 결과" 페이지. 백엔드 없이 `mock/result.json` 하나로
전체 화면을 그리는 정적 데모다. 디자인은 `ppibik-result.html`(색감·폰트·스티커 카드 스타일)을
계승하되, 좌(원문) / 우(요약+성분리스트) 2단 레이아웃으로 재구성했다.

## 열어보기

**더블클릭으로 바로 열어도 된다** — `result.html`을 그냥 열면 끝. (자세한 이유는 아래 참고)

서버로 띄우고 싶다면:
```bash
cd result-page
python -m http.server 8123   # 아무 정적 서버나 상관없음
# http://localhost:8123/result.html
```

## 파일 구성

```
result.html          # 마크업 뼈대 (데이터는 하드코딩 없음, 전부 render.js가 채움)
style.css             # ppibik-result.html 스타일 계승 + 2단 레이아웃 + 압축된 행 높이
render.js              # render(data) 하나로 전체 화면을 그리는 렌더러
mock/result.json        # JSON 계약 그대로의 목 데이터 (진짜 소스 오브 트루스)
mock/result.inline.js    # result.json과 동일한 내용을 <script>로 심기 위한 래퍼 (아래 참고)
```

## JSON 계약

`render.js`의 `render(data)`가 받는 `data`는 `mock/result.json`과 동일한 모양이다.
`product`(제품 정보 + summary)와 `ingredients`(성분 배열) 두 키만 갖는다.

## 실제 API 연결 지점

`render.js`의 `loadData()` 안 `// TODO: API 연결` 주석 아래, `fetch('./mock/result.json')`을
실제 엔드포인트(`fetch('/api/scan-result?...')` 등)로 바꾸는 한 줄이면 된다. `render(data)`는
그대로 재사용된다.

## 왜 `mock/result.inline.js`가 따로 있나

`result.html`을 서버 없이 `file://`로 더블클릭해서 열면, `fetch('./mock/result.json')`은
브라우저 보안 정책(CORS)에 막혀 **항상 실패한다** (이건 이 페이지만의 문제가 아니라 로컬
파일에 대한 모든 `fetch`/`XHR`의 공통 제약이다). 그래서 `result.json`과 완전히 동일한 내용을
`window.__MOCK_RESULT__` 전역변수로 감싼 `result.inline.js`를 `<script src>`로 같이 불러오고,
`render.js`의 `loadData()`가 `fetch` 실패 시 이 값으로 자동 폴백한다 — 이 방식(`<script src>`)은
`file://`에서도 정상 동작한다.

**목 데이터를 고칠 땐 `mock/result.json`을 먼저 고치고**, `mock/result.inline.js`는 그 내용을
그대로 다시 붙여넣어 동기화할 것 (또는 아래 한 줄로 재생성):

```bash
python -c "
import json
data = json.load(open('mock/result.json', encoding='utf-8'))
text = json.dumps(data, ensure_ascii=False, indent=2)
open('mock/result.inline.js', 'w', encoding='utf-8').write(
    'window.__MOCK_RESULT__ = ' + text + ';\n'
)
"
```

실제 백엔드가 붙고 나면 `mock/result.inline.js` 스크립트 태그와 `loadData()`의 폴백 분기는
지워도 된다 — 서버를 통해 열리는 페이지는 `fetch`가 정상 동작하기 때문.
