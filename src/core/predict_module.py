import base64
import io
import os
import re
import sys
import traceback

from PIL import Image, ImageOps

import ocr_engines

# LabelLens OCR - 성분 토큰 분리용 구분자(쉼표류만).
# 단, 숫자와 숫자 사이의 쉼표는 성분명의 일부라 자르지 않는다.
#   "1,2-헥산다이올", "2,3-부탄다이올"  -> 한 성분
#   "하이드롤라이즈드하이알루로닉애씨드(1,000ppm)"  -> 자릿수 구분 쉼표
# 양쪽이 모두 숫자일 때만 구분자로 보지 않는다(앞뒤 중 하나라도 숫자가 아니면 자른다).
_INGREDIENT_SPLIT_PATTERN = re.compile(r"(?<!\d)[,，;]+|[,，;]+(?!\d)")

# message에 engine을 지정하지 않았을 때 사용하는 기본 엔진.
_DEFAULT_ENGINE = "paddleocr"

# 입력 사진의 최대 변 길이(px). 폰 카메라 사진은 12MP(4032px)까지 오는데, 그대로 넣으면
# PaddleOCR가 GPU 메모리 부족(OOM)으로 실패하고 CPU에서도 매우 느려진다. 라벨 글자를 읽는 데
# 2000px이면 충분해서 이 크기로 줄여 넣는다. 환경변수로 조정 가능.
_MAX_SIDE = int(os.getenv("LABELLENS_OCR_MAX_SIDE", "2000"))

# GPU 사용 여부. "auto"(기본)면 CUDA GPU가 보일 때만 쓰고, 없으면 자동으로 CPU로 떨어진다.
# 강제하려면 LABELLENS_OCR_GPU=1(켜기) / 0(끄기).
_GPU_SETTING = os.getenv("LABELLENS_OCR_GPU", "auto").strip().lower()
_gpu_resolved = None


def _use_gpu() -> bool:
    """이 환경에서 GPU를 쓸지 한 번만 판단하고 결과를 재사용합니다."""
    global _gpu_resolved
    if _gpu_resolved is not None:
        return _gpu_resolved

    if _GPU_SETTING in ("1", "true", "yes", "on"):
        _gpu_resolved = True
    elif _GPU_SETTING in ("0", "false", "no", "off"):
        _gpu_resolved = False
    else:
        try:
            import paddle

            _gpu_resolved = paddle.device.cuda.device_count() > 0
        except Exception:
            _gpu_resolved = False

    print(f"[LabelLens OCR] 실행 장치: {'GPU' if _gpu_resolved else 'CPU'}")
    return _gpu_resolved


def _apply_exif_orientation(image: Image.Image) -> Image.Image:
    """EXIF 회전 정보를 실제 픽셀에 반영합니다.

    폰 카메라는 센서 방향 그대로 저장하고 "돌려서 보라"는 EXIF Orientation 태그만
    따로 붙인다. 갤러리·메신저는 이 태그를 읽어 똑바로 보여주지만, PIL의 Image.open()은
    적용하지 않아서 그대로 넣으면 90도 누운 사진을 OCR하게 된다.
    (실제로 4032x3024 / Orientation=6 사진에서 글자가 전혀 다르게 읽혔다.)
    """
    fixed = ImageOps.exif_transpose(image)
    if fixed.size != image.size:
        print(f"[LabelLens OCR] EXIF 회전 보정: {image.size[0]}x{image.size[1]} "
              f"-> {fixed.size[0]}x{fixed.size[1]}")
    return fixed


def _fit_max_side(image: Image.Image) -> Image.Image:
    w, h = image.size
    if max(w, h) <= _MAX_SIDE:
        return image
    scale = _MAX_SIDE / max(w, h)
    resized = image.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    print(f"[LabelLens OCR] 입력 이미지 축소: {w}x{h} -> {resized.width}x{resized.height}")
    return resized


def init():
    """
    모델 로드를 비롯한 모듈 초기화 작업을 수행합니다.
    """
    try:
        print("모듈 초기화 함수가 실행되었습니다.")
        availability = ocr_engines.check_engine_availability()
        for name, installed in availability.items():
            print(f"[LabelLens OCR] 엔진 설치 상태 - {name}: {'OK' if installed else '미설치'}")

    except Exception as e:
        print("모듈 초기화 중 에러가 발생하였습니다.")
        print(str(e))
        traceback.print_exc()
        sys.exit(1)


