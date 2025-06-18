#!/bin/bash

# Callytics 빠른 빌드 스크립트

echo "=== Callytics 빠른 빌드 시작 ==="

# 필요한 디렉토리 생성
mkdir -p audio data logs temp

echo "CPU 전용으로 빠르게 빌드합니다..."
docker-compose -f docker-compose.yml -f docker-compose.cpu.yml build --no-cache

echo ""
echo "빌드가 완료되었습니다!"
echo "다음 명령으로 실행하세요:"
echo "docker-compose -f docker-compose.yml -f docker-compose.cpu.yml up" 