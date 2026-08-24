"""
LabelLens OCR - 크롭(단어/문구) 단위 4개 엔진 비교 (완전일치 / CER / GPU 지연시간).

fine-tuning 전/후 비교와 동일한 방법론으로 4개 엔진을 나란히 비교하기 위한
스크립트. rec/val_label.txt에서 무작위 샘플을 뽑아
Tesseract/EasyOCR/PaddleOCR/docTR을 모두 GPU로 실행한다.

PaddleOCR는 크롭에 검출(det)까지 다시 돌리면 이미 잘라둔 크롭을 여러
조각으로 재분할해 점수가 부당하게 낮아지므로, 검출을 생략하는 rec-only
경로(paddleocr_rec)를 쓴다.

사용법:
    cd src/core
    python benchmark_ocr_crops.py
"""
import json
import random
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

from ocr_engines import ENGINE_NAMES, run_engine

plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

REC_DIR = Path(__file__).parent.parent.parent / "data" / "aihub_cosmetics_ocr" / "rec"
VAL_LABEL_PATH = REC_DIR / "val_label.txt"
RESULTS_DIR = Path(__file__).parent / "results"

SAMPLE_SIZE = 400
SEED = 42


def edit_distance(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = curr
    return prev[-1]


def cer(predicted: str, expected: str) -> float:
    if not expected:
        return 0.0 if not predicted else 1.0
    return edit_distance(predicted, expected) / len(expected)


def load_val_pairs():
    pairs = []
    for line in VAL_LABEL_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rel_path, text = line.split("\t", 1)
        pairs.append((rel_path, text))
    return pairs


def run_benchmark():
    pairs = load_val_pairs()
    print(f"검증 크롭 전체 개수: {len(pairs)}개")

    random.seed(SEED)
    sample = random.sample(pairs, min(SAMPLE_SIZE, len(pairs)))
    print(f"샘플 {len(sample)}개로 진행 (seed={SEED})")

    per_engine_correct = {name: 0 for name in ENGINE_NAMES}
    per_engine_total = {name: 0 for name in ENGINE_NAMES}
    per_engine_times = {name: [] for name in ENGINE_NAMES}
    per_engine_cers = {name: [] for name in ENGINE_NAMES}
    rows = []

    for i, (rel_path, expected) in enumerate(sample, 1):
        image_path = REC_DIR / rel_path
        image = Image.open(image_path).convert("RGB")
        # 크롭은 이미 한 단어/문구 단위로 잘려 있으므로, PaddleOCR만 검출을
        # 건너뛰는 rec-only 경로(paddleocr_rec)로 돌린다. 전체 파이프라인을
        # 쓰면 범용 검출기가 크롭을 여러 조각으로 재분할해 결과가 줄바꿈으로
        # 쪼개지는 오검출이 나서 PaddleOCR 점수가 부당하게 낮게 나온다.
        results = [
            run_engine("paddleocr_rec" if name == "paddleocr" else name, image, gpu=True)
            for name in ENGINE_NAMES
        ]
        for result, name in zip(results, ENGINE_NAMES):
            result["engine"] = name
            if not result["ok"]:
                continue
            per_engine_total[name] += 1
            per_engine_times[name].append(result["elapsed_ms"])
            predicted = result["text"].strip()
            correct = predicted == expected.strip()
            char_error_rate = cer(predicted, expected.strip())
            per_engine_cers[name].append(char_error_rate)
            if correct:
                per_engine_correct[name] += 1
            rows.append(
                {
                    "image": rel_path,
                    "engine": name,
                    "expected": expected,
                    "predicted": predicted,
                    "correct": correct,
                    "cer": round(char_error_rate, 4),
                    "elapsed_ms": result["elapsed_ms"],
                }
            )

        if i % 20 == 0:
            print(f"[{i}/{len(sample)}] 진행 중...")

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "crop_benchmark_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summarize(per_engine_correct, per_engine_total, per_engine_times, per_engine_cers)


def summarize(per_engine_correct, per_engine_total, per_engine_times, per_engine_cers):
    print("\n=== 결과 (완전일치 / CER / GPU 지연시간) ===")
    summary = {}
    for name in ENGINE_NAMES:
        total = per_engine_total[name]
        if total == 0:
            print(f"  {name:10s}: 실행 안 됨(미설치)")
            continue
        acc = per_engine_correct[name] / total * 100
        avg_cer = statistics.mean(per_engine_cers[name]) * 100
        avg_s = statistics.mean(per_engine_times[name]) / 1000
        summary[name] = (acc, avg_cer, avg_s)
        print(f"  {name:10s}: 정확도 {acc:5.1f}%  CER {avg_cer:5.1f}%  평균 {avg_s:6.2f}s  (n={total})")

    _plot_summary(summary)
    print(f"\n결과 저장: {RESULTS_DIR}/crop_benchmark_raw.json, crop_engine_comparison.png")
    return summary


def _plot_summary(summary: dict):
    names = [n for n in ENGINE_NAMES if n in summary]
    if not names:
        return
    accs = [summary[n][0] for n in names]
    cers = [summary[n][1] for n in names]
    times = [summary[n][2] for n in names]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.5))
    fig.suptitle("한국어 화장품 성분 OCR 엔진 성능 비교 (GPU)", fontsize=14, fontweight="bold")

    bars0 = axes[0].bar(names, accs, color="#4C72B0")
    axes[0].set_ylabel("정확도 (%)")
    axes[0].set_ylim(0, 100)
    axes[0].set_title("Exact Match")
    for b, v in zip(bars0, accs):
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"{v:.1f}%", ha="center", fontweight="bold")

    bars1 = axes[1].bar(names, cers, color="#C44E52")
    axes[1].set_ylabel("CER (%)")
    axes[1].set_title("Character Error Rate (낮을수록 좋음)")
    for b, v in zip(bars1, cers):
        axes[1].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f"{v:.1f}%", ha="center", fontweight="bold")

    bars2 = axes[2].bar(names, times, color="#55A868")
    axes[2].set_ylabel("평균 처리시간 (s)")
    axes[2].set_title("GPU Latency (낮을수록 좋음)")
    for b, v in zip(bars2, times):
        axes[2].text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.2f}s", ha="center", va="bottom", fontweight="bold")

    fig.text(
        0.02, 0.01,
        "* docTR: 기본 pretrained recognition 모델의 한국어 문자 인식 한계 확인",
        fontsize=9, color="#555555",
    )

    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(RESULTS_DIR / "crop_engine_comparison.png", dpi=150)
    plt.close(fig)


def recompute_from_raw():
    """이미 저장된 crop_benchmark_raw.json으로 OCR을 다시 돌리지 않고 지표만 재계산."""
    rows = json.loads((RESULTS_DIR / "crop_benchmark_raw.json").read_text(encoding="utf-8"))

    per_engine_correct = {name: 0 for name in ENGINE_NAMES}
    per_engine_total = {name: 0 for name in ENGINE_NAMES}
    per_engine_times = {name: [] for name in ENGINE_NAMES}
    per_engine_cers = {name: [] for name in ENGINE_NAMES}

    for row in rows:
        name = row["engine"]
        per_engine_total[name] += 1
        per_engine_times[name].append(row["elapsed_ms"])
        if row["correct"]:
            per_engine_correct[name] += 1
        per_engine_cers[name].append(cer(row["predicted"], row["expected"].strip()))

    return summarize(per_engine_correct, per_engine_total, per_engine_times, per_engine_cers)


if __name__ == "__main__":
    run_benchmark()
