"""LabelLens OCR - Tesseract/EasyOCR/PaddleOCR/docTR 4개 엔진 공통 실행 래퍼.

엔진별 초기화·호출 방식이 제각각이라, 모든 엔진을 동일한 인터페이스
(run_engine / run_all_engines)로 감싸서 predict_module.py와 benchmark_ocr.py가
엔진 종류에 상관없이 같은 방식으로 결과(text, elapsed_ms, ok)를 받게 한다.
"""
import os
import time
import traceback

import numpy as np
from PIL import Image

ENGINE_NAMES = ["tesseract", "easyocr", "paddleocr", "doctr"]

_MODULE_BY_ENGINE = {
    "tesseract": "pytesseract",
    "easyocr": "easyocr",
    "paddleocr": "paddleocr",
    "doctr": "doctr",
}

_reader_cache = {}


def check_engine_availability() -> dict:
    """4개 엔진 각각의 설치(임포트 가능) 여부를 {엔진명: bool} 형태로 반환합니다."""
    availability = {}
    for name, module_name in _MODULE_BY_ENGINE.items():
        try:
            __import__(module_name)
            availability[name] = True
        except Exception:
            availability[name] = False
    return availability


def _tesseract_lang(language: str) -> str:
    mapping = {"ko": "kor", "kor": "kor", "en": "eng", "eng": "eng"}
    parts = [mapping.get(part.strip(), part.strip()) for part in language.split("+")]
    return "+".join(dict.fromkeys(parts))


def _easyocr_langs(language: str) -> tuple:
    mapping = {"kor": "ko", "ko": "ko", "eng": "en", "en": "en"}
    parts = [mapping.get(part.strip(), part.strip()) for part in language.split("+")]
    return tuple(dict.fromkeys(parts))


def _paddleocr_lang(language: str) -> str:
    mapping = {"kor": "korean", "ko": "korean", "eng": "en", "en": "en"}
    primary = language.split("+")[0].strip()
    return mapping.get(primary, "korean")


def _get_easyocr_reader(languages: tuple, gpu: bool):
    import easyocr

    key = ("easyocr", languages, gpu)
    if key not in _reader_cache:
        _reader_cache[key] = easyocr.Reader(list(languages), gpu=gpu)
    return _reader_cache[key]


# LabelLens 화장품 라벨 코퍼스로 fine-tuning한 인식(rec) 모델.
# 빌드 시 user-values.yaml의 copy_folder_list로 복제되는 경로라 파일이 없을 수도 있어
# (예: 이 폴더가 아직 준비 안 된 개발환경) 존재할 때만 사용하고, 없으면 기본 사전학습 모델로 폴백한다.
_FINETUNED_KOREAN_REC_DIR = os.path.join(
    os.path.dirname(__file__), "models", "labellens_korean_rec"
)
_FINETUNED_KOREAN_REC_NAME = "korean_PP-OCRv5_mobile_rec"


def _get_paddleocr_reader(lang: str, gpu: bool):
    from paddleocr import PaddleOCR

    key = ("paddleocr", lang, gpu)
    if key not in _reader_cache:
        kwargs = {
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        }
        if lang == "korean" and os.path.isdir(_FINETUNED_KOREAN_REC_DIR):
            # fine-tuned 모델을 쓸 때는 model_dir이 lang을 무시하므로 lang 대신
            # 모델명을 명시해야 한다 (그렇지 않으면 다른 기본 모델과 매칭 에러가 남).
            kwargs["text_recognition_model_name"] = _FINETUNED_KOREAN_REC_NAME
            kwargs["text_recognition_model_dir"] = _FINETUNED_KOREAN_REC_DIR
        else:
            kwargs["lang"] = lang
        if gpu:
            kwargs["device"] = "gpu:0"
        else:
            # enable_mkldnn=False: 이 환경의 CPU용 paddlepaddle이 oneDNN 백엔드로 PP-OCRv5
            # 모델을 못 돌리고 NotImplementedError를 내는 이슈가 있어 명시적으로 꺼둔다.
            # (GPU 경로는 oneDNN을 안 타서 이 옵션이 필요 없다.)
            kwargs["enable_mkldnn"] = False
        _reader_cache[key] = PaddleOCR(**kwargs)
    return _reader_cache[key]


def _get_paddleocr_rec_only(lang: str, gpu: bool):
    """검출(detection) 없이 인식(recognition)만 수행하는 PaddleOCR 예측기.

    이미 한 단어/문구로 잘라낸 크롭 이미지(크롭 단위 벤치마크 등)에 전체
    파이프라인(_get_paddleocr_reader)을 쓰면, 범용 검출기가 크롭을 다시 여러
    조각으로 재분할해 결과가 줄바꿈으로 쪼개지는 오검출이 발생한다. 프로덕션
    (predict_module.py)은 전체 사진을 다루므로 검출이 필요해 이 함수를 쓰지
    않는다 — 크롭 단위 평가 스크립트 전용.
    """
    from paddleocr import TextRecognition

    key = ("paddleocr_rec_only", lang, gpu)
    if key not in _reader_cache:
        kwargs = {}
        if lang == "korean" and os.path.isdir(_FINETUNED_KOREAN_REC_DIR):
            kwargs["model_name"] = _FINETUNED_KOREAN_REC_NAME
            kwargs["model_dir"] = _FINETUNED_KOREAN_REC_DIR
        else:
            kwargs["model_name"] = _FINETUNED_KOREAN_REC_NAME
        if gpu:
            kwargs["device"] = "gpu:0"
        else:
            kwargs["enable_mkldnn"] = False
        _reader_cache[key] = TextRecognition(**kwargs)
    return _reader_cache[key]


def _run_paddleocr_rec_only(image: Image.Image, language: str, gpu: bool) -> str:
    model = _get_paddleocr_rec_only(_paddleocr_lang(language), gpu)
    result = model.predict(np.array(image.convert("RGB")))
    if not result:
        return ""
    return result[0].get("rec_text", "") or ""


def _get_doctr_model(gpu: bool):
    from doctr.models import ocr_predictor

    key = ("doctr", gpu)
    if key not in _reader_cache:
        model = ocr_predictor(pretrained=True)
        if gpu:
            model = model.cuda()
        _reader_cache[key] = model
    return _reader_cache[key]


def _run_tesseract(image: Image.Image, language: str, gpu: bool) -> str:
    import pytesseract

    return pytesseract.image_to_string(image, lang=_tesseract_lang(language))


def _run_easyocr(image: Image.Image, language: str, gpu: bool) -> str:
    reader = _get_easyocr_reader(_easyocr_langs(language), gpu)
    lines = reader.readtext(np.array(image.convert("RGB")), detail=0, paragraph=True)
    return "\n".join(lines)


def _run_paddleocr(image: Image.Image, language: str, gpu: bool) -> str:
    reader = _get_paddleocr_reader(_paddleocr_lang(language), gpu)
    result = reader.predict(np.array(image.convert("RGB")))
    lines = []
    for page in result or []:
        lines.extend(page.get("rec_texts", []))
    return "\n".join(lines)


def _run_doctr(image: Image.Image, language: str, gpu: bool) -> str:
    # docTR 기본 사전학습 모델은 라틴 문자 위주라 한국어 인식률이 낮다.
    # 4개 엔진 비교 결과에서 이 특성 자체가 유의미한 데이터가 된다.
    model = _get_doctr_model(gpu)
    result = model([np.array(image.convert("RGB"))])
    lines = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                lines.append(" ".join(word.value for word in line.words))
    return "\n".join(lines)


_RUNNERS = {
    "tesseract": _run_tesseract,
    "easyocr": _run_easyocr,
    "paddleocr": _run_paddleocr,
    "doctr": _run_doctr,
    # 크롭 단위 평가 전용(검출 생략). ENGINE_NAMES에는 포함하지 않는다 -
    # run_all_engines()의 기본 4엔진 비교(전체 사진 대상)엔 필요 없다.
    "paddleocr_rec": _run_paddleocr_rec_only,
}


def run_engine(
    engine: str, image: Image.Image, language: str = "kor+eng", gpu: bool = False
) -> dict:
    """지정한 엔진 하나로 OCR을 실행해 텍스트·소요시간·성공여부를 반환합니다."""
    if engine not in _RUNNERS:
        raise ValueError(f"지원하지 않는 엔진입니다: {engine} (지원: {list(_RUNNERS)})")

    start = time.perf_counter()
    try:
        text = _RUNNERS[engine](image, language, gpu)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "engine": engine,
            "ok": True,
            "text": text.strip(),
            "elapsed_ms": round(elapsed_ms, 1),
            "error": None,
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        traceback.print_exc()
        return {
            "engine": engine,
            "ok": False,
            "text": "",
            "elapsed_ms": round(elapsed_ms, 1),
            "error": str(e),
        }


def run_all_engines(
    image: Image.Image,
    language: str = "kor+eng",
    engines: list = None,
    gpu: bool = False,
) -> list:
    """설치된 엔진(또는 지정한 engines 목록)을 모두 실행해 결과 리스트를 반환합니다.

    미설치 엔진은 건너뛰지 않고 ok=False, error="엔진 미설치"로 채워 반환하므로,
    호출 측에서 설치 상태를 그대로 확인할 수 있다 (미설치 엔진이 있어도 나머지는 정상 동작).
    """
    availability = check_engine_availability()
    target_engines = engines or ENGINE_NAMES
    results = []
    for name in target_engines:
        if not availability.get(name, False):
            results.append(
                {
                    "engine": name,
                    "ok": False,
                    "text": "",
                    "elapsed_ms": 0.0,
                    "error": "엔진 미설치",
                }
            )
            continue
        results.append(run_engine(name, image, language, gpu))
    return results
