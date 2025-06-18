#!/usr/bin/env python3
"""
오디오 파일 분석 테스트 스크립트
"""

import os
import sys
import glob
from pathlib import Path

def test_audio_analysis():
    """오디오 파일 분석 테스트"""
    print("=== Callytics 오디오 분석 테스트 시작 ===")
    
    # 오디오 파일 찾기
    audio_dir = Path("./audio")
    if not audio_dir.exists():
        print("❌ audio 폴더가 없습니다. 생성합니다...")
        audio_dir.mkdir(exist_ok=True)
        print("📁 audio 폴더를 생성했습니다.")
        print("💡 오디오 파일을 audio 폴더에 넣고 다시 실행하세요.")
        return
    
    # 오디오 파일 검색
    audio_files = []
    for ext in ['*.wav', '*.mp3', '*.flac', '*.m4a']:
        audio_files.extend(audio_dir.glob(ext))
    
    if not audio_files:
        print("❌ audio 폴더에 오디오 파일이 없습니다.")
        print("💡 다음 형식의 파일을 audio 폴더에 넣어주세요:")
        print("   - .wav, .mp3, .flac, .m4a")
        return
    
    print(f"✅ {len(audio_files)}개의 오디오 파일을 찾았습니다:")
    for i, file in enumerate(audio_files, 1):
        print(f"   {i}. {file.name}")
    
    # 첫 번째 파일로 테스트
    test_file = audio_files[0]
    print(f"\n🎵 테스트 파일: {test_file.name}")
    
    try:
        # main_enhanced 모듈 import 시도
        print("📁 오디오 파일 로드 중...")
        
        # librosa로 기본 로드 테스트
        import librosa
        y, sr = librosa.load(str(test_file), sr=None)
        duration = len(y) / sr
        print(f"✅ 오디오 로드 성공: {duration:.2f}초, 샘플레이트: {sr}Hz")
        
        # main_enhanced 함수 호출
        print("🔍 오디오 분석 시작...")
        import asyncio
        from main_enhanced import main_enhanced
        
        # 비동기 함수 실행
        asyncio.run(main_enhanced(str(test_file)))
        
        print("✅ 오디오 분석 완료!")
        
    except ImportError as e:
        print(f"❌ 모듈 import 오류: {e}")
        print("💡 필요한 패키지가 설치되지 않았습니다.")
        
    except Exception as e:
        print(f"❌ 분석 중 오류 발생: {e}")
        print("💡 오류 로그를 확인해주세요.")

if __name__ == "__main__":
    test_audio_analysis() 