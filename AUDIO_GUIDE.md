# Callytics 오디오 파일 사용 가이드

## 📁 오디오 파일 위치

### 1. 기본 위치
```
Callytics/audio/
```

### 2. 지원하는 오디오 형식
- `.wav` (권장)
- `.mp3`
- `.flac`
- `.m4a`
- `.ogg`

## 🚀 사용 방법

### 1. 오디오 파일 준비
```bash
# 오디오 파일을 audio 폴더에 복사
cp your_audio_file.mp3 Callytics/audio/
```

### 2. Docker 컨테이너 실행
```bash
# Windows
docker-compose up

# 또는 Ultra Minimal 버전
docker-compose -f docker-compose.ultra_minimal.yml up
```

### 3. 오디오 파일 처리
```bash
# 컨테이너 내에서 실행
docker exec -it callytics-enhanced python main_enhanced.py ./audio/your_file.mp3

# 또는 여러 파일 처리
docker exec -it callytics-enhanced python main_enhanced.py ./audio/
```

## 📋 단계별 가이드

### Step 1: 오디오 파일 준비
1. 처리할 오디오 파일을 `Callytics/audio/` 폴더에 복사
2. 파일명에 한글이나 특수문자 피하기
3. 권장: `call_001.wav`, `complaint_002.mp3` 등

### Step 2: Docker 컨테이너 시작
```bash
# 현재 디렉토리에서
cd Callytics

# 컨테이너 시작
docker-compose up -d
```

### Step 3: 파일 처리
```bash
# 단일 파일 처리
docker exec -it callytics-enhanced python main_enhanced.py ./audio/call_001.wav

# 폴더 내 모든 파일 처리
docker exec -it callytics-enhanced python main_enhanced.py ./audio/
```

### Step 4: 결과 확인
- 데이터베이스: `./data/Callytics.sqlite`
- 로그: `./logs/callytics.log`
- 임시 파일: `./temp/`

## 🔧 문제 해결

### 1. "No such file or directory"
```bash
# 파일 경로 확인
ls -la Callytics/audio/

# 컨테이너 내부에서 확인
docker exec -it callytics-enhanced ls -la /app/audio/
```

### 2. "Unsupported audio format"
```bash
# ffmpeg로 변환
ffmpeg -i input.mp3 output.wav

# 또는 Python으로 변환
python -c "
import librosa
import soundfile as sf
y, sr = librosa.load('input.mp3')
sf.write('output.wav', y, sr)
"
```

### 3. "Permission denied"
```bash
# 파일 권한 확인
chmod 644 Callytics/audio/*.mp3

# Docker 볼륨 마운트 확인
docker-compose down
docker-compose up
```

## 📊 배치 처리

### 1. 모든 오디오 파일 처리
```bash
# Windows (PowerShell)
Get-ChildItem audio\*.wav | ForEach-Object {
    docker exec -it callytics-enhanced python main_enhanced.py "/app/audio/$($_.Name)"
}

# Linux/macOS
for file in audio/*.wav; do
    docker exec -it callytics-enhanced python main_enhanced.py "/app/audio/$(basename $file)"
done
```

### 2. 특정 형식만 처리
```bash
# MP3 파일만 처리
docker exec -it callytics-enhanced python main_enhanced.py ./audio/ --format mp3

# WAV 파일만 처리
docker exec -it callytics-enhanced python main_enhanced.py ./audio/ --format wav
```

## 🎯 최적화 팁

### 1. 파일 크기 최적화
- 긴 오디오는 10분 단위로 분할
- 샘플링 레이트: 16kHz 권장
- 비트레이트: 128kbps (MP3)

### 2. 성능 최적화
```bash
# CPU 코어 수에 맞게 조정
docker-compose up --scale callytics=4

# 메모리 제한 설정
docker run --memory=4g callytics-enhanced
```

### 3. 스토리지 최적화
```bash
# 오디오 파일 압축
gzip audio/*.wav

# 처리 후 원본 삭제
rm audio/processed_*.wav
```

## 📞 지원

문제가 발생하면 다음을 확인해주세요:

1. **파일 경로**: `Callytics/audio/` 폴더에 파일이 있는지
2. **파일 형식**: 지원하는 오디오 형식인지
3. **파일 크기**: 너무 큰 파일은 분할
4. **권한**: 파일 읽기 권한이 있는지
5. **로그**: `./logs/callytics.log` 확인 