# Callytics Dockerfile
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

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
    && rm -rf /var/lib/apt/lists/*

# Python 심볼릭 링크 생성
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# 작업 디렉토리 설정
WORKDIR /app

# pip 설정 (타임아웃 증가)
RUN pip config set global.timeout 300

# PyTorch CPU 버전 먼저 설치 (더 빠름)
RUN pip install --no-cache-dir torch==2.0.1+cpu torchaudio==2.0.1+cpu -f https://download.pytorch.org/whl/torch_stable.html

# 나머지 Python 의존성 설치
COPY requirements_minimal.txt .
RUN pip install --no-cache-dir -r requirements_minimal.txt

# omegaconf 추가 (NeMo 의존성)
RUN pip install --no-cache-dir omegaconf

# pyannote.audio 추가 (화자 분리)
RUN pip install --no-cache-dir pyannote.audio

# 한국어 처리 관련 패키지 설치 (안정적인 것만)
RUN pip install --no-cache-dir \
    konlpy \
    soynlp

# 모델 다운로드 스크립트 생성
RUN mkdir -p /app/models
COPY download_models.sh /app/
RUN chmod +x /app/download_models.sh

# 애플리케이션 코드 복사
COPY . /app/

# 필요한 디렉토리 생성
RUN mkdir -p /app/.temp /app/.db /app/logs /app/audio

# 포트 노출
EXPOSE 8000

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV CUDA_LAUNCH_BLOCKING=1

# 실행 명령 (main_enhanced.py로 변경)
CMD ["python", "main_enhanced.py"]
