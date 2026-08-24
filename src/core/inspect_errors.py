"""fine-tuned PaddleOCR가 검증 크롭에서 틀린 사례를 뽑아서 직접 확인하기 위한 스크립트.

라벨 자체가 이상한 건지(크롭이 잘못 잘렸거나 오탈자), 모델이 진짜 못 읽는 건지
구분하기 위한 진단용. GPU로 val_label.txt에서 N개 샘플을 뽑아 예측하고,
틀린 것만 골라 GT/예측/추정 원인을 출력한다.
"""
import random
from pathlib import Path

from PIL import Image

from ocr_engines import run_engine

REC_DIR = Path(__file__).parent.parent.parent / "data" / "aihub_cosmetics_ocr" / "rec"
VAL_LABEL_PATH = REC_DIR / "val_label.txt"

SAMPLE_SIZE = 300
SEED = 7
MAX_SHOW = 60


def load_val_pairs():
    pairs = []
    for line in VAL_LABEL_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rel_path, text = line.split("\t", 1)
        pairs.append((rel_path, text))
    return pairs


def guess_cause(expected: str, predicted: str) -> str:
    if not predicted:
        return "빈 예측"
    if len(predicted) != len(expected):
        return f"길이 다름(GT {len(expected)} / 예측 {len(predicted)})"
    diff = sum(1 for a, b in zip(expected, predicted) if a != b)
    if diff <= 2:
        return f"글자 {diff}개만 다름(유사)"
    return "전혀 다름"


def main():
    pairs = load_val_pairs()
    random.seed(SEED)
    sample = random.sample(pairs, min(SAMPLE_SIZE, len(pairs)))
    print(f"샘플 {len(sample)}개 중 오답 최대 {MAX_SHOW}개 출력\n")

    shown = 0
    checked = 0
    for rel_path, expected in sample:
        image = Image.open(REC_DIR / rel_path).convert("RGB")
        result = run_engine("paddleocr_rec", image, gpu=True)
        checked += 1
        if not result["ok"]:
            continue
        predicted = result["text"].strip()
        expected_s = expected.strip()
        if predicted == expected_s:
            continue
        shown += 1
        print(f"[{shown}] {rel_path}")
        print(f"  GT  : {expected_s}")
        print(f"  PRED: {predicted}")
        print(f"  추정: {guess_cause(expected_s, predicted)}")
        print()
        if shown >= MAX_SHOW:
            break

    print(f"\n검사 {checked}개 중 오답 {shown}개 출력")


if __name__ == "__main__":
    main()
