-- Callytics 통합 상담 분석 시스템 데이터베이스 스키마
-- 통신사 상담 분석에 특화된 최적화된 스키마

-- =====================================================
-- 1. 오디오 파일 관리 테이블
-- =====================================================

-- 오디오 파일 속성 테이블
CREATE TABLE IF NOT EXISTS audio_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    duration REAL,
    sample_rate INTEGER,
    channels INTEGER,
    file_size INTEGER,
    format TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 2. 화자 분리 및 음성 인식 결과 테이블
-- =====================================================

-- 발화 내용 테이블 (화자 분리 결과)
CREATE TABLE IF NOT EXISTS utterances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audio_properties_id INTEGER,
    speaker TEXT,
    start_time REAL,
    end_time REAL,
    text TEXT,
    confidence REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (audio_properties_id) REFERENCES audio_properties(id)
);

-- =====================================================
-- 3. 상담 분석 결과 테이블
-- =====================================================

-- 상담 분석 결과 테이블 (ChatGPT 분석 결과)
CREATE TABLE IF NOT EXISTS consultation_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audio_properties_id INTEGER,
    business_type TEXT NOT NULL,                    -- 수집기관별 업무 유형
    classification_type TEXT NOT NULL,              -- 분류 유형
    detail_classification TEXT NOT NULL,            -- 세부 분류 유형
    consultation_result TEXT NOT NULL,              -- 상담 결과
    summary TEXT,                                   -- 상담 요약
    customer_request TEXT,                          -- 고객 요청사항
    solution TEXT,                                  -- 해결방안
    additional_info TEXT,                           -- 추가 안내사항
    confidence REAL DEFAULT 0.0,                    -- 분석 신뢰도
    processing_time REAL DEFAULT 0.0,               -- 처리 시간
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (audio_properties_id) REFERENCES audio_properties(id)
);

-- =====================================================
-- 4. 상담 분류 코드 테이블 (참조용)
-- =====================================================

-- 업무 유형 코드 테이블
CREATE TABLE IF NOT EXISTS business_type_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 기본 업무 유형 코드 삽입
INSERT INTO business_type_codes (code, name, description) VALUES 
('FEE_INFO', '요금 안내', '요금제 안내, 요금 계산, 요금 문의 등'),
('FEE_PAYMENT', '요금 납부', '납부 방법, 납부 확인, 납부 오류 등'),
('PLAN_CHANGE', '요금제 변경', '요금제 변경 신청, 변경 안내, 변경 처리 등'),
('SELECTIVE_DISCOUNT', '선택약정 할인', '선택약정 신청, 할인 혜택, 약정 조건 등'),
('PAYMENT_METHOD_CHANGE', '납부 방법 변경', '자동이체, 신용카드, 현금납부 등 납부 방법 변경'),
('ADDITIONAL_SERVICE', '부가서비스 안내', '부가서비스 소개, 가입 안내, 요금 안내 등'),
('MICRO_PAYMENT', '소액 결제', '소액결제 신청, 결제 확인, 결제 오류 등'),
('PHONE_SUSPENSION_LOSS_DAMAGE', '휴대폰 정지 분실 파손', '기기 정지, 분실 신고, 파손 처리 등'),
('DEVICE_CHANGE', '기기변경', '기기 교체, 기기 업그레이드, 기기 이전 등'),
('NAME_NUMBER_USIM_CANCEL', '명의 번호 유심 해지', '명의 변경, 번호 변경, 유심 해지 등'),
('OTHER', '그 외 업무유형', '기타 통신사 관련 업무');

-- 분류 유형 코드 테이블
CREATE TABLE IF NOT EXISTS classification_type_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 기본 분류 유형 코드 삽입
INSERT INTO classification_type_codes (code, name, description) VALUES 
('CONSULTATION_TOPIC', '상담 주제', '상담의 주요 주제 분류'),
('CONSULTATION_REQUIREMENT', '상담 요건', '상담 요건의 복잡도 분류'),
('CONSULTATION_CONTENT', '상담 내용', '상담 내용의 성격 분류'),
('CONSULTATION_REASON', '상담 사유', '상담 발생 사유 분류'),
('CONSULTATION_RESULT', '상담 결과', '상담 결과 평가 분류');

-- 세부 분류 코드 테이블
CREATE TABLE IF NOT EXISTS detail_classification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classification_type_code TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (classification_type_code) REFERENCES classification_type_codes(code),
    UNIQUE(classification_type_code, code)
);

