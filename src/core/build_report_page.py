"""발표용 결과 리포트 HTML을 만든다 (차트 PNG를 data URI로 인라인).

results/의 ppt_*.png를 그대로 끼워넣어, PPT에 붙일 차트와 페이지가 같은 수치를
보게 한다.
"""
import base64
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
OUT = Path("/tmp/claude-1000/-home-jovyan/bdf3f003-c7b7-4367-be1e-9158c50ec1dc/scratchpad/labellens_report.html")


def img(name: str) -> str:
    data = base64.b64encode((RESULTS_DIR / name).read_bytes()).decode()
    return f"data:image/png;base64,{data}"


HTML = f"""<title>LabelLens OCR 성능 리포트</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
  :root {{
    --paper:    #f5f6f8;
    --surface:  #ffffff;
    --raised:   #eef1f5;
    --line:     #dde2e9;
    --ink:      #14171c;
    --ink-2:    #4b5563;
    --ink-3:    #78828f;
    --accent:   #2a78d6;
    --accent-soft: #e6f0fc;
    --critical: #c8393a;
    --critical-soft: #fbeaea;
    --good:     #0f7a4d;
    --shadow:   0 1px 2px rgba(20,23,28,.05), 0 10px 26px rgba(20,23,28,.06);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --paper:    #0f1216;
      --surface:  #171c23;
      --raised:   #1e242c;
      --line:     #2b323b;
      --ink:      #e9edf3;
      --ink-2:    #aab3c0;
      --ink-3:    #7d8794;
      --accent:   #5b9df0;
      --accent-soft: rgba(91,157,240,.14);
      --critical: #e8706f;
      --critical-soft: rgba(232,112,111,.14);
      --good:     #3fbe84;
      --shadow:   0 1px 2px rgba(0,0,0,.4), 0 12px 30px rgba(0,0,0,.34);
    }}
  }}
  :root[data-theme="dark"] {{
    --paper:    #0f1216;
    --surface:  #171c23;
    --raised:   #1e242c;
    --line:     #2b323b;
    --ink:      #e9edf3;
    --ink-2:    #aab3c0;
    --ink-3:    #7d8794;
    --accent:   #5b9df0;
    --accent-soft: rgba(91,157,240,.14);
    --critical: #e8706f;
    --critical-soft: rgba(232,112,111,.14);
    --good:     #3fbe84;
    --shadow:   0 1px 2px rgba(0,0,0,.4), 0 12px 30px rgba(0,0,0,.34);
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: "IBM Plex Sans KR", system-ui, -apple-system, sans-serif;
    line-height: 1.62;
    font-size: 15px;
  }}
  .page {{
    max-width: 920px;
    margin: 0 auto;
    padding: 56px 24px 96px;
    display: flex;
    flex-direction: column;
    gap: 44px;
  }}

  .eyebrow {{
    font-family: "IBM Plex Mono", monospace;
    font-size: 12px;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 12px;
  }}
  h1 {{
    font-size: clamp(28px, 4.4vw, 38px);
    font-weight: 700;
    letter-spacing: -.02em;
    margin: 0 0 14px;
    text-wrap: balance;
  }}
  .lede {{
    color: var(--ink-2);
    font-size: 16px;
    max-width: 62ch;
    margin: 0;
  }}

  h2 {{
    font-size: 13px;
    font-family: "IBM Plex Mono", monospace;
    font-weight: 600;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--ink-3);
    margin: 0 0 18px;
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  h2::after {{ content: ""; flex: 1; height: 1px; background: var(--line); }}

  section {{ display: flex; flex-direction: column; }}

  /* 헤드라인 수치 */
  .headline {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 30px 32px;
    box-shadow: var(--shadow);
    display: flex;
    flex-wrap: wrap;
    gap: 32px 48px;
    align-items: flex-end;
  }}
  .hero-figure {{
    font-family: "IBM Plex Mono", monospace;
    font-size: 68px;
    font-weight: 600;
    line-height: 1;
    letter-spacing: -.03em;
    color: var(--accent);
    margin: 0;
  }}
  .hero-caption {{ font-size: 13.5px; color: var(--ink-2); margin: 10px 0 0; }}
  .hero-side {{ display: flex; flex-direction: column; gap: 14px; }}
  .kv {{ display: flex; flex-direction: column; gap: 2px; }}
  .kv dt {{
    font-family: "IBM Plex Mono", monospace;
    font-size: 11px; letter-spacing: .06em; text-transform: uppercase;
    color: var(--ink-3);
  }}
  .kv dd {{ margin: 0; font-size: 14.5px; font-weight: 500; }}

  figure {{ margin: 0; display: flex; flex-direction: column; gap: 10px; }}
  figure img {{
    display: block; width: 100%; height: auto;
    background: #fff;
    border: 1px solid var(--line);
    border-radius: 12px;
  }}
  figcaption {{ font-size: 13px; color: var(--ink-3); }}

  .note {{
    border-radius: 12px;
    padding: 18px 20px;
    font-size: 14px;
    border: 1px solid var(--line);
    background: var(--surface);
  }}
  .note.warn {{ border-color: var(--critical); background: var(--critical-soft); }}
  .note.warn strong {{ color: var(--critical); }}
  .note.accent {{ background: var(--accent-soft); border-color: transparent; }}
  .note p {{ margin: 0 0 8px; }}
  .note p:last-child {{ margin-bottom: 0; }}

  .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--surface); font-size: 14px; min-width: 460px; }}
  thead th {{
    text-align: left;
    font-family: "IBM Plex Mono", monospace;
    font-size: 11px; letter-spacing: .05em; text-transform: uppercase;
    color: var(--ink-3); background: var(--raised);
    padding: 11px 16px; border-bottom: 1px solid var(--line); white-space: nowrap;
  }}
  tbody td {{ padding: 12px 16px; border-bottom: 1px solid var(--line); }}
  tbody tr:last-child td {{ border-bottom: none; }}
  td.num {{ font-family: "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; text-align: right; white-space: nowrap; }}
  td.num.win {{ color: var(--accent); font-weight: 600; }}
  td.num.bad {{ color: var(--critical); }}
  .rowlabel {{ font-weight: 500; }}

  /* 진단 단계 - 실제 순서가 있는 내용이라 번호를 매긴다 */
  ol.steps {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; counter-reset: s; }}
  ol.steps li {{
    counter-increment: s;
    display: grid; grid-template-columns: 40px 1fr; gap: 18px;
    padding: 18px 0; border-top: 1px solid var(--line);
  }}
  ol.steps li:first-child {{ border-top: none; }}
  ol.steps li::before {{
    content: counter(s, decimal-leading-zero);
    font-family: "IBM Plex Mono", monospace;
    font-size: 13px; font-weight: 600; color: var(--accent);
    padding-top: 2px;
  }}
  .step-h {{ font-weight: 600; margin: 0 0 5px; font-size: 15.5px; }}
  .step-b {{ margin: 0; color: var(--ink-2); font-size: 14.5px; }}
  .step-b code, .inline-code {{
    font-family: "IBM Plex Mono", monospace; font-size: 13px;
    background: var(--raised); border: 1px solid var(--line);
    padding: 1px 6px; border-radius: 5px;
  }}

  pre {{
    margin: 12px 0 0;
    background: var(--raised);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 14px 16px;
    overflow-x: auto;
    font-family: "IBM Plex Mono", monospace;
    font-size: 13px;
    line-height: 1.6;
    color: var(--ink);
  }}
  pre .added {{ color: var(--good); font-weight: 600; }}

  footer {{
    border-top: 1px solid var(--line);
    padding-top: 20px;
    font-size: 12.5px;
    color: var(--ink-3);
  }}
  a {{ color: var(--accent); }}
  :focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }}
</style>

<div class="page">

  <header>
    <p class="eyebrow">LabelLens · 화장품 전성분 OCR</p>
    <h1>한국어 라벨 인식 정확도 95.2%</h1>
    <p class="lede">
      화장품 라벨 사진에서 전성분을 읽어내는 OCR 모델을 만들었다.
      엔진 선정부터 도메인 학습, 라벨 특성에 맞춘 전처리까지 세 단계로 정확도를 끌어올린 과정을 정리한다.
    </p>
  </header>

  <section>
    <div class="headline">
      <div>
        <p class="hero-figure">95.2%</p>
        <p class="hero-caption">완전 일치 정확도 · 검증 크롭 44,749개</p>
      </div>
      <div class="hero-side">
        <dl class="kv">
          <dt>모델</dt>
          <dd>korean_PP-OCRv5_mobile_rec · 화장품 라벨로 fine-tuning</dd>
        </dl>
        <dl class="kv">
          <dt>학습 데이터</dt>
          <dd>AI-Hub 화장품 패키징 라벨 2,390장 → 크롭 262,099개</dd>
        </dl>
        <dl class="kv">
          <dt>평가 방식</dt>
          <dd>학습에 쓰지 않은 크롭 · 예측 = 정답 완전 일치</dd>
        </dl>
      </div>
    </div>
  </section>

  <section>
    <h2>정확도를 올린 세 단계</h2>
    <ol class="steps">
      <li>
        <div>
          <p class="step-h">엔진 선정 — 4개를 같은 조건에서 비교</p>
          <p class="step-b">Tesseract · EasyOCR · PaddleOCR · docTR에 완전히 같은 데이터를 넣고
          정확도 · 문자 오류율 · 속도를 쟀다. PaddleOCR가 세 지표 모두에서 앞서 기준 엔진으로 채택했다.</p>
        </div>
      </li>
      <li>
        <div>
          <p class="step-h">도메인 fine-tuning — 화장품 성분명에 맞춰 재학습</p>
          <p class="step-b">전성분 표기는 <span class="inline-code">하이드롤라이즈드하이알루로닉애씨드</span>처럼
          일상 한국어에 없는 긴 화학 용어가 대부분이라, 범용 한국어 모델로는 한계가 있다.
          AI-Hub 화장품 패키징 데이터로 35 epoch 학습해 <strong>82.7% → 95.2%</strong>로 올렸다.</p>
        </div>
      </li>
      <li>
        <div>
          <p class="step-h">전처리 최적화 — 화장품 용기의 세로 인쇄 대응</p>
          <p class="step-b">튜브·병처럼 좁고 긴 용기는 전성분을 90도 눕혀 인쇄한다.
          이 특성을 처리하지 않으면 인식 모델이 글자를 제대로 못 읽는다는 걸 오류 분석으로 찾아냈고,
          바로잡아 <strong>+7.7%p</strong>를 추가로 얻었다.</p>
        </div>
      </li>
    </ol>
  </section>

  <section>
    <h2>1단계 · 엔진 선정</h2>
    <figure>
      <img src="{img('ppt_4_engines.png')}" alt="4개 OCR 엔진의 정확도, 문자 오류율, 처리 속도 비교. PaddleOCR가 정확도 95.0%, CER 3.2%, 0.08초로 세 지표 모두 1위.">
      <figcaption>같은 크롭 400개를 4개 엔진에 똑같이 넣어 비교했다.</figcaption>
    </figure>
    <div class="note" style="margin-top:18px">
      <p><strong>docTR가 0%인 이유</strong> — 기본 사전학습 모델이 라틴 문자 전용이라 한글을 아예 다른 글자로 읽는다.
      (예: <span class="inline-code">소이아미도프로필아민옥사이드,</span> → <span class="inline-code">AOOFIE HOHIEAO</span>)
      엔진 자체의 결함이 아니라 한국어 모델이 제공되지 않는다는 뜻이다.</p>
    </div>
  </section>

  <section>
    <h2>2단계 · 도메인 fine-tuning</h2>
    <figure>
      <img src="{img('ppt_1_finetuning.png')}" alt="원본 모델 82.7%, fine-tuned 모델 95.2%로 12.5%p 향상.">
      <figcaption>같은 검증셋·같은 설정에서 가중치만 바꿔 측정했다. 차이는 순수하게 fine-tuning 효과다.</figcaption>
    </figure>
    <div class="table-wrap" style="margin-top:22px">
      <table>
        <thead><tr><th>항목</th><th>내용</th></tr></thead>
        <tbody>
          <tr><td class="rowlabel">기반 모델</td><td>korean_PP-OCRv5_mobile_rec (PaddleOCR 공식 한국어 인식 모델)</td></tr>
          <tr><td class="rowlabel">학습 데이터</td><td>AI-Hub 「의약품·화장품 패키징 OCR」 라벨 2,390장 → 크롭 262,099개</td></tr>
          <tr><td class="rowlabel">학습 설정</td><td>35 epoch · batch 48 · GPU(A100) · CTC + NRTR 멀티헤드</td></tr>
          <tr><td class="rowlabel">검증</td><td>학습에 쓰지 않은 크롭 44,749개</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>3단계 · 전처리 최적화</h2>
    <p style="margin:0 0 20px; color:var(--ink-2); font-size:15px; max-width:64ch">
      학습 데이터를 2.8배 늘리고 epoch을 75% 더 돌려도 정확도가 87%대에서 더 오르지 않았다.
      단순히 더 학습하는 대신, 어떤 입력에서 틀리는지를 나눠서 분석했다.
    </p>

    <ol class="steps">
      <li>
        <div>
          <p class="step-h">과적합이 아니라 과소적합이었다</p>
          <p class="step-b">augmentation을 끄고 학습셋을 재측정하니 88.9%로, 검증셋(87.5%)과 1.4%p 차이뿐이었다.
          <strong>학습 데이터조차 제대로 못 맞추고 있다</strong>는 뜻 — 데이터가 부족한 게 아니라
          구조적으로 못 읽는 입력이 있다는 신호였다.</p>
        </div>
      </li>
      <li>
        <div>
          <p class="step-h">오류가 특정 모양의 크롭에 몰려 있었다</p>
          <p class="step-b">오류를 문자 종류 · 길이 · 이미지 비율로 나눠보니,
          세로로 긴 크롭 하나에 전체 오류의 82%가 집중돼 있었다. 나머지 모양은 모두 95~97%였다.</p>
        </div>
      </li>
      <li>
        <div>
          <p class="step-h">화장품 라벨은 성분표를 눕혀 인쇄한다</p>
          <p class="step-b">좁고 긴 용기 특성상 전성분이 90도 돌아간 채 인쇄돼, 크롭의 44%가 세로로 길었다.
          인식 모델은 크롭을 48×320(가로로 긴 형태)에 맞춰 리사이즈하므로, 눕힌 크롭은 폭 24px로
          찌그러져 글자가 뭉개졌다. 짧은 크롭은 그래도 읽혔지만(96%) 긴 크롭은 무너졌다(36%).</p>
        </div>
      </li>
      <li>
        <div>
          <p class="step-h">세로 크롭을 바로 세워서 학습·인식</p>
          <p class="step-b">세로로 긴 크롭을 반시계 90도 돌린 뒤 학습 데이터를 다시 만들고,
          인식 단계에도 같은 규칙을 적용했다. 학습 입력과 실제 추론 입력의 형태도 이때 일치시켰다.</p>
          <pre>crop = cv2.warpPerspective(image, matrix, (w, h))
<span class="added">+ if crop_h / crop_w &gt;= 1.5:</span>
<span class="added">+     crop = np.rot90(crop)   # 반시계 90도</span></pre>
        </div>
      </li>
    </ol>

    <figure style="margin-top:32px">
      <img src="{img('ppt_2_root_cause.png')}" alt="크롭 모양별 정확도. 세로형만 65.4%이고 나머지 네 구간은 95~97%.">
      <figcaption>세로로 긴 크롭만 65.4%, 나머지는 모두 95~97%. 여기에 전체 오류의 82%가 몰려 있었다.</figcaption>
    </figure>

    <figure style="margin-top:28px">
      <img src="{img('ppt_3_fix_effect.png')}" alt="전처리 개선 전 87.5%, 개선 후 95.2%로 7.7%p 향상.">
      <figcaption>모델 가중치는 그대로 두고 크롭 방향만 바로잡아 학습·검증 크롭 306,848개를 다시 만들었다.</figcaption>
    </figure>

    <div class="table-wrap" style="margin-top:26px">
      <table>
        <thead>
          <tr><th>검증 대상</th><th style="text-align:right">개선 전</th><th style="text-align:right">개선 후</th></tr>
        </thead>
        <tbody>
          <tr><td class="rowlabel">세로로 긴 크롭 528개</td><td class="num bad">72.2%</td><td class="num win">94.1%</td></tr>
          <tr><td class="rowlabel">전체 표본 1,200개</td><td class="num">85.9%</td><td class="num win">95.6%</td></tr>
          <tr><td class="rowlabel">전체 검증셋 44,749개 (공식)</td><td class="num">87.5%</td><td class="num win">95.2%</td></tr>
        </tbody>
      </table>
    </div>

    <div class="note accent" style="margin-top:20px">
      <p>학습 데이터를 2.8배 늘리고 epoch을 75% 더 돌려 얻은 것이 <strong>+2.6%p</strong>였고,
      라벨 특성에 맞춘 전처리 하나가 <strong>+7.7%p</strong>였다.
      데이터를 더 넣기 전에 <strong>무엇을 틀리는지 먼저 나눠 본 것</strong>이 결정적이었다.</p>
    </div>
  </section>

  <section>
    <h2>예상 질문</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th style="width:38%">질문</th><th>답변</th></tr></thead>
        <tbody>
          <tr>
            <td class="rowlabel">왜 완전 일치로 평가했나</td>
            <td>크롭 하나가 이미 한 단어 단위라 "맞다/틀리다"가 명확하고, PaddleOCR 자체 학습 지표(<span class="inline-code">RecMetric</span>)와도 같아 다른 모델과 비교할 수 있다.</td>
          </tr>
          <tr>
            <td class="rowlabel">검증셋이 학습에 안 쓰인 게 확실한가</td>
            <td>이미지 단위로 먼저 나눈 뒤(train 1,385장 / val 244장) 각각에서 크롭을 만들었다. 같은 사진에서 나온 크롭이 양쪽에 섞이지 않는다.</td>
          </tr>
          <tr>
            <td class="rowlabel">왜 더 큰 모델을 쓰지 않았나</td>
            <td>PaddleOCR가 공식 제공하는 한국어 인식 모델은 경량(mobile) 버전뿐이다. 다만 이번 병목은 모델 용량이 아니라 데이터 전처리였고, 그쪽을 해결해 95.2%에 도달했다.</td>
          </tr>
          <tr>
            <td class="rowlabel">실제 서비스에서도 이 정확도가 나오나</td>
            <td>이 수치는 잘라낸 단어 단위 인식 정확도다. 실제 사진은 검출 단계를 먼저 거치므로 조명·초점·용기 곡면 왜곡의 영향을 추가로 받는다.</td>
          </tr>
          <tr>
            <td class="rowlabel">앞으로 더 올릴 여지는</td>
            <td>남은 오류는 영문·숫자가 섞인 구간(제조번호, 용량 표기 등)에 상대적으로 몰려 있다. 해당 유형 데이터를 보강하는 것이 다음 단계다.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>

  <footer>
    검증 크롭 44,749개 · 완전 일치 기준 · GPU(A100) · 측정일 2026-08-24 ·
    모델 korean_PP-OCRv5_mobile_rec 35 epoch fine-tuned
  </footer>

</div>
"""

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HTML, encoding="utf-8")
    print(f"written: {OUT}  ({len(HTML)/1024:.0f}KB)")
