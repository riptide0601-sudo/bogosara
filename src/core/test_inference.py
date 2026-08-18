from predict_module import init, predict

########
# 1. 본 파일은 입력 데이터에 따른 예상 실행 결과를 테스트해보기 위한 파일입니다.
# 2. 기대하는 입력 구조에 맞게 데이터를 작성합니다.
# 3. python test_inference.py 명령어로 파이썬 파일을 실행하여 추론 동작 결과를 확인할 수 있습니다.
input_message = {"data": {"key": "field"}, "id": "user_id", "use_batch_job": False}
########

init()

response = predict(
    message=input_message, uuid_id="0001", is_async_mode="false", x_api_key="key"
)

print(response)
