# Standard library imports
import re
import json
import asyncio
from typing import Annotated, Optional, Dict, Any, List
import os

# Related third-party imports
import yaml
import openai
import time

# Local imports
from src.text.model import LanguageModelManager
from src.audio.utils import Formatter


class LLMOrchestrator:
    """
    A handler to perform specific LLM tasks such as classification or sentiment analysis.

    This class uses a language model to perform different tasks by dynamically changing the prompt.

    Parameters
    ----------
    config_path : str
        Path to the configuration file for the language model manager.
    prompt_config_path : str
        Path to the configuration file containing prompts for different tasks.
    model_id : str, optional
        Identifier of the model to use. Defaults to "llama".
    cache_size : int, optional
        Cache size for the language model manager. Defaults to 2.

    Attributes
    ----------
    manager : LanguageModelManager
        An instance of LanguageModelManager for interacting with the model.
    model_id : str
        The identifier of the language model in use.
    prompts : Dict[str, Dict[str, str]]
        A dictionary containing prompts for different tasks.
    """

    def __init__(
            self,
            config_path: Annotated[str, "Path to the configuration file"],
            prompt_config_path: Annotated[str, "Path to the prompt configuration file"],
            model_id: Annotated[str, "Language model identifier"] = "llama",
            cache_size: Annotated[int, "Cache size for the language model manager"] = 2,
    ):
        """
        Initializes the LLMOrchestrator with a language model manager and loads prompts.

        Parameters
        ----------
        config_path : str
            Path to the configuration file for the language model manager.
        prompt_config_path : str
            Path to the configuration file containing prompts for different tasks.
        model_id : str, optional
            Identifier of the model to use. Defaults to "llama".
        cache_size : int, optional
            Cache size for the language model manager. Defaults to 2.
        """
        self.manager = LanguageModelManager(config_path=config_path, cache_size=cache_size)
        self.model_id = model_id
        self.prompts = self._load_prompts(prompt_config_path)

    @staticmethod
    def _load_prompts(prompt_config_path: str) -> Dict[str, Dict[str, str]]:
        """
        Loads prompts from the prompt configuration file.

        Parameters
        ----------
        prompt_config_path : str
            Path to the prompt configuration file.

        Returns
        -------
        Dict[str, Dict[str, str]]
            A dictionary containing prompts for different tasks.
        """
        with open(prompt_config_path, encoding='utf-8') as f:
            prompts = yaml.safe_load(f)
        return prompts

    @staticmethod
    def extract_json(
            response: Annotated[str, "The response string to extract JSON from"]
    ) -> Annotated[Optional[Dict[str, Any]], "Extracted JSON as a dictionary or None if not found"]:
        """
        Extracts the last valid JSON object from a given response string.

        Parameters
        ----------
        response : str
            The response string to extract JSON from.

        Returns
        -------
        Optional[Dict[str, Any]]
            The last valid JSON dictionary if successfully extracted and parsed, otherwise None.
        """
        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        matches = re.findall(json_pattern, response)
        for match in reversed(matches):
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        return None

    async def generate(
            self,
            prompt_name: Annotated[str, "The name of the prompt to use (e.g., 'Classification', 'SentimentAnalysis')"],
            user_input: Annotated[Any, "The user's context or input data"],
            system_input: Annotated[Optional[Any], "The system's context or input data"] = None
    ) -> Annotated[Dict[str, Any], "Task results or error dictionary"]:
        """
        Performs the specified LLM task using the selected prompt, supporting both user and optional system contexts.
        """
        if prompt_name not in self.prompts:
            return {"error": f"Prompt '{prompt_name}' is not defined in prompt.yaml."}

        system_prompt_template = self.prompts[prompt_name].get('system', '')
        user_prompt_template = self.prompts[prompt_name].get('user', '')

        if not system_prompt_template or not user_prompt_template:
            return {"error": f"Prompts for '{prompt_name}' are incomplete."}

        formatted_user_input = Formatter.format_ssm_as_dialogue(user_input)

        if system_input:
            system_prompt = system_prompt_template.format(system_context=system_input)
        else:
            system_prompt = system_prompt_template

        user_prompt = user_prompt_template.format(user_context=formatted_user_input)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await self.manager.generate(
            model_id=self.model_id,
            messages=messages,
            max_new_tokens=10000,
        )
        print(response)

        dict_obj = self.extract_json(response)
        if dict_obj:
            return dict_obj
        else:
            return {"error": "No valid JSON object found in the response."}


