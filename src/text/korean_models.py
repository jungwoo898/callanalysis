# Standard library imports
import os
import torch
import pickle
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import re
import time
import gc
import requests
import json
from dotenv import load_dotenv

# Related third-party imports
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import openai
from openai import OpenAI

# Local imports
from src.text.model import LanguageModel

# .env 파일 로드
load_dotenv()


class APIModelHandler:
    """
    API 기반 모델 핸들러
    Hugging Face API, ChatGPT API, Azure API를 통합 관리
    """
    
    def __init__(self):
        """API 핸들러 초기화"""
        # .env 파일에서 API 키 로드
        self.hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        # API 클라이언트 초기화
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
        else:
            self.openai_client = None
            
        if self.azure_key and self.azure_endpoint:
            self.azure_client = OpenAI(
                api_key=self.azure_key,
                base_url=self.azure_endpoint
            )
        else:
            self.azure_client = None
    
    async def generate_with_api(
        self, 
        messages: List[Dict[str, str]], 
        api_type: str = "openai",
        model_name: str = "gpt-3.5-turbo"
    ) -> str:
        """
        API를 통해 텍스트 생성
        
        Parameters
        ----------
        messages : List[Dict[str, str]]
            메시지 리스트
        api_type : str
            API 타입 (openai, azure, huggingface)
        model_name : str
            모델 이름
            
        Returns
        -------
        str
            생성된 텍스트
        """
        try:
            if api_type == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2000
                )
                return response.choices[0].message.content
                
            elif api_type == "azure" and self.azure_client:
                response = self.azure_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2000
                )
                return response.choices[0].message.content
                
            elif api_type == "huggingface" and self.hf_token:
                # Hugging Face Inference API 사용
                api_url = f"https://api-inference.huggingface.co/models/{model_name}"
                headers = {"Authorization": f"Bearer {self.hf_token}"}
                
                # 메시지를 텍스트로 변환
                text = self._messages_to_text(messages)
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    json={"inputs": text, "parameters": {"max_new_tokens": 2000}}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "")
                    return str(result)
                else:
                    raise Exception(f"Hugging Face API 오류: {response.status_code}")
            
            else:
                raise Exception(f"사용 가능한 API가 없습니다: {api_type}")
                
        except Exception as e:
            print(f"API 호출 실패 ({api_type}): {e}")
            return "API 호출에 실패했습니다."
    
    def _messages_to_text(self, messages: List[Dict[str, str]]) -> str:
        """메시지 리스트를 텍스트로 변환"""
        text = ""
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            if role == "system":
                text += f"시스템: {content}\n"
            elif role == "user":
                text += f"사용자: {content}\n"
            elif role == "assistant":
                text += f"어시스턴트: {content}\n"
        return text
    
    def get_available_apis(self) -> List[str]:
        """사용 가능한 API 목록 반환"""
        available = []
        if self.openai_key:
            available.append("openai")
        if self.azure_key and self.azure_endpoint:
            available.append("azure")
        if self.hf_token:
            available.append("huggingface")
        return available


