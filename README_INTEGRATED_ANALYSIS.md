# Callytics 통합 상담 분석 시스템

## 개요

Callytics 통합 상담 분석 시스템은 오디오 파일을 입력받아 화자 분리, 음성 인식, ChatGPT API를 통한 상담 분석을 수행하고 결과를 데이터베이스에 저장하는 완전한 파이프라인입니다.

## 주요 기능

### 1. 화자 분리 (Speaker Diarization)
- Pyannote.audio를 사용한 고정밀 화자 분리
- 다중 화자 대화에서 개별 화자 식별
- 한국어 특화 최적화

### 2. 음성 인식 (Speech Recognition)
- Faster-Whisper를 사용한 고속 음성 인식
- 한국어 음성 인식 최적화
- 실시간 처리 지원

### 3. ChatGPT 상담 분석
- OpenAI GPT-4를 사용한 지능형 상담 분석
- 통신사 특화 분류 체계 적용
- 구조화된 JSON 응답 생성

### 4. 상담 분류 체계

#### 수집기관별 업무 유형
- 요금 안내
- 요금 납부
- 요금제 변경
- 선택약정 할인
- 납부 방법 변경
- 부가서비스 안내
- 소액 결제
- 휴대폰 정지 분실 파손
- 기기변경
- 명의 번호 유심 해지
- 그 외 업무유형

#### 분류 유형
- 상담 주제
- 상담 요건
- 상담 내용
- 상담 사유
- 상담 결과

#### 세부 분류 유형
- **상담 주제**: 상품 및 서비스 일반, 주문 결제 입금 확인, 취소 반품 교환 환불 AS, 회원 관리, 배송 문의, 이벤트 할인, 콘텐츠, 제휴, 기타
- **상담 요건**: 단일 요건 민원, 다수 요건 민원
- **상담 내용**: 일반 문의 상담, 업무 처리 상담, 고충 상담
- **상담 사유**: 업체, 민원인
- **상담 결과**: 만족, 미흡, 해결 불가, 추가 상담 필요

## 설치 및 설정

### 1. 환경 요구사항
- Python 3.8+
- CUDA 지원 GPU (권장)
- OpenAI API 키

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. OpenAI API 키 설정
```bash
export OPENAI_API_KEY="your-api-key-here"
```

또는 `config/config_enhanced.yaml` 파일에서 설정:
```yaml
openai:
  api_key: "your-api-key-here"
  model: "gpt-4"
  max_tokens: 2000
  temperature: 0.1
```

## 사용 방법

### 1. 단일 파일 분석
```bash
python integrated_analysis_main.py audio/example.wav
```

### 2. 디렉토리 일괄 분석
```bash
python integrated_analysis_main.py audio_directory/
```

### 3. 고급 옵션 사용
```bash
python integrated_analysis_main.py audio/example.wav \
  --model gpt-4 \
  --device gpu \
  --api-key your-api-key
```

### 4. Python 코드에서 사용
```python
from src.integrated_analyzer import IntegratedAnalyzer, AnalysisConfig

# 설정
config = AnalysisConfig(
    openai_api_key="your-api-key",
    model="gpt-4",
    device="auto"
)

# 분석기 초기화
analyzer = IntegratedAnalyzer(config)

# 파일 처리
result = analyzer.process_audio_file("audio/example.wav")

# 결과 확인
if result.get("success"):
    print(f"업무 유형: {result['analysis_result']['business_type']}")
    print(f"상담 결과: {result['analysis_result']['consultation_result']}")
    print(f"요약: {result['analysis_result']['summary']}")
```

## 출력 결과

