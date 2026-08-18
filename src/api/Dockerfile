# ✅ 베이스 이미지를 입력합니다 (필요 시 변경 가능! 예: nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04)
FROM harbor.harbor.svc.cluster.local/base/python:3.11

# ✅ 빌드에 사용할 환경설정 값을 주입 및 설정합니다
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=ko_KR.UTF-8 \
    LANGUAGE=ko_KR:ko \
    LC_ALL=ko_KR.UTF-8 \
    PYTHONPATH=/root/src/core

# ✅ /app을 작업 디렉토리로 설정합니다. 시스템 코드의 정상적인 동작을 위해서 가급적 변경하지 않습니다.
WORKDIR /app

# ✅ 설치할 패키지가 있다면 아래의 영역에 추가합니다
RUN rm -rf /var/lib/apt/lists/* && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    vim curl wget sudo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ✅ 설치할 파이썬 패키지가 있다면 이 영역에 추가합니다
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

CMD ["/bin/sh -c", "sleep infinity"]