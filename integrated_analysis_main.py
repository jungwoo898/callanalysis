#!/usr/bin/env python3
"""
Callytics 통합 분석 메인 실행 파일
오디오 파일에서 화자 분리, 음성 인식, 상담 분석을 수행하는 완전한 파이프라인
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.integrated_analyzer import IntegratedAnalyzer

def setup_logging():
    """로깅 설정"""
    # logs 디렉토리 생성
    Path("logs").mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/integrated_analysis.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    """메인 실행 함수"""
    logger = setup_logging()
    
    try:
        logger.info("=== Callytics 통합 분석 시작 ===")
        
        # 환경 변수에서 토큰 확인
        huggingface_token = os.getenv("HUGGINGFACE_TOKEN")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_api_key:
            logger.error("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            logger.info("환경 변수 설정 방법:")
            logger.info("Windows: set OPENAI_API_KEY=your_api_key")
            logger.info("Linux/Mac: export OPENAI_API_KEY=your_api_key")
            return
        
        if not huggingface_token:
            logger.warning("HUGGINGFACE_TOKEN이 설정되지 않았습니다. 화자 분리 없이 기본 음성 인식만 수행합니다.")
        
        # 통합 분석기 초기화
        logger.info("통합 분석기 초기화 중...")
        analyzer = IntegratedAnalyzer(
            config_path="config/config_enhanced.yaml",
            diarization_token=huggingface_token
        )
        
        # 테스트 오디오 파일 경로
        audio_file = "audio/40186.mp3"
        
        if not Path(audio_file).exists():
            logger.error(f"오디오 파일을 찾을 수 없습니다: {audio_file}")
            logger.info("audio/ 디렉토리에 오디오 파일을 넣어주세요.")
            return
        
        # 상담 분석 실행
        logger.info(f"상담 분석 시작: {audio_file}")
        start_time = time.time()
        
        result = analyzer.analyze_consultation(
            audio_path=audio_file,
            consultation_id=f"test_consultation_{int(time.time())}",
            metadata={
                "source": "test",
                "description": "통합 분석 테스트"
            }
        )
        
        processing_time = time.time() - start_time
        
        # 결과 출력
        logger.info("=== 분석 결과 ===")
        logger.info(f"상담 ID: {result['consultation_id']}")
        logger.info(f"발화 수: {len(result['utterances'])}")
        logger.info(f"처리 시간: {processing_time:.2f}초")
        
        # 분석 결과 요약
        analysis = result['analysis']
        logger.info("=== 상담 분석 결과 ===")
        logger.info(f"수집기관: {analysis.get('collection_agency', 'Unknown')}")
        logger.info(f"업무 유형: {analysis.get('business_type', 'Unknown')}")
        logger.info(f"분류 유형: {analysis.get('classification_type', 'Unknown')}")
        logger.info(f"세부 분류: {analysis.get('detailed_classification', 'Unknown')}")
        logger.info(f"상담 주제: {analysis.get('consultation_topic', 'Unknown')}")
        logger.info(f"상담 요건: {analysis.get('consultation_requirement', 'Unknown')}")
        logger.info(f"상담 결과: {analysis.get('consultation_result', 'Unknown')}")
        
        # 발화 내용 요약
        logger.info("=== 발화 내용 요약 ===")
        for i, utterance in enumerate(result['utterances'][:5], 1):  # 처음 5개만 출력
            logger.info(f"발화 {i}: {utterance['speaker']} - {utterance['text'][:100]}...")
        
        if len(result['utterances']) > 5:
            logger.info(f"... 외 {len(result['utterances']) - 5}개 발화")
        
        # 통계 조회
        logger.info("=== 분석 통계 ===")
        stats = analyzer.get_analysis_summary()
        if stats:
            logger.info(f"전체 상담 수: {stats.get('total_consultations', 0)}")
            logger.info(f"전체 발화 수: {stats.get('total_utterances', 0)}")
            logger.info(f"평균 처리 시간: {stats.get('average_processing_time', 0):.2f}초")
        
        logger.info("=== 분석 완료 ===")
        
    except Exception as e:
        logger.error(f"분석 중 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 