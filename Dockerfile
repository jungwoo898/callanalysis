# 빌드 스테이지
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04 as builder

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=1000
ENV PIP_RETRY=5
ENV PIP_NO_CACHE_DIR=0
ENV TORCH_CUDA_ARCH_LIST="6.0 6.1 7.0 7.5 8.0 8.6"

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    portaudio19-dev \
    build-essential \
    cmake \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.10 /usr/bin/python

# 작업 디렉토리 설정
WORKDIR /build

# pip 업그레이드 및 캐시 설정
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip config set global.cache-dir /build/.pip-cache

# requirements.txt 복사 및 의존성 설치 (재시도 로직 포함)
COPY requirements.txt .
RUN for i in {1..3}; do \
        pip install -r requirements.txt && break || \
        echo "Retry $i/3..." && \
        sleep 5; \
    done

# 실행 스테이지
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTHONPATH=/app
ENV CUDA_LAUNCH_BLOCKING=1
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb=512
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV TORCH_CUDA_ARCH_LIST="6.0 6.1 7.0 7.5 8.0 8.6"

# 기본 패키지 설치
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-minimal \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.10 /usr/bin/python

# Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/.temp /app/.db /app/logs /app/audio /app/models \
    && chmod -R 755 /app/.temp /app/.db /app/logs /app/audio /app/models

# 로그 로테이션 설정
RUN echo '"/app/logs/*.log" {\n\
    daily\n\
    rotate 7\n\
    compress\n\
    delaycompress\n\
    missingok\n\
    notifempty\n\
    create 0644 root root\n\
}' > /etc/logrotate.d/callytics

# 임시 파일 정리 스크립트
RUN echo '#!/bin/sh\nfind /app/.temp -type f -mtime +7 -delete' > /app/cleanup.sh \
    && chmod +x /app/cleanup.sh

# 애플리케이션 파일 복사
COPY . /app/

# 시작 스크립트 생성
RUN echo '#!/bin/bash\n\
trap "exit" TERM\n\
trap "kill 0" INT\n\
python -c "import torch; print(f\"CUDA available: {torch.cuda.is_available()}, Device count: {torch.cuda.device_count()}\")" || exit 1\n\
exec python test_audio_analysis.py\n' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# 포트 노출
EXPOSE 8000

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 실행 명령
ENTRYPOINT ["/app/entrypoint.sh"]
