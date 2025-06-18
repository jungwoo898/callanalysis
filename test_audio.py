#!/usr/bin/env python3
"""
간단한 오디오 파일 테스트 스크립트
"""

import os
import sys
import librosa
import soundfile as sf

def test_audio_file(audio_path):
    """오디오 파일을 테스트합니다."""
    print(f"테스트 중인 파일: {audio_path}")
    
    try:
        # 파일 존재 확인
        if not os.path.exists(audio_path):
            print(f"❌ 파일이 존재하지 않습니다: {audio_path}")
            return False
            
        # 오디오 파일 로드
        print("📁 오디오 파일 로드 중...")
        y, sr = librosa.load(audio_path, sr=None)
        
        # 기본 정보 출력
        duration = len(y) / sr
        print(f"✅ 파일 로드 성공!")
        print(f"   - 샘플링 레이트: {sr} Hz")
        print(f"   - 길이: {duration:.2f}초")
        print(f"   - 샘플 수: {len(y)}")
        
        # 오디오 특성 분석
        print("🔍 오디오 특성 분석 중...")
        
        # RMS 에너지
        rms = librosa.feature.rms(y=y)[0]
        avg_rms = rms.mean()
        print(f"   - 평균 RMS 에너지: {avg_rms:.4f}")
        
        # 스펙트럼 중심
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        avg_centroid = spectral_centroids.mean()
        print(f"   - 평균 스펙트럼 중심: {avg_centroid:.1f} Hz")
        
        # 제로 크로싱 레이트
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
        avg_zcr = zero_crossing_rate.mean()
        print(f"   - 평균 제로 크로싱 레이트: {avg_zcr:.4f}")
        
        # 음성/음악 구분 (간단한 방법)
        if avg_zcr > 0.1:
            print("   - 추정: 음성 (높은 제로 크로싱 레이트)")
        else:
            print("   - 추정: 음악 (낮은 제로 크로싱 레이트)")
            
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    print("🎵 Callytics 오디오 파일 테스트")
    print("=" * 50)
    
    # 테스트할 파일들
    test_files = [
        "./audio/",
        "./.data/input/",
        "./audio/*.mp3",
        "./audio/*.wav",
        "./.data/input/*.mp3",
        "./.data/input/*.wav"
    ]
    
    found_files = []
    
    # 파일 찾기
    for pattern in test_files:
        if os.path.isdir(pattern):
            # 디렉토리인 경우
            print(f"📂 디렉토리 확인: {pattern}")
            if os.path.exists(pattern):
                files = [f for f in os.listdir(pattern) if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]
                for file in files:
                    full_path = os.path.join(pattern, file)
                    found_files.append(full_path)
                    print(f"   - 발견: {file}")
            else:
                print(f"   - 디렉토리가 존재하지 않음")
        else:
            # 패턴인 경우
            import glob
            files = glob.glob(pattern)
            found_files.extend(files)
    
    if not found_files:
        print("❌ 오디오 파일을 찾을 수 없습니다!")
        print("\n📋 사용 가능한 위치:")
        print("   - ./audio/ (권장)")
        print("   - ./.data/input/")
        print("\n📋 지원하는 형식:")
        print("   - .mp3, .wav, .flac, .m4a")
        return
    
    print(f"\n🎯 발견된 파일 수: {len(found_files)}")
    
    # 각 파일 테스트
    success_count = 0
    for file_path in found_files:
        print(f"\n{'='*30}")
        if test_audio_file(file_path):
            success_count += 1
        print(f"{'='*30}")
    
    print(f"\n📊 결과 요약:")
    print(f"   - 총 파일 수: {len(found_files)}")
    print(f"   - 성공: {success_count}")
    print(f"   - 실패: {len(found_files) - success_count}")
    
    if success_count > 0:
        print(f"\n✅ 테스트 성공! 오디오 파일이 정상적으로 인식됩니다.")
        print(f"💡 이제 다음 명령으로 처리할 수 있습니다:")
        print(f"   docker exec -it callytics-enhanced python main_enhanced.py {found_files[0]}")
    else:
        print(f"\n❌ 모든 파일에서 오류가 발생했습니다.")

if __name__ == "__main__":
    main() 