def _load_image(message: dict) -> Image.Image:
    """message에서 이미지를 읽어 PIL Image로 반환합니다.

    - image_base64: base64로 인코딩된 이미지 문자열
    - image_path: 개발환경 내 로컬 테스트용 이미지 경로
    """
    if message.get("image_base64"):
        image_bytes = base64.b64decode(message["image_base64"])
        raw = Image.open(io.BytesIO(image_bytes))
    elif message.get("image_path"):
        raw = Image.open(message["image_path"])
    else:
        raise ValueError("message에 'image_base64' 또는 'image_path'가 필요합니다.")

    # 순서 주의: convert("RGB")가 EXIF를 떨어뜨리므로 회전 보정을 먼저 한다.
    return _fit_max_side(_apply_exif_orientation(raw).convert("RGB"))


def _split_ingredients(raw_text: str) -> list:
    """OCR 원문 텍스트를 쉼표 기준으로 분리해 성분 토큰 리스트로 반환합니다.

    라벨 인쇄상의 줄바꿈은 단어 중간에서 끊기는 경우가 많아(예: "…디\n카프레이트")
    구분자로 쓰지 않고 그대로 이어붙인 뒤, 실제 구분자인 쉼표로만 분리한다.
    리스트의 순서가 곧 전성분표 배합 순서(label_rank)에 대응합니다.
    """
    joined = raw_text.replace("\n", "")
    tokens = _INGREDIENT_SPLIT_PATTERN.split(joined)
    return [token.strip() for token in tokens if token.strip()]


def predict(
    message: dict,
    uuid_id: str,
    is_async_mode: str = "false",
    x_api_key: str = "",
    is_stream: str = "",
) -> dict:
    """
    화장품 전성분 라벨 이미지를 받아 OCR로 텍스트를 추출하고,
    쉼표/개행 기준으로 분리한 성분 토큰 리스트를 반환합니다.
    (표준 성분명 매칭·규제 조회는 이 모듈의 책임 범위가 아닙니다.)

    message["engine"]:
      - 미지정 시 기본 엔진(paddleocr) 하나로 실행
      - "tesseract" / "easyocr" / "paddleocr" / "doctr" 중 하나로 특정 엔진 지정
      - "all" 이면 4개 엔진을 모두 실행해 비교 결과를 반환 (미설치 엔진은 자동 건너뜀)
    """
    print("예측 함수가 실행되었습니다.")
    message["uuid"] = uuid_id

    try:
        image = _load_image(message)
        language = message.get("language", "kor+eng")
        engine = message.get("engine", _DEFAULT_ENGINE)

        if engine == "all":
            engine_results = ocr_engines.run_all_engines(
                image, language=language, gpu=_use_gpu()
            )
            data = {
                "engines": [
                    {
                        **result,
                        "ingredients": _split_ingredients(result["text"]) if result["ok"] else [],
                    }
                    for result in engine_results
                ]
            }
        else:
            result = ocr_engines.run_engine(
                engine, image, language=language, gpu=_use_gpu()
            )
            if not result["ok"]:
                raise RuntimeError(result["error"])
            ingredients = _split_ingredients(result["text"])
            data = {"ingredients": ingredients}

        status, message_text = 200, f"UUID {uuid_id} OCR 완료"
        # 상세 정보(엔진·처리시간·원문)는 응답 JSON에는 안 담고 서버 로그로만 남긴다.
        print(
            f"[LabelLens OCR] status={status} message={message_text} "
            f"engine={engine} elapsed_ms={result.get('elapsed_ms') if engine != 'all' else '-'} "
            f"raw_text={result.get('text') if engine != 'all' else '-'!r}"
        )
        return {
            "status": status,
            "message": message_text,
            "data": data,
        }
    except Exception as e:
        print(f"[-] OCR 처리 중 에러가 발생하였습니다: {str(e)}")
        traceback.print_exc()
        return {
            "status": 500,
            "message": f"UUID {uuid_id} OCR 실패: {str(e)}",
            "data": None,
        }


####################
# if use_batch_job #
####################


