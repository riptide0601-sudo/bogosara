import base64
import io
import os
import re
import sys
import traceback

from PIL import Image

import ocr_engines

# LabelLens OCR - 성분 토큰 분리용 구분자(쉼표류 + 개행). 실제 라벨 샘플 검증하며 보완 예정.
_INGREDIENT_SPLIT_PATTERN = re.compile(r"[,，;\n]+")

# message에 engine을 지정하지 않았을 때 사용하는 기본 엔진.
_DEFAULT_ENGINE = "paddleocr"


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
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if message.get("image_path"):
        return Image.open(message["image_path"]).convert("RGB")
    raise ValueError("message에 'image_base64' 또는 'image_path'가 필요합니다.")


def _split_ingredients(raw_text: str) -> list:
    """OCR 원문 텍스트를 쉼표/개행 기준으로 분리해 성분 토큰 리스트로 반환합니다.

    리스트의 순서가 곧 전성분표 배합 순서(label_rank)에 대응합니다.
    """
    tokens = _INGREDIENT_SPLIT_PATTERN.split(raw_text)
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
            engine_results = ocr_engines.run_all_engines(image, language=language)
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
            result = ocr_engines.run_engine(engine, image, language=language)
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
