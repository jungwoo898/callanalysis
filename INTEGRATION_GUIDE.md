# AI 모델과 Callytics 통합 가이드

## 개요

이 가이드는 AI 모델의 한국어 특화 기능을 Callytics에 통합하여 통신사 고객 상담 분석을 강화하는 방법을 설명합니다.

## 주요 개선사항

### 1. 한국어 특화 모델 통합
- **OpenChat-3.5**: 통신사 상담 분석에 최적화된 한국어 모델
- **Llama-3**: Meta의 최신 모델
- **Gemma**: Google의 경량화 모델
- **PEFT (LoRA)**: 효율적인 파인튜닝 지원

### 2. 통신사 민원 분석 기능 강화
- **통신사 민원 분류**: 7개 카테고리로 자동 분류
- **심각도/긴급도 평가**: 자동 우선순위 결정
- **부서 배정**: 적절한 담당부서 자동 배정
- **질의응답**: 상담 내용 기반 질의응답
- **요약 기능**: 구조화된 요약 및 액션 아이템 생성

### 3. 데이터베이스 확장
- 통신사 민원 분석 결과 저장
- 우선순위 관리
- 부서별 처리 이력
- 통계 및 리포트 기능

## 설치 및 설정

### 1. 의존성 설치

```bash
# 기존 Callytics 환경에서
pip install -r requirements_enhanced.txt

# 또는 새로운 환경 생성
conda create -n callytics-enhanced python=3.10
conda activate callytics-enhanced
pip install -r requirements_enhanced.txt
```

### 2. 모델 다운로드

```bash
# AI 모델 폴더에서 모델 다운로드
cd AI\ 모델/
# 모델 파일들을 model/ 폴더에 배치
# - openchat-3.5-0106-private/
# - Meta-Llama-3-8B-Instruct-private/
# - gemma-2b-it-private/
```

### 3. 설정 파일 구성

```yaml
# config/config_enhanced.yaml
runtime:
  device: "cuda"
  compute_type: "float16"

models:
  korean_models:
    openchat:
      base_model_name: "../AI 모델/model/openchat-3.5-0106-private"
      # 실제 모델 경로로 수정
```

### 4. 데이터베이스 스키마 업데이트

```bash
# SQLite 데이터베이스에 새로운 테이블 생성
sqlite3 .db/Callytics.sqlite < src/db/sql/EnhancedSchema.sql
```

## 사용 방법

### 1. 기본 사용법

```python
import asyncio
from src.text.complaint_analyzer import ComplaintAnalyzer, KoreanModelConfig

# 한국어 모델 설정
korean_config = KoreanModelConfig(
    model_type="openchat",
    base_model_name="../AI 모델/model/openchat-3.5-0106-private"
)

# 통신사 민원 분석기 초기화
analyzer = ComplaintAnalyzer(
    config_path="config/config_enhanced.yaml",
    korean_prompt_path="config/korean_prompts.yaml",
    korean_model_config=korean_config
)

# 통신사 민원 분석 실행
result = await analyzer.analyze_complaint(conversation_data)
print(f"카테고리: {result.category}")
print(f"우선순위: {result.priority_level}")
```

### 2. 향상된 메인 프로세스 실행

```bash
# 단일 파일 처리
python main_enhanced.py ./audio/sample.wav

# 배치 처리
python main_enhanced.py --batch ./audio/
```

### 3. 질의응답 기능

```python
# 통신사 상담 내용에 대한 질의응답
qa_result = await analyzer.answer_question(
    conversation_text="상담 내용...",
    question="이 고객의 핵심 문제는 무엇인가요?"
)
print(qa_result["answer"])
```

## 모델 선택 가이드

### 1. OpenChat-3.5 (권장)
- **장점**: 한국어 통신사 상담 분석에 최적화, 빠른 응답
- **단점**: 모델 크기가 큼 (약 7GB)
- **사용 시나리오**: 프로덕션 환경, 고품질 분석 필요

### 2. Llama-3
- **장점**: Meta의 최신 기술, 다국어 지원
- **단점**: 리소스 요구사항 높음
- **사용 시나리오**: 다국어 환경, 최신 기술 적용

