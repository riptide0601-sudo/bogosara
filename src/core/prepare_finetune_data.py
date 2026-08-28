"""
AI-Hub '056.의약품, 화장품 패키징 OCR 데이터'(복구된 843장)를
PaddleOCR 검출(det)/인식(rec) fine-tuning 라벨 포맷으로 변환한다.

전제:
- /home/jovyan/data/aihub_cosmetics_ocr/images/ 에 이미지가 있음
- VL1.zip(라벨 zip)에서 이미지와 매칭되는 JSON만 사용

사용법:
    python prepare_finetune_data.py
"""
import json
import random
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

VL1_PATH = Path(
    "/tmp/claude-1000/-home-jovyan/bdf3f003-c7b7-4367-be1e-9158c50ec1dc/scratchpad/dataset_repair/VL1.zip"
)
DATA_ROOT = Path("/home/jovyan/data/aihub_cosmetics_ocr")
IMAGES_DIR = DATA_ROOT / "images"

DET_DIR = DATA_ROOT / "det"
REC_DIR = DATA_ROOT / "rec"
REC_CROPS_DIR = REC_DIR / "crop_images"

VAL_RATIO = 0.15
SEED = 42


def load_matched_records():
    z = zipfile.ZipFile(VL1_PATH)
    available = {p.name for p in IMAGES_DIR.iterdir()}
    json_names = [
        n
        for n in z.namelist()
        if n.startswith("result/cosmetics/annotations/") and n.endswith(".json")
    ]

    records = []
    for jn in json_names:
        obj = json.loads(z.read(jn))
        img_name = obj.get("name")
        if img_name in available:
            records.append(obj)
    return records


def to_det_label(obj) -> str:
    """PaddleOCR det 라벨 한 줄: images/xxx.jpg\t[{"transcription":..,"points":[[x,y]x4]}, ...]"""
    boxes = []
    for ann in obj.get("annotations", []):
        for poly in ann.get("polygons", []):
            text = (poly.get("text") or "").strip()
            points = poly.get("points")
            if not text or not points:
                continue
            # PaddleOCR det은 점 4개(사각형) 기준 포맷을 기대. 4개가 아니면 스킵.
            if len(points) != 4:
                continue
            rounded = [[round(x, 1), round(y, 1)] for x, y in points]
            boxes.append({"transcription": text, "points": rounded})
    if not boxes:
        return None
    img_name = obj["name"]
    return f"images/{img_name}\t{json.dumps(boxes, ensure_ascii=False)}"


def crop_polygon(image: np.ndarray, points):
    """4점 폴리곤을 투시변환으로 반듯하게 잘라낸다 (기울어진 사각형 보정).

    PaddleOCR 본체의 get_rotate_crop_image(tools/infer/utility.py)와 동일하게
    동작시킨다. 특히 세로로 긴 크롭을 반시계 90도 회전시키는 처리가 핵심인데,
    화장품 용기는 성분표를 옆으로 눕혀 인쇄한 경우가 많아 이 데이터셋 크롭의
    약 44%가 세로로 길다. 인식 모델은 크롭을 48x320(가로로 긴 형태)에 맞춰
    리사이즈하므로, 눕힌 채로 넣으면 글자가 뭉개져 인식이 무너진다.
    (실측: 회전 미적용 85.9% -> 적용 95.6%)

    추론 파이프라인(PaddleOCR)은 이미 이 회전을 하고 들어오므로, 학습 데이터도
    같은 규칙으로 만들어야 학습/추론 입력이 일치한다.
    """
    pts = np.array(points, dtype=np.float32)
    w = int(max(np.linalg.norm(pts[0] - pts[1]), np.linalg.norm(pts[2] - pts[3])))
    h = int(max(np.linalg.norm(pts[1] - pts[2]), np.linalg.norm(pts[3] - pts[0])))
    if w < 4 or h < 4:
        return None
    dst = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(pts, dst)
    crop = cv2.warpPerspective(
        image,
        matrix,
        (w, h),
        borderMode=cv2.BORDER_REPLICATE,
        flags=cv2.INTER_CUBIC,
    )
    crop_h, crop_w = crop.shape[:2]
    if crop_h * 1.0 / crop_w >= 1.5:
        crop = np.rot90(crop)
    return np.ascontiguousarray(crop)


def build_rec_crops(obj, img_bgr, rec_lines: list, crop_counter: list):
    img_name_stem = Path(obj["name"]).stem
    for ann in obj.get("annotations", []):
        for poly in ann.get("polygons", []):
            text = (poly.get("text") or "").strip()
            points = poly.get("points")
            if not text or not points or len(points) != 4:
                continue
            crop = crop_polygon(img_bgr, points)
            if crop is None:
                continue
            crop_counter[0] += 1
            crop_name = f"{img_name_stem}_{crop_counter[0]}.jpg"
            cv2.imwrite(str(REC_CROPS_DIR / crop_name), crop)
            rec_lines.append(f"crop_images/{crop_name}\t{text}")


def main():
    DET_DIR.mkdir(parents=True, exist_ok=True)
    REC_CROPS_DIR.mkdir(parents=True, exist_ok=True)

    records = load_matched_records()
    print(f"매칭된 이미지+라벨 쌍: {len(records)}개")

    random.seed(SEED)
    random.shuffle(records)
    n_val = max(1, int(len(records) * VAL_RATIO))
    val_records = records[:n_val]
    train_records = records[n_val:]
    print(f"train {len(train_records)}개 / val {len(val_records)}개 (seed={SEED})")

    det_train_lines, det_val_lines = [], []
    rec_train_lines, rec_val_lines = [], []
    crop_counter = [0]
    skipped_unreadable = 0

    for split_name, split_records, det_lines, rec_lines in [
        ("train", train_records, det_train_lines, rec_train_lines),
        ("val", val_records, det_val_lines, rec_val_lines),
    ]:
        for obj in split_records:
            det_line = to_det_label(obj)
            if det_line:
                det_lines.append(det_line)

            img_path = IMAGES_DIR / obj["name"]
            pil_img = Image.open(img_path).convert("RGB")
            img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            if img_bgr is None:
                skipped_unreadable += 1
                continue
            build_rec_crops(obj, img_bgr, rec_lines, crop_counter)

    (DET_DIR / "train_label.txt").write_text("\n".join(det_train_lines), encoding="utf-8")
    (DET_DIR / "val_label.txt").write_text("\n".join(det_val_lines), encoding="utf-8")
    (REC_DIR / "train_label.txt").write_text("\n".join(rec_train_lines), encoding="utf-8")
    (REC_DIR / "val_label.txt").write_text("\n".join(rec_val_lines), encoding="utf-8")

    print(f"\ndet: train {len(det_train_lines)}줄 / val {len(det_val_lines)}줄 -> {DET_DIR}")
    print(f"rec: train {len(rec_train_lines)}개 크롭 / val {len(rec_val_lines)}개 크롭 -> {REC_DIR}")
    if skipped_unreadable:
        print(f"읽기 실패로 스킵된 이미지: {skipped_unreadable}개")


if __name__ == "__main__":
    main()
