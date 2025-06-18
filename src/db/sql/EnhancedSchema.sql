-- 기존 스키마에 민원 분석 기능 추가

-- 민원 분류 테이블
CREATE TABLE ComplaintCategory (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL UNIQUE CHECK (length(Name) <= 200),
    Description TEXT,
    ParentID INTEGER,
    FOREIGN KEY (ParentID) REFERENCES ComplaintCategory (ID)
);

-- 기본 민원 카테고리 삽입
INSERT INTO ComplaintCategory (Name, Description) VALUES 
('교통', '교통 관련 민원'),
('환경', '환경 관련 민원'),
('복지', '복지 관련 민원'),
('교육', '교육 관련 민원'),
('건설', '건설 관련 민원'),
('행정', '행정 관련 민원'),
('기타', '기타 민원');

-- 민원 분석 결과 테이블
CREATE TABLE ComplaintAnalysis (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    CategoryID INTEGER,
    Severity TEXT CHECK (Severity IN ('Low', 'Medium', 'High', 'Critical')),
    Urgency TEXT CHECK (Urgency IN ('Low', 'Medium', 'High', 'Critical')),
    Satisfaction INTEGER CHECK (Satisfaction >= 1 AND Satisfaction <= 5),
    ResolutionStatus TEXT CHECK (ResolutionStatus IN ('Pending', 'In Progress', 'Resolved', 'Escalated')),
    Keywords TEXT, -- JSON 형태로 키워드 저장
    SentimentScore REAL, -- -1.0 ~ 1.0
    AnalysisDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID),
    FOREIGN KEY (CategoryID) REFERENCES ComplaintCategory (ID)
);

-- 질의응답 테이블
CREATE TABLE QAResponse (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    Question TEXT NOT NULL,
    Answer TEXT NOT NULL,
    Confidence REAL CHECK (Confidence >= 0.0 AND Confidence <= 1.0),
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID)
);

-- 민원 요약 테이블 (기존 Summary 필드 대체)
CREATE TABLE ComplaintSummary (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    Summary TEXT NOT NULL,
    KeyPoints TEXT, -- JSON 형태로 핵심 포인트 저장
    ActionItems TEXT, -- JSON 형태로 액션 아이템 저장
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID)
);

-- 민원 처리 이력 테이블
CREATE TABLE ComplaintHistory (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    Action TEXT NOT NULL,
    Description TEXT,
    AssignedTo TEXT,
    Status TEXT CHECK (Status IN ('Open', 'In Progress', 'Completed', 'Closed')),
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID)
);

-- 민원 우선순위 테이블
CREATE TABLE ComplaintPriority (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    PriorityLevel INTEGER CHECK (PriorityLevel >= 1 AND PriorityLevel <= 5),
    PriorityReason TEXT,
    EscalationLevel INTEGER DEFAULT 1,
    EscalationDate DATETIME,
    FOREIGN KEY (FileID) REFERENCES File (ID)
);

-- 민원 관련 부서 테이블
CREATE TABLE Department (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL UNIQUE,
    Description TEXT,
    ContactInfo TEXT
);

-- 기본 부서 삽입
INSERT INTO Department (Name, Description) VALUES 
('교통과', '교통 관련 업무'),
('환경과', '환경 관련 업무'),
('복지과', '복지 관련 업무'),
('교육과', '교육 관련 업무'),
('건설과', '건설 관련 업무'),
('행정과', '행정 관련 업무');

-- 민원-부서 매핑 테이블
CREATE TABLE ComplaintDepartmentMapping (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    DepartmentID INTEGER NOT NULL,
    IsPrimary BOOLEAN DEFAULT FALSE,
    AssignedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID),
    FOREIGN KEY (DepartmentID) REFERENCES Department (ID)
);

-- 민원 템플릿 테이블
CREATE TABLE ComplaintTemplate (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    CategoryID INTEGER,
    TemplateName TEXT NOT NULL,
    TemplateContent TEXT NOT NULL,
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CategoryID) REFERENCES ComplaintCategory (ID)
);

-- 민원 통계 뷰
CREATE VIEW ComplaintStatistics AS
SELECT 
    cc.Name as CategoryName,
    COUNT(f.ID) as TotalComplaints,
    AVG(ca.SentimentScore) as AvgSentiment,
    AVG(ca.Satisfaction) as AvgSatisfaction,
    COUNT(CASE WHEN ca.ResolutionStatus = 'Resolved' THEN 1 END) as ResolvedCount,
    COUNT(CASE WHEN ca.Severity = 'High' OR ca.Severity = 'Critical' THEN 1 END) as HighPriorityCount
FROM File f
LEFT JOIN ComplaintAnalysis ca ON f.ID = ca.FileID
LEFT JOIN ComplaintCategory cc ON ca.CategoryID = cc.ID
GROUP BY cc.ID, cc.Name;

