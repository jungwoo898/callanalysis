# Standard library imports
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Related third-party imports
import yaml

# Local imports
from src.text.korean_models import KoreanModelManager, KoreanModelConfig
from src.text.llm import LLMOrchestrator
from src.audio.utils import Formatter


@dataclass
class ComplaintAnalysisResult:
    """통신사 민원 분석 결과"""
    category: str
    consultation_topic: str
    consultation_type: str
    severity: str
    urgency: str
    satisfaction: int
    resolution_status: str
    keywords: List[str]
    sentiment_score: float
    summary: str
    key_points: List[str]
    action_items: List[str]
    priority_level: int
    department: str
    confidence: float


class ComplaintAnalyzer:
    """
    통신사 민원 분석 전용 오케스트레이터
    
    한국어 특화 모델을 사용하여 통신사 고객 상담을 종합적으로 분석합니다.
    """
    
    def __init__(
        self,
        config_path: str,
        korean_prompt_path: str,
        korean_model_config: KoreanModelConfig
    ):
        """
        초기화
        
        Parameters
        ----------
        config_path : str
            기본 설정 파일 경로
        korean_prompt_path : str
            한국어 프롬프트 설정 파일 경로
        korean_model_config : KoreanModelConfig
            한국어 모델 설정
        """
        self.korean_model_manager = KoreanModelManager(config_path)
        self.korean_model = self.korean_model_manager.load_model("korean", korean_model_config)
        self.korean_prompts = self._load_korean_prompts(korean_prompt_path)
        
        # 기존 LLM 오케스트레이터 (OpenAI/Azure용)
        self.llm_orchestrator = LLMOrchestrator(
            config_path=config_path,
            prompt_config_path=korean_prompt_path,
            model_id="openai"  # 기본값
        )
        
    def _load_korean_prompts(self, prompt_path: str) -> Dict[str, Dict[str, str]]:
        """한국어 프롬프트 로드"""
        with open(prompt_path, encoding='utf-8') as f:
            prompts = yaml.safe_load(f)
        return prompts
    
    async def analyze_complaint(self, conversation_data: List[Dict[str, Any]]) -> ComplaintAnalysisResult:
        """
        통신사 민원 종합 분석
        
        Parameters
        ----------
        conversation_data : List[Dict[str, Any]]
            대화 데이터 (SSM 형식)
            
        Returns
        -------
        ComplaintAnalysisResult
            분석 결과
        """
        # 대화 내용을 텍스트로 변환
        conversation_text = Formatter.format_ssm_as_dialogue(conversation_data)
        
        # 1. 통신사 업무 분야 분류
        classification_result = await self._classify_complaint(conversation_text)
        
        # 2. 통신사 민원 상세 분석
        analysis_result = await self._analyze_complaint_details(conversation_text)
        
        # 3. 통신사 민원 요약
        summary_result = await self._summarize_complaint(conversation_text)
        
        # 4. 우선순위 평가
        priority_result = await self._evaluate_priority(conversation_text)
        
        # 5. 부서 배정
        department_result = await self._assign_department(conversation_text)
        
        # 결과 통합
        return ComplaintAnalysisResult(
            category=classification_result.get("category", "기타"),
            consultation_topic=analysis_result.get("consultationTopic", "기타"),
            consultation_type=analysis_result.get("consultationType", "일반 문의 상담"),
            severity=analysis_result.get("severity", "Medium"),
            urgency=analysis_result.get("urgency", "Medium"),
            satisfaction=analysis_result.get("satisfaction", 3),
            resolution_status=analysis_result.get("resolutionStatus", "Pending"),
            keywords=analysis_result.get("keywords", []),
            sentiment_score=analysis_result.get("sentimentScore", 0.0),
            summary=summary_result.get("summary", ""),
            key_points=summary_result.get("keyPoints", []),
            action_items=summary_result.get("actionItems", []),
            priority_level=priority_result.get("priorityLevel", 3),
            department=department_result.get("primaryDepartment", "모바일일반상담"),
            confidence=classification_result.get("confidence", 0.5)
        )
    
    async def _classify_complaint(self, conversation_text: str) -> Dict[str, Any]:
        """통신사 업무 분야 분류"""
        try:
            # 한국어 모델 사용
            messages = [
                {"role": "user", "content": f"질문: 다음 통신사 고객 상담 내용을 분석하여 적절한 업무 분야로 분류해주세요.\n\ncontext: {conversation_text}"}
            ]
            
            response = self.korean_model.generate(messages)
            
            # JSON 추출
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"category": "기타", "confidence": 0.5, "reason": "분류 실패"}
                
        except Exception as e:
            print(f"통신사 업무 분야 분류 중 에러: {e}")
            return {"category": "기타", "confidence": 0.5, "reason": "에러 발생"}
    
    async def _analyze_complaint_details(self, conversation_text: str) -> Dict[str, Any]:
        """통신사 민원 상세 분석"""
        try:
            messages = [
                {"role": "user", "content": f"질문: 다음 통신사 고객 상담 내용을 종합적으로 분석해주세요.\n\ncontext: {conversation_text}"}
            ]
            
            response = self.korean_model.generate(messages)
            
            # JSON 추출
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {
                    "severity": "Medium",
                    "urgency": "Medium",
                    "satisfaction": 3,
                    "resolutionStatus": "Pending",
                    "keywords": [],
                    "sentimentScore": 0.0,
                    "consultationTopic": "기타",
                    "consultationType": "일반 문의 상담",
                    "analysis": "분석 실패"
                }
                
        except Exception as e:
            print(f"통신사 민원 분석 중 에러: {e}")
            return {
                "severity": "Medium",
                "urgency": "Medium",
                "satisfaction": 3,
                "resolutionStatus": "Pending",
                "keywords": [],
                "sentimentScore": 0.0,
                "consultationTopic": "기타",
                "consultationType": "일반 문의 상담",
                "analysis": "에러 발생"
            }
    
    async def _summarize_complaint(self, conversation_text: str) -> Dict[str, Any]:
        """통신사 민원 요약"""
        try:
            messages = [
                {"role": "user", "content": f"질문: 다음 통신사 고객 상담 내용을 요약해주세요.\n\ncontext: {conversation_text}"}
            ]
            
            response = self.korean_model.generate(messages)
            
            # JSON 추출
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {
                    "summary": "요약 실패",
                    "keyPoints": [],
                    "actionItems": []
                }
                
        except Exception as e:
            print(f"통신사 민원 요약 중 에러: {e}")
            return {
                "summary": "에러 발생",
                "keyPoints": [],
                "actionItems": []
            }
    
    async def _evaluate_priority(self, conversation_text: str) -> Dict[str, Any]:
        """우선순위 평가"""
        try:
            messages = [
                {"role": "user", "content": f"질문: 다음 통신사 고객 민원의 우선순위를 평가해주세요.\n\ncontext: {conversation_text}"}
            ]
            
            response = self.korean_model.generate(messages)
            
            # JSON 추출
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {
                    "priorityLevel": 3,
                    "escalationLevel": 1,
                    "priorityReason": "우선순위 평가 실패",
                    "recommendations": []
                }
                
        except Exception as e:
            print(f"우선순위 평가 중 에러: {e}")
            return {
                "priorityLevel": 3,
                "escalationLevel": 1,
                "priorityReason": "에러 발생",
                "recommendations": []
            }
    
    async def _assign_department(self, conversation_text: str) -> Dict[str, Any]:
        """부서 배정"""
        try:
            messages = [
                {"role": "user", "content": f"질문: 다음 LG U+ 고객 민원을 적절한 부서에 배정해주세요.\n\ncontext: {conversation_text}"}
            ]
            
            response = self.korean_model.generate(messages)
            
            # JSON 추출
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {
                    "primaryDepartment": "모바일일반상담",
                    "secondaryDepartments": [],
                    "reason": "부서 배정 실패",
                    "estimatedProcessingTime": "3-5일"
                }
                
        except Exception as e:
            print(f"부서 배정 중 에러: {e}")
            return {
                "primaryDepartment": "모바일일반상담",
                "secondaryDepartments": [],
                "reason": "에러 발생",
                "estimatedProcessingTime": "3-5일"
            }
    
    async def answer_question(self, conversation_text: str, question: str) -> Dict[str, Any]:
        """
        질의응답
        
        Parameters
        ----------
        conversation_text : str
            대화 내용
        question : str
            질문
            
        Returns
        -------
        Dict[str, Any]
            답변 결과
        """
        try:
            messages = [
                {"role": "user", "content": f"질문: {question}\n\ncontext: {conversation_text}"}
            ]
            
            response = self.korean_model.generate(messages)
            
            # JSON 추출 시도
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {
                    "answer": response,
                    "confidence": 0.7,
                    "source": "통신사 상담 내용 기반"
                }
                
        except Exception as e:
            print(f"질의응답 중 에러: {e}")
            return {
                "answer": "답변 생성 중 오류가 발생했습니다.",
                "confidence": 0.0,
                "source": "에러"
            }
    
    def unload(self):
        """리소스 해제"""
        self.korean_model_manager.unload_all()
        self.llm_orchestrator.manager.unload_all() 