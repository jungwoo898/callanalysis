# Standard library imports
import os

# Related third-party imports
from omegaconf import OmegaConf
from nemo.collections.asr.models.msdd_models import NeuralDiarizer

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
from src.utils.utils import Cleaner, Watcher
from src.db.manager import Database
from watchdog.events import FileSystemEventHandler
import asyncio
from watchdog.observers import Observer
from src.text.korean_models import KoreanModels


async def main(audio_file_path: str):
    """
    Process an audio file to perform diarization, transcription, punctuation restoration,
    and speaker role classification.

    Parameters
    ----------
    audio_file_path : str
        The path to the input audio file to be processed.

    Returns
    -------
    None
    """
    # Paths
    config_nemo = "config/nemo/diar_infer_telephonic.yaml"
    manifest_path = "/app/.temp/manifest.json"
    temp_dir = "/app/.temp"
    rttm_file_path = os.path.join(temp_dir, "pred_rttms", "mono_file.rttm")
    transcript_output_path = "/app/.temp/output.txt"
    srt_output_path = "/app/.temp/output.srt"
    config_path = "config/config.yaml"
    prompt_path = "config/prompt.yaml"
    db_path = "/app/.db/Callytics.sqlite"
    db_topic_fetch_path = "src/db/sql/TopicFetch.sql"
    db_topic_insert_path = "src/db/sql/TopicInsert.sql"
    db_audio_properties_insert_path = "src/db/sql/AudioPropertiesInsert.sql"
    db_utterance_insert_path = "src/db/sql/UtteranceInsert.sql"

    # Configuration
    config = OmegaConf.load(config_path)
    device = config.runtime.device
    compute_type = config.runtime.compute_type
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = config.runtime.cuda_alloc_conf

    # Initialize Classes
    dialogue_detector = DialogueDetecting(delete_original=True)
    enhancer = SpeechEnhancement(config_path=config_path, output_dir=temp_dir)
    separator = DemucsVocalSeparator()
    processor = AudioProcessor(audio_path=audio_file_path, temp_dir=temp_dir)
    transcriber = Transcriber(device=device, compute_type=compute_type)
    aligner = ForcedAligner(device=device)
    llm_handler = LLMOrchestrator(config_path=config_path, prompt_config_path=prompt_path, model_id="openai")
    llm_result_handler = LLMResultHandler()
    cleaner = Cleaner()
    formatter = Formatter()
    db = Database(db_path)
    audio_feature_extractor = Audio(audio_file_path)

    # Step 1: Detect Dialogue
    has_dialogue = dialogue_detector.process(audio_file_path)
    if not has_dialogue:
        return

    # Step 2: Speech Enhancement
    audio_path = enhancer.enhance_audio(
        input_path=audio_file_path,
        output_path=os.path.join(temp_dir, "enhanced.wav"),
        noise_threshold=0.0001,
        verbose=True
    )

    # Step 3: Vocal Separation
    vocal_path = separator.separate_vocals(audio_file=audio_path, output_dir=temp_dir)

    # Step 4: Transcription
    transcript, info = transcriber.transcribe(audio_path=vocal_path)
    detected_language = info["language"]

    # Step 5: Forced Alignment
    word_timestamps = aligner.align(
        audio_path=vocal_path,
        transcript=transcript,
        language=detected_language
    )

    # Step 6: Diarization
    processor.audio_path = vocal_path
    mono_audio_path = processor.convert_to_mono()
    processor.audio_path = mono_audio_path
    processor.create_manifest(manifest_path)
    cfg = OmegaConf.load(config_nemo)
    cfg.diarizer.manifest_filepath = manifest_path
    cfg.diarizer.out_dir = temp_dir
    msdd_model = NeuralDiarizer(cfg=cfg)
    msdd_model.diarize()

    # Step 7: Processing Transcript
    # Step 7.1: Speaker Timestamps
    speaker_reader = SpeakerTimestampReader(rttm_path=rttm_file_path)
    speaker_ts = speaker_reader.read_speaker_timestamps()

    # Step 7.2: Mapping Words
    word_speaker_mapper = WordSpeakerMapper(word_timestamps, speaker_ts)
    wsm = word_speaker_mapper.get_words_speaker_mapping()

    # Step 7.3: Punctuation Restoration
    punct_restorer = PunctuationRestorer(language=detected_language)
    wsm = punct_restorer.restore_punctuation(wsm)
    word_speaker_mapper.word_speaker_mapping = wsm
    word_speaker_mapper.realign_with_punctuation()
    wsm = word_speaker_mapper.word_speaker_mapping

    # Step 7.4: Mapping Sentences
    sentence_mapper = SentenceSpeakerMapper()
    ssm = sentence_mapper.get_sentences_speaker_mapping(wsm)

    # Step 7.5: 언어 감지 및 검증
    # API 기반 한국어 모델 초기화
    korean_models = KoreanModels(device=device)
    
    # 전체 텍스트를 합쳐서 언어 감지
    full_text = " ".join([utterance["text"] for utterance in ssm])
    
    if not korean_models.is_korean_content(full_text):
        print("⚠️ 경고: 한국어가 아닌 오디오가 감지되었습니다.")
        print("📝 감지된 언어로 처리하거나 한국어 오디오를 사용해주세요.")
        # 한국어가 아닌 경우에도 계속 진행하되 경고 표시
        language_warning = True
    else:
        print("✅ 한국어 오디오가 확인되었습니다.")
        language_warning = False

    # Step 8 (Optional): Write Transcript and SRT Files
    writer = TranscriptWriter()
    writer.write_transcript(ssm, transcript_output_path)
    writer.write_srt(ssm, srt_output_path)

    # Step 9: Classify Speaker Roles
    speaker_roles = await llm_handler.generate("Classification", ssm)

    # Step 9.1: LLM results validate and fallback
    ssm = llm_result_handler.validate_and_fallback(speaker_roles, ssm)
    llm_result_handler.log_result(ssm, speaker_roles)

    # Step 10: Sentiment Analysis (API 기반 배치 처리)
    ssm_with_indices = formatter.add_indices_to_ssm(ssm)
    annotator = Annotator(ssm_with_indices)
    
    # API를 통해 배치로 감정 분석 수행
    texts_for_sentiment = [utterance["text"] for utterance in ssm]
    sentiment_results = await korean_models.analyze_sentiment_batch(texts_for_sentiment)
    
    # 결과를 SSM에 적용
    for i, utterance in enumerate(ssm):
        utterance["sentiment"] = sentiment_results[i]
    
    # Step 11: Profanity Word Detection (API 기반 배치 처리)
    profanity_results = await korean_models.detect_profanity_batch(texts_for_sentiment)
    
    # 결과를 SSM에 적용
    for i, utterance in enumerate(ssm):
        utterance["profane"] = profanity_results[i]

    # Step 12: Summary
    summary_result = await llm_handler.generate("Summary", user_input=ssm)
    annotator.add_summary(summary_result)

    # Step 13: Conflict Detection
    conflict_result = await llm_handler.generate("ConflictDetection", user_input=ssm)
    annotator.add_conflict(conflict_result)

    # Step 14: Topic Detection
    topics = db.fetch(db_topic_fetch_path)
    topic_result = await llm_handler.generate(
        "TopicDetection",
        user_input=ssm,
        system_input=topics
    )
    annotator.add_topic(topic_result)

    # Step 15: Complaint Analysis
    complaint_result = await llm_handler.generate("ComplaintAnalysis", user_input=ssm)
    annotator.add_complaint(complaint_result)

    # Step 16: Action Items
    action_result = await llm_handler.generate("ActionItems", user_input=ssm)
    annotator.add_action_items(action_result)

    # Step 17: Quality Assessment
    quality_result = await llm_handler.generate("QualityAssessment", user_input=ssm)
    annotator.add_quality_assessment(quality_result)

    # Step 18: Extract Audio Properties
    audio_properties = audio_feature_extractor.extract_properties()

    # Step 19: Database Operations
    # Step 19.1: Insert Audio Properties (기존 SQL 파일 사용)
    try:
        # 기존 AudioPropertiesInsert.sql에 맞는 데이터 구조로 변환
        (
            name,
            extension,
            path,
            sample_rate,
            min_freq,
            max_freq,
            bit_depth,
            channels,
            duration,
            rms_loudness,
            final_features
        ) = audio_feature_extractor.properties()
        
        # 기본값 설정
        summary = "오디오 분석 완료"
        conflict_flag = 0
        silence_value = 0.0
        detected_topic = "일반"
        
        # Topic ID 가져오기 (기본값 1 사용)
        topic_id = 1
        
        # AudioPropertiesInsert.sql에 맞는 파라미터 구성
        params = (
            name,
            topic_id,
            extension,
            path,
            sample_rate,
            min_freq,
            max_freq,
            bit_depth,
            channels,
            duration,
            rms_loudness,
            final_features.get("ZeroCrossingRate", 0.0),
            final_features.get("SpectralCentroid", 0.0),
            final_features.get("EQ_20_250_Hz", 0.0),
            final_features.get("EQ_250_2000_Hz", 0.0),
            final_features.get("EQ_2000_6000_Hz", 0.0),
            final_features.get("EQ_6000_20000_Hz", 0.0),
            final_features.get("MFCC_1", 0.0),
            final_features.get("MFCC_2", 0.0),
            final_features.get("MFCC_3", 0.0),
            final_features.get("MFCC_4", 0.0),
            final_features.get("MFCC_5", 0.0),
            final_features.get("MFCC_6", 0.0),
            final_features.get("MFCC_7", 0.0),
            final_features.get("MFCC_8", 0.0),
            final_features.get("MFCC_9", 0.0),
            final_features.get("MFCC_10", 0.0),
            final_features.get("MFCC_11", 0.0),
            final_features.get("MFCC_12", 0.0),
            final_features.get("MFCC_13", 0.0),
            summary,
            conflict_flag,
            silence_value
        )
        
        last_id = db.insert(db_audio_properties_insert_path, params)
        print(f"✅ 오디오 속성 DB 저장 완료: ID {last_id}")
        
    except Exception as e:
        print(f"❌ 오디오 속성 DB 저장 실패: {e}")
        last_id = None

    # Step 19.2: Insert Utterances (기존 SQL 파일 사용)
    if last_id is not None:
        try:
            for i, utterance in enumerate(ssm):
                # UtteranceInsert.sql에 맞는 파라미터 구성
                utterance_params = (
                    last_id,  # FileID
                    utterance["speaker"],  # Speaker
                    i + 1,  # Sequence
                    utterance["start"] / 1000.0,  # StartTime (초 단위)
                    utterance["end"] / 1000.0,  # EndTime (초 단위)
                    utterance["text"],  # Content
                    utterance.get("sentiment", "중립"),  # Sentiment
                    1 if utterance.get("profane", False) else 0  # Profane (0/1)
                )
                db.insert(db_utterance_insert_path, utterance_params)
            
            print(f"✅ 발화 데이터 DB 저장 완료: {len(ssm)}개 발화")
            
        except Exception as e:
            print(f"❌ 발화 데이터 DB 저장 실패: {e}")
    else:
        print("⚠️ File ID가 없어 발화 데이터 저장을 건너뜁니다.")

    # Step 20: Cleanup
    cleaner.cleanup_temp_files(temp_dir)

    print(f"✅ 오디오 처리 완료: {audio_file_path}")
    print(f"📊 처리된 발화 수: {len(ssm)}")
    print(f"🗣️ 감지된 화자 수: {len(set(utterance['speaker'] for utterance in ssm))}")
    print(f"📝 감지된 언어: {detected_language}")
    if language_warning:
        print("⚠️ 언어 경고: 한국어가 아닌 콘텐츠가 포함되어 있습니다.")