-- 인덱스 생성
CREATE INDEX idx_complaint_analysis_fileid ON ComplaintAnalysis(FileID);
CREATE INDEX idx_complaint_analysis_category ON ComplaintAnalysis(CategoryID);
CREATE INDEX idx_complaint_analysis_severity ON ComplaintAnalysis(Severity);
CREATE INDEX idx_qa_response_fileid ON QAResponse(FileID);
CREATE INDEX idx_complaint_summary_fileid ON ComplaintSummary(FileID);
CREATE INDEX idx_complaint_history_fileid ON ComplaintHistory(FileID);
CREATE INDEX idx_complaint_priority_fileid ON ComplaintPriority(FileID);

-- 기존 스키마에 통신사 민원 분석 기능 추가

-- 통신사 업무 분야 테이블
CREATE TABLE ComplaintCategory (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL UNIQUE CHECK (length(Name) <= 200),
    Description TEXT,
    ParentID INTEGER,
    FOREIGN KEY (ParentID) REFERENCES ComplaintCategory (ID)
);

-- 기본 통신사 업무 분야 삽입
INSERT INTO ComplaintCategory (Name, Description) VALUES 
('요금 안내', '요금제 안내, 요금 계산, 요금 문의 등'),
('요금 납부', '납부 방법, 납부 확인, 납부 오류 등'),
('요금제 변경', '요금제 변경 신청, 변경 안내, 변경 처리 등'),
('선택약정 할인', '선택약정 신청, 할인 혜택, 약정 조건 등'),
('납부 방법 변경', '자동이체, 신용카드, 현금납부 등 납부 방법 변경'),
('부가서비스 안내', '부가서비스 소개, 가입 안내, 요금 안내 등'),
('소액 결제', '소액결제 신청, 결제 확인, 결제 오류 등'),
('휴대폰 정지/분실/파손', '기기 정지, 분실 신고, 파손 처리 등'),
('기기변경', '기기 교체, 기기 업그레이드, 기기 이전 등'),
('명의/번호/유심 해지', '명의 변경, 번호 변경, 유심 해지 등'),
('기타', '기타 통신사 관련 업무');

-- 통신사 상담 주제 테이블
CREATE TABLE ConsultationTopic (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL UNIQUE CHECK (length(Name) <= 200),
    Description TEXT
);

-- 기본 통신사 상담 주제 삽입
INSERT INTO ConsultationTopic (Name, Description) VALUES 
('상품 및 서비스 일반', '상품 및 서비스에 대한 일반적인 문의'),
('주문/결제/입금 확인', '주문, 결제, 입금 관련 확인 문의'),
('취소/반품/교환/환불/AS', '취소, 반품, 교환, 환불, AS 관련 문의'),
('회원 관리', '회원 정보 관리, 계정 관련 문의'),
('배송 문의', '배송 관련 문의 및 문제'),
('이벤트/할인', '이벤트, 할인, 프로모션 관련 문의'),
('콘텐츠', '콘텐츠 관련 문의'),
('제휴', '제휴 서비스 관련 문의'),
('기타', '기타 상담 주제');

-- 통신사 상담 내용 유형 테이블
CREATE TABLE ConsultationType (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL UNIQUE CHECK (length(Name) <= 200),
    Description TEXT
);

-- 기본 통신사 상담 내용 유형 삽입
INSERT INTO ConsultationType (Name, Description) VALUES 
('일반 문의 상담', '일반적인 문의 및 안내 상담'),
('업무 처리 상담', '실제 업무 처리 및 신청 상담'),
('고충 상담', '고객 불만 및 고충 상담');

-- 통신사 민원 분석 결과 테이블
CREATE TABLE ComplaintAnalysis (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    CategoryID INTEGER,
    TopicID INTEGER,
    TypeID INTEGER,
    Severity TEXT CHECK (Severity IN ('Low', 'Medium', 'High', 'Critical')),
    Urgency TEXT CHECK (Urgency IN ('Low', 'Medium', 'High', 'Critical')),
    Satisfaction INTEGER CHECK (Satisfaction >= 1 AND Satisfaction <= 5),
    ResolutionStatus TEXT CHECK (ResolutionStatus IN ('Pending', 'In Progress', 'Resolved', 'Escalated')),
    Keywords TEXT, -- JSON 형태로 키워드 저장
    SentimentScore REAL, -- -1.0 ~ 1.0
    AnalysisDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID),
    FOREIGN KEY (CategoryID) REFERENCES ComplaintCategory (ID),
    FOREIGN KEY (TopicID) REFERENCES ConsultationTopic (ID),
    FOREIGN KEY (TypeID) REFERENCES ConsultationType (ID)
);

-- 질의응답 테이블
CREATE TABLE QAResponse (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    Question TEXT NOT NULL,
    Answer TEXT NOT NULL,
    Confidence REAL CHECK (Confidence >= 0.0 AND Confidence <= 1.0),
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID)
);

-- 통신사 민원 요약 테이블 (기존 Summary 필드 대체)
CREATE TABLE ComplaintSummary (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    Summary TEXT NOT NULL,
    KeyPoints TEXT, -- JSON 형태로 핵심 포인트 저장
    ActionItems TEXT, -- JSON 형태로 액션 아이템 저장
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID)
);

-- 통신사 민원 처리 이력 테이블
CREATE TABLE ComplaintHistory (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    Action TEXT NOT NULL,
    Description TEXT,
    AssignedTo TEXT,
    Status TEXT CHECK (Status IN ('Open', 'In Progress', 'Completed', 'Closed')),
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID)
);

