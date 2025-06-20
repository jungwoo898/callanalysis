#!/usr/bin/env python3
"""
분류 기능 테스트 스크립트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_api_keys():
    """API 키 설정 확인"""
    print("=== API 키 설정 확인 ===")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    
    print(f"OpenAI API Key: {'✅ 설정됨' if openai_key else '❌ 없음'}")
    print(f"Azure API Key: {'✅ 설정됨' if azure_key else '❌ 없음'}")
    print(f"Azure Endpoint: {'✅ 설정됨' if azure_endpoint else '❌ 없음'}")
    print(f"HuggingFace Token: {'✅ 설정됨' if hf_token else '❌ 없음'}")
    
    return bool(openai_key or (azure_key and azure_endpoint) or hf_token)

def test_audio_file():
    """오디오 파일 확인"""
    print("\n=== 오디오 파일 확인 ===")
    
    audio_file = "audio/40186.mp3"
    if Path(audio_file).exists():
        print(f"✅ 오디오 파일 발견: {audio_file}")
        file_size = Path(audio_file).stat().st_size / (1024 * 1024)  # MB
        print(f"📁 파일 크기: {file_size:.2f} MB")
        return True
    else:
        print(f"❌ 오디오 파일 없음: {audio_file}")
        return False

def test_basic_imports():
    """기본 모듈 import 테스트"""
    print("\n=== 기본 모듈 import 테스트 ===")
    
    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
        
        import numpy as np
        print(f"✅ NumPy: {np.__version__}")
        
        import faster_whisper
        print("✅ faster-whisper")
        
        from src.text.llm import LLMOrchestrator
        print("✅ LLMOrchestrator")
        
        from src.audio.processing import Transcriber
        print("✅ Transcriber")
        
        return True
    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        return False

def test_simple_classification():
    """간단한 분류 테스트"""
    print("\n=== 간단한 분류 테스트 ===")
    
    try:
        from src.text.llm import LLMOrchestrator
        
        # LLM 초기화
        llm = LLMOrchestrator(
            config_path="config/config_enhanced.yaml",
            prompt_config_path="config/prompt.yaml",
            model_id="openai"
        )
        
        # 테스트 대화
        test_conversation = [
            {"speaker": "Speaker 1", "text": "안녕하세요, 요금제 문의드리려고 합니다."},
            {"speaker": "Speaker 0", "text": "네, 안녕하세요. 어떤 요금제를 찾고 계신가요?"},
            {"speaker": "Speaker 1", "text": "5G 요금제 중에서 가장 저렴한 걸로 알려주세요."},
            {"speaker": "Speaker 0", "text": "5G 베이직 요금제가 월 55,000원으로 가장 저렴합니다."}
        ]
        
        print("📝 테스트 대화:")
        for i, utterance in enumerate(test_conversation, 1):
            print(f"  {i}. {utterance['speaker']}: {utterance['text']}")
        
        print("\n🔄 분류 중...")
        
        # 비동기 실행을 위한 래퍼
        import asyncio
        
        async def run_classification():
            result = await llm.generate("Classification", test_conversation)
            return result
        
        result = asyncio.run(run_classification())
        
        print(f"✅ 분류 결과: {result}")
        return True
        
    except Exception as e:
        print(f"❌ 분류 테스트 실패: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 Callytics 분류 기능 테스트 시작\n")
    
    tests = [
        ("API 키 설정", test_api_keys),
        ("오디오 파일", test_audio_file),
        ("기본 모듈", test_basic_imports),
        ("간단한 분류", test_simple_classification)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 오류: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 테스트 결과 요약")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n전체 {len(results)}개 테스트 중 {passed}개 통과")
    
    if passed == len(results):
        print("🎉 모든 테스트 통과! 시스템이 정상 작동합니다.")
    else:
        print("⚠️ 일부 테스트 실패. 문제를 해결해주세요.")

if __name__ == "__main__":
    main() 