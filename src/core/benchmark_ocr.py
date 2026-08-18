"""LabelLens OCR - 4개 엔진(Tesseract/EasyOCR/PaddleOCR/docTR) 비교 벤치마크.

samples/ 폴더의 라벨 이미지들에 대해 4개 엔진을 모두 실행해 처리 시간과
(선택적으로) 인식 정확도를 비교하고, PPT에 바로 쓸 수 있는 막대그래프를
results/ 폴더에 저장한다.

사용법:
    cd src/core
    python benchmark_ocr.py

samples/ground_truth.json이 있으면 정확도도 함께 계산한다. 형식 예시:
    {"label1.jpg": "정제수, 글리세린, ...", "label2.jpg": "..."}
정답 텍스트가 없는 이미지는 속도만 비교 대상에 포함된다.
"""
import difflib
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from ocr_engines import ENGINE_NAMES, run_all_engines

plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

SAMPLES_DIR = Path(__file__).parent / "samples"
RESULTS_DIR = Path(__file__).parent / "results"
GROUND_TRUTH_PATH = SAMPLES_DIR / "ground_truth.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _load_ground_truth() -> dict:
    if GROUND_TRUTH_PATH.exists():
        return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    return {}


def _accuracy(predicted: str, expected: str) -> float:
    """정답(전성분) 텍스트가 예측 텍스트 안에 얼마나 정확히 재현됐는지 재현율로 근사한다.

    실제 라벨 사진은 마케팅 문구·사용법 등 정답과 무관한 텍스트가 전성분보다 훨씬 많이
    섞여 있다. difflib의 대칭적 ratio(2*일치문자/(예측길이+정답길이))를 그대로 쓰면 정답과
    무관한 나머지 텍스트 분량 때문에 점수가 실제 인식 품질과 무관하게 과도히 낮아진다.
    대신 정답 문자들이 예측 텍스트 어딘가에 올바른 순서로 얼마나 포착됐는지만 측정한다
    (matched_chars / len(expected)).
    """
    if not expected:
        return 0.0
    matcher = difflib.SequenceMatcher(None, predicted, expected)
    matched_chars = sum(block.size for block in matcher.get_matching_blocks())
    return matched_chars / len(expected)


def run_benchmark():
    image_paths = sorted(
        p for p in SAMPLES_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not image_paths:
        print(f"[!] {SAMPLES_DIR}에 이미지가 없습니다. 라벨 사진을 넣고 다시 실행하세요.")
        return

    ground_truth = _load_ground_truth()

    per_engine_times = {name: [] for name in ENGINE_NAMES}
    per_engine_accuracy = {name: [] for name in ENGINE_NAMES}
    rows = []

    for image_path in image_paths:
        print(f"\n=== {image_path.name} ===")
        image = Image.open(image_path).convert("RGB")
        results = run_all_engines(image)
        expected = ground_truth.get(image_path.name)

        for result in results:
            name = result["engine"]
            if not result["ok"]:
                print(f"  {name:10s}: 실패 ({result['error']})")
                continue

            per_engine_times[name].append(result["elapsed_ms"])
            row = {
                "image": image_path.name,
                "engine": name,
                "elapsed_ms": result["elapsed_ms"],
                "text": result["text"],
            }
            if expected:
                acc = _accuracy(result["text"], expected)
                per_engine_accuracy[name].append(acc)
                row["accuracy_pct"] = round(acc * 100, 1)
                print(f"  {name:10s}: {result['elapsed_ms']:7.1f}ms  정확도 {acc * 100:5.1f}%")
            else:
                print(f"  {name:10s}: {result['elapsed_ms']:7.1f}ms")
            rows.append(row)

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "benchmark_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _plot_speed_chart(per_engine_times)
    if ground_truth:
        _plot_accuracy_chart(per_engine_accuracy)
    else:
        print(
            "\n[i] samples/ground_truth.json이 없어 정확도 그래프는 생략했습니다. "
            "정답 텍스트를 추가하면 정확도 비교도 그려줍니다."
        )

    _plot_ppt_summary(per_engine_times, per_engine_accuracy)

    print(f"\n결과 저장 위치: {RESULTS_DIR}")


def _plot_speed_chart(per_engine_times: dict):
    names = [n for n in ENGINE_NAMES if per_engine_times[n]]
    if not names:
        return
    avgs = [statistics.mean(per_engine_times[n]) for n in names]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(names, avgs, color="#4C72B0")
    ax.set_ylabel("평균 처리 시간 (ms)")
    ax.set_title("OCR 엔진별 처리 속도 비교")
    for bar, avg in zip(bars, avgs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{avg:.0f}ms",
            ha="center",
            va="bottom",
        )
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "engine_speed.png", dpi=150)
    plt.close(fig)