### 분석 결과 구조
```json
{
  "success": true,
  "audio_properties_id": 1,
  "utterances_count": 15,
  "conversation_text": "고객: 안녕하세요...",
  "analysis_result": {
    "business_type": "요금 안내",
    "classification_type": "상담 주제",
    "detail_classification": "상품 및 서비스 일반",
    "consultation_result": "만족",
    "summary": "고객이 요금제 변경에 대해 문의했으며, 상담원이 상세히 안내하여 만족스러운 결과를 얻었습니다.",
    "customer_request": "요금제 변경 방법 문의",
    "solution": "온라인 또는 고객센터를 통한 요금제 변경 신청 안내",
    "additional_info": "변경 후 첫 달 요금 계산 방법 안내",
    "confidence": 0.95
  },
  "processing_time": 45.2
}
```

## 데이터베이스 스키마

### 주요 테이블
- `audio_properties`: 오디오 파일 정보
- `utterances`: 발화 내용 (화자별)
- `consultation_analysis`: 상담 분석 결과

### 분석 결과 조회
```python
# 특정 파일의 분석 요약 조회
summary = analyzer.get_analysis_summary(audio_properties_id=1)
```

## 성능 최적화

### 1. GPU 가속
- CUDA 지원 GPU 사용 시 처리 속도 대폭 향상
- 자동 디바이스 감지 지원

### 2. 배치 처리
- 여러 파일 동시 처리 지원
- 메모리 효율적 처리

### 3. 캐싱
- 모델 로딩 캐싱
- 중복 처리 방지

## 오류 처리

### 1. 파일 유효성 검사
- 지원 형식: WAV, MP3, M4A, FLAC, OGG
- 최대 파일 크기: 100MB
- 자동 형식 검증

### 2. API 오류 처리
- OpenAI API 호출 실패 시 재시도
- 네트워크 오류 시 폴백 처리
- 상세한 오류 메시지 제공

### 3. 데이터베이스 오류 처리
- 연결 실패 시 재시도 로직
- 트랜잭션 롤백 지원
- 데이터 무결성 보장

## 설정 파일

### config/config_enhanced.yaml
```yaml
# OpenAI API 설정
openai:
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4"
  max_tokens: 2000
  temperature: 0.1

# 통합 분석 설정
integrated_analysis:
  enabled: true
  default_model: "gpt-4"
  fallback_model: "openchat"
  
  # 분석 옵션
  analysis_options:
    business_type_classification: true
    consultation_type_classification: true
    detail_classification: true
    result_evaluation: true
    summary_generation: true
    solution_proposal: true
```

## 예제 코드

### examples/integrated_analysis_example.py
```python
# 단일 파일 분석 예제
python examples/integrated_analysis_example.py
```

## 모니터링 및 로깅

### 1. 처리 상태 모니터링
- 실시간 처리 진행률 표시
- 각 단계별 소요 시간 측정
- 성공/실패 통계

### 2. 로그 관리
- 상세한 처리 로그 기록
- 오류 로그 분리 저장
- 로그 레벨 조정 가능

## 확장 가능성

### 1. 새로운 분류 체계 추가
- 설정 파일을 통한 쉬운 확장
- 커스텀 분류 규칙 정의
- 다국어 지원

### 2. 추가 분석 기능
- 감정 분석
- 키워드 추출
- 의도 분석
- 품질 평가

### 3. API 서비스
- RESTful API 제공
- 실시간 스트리밍 처리
- 웹 인터페이스

## 문제 해결

### 1. 일반적인 문제
- **GPU 메모리 부족**: 배치 크기 조정
- **API 호출 실패**: 네트워크 연결 확인
- **모델 로딩 실패**: 캐시 삭제 후 재시도

### 2. 성능 최적화
- **처리 속도 향상**: GPU 사용, 배치 크기 증가
- **메모리 사용량 감소**: 배치 크기 감소, 모델 최적화
- **정확도 향상**: 모델 파라미터 조정, 프롬프트 개선

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여

버그 리포트, 기능 요청, 풀 리퀘스트를 환영합니다.

## 지원

문제가 발생하면 이슈를 생성하거나 문서를 참조하세요. 