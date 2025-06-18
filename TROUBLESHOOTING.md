# Callytics Docker 빌드 문제 해결 가이드

## 🔧 주요 문제 및 해결책

### 1. pykospacing 패키지 오류
**문제**: `ERROR: No matching distribution found for pykospacing>=0.5`

**해결책**:
- ✅ `pykospacing` 패키지를 제거했습니다
- ✅ `kiwipiepy`, `py-hanspell` 패키지도 제거했습니다
- ✅ 안정적인 `konlpy`, `soynlp`만 사용합니다

### 2. 빌드 시간이 너무 오래 걸림
**문제**: Docker 빌드가 30분 이상 걸림

**해결책**:
```bash
# CPU 전용으로 빠른 빌드
./build_quick.sh  # Linux/macOS
build_quick.bat   # Windows
```

### 3. 메모리 부족 오류
**문제**: `Out of memory` 또는 `Killed`

**해결책**:
```bash
# Docker Desktop 설정에서 메모리 증가
# Settings > Resources > Memory: 8GB 이상

# 또는 CPU 전용 빌드 사용
docker-compose -f docker-compose.yml -f docker-compose.cpu.yml build
```

### 4. CUDA 관련 오류
**문제**: CUDA 버전 불일치 또는 GPU 접근 오류

**해결책**:
```bash
# CPU 전용으로 실행
docker-compose -f docker-compose.yml -f docker-compose.cpu.yml up

# 또는 GPU 설정 확인
nvidia-smi
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi
```

## 🚀 빠른 시작 방법

### 방법 1: CPU 전용 (권장)
```bash
# Windows
build_quick.bat

# Linux/macOS
chmod +x build_quick.sh
./build_quick.sh
```

### 방법 2: 수동 빌드
```bash
# 1. 기존 이미지 정리
docker system prune -a

# 2. CPU 전용 빌드
docker-compose -f docker-compose.yml -f docker-compose.cpu.yml build --no-cache

# 3. 실행
docker-compose -f docker-compose.yml -f docker-compose.cpu.yml up
```

### 방법 3: 단계별 빌드
```bash
# 1. 기본 이미지만 빌드
docker build -f Dockerfile.cpu -t callytics-cpu .

# 2. 컨테이너 실행
docker run -it --rm -v $(pwd)/audio:/app/audio callytics-cpu
```

## 📋 빌드 전 체크리스트

### 필수 확인사항
- [ ] Docker Desktop 실행 중
- [ ] 충분한 디스크 공간 (최소 10GB)
- [ ] 충분한 메모리 (최소 8GB)
- [ ] 인터넷 연결 상태

### 권장사항
- [ ] VPN 사용 중이면 끄기
- [ ] 방화벽에서 Docker 허용
- [ ] 안티바이러스에서 Docker 제외

## 🔍 문제 진단

### 로그 확인
```bash
# Docker 빌드 로그
docker-compose build --no-cache 2>&1 | tee build.log

# 컨테이너 로그
docker logs callytics-enhanced

# 시스템 리소스 확인
docker system df
docker stats
```

### 네트워크 문제 확인
```bash
# Docker Hub 연결 확인
docker pull hello-world

# DNS 설정 확인
nslookup registry-1.docker.io
```

## 🛠️ 고급 해결책

### 1. 멀티스테이지 빌드 사용
```dockerfile
# Dockerfile.optimized
FROM python:3.10-slim as builder
WORKDIR /app
COPY requirements_minimal.txt .
RUN pip install --user -r requirements_minimal.txt

FROM python:3.10-slim
COPY --from=builder /root/.local /root/.local
# ... 나머지 설정
```

### 2. 캐시 최적화
```bash
# 빌드 캐시 정리
docker builder prune -a

# 레이어 캐시 활용
docker-compose build --parallel
```

### 3. 로컬 미러 사용
```bash
# 로컬 PyPI 미러 설정
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements_minimal.txt
```

## 📞 지원

문제가 지속되면 다음 정보를 확인해주세요:

1. **시스템 정보**:
   ```bash
   docker --version
   docker-compose --version
   uname -a  # Linux/macOS
   systeminfo  # Windows
   ```

2. **Docker 설정**:
   ```bash
   docker info
   docker system df
   ```

3. **빌드 로그**:
   ```bash
   docker-compose build --no-cache 2>&1 | tee build.log
   ```

4. **네트워크 상태**:
   ```bash
   ping registry-1.docker.io
   curl -I https://pypi.org
   ``` 