class LLMResultHandler:
    """
    A handler class to process and validate the output from a Language Learning Model (LLM)
    and format structured data.

    This class ensures that the input data conforms to expected formats and applies fallback
    mechanisms to maintain data integrity.

    Methods
    -------
    validate_and_fallback(llm_result, ssm)
        Validates the LLM result against structured speaker metadata and applies fallback.
    _fallback(ssm)
        Applies fallback formatting to the speaker data.
    log_result(ssm, llm_result)
        Logs the final processed data and the original LLM result.
    """

    def __init__(self):
        """
        Initializes the LLMResultHandler class.
        """
        pass

    def validate_and_fallback(
            self,
            llm_result: Annotated[Dict[str, str], "LLM result with customer and CSR speaker identifiers"],
            ssm: Annotated[List[Dict[str, Any]], "List of sentences with speaker metadata"]
    ) -> Annotated[List[Dict[str, Any]], "Processed speaker metadata"]:
        """
        Validates the LLM result and applies corrections to the speaker metadata.

        Parameters
        ----------
        llm_result : dict
            A dictionary containing speaker identifiers for 'Customer' and 'CSR'.
        ssm : list of dict
            A list of dictionaries where each dictionary represents a sentence with
            metadata, including the 'speaker'.

        Returns
        -------
        list of dict
            The processed speaker metadata with standardized speaker labels.

        Examples
        --------
        >>> result = {"Customer": "Speaker 1", "CSR": "Speaker 2"}
        >>> ssm_ = [{"speaker": "Speaker 1", "text": "Hello!"}, {"speaker": "Speaker 2", "text": "Hi!"}]
        >>> handler = LLMResultHandler()
        >>> handler.validate_and_fallback(llm_result, ssm)
        [{'speaker': 'Customer', 'text': 'Hello!'}, {'speaker': 'CSR', 'text': 'Hi!'}]
        """
        if not isinstance(llm_result, dict):
            return self._fallback(ssm)

        if "Customer" not in llm_result or "CSR" not in llm_result:
            return self._fallback(ssm)

        customer_speaker = llm_result["Customer"]
        csr_speaker = llm_result["CSR"]

        speaker_pattern = r"^Speaker\s+\d+$"

        if (not re.match(speaker_pattern, customer_speaker)) or (not re.match(speaker_pattern, csr_speaker)):
            return self._fallback(ssm)

        ssm_speakers = {sentence["speaker"] for sentence in ssm}
        if customer_speaker not in ssm_speakers or csr_speaker not in ssm_speakers:
            return self._fallback(ssm)

        for sentence in ssm:
            if sentence["speaker"] == csr_speaker:
                sentence["speaker"] = "CSR"
            elif sentence["speaker"] == customer_speaker:
                sentence["speaker"] = "Customer"
            else:
                sentence["speaker"] = "Customer"

        return ssm

    @staticmethod
    def _fallback(
            ssm: Annotated[List[Dict[str, Any]], "List of sentences with speaker metadata"]
    ) -> Annotated[List[Dict[str, Any]], "Fallback speaker metadata"]:
        """
        Applies fallback formatting to speaker metadata when validation fails.

        Parameters
        ----------
        ssm : list of dict
            A list of dictionaries representing sentences with speaker metadata.

        Returns
        -------
        list of dict
            The speaker metadata with fallback formatting applied.

        Examples
        --------
        >>> ssm_ = [{"speaker": "Speaker 1", "text": "Hello!"}, {"speaker": "Speaker 2", "text": "Hi!"}]
        >>> handler = LLMResultHandler()
        >>> handler._fallback(ssm)
        [{'speaker': 'CSR', 'text': 'Hello!'}, {'speaker': 'Customer', 'text': 'Hi!'}]
        """
        if len(ssm) > 0:
            first_speaker = ssm[0]["speaker"]
            for sentence in ssm:
                if sentence["speaker"] == first_speaker:
                    sentence["speaker"] = "CSR"
                else:
                    sentence["speaker"] = "Customer"
        return ssm

    @staticmethod
    def log_result(
            ssm: Annotated[List[Dict[str, Any]], "Final processed speaker metadata"],
            llm_result: Annotated[Dict[str, str], "Original LLM result"]
    ) -> None:
        """
        Logs the final processed speaker metadata and the original LLM result.

        Parameters
        ----------
        ssm : list of dict
            The processed speaker metadata.
        llm_result : dict
            The original LLM result.

        Returns
        -------
        None

        Examples
        --------
        >>> ssm_ = [{"speaker": "CSR", "text": "Hello!"}, {"speaker": "Customer", "text": "Hi!"}]
        >>> result = {"Customer": "Speaker 1", "CSR": "Speaker 2"}
        >>> handler = LLMResultHandler()
        >>> handler.log_result(ssm, llm_result)
        Final SSM: [{'speaker': 'CSR', 'text': 'Hello!'}, {'speaker': 'Customer', 'text': 'Hi!'}]
        LLM Result: {'Customer': 'Speaker 1', 'CSR': 'Speaker 2'}
        """
        print("Final SSM:", ssm)
        print("LLM Result:", llm_result)