def _plot_accuracy_chart(per_engine_accuracy: dict):
    names = [n for n in ENGINE_NAMES if per_engine_accuracy[n]]
    if not names:
        return
    avgs = [statistics.mean(per_engine_accuracy[n]) * 100 for n in names]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(names, avgs, color="#55A868")
    ax.set_ylabel("평균 정확도 (%)")
    ax.set_ylim(0, 100)
    ax.set_title("OCR 엔진별 인식 정확도 비교")
    for bar, avg in zip(bars, avgs):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{avg:.1f}%",
            ha="center",
            va="bottom",
        )
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "engine_accuracy.png", dpi=150)
    plt.close(fig)


def _plot_ppt_summary(per_engine_times: dict, per_engine_accuracy: dict):
    """그래프 2개 + 요약 표를 한 장으로 합쳐 PPT에 바로 첨부할 수 있는 이미지를 만든다."""
    names = [n for n in ENGINE_NAMES if per_engine_times[n]]
    if not names:
        return

    avg_times = [statistics.mean(per_engine_times[n]) for n in names]
    avg_accs = [
        statistics.mean(per_engine_accuracy[n]) * 100 if per_engine_accuracy[n] else None
        for n in names
    ]

    fig = plt.figure(figsize=(13, 7.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1.3], hspace=0.4, wspace=0.25)
    fig.suptitle("LabelLens OCR 엔진 비교", fontsize=18, fontweight="bold")

    ax_speed = fig.add_subplot(gs[0, 0])
    bars = ax_speed.bar(names, avg_times, color="#4C72B0")
    ax_speed.set_ylabel("평균 처리 시간 (ms)")
    ax_speed.set_title("처리 속도")
    for bar, v in zip(bars, avg_times):
        ax_speed.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height(),
            f"{v:,.0f}ms", ha="center", va="bottom", fontsize=9,
        )

    ax_acc = fig.add_subplot(gs[0, 1])
    acc_vals = [v if v is not None else 0 for v in avg_accs]
    bars2 = ax_acc.bar(names, acc_vals, color="#55A868")
    ax_acc.set_ylabel("평균 정확도 (%)")
    ax_acc.set_ylim(0, 100)
    ax_acc.set_title("인식 정확도")
    for bar, v in zip(bars2, avg_accs):
        label = f"{v:.1f}%" if v is not None else "N/A"
        ax_acc.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height(),
            label, ha="center", va="bottom", fontsize=9,
        )

    ax_table = fig.add_subplot(gs[1, :])
    ax_table.axis("off")
    col_labels = ["엔진", "평균 처리시간", "평균 정확도", "샘플 수"]
    table_rows = []
    for n in names:
        t = statistics.mean(per_engine_times[n])
        a = statistics.mean(per_engine_accuracy[n]) * 100 if per_engine_accuracy[n] else None
        table_rows.append([
            n,
            f"{t / 1000:.1f}s" if t >= 1000 else f"{t:.0f}ms",
            f"{a:.1f}%" if a is not None else "-",
            str(len(per_engine_times[n])),
        ])
    table = ax_table.table(cellText=table_rows, colLabels=col_labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.8)

    fig.savefig(RESULTS_DIR / "ppt_summary.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    run_benchmark()