class ModelCache:
    """
    모델 캐싱 시스템
    메모리 효율적인 모델 로딩과 캐싱을 관리합니다.
    """
    
    def __init__(self, cache_dir: str = "/app/.cache/models"):
        """
        모델 캐시 초기화
        
        Parameters
        ----------
        cache_dir : str
            캐시 디렉토리 경로
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_models = {}
        self.model_metadata = {}
        
        # 캐시 메타데이터 로드
        self._load_metadata()
    
    def _load_metadata(self):
        """캐시 메타데이터를 로드합니다."""
        metadata_file = self.cache_dir / "metadata.pkl"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'rb') as f:
                    self.model_metadata = pickle.load(f)
            except Exception as e:
                print(f"캐시 메타데이터 로드 실패: {e}")
                self.model_metadata = {}
    
    def _save_metadata(self):
        """캐시 메타데이터를 저장합니다."""
        metadata_file = self.cache_dir / "metadata.pkl"
        try:
            with open(metadata_file, 'wb') as f:
                pickle.dump(self.model_metadata, f)
        except Exception as e:
            print(f"캐시 메타데이터 저장 실패: {e}")
    
    def _get_model_hash(self, model_name: str, model_type: str) -> str:
        """모델의 해시값을 생성합니다."""
        content = f"{model_name}_{model_type}_{torch.__version__}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_cached_model(self, model_name: str, model_type: str):
        """캐시된 모델을 가져옵니다."""
        model_hash = self._get_model_hash(model_name, model_type)
        cache_key = f"{model_name}_{model_type}"
        
        # 메모리에 로드된 모델 확인
        if cache_key in self.loaded_models:
            return self.loaded_models[cache_key]
        
        # 디스크 캐시 확인
        cache_file = self.cache_dir / f"{model_hash}.pkl"
        if cache_file.exists():
            try:
                print(f"캐시에서 모델 로드 중: {model_name}")
                with open(cache_file, 'rb') as f:
                    model_data = pickle.load(f)
                
                # 모델을 메모리에 로드
                self.loaded_models[cache_key] = model_data
                return model_data
            except Exception as e:
                print(f"캐시 로드 실패: {e}")
        
        return None
    
    def cache_model(self, model_name: str, model_type: str, model_data: Any):
        """모델을 캐시에 저장합니다."""
        model_hash = self._get_model_hash(model_name, model_type)
        cache_key = f"{model_name}_{model_type}"
        
        # 메모리에 저장
        self.loaded_models[cache_key] = model_data
        
        # 디스크에 저장
        cache_file = self.cache_dir / f"{model_hash}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(model_data, f)
            
            # 메타데이터 업데이트
            self.model_metadata[cache_key] = {
                'hash': model_hash,
                'timestamp': time.time(),
                'size': cache_file.stat().st_size
            }
            self._save_metadata()
            
            print(f"모델 캐시 저장 완료: {model_name}")
        except Exception as e:
            print(f"모델 캐시 저장 실패: {e}")
    
    def unload_model(self, model_name: str, model_type: str):
        """모델을 메모리에서 해제합니다."""
        cache_key = f"{model_name}_{model_type}"
        if cache_key in self.loaded_models:
            del self.loaded_models[cache_key]
            gc.collect()  # 가비지 컬렉션 강제 실행
            print(f"모델 메모리 해제: {model_name}")
    
    def cleanup_old_cache(self, max_age_days: int = 30):
        """오래된 캐시를 정리합니다."""
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        
        for cache_key, metadata in list(self.model_metadata.items()):
            if current_time - metadata['timestamp'] > max_age_seconds:
                cache_file = self.cache_dir / f"{metadata['hash']}.pkl"
                if cache_file.exists():
                    cache_file.unlink()
                del self.model_metadata[cache_key]
        
        self._save_metadata()
        print(f"오래된 캐시 정리 완료 (최대 {max_age_days}일)")


@dataclass
class KoreanModelConfig:
    """한국어 모델 설정 (API 우선)"""
    api_type: str = "openai"  # "openai", "azure", "huggingface"
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.3
    max_tokens: int = 2000


class KoreanLanguageModel(LanguageModel):
    """
    API 기반 한국어 언어 모델
    
    OpenAI, Azure, Hugging Face API를 통해 민원 분석, 분류, 질의응답, 요약 기능을 제공합니다.
    """
    
    def __init__(self, config: KoreanModelConfig):
        super().__init__(config.__dict__)
        self.config = config
        self.api_handler = APIModelHandler()
        
        print(f"API 기반 한국어 모델 초기화: {config.api_type}")
        print(f"사용 가능한 API: {self.api_handler.get_available_apis()}")
        
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        API를 통해 텍스트 생성
        
        Parameters
        ----------
        messages : List[Dict[str, str]]
            메시지 리스트
        max_new_tokens : Optional[int]
            최대 생성 토큰 수 (사용하지 않음, config에서 관리)
        **kwargs
            추가 키워드 인자
            
        Returns
        -------
        str
            생성된 텍스트
        """
        try:
            # API 타입 우선순위 결정
            available_apis = self.api_handler.get_available_apis()
            
            if self.config.api_type in available_apis:
                api_type = self.config.api_type
            elif "openai" in available_apis:
                api_type = "openai"
            elif "azure" in available_apis:
                api_type = "azure"
            elif "huggingface" in available_apis:
                api_type = "huggingface"
            else:
                return "사용 가능한 API가 없습니다."
            
            return await self.api_handler.generate_with_api(
                messages=messages,
                api_type=api_type,
                model_name=self.config.model_name
            )
            
        except Exception as e:
            print(f"API 기반 텍스트 생성 실패: {e}")
            return "텍스트 생성에 실패했습니다."
    
    def unload(self):
        """리소스 정리 (API 기반이므로 별도 정리 불필요)"""
        print("API 기반 모델 언로드 완료")


