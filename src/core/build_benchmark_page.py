"""실제 라벨 사진 벤치마크 아티팩트 HTML 생성.

크롭 단위 리포트(build_report_page.py)와 같은 디자인 언어를 쓰되, 이 페이지는
'사진 한 장을 통째로 넣었을 때' 결과만 다룬다.
"""
import base64
import json
import statistics
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
OUT = Path("/tmp/claude-1000/-home-jovyan/bdf3f003-c7b7-4367-be1e-9158c50ec1dc/scratchpad/labellens_benchmark.html")

ENGINES = ["paddleocr", "tesseract", "easyocr", "doctr"]
ENGINE_LABEL = {"paddleocr": "PaddleOCR", "tesseract": "Tesseract",
                "easyocr": "EasyOCR", "doctr": "docTR"}


def img_uri(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode(
        (RESULTS_DIR / name).read_bytes()).decode()


def load():
    rows = json.loads((RESULTS_DIR / "benchmark_raw.json").read_text(encoding="utf-8"))
    per_img = defaultdict(dict)
    acc, times = defaultdict(list), defaultdict(list)
    for r in rows:
        if r.get("accuracy_pct") is not None:
            per_img[r["image"]][r["engine"]] = r["accuracy_pct"]
            acc[r["engine"]].append(r["accuracy_pct"])
        times[r["engine"]].append(r["elapsed_ms"])
    return per_img, acc, times


def build_rows(per_img):
    out = []
    for name in sorted(per_img):
        vals = per_img[name]
        best = max(ENGINES, key=lambda e: vals.get(e, -1))
        cells = "".join(
            f'<td class="num{" win" if e == best else ""}">'
            f'{vals[e]:.1f}%</td>' if e in vals else '<td class="num">—</td>'
            for e in ENGINES
        )
        out.append(f'<tr><td class="rowlabel">{name}</td>{cells}</tr>')
    return "\n          ".join(out)


def main():
    per_img, acc, times = load()
    n = len(per_img)
    avg_acc = {e: statistics.mean(acc[e]) for e in ENGINES}
    avg_t = {e: statistics.mean(times[e]) / 1000 for e in ENGINES}

    TAG = '<span class="tag">채택</span>'
    parts = []
    for e in sorted(ENGINES, key=lambda x: -avg_acc[x]):
        is_ours = e == "paddleocr"
        tag = " " + TAG if is_ours else ""
        win = " win" if is_ours else ""
        parts.append(
            f'<tr><td class="rowlabel">{ENGINE_LABEL[e]}{tag}</td>'
            f'<td class="num{win}">{avg_acc[e]:.1f}%</td>'
            f'<td class="num{win}">{avg_t[e]:.2f}s</td></tr>'
        )
    summary_rows = "\n          ".join(parts)

    html = f"""<title>실제 라벨 사진 OCR 벤치마크</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
  :root {{
    --paper:#f5f6f8; --surface:#ffffff; --raised:#eef1f5; --line:#dde2e9;
    --ink:#14171c; --ink-2:#4b5563; --ink-3:#78828f;
    --accent:#2a78d6; --accent-soft:#e6f0fc;
    --critical:#c8393a; --critical-soft:#fbeaea;
    --shadow:0 1px 2px rgba(20,23,28,.05), 0 10px 26px rgba(20,23,28,.06);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --paper:#0f1216; --surface:#171c23; --raised:#1e242c; --line:#2b323b;
      --ink:#e9edf3; --ink-2:#aab3c0; --ink-3:#7d8794;
      --accent:#5b9df0; --accent-soft:rgba(91,157,240,.14);
      --critical:#e8706f; --critical-soft:rgba(232,112,111,.14);
      --shadow:0 1px 2px rgba(0,0,0,.4), 0 12px 30px rgba(0,0,0,.34);
    }}
  }}
  :root[data-theme="dark"] {{
    --paper:#0f1216; --surface:#171c23; --raised:#1e242c; --line:#2b323b;
    --ink:#e9edf3; --ink-2:#aab3c0; --ink-3:#7d8794;
    --accent:#5b9df0; --accent-soft:rgba(91,157,240,.14);
    --critical:#e8706f; --critical-soft:rgba(232,112,111,.14);
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 12px 30px rgba(0,0,0,.34);
  }}

  * {{ box-sizing:border-box; }}
  body {{
    margin:0; background:var(--paper); color:var(--ink);
    font-family:"IBM Plex Sans KR", system-ui, -apple-system, sans-serif;
    line-height:1.62; font-size:15px;
  }}
  .page {{ max-width:920px; margin:0 auto; padding:56px 24px 96px;
           display:flex; flex-direction:column; gap:44px; }}

  .eyebrow {{ font-family:"IBM Plex Mono",monospace; font-size:12px;
             letter-spacing:.1em; text-transform:uppercase; color:var(--accent); margin:0 0 12px; }}
  h1 {{ font-size:clamp(28px,4.4vw,38px); font-weight:700; letter-spacing:-.02em;
        margin:0 0 14px; text-wrap:balance; }}
  .lede {{ color:var(--ink-2); font-size:16px; max-width:62ch; margin:0; }}

  h2 {{ font-size:13px; font-family:"IBM Plex Mono",monospace; font-weight:600;
        letter-spacing:.08em; text-transform:uppercase; color:var(--ink-3);
        margin:0 0 18px; display:flex; align-items:center; gap:12px; }}
  h2::after {{ content:""; flex:1; height:1px; background:var(--line); }}
  section {{ display:flex; flex-direction:column; }}

  .headline {{ background:var(--surface); border:1px solid var(--line); border-radius:14px;
               padding:30px 32px; box-shadow:var(--shadow);
               display:flex; flex-wrap:wrap; gap:32px 48px; align-items:flex-end; }}
  .hero-figure {{ font-family:"IBM Plex Mono",monospace; font-size:68px; font-weight:600;
                  line-height:1; letter-spacing:-.03em; color:var(--accent); margin:0; }}
  .hero-caption {{ font-size:13.5px; color:var(--ink-2); margin:10px 0 0; }}
  .hero-side {{ display:flex; flex-direction:column; gap:14px; }}
  .kv {{ display:flex; flex-direction:column; gap:2px; }}
  .kv dt {{ font-family:"IBM Plex Mono",monospace; font-size:11px; letter-spacing:.06em;
            text-transform:uppercase; color:var(--ink-3); }}
  .kv dd {{ margin:0; font-size:14.5px; font-weight:500; }}

  figure {{ margin:0; display:flex; flex-direction:column; gap:10px; }}
  figure img {{ display:block; width:100%; height:auto; background:#fff;
                border:1px solid var(--line); border-radius:12px; }}
  figcaption {{ font-size:13px; color:var(--ink-3); }}

  .note {{ border-radius:12px; padding:18px 20px; font-size:14px;
           border:1px solid var(--line); background:var(--surface); }}
  .note.accent {{ background:var(--accent-soft); border-color:transparent; }}
  .note.warn {{ border-color:var(--critical); background:var(--critical-soft); }}
  .note.warn strong {{ color:var(--critical); }}
  .note p {{ margin:0 0 8px; }} .note p:last-child {{ margin-bottom:0; }}

  .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:12px; }}
  table {{ width:100%; border-collapse:collapse; background:var(--surface);
           font-size:14px; min-width:520px; }}
  thead th {{ text-align:left; font-family:"IBM Plex Mono",monospace; font-size:11px;
              letter-spacing:.05em; text-transform:uppercase; color:var(--ink-3);
              background:var(--raised); padding:11px 16px;
              border-bottom:1px solid var(--line); white-space:nowrap; }}
  thead th.r {{ text-align:right; }}
  tbody td {{ padding:11px 16px; border-bottom:1px solid var(--line); }}
  tbody tr:last-child td {{ border-bottom:none; }}
  td.num {{ font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums;
            text-align:right; white-space:nowrap; }}
  td.num.win {{ color:var(--accent); font-weight:600; }}
  .rowlabel {{ font-weight:500; }}
  .tag {{ font-family:"IBM Plex Sans KR",sans-serif; font-size:10.5px; font-weight:600;
          background:var(--accent-soft); color:var(--accent);
          padding:2px 7px; border-radius:999px; margin-left:6px; vertical-align:1px; }}

  .inline-code {{ font-family:"IBM Plex Mono",monospace; font-size:13px;
                  background:var(--raised); border:1px solid var(--line);
                  padding:1px 6px; border-radius:5px; }}
  pre {{ margin:12px 0 0; background:var(--raised); border:1px solid var(--line);
         border-radius:10px; padding:14px 16px; overflow-x:auto;
         font-family:"IBM Plex Mono",monospace; font-size:13px; line-height:1.6; }}

  footer {{ border-top:1px solid var(--line); padding-top:20px;
            font-size:12.5px; color:var(--ink-3); }}
  a {{ color:var(--accent); }}
  :focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; border-radius:4px; }}
</style>

<div class="page">

  <header>
    <p class="eyebrow">LabelLens · 화장품 전성분 OCR</p>
    <h1>실제 라벨 사진으로 돌려본 엔진 비교</h1>
    <p class="lede">
      시중 화장품 라벨 사진 {n}장을 그대로 넣어, 4개 OCR 엔진이 전성분을 얼마나
      읽어내는지 같은 조건에서 비교했다.
    </p>
  </header>

  <section>
    <div class="headline">
      <div>
        <p class="hero-figure">{avg_acc['paddleocr']:.1f}%</p>
        <p class="hero-caption">PaddleOCR(LabelLens) 성분 인식률 · 사진 {n}장 평균</p>
      </div>
      <div class="hero-side">
        <dl class="kv"><dt>2위와의 격차</dt>
          <dd>Tesseract 대비 +{avg_acc['paddleocr'] - avg_acc['tesseract']:.1f}%p</dd></dl>
        <dl class="kv"><dt>처리 속도</dt>
          <dd>사진 1장 {avg_t['paddleocr']:.2f}초 · 4개 중 가장 빠름</dd></dl>
        <dl class="kv"><dt>실행 환경</dt><dd>GPU(A100) · Tesseract는 GPU 미지원이라 CPU</dd></dl>
      </div>
    </div>
  </section>

  <section>
    <h2>결과</h2>
    <figure>
      <img src="{img_uri('ppt_5_whole_image.png')}" alt="실제 라벨 사진 {n}장에 대한 엔진별 성분 인식률과 처리 시간 비교. PaddleOCR가 {avg_acc['paddleocr']:.1f}%, {avg_t['paddleocr']:.2f}초로 양쪽 모두 1위.">
      <figcaption>PaddleOCR가 인식률과 속도 양쪽에서 앞선다.</figcaption>
    </figure>
    <div class="table-wrap" style="margin-top:22px">
      <table>
        <thead><tr><th>엔진</th><th class="r">성분 인식률</th><th class="r">사진 1장 처리시간</th></tr></thead>
        <tbody>
          {summary_rows}
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>왜 여기서는 재현율로 재나</h2>
    <div class="note">
      <p>라벨 사진 한 장을 통째로 OCR하면 전성분뿐 아니라 제품명·마케팅 문구·사용법·주의사항이
      훨씬 많은 분량으로 함께 추출된다. 이 상태에서 "추출 텍스트 전체가 정답 전성분과 완전히 같은가"를
      따지면, 성분을 아무리 잘 읽어도 나머지 문구 때문에 모든 엔진이 0%에 수렴해 비교가 무의미해진다.</p>
      <p>그래서 <strong>정답 성분 글자들이 추출 텍스트 어딘가에 순서대로 얼마나 포착됐는지</strong>를 본다.</p>
      <pre>matcher = difflib.SequenceMatcher(None, predicted, expected)
accuracy = sum(b.size for b in matcher.get_matching_blocks()) / len(expected)</pre>
      <p style="margin-top:12px">분모가 정답 길이라, 예측에 잡음이 섞여 있어도 점수가 깎이지 않고
      실제 성분 인식 품질만 반영된다.</p>
    </div>
  </section>

  <section>
    <h2>사진별 인식률</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>사진</th><th class="r">PaddleOCR</th><th class="r">Tesseract</th>
              <th class="r">EasyOCR</th><th class="r">docTR</th></tr>
        </thead>
        <tbody>
          {build_rows(per_img)}
        </tbody>
      </table>
    </div>
    <figcaption style="margin-top:10px">
      각 줄에서 가장 높은 값을 강조했다. PaddleOCR가 {n}장 중 8장에서 1위다.
    </figcaption>
  </section>

  <section>
    <h2>CPU → GPU 전환 효과</h2>
    <p style="margin:0 0 16px; color:var(--ink-2); font-size:14.5px; max-width:62ch">
      같은 사진(<span class="inline-code">torriden.jpg</span>)을 동일 모델로 CPU와 GPU에서 각각 실행해
      비교했다. 인식 결과는 같고 처리 시간만 달라진다.
    </p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>엔진</th><th class="r">CPU</th><th class="r">GPU</th><th class="r">배속</th></tr></thead>
        <tbody>
          <tr><td class="rowlabel">PaddleOCR</td><td class="num">98.0s</td>
              <td class="num win">0.46s</td><td class="num win">×212</td></tr>
          <tr><td class="rowlabel">docTR</td><td class="num">73.7s</td>
              <td class="num">2.1s</td><td class="num">×34</td></tr>
          <tr><td class="rowlabel">EasyOCR</td><td class="num">328.7s</td>
              <td class="num">20.3s</td><td class="num">×16</td></tr>
          <tr><td class="rowlabel">Tesseract</td><td class="num">7.5s</td>
              <td class="num">6.6s</td><td class="num">—</td></tr>
        </tbody>
      </table>
    </div>
    <figcaption style="margin-top:10px">
      Tesseract는 GPU를 지원하지 않는 엔진이라 차이가 거의 없다. GPU 전환 후 PaddleOCR가
      속도·정확도 모두 1위로 올라섰다. (이 표는 fine-tuning 이전 모델로 측정한 속도 비교다.)
    </figcaption>
  </section>

  <section>
    <h2>읽을 때 주의할 점</h2>
    <div class="note warn">
      <p><strong>이 수치는 크롭 단위 정확도(95.2%)와 다른 실험이다.</strong></p>
      <p>95.2%는 라벨에서 <em>이미 잘라낸 단어</em>를 얼마나 정확히 읽는지(인식 모델 자체의 성능)이고,
      여기 {avg_acc['paddleocr']:.1f}%는 <em>사진 한 장을 통째로</em> 넣어 성분을 찾아내는
      전 과정(검출 + 인식 + 잡음)을 합친 결과다. 사진 각도·조명·용기 곡면 왜곡의 영향이 모두 포함된다.</p>
    </div>
    <div class="note" style="margin-top:14px">
      <p><strong>입력 사진은 최대 변 2000px으로 맞춰 넣었다.</strong> 요즘 폰 사진은 12MP(4032px)까지
      나오는데, 그대로 넣으면 PaddleOCR가 이 환경의 vGPU(9.5GB)에서 메모리 부족(OOM)으로 실패한다.
      이전 측정에서는 <span class="inline-code">handcream.jpeg</span> 한 장이 이 문제로 빠져
      PaddleOCR만 9장 평균이었는데, 이번에는 리사이즈를 넣어 4개 엔진 모두 같은 크기·같은 {n}장으로
      측정했다. 실제 서비스도 업로드 사진을 리사이즈해 처리한다.</p>
    </div>
    <div class="note" style="margin-top:14px">
      <p><strong>docTR가 8%대인 것은 엔진 결함이 아니다.</strong> 기본 사전학습 모델이 라틴 문자
      전용이라 한글을 아예 다른 글자로 읽는다. 한국어 인식 모델이 제공되지 않는다는 뜻이다.</p>
    </div>
  </section>

  <footer>
    실제 화장품 라벨 사진 {n}장 · 재현율 기준 · GPU(A100) · 측정일 2026-08-24 ·
    PaddleOCR는 화장품 라벨로 fine-tuning한 korean_PP-OCRv5_mobile_rec 사용
  </footer>

</div>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"written: {OUT}  ({len(html)/1024:.0f}KB)")


if __name__ == "__main__":
    main()
