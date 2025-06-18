@echo off
REM Callytics Enhanced Docker 실행 스크립트 (Windows)

echo === Callytics Enhanced Docker 실행 ===

REM 필요한 디렉토리 생성
if not exist "audio" mkdir audio
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp

REM Docker Compose 실행
echo Docker Compose로 Callytics를 시작합니다...

REM GPU 사용 가능 여부 확인 (Windows에서는 Docker Desktop 설정에 따라 다름)
docker-compose up --build

echo.
echo Callytics가 시작되었습니다.
echo 오디오 파일을 ./audio/ 디렉토리에 넣고 다음 명령으로 실행하세요:
echo docker exec -it callytics-enhanced python main_enhanced.py ./audio/your_file.wav
echo.
pause 