#!/bin/bash

# AI 모델 다운로드 스크립트
echo "AI 모델 다운로드를 시작합니다..."

# 모델 디렉토리 생성
mkdir -p /app/models

# OpenChat-3.5 모델 다운로드 (예시)
echo "OpenChat-3.5 모델 다운로드 중..."
# 실제 모델 경로로 수정 필요
# git clone https://huggingface.co/openchat/openchat-3.5-0106 /app/models/openchat-3.5-0106-private

# Llama-3 모델 다운로드 (예시)
echo "Llama-3 모델 다운로드 중..."
# git clone https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct /app/models/Meta-Llama-3-8B-Instruct-private

# Gemma 모델 다운로드 (예시)
echo "Gemma 모델 다운로드 중..."
# git clone https://huggingface.co/google/gemma-2b-it /app/models/gemma-2b-it-private

echo "모델 다운로드가 완료되었습니다."
echo "실제 모델 파일을 /app/models/ 디렉토리에 배치해주세요." 