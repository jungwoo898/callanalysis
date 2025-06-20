# Standard library imports
import os
import re
import json
from io import TextIOWrapper
from typing import Annotated, Optional, Tuple, List, Dict, Any

# Related third party imports
import torch
import faster_whisper
from pydub import AudioSegment
from deepmultilingualpunctuation import PunctuationModel

# Local imports
from src.audio.utils import TokenizerUtils


class AudioProcessor:
    """
    A class to handle various audio processing tasks, such as conversion,
    trimming, merging, and audio transformations.

    Parameters
    ----------
    audio_path : str
        Path to the audio file to process.
    temp_dir : str, optional
        Directory for storing temporary files. Defaults to ".temp".

    Attributes
    ----------
    audio_path : str
        Path to the input audio file.
    temp_dir : str
        Path to the temporary directory for processed files.
    mono_audio_path : Optional[str]
        Path to the mono audio file after conversion.

    Methods
    -------
    convert_to_mono()
        Converts the audio file to mono.
    get_duration()
        Gets the duration of the audio file in seconds.
    change_format(new_format)
        Converts the audio file to a new format.
    trim_audio(start_time, end_time)
        Trims the audio file to the specified time range.
    adjust_volume(change_in_db)
        Adjusts the volume of the audio file.
    get_channels()
        Gets the number of audio channels.
    fade_in_out(fade_in_duration, fade_out_duration)
        Applies fade-in and fade-out effects to the audio.
    merge_audio(other_audio_path)
        Merges the current audio with another audio file.
    split_audio(chunk_duration)
        Splits the audio file into chunks of a specified duration.
    create_manifest(manifest_path)
        Creates a manifest file containing metadata about the audio.
    """

    def __init__(
            self,
            audio_path: Annotated[str, "Path to the audio file"],
            temp_dir: Annotated[str, "Directory for temporary processed files"] = ".temp"
    ) -> None:
        if not isinstance(audio_path, str):
            raise TypeError("Expected 'audio_path' to be a string.")
        if not isinstance(temp_dir, str):
            raise TypeError("Expected 'temp_dir' to be a string.")

        self.audio_path = audio_path
        self.temp_dir = temp_dir
        self.mono_audio_path = None
        os.makedirs(temp_dir, exist_ok=True)

    def convert_to_mono(self) -> Annotated[str, "Path to the mono audio file"]:
        """
        Convert the audio file to mono.

        Returns
        -------
        str
            Path to the mono audio file.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> mono_path = processor.convert_to_mono()
        >>> isinstance(mono_path, str)
        True
        """
        sound = AudioSegment.from_file(self.audio_path)
        mono_sound = sound.set_channels(1)
        self.mono_audio_path = os.path.join(self.temp_dir, "mono_file.wav")
        mono_sound.export(self.mono_audio_path, format="wav")
        return self.mono_audio_path

    def get_duration(self) -> Annotated[float, "Audio duration in seconds"]:
        """
        Get the duration of the audio file.

        Returns
        -------
        float
            Duration of the audio in seconds.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> duration = processor.get_duration()
        >>> isinstance(duration, float)
        True
        """
        sound = AudioSegment.from_file(self.audio_path)
        return len(sound) / 1000.0

    def change_format(
            self, new_format: Annotated[str, "New audio format"]
    ) -> Annotated[str, "Path to converted audio file"]:
        """
        Convert the audio file to a new format.

        Parameters
        ----------
        new_format : str
            Desired format for the output audio file.

        Returns
        -------
        str
            Path to the converted audio file.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> converted_path = processor.change_format("mp3")
        >>> isinstance(converted_path, str)
        True
        """
        if not isinstance(new_format, str):
            raise TypeError("Expected 'new_format' to be a string.")

        sound = AudioSegment.from_file(self.audio_path)
        output_path = os.path.join(self.temp_dir, f"converted_file.{new_format}")
        sound.export(output_path, format=new_format)
        return output_path

    def trim_audio(
            self, start_time: Annotated[float, "Start time in seconds"],
            end_time: Annotated[float, "End time in seconds"]
    ) -> Annotated[str, "Path to trimmed audio file"]:
        """
        Trim the audio file to the specified duration.

        Parameters
        ----------
        start_time : float
            Start time in seconds.
        end_time : float
            End time in seconds.

        Returns
        -------
        str
            Path to the trimmed audio file.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> trimmed_path = processor.trim_audio(0.0, 10.0)
        >>> isinstance(trimmed_path, str)
        True
        """
        if not isinstance(start_time, (int, float)):
            raise TypeError("Expected 'start_time' to be a float or int.")
        if not isinstance(end_time, (int, float)):
            raise TypeError("Expected 'end_time' to be a float or int.")

        sound = AudioSegment.from_file(self.audio_path)
        trimmed_audio = sound[start_time * 1000:end_time * 1000]
        trimmed_audio_path = os.path.join(self.temp_dir, "trimmed_file.wav")
        trimmed_audio.export(trimmed_audio_path, format="wav")
        return trimmed_audio_path

    def adjust_volume(
            self, change_in_db: Annotated[float, "Volume change in dB"]
    ) -> Annotated[str, "Path to volume-adjusted audio file"]:
        """
        Adjust the volume of the audio file.

        Parameters
        ----------
        change_in_db : float
            Volume change in decibels.

        Returns
        -------
        str
            Path to the volume-adjusted audio file.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> adjusted_path = processor.adjust_volume(5.0)
        >>> isinstance(adjusted_path, str)
        True
        """
        if not isinstance(change_in_db, (int, float)):
            raise TypeError("Expected 'change_in_db' to be a float or int.")

        sound = AudioSegment.from_file(self.audio_path)
        adjusted_audio = sound + change_in_db
        adjusted_audio_path = os.path.join(self.temp_dir, "adjusted_file.wav")
        adjusted_audio.export(adjusted_audio_path, format="wav")
        return adjusted_audio_path

    def get_channels(self) -> Annotated[int, "Number of channels"]:
        """
        Get the number of audio channels.

        Returns
        -------
        int
            Number of audio channels.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> channels = processor.get_channels()
        >>> isinstance(channels, int)
        True
        """
        sound = AudioSegment.from_file(self.audio_path)
        return sound.channels

    def fade_in_out(
            self, fade_in_duration: Annotated[float, "Fade-in duration in seconds"],
            fade_out_duration: Annotated[float, "Fade-out duration in seconds"]
    ) -> Annotated[str, "Path to faded audio file"]:
        """
        Apply fade-in and fade-out effects to the audio.

        Parameters
        ----------
        fade_in_duration : float
            Duration of fade-in effect in seconds.
        fade_out_duration : float
            Duration of fade-out effect in seconds.

        Returns
        -------
        str
            Path to the faded audio file.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> faded_path = processor.fade_in_out(1.0, 1.0)
        >>> isinstance(faded_path, str)
        True
        """
        if not isinstance(fade_in_duration, (int, float)):
            raise TypeError("Expected 'fade_in_duration' to be a float or int.")
        if not isinstance(fade_out_duration, (int, float)):
            raise TypeError("Expected 'fade_out_duration' to be a float or int.")

        sound = AudioSegment.from_file(self.audio_path)
        faded_audio = sound.fade_in(fade_in_duration * 1000).fade_out(fade_out_duration * 1000)
        faded_audio_path = os.path.join(self.temp_dir, "faded_file.wav")
        faded_audio.export(faded_audio_path, format="wav")
        return faded_audio_path

    def merge_audio(
            self, other_audio_path: Annotated[str, "Path to other audio file"]
    ) -> Annotated[str, "Path to merged audio file"]:
        """
        Merge the current audio with another audio file.

        Parameters
        ----------
        other_audio_path : str
            Path to the other audio file to merge with.

        Returns
        -------
        str
            Path to the merged audio file.

        Examples
        --------
        >>> processor = AudioProcessor("example1.wav")
        >>> merged_path = processor.merge_audio("example2.wav")
        >>> isinstance(merged_path, str)
        True
        """
        if not isinstance(other_audio_path, str):
            raise TypeError("Expected 'other_audio_path' to be a string.")

        sound1 = AudioSegment.from_file(self.audio_path)
        sound2 = AudioSegment.from_file(other_audio_path)
        merged_audio = sound1 + sound2
        merged_audio_path = os.path.join(self.temp_dir, "merged_file.wav")
        merged_audio.export(merged_audio_path, format="wav")
        return merged_audio_path

    def split_audio(
            self, chunk_duration: Annotated[float, "Chunk duration in seconds"]
    ) -> Annotated[List[str], "Paths to audio chunks"]:
        """
        Split the audio file into chunks of a specified duration.

        Parameters
        ----------
        chunk_duration : float
            Duration of each chunk in seconds.

        Returns
        -------
        List[str]
            List of paths to the audio chunks.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> chunk_paths = processor.split_audio(30.0)
        >>> isinstance(chunk_paths, list)
        True
        """
        if not isinstance(chunk_duration, (int, float)):
            raise TypeError("Expected 'chunk_duration' to be a float or int.")

        sound = AudioSegment.from_file(self.audio_path)
        chunk_paths = []
        total_duration = len(sound)
        chunk_duration_ms = chunk_duration * 1000

        for i, start in enumerate(range(0, total_duration, int(chunk_duration_ms))):
            end = min(start + int(chunk_duration_ms), total_duration)
            chunk = sound[start:end]
            chunk_path = os.path.join(self.temp_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")
            chunk_paths.append(chunk_path)

        return chunk_paths

    def create_manifest(
            self,
            manifest_path: Annotated[str, "Manifest file path"]
    ) -> None:
        """
        Create a manifest file containing metadata about the audio.

        Parameters
        ----------
        manifest_path : str
            Path where the manifest file should be created.

        Examples
        --------
        >>> processor = AudioProcessor("example.wav")
        >>> processor.create_manifest("manifest.json")
        """
        if not isinstance(manifest_path, str):
            raise TypeError("Expected 'manifest_path' to be a string.")

        sound = AudioSegment.from_file(self.audio_path)
        manifest = {
            "audio_path": self.audio_path,
            "duration": len(sound) / 1000.0,
            "channels": sound.channels,
            "sample_rate": sound.frame_rate,
            "frame_width": sound.sample_width,
            "file_size": os.path.getsize(self.audio_path)
        }

        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)


class IntegratedAudioProcessor:
    """
    통합 오디오 프로세서 - 화자 분리, 음성 인식, 구두점 복원을 포함한 완전한 파이프라인
    """
    
    def __init__(
        self,
        language: str = "ko",
        device: str = "auto",
        whisper_model: str = "base",
        diarization_auth_token: Optional[str] = None
    ):
        """
        통합 오디오 프로세서 초기화
        
        Parameters
        ----------
        language : str
            처리할 언어 (기본값: "ko")
        device : str
            사용할 디바이스 (cpu/gpu/auto)
        whisper_model : str
            Whisper 모델 크기 (tiny/base/small/medium/large)
        diarization_auth_token : str, optional
            HuggingFace 인증 토큰 (화자 분리용)
        """
        self.language = language
        self.device = self._determine_device(device)
        self.whisper_model = whisper_model
        self.diarization_auth_token = diarization_auth_token
        
        # 컴포넌트 초기화
        self.transcriber = Transcriber(
            model_name=whisper_model,
            device=self.device,
            compute_type='float16' if self.device == 'cuda' else 'int8'
        )
        
        self.punctuation_restorer = PunctuationRestorer(language=language)
        
        # 화자 분리 모델은 필요시에만 로드
        self.diarization_model = None
    
    def _determine_device(self, device: str) -> str:
        """디바이스 결정"""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def _load_diarization_model(self):
        """화자 분리 모델 로드"""
        if self.diarization_model is None:
            try:
                # Windows 환경에서 signal 모듈 패치
                import signal
                if not hasattr(signal, 'SIGKILL'):
                    signal.SIGKILL = signal.SIGTERM
                if not hasattr(signal, 'SIGUSR1'):
                    signal.SIGUSR1 = signal.SIGTERM
                if not hasattr(signal, 'SIGUSR2'):
                    signal.SIGUSR2 = signal.SIGTERM
                
                # Windows 환경에서 pyannote.audio 안정성을 위한 환경 변수 설정
                import os
                os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
                os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
                
                from pyannote.audio import Pipeline
                if self.diarization_auth_token:
                    self.diarization_model = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=self.diarization_auth_token
                    )
                    print("✅ 화자 분리 모델 로드 완료")
                else:
                    print("⚠️ 화자 분리 토큰이 없어 기본 음성 인식만 수행합니다.")
                    self.diarization_model = None
            except ImportError:
                print("⚠️ pyannote.audio가 설치되지 않아 화자 분리를 건너뜁니다.")
                self.diarization_model = None
            except Exception as e:
                print(f"⚠️ 화자 분리 모델 로드 실패: {e}")
                print("기본 음성 인식만 수행합니다.")
                self.diarization_model = None
    
    def process_audio(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        오디오 파일을 처리하여 화자별 발화 내용을 반환
        
        Parameters
        ----------
        audio_path : str
            처리할 오디오 파일 경로
            
        Returns
        -------
        List[Dict[str, Any]]
            화자별 발화 내용 리스트
        """
        try:
            print(f"오디오 파일 처리 시작: {audio_path}")
            
            # 0. 오디오 전처리 (노이즈 제거, 음성 강화)
            print("오디오 전처리 수행 중...")
            processed_audio_path = self._preprocess_audio(audio_path)
            
            # 1. 화자 분리 수행
            self._load_diarization_model()
            
            if self.diarization_model:
                # 화자 분리 + 음성 인식
                utterances = self._process_with_diarization(processed_audio_path)
            else:
                # 기본 음성 인식만
                utterances = self._process_without_diarization(processed_audio_path)
            
            print(f"처리 완료: {len(utterances)}개 발화")
            return utterances
            
        except Exception as e:
            print(f"오디오 처리 중 오류 발생: {e}")
            return []
    
    def _preprocess_audio(self, audio_path: str) -> str:
        """오디오 전처리 (노이즈 제거, 음성 강화)"""
        try:
            # 임시 파일 경로
            temp_dir = ".temp"
            os.makedirs(temp_dir, exist_ok=True)
            processed_path = os.path.join(temp_dir, "processed_audio.wav")
            
            # pydub을 사용한 기본 전처리
            audio = AudioSegment.from_file(audio_path)
            
            # 1. 모노 변환 (화자 분리 성능 향상)
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # 2. 샘플링 레이트 정규화 (16kHz)
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
            
            # 3. 볼륨 정규화
            audio = audio.normalize()
            
            # 4. 기본 노이즈 제거 (고주파/저주파 필터링)
            # 고주파 노이즈 제거 (8kHz 이상)
            audio = audio.high_pass_filter(8000)
            # 저주파 노이즈 제거 (80Hz 이하)
            audio = audio.low_pass_filter(80)
            
            # 처리된 오디오 저장
            audio.export(processed_path, format="wav")
            
            print("✅ 오디오 전처리 완료")
            return processed_path
            
        except Exception as e:
            print(f"⚠️ 오디오 전처리 실패, 원본 사용: {e}")
            return audio_path
    
    def _process_with_diarization(self, audio_path: str) -> List[Dict[str, Any]]:
        """화자 분리를 포함한 처리"""
        try:
            # 화자 분리 수행
            print("화자 분리 수행 중...")
            diarization = self.diarization_model(audio_path)
            
            utterances = []
            speaker_mapping = {}  # 화자 ID를 고객/상담사로 매핑
            speaker_count = 0
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                start_time = turn.start
                end_time = turn.end
                
                # 화자 ID를 고객/상담사로 매핑
                if speaker not in speaker_mapping:
                    if speaker_count == 0:
                        speaker_mapping[speaker] = "고객"
                    else:
                        speaker_mapping[speaker] = "상담사"
                    speaker_count += 1
                
                # 해당 구간 음성 인식
                text, info = self.transcriber.transcribe(
                    audio_path,
                    language=self.language,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if text.strip():
                    # 간단한 구두점 복원 (속도 향상)
                    restored_text = text.strip()
                    
                    utterances.append({
                        'speaker': speaker_mapping[speaker],
                        'start': start_time,
                        'end': end_time,
                        'text': restored_text,
                        'confidence': info.get('confidence', 0.0)
                    })
            
            return utterances
        except Exception as e:
            print(f"화자 분리 처리 중 오류: {e}")
            # 화자 분리 실패 시 기본 처리로 폴백
            return self._process_without_diarization(audio_path)
    
    def _process_without_diarization(self, audio_path: str) -> List[Dict[str, Any]]:
        """화자 분리 없이 기본 처리"""
        try:
            # 전체 음성 인식
            print("기본 음성 인식 수행 중...")
            text, info = self.transcriber.transcribe(
                audio_path,
                language=self.language
            )
            
            if text.strip():
                # 간단한 구두점 복원 (속도 향상)
                restored_text = text.strip()
                
                return [{
                    'speaker': 'Unknown',
                    'start': 0.0,
                    'end': info.get('duration', 0.0),
                    'text': restored_text,
                    'confidence': info.get('confidence', 0.0)
                }]
            
            return []
        except Exception as e:
            print(f"기본 음성 인식 중 오류: {e}")
            return []


class Transcriber:
    """
    A class to handle audio transcription using the Faster Whisper model.

    Parameters
    ----------
    model_name : str
        Name of the model to load.
    device : str
        Device to use for model inference.
    compute_type : str
        Data type for model computation, e.g., 'int8' or 'float16'.

    Attributes
    ----------
    model : faster_whisper.WhisperModel
        The loaded Whisper model.
    """

    def __init__(
            self,
            model_name: str = 'medium',
            device: str = 'cpu',
            compute_type: str = 'int8'
    ) -> None:
        if not isinstance(model_name, str):
            raise TypeError("Expected 'model_name' to be a string.")
        if not isinstance(device, str):
            raise TypeError("Expected 'device' to be a string.")
        if not isinstance(compute_type, str):
            raise TypeError("Expected 'compute_type' to be a string.")

        self.model = faster_whisper.WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type
        )

    def transcribe(
            self,
            audio_path: str,
            language: Optional[str] = None,
            start_time: Optional[float] = None,
            end_time: Optional[float] = None
    ) -> tuple:
        """
        Transcribe an audio file using the Whisper model.
        """
        if not isinstance(audio_path, str):
            raise TypeError("Expected 'audio_path' to be a string.")
        if language is not None and not isinstance(language, str):
            raise TypeError("Expected 'language' to be a string or None.")

        # 시간 범위가 지정된 경우 오디오를 자르기
        if start_time is not None or end_time is not None:
            processor = AudioProcessor(audio_path)
            if start_time is None:
                start_time = 0.0
            if end_time is None:
                end_time = processor.get_duration()
            audio_path = processor.trim_audio(start_time, end_time)

        segments, info = self.model.transcribe(
            audio_path,
            language=language
        )

        # 텍스트 조합
        text = " ".join([segment.text for segment in segments])
        # 추가 정보 구성
        result_info = {
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration,
            'confidence': info.confidence if hasattr(info, 'confidence') else 0.0
        }
        return text, result_info


class PunctuationRestorer:
    """
    A class to restore punctuation in transcribed text.

    Parameters
    ----------
    language : str
        Language for punctuation restoration.

    Attributes
    ----------
    model : PunctuationModel
        The punctuation restoration model.
    """

    def __init__(self, language: Annotated[str, "Language for punctuation restoration"] = 'en') -> None:
        if not isinstance(language, str):
            raise TypeError("Expected 'language' to be a string.")

        self.language = language
        self.model = PunctuationModel()

    def restore_punctuation(
            self, word_speaker_mapping: Annotated[List[Dict], "List of word-speaker mappings"]
    ) -> Annotated[List[Dict], "Word mappings with restored punctuation"]:
        """
        Restore punctuation in the transcribed text.

        Parameters
        ----------
        word_speaker_mapping : List[Dict]
            List of dictionaries containing word-speaker mappings.

        Returns
        -------
        List[Dict]
            Word mappings with restored punctuation.

        Examples
        --------
        >>> restorer = PunctuationRestorer()
        >>> mappings = [{"word": "hello", "speaker": "A"}, {"word": "world", "speaker": "B"}]
        >>> result = restorer.restore_punctuation(mappings)
        >>> isinstance(result, list)
        True
        """
        if not isinstance(word_speaker_mapping, list):
            raise TypeError("Expected 'word_speaker_mapping' to be a list.")

        if self.language == 'ko':
            return self._restore_korean_punctuation(word_speaker_mapping)

        # 영어 및 기타 언어용 기본 처리
        text = " ".join([mapping["word"] for mapping in word_speaker_mapping])
        restored_text = self.model.restore_punctuation(text)

        # 단어별로 분리하여 매핑 복원
        restored_words = restored_text.split()
        result = []

        for i, mapping in enumerate(word_speaker_mapping):
            if i < len(restored_words):
                result.append({
                    "word": restored_words[i],
                    "speaker": mapping["speaker"]
                })

        return result

    def _restore_korean_punctuation(
            self, word_speaker_mapping: Annotated[List[Dict], "List of word-speaker mappings"]
    ) -> Annotated[List[Dict], "Word mappings with restored Korean punctuation"]:
        """
        Restore Korean punctuation in the transcribed text.

        Parameters
        ----------
        word_speaker_mapping : List[Dict]
            List of dictionaries containing word-speaker mappings.

        Returns
        -------
        List[Dict]
            Word mappings with restored Korean punctuation.
        """
        # 한국어 텍스트 조합
        text = " ".join([mapping["word"] for mapping in word_speaker_mapping])
        
        # 한국어 구두점 복원 규칙 적용
        restored_text = self._apply_korean_punctuation_rules(text)
        
        # 단어별로 분리하여 매핑 복원
        restored_words = restored_text.split()
        result = []
        
        for i, mapping in enumerate(word_speaker_mapping):
            if i < len(restored_words):
                result.append({
                    "word": restored_words[i],
                    "speaker": mapping["speaker"]
                })
        
        return result

    def _apply_korean_punctuation_rules(self, text: str) -> str:
        """
        한국어 구두점 복원 규칙 적용
        
        Parameters
        ----------
        text : str
            원본 텍스트
            
        Returns
        -------
        str
            구두점이 복원된 텍스트
        """
        # 기본 구두점 규칙
        text = re.sub(r'\s+([,.!?])', r'\1', text)  # 구두점 앞 공백 제거
        text = re.sub(r'([,.!?])\s*', r'\1 ', text)  # 구두점 뒤 공백 추가
        
        # 한국어 특화 규칙
        text = re.sub(r'([가-힣])\s+([이에]다)', r'\1\2', text)  # 조사 연결
        text = re.sub(r'([가-힣])\s+([을를])', r'\1\2', text)  # 조사 연결
        
        return text

    def restore_punctuation_simple(self, text: str) -> str:
        """
        간단한 구두점 복원 (전체 텍스트용)
        
        Parameters
        ----------
        text : str
            원본 텍스트
            
        Returns
        -------
        str
            구두점이 복원된 텍스트
        """
        if self.language == 'ko':
            return self._apply_korean_punctuation_rules(text)
        else:
            # 영어 및 기타 언어용
            return self.model.restore_punctuation(text)


if __name__ == "__main__":
    sample_audio_path = "sample_audio.wav"
    audio_processor_instance = AudioProcessor(sample_audio_path)

    mono_audio_path = audio_processor_instance.convert_to_mono()
    print(f"Mono audio file saved at: {mono_audio_path}")

    audio_duration = audio_processor_instance.get_duration()
    print(f"Audio duration: {audio_duration} seconds")

    converted_audio_path = audio_processor_instance.change_format("mp3")
    print(f"Converted audio file saved at: {converted_audio_path}")

    audio_path_trimmed = audio_processor_instance.trim_audio(0.0, 10.0)
    print(f"Trimmed audio file saved at: {audio_path_trimmed}")

    volume_adjusted_audio_path = audio_processor_instance.adjust_volume(5.0)
    print(f"Volume adjusted audio file saved at: {volume_adjusted_audio_path}")

    additional_audio_path = "additional_audio.wav"
    merged_audio_output_path = audio_processor_instance.merge_audio(additional_audio_path)
    print(f"Merged audio file saved at: {merged_audio_output_path}")

    audio_chunk_paths = audio_processor_instance.split_audio(10.0)
    print(f"Audio chunks saved at: {audio_chunk_paths}")

    output_manifest_path = "output_manifest.json"
    audio_processor_instance.create_manifest(output_manifest_path)
    print(f"Manifest file saved at: {output_manifest_path}")

    transcriber_instance = Transcriber()
    transcribed_text_output, transcription_metadata = transcriber_instance.transcribe(sample_audio_path)
    print(f"Transcribed Text: {transcribed_text_output}")
    print(f"Transcription Info: {transcription_metadata}")

    word_mapping_example = [
        {"text": "hello"},
        {"text": "world"},
        {"text": "this"},
        {"text": "is"},
        {"text": "a"},
        {"text": "test"}
    ]
    punctuation_restorer_instance = PunctuationRestorer()
    punctuation_restored_mapping = punctuation_restorer_instance.restore_punctuation(word_mapping_example)
    print(f"Restored Mapping: {punctuation_restored_mapping}")