-- 통신사 민원 우선순위 테이블
CREATE TABLE ComplaintPriority (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    PriorityLevel INTEGER CHECK (PriorityLevel >= 1 AND PriorityLevel <= 5),
    PriorityReason TEXT,
    EscalationLevel INTEGER DEFAULT 1,
    EscalationDate DATETIME,
    FOREIGN KEY (FileID) REFERENCES File (ID)
);

-- LG U+ 부서 테이블
CREATE TABLE Department (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL UNIQUE,
    Description TEXT,
    ServiceType TEXT CHECK (ServiceType IN ('Home', 'Mobile')), -- 홈 서비스 또는 모바일 서비스
    ContactInfo TEXT
);

-- 기본 LG U+ 부서 삽입
INSERT INTO Department (Name, Description, ServiceType) VALUES 
-- 홈 서비스 부서
('홈서비스일반상담', '인터넷, TV, IoT 등 서비스에 대한 일반적인 문제해결과 정보 변경', 'Home'),
('홈서비스기술상담', '인터넷, TV, IoT 등 서비스에 대한 장애, 품질, 단말기 A/S 지원', 'Home'),
('홈서비스가입상담', '서비스 가입에 대한 고객별 맞춤 혜택 안내와 가입 신청 접수', 'Home'),
('홈가치제안상담', '해지 희망 고객에 대한 불편사항 처리와 재약정, 요금할인 안내', 'Home'),

-- 모바일 서비스 부서
('모바일일반상담', '휴대폰 서비스에 대한 일반적인 문제해결과 요금제 컨설팅 등 정보 변경', 'Mobile'),
('SAVE상담', '해지 희망 고객과 휴대폰 분실/파손 고객에 대한 맞춤 혜택 안내', 'Mobile'),
('통화품질상담', '휴대폰 통화품질 문의에 대한 문제해결 방법 제공', 'Mobile'),
('전문상담', '로밍상담, 유플러스샵, cyber, 외국인상담, 알뜰폰 등 전문 서비스 지원', 'Mobile');

-- 통신사 민원-부서 매핑 테이블
CREATE TABLE ComplaintDepartmentMapping (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    FileID INTEGER NOT NULL,
    DepartmentID INTEGER NOT NULL,
    IsPrimary BOOLEAN DEFAULT FALSE,
    AssignedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (FileID) REFERENCES File (ID),
    FOREIGN KEY (DepartmentID) REFERENCES Department (ID)
);

-- 통신사 민원 템플릿 테이블
CREATE TABLE ComplaintTemplate (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    CategoryID INTEGER,
    TemplateName TEXT NOT NULL,
    TemplateContent TEXT NOT NULL,
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedDate DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CategoryID) REFERENCES ComplaintCategory (ID)
);

-- 통신사 민원 통계 뷰
CREATE VIEW ComplaintStatistics AS
SELECT 
    cc.Name as CategoryName,
    ct.Name as TopicName,
    cty.Name as TypeName,
    d.Name as DepartmentName,
    d.ServiceType,
    COUNT(f.ID) as TotalComplaints,
    AVG(ca.SentimentScore) as AvgSentiment,
    AVG(ca.Satisfaction) as AvgSatisfaction,
    COUNT(CASE WHEN ca.ResolutionStatus = 'Resolved' THEN 1 END) as ResolvedCount,
    COUNT(CASE WHEN ca.Severity = 'High' OR ca.Severity = 'Critical' THEN 1 END) as HighPriorityCount
FROM File f
LEFT JOIN ComplaintAnalysis ca ON f.ID = ca.FileID
LEFT JOIN ComplaintCategory cc ON ca.CategoryID = cc.ID
LEFT JOIN ConsultationTopic ct ON ca.TopicID = ct.ID
LEFT JOIN ConsultationType cty ON ca.TypeID = cty.ID
LEFT JOIN ComplaintDepartmentMapping cdm ON f.ID = cdm.FileID
LEFT JOIN Department d ON cdm.DepartmentID = d.ID
GROUP BY cc.ID, cc.Name, ct.ID, ct.Name, cty.ID, cty.Name, d.ID, d.Name, d.ServiceType;

-- 인덱스 생성
CREATE INDEX idx_complaint_analysis_fileid ON ComplaintAnalysis(FileID);
CREATE INDEX idx_complaint_analysis_category ON ComplaintAnalysis(CategoryID);
CREATE INDEX idx_complaint_analysis_topic ON ComplaintAnalysis(TopicID);
CREATE INDEX idx_complaint_analysis_type ON ComplaintAnalysis(TypeID);
CREATE INDEX idx_complaint_analysis_severity ON ComplaintAnalysis(Severity);
CREATE INDEX idx_qa_response_fileid ON QAResponse(FileID);
CREATE INDEX idx_complaint_summary_fileid ON ComplaintSummary(FileID);
CREATE INDEX idx_complaint_history_fileid ON ComplaintHistory(FileID);
CREATE INDEX idx_complaint_priority_fileid ON ComplaintPriority(FileID); 