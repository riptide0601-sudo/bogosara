"""크롭의 가로세로 비율(aspect ratio)과 정확도의 관계를 분석한다.

인식(rec) 모델은 크롭을 고정 크기(48x320)로 리사이즈하므로, 세로로 긴 크롭이나
가로로 아주 긴 크롭은 글자가 뭉개져 인식이 실패할 수 있다. 어느 쪽이 병목인지
확인하기 위한 진단용.
"""
import random
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

from ocr_engines import run_engine

REC_DIR = Path(__file__).parent.parent.parent / "data" / "aihub_cosmetics_ocr" / "rec"
VAL_LABEL_PATH = REC_DIR / "val_label.txt"

SAMPLE_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
SEED = 42

# 학습/추론 시 리사이즈 목표 (config의 image_shape: [3, 48, 320])
TARGET_H, TARGET_W = 48, 320


def load_val_pairs():
    pairs = []
    for line in VAL_LABEL_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rel_path, text = line.split("\t", 1)
        pairs.append((rel_path, text))
    return pairs


def bucket_aspect(w: int, h: int) -> str:
    ratio = w / h
    if ratio < 0.5:
        return "세로형 (W/H<0.5)"
    if ratio < 1.0:
        return "세로기움 (0.5~1)"
    if ratio < 2.0:
        return "정사각 (1~2)"
    if ratio < 6.67:
        return "가로형 (2~6.67)"
    return "초가로형 (>6.67)"


def main():
    pairs = load_val_pairs()
    random.seed(SEED)
    sample = random.sample(pairs, min(SAMPLE_SIZE, len(pairs)))
    print(f"샘플 {len(sample)}개 aspect ratio 분석 (seed={SEED})")
    print(f"리사이즈 목표: {TARGET_H}x{TARGET_W} (W/H = {TARGET_W/TARGET_H:.2f})\n")

    by_aspect = defaultdict(lambda: {"n": 0, "correct": 0})
    # 세로형 크롭만 따로: 90도 회전하면 맞는지도 같이 측정
    vertical_rotated = {"n": 0, "correct_orig": 0, "correct_rot": 0}

    for i, (rel_path, expected) in enumerate(sample, 1):
        image = Image.open(REC_DIR / rel_path).convert("RGB")
        w, h = image.size
        expected_s = expected.strip()

        result = run_engine("paddleocr_rec", image, gpu=True)
        if not result["ok"]:
            continue
        correct = result["text"].strip() == expected_s

        kind = bucket_aspect(w, h)
        by_aspect[kind]["n"] += 1
        by_aspect[kind]["correct"] += correct

        # 세로로 긴 크롭은 90도 돌리면 인식되는지 확인
        if w / h < 1.0:
            vertical_rotated["n"] += 1
            vertical_rotated["correct_orig"] += correct
            rotated = image.rotate(-90, expand=True)
            r2 = run_engine("paddleocr_rec", rotated, gpu=True)
            if r2["ok"] and r2["text"].strip() == expected_s:
                vertical_rotated["correct_rot"] += 1

        if i % 200 == 0:
            print(f"  [{i}/{len(sample)}] 진행 중...")

    total_n = sum(v["n"] for v in by_aspect.values())
    total_c = sum(v["correct"] for v in by_aspect.values())
    print(f"\n전체 정확도: {total_c/total_n*100:.1f}% (n={total_n})\n")

    print("=== aspect ratio(가로/세로)별 정확도 ===")
    order = ["세로형 (W/H<0.5)", "세로기움 (0.5~1)", "정사각 (1~2)", "가로형 (2~6.67)", "초가로형 (>6.67)"]
    print(f"{'구간':22s} {'개수':>7s} {'비중':>7s} {'정확도':>8s} {'오류수':>7s}")
    for kind in order:
        if kind not in by_aspect:
            continue
        n, c = by_aspect[kind]["n"], by_aspect[kind]["correct"]
        print(f"{kind:22s} {n:7d} {n/total_n*100:6.1f}% {c/n*100:7.1f}% {n-c:7d}")

    print("\n=== 오류 비중 ===")
    total_err = total_n - total_c
    for kind in order:
        if kind not in by_aspect:
            continue
        err = by_aspect[kind]["n"] - by_aspect[kind]["correct"]
        if err:
            print(f"  {kind:22s}: {err:5d}개 ({err/total_err*100:5.1f}% of 전체오류)")

    v = vertical_rotated
    if v["n"]:
        print(f"\n=== 세로로 긴 크롭(W<H) {v['n']}개: 90도 회전 효과 ===")
        print(f"  원본 그대로 : {v['correct_orig']/v['n']*100:5.1f}% ({v['correct_orig']}/{v['n']})")
        print(f"  90도 회전   : {v['correct_rot']/v['n']*100:5.1f}% ({v['correct_rot']}/{v['n']})")


if __name__ == "__main__":
    main()