### 3. Gemma
- **장점**: 경량화, 빠른 추론
- **단점**: 성능이 상대적으로 낮을 수 있음
- **사용 시나리오**: 개발/테스트 환경, 리소스 제약

## 성능 최적화

### 1. GPU 메모리 최적화

```yaml
# config/config_enhanced.yaml
runtime:
  device: "cuda"
  compute_type: "int8"  # 메모리 절약

performance:
  gpu_memory_fraction: 0.8
  batch_size: 1
```

### 2. 모델 캐싱

```python
# 모델을 메모리에 유지하여 재사용
analyzer = ComplaintAnalyzer(...)
# 여러 파일 처리 시 모델 재사용
for file in files:
    result = await analyzer.analyze_complaint(file)
```

### 3. 배치 처리

```python
# 여러 통신사 민원을 배치로 처리
results = await asyncio.gather(*[
    analyzer.analyze_complaint(data) 
    for data in batch_data
])
```

## 데이터베이스 스키마

### 새로운 테이블

1. **ComplaintCategory**: 통신사 민원 카테고리
2. **ComplaintAnalysis**: 통신사 민원 분석 결과
3. **ComplaintSummary**: 통신사 민원 요약
4. **ComplaintPriority**: 우선순위 정보
5. **Department**: 통신사 부서 정보
6. **ComplaintDepartmentMapping**: 통신사 민원-부서 매핑
7. **QAResponse**: 질의응답 결과

### 쿼리 예시

```sql
-- 카테고리별 통신사 민원 통계
SELECT 
    cc.Name as Category,
    COUNT(*) as Count,
    AVG(ca.SentimentScore) as AvgSentiment
FROM ComplaintAnalysis ca
JOIN ComplaintCategory cc ON ca.CategoryID = cc.ID
GROUP BY cc.Name;

-- 우선순위별 통신사 민원 목록
SELECT 
    f.Name as FileName,
    ca.Severity,
    ca.Urgency,
    cp.PriorityLevel
FROM ComplaintAnalysis ca
JOIN File f ON ca.FileID = f.ID
JOIN ComplaintPriority cp ON f.ID = cp.FileID
WHERE cp.PriorityLevel >= 4
ORDER BY cp.PriorityLevel DESC;
```

## 모니터링 및 로깅

### 1. 로그 설정

```yaml
# config/config_enhanced.yaml
logging:
  level: "INFO"
  file: "logs/callytics.log"
  max_file_size: "10MB"
```

### 2. 성능 모니터링

```python
import time
import logging

logger = logging.getLogger(__name__)

async def analyze_with_monitoring(analyzer, data):
    start_time = time.time()
    result = await analyzer.analyze_complaint(data)
    end_time = time.time()
    
    logger.info(f"분석 완료: {end_time - start_time:.2f}초")
    logger.info(f"결과: {result.category}, 신뢰도: {result.confidence}")
    
    return result
```

## 문제 해결

### 1. 모델 로딩 오류

```bash
# CUDA 메모리 부족 시
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# CPU 사용 시
export CUDA_VISIBLE_DEVICES=""
```

### 2. 메모리 부족

```python
# 모델 언로드
analyzer.unload()

# 가비지 컬렉션
import gc
gc.collect()
torch.cuda.empty_cache()
```

### 3. 토크나이저 오류

```python
# 토크나이저 재설정
tokenizer.pad_token = tokenizer.eos_token
model.resize_token_embeddings(len(tokenizer))
```

## 향후 개선 계획

### 1. 모델 업데이트
- 최신 모델 버전 적용
- 성능 최적화
- 다국어 지원 확장

### 2. 기능 확장
- 실시간 분석
- 웹 인터페이스
- API 서비스

### 3. 성능 개선
- 모델 압축
- 추론 속도 최적화
- 배치 처리 개선

## 지원 및 문의

문제가 발생하거나 추가 지원이 필요한 경우:

1. 로그 파일 확인: `logs/callytics.log`
2. 설정 파일 검증: `config/config_enhanced.yaml`
3. 모델 경로 확인: AI 모델 폴더 구조
4. 의존성 버전 확인: `requirements_enhanced.txt`

## 라이선스

이 통합은 기존 Callytics와 AI 모델의 라이선스를 따릅니다.
각 모델의 라이선스 조건을 확인하시기 바랍니다. 