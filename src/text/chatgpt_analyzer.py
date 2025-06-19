import os
import json
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import openai
import yaml

class BusinessType(Enum):
    """수집기관별 업무 유형"""
    FEE_INFO = "요금 안내"
    FEE_PAYMENT = "요금 납부"
    PLAN_CHANGE = "요금제 변경"
    SELECTIVE_DISCOUNT = "선택약정 할인"
    PAYMENT_METHOD_CHANGE = "납부 방법 변경"
    ADDITIONAL_SERVICE = "부가서비스 안내"
    MICRO_PAYMENT = "소액 결제"
    PHONE_SUSPENSION_LOSS_DAMAGE = "휴대폰 정지 분실 파손"
    DEVICE_CHANGE = "기기변경"
    NAME_NUMBER_USIM_CANCEL = "명의 번호 유심 해지"
    OTHER = "그 외 업무유형"

class ClassificationType(Enum):
    """분류 유형"""
    CONSULTATION_TOPIC = "상담 주제"
    CONSULTATION_REQUIREMENT = "상담 요건"
    CONSULTATION_CONTENT = "상담 내용"
    CONSULTATION_REASON = "상담 사유"
    CONSULTATION_RESULT = "상담 결과"

class DetailClassificationType(Enum):
    """세부 분류 유형"""
    # 상담 주제
    PRODUCT_SERVICE_GENERAL = "상품 및 서비스 일반"
    ORDER_PAYMENT_DEPOSIT_CONFIRM = "주문 결제 입금 확인"
    CANCEL_RETURN_EXCHANGE_REFUND_AS = "취소 반품 교환 환불 AS"
    MEMBER_MANAGEMENT = "회원 관리"
    DELIVERY_INQUIRY = "배송 문의"
    EVENT_DISCOUNT = "이벤트 할인"
    CONTENT = "콘텐츠"
    PARTNERSHIP = "제휴"
    ETC = "기타"
    
    # 상담 요건
    SINGLE_REQUIREMENT = "단일 요건 민원"
    MULTIPLE_REQUIREMENT = "다수 요건 민원"
    
    # 상담 내용
    GENERAL_INQUIRY = "일반 문의 상담"
    BUSINESS_PROCESSING = "업무 처리 상담"
    COMPLAINT = "고충 상담"
    
    # 상담 사유
    COMPANY = "업체"
    COMPLAINANT = "민원인"
    
    # 상담 결과
    SATISFACTION = "만족"
    INSUFFICIENT = "미흡"
    UNSOLVABLE = "해결 불가"
    ADDITIONAL_CONSULTATION = "추가 상담 필요"

@dataclass
class ConsultationAnalysisResult:
    """상담 분석 결과"""
    business_type: str
    classification_type: str
    detail_classification: str
    consultation_result: str
    summary: str
    customer_request: str
    solution: str
    additional_info: str
    confidence: float = 0.0
    processing_time: float = 0.0

