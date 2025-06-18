@echo off
REM Callytics 간단한 테스트 스크립트 (Windows)

echo === Callytics 간단한 테스트 시작 ===

REM 필요한 디렉토리 생성
if not exist "audio" mkdir audio
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp
if not exist ".data" mkdir .data

echo 간단한 테스트 컨테이너를 빌드합니다...
docker-compose -f docker-compose.simple.yml build --no-cache

echo.
echo 테스트를 실행합니다...
docker-compose -f docker-compose.simple.yml up

echo.
echo 테스트가 완료되었습니다!
pause 