class LLMHandler:
    """
    A class to handle interactions with OpenAI's GPT models for various text analysis tasks.
    """

    def __init__(self):
        """
        Initializes the LLMHandler with OpenAI API configuration.
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        openai.api_key = self.api_key
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        
        # 재시도 설정
        self.max_retries = 3
        self.retry_delay = 1

    async def generate(
            self,
            task_type: str,
            user_input: Optional[Any] = None,
            system_input: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generates responses for different analysis tasks using OpenAI's GPT models.

        Parameters
        ----------
        task_type : str
            The type of analysis task (e.g., "Classification", "SentimentAnalysis").
        user_input : Any, optional
            The user input data for the analysis.
        system_input : Any, optional
            Additional system input data (e.g., topics for topic detection).

        Returns
        -------
        Dict[str, Any]
            The generated response from the LLM.

        Raises
        ------
        Exception
            If the API call fails after all retry attempts.
        """
        for attempt in range(self.max_retries):
            try:
                # API 키 재검증
                if not self.api_key:
                    raise ValueError("OpenAI API key is missing")
                
                # API 할당량 확인 (간단한 테스트)
                if attempt == 0:
                    try:
                        await self.client.models.list()
                    except Exception as e:
                        if "quota" in str(e).lower() or "rate" in str(e).lower():
                            raise Exception(f"API quota exceeded or rate limited: {e}")
                
                # 프롬프트 생성
                prompt = self._create_prompt(task_type, user_input, system_input)
                
                # API 호출
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": prompt["system"]},
                        {"role": "user", "content": prompt["user"]}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                # 응답 파싱
                result = self._parse_response(task_type, response.choices[0].message.content)
                return result
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"LLM API call failed after {self.max_retries} attempts: {e}")
                    # 폴백 응답 반환
                    return self._get_fallback_response(task_type)
                
                print(f"LLM API call attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))

    def _create_prompt(self, task_type: str, user_input: Any, system_input: Any) -> Dict[str, str]:
        """
        Creates appropriate prompts for different task types.
        
        Parameters
        ----------
        task_type : str
            The type of analysis task.
        user_input : Any
            The user input data.
        system_input : Any
            Additional system input data.
            
        Returns
        -------
        Dict[str, str]
            Dictionary containing system and user prompts.
        """
        # 기본 시스템 프롬프트
        system_prompt = "당신은 한국어 음성 대화 분석 전문가입니다. 정확하고 일관된 분석을 제공해주세요."
        
        if task_type == "Classification":
            system_prompt += " 화자 역할을 분류해주세요 (고객/상담원)."
            user_prompt = f"다음 대화에서 각 화자의 역할을 분류해주세요:\n{user_input}"
            
        elif task_type == "SentimentAnalysis":
            system_prompt += " 감정 분석을 수행해주세요 (긍정/부정/중립)."
            user_prompt = f"다음 대화의 감정을 분석해주세요:\n{user_input}"
            
        elif task_type == "ProfanityWordDetection":
            system_prompt += " 비속어나 부적절한 표현을 감지해주세요."
            user_prompt = f"다음 대화에서 비속어나 부적절한 표현을 찾아주세요:\n{user_input}"
            
        elif task_type == "Summary":
            system_prompt += " 대화 내용을 요약해주세요."
            user_prompt = f"다음 대화를 요약해주세요:\n{user_input}"
            
        elif task_type == "ConflictDetection":
            system_prompt += " 갈등이나 문제 상황을 감지해주세요."
            user_prompt = f"다음 대화에서 갈등이나 문제 상황이 있는지 확인해주세요:\n{user_input}"
            
        elif task_type == "TopicDetection":
            system_prompt += " 주제를 분류해주세요."
            user_prompt = f"다음 대화의 주제를 다음 중에서 선택해주세요:\n{system_input}\n\n대화 내용:\n{user_input}"
            
        else:
            system_prompt += " 일반적인 분석을 수행해주세요."
            user_prompt = f"다음 내용을 분석해주세요:\n{user_input}"
        
        return {"system": system_prompt, "user": user_prompt}

    def _parse_response(self, task_type: str, response: str) -> Dict[str, Any]:
        """
        Parses the LLM response based on task type.
        
        Parameters
        ----------
        task_type : str
            The type of analysis task.
        response : str
            The raw response from the LLM.
            
        Returns
        -------
        Dict[str, Any]
            Parsed response data.
        """
        try:
            # 기본 파싱 로직
            if task_type == "Classification":
                return {"speaker_roles": response}
            elif task_type == "SentimentAnalysis":
                return {"sentiment": response}
            elif task_type == "ProfanityWordDetection":
                return {"profanity": response}
            elif task_type == "Summary":
                return {"summary": response}
            elif task_type == "ConflictDetection":
                return {"conflict": "갈등" in response or "문제" in response}
            elif task_type == "TopicDetection":
                return {"topic": response}
            else:
                return {"result": response}
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return self._get_fallback_response(task_type)

    def _get_fallback_response(self, task_type: str) -> Dict[str, Any]:
        """
        Provides fallback responses when LLM API fails.
        
        Parameters
        ----------
        task_type : str
            The type of analysis task.
            
        Returns
        -------
        Dict[str, Any]
            Fallback response data.
        """
        fallbacks = {
            "Classification": {"speaker_roles": "화자 역할 분류 실패"},
            "SentimentAnalysis": {"sentiment": "중립"},
            "ProfanityWordDetection": {"profanity": "비속어 감지 실패"},
            "Summary": {"summary": "요약 생성 실패"},
            "ConflictDetection": {"conflict": False},
            "TopicDetection": {"topic": "기타"}
        }
        return fallbacks.get(task_type, {"result": "분석 실패"})

    def health_check(self) -> Dict[str, Any]:
        """
        API 상태를 확인합니다.
        
        Returns
        -------
        Dict[str, Any]
            API 상태 정보
        """
        try:
            # API 키 확인
            if not self.api_key:
                return {"status": "error", "message": "API 키가 설정되지 않음"}
            
            # API 연결 테스트
            response = asyncio.run(self.client.models.list())
            
            return {
                "status": "healthy",
                "message": "API 연결 정상",
                "models_available": len(response.data) if response.data else 0
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"API 연결 실패: {str(e)}"
            }

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        API 사용 통계를 반환합니다.
        
        Returns
        -------
        Dict[str, Any]
            사용 통계
        """
        return {
            "api_key_configured": bool(self.api_key),
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay
        }


if __name__ == "__main__":
    # noinspection PyMissingOrEmptyDocstring
    async def main():
        handler = LLMOrchestrator(
            config_path="config/config.yaml",
            prompt_config_path="config/prompt.yaml",
            model_id="openai",
        )

        conversation = [
            {"speaker": "Speaker 1", "text": "Hello, I need help with my order."},
            {"speaker": "Speaker 0", "text": "Sure, I'd be happy to assist you."},
            {"speaker": "Speaker 1", "text": "I haven't received it yet."},
            {"speaker": "Speaker 0", "text": "Let me check the status for you."}
        ]

        speaker_roles = await handler.generate("Classification", conversation)
        print("Speaker Roles:", speaker_roles)
        print("Type:", type(speaker_roles))

        sentiment_analyzer = LLMOrchestrator(
            config_path="config/config.yaml",
            prompt_config_path="config/prompt.yaml"
        )

        sentiment = await sentiment_analyzer.generate("SentimentAnalysis", conversation)
        print("\nSentiment Analysis:", sentiment)


    asyncio.run(main())