-- 기본 세부 분류 코드 삽입
INSERT INTO detail_classification_codes (classification_type_code, code, name, description) VALUES 
-- 상담 주제
('CONSULTATION_TOPIC', 'PRODUCT_SERVICE_GENERAL', '상품 및 서비스 일반', '상품 및 서비스에 대한 일반적인 문의'),
('CONSULTATION_TOPIC', 'ORDER_PAYMENT_DEPOSIT_CONFIRM', '주문 결제 입금 확인', '주문, 결제, 입금 관련 확인 문의'),
('CONSULTATION_TOPIC', 'CANCEL_RETURN_EXCHANGE_REFUND_AS', '취소 반품 교환 환불 AS', '취소, 반품, 교환, 환불, AS 관련 문의'),
('CONSULTATION_TOPIC', 'MEMBER_MANAGEMENT', '회원 관리', '회원 정보 관리, 계정 관련 문의'),
('CONSULTATION_TOPIC', 'DELIVERY_INQUIRY', '배송 문의', '배송 관련 문의 및 문제'),
('CONSULTATION_TOPIC', 'EVENT_DISCOUNT', '이벤트 할인', '이벤트, 할인, 프로모션 관련 문의'),
('CONSULTATION_TOPIC', 'CONTENT', '콘텐츠', '콘텐츠 관련 문의'),
('CONSULTATION_TOPIC', 'PARTNERSHIP', '제휴', '제휴 서비스 관련 문의'),
('CONSULTATION_TOPIC', 'ETC', '기타', '기타 상담 주제'),

-- 상담 요건
('CONSULTATION_REQUIREMENT', 'SINGLE_REQUIREMENT', '단일 요건 민원', '단일 요건에 대한 민원'),
('CONSULTATION_REQUIREMENT', 'MULTIPLE_REQUIREMENT', '다수 요건 민원', '다수 요건에 대한 민원'),

-- 상담 내용
('CONSULTATION_CONTENT', 'GENERAL_INQUIRY', '일반 문의 상담', '일반적인 문의 및 안내 상담'),
('CONSULTATION_CONTENT', 'BUSINESS_PROCESSING', '업무 처리 상담', '실제 업무 처리 및 신청 상담'),
('CONSULTATION_CONTENT', 'COMPLAINT', '고충 상담', '고충 사항 및 불만 상담'),

-- 상담 사유
('CONSULTATION_REASON', 'COMPANY', '업체', '업체 관련 상담'),
('CONSULTATION_REASON', 'COMPLAINANT', '민원인', '민원인 관련 상담'),

-- 상담 결과
('CONSULTATION_RESULT', 'SATISFACTION', '만족', '고객이 만족한 상담'),
('CONSULTATION_RESULT', 'INSUFFICIENT', '미흡', '상담이 미흡한 경우'),
('CONSULTATION_RESULT', 'UNSOLVABLE', '해결 불가', '해결이 불가능한 경우'),
('CONSULTATION_RESULT', 'ADDITIONAL_CONSULTATION', '추가 상담 필요', '추가 상담이 필요한 경우');

-- =====================================================
-- 5. 성능 최적화 인덱스
-- =====================================================

-- 오디오 파일 관련 인덱스
CREATE INDEX IF NOT EXISTS idx_audio_properties_file_path ON audio_properties(file_path);
CREATE INDEX IF NOT EXISTS idx_audio_properties_created_at ON audio_properties(created_at);

-- 발화 내용 관련 인덱스
CREATE INDEX IF NOT EXISTS idx_utterances_audio_id ON utterances(audio_properties_id);
CREATE INDEX IF NOT EXISTS idx_utterances_speaker ON utterances(speaker);
CREATE INDEX IF NOT EXISTS idx_utterances_start_time ON utterances(start_time);

-- 상담 분석 관련 인덱스
CREATE INDEX IF NOT EXISTS idx_consultation_analysis_audio_id ON consultation_analysis(audio_properties_id);
CREATE INDEX IF NOT EXISTS idx_consultation_analysis_business_type ON consultation_analysis(business_type);
CREATE INDEX IF NOT EXISTS idx_consultation_analysis_classification_type ON consultation_analysis(classification_type);
CREATE INDEX IF NOT EXISTS idx_consultation_analysis_consultation_result ON consultation_analysis(consultation_result);
CREATE INDEX IF NOT EXISTS idx_consultation_analysis_created_at ON consultation_analysis(created_at);

-- 코드 테이블 관련 인덱스
CREATE INDEX IF NOT EXISTS idx_business_type_codes_code ON business_type_codes(code);
CREATE INDEX IF NOT EXISTS idx_classification_type_codes_code ON classification_type_codes(code);
CREATE INDEX IF NOT EXISTS idx_detail_classification_codes_type_code ON detail_classification_codes(classification_type_code);

-- =====================================================
-- 6. 통계 뷰
-- =====================================================

-- 상담 분석 통계 뷰
CREATE VIEW consultation_statistics AS
SELECT 
    ca.business_type,
    ca.classification_type,
    ca.consultation_result,
    COUNT(*) as total_count,
    AVG(ca.confidence) as avg_confidence,
    AVG(ca.processing_time) as avg_processing_time,
    MIN(ca.created_at) as first_analysis,
    MAX(ca.created_at) as last_analysis
FROM consultation_analysis ca
GROUP BY ca.business_type, ca.classification_type, ca.consultation_result;

-- 일별 상담 분석 통계 뷰
CREATE VIEW daily_consultation_stats AS
SELECT 
    DATE(ca.created_at) as analysis_date,
    COUNT(*) as total_analyses,
    COUNT(DISTINCT ca.audio_properties_id) as unique_files,
    AVG(ca.confidence) as avg_confidence,
    AVG(ca.processing_time) as avg_processing_time
FROM consultation_analysis ca
GROUP BY DATE(ca.created_at)
ORDER BY analysis_date DESC; 