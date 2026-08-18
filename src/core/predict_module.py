import os
import sys
import traceback

from oneflowai import handler, minio_client, postgres, utils
from oneflowai.fptr_util import send_notification
from oneflowai.orchestrator import generate_job


def init():
    """
    모델 로드를 비롯한 모듈 초기화 작업을 수행합니다.
    """
    try:
        print("모듈 초기화 함수가 실행되었습니다.")

    except Exception as e:
        print("모듈 초기화 중 에러가 발생하였습니다.")
        print(str(e))
        traceback.print_exc()
        sys.exit(1)


def predict(
    message: dict,
    uuid_id: str,
    is_async_mode: str = "false",
    x_api_key: str = "",
    is_stream: str = "",
) -> dict:
    """
    주어진 메시지를 기반으로 예측이나 메세지에 대한 처리를 수행합니다.
    결과는 dictionary 형태로 반환하는 것을 권장합니다.
    """
    print("예측 함수가 실행되었습니다.")
    message["uuid"] = uuid_id
    async_mode = True if is_async_mode == "true" else False

    if message["use_batch_job"]:  # 페이로드에 정의함
        env = "vfx"
        valkey_stream_key = os.getenv("VALKEY_STREAM_KEY")

        job_info = generate_job(
            env=env,
            payload=message,
            valkey_stream_key=valkey_stream_key,
            extra_values=[{"name": "ASYNC_MODE", "value": is_async_mode}],
        )  # minio 파일 저장, job 등록

        return {
            "status": 200,
            "message": f"UUID {uuid_id} job registered",
            "job_info": job_info,
        }
    else:
        # 메인 코드 실행 예시

        # 클러스터 내 다른 모델/서비스에 다시 요청해야 할 경우, 아래의 코드와 같이 oneflowai 라이브러리의 Handler를 사용하여 요청을 전송할 수 있습니다
        # response_data = handler.send_request(data=message, async_mode=async_mode) # execute handler

        response_status = 200
        response_message = f"UUID {uuid_id} job is succeded"
        response = {
            "status": response_status,
            "message": response_message,
            "data": {
                "result": "Hello World",
            },
        }
        return response


####################
# if use_batch_job #
####################


def run_job(env: str = "vfx") -> dict:
    """
    배치 작업이 실제 수행하는 함수입니다.
    '''if __name__=="__main__":'''
    하위에서 불러 사용하는 함수입니다.
    """
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
