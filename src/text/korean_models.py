# Standard library imports
import os
import torch
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Related third-party imports
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
from peft import AutoPeftModelForCausalLM
from accelerate import PartialState

# Local imports
from src.text.model import LanguageModel


@dataclass
class KoreanModelConfig:
    """한국어 모델 설정"""
    model_type: str = "openchat"  # "openchat", "llama3", "gemma"
    base_model_name: str = ""
    peft_model_name: str = ""
    device: str = "auto"
    torch_dtype: str = "bfloat16"
    max_new_tokens: int = 1024
    temperature: float = 0.1


class KoreanLanguageModel(LanguageModel):
    """
    한국어 특화 언어 모델 (OpenChat)
    
    민원 분석, 분류, 질의응답, 요약 기능을 제공합니다.
    """
    
    def __init__(self, config: KoreanModelConfig):
        super().__init__(config.__dict__)
        self.config = config
        self.device_string = PartialState().process_index
        
        print(f"Loading Korean model: {config.model_type}")
        print(f"Base model: {config.base_model_name}")
        
        # 모델 로드
        if config.peft_model_name:
            self.model = self._load_peft_model()
        else:
            self.model = self._load_base_model()
            
        # 토크나이저 로드
        self.tokenizer = self._load_tokenizer()
        
        # 생성 설정
        self._setup_generation_config()
        
        self.model.eval()
        
    def _load_base_model(self):
        """베이스 모델 로드"""
        model_kwargs = {
            "torch_dtype": getattr(torch, self.config.torch_dtype),
            "return_dict": True,
            "device_map": {'': self.device_string},
        }
        
        if self.config.model_type == "openchat":
            model_kwargs["attn_implementation"] = "flash_attention_2"
        elif self.config.model_type == "llama3":
            model_kwargs["attn_implementation"] = "flash_attention_2"
        elif self.config.model_type in ["gemma", "gemma2"]:
            model_kwargs["attn_implementation"] = "eager"
            
        model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model_name,
            **model_kwargs
        )
        
        # OpenChat 특별 설정
        if self.config.model_type == "openchat":
            model.generation_config.temperature = None
            model.generation_config.top_p = None
            
        return model
    
    def _load_peft_model(self):
        """PEFT 모델 로드"""
        model_kwargs = {
            "torch_dtype": getattr(torch, self.config.torch_dtype),
            "return_dict": True,
            "is_trainable": True,
            "device_map": {'': self.device_string},
        }
        
        if self.config.model_type == "openchat":
            model_kwargs["attn_implementation"] = "flash_attention_2"
        elif self.config.model_type == "llama3":
            model_kwargs["attn_implementation"] = "flash_attention_2"
        elif self.config.model_type in ["gemma", "gemma2"]:
            model_kwargs["attn_implementation"] = "eager"
            
        model = AutoPeftModelForCausalLM.from_pretrained(
            self.config.peft_model_name,
            **model_kwargs
        )
        
        # OpenChat 특별 설정
        if self.config.model_type == "openchat":
            model.generation_config.temperature = None
            model.generation_config.top_p = None
            
        return model
    
    def _load_tokenizer(self):
        """토크나이저 로드"""
        tokenizer = AutoTokenizer.from_pretrained(self.config.base_model_name)
        
        if self.config.model_type == "openchat":
            tokenizer.padding_side = "right"
            if tokenizer.pad_token is None:
                tokenizer.add_special_tokens({'pad_token': '<unk>'})
                self.model.resize_token_embeddings(len(tokenizer))
        elif self.config.model_type in ["gemma", "gemma2"]:
            tokenizer.padding_side = "right"
        elif self.config.model_type == "llama3":
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            tokenizer.convert_tokens_to_ids("<|eot_id|>")
            
        return tokenizer
    
    def _setup_generation_config(self):
        """생성 설정 구성"""
        self.model.generation_config.temperature = self.config.temperature
        self.model.generation_config.max_new_tokens = self.config.max_new_tokens
        self.model.generation_config.pad_token_id = self.tokenizer.eos_token_id
        
    def _create_prompt(self, question: str, context: str = "") -> str:
        """프롬프트 생성"""
        system_msg = "다음의 민원 상담에 대한 context를 기반으로 질문에 대한 적절한 답변을 한국어로 작성하세요. "
        
        if self.config.model_type == "openchat":
            chat = [{"role": "user", "content": f"{system_msg + question}"}]
        elif self.config.model_type in ["gemma", "gemma2"]:
            chat = [{"role": "user", "content": f"{system_msg + question}"}]
        elif self.config.model_type == "llama3":
            chat = [
                {"role": "system", "content": f"{system_msg}"},
                {"role": "user", "content": f"{question}"}
            ]
            
        self.tokenizer.use_default_system_prompt = False
        prompt = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        return prompt
    
    def _extract_response(self, response) -> str:
        """응답에서 실제 텍스트 추출"""
        if self.config.model_type == "openchat":
            find_start = "GPT4 Correct Assistant:"
            find_end = "<|end_of_turn|>"
        elif self.config.model_type in ["gemma", "gemma2"]:
            find_start = "<start_of_turn>model"
            find_end = "<end_of_turn>"
        elif self.config.model_type == "llama3":
            find_start = "<|start_header_id|>assistant<|end_header_id|>"
            find_end = "<|eot_id|>"
            
        decode = self.tokenizer.batch_decode(response)[0]
        start_index = decode.rfind(find_start)
        end_index = decode.rfind(find_end)
        
        if start_index != -1:
            if end_index != -1 and end_index > start_index:
                return decode[start_index + len(find_start) + 1 : end_index].strip()
            else:
                return decode[start_index + len(find_start) + 1 :].strip()
        else:
            return decode
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        텍스트 생성
        
        Parameters
        ----------
        messages : List[Dict[str, str]]
            메시지 리스트
        max_new_tokens : Optional[int]
            최대 생성 토큰 수
        **kwargs
            추가 키워드 인자
            
        Returns
        -------
        str
            생성된 텍스트
        """
        try:
            torch.cuda.empty_cache()
            
            # 메시지에서 질문 추출
            question = ""
            context = ""
            
            for message in messages:
                if message.get("role") == "user":
                    content = message.get("content", "")
                    if "질문:" in content:
                        question = content.split("질문:")[-1].strip()
                    else:
                        question = content
                elif message.get("role") == "system":
                    context = message.get("content", "")
            
            # 프롬프트 생성
            prompt = self._create_prompt(question, context)
            inputs = self.tokenizer(prompt, return_tensors="pt")
            inputs = {k: v.to(self.device_string) for k, v in inputs.items()}
            
            # 생성
            response = self.model.generate(
                **inputs,
                generation_config=self.model.generation_config,
                **kwargs
            )
            
            # 응답 추출
            answer = self._extract_response(response)
            return answer
            
        except Exception as e:
            print(f"한국어 모델 생성 중 에러 발생: {e}")
            return "에러가 발생했습니다."
    
    def unload(self):
        """모델 언로드"""
        del self.model
        del self.tokenizer
        torch.cuda.empty_cache()
        print(f"한국어 모델 '{self.config.model_type}' 언로드 완료.")


class KoreanModelManager:
    """한국어 모델 관리자"""
    
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