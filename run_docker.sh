#!/bin/bash

# Callytics Docker 실행 스크립트

echo "=== Callytics Enhanced Docker 실행 ==="

# 필요한 디렉토리 생성
mkdir -p audio data logs temp

# Docker Compose 실행
echo "Docker Compose로 Callytics를 시작합니다..."

# GPU 사용 가능 여부 확인
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA GPU가 감지되었습니다. GPU 모드로 실행합니다."
    docker-compose up --build
else
    echo "NVIDIA GPU가 감지되지 않았습니다. CPU 모드로 실행합니다."
    # CPU 전용 설정으로 실행
    docker-compose -f docker-compose.yml -f docker-compose.cpu.yml up --build
fi

echo "Callytics가 시작되었습니다."
echo "오디오 파일을 ./audio/ 디렉토리에 넣고 다음 명령으로 실행하세요:"
echo "docker exec -it callytics-enhanced python main_enhanced.py ./audio/your_file.wav" 