async def process(path: str):
    """
    Process a single audio file asynchronously.

    Parameters
    ----------
    path : str
        Path to the audio file to process.

    Returns
    -------
    None
    """
    try:
        print(f"🎵 오디오 파일 처리 시작: {path}")
        await main(path)
        print(f"✅ 오디오 파일 처리 완료: {path}")
    except Exception as e:
        print(f"❌ 오디오 파일 처리 실패: {path}")
        print(f"오류: {e}")


def watch_and_process():
    """
    Watch for new audio files and process them automatically.
    """
    print("🔍 오디오 파일 감시 시작...")
    
    # 감시할 디렉토리 설정
    watch_directories = [
        "/app/audio",
        "/app/temp"
    ]
    
    # 파일 핸들러 클래스 정의
    class FileHandler(FileSystemEventHandler):
        def __init__(self, callback):
            self.callback = callback
            self.processing_files = set()
        
        def on_created(self, event):
            if not event.is_directory:
                self._handle_file(event.src_path)
        
        def on_moved(self, event):
            if not event.is_directory:
                self._handle_file(event.dest_path)
        
        def _handle_file(self, file_path):
            # 이미 처리 중인 파일인지 확인
            if file_path in self.processing_files:
                return
            
            # 오디오 파일 확장자 확인
            audio_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg'}
            if any(file_path.lower().endswith(ext) for ext in audio_extensions):
                print(f"🎵 새로운 오디오 파일 감지: {file_path}")
                self.processing_files.add(file_path)
                
                # 비동기로 파일 처리
                asyncio.create_task(self._process_file(file_path))
        
        async def _process_file(self, file_path):
            try:
                await self.callback(file_path)
            finally:
                # 처리 완료 후 파일 목록에서 제거
                self.processing_files.discard(file_path)
    
    # 파일 핸들러 생성
    handler = FileHandler(process)
    
    # Observer 설정 및 시작
    observer = Observer()
    for directory in watch_directories:
        if os.path.exists(directory):
            observer.schedule(handler, directory, recursive=False)
            print(f"📁 디렉토리 감시 시작: {directory}")
        else:
            print(f"⚠️ 디렉토리가 존재하지 않습니다: {directory}")
    
    observer.start()
    
    try:
        print("🔄 파일 감시 중... (Ctrl+C로 종료)")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 파일 감시 중지...")
        observer.stop()
    
    observer.join()
    print("✅ 파일 감시 종료")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 파일 경로가 제공된 경우 해당 파일만 처리
        file_path = sys.argv[1]
        asyncio.run(process(file_path))
    else:
        # 파일 경로가 제공되지 않은 경우 감시 모드로 실행
        watch_and_process()