def run_job(env: str = "vfx") -> dict:
    """
    배치 작업이 실제 수행하는 함수입니다.
    '''if __name__=="__main__":'''
    하위에서 불러 사용하는 함수입니다.
    """
    from oneflowai import handler, minio_client, postgres, utils

    try:
        batch_req_id = os.getenv("BATCH_REQ_ID")
        pod = os.getenv("POD_NAME")

        req_data = postgres.select_row(
            "model.md_svc_batch_req_history",
            ["batch_req_data_url"],
            {"batch_req_id": batch_req_id},
            env=env,
        )

        # MinIO에서 요청 Payload JSON 파일 다운로드
        data_url = req_data["batch_req_data_url"]
        path = data_url.replace("s3://", "", 1)
        bucket, key = path.split("/", 1)

        downloaded_payload = minio_client.download_dict(object_name=key, bucket=bucket)
        uuid = downloaded_payload["uuid"]

        ##################################################################################
        # 실제 수행 함수 호출 (예시))
        # pipeline 실행부 코드 작성 & Payload 사용하여 처리
        async_mode = (
            True if os.getenv("ASYNC_MODE") == "true" else False
        )  # 비동기 요청(처리 시간 길 경우) 시 true, 동기 요청 시 false
        results = handler.send_request(
            api_key="", data=downloaded_payload, async_mode=async_mode
        )
        ##################################################################################
        ##################################################################################
        # 비동기 요청하는 경우에 아래 로직 추가 사용 (async_mode == "true")
        # handler 내 각 요청 마다 추가 해주어야 함
        ##################################################################################
        if async_mode:
            try:
                # Valkey에서 결과가 나올 때까지 대기
                result_key = results["data"]["result_key"]
                final_result = utils.wait_for_result_key(
                    result_key=result_key,
                )
                results = final_result
            except Exception as e:
                print(f"[-] Error in model handler process: {str(e)}")
                traceback.print_exc()
                results = None
        ##################################################################################

        # ✅ 성공 상태 업데이트
        postgres.update_row(
            "model.md_svc_batch_req_history",
            {
                "batch_req_status": "COMPLETED",
                "batch_req_run_pod_nm": pod,
                "batch_req_run_stts": results["status"],
            },
            {"batch_req_id": batch_req_id},
            env=env,
        )

        # # Job 결과 알림
        # send_notification(
        #     project_name=downloaded_payload["project_name"] if "project_name" in downloaded_payload else "",
        #     uuid=uuid,
        #     task_status=results["status"],
        #     save_path=downloaded_payload["save_path"] if "save_path" in downloaded_payload else None,
        #     tag_id=downloaded_payload["tag_id"] if "tag_id" in downloaded_payload else None,
        #     task_id=downloaded_payload["task_id"] if "task_id" in downloaded_payload else None,
        # )

        return {
            "status": 200,
            "message": f"UUID {uuid} Batch job completed successfully: Status {results['status']}",
            "data": results["data"],
        }

    except Exception as e:
        print(f"[-] Error in batch job process: {str(e)}")
        traceback.print_exc()

        batch_req_id = os.getenv("BATCH_REQ_ID")
        if batch_req_id:
            postgres.update_row(
                "model.md_svc_batch_req_history",
                {"batch_req_status": "FAILED", "batch_req_run_pod_nm": pod},
                {"batch_req_id": batch_req_id},
                env=env,
            )

        # # Job 실패 결과 알림
        # send_notification(
        #     project_name=downloaded_payload["project_name"] if "project_name" in downloaded_payload else "",
        #     uuid=uuid,
        #     task_status="FAILED",
        #     save_path=downloaded_payload["save_path"] if "save_path" in downloaded_payload else None,
        #     tag_id=downloaded_payload["tag_id"] if "tag_id" in downloaded_payload else None,
        #     task_id=downloaded_payload["task_id"] if "task_id" in downloaded_payload else None,
        # )

        return {
            "status": 500,
            "message": f"UUID {uuid} Batch job failed: {str(e)}",
            "data": None,
        }


if __name__ == "__main__":
    # 모듈 초기화
    init()

    # run_job 함수 실행
    result = run_job()

    # 결과 출력 및 적절한 종료 코드 설정
    if result and result.get("status") == 200:
        print("✅ Batch job completed successfully")
        print(result.get("data"))
        sys.exit(0)  # 성공적으로 종료
    else:
        print("❌ Batch job failed")
        print(
            f"Error: {result.get('message', 'Unknown error') if result else 'No result returned'}"
        )
        sys.exit(1)  # 실패로 종료