class KoreanModelManager:
    """API 기반 한국어 모델 관리자"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.models = {}
        
    def load_model(self, model_id: str, config: KoreanModelConfig) -> KoreanLanguageModel:
        """모델 로드"""
        if model_id not in self.models:
            self.models[model_id] = KoreanLanguageModel(config)
        return self.models[model_id]
    
    def get_model(self, model_id: str) -> Optional[KoreanLanguageModel]:
        """모델 가져오기"""
        return self.models.get(model_id)
    
    def unload_model(self, model_id: str):
        """모델 언로드"""
        if model_id in self.models:
            self.models[model_id].unload()
            del self.models[model_id]
    
    def unload_all(self):
        """모든 모델 언로드"""
        for model_id in list(self.models.keys()):
            self.unload_model(model_id)


class LanguageDetector:
    """
    자동 언어 감지 클래스 (API 기반)
    한국어와 다른 언어를 구분하여 적절한 모델을 선택합니다.
    """
    
    def __init__(self):
        """
        언어 감지 모델을 초기화합니다.
        """
        try:
            # 다국어 언어 감지 모델 로드 (가벼운 로컬 모델 사용)
            self.language_detector = pipeline(
                "text-classification",
                model="papluca/xlm-roberta-base-language-detection",
                device=0 if torch.cuda.is_available() else -1
            )
            print("✅ 언어 감지 모델이 로드되었습니다.")
        except Exception as e:
            print(f"⚠️ 언어 감지 모델 로드 실패: {e}")
            self.language_detector = None

    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        텍스트의 언어를 감지합니다.
        
        Parameters
        ----------
        text : str
            감지할 텍스트
            
        Returns
        -------
        Dict[str, Any]
            언어 감지 결과
        """
        if not self.language_detector:
            return {"language": "ko", "confidence": 1.0, "is_korean": True}
        
        try:
            # 텍스트 전처리
            cleaned_text = self._clean_text(text)
            if len(cleaned_text) < 10:
                return {"language": "ko", "confidence": 1.0, "is_korean": True}
            
            # 언어 감지
            result = self.language_detector(cleaned_text[:512])  # 최대 512자만 사용
            
            detected_lang = result[0]['label'].lower()
            confidence = result[0]['score']
            
            # 한국어 여부 확인
            is_korean = detected_lang in ['ko', 'korean', 'ko-kr']
            
            return {
                "language": detected_lang,
                "confidence": confidence,
                "is_korean": is_korean
            }
            
        except Exception as e:
            print(f"언어 감지 오류: {e}")
            return {"language": "ko", "confidence": 1.0, "is_korean": True}

    def _clean_text(self, text: str) -> str:
        """
        텍스트를 정제합니다.
        
        Parameters
        ----------
        text : str
            정제할 텍스트
            
        Returns
        -------
        str
            정제된 텍스트
        """
        # 특수문자 제거
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def is_korean_audio(self, text: str, threshold: float = 0.7) -> bool:
        """
        오디오가 한국어인지 확인합니다.
        
        Parameters
        ----------
        text : str
            확인할 텍스트
        threshold : float
            한국어 판정 임계값
            
        Returns
        -------
        bool
            한국어 여부
        """
        result = self.detect_language(text)
        return result["is_korean"] and result["confidence"] >= threshold


