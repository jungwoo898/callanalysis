# Callytics Enhanced Windows Docker 실행 가이드

## 사전 요구사항

### 1. Docker Desktop 설치
1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) 다운로드
2. 설치 후 재부팅
3. Docker Desktop 실행 및 로그인

### 2. WSL2 설정 (권장)
```powershell
# WSL2 설치
wsl --install

# Ubuntu 배포판 설치
wsl --install -d Ubuntu

# WSL2를 기본 버전으로 설정
wsl --set-default-version 2
```

### 3. NVIDIA GPU 사용 (선택사항)
- NVIDIA GPU가 있는 경우: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) 설치
- Docker Desktop에서 GPU 지원 활성화

### 4. AI 모델 준비
```cmd
REM AI 모델 폴더 생성
mkdir "AI 모델\model"

REM 모델 파일들을 다음 경로에 배치:
REM - AI 모델\model\openchat-3.5-0106-private\
REM - AI 모델\model\Meta-Llama-3-8B-Instruct-private\
REM - AI 모델\model\gemma-2b-it-private\
```

## 실행 방법

### 1. 빠른 시작 (권장)
```cmd
REM 배치 파일 실행
run_docker.bat
```

### 2. 수동 실행
```cmd
REM 필요한 디렉토리 생성
mkdir audio
mkdir data
mkdir logs
mkdir temp

REM Docker Compose로 실행
docker-compose up --build
```

### 3. PowerShell에서 실행
```powershell
# PowerShell에서 실행
.\run_docker.bat

# 또는 직접 실행
docker-compose up --build
```

## 사용 방법

### 1. 오디오 파일 처리
```cmd
REM 오디오 파일을 ./audio/ 디렉토리에 복사
copy your_audio_file.wav audio\

REM 컨테이너 내에서 실행
docker exec -it callytics-enhanced python main_enhanced.py ./audio/your_audio_file.wav
```

### 2. 배치 처리
```cmd
REM 여러 파일 처리 (PowerShell)
Get-ChildItem audio\*.wav | ForEach-Object {
    docker exec -it callytics-enhanced python main_enhanced.py ".\audio\$($_.Name)"
}

REM CMD에서
for %f in (audio\*.wav) do docker exec -it callytics-enhanced python main_enhanced.py ".\audio\%f"
```

### 3. 개발 모드
```cmd
REM 코드 변경사항이 실시간으로 반영되는 개발 모드
docker-compose --profile dev up --build
```

## 설정 파일

### 1. 환경 변수 설정
```cmd
REM .env 파일 생성
copy .env.example .env

REM 텍스트 에디터로 .env 파일 편집
notepad .env
```

```env
# .env 파일 내용
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
```cmd
REM 실시간 로그 확인
docker-compose logs -f callytics

REM 특정 컨테이너 로그
docker logs callytics-enhanced
```

### 2. 성능 모니터링
```cmd
REM GPU 사용량 확인 (GPU 모드)
nvidia-smi

REM 컨테이너 리소스 사용량
docker stats callytics-enhanced
```

## 문제 해결

### 1. Docker Desktop 문제
```cmd
REM Docker Desktop 재시작
net stop com.docker.service
net start com.docker.service

REM 또는 Docker Desktop에서 재시작
```

### 2. WSL2 문제
```powershell
REM WSL2 재시작
wsl --shutdown
wsl

REM WSL2 버전 확인
wsl -l -v
```

### 3. 메모리 부족
```json
// Docker Desktop 설정에서 메모리 증가
// Settings > Resources > Memory: 8GB 이상
```

### 4. 포트 충돌
```cmd
REM 포트 사용 확인
netstat -ano | findstr :8000

REM 포트 변경
REM docker-compose.yml 수정
ports:
  - "8001:8000"  # 호스트 포트를 8001로 변경
```

### 5. 파일 경로 문제
```cmd
REM Windows 경로를 Linux 경로로 변환
REM C:\path\to\file -> /c/path/to/file

REM 또는 볼륨 마운트 수정
volumes:
  - ./audio:/app/audio:ro
```

## 데이터 백업

### 1. 데이터베이스 백업
```cmd
REM 데이터베이스 백업
docker exec callytics-enhanced sqlite3 /app/.db/Callytics.sqlite ".backup /app/.db/backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sqlite"
```

### 2. 로그 백업
```cmd
REM 로그 파일 백업
docker cp callytics-enhanced:/app/logs backup_logs_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
```

## 성능 최적화

### 1. Docker Desktop 설정
- Settings > Resources > Memory: 8GB 이상
- Settings > Resources > CPUs: 4개 이상
- Settings > Resources > Disk image size: 64GB 이상

### 2. WSL2 최적화
```powershell
# .wslconfig 파일 생성 (C:\Users\username\.wslconfig)
[wsl2]
memory=8GB
processors=4
swap=2GB
```

### 3. GPU 메모리 최적화
```yaml
# config/config_enhanced.yaml
runtime:
  device: "cuda"
  compute_type: "int8"  # 메모리 절약
  cuda_alloc_conf: "expandable_segments:True"
```

## 일반적인 문제

### 1. "docker-compose not found"
```cmd
REM Docker Compose 설치 확인
docker-compose --version

REM Docker Desktop에 포함되어 있어야 함
```

### 2. "Permission denied"
```cmd
REM 관리자 권한으로 실행
REM 또는 Docker Desktop에서 파일 공유 설정 확인
```

### 3. "Port already in use"
```cmd
REM 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000

REM 프로세스 종료 또는 포트 변경
```

### 4. "CUDA out of memory"
```yaml
# config/config_enhanced.yaml에서 메모리 사용량 조정
runtime:
  device: "cuda"
  compute_type: "int8"
  gpu_memory_fraction: 0.5
```

## 지원 및 문의

문제가 발생하거나 추가 지원이 필요한 경우:

1. 로그 파일 확인: `logs\callytics.log`
2. Docker 로그 확인: `docker logs callytics-enhanced`
3. 설정 파일 검증: `config\config_enhanced.yaml`
4. 모델 경로 확인: `AI 모델\` 폴더 구조
5. Docker Desktop 로그 확인 