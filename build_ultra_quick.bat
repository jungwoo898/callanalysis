@echo off
REM Callytics Ultra Quick 빌드 스크립트 (Windows)

echo === Callytics Ultra Quick 빌드 시작 ===
echo 이 버전은 CUDA 없이 CPU 전용으로 매우 빠르게 빌드됩니다.

REM 필요한 디렉토리 생성
if not exist "audio" mkdir audio
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp

echo Ultra Minimal CPU 전용으로 빠르게 빌드합니다...
docker-compose -f docker-compose.ultra_minimal.yml build --no-cache

echo.
echo 빌드가 완료되었습니다!
echo 다음 명령으로 실행하세요:
echo docker-compose -f docker-compose.ultra_minimal.yml up
echo.
pause 