# Callytics Enhanced Docker 실행 가이드

## 사전 요구사항

### 1. Docker 및 Docker Compose 설치
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# macOS
brew install docker docker-compose

# Windows
# Docker Desktop 설치
```

### 2. NVIDIA Docker (GPU 사용 시)
```bash
# NVIDIA Container Toolkit 설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 3. AI 모델 준비
```bash
# AI 모델 폴더 생성
mkdir -p "AI 모델/model"

# 모델 파일들을 다음 경로에 배치:
# - AI 모델/model/openchat-3.5-0106-private/
# - AI 모델/model/Meta-Llama-3-8B-Instruct-private/
# - AI 모델/model/gemma-2b-it-private/
```

## 실행 방법

### 1. 빠른 시작
```bash
# 실행 스크립트 사용
chmod +x run_docker.sh
./run_docker.sh
```

### 2. 수동 실행
```bash
# 필요한 디렉토리 생성
mkdir -p audio data logs temp

# Docker Compose로 실행
docker-compose up --build
```

### 3. CPU 전용 실행
```bash
# GPU가 없는 환경에서 실행
docker-compose -f docker-compose.yml -f docker-compose.cpu.yml up --build
```

## 사용 방법

### 1. 오디오 파일 처리
```bash
# 오디오 파일을 ./audio/ 디렉토리에 복사
cp your_audio_file.wav ./audio/

# 컨테이너 내에서 실행
docker exec -it callytics-enhanced python main_enhanced.py ./audio/your_audio_file.wav
```

### 2. 배치 처리
```bash
# 여러 파일 처리
for file in ./audio/*.wav; do
    docker exec -it callytics-enhanced python main_enhanced.py "$file"
done
```

### 3. 개발 모드
```bash
# 코드 변경사항이 실시간으로 반영되는 개발 모드
docker-compose --profile dev up --build
```

## 설정 파일

### 1. 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# 필요한 API 키 설정
OPENAI_API_KEY=your_openai_api_key
AZURE_OPENAI_API_KEY=your_azure_api_key
HUGGINGFACE_TOKEN=your_huggingface_token
```

### 2. 모델 경로 설정
```yaml
# config/config_enhanced.yaml 수정
models:
  korean_models:
    openchat:
      base_model_name: "/app/AI 모델/model/openchat-3.5-0106-private"
```

## 모니터링 및 로그

### 1. 로그 확인
```bash
# 실시간 로그 확인
docker-compose logs -f callytics

# 특정 컨테이너 로그
docker logs callytics-enhanced
```

### 2. 성능 모니터링
```bash
# GPU 사용량 확인 (GPU 모드)
nvidia-smi

# 컨테이너 리소스 사용량
docker stats callytics-enhanced
```

## 문제 해결

### 1. GPU 관련 문제
```bash
# NVIDIA Docker 확인
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# GPU 접근 권한 확인
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

### 2. 메모리 부족
```bash
# Docker 메모리 제한 설정
# /etc/docker/daemon.json
{
  "default-shm-size": "2G",
  "default-memory": "8G"
}
```

### 3. 포트 충돌
```bash
# 포트 변경
# docker-compose.yml 수정
ports:
  - "8001:8000"  # 호스트 포트를 8001로 변경
```

## 데이터 백업

### 1. 데이터베이스 백업
```bash
# 데이터베이스 백업
docker exec callytics-enhanced sqlite3 /app/.db/Callytics.sqlite ".backup /app/.db/backup_$(date +%Y%m%d_%H%M%S).sqlite"
```

### 2. 로그 백업
```bash
# 로그 파일 백업
docker cp callytics-enhanced:/app/logs ./backup_logs_$(date +%Y%m%d_%H%M%S)
```

## 성능 최적화

### 1. GPU 메모리 최적화
```yaml
# config/config_enhanced.yaml
runtime:
  device: "cuda"
  compute_type: "int8"  # 메모리 절약
  cuda_alloc_conf: "expandable_segments:True"
```

### 2. 배치 처리
```python
# main_enhanced.py에서 배치 크기 조정
performance:
  batch_size: 1
  max_workers: 4
```

## 지원 및 문의

문제가 발생하거나 추가 지원이 필요한 경우:

1. 로그 파일 확인: `./logs/callytics.log`
2. Docker 로그 확인: `docker logs callytics-enhanced`
3. 설정 파일 검증: `config/config_enhanced.yaml`
4. 모델 경로 확인: `AI 모델/` 폴더 구조 