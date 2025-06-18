# Standard library imports
import os
import json
from datetime import datetime

# Related third-party imports
try:
    from omegaconf import OmegaConf
    OMEGACONF_AVAILABLE = True
except ImportError:
    print("Warning: omegaconf not available, using fallback configuration")
    OMEGACONF_AVAILABLE = False
    # 간단한 설정 클래스 생성
    class OmegaConf:
        @staticmethod
        def load(path):
            # 기본 설정 반환
            return {
                "runtime": {
                    "device": "cpu",
                    "compute_type": "float32",
                    "cuda_alloc_conf": ""
                }
            }

try:
    from nemo.collections.asr.models.msdd_models import NeuralDiarizer
    NEMO_AVAILABLE = True
except ImportError:
    print("Warning: NeMo not available, diarization will be skipped")
    NEMO_AVAILABLE = False
    # 더미 클래스 생성
    class NeuralDiarizer:
        def __init__(self, cfg):
            pass
        def diarize(self):
            print("NeMo not available, skipping diarization")

# Local imports
from src.audio.utils import Formatter
from src.audio.metrics import SilenceStats
from src.audio.error import DialogueDetecting
from src.audio.alignment import ForcedAligner
from src.audio.effect import DemucsVocalSeparator
from src.audio.preprocessing import SpeechEnhancement
from src.audio.io import SpeakerTimestampReader, TranscriptWriter
from src.audio.analysis import WordSpeakerMapper, SentenceSpeakerMapper, Audio
from src.audio.processing import AudioProcessor, Transcriber, PunctuationRestorer
from src.text.utils import Annotator
from src.text.llm import LLMOrchestrator, LLMResultHandler
from src.text.complaint_analyzer import ComplaintAnalyzer, ComplaintAnalysisResult
from src.text.korean_models import KoreanModelConfig
from src.utils.utils import Cleaner, Watcher
from src.db.manager import Database
from watchdog.events import FileSystemEventHandler
import asyncio
from watchdog.observers.polling import PollingObserver


async def main_enhanced(audio_file_path: str):
    """
    향상된 메인 프로세스 - 통신사 민원 분석 기능 포함
    
    Parameters
    ----------
    audio_file_path : str
        처리할 오디오 파일 경로
    """
    # 경로 설정
    config_nemo = "config/nemo/diar_infer_telephonic.yaml"
    manifest_path = ".temp/manifest.json"
    temp_dir = ".temp"
    rttm_file_path = os.path.join(temp_dir, "pred_rttms", "mono_file.rttm")
    transcript_output_path = ".temp/output.txt"
    srt_output_path = ".temp/output.srt"
    config_path = "config/config.yaml"
    prompt_path = "config/prompt.yaml"
    korean_prompt_path = "config/korean_prompts.yaml"
    db_path = ".db/Callytics.sqlite"
    
    # 데이터베이스 SQL 경로
    db_topic_fetch_path = "src/db/sql/TopicFetch.sql"
    db_topic_insert_path = "src/db/sql/TopicInsert.sql"
    db_audio_properties_insert_path = "src/db/sql/AudioPropertiesInsert.sql"
    db_utterance_insert_path = "src/db/sql/UtteranceInsert.sql"
    
    # 설정 로드
    if OMEGACONF_AVAILABLE:
        config = OmegaConf.load(config_path)
        device = config.runtime.device
        compute_type = config.runtime.compute_type
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = config.runtime.cuda_alloc_conf
    else:
        # 기본 설정 사용
        device = "cpu"
        compute_type = "float32"
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = ""
    
    # 한국어 모델 설정
    korean_model_config = KoreanModelConfig(
        model_type="openchat",  # 또는 "llama3", "gemma"
        base_model_name="../AI 모델/model/openchat-3.5-0106-private",  # 실제 모델 경로로 수정 필요
        peft_model_name="",  # PEFT 모델이 있다면 경로 지정
        device=device,
        torch_dtype="bfloat16" if compute_type == "float16" else "float32",
        max_new_tokens=1024,
        temperature=0.1
    )
    
    # 클래스 초기화
    dialogue_detector = DialogueDetecting(delete_original=True)
    enhancer = SpeechEnhancement(config_path=config_path, output_dir=temp_dir)
    separator = DemucsVocalSeparator()
    processor = AudioProcessor(audio_path=audio_file_path, temp_dir=temp_dir)
    transcriber = Transcriber(device=device, compute_type=compute_type)
    aligner = ForcedAligner(device=device)
    
    # 기존 LLM 오케스트레이터
    llm_handler = LLMOrchestrator(config_path=config_path, prompt_config_path=prompt_path, model_id="openai")
    llm_result_handler = LLMResultHandler()
    
    # 통신사 민원 분석기 초기화
    complaint_analyzer = ComplaintAnalyzer(
        config_path=config_path,
        korean_prompt_path=korean_prompt_path,
        korean_model_config=korean_model_config
    )
    
    cleaner = Cleaner()
    formatter = Formatter()
    db = Database(db_path)
    audio_feature_extractor = Audio(audio_file_path)
    
    try:
        # Step 1: 대화 감지
        has_dialogue = dialogue_detector.process(audio_file_path)
        if not has_dialogue:
            print("대화가 감지되지 않았습니다.")
            return
        
        # Step 2: 음성 향상
        audio_path = enhancer.enhance_audio(
            input_path=audio_file_path,
            output_path=os.path.join(temp_dir, "enhanced.wav"),
            noise_threshold=0.0001,
            verbose=True
        )
        
        # Step 3: 보컬 분리
        vocal_path = separator.separate_vocals(audio_file=audio_path, output_dir=temp_dir)
        
        # Step 4: 전사
        transcript, info = transcriber.transcribe(audio_path=vocal_path)
        detected_language = info["language"]
        
        # Step 5: 강제 정렬
        word_timestamps = aligner.align(
            audio_path=vocal_path,
            transcript=transcript,
            language=detected_language
        )
        
        # Step 6: 다이어리제이션
        if NEMO_AVAILABLE:
            processor.audio_path = vocal_path
            mono_audio_path = processor.convert_to_mono()
            processor.audio_path = mono_audio_path
            processor.create_manifest(manifest_path)
            cfg = OmegaConf.load(config_nemo)
            cfg.diarizer.manifest_filepath = manifest_path
            cfg.diarizer.out_dir = temp_dir
            msdd_model = NeuralDiarizer(cfg=cfg)
            msdd_model.diarize()
        else:
            print("NeMo not available, skipping diarization step")
            # 더미 화자 타임스탬프 생성
            speaker_ts = [{"speaker": "SPEAKER_00", "start": 0.0, "end": 60.0}]
        
        # Step 7: 전사 처리
        # Step 7.1: 화자 타임스탬프
        if NEMO_AVAILABLE:
            speaker_reader = SpeakerTimestampReader(rttm_path=rttm_file_path)
            speaker_ts = speaker_reader.read_speaker_timestamps()
        else:
            # NeMo가 없을 때는 더미 데이터 사용
            speaker_ts = [{"speaker": "SPEAKER_00", "start": 0.0, "end": 60.0}]
        
        # Step 7.2: 단어 매핑
        word_speaker_mapper = WordSpeakerMapper(word_timestamps, speaker_ts)
        wsm = word_speaker_mapper.get_words_speaker_mapping()
        
        # Step 7.3: 문장 부호 복원
        punct_restorer = PunctuationRestorer(language=detected_language)
        wsm = punct_restorer.restore_punctuation(wsm)
        word_speaker_mapper.word_speaker_mapping = wsm
        word_speaker_mapper.realign_with_punctuation()
        wsm = word_speaker_mapper.word_speaker_mapping
        
        # Step 7.4: 문장 매핑
        sentence_mapper = SentenceSpeakerMapper()
        ssm = sentence_mapper.get_sentences_speaker_mapping(wsm)
        
        # Step 8: 전사 파일 작성
        writer = TranscriptWriter()
        writer.write_transcript(ssm, transcript_output_path)
        writer.write_srt(ssm, srt_output_path)
        
        # Step 9: 화자 역할 분류
        speaker_roles = await llm_handler.generate("Classification", ssm)
        ssm = llm_result_handler.validate_and_fallback(speaker_roles, ssm)
        llm_result_handler.log_result(ssm, speaker_roles)
        
        # Step 10: 감정 분석
        ssm_with_indices = formatter.add_indices_to_ssm(ssm)
        annotator = Annotator(ssm_with_indices)
        sentiment_results = await llm_handler.generate("SentimentAnalysis", user_input=ssm)
        annotator.add_sentiment(sentiment_results)
        
        # Step 11: 욕설 감지
        profane_results = await llm_handler.generate("ProfanityWordDetection", user_input=ssm)
        annotator.add_profanity(profane_results)
        
        # Step 12: 기존 요약
        summary_result = await llm_handler.generate("Summary", user_input=ssm)
        annotator.add_summary(summary_result)
        
        # Step 13: 감정 감지
        conflict_result = await llm_handler.generate("ConflictDetection", user_input=ssm)
        annotator.add_conflict(conflict_result)
        
        # Step 14: 주제 감지
        topics = db.fetch(db_topic_fetch_path)
        topic_result = await llm_handler.generate("TopicDetection", user_input=ssm, system_input=topics)
        annotator.add_topic(topic_result)
        
        # Step 15: 통신사 민원 분석 (새로운 기능)
        print("통신사 민원 분석을 시작합니다...")
        complaint_analysis_result = await complaint_analyzer.analyze_complaint(ssm)
        
        # Step 16: 오디오 특성 추출
        props = audio_feature_extractor.properties()
        (
            name, file_extension, absolute_file_path, sample_rate, min_frequency,
            max_frequency, audio_bit_depth, num_channels, audio_duration,
            rms_loudness, final_features
        ) = props
        
        rms_loudness_db = final_features["RMSLoudness"]
        zero_crossing_rate_db = final_features["ZeroCrossingRate"]
        spectral_centroid_db = final_features["SpectralCentroid"]
        eq_20_250_db = final_features["EQ_20_250_Hz"]
        eq_250_2000_db = final_features["EQ_250_2000_Hz"]
        eq_2000_6000_db = final_features["EQ_2000_6000_Hz"]
        eq_6000_20000_db = final_features["EQ_6000_20000_Hz"]
        mfcc_values = [final_features[f"MFCC_{i}"] for i in range(1, 14)]
        
        # Step 17: 최종 결과 생성
        final_output = annotator.finalize()
        
        # Step 18: 데이터베이스에 통신사 민원 분석 결과 저장
        await save_complaint_analysis_to_db(
            db=db,
            file_id=1,  # 실제 파일 ID로 수정 필요
            complaint_result=complaint_analysis_result,
            final_output=final_output,
            audio_props=props
        )
        
        # Step 19: 결과 출력
        print("\n=== 통신사 민원 분석 결과 ===")
        print(f"업무 분야: {complaint_analysis_result.category}")
        print(f"상담 주제: {complaint_analysis_result.consultation_topic}")
        print(f"상담 내용: {complaint_analysis_result.consultation_type}")
        print(f"심각도: {complaint_analysis_result.severity}")
        print(f"긴급도: {complaint_analysis_result.urgency}")
        print(f"만족도: {complaint_analysis_result.satisfaction}/5")
        print(f"해결상태: {complaint_analysis_result.resolution_status}")
        print(f"우선순위: {complaint_analysis_result.priority_level}/5")
        print(f"담당부서: {complaint_analysis_result.department}")
        print(f"신뢰도: {complaint_analysis_result.confidence:.2f}")
        print(f"키워드: {', '.join(complaint_analysis_result.keywords)}")
        print(f"감정점수: {complaint_analysis_result.sentiment_score:.2f}")
        print(f"요약: {complaint_analysis_result.summary}")
        print(f"주요 포인트: {complaint_analysis_result.key_points}")
        print(f"액션 아이템: {complaint_analysis_result.action_items}")
        
        print("\n=== 기존 분석 결과 ===")
        print(f"화자 분류: {speaker_roles}")
        print(f"감정 분석: {sentiment_results}")
        print(f"욕설 감지: {profane_results}")
        print(f"요약: {summary_result}")
        print(f"감정 감지: {conflict_result}")
        print(f"주제: {topic_result}")
        
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")
        raise
    finally:
        # 리소스 정리
        complaint_analyzer.unload()
        llm_handler.manager.unload_all()


async def save_complaint_analysis_to_db(db, file_id, complaint_result, final_output, audio_props):
    """통신사 민원 분석 결과를 데이터베이스에 저장"""
    try:
        # 1. 통신사 민원 분석 결과 저장
        complaint_analysis_sql = """
        INSERT INTO ComplaintAnalysis 
        (FileID, CategoryID, TopicID, TypeID, Severity, Urgency, Satisfaction, ResolutionStatus, 
         Keywords, SentimentScore, AnalysisDate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # 카테고리 ID, 주제 ID, 유형 ID 조회 (실제 구현에서는 매핑 로직 필요)
        category_id = 1  # 기본값, 실제로는 업무분야명으로 조회
        topic_id = 1     # 기본값, 실제로는 상담주제명으로 조회
        type_id = 1      # 기본값, 실제로는 상담내용명으로 조회
        
        db.execute(complaint_analysis_sql, (
            file_id,
            category_id,
            topic_id,
            type_id,
            complaint_result.severity,
            complaint_result.urgency,
            complaint_result.satisfaction,
            complaint_result.resolution_status,
            json.dumps(complaint_result.keywords, ensure_ascii=False),
            complaint_result.sentiment_score,
            datetime.now()
        ))
        
        # 2. 통신사 민원 요약 저장
        complaint_summary_sql = """
        INSERT INTO ComplaintSummary 
        (FileID, Summary, KeyPoints, ActionItems, CreatedDate)
        VALUES (?, ?, ?, ?, ?)
        """
        
        db.execute(complaint_summary_sql, (
            file_id,
            complaint_result.summary,
            json.dumps(complaint_result.key_points, ensure_ascii=False),
            json.dumps(complaint_result.action_items, ensure_ascii=False),
            datetime.now()
        ))
        
        # 3. 우선순위 저장
        complaint_priority_sql = """
        INSERT INTO ComplaintPriority 
        (FileID, PriorityLevel, PriorityReason, EscalationLevel, EscalationDate)
        VALUES (?, ?, ?, ?, ?)
        """
        
        db.execute(complaint_priority_sql, (
            file_id,
            complaint_result.priority_level,
            f"자동 분석 결과 (신뢰도: {complaint_result.confidence:.2f})",
            1,  # 기본 에스컬레이션 레벨
            datetime.now()
        ))
        
        # 4. 부서 배정 저장
        department_mapping_sql = """
        INSERT INTO ComplaintDepartmentMapping 
        (FileID, DepartmentID, IsPrimary, AssignedDate)
        VALUES (?, ?, ?, ?)
        """
        
        # 부서 ID 조회 (실제 구현에서는 부서명으로 조회)
        department_id = 1  # 기본값, 실제로는 부서명으로 조회
        
        db.execute(department_mapping_sql, (
            file_id,
            department_id,
            True,  # 주관부서
            datetime.now()
        ))
        
        print("통신사 민원 분석 결과가 데이터베이스에 저장되었습니다.")
        
    except Exception as e:
        print(f"데이터베이스 저장 중 오류: {e}")


async def process_enhanced(path: str):
    """향상된 파일 처리 함수"""
    try:
        await main_enhanced(path)
        print(f"파일 처리 완료: {path}")
    except Exception as e:
        print(f"파일 처리 실패: {path}, 오류: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        asyncio.run(process_enhanced(audio_file))
    else:
        print("사용법: python main_enhanced.py <audio_file_path>")
        print("예시: python main_enhanced.py ./audio/sample.wav") 