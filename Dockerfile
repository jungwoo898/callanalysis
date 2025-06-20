# 빌드 스테이지
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04 AS builder

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=1000
ENV PIP_RETRY=5
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
    libicu-dev \
    htop \
    iotop \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.10 /usr/bin/python

# 작업 디렉토리 설정
WORKDIR /build

# pip 업그레이드
RUN python -m pip install --upgrade pip setuptools wheel

# PyTorch 설치 (CUDA 버전)
RUN pip install torch==2.0.0+cu118 torchaudio==2.0.0+cu118 -f https://download.pytorch.org/whl/torch_stable.html

# 기본 의존성 먼저 설치 (안정적인 패키지들)
RUN pip install \
    numpy==1.24.0 \
    scipy==1.10.0 \
    requests==2.32.3 \
    python-dotenv==1.0.1 \
    pyyaml==6.0.2 \
    omegaconf==2.3.0 \
    watchdog==6.0.0 \
    pydub==0.25.1 \
    soundfile==0.12.1 \
    librosa==0.10.2.post1 \
    noisereduce==3.0.3 \
    nltk==3.9.1 \
    openai==1.57.0 \
    aiohttp==3.9.1 \
    httpx==0.25.2 \
    huggingface-hub==0.19.4 \
    accelerate==0.26.0 \
    transformers==4.30.0 \
    IPython==8.30.0 \
    treetable==0.2.5 \
    gradio==4.19.2 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    psutil==5.9.5 \
    cython==3.0.6

# 대용량/복잡한 패키지들 단계별 설치
RUN pip install faster-whisper==1.1.0

# demucs 설치 (메모리 사용량 높음)
RUN pip install demucs==4.0.1

# nemo_toolkit 설치 (Cython 의존성 해결 후)
RUN pip install "nemo_toolkit[asr]==1.20.0"

# pyannote.audio 설치
RUN pip install pyannote.audio==3.3.2

# MPSENet 설치
RUN pip install MPSENet==1.0.3

# CTC Forced Aligner 설치
RUN pip install ctc-forced-aligner==1.0.2

# 추가 의존성 설치
RUN pip install pandas==2.3.0 matplotlib==3.10.3 scikit-learn==1.7.0

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
ENV DEVICE=cuda
ENV COMPUTE_TYPE=float16

# API 관련 환경 변수 (기본값 설정)
ENV OPENAI_API_KEY=""
ENV AZURE_OPENAI_API_KEY=""
ENV AZURE_OPENAI_ENDPOINT=""
ENV HUGGINGFACE_API_TOKEN=""

# 기본 패키지 설치
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-minimal \
    python3-pip \
    git \
    ffmpeg \
    libsndfile1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.10 /usr/bin/python

# Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages/
COPY --from=builder /usr/local/bin /usr/local/bin/

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/.temp /app/.db /app/logs /app/audio /app/models /app/.data/input \
    && chmod -R 755 /app/.temp /app/.db /app/audio /app/models /app/.data \
    && chmod -R 777 /app/logs

# 로그 로테이션 설정
RUN echo '"/app/logs/*.log" {\n\
    daily\n\
    rotate 30\n\
    compress\n\
    delaycompress\n\
    missingok\n\
    notifempty\n\
    create 0666 root root\n\
    size 100M\n\
}' > /etc/logrotate.d/callytics

# 임시 파일 정리 스크립트
RUN echo '#!/bin/sh\nfind /app/.temp -type f -mtime +7 -delete' > /app/cleanup.sh \
    && chmod +x /app/cleanup.sh

# 애플리케이션 파일 복사
COPY . /app/

# 시작 스크립트 수정 (API 키 검증 추가)
RUN echo '#!/bin/bash\n\
trap "exit" TERM\n\
trap "kill 0" INT\n\
echo "Checking CUDA availability..."\n\
if python -c "import torch; print(f\"CUDA available: {torch.cuda.is_available()}, Device count: {torch.cuda.device_count()}\")" 2>/dev/null; then\n\
    echo "GPU mode: CUDA is available - Using GPU for optimal performance"\n\
    export DEVICE=cuda\n\
    export COMPUTE_TYPE=float16\n\
else\n\
    echo "WARNING: CUDA not available, falling back to CPU mode (slower performance)"\n\
    export CUDA_VISIBLE_DEVICES=""\n\
    export DEVICE=cpu\n\
    export COMPUTE_TYPE=int8\n\
fi\n\
echo "Checking API configuration..."\n\
if [ -n "$OPENAI_API_KEY" ]; then\n\
    echo "✅ OpenAI API key is configured"\n\
elif [ -n "$AZURE_OPENAI_API_KEY" ] && [ -n "$AZURE_OPENAI_ENDPOINT" ]; then\n\
    echo "✅ Azure OpenAI API is configured"\n\
elif [ -n "$HUGGINGFACE_API_TOKEN" ]; then\n\
    echo "✅ Hugging Face API token is configured"\n\
else\n\
    echo "⚠️ WARNING: No API keys configured. Please set at least one of:"\n\
    echo "   - OPENAI_API_KEY"\n\
    echo "   - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT"\n\
    echo "   - HUGGINGFACE_API_TOKEN"\n\
fi\n\
python main.py\n' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# 포트 노출
EXPOSE 8000

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 실행 명령
ENTRYPOINT ["/app/entrypoint.sh"]
