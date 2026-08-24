"""검출 버그 수정 후(rec-only) 기준으로, 남은 오류가 어떤 유형에 몰려있는지 정량화한다.

크롭 텍스트를 문자 구성(한글/라틴/숫자/기호)과 길이로 분류해서 유형별 정확도를
따로 계산한다. "무엇을 보강하면 정확도가 오르는가"를 데이터로 답하기 위한 스크립트.
"""
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

from ocr_engines import run_engine

REC_DIR = Path(__file__).parent.parent.parent / "data" / "aihub_cosmetics_ocr" / "rec"
VAL_LABEL_PATH = REC_DIR / "val_label.txt"

SAMPLE_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
SEED = 42
MAX_TEXT_LENGTH = 25  # 학습 config의 max_text_length

_HANGUL = re.compile(r"[가-힣]")
_LATIN = re.compile(r"[A-Za-z]")
_DIGIT = re.compile(r"[0-9]")


def classify(text: str) -> str:
    """크롭 텍스트를 문자 구성 기준으로 분류."""
    has_hangul = bool(_HANGUL.search(text))
    has_latin = bool(_LATIN.search(text))
    has_digit = bool(_DIGIT.search(text))

    if has_hangul and has_latin:
        return "한글+라틴 혼합"
    if has_latin:
        return "라틴(영문)"
    if has_hangul and has_digit:
        return "한글+숫자"
    if has_hangul:
        return "한글만"
    if has_digit:
        return "숫자만"
    return "기호만"


def load_val_pairs():
    pairs = []
    for line in VAL_LABEL_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rel_path, text = line.split("\t", 1)
        pairs.append((rel_path, text))
    return pairs


def main():
    pairs = load_val_pairs()
    random.seed(SEED)
    sample = random.sample(pairs, min(SAMPLE_SIZE, len(pairs)))
    print(f"샘플 {len(sample)}개로 유형별 정확도 분석 (seed={SEED})\n")

    by_type = defaultdict(lambda: {"n": 0, "correct": 0})
    by_len = defaultdict(lambda: {"n": 0, "correct": 0})
    over_max_len = {"n": 0, "correct": 0}
    errors = []

    for i, (rel_path, expected) in enumerate(sample, 1):
        image = Image.open(REC_DIR / rel_path).convert("RGB")
        result = run_engine("paddleocr_rec", image, gpu=True)
        if not result["ok"]:
            continue
        predicted = result["text"].strip()
        expected_s = expected.strip()
        correct = predicted == expected_s

        kind = classify(expected_s)
        by_type[kind]["n"] += 1
        by_type[kind]["correct"] += correct

        length = len(expected_s)
        bucket = "1자" if length == 1 else "2-4자" if length <= 4 else "5-10자" if length <= 10 else "11-25자" if length <= MAX_TEXT_LENGTH else "25자 초과"
        by_len[bucket]["n"] += 1
        by_len[bucket]["correct"] += correct

        if length > MAX_TEXT_LENGTH:
            over_max_len["n"] += 1
            over_max_len["correct"] += correct

        if not correct:
            errors.append((kind, expected_s, predicted))

        if i % 200 == 0:
            print(f"  [{i}/{len(sample)}] 진행 중...")

    total_n = sum(v["n"] for v in by_type.values())
    total_correct = sum(v["correct"] for v in by_type.values())
    print(f"\n전체 정확도: {total_correct / total_n * 100:.1f}% (n={total_n})\n")

    print("=== 문자 구성별 ===")
    print(f"{'유형':16s} {'개수':>7s} {'비중':>7s} {'정확도':>8s} {'오류수':>7s}")
    for kind, v in sorted(by_type.items(), key=lambda x: -x[1]["n"]):
        n, c = v["n"], v["correct"]
        print(f"{kind:16s} {n:7d} {n/total_n*100:6.1f}% {c/n*100:7.1f}% {n-c:7d}")

    print("\n=== 길이별 ===")
    order = ["1자", "2-4자", "5-10자", "11-25자", "25자 초과"]
    for bucket in order:
        if bucket not in by_len:
            continue
        n, c = by_len[bucket]["n"], by_len[bucket]["correct"]
        print(f"{bucket:10s} {n:7d} {n/total_n*100:6.1f}% {c/n*100:7.1f}% {n-c:7d}")

    print("\n=== 오류가 전체 오류에서 차지하는 비중 ===")
    total_err = total_n - total_correct
    for kind, v in sorted(by_type.items(), key=lambda x: -(x[1]["n"] - x[1]["correct"])):
        err = v["n"] - v["correct"]
        if err == 0:
            continue
        print(f"  {kind:16s}: {err:5d}개 ({err/total_err*100:5.1f}% of 전체오류)")

    print("\n=== 오류 샘플 (유형별 최대 8개) ===")
    shown = defaultdict(int)
    for kind, exp, pred in errors:
        if shown[kind] >= 8:
            continue
        shown[kind] += 1
        print(f"  [{kind}] GT={exp!r}  PRED={pred!r}")


if __name__ == "__main__":
    main()