class ChatGPTAnalyzer:
    """ChatGPT API를 사용한 상담 분석기"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", max_tokens: int = 2000, temperature: float = 0.1):
        """
        ChatGPT 분석기 초기화
        
        Parameters
        ----------
        api_key : str
            OpenAI API 키
        model : str
            사용할 모델명 (기본값: gpt-4)
        max_tokens : int
            최대 토큰 수 (기본값: 2000)
        temperature : float
            생성 다양성 (기본값: 0.1)
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = openai.OpenAI(api_key=api_key)
        
        # 분석 프롬프트 템플릿
        self.analysis_prompt = self._create_analysis_prompt()
    
    def _create_analysis_prompt(self) -> str:
        """분석용 프롬프트 생성"""
        return """당신은 통신사 고객 상담 전문가입니다. 
다음의 통신사 상담 내용을 분석하여 JSON 형태로 결과를 반환해주세요.

분석해야 할 항목:
1. 수집기관별 업무 유형: 요금 안내, 요금 납부, 요금제 변경, 선택약정 할인, 납부 방법 변경, 부가서비스 안내, 소액 결제, 휴대폰 정지 분실 파손, 기기변경, 명의 번호 유심 해지, 그 외 업무유형

2. 분류 유형: 상담 주제, 상담 요건, 상담 내용, 상담 사유, 상담 결과

3. 세부 분류 유형:
   - 상담 주제: 상품 및 서비스 일반, 주문 결제 입금 확인, 취소 반품 교환 환불 AS, 회원 관리, 배송 문의, 이벤트 할인, 콘텐츠, 제휴, 기타
   - 상담 요건: 단일 요건 민원, 다수 요건 민원
   - 상담 내용: 일반 문의 상담, 업무 처리 상담, 고충 상담
   - 상담 사유: 업체, 민원인
   - 상담 결과: 만족, 미흡, 해결 불가, 추가 상담 필요

4. 추가 분석:
   - 상담 요약 (100자 이내)
   - 고객 요청사항
   - 해결방안
   - 추가 안내사항

분석 지침:
- 상담 내용을 자세히 읽고 가장 적합한 분류를 선택하세요
- "기타"나 "미흡" 같은 기본값은 최후의 수단으로만 사용하세요
- 고객의 구체적인 요청사항을 파악하여 정확한 업무 유형을 분류하세요
- 상담 주제는 고객이 문의한 핵심 내용에 따라 분류하세요
- 상담 요건은 고객이 제기한 문제의 개수에 따라 분류하세요

다음 형식의 JSON으로 응답해주세요:
{
    "business_type": "업무 유형",
    "classification_type": "분류 유형", 
    "detail_classification": "세부 분류",
    "consultation_result": "상담 결과",
    "summary": "상담 요약",
    "customer_request": "고객 요청사항",
    "solution": "해결방안",
    "additional_info": "추가 안내사항",
    "confidence": 0.95
}

상담 내용:
{conversation_text}
"""
    
    def analyze_conversation(self, conversation_text: str) -> ConsultationAnalysisResult:
        """
        대화 내용 분석
        
        Parameters
        ----------
        conversation_text : str
            분석할 대화 내용
            
        Returns
        -------
        ConsultationAnalysisResult
            분석 결과
        """
        start_time = time.time()
        
        try:
            # ChatGPT API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 통신사 고객 상담 전문가입니다."},
                    {"role": "user", "content": self.analysis_prompt.format(conversation_text=conversation_text)}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # 응답 파싱
            content = response.choices[0].message.content
            result_dict = self._parse_json_response(content)
            
            processing_time = time.time() - start_time
            
            return ConsultationAnalysisResult(
                business_type=result_dict.get("business_type", "그 외 업무유형"),
                classification_type=result_dict.get("classification_type", "상담 주제"),
                detail_classification=result_dict.get("detail_classification", "기타"),
                consultation_result=result_dict.get("consultation_result", "미흡"),
                summary=result_dict.get("summary", ""),
                customer_request=result_dict.get("customer_request", ""),
                solution=result_dict.get("solution", ""),
                additional_info=result_dict.get("additional_info", ""),
                confidence=result_dict.get("confidence", 0.0),
                processing_time=processing_time
            )
            
        except Exception as e:
            print(f"ChatGPT 분석 중 오류 발생: {e}")
            # 기본값 반환
            return ConsultationAnalysisResult(
                business_type="그 외 업무유형",
                classification_type="상담 주제",
                detail_classification="기타",
                consultation_result="미흡",
                summary="분석 실패",
                customer_request="",
                solution="",
                additional_info="",
                confidence=0.0,
                processing_time=time.time() - start_time
            )
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """JSON 응답 파싱"""
        try:
            # JSON 블록 찾기
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {}
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return {}
    
    def batch_analyze(self, conversations: List[str]) -> List[ConsultationAnalysisResult]:
        """
        여러 대화 내용 일괄 분석
        
        Parameters
        ----------
        conversations : List[str]
            분석할 대화 내용 리스트
            
        Returns
        -------
        List[ConsultationAnalysisResult]
            분석 결과 리스트
        """
        results = []
        for conversation in conversations:
            result = self.analyze_conversation(conversation)
            results.append(result)
            # API 호출 간격 조절
            time.sleep(0.5)
        return results 