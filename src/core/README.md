# LabelLens OCR 모듈

화장품 전성분 라벨을 촬영하면 OCR로 성분 텍스트를 추출하는 **LabelLens** 프로젝트의 OCR 파트.
AI SW Wave 트랙 A(OCR Multi-Engine)의 인프라(FastAPI/Docker, 4개 OCR 엔진 비교)를 화장품 라벨 시나리오로 재설계했다.

## 담당 범위

이 모듈은 **OCR 텍스트 추출 + 쉼표/개행 기준 성분 분리**까지만 담당한다.

| 포함 | 제외 (팀원 백엔드 담당) |
|---|---|
| 이미지 → OCR 텍스트 추출 | 표준 성분명 매칭 (`INGREDIENT` 테이블 대조) |
| 쉼표/개행 기준 성분 토큰 분리 (순서 보존) | 배합목적(`PURPOSE`) 조회 |
| | 사용금지·제한 원료 규제 조회 |
| | LLM 요약 생성 |

팀원이 작성한 ERD(`PRODUCT_INGREDIENT.label_rank`)를 보면 성분 순서 정보가 필요해서, 분리까지는 이 모듈이 맡고 그 뒤 DB 조회가 필요한 매칭부터는 백엔드가 담당하는 것으로 경계를 정했다.

### `predict()` 입출력 계약

```python
# 입력 (message)
{
    "image_base64": "...",       # 또는 "image_path": "samples/xxx.jpg"
    "language": "kor+eng",       # 생략 가능, 기본값
    "engine": "paddleocr",       # 생략 시 기본 엔진 / "tesseract" / "easyocr" / "doctr" / "all"
    "use_batch_job": False,
}

# 출력 (data) - engine 지정 시
{
    "engine": "paddleocr",
    "elapsed_ms": 8499.8,
    "raw_text": "전성분: 정제수, 글리세린, ...",
    "ingredients": ["정제수", "글리세린", ...],  # 리스트 순서 = label_rank
}

# 출력 (data) - engine="all" (비교 모드)
{
    "engines": [
        {"engine": "tesseract", "ok": True, "text": "...", "elapsed_ms": 337.9, "ingredients": [...]},
        ...
    ]
}
```

## 파일 구조

```
src/core/
├── predict_module.py   # 추론 진입점 (init/predict) - 플랫폼이 이 함수들을 직접 호출
├── ocr_engines.py       # 4개 엔진 공통 실행 래퍼 (run_engine/run_all_engines/check_engine_availability)
├── benchmark_ocr.py      # samples/ 이미지로 4개 엔진 비교 + 그래프 생성 (개발용 스크립트)
├── test_inference.py    # 로컬 동작 확인용
├── samples/              # 라벨 테스트 이미지 + ground_truth.json (정답 텍스트)
└── results/              # benchmark_ocr.py 실행 결과 (그래프 PNG, 원본 JSON) - git 추적 제외
```

## 진행 상황

- **1단계 (완료)** — 단일 엔진(Tesseract) 최소 파이프라인. `init()`/`predict()` 동작 확인.
- **2단계 (완료)** — EasyOCR/PaddleOCR/docTR 추가, 4개 엔진 비교 구조(`ocr_engines.py`) + 벤치마크 스크립트(`benchmark_ocr.py`) 구축.
- **3단계 (진행 중)** — 실제 라벨 샘플로 정량 평가. 샘플 1장(`torriden.jpg`) 검증 완료, 샘플 추가 예정.
- **4단계 (예정)** — `requirements.txt`/`Dockerfile` 최종 정리 후 `model/ci` 빌드 검증.

## 벤치마크 결과 (실제 라벨 사진 1장, torriden.jpg 기준)

| 엔진 | 처리시간 | 정확도(재현율) |
|---|---|---|
| tesseract | 7.5s | 80.9% |
| **paddleocr** | 98.0s | **82.0%** |
| easyocr | 328.7s (≈5.5분) | 40.3% |
| doctr | 73.7s | 3.8% |

결과 그래프: `results/engine_speed.png`, `results/engine_accuracy.png`, PPT 첨부용 합성 이미지 `results/ppt_summary.png`.
발행된 결과 페이지: https://claude.ai/code/artifact/feaadb2e-ea33-4c2f-90f8-af6e1e6c6681

**핵심 발견**
- PaddleOCR와 Tesseract는 정확도가 거의 동률이지만, Tesseract가 약 13배 빠르다. 실사용에서 속도가 중요하면 Tesseract가 유리할 수 있다.
- EasyOCR는 정확도도 낮은데 처리시간이 압도적으로 느려(5.5분/장) 이번 시나리오엔 부적합해 보인다.
- docTR는 사전학습 모델이 라틴 문자 위주라 한글 라벨 인식이 사실상 안 된다(3.8%).
- fine-tuning 대상을 고를 때 정확도만이 아니라 이 속도 격차도 함께 고려해야 한다.

## 알아두면 좋은 이슈

- **PaddleOCR 3.x API 변경**: 2.x의 `ocr()` 대신 `predict()`를 쓰고, 결과는 `rec_texts` 키를 가진 dict 리스트로 반환된다.
- **PaddleOCR 3.x + CPU oneDNN 버그**: 이 환경의 CPU 추론에서 oneDNN 백엔드가 PP-OCRv5 모델과 호환되지 않아 `NotImplementedError`가 발생한다. `PaddleOCR(..., enable_mkldnn=False)`로 우회했다.
- **정확도 지표를 재현율 방식으로 변경**: 실제 라벨 사진에는 마케팅 문구·사용법 등 정답(전성분)과 무관한 텍스트가 훨씬 많이 섞여 있어, 전체 텍스트 대 정답을 단순 대칭 비교(`difflib.ratio()`)하면 점수가 실제 인식 품질과 무관하게 낮아진다. "정답 문자가 추출 텍스트 어딘가에 올바른 순서로 얼마나 포착됐는지"(재현율: `matched_chars / len(정답)`)로 측정하도록 `benchmark_ocr.py`의 `_accuracy()`를 수정했다.
- **엔진 설치 의존성**: Tesseract는 apt 패키지(`tesseract-ocr`, `tesseract-ocr-kor`)가 필요하고, 나머지 3개는 pip만으로 설치되지만 EasyOCR/docTR는 torch, PaddleOCR는 paddlepaddle을 끌어와 설치 용량이 크다(엔진당 수백MB~1GB). opencv 의존성 때문에 컨테이너에 `libgl1`, `libglib2.0-0`도 필요하다.

## 실행 방법

```bash
cd src/core

# 단일 이미지 동작 확인 (test_inference.py의 image_path를 실제 이미지로 수정)
python test_inference.py

# 4개 엔진 비교 벤치마크 (samples/ 폴더의 이미지 전체 대상)
python benchmark_ocr.py
```

`samples/ground_truth.json`에 `{"파일명": "정답 전성분 텍스트"}`를 추가하면 정확도 비교도 함께 나온다.

## 다음 단계

1. 라벨 샘플 추가 확보 (곡면 용기, 반사광, 저대비 등 다양한 촬영 조건 포함)
2. 위 벤치마크 결과를 바탕으로 fine-tuning 대상 엔진 결정 (속도 vs 정확도 트레이드오프 고려)
3. 화장품 라벨 특유의 어려움 대응 전처리 (기울기 보정, 대비 개선 등)
4. `requirements.txt`/`Dockerfile` 최종 점검 후 `model/ci` 빌드 검증
