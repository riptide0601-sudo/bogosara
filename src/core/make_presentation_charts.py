"""발표용 차트 생성.

results/ 아래에 PPT에 바로 붙일 수 있는 PNG를 만든다.
수치는 모두 같은 기준끼리만 묶어서 비교한다 (버그 수정 전/후는 검증셋 자체가
달라졌으므로, 서로 다른 검증셋의 값을 한 축에 성장 그래프로 그리지 않는다).
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

RESULTS_DIR = Path(__file__).parent / "results"

# dataviz 스킬의 검증된 팔레트에서 가져온 값 (references/palette.md)
BLUE = "#2a78d6"        # categorical 슬롯 1 - 강조 대상
GRAY = "#b8b6b0"        # 비교용 배경 막대 (de-emphasis)
CRITICAL = "#d03b3b"    # status: critical - 문제 구간
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"


def _style(ax, ylabel, ymax=100):
    """공통 축 스타일: 그리드는 옅게, 축선은 최소로."""
    ax.set_ylabel(ylabel, fontsize=11, color=INK_MUTED)
    ax.set_ylim(0, ymax)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=INK_MUTED, labelsize=10, length=0)


def _label_bars(ax, bars, values, fmt="{:.1f}%", dy=1.2):
    for b, v in zip(bars, values):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + dy,
            fmt.format(v),
            ha="center",
            fontsize=12,
            fontweight="bold",
            color=INK,
        )


def _titles(fig, title, subtitle, title_y=0.965, sub_y=0.912):
    """제목(위) / 부제(아래) 순서를 고정한다."""
    fig.text(0.5, title_y, title, ha="center", va="top",
             fontsize=15, fontweight="bold", color=INK)
    fig.text(0.5, sub_y, subtitle, ha="center", va="top",
             fontsize=9.5, color=INK_MUTED)


def _delta(ax, x0, y0, x1, y1, text, color=BLUE):
    """두 막대 사이 차이를 기준선 + 양방향 화살표로 표시한다."""
    ax.plot([x0, x1 + 0.32], [y0, y0], color=BASELINE,
            linestyle="--", linewidth=1.1, zorder=2)
    xm = x1 + 0.32
    ax.annotate("", xy=(xm, y1), xytext=(xm, y0),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.5))
    ax.text(xm + 0.06, (y0 + y1) / 2, text, ha="left", va="center",
            fontsize=12.5, fontweight="bold", color=color)


def chart_finetuning():
    """Fine-tuning 전/후 — 같은(수정된) 검증셋 44,749개 기준."""
    names = ["Pretrained\n(원본 모델)", "Fine-tuned\n(LabelLens)"]
    values = [82.7, 95.2]

    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    bars = ax.bar(names, values, color=[GRAY, BLUE], width=0.46, zorder=3)
    _style(ax, "완전 일치 정확도 (%)", ymax=106)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    _label_bars(ax, bars, values)
    _delta(ax, 0, 82.7, 1, 95.2, "+12.5%p")
    ax.set_xlim(-0.6, 1.85)

    _titles(fig, "화장품 라벨 전용 Fine-tuning 효과",
            "검증 크롭 44,749개 · 학습에 사용하지 않은 데이터 · 완전 일치 기준")

    fig.tight_layout(rect=(0, 0, 1, 0.885))
    out = RESULTS_DIR / "ppt_1_finetuning.png"
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"saved: {out}")


def chart_root_cause():
    """크롭 모양(aspect ratio)별 정확도 — 세로 크롭이 개선 지점이었음."""
    names = ["세로형\n(W/H<0.5)", "세로기움\n(0.5~1)", "정사각\n(1~2)",
             "가로형\n(2~6.67)", "초가로형\n(>6.67)"]
    values = [65.4, 95.0, 97.2, 96.4, 96.2]
    colors = [CRITICAL] + [BLUE] * 4

    fig, ax = plt.subplots(figsize=(10, 5.2))
    bars = ax.bar(names, values, color=colors, width=0.56, zorder=3)
    _style(ax, "완전 일치 정확도 (%)")
    _label_bars(ax, bars, values)

    ax.annotate(
        "전체 오류의 82%가\n이 구간에 집중",
        xy=(0, 68), xytext=(0, 84),
        fontsize=11.5, color=CRITICAL, fontweight="bold",
        ha="center", va="bottom",
        arrowprops=dict(arrowstyle="->", color=CRITICAL, lw=1.5,
                        shrinkA=6, shrinkB=2),
    )

    _titles(fig, "개선 지점 발견 — 크롭 모양별 정확도",
            "화장품 용기는 성분표를 눕혀 인쇄 → 크롭의 44%가 세로형 "
            "→ 48×320으로 리사이즈될 때 글자가 뭉개짐")

    fig.tight_layout(rect=(0, 0, 1, 0.885))
    out = RESULTS_DIR / "ppt_2_root_cause.png"
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"saved: {out}")


def chart_fix_effect():
    """전처리 개선 효과 — 모델은 동일, 크롭을 바로 세우는 처리만 추가."""
    names = ["개선 전\n(세로 크롭 그대로)", "개선 후\n(반시계 90° 회전)"]
    values = [87.5, 95.2]

    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    bars = ax.bar(names, values, color=[GRAY, BLUE], width=0.46, zorder=3)
    _style(ax, "완전 일치 정확도 (%)", ymax=106)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    _label_bars(ax, bars, values)
    _delta(ax, 0, 87.5, 1, 95.2, "+7.7%p")
    ax.set_xlim(-0.6, 1.85)

    _titles(fig, "데이터 전처리 개선 효과",
            "동일한 모델 가중치 · 세로로 인쇄된 성분표를 바로 세워서 학습·인식")

    fig.tight_layout(rect=(0, 0, 1, 0.885))
    out = RESULTS_DIR / "ppt_3_fix_effect.png"
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"saved: {out}")


def chart_engines():
    """4개 엔진 비교 — crop_benchmark_raw.json에서 재계산."""
    import statistics
    from benchmark_ocr_crops import cer

    raw = RESULTS_DIR / "crop_benchmark_raw.json"
    if not raw.exists():
        print(f"skip: {raw} 없음 (benchmark_ocr_crops.py 먼저 실행)")
        return

    rows = json.loads(raw.read_text(encoding="utf-8"))
    order = ["paddleocr", "easyocr", "tesseract", "doctr"]
    labels = {"paddleocr": "PaddleOCR\n(LabelLens)", "easyocr": "EasyOCR",
              "tesseract": "Tesseract", "doctr": "docTR"}

    acc, cers, times, n = {}, {}, {}, {}
    for name in order:
        sel = [r for r in rows if r["engine"] == name]
        if not sel:
            continue
        n[name] = len(sel)
        acc[name] = sum(r["correct"] for r in sel) / len(sel) * 100
        cers[name] = statistics.mean(
            cer(r["predicted"], r["expected"].strip()) for r in sel) * 100
        times[name] = statistics.mean(r["elapsed_ms"] for r in sel) / 1000

    names = [n_ for n_ in order if n_ in acc]
    disp = [labels[x] for x in names]
    colors = [BLUE if x == "paddleocr" else GRAY for x in names]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.6))

    b0 = axes[0].bar(disp, [acc[x] for x in names], color=colors, width=0.6, zorder=3)
    _style(axes[0], "정확도 (%)")
    _label_bars(axes[0], b0, [acc[x] for x in names])
    axes[0].set_title("Exact Match (높을수록 좋음)", fontsize=12,
                      fontweight="bold", color=INK, pad=10)

    cvals = [cers[x] for x in names]
    b1 = axes[1].bar(disp, cvals, color=colors, width=0.6, zorder=3)
    _style(axes[1], "CER (%)", ymax=max(cvals) * 1.25)
    _label_bars(axes[1], b1, cvals, dy=max(cvals) * 0.02)
    axes[1].set_title("Character Error Rate (낮을수록 좋음)", fontsize=12,
                      fontweight="bold", color=INK, pad=10)

    tvals = [times[x] for x in names]
    b2 = axes[2].bar(disp, tvals, color=colors, width=0.6, zorder=3)
    _style(axes[2], "평균 처리시간 (초)", ymax=max(tvals) * 1.25)
    _label_bars(axes[2], b2, tvals, fmt="{:.2f}s", dy=max(tvals) * 0.02)
    axes[2].set_title("처리 속도 (낮을수록 좋음)", fontsize=12,
                      fontweight="bold", color=INK, pad=10)

    fig.suptitle("한국어 화장품 성분 OCR — 엔진별 성능 비교",
                 fontsize=15, fontweight="bold", color=INK, y=0.985)
    sample_n = n[names[0]]
    fig.text(0.5, 0.925,
             f"동일 크롭 {sample_n}개 · GPU(A100) · 완전 일치 기준"
             "   |   * docTR: 기본 사전학습 모델이 라틴 문자 전용이라 한글 인식 불가",
             ha="center", fontsize=9.5, color=INK_MUTED)

    fig.tight_layout(rect=(0, 0, 1, 0.90))
    out = RESULTS_DIR / "ppt_4_engines.png"
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"saved: {out}")
    for x in names:
        print(f"  {x:10s} acc={acc[x]:5.1f}%  cer={cers[x]:5.1f}%  {times[x]:.2f}s")


def chart_whole_image():
    """실제 라벨 사진 전체를 넣었을 때의 엔진 비교 (재현율 기준)."""
    import statistics
    from collections import defaultdict

    raw = RESULTS_DIR / "benchmark_raw.json"
    if not raw.exists():
        print(f"skip: {raw} 없음 (benchmark_ocr.py 먼저 실행)")
        return

    rows = json.loads(raw.read_text(encoding="utf-8"))
    acc, times = defaultdict(list), defaultdict(list)
    for r in rows:
        if r.get("accuracy_pct") is not None:
            acc[r["engine"]].append(r["accuracy_pct"])
        times[r["engine"]].append(r["elapsed_ms"])

    order = ["paddleocr", "tesseract", "easyocr", "doctr"]
    labels = {"paddleocr": "PaddleOCR\n(LabelLens)", "tesseract": "Tesseract",
              "easyocr": "EasyOCR", "doctr": "docTR"}
    names = [x for x in order if acc[x]]
    disp = [labels[x] for x in names]
    colors = [BLUE if x == "paddleocr" else GRAY for x in names]
    avals = [statistics.mean(acc[x]) for x in names]
    tvals = [statistics.mean(times[x]) / 1000 for x in names]

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.4))

    b0 = axes[0].bar(disp, avals, color=colors, width=0.58, zorder=3)
    _style(axes[0], "재현율 기반 정확도 (%)")
    _label_bars(axes[0], b0, avals)
    axes[0].set_title("정답 성분 인식률 (높을수록 좋음)", fontsize=12,
                      fontweight="bold", color=INK, pad=10)

    b1 = axes[1].bar(disp, tvals, color=colors, width=0.58, zorder=3)
    _style(axes[1], "평균 처리시간 (초)", ymax=max(tvals) * 1.25)
    _label_bars(axes[1], b1, tvals, fmt="{:.2f}s", dy=max(tvals) * 0.02)
    axes[1].set_title("사진 1장 처리 시간 (낮을수록 좋음)", fontsize=12,
                      fontweight="bold", color=INK, pad=10)

    n = len(acc[names[0]])
    _titles(fig, "실제 라벨 사진 전체를 넣었을 때 — 엔진별 비교",
            f"시중 화장품 라벨 사진 {n}장 · GPU(A100) · "
            "정답 전성분이 추출 텍스트에 얼마나 포착됐는지(재현율) 기준",
            title_y=0.97, sub_y=0.915)

    fig.tight_layout(rect=(0, 0, 1, 0.875))
    out = RESULTS_DIR / "ppt_5_whole_image.png"
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"saved: {out}")
    for x in names:
        print(f"  {x:10s} acc={statistics.mean(acc[x]):5.1f}%  {statistics.mean(times[x])/1000:.2f}s")


if __name__ == "__main__":
    RESULTS_DIR.mkdir(exist_ok=True)
    chart_finetuning()
    chart_root_cause()
    chart_fix_effect()
    chart_engines()
    chart_whole_image()