class KoreanModels:
    """
    API 기반 한국어 모델들을 관리하는 클래스
    """

    def __init__(self, device: str = "cuda"):
        """
        한국어 모델들을 초기화합니다.

        Parameters
        ----------
        device : str
            사용할 디바이스 (cuda/cpu) - API 기반이므로 실제로는 사용하지 않음
        """
        self.device = device
        self.language_detector = LanguageDetector()
        self.api_handler = APIModelHandler()
        
        # API 사용 가능 여부 확인
        available_apis = self.api_handler.get_available_apis()
        print(f"🔧 API 기반 한국어 모델 초기화 완료")
        print(f"📡 사용 가능한 API: {available_apis}")
        
        if not available_apis:
            print("⚠️ 경고: 사용 가능한 API가 없습니다. 환경 변수를 확인해주세요.")

    async def analyze_sentiment_with_api(self, text: str) -> str:
        """
        API를 통해 감정 분석을 수행합니다.

        Parameters
        ----------
        text : str
            분석할 텍스트

        Returns
        -------
        str
            감정 분석 결과 (긍정/부정/중립)
        """
        try:
            messages = [
                {"role": "system", "content": "당신은 한국어 감정 분석 전문가입니다. 다음 텍스트의 감정을 '긍정', '부정', '중립' 중 하나로 분류해주세요."},
                {"role": "user", "content": f"다음 텍스트의 감정을 분석해주세요: {text}"}
            ]
            
            response = await self.api_handler.generate_with_api(
                messages=messages,
                api_type="openai",
                model_name="gpt-3.5-turbo"
            )
            
            # 응답에서 감정 추출
            if "긍정" in response:
                return "긍정"
            elif "부정" in response:
                return "부정"
            else:
                return "중립"
                
        except Exception as e:
            print(f"API 감정 분석 오류: {e}")
            return "중립"

    async def analyze_sentiment_batch(self, texts: List[str]) -> List[str]:
        """
        배치로 감정 분석을 수행합니다.

        Parameters
        ----------
        texts : List[str]
            분석할 텍스트 리스트

        Returns
        -------
        List[str]
            감정 분석 결과 리스트
        """
        results = []
        for text in texts:
            result = await self.analyze_sentiment_with_api(text)
            results.append(result)
        return results

    async def detect_profanity_with_api(self, text: str) -> bool:
        """
        API를 통해 비속어를 감지합니다.

        Parameters
        ----------
        text : str
            감지할 텍스트

        Returns
        -------
        bool
            비속어 포함 여부
        """
        try:
            messages = [
                {"role": "system", "content": "당신은 한국어 비속어 감지 전문가입니다. 다음 텍스트에 비속어나 부적절한 표현이 포함되어 있는지 '예' 또는 '아니오'로 답변해주세요."},
                {"role": "user", "content": f"다음 텍스트에 비속어가 포함되어 있나요: {text}"}
            ]
            
            response = await self.api_handler.generate_with_api(
                messages=messages,
                api_type="openai",
                model_name="gpt-3.5-turbo"
            )
            
            return "예" in response or "yes" in response.lower()
                
        except Exception as e:
            print(f"API 비속어 감지 오류: {e}")
            return False

    async def detect_profanity_batch(self, texts: List[str]) -> List[bool]:
        """
        배치로 비속어를 감지합니다.

        Parameters
        ----------
        texts : List[str]
            감지할 텍스트 리스트

        Returns
        -------
        List[bool]
            비속어 포함 여부 리스트
        """
        results = []
        for text in texts:
            result = await self.detect_profanity_with_api(text)
            results.append(result)
        return results

    async def classify_speaker_with_api(self, text: str) -> str:
        """
        API를 통해 화자 역할을 분류합니다.

        Parameters
        ----------
        text : str
            분류할 텍스트

        Returns
        -------
        str
            화자 역할 (고객/상담원)
        """
        try:
            messages = [
                {"role": "system", "content": "당신은 고객 상담 분석 전문가입니다. 다음 발화가 '고객'인지 '상담원'인지 분류해주세요."},
                {"role": "user", "content": f"다음 발화의 화자를 분류해주세요: {text}"}
            ]
            
            response = await self.api_handler.generate_with_api(
                messages=messages,
                api_type="openai",
                model_name="gpt-3.5-turbo"
            )
            
            if "상담원" in response or "agent" in response.lower():
                return "상담원"
            else:
                return "고객"
                
        except Exception as e:
            print(f"API 화자 분류 오류: {e}")
            return "고객"

    async def classify_speaker_batch(self, texts: List[str]) -> List[str]:
        """
        배치로 화자 역할을 분류합니다.

        Parameters
        ----------
        texts : List[str]
            분류할 텍스트 리스트

        Returns
        -------
        List[str]
            화자 역할 리스트 (고객/상담원)
        """
        results = []
        for text in texts:
            result = await self.classify_speaker_with_api(text)
            results.append(result)
        return results

    def is_korean_content(self, text: str) -> bool:
        """
        콘텐츠가 한국어인지 확인합니다.

        Parameters
        ----------
        text : str
            확인할 텍스트

        Returns
        -------
        bool
            한국어 여부
        """
        return self.language_detector.is_korean_audio(text)

    def get_model_status(self) -> Dict[str, Any]:
        """
        모델 상태를 반환합니다.

        Returns
        -------
        Dict[str, Any]
            모델 상태 정보
        """
        return {
            "api_available": bool(self.api_handler.get_available_apis()),
            "available_apis": self.api_handler.get_available_apis(),
            "language_detector": self.language_detector.language_detector is not None
        } 