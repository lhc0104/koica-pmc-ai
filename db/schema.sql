-- BUCAS PMC AI 사업비서 : 통합 사업 지식베이스(정형 데이터) 스키마 v0.5
-- 원칙: 환자 단위 정보 미취급(집계값만) / 수치·문서는 출처(doc_id)와 연결 / 공식 수치는 전문가 검증 표시

PRAGMA foreign_keys = ON;

-- ───────── 공통 ─────────
CREATE TABLE IF NOT EXISTS users (
  user_id      TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  org          TEXT,
  role         TEXT NOT NULL CHECK(role IN ('ADMIN','PM','PL','PAO','EXPERT','KOICA_VIEWER')),
  email        TEXT,
  active       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS documents (           -- 비정형 문서 메타(기준문서·회의록·보고서·공문·2차자료)
  doc_id       TEXT PRIMARY KEY,
  title        TEXT NOT NULL,
  doc_type     TEXT NOT NULL,                    -- 기준문서/회의록/보고서/공문/2차자료/주간보고/기타
  language     TEXT DEFAULT 'ko',
  doc_date     TEXT,
  source_org   TEXT,
  file_path    TEXT,
  version      TEXT DEFAULT 'v1',
  access_level TEXT DEFAULT 'INTERNAL',          -- INTERNAL / KOICA / PUBLIC
  created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doc_chunks (          -- 검색 단위(1단계: 키워드 검색 → 2단계: 임베딩 컬럼 추가)
  chunk_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  doc_id       TEXT NOT NULL REFERENCES documents(doc_id),
  seq          INTEGER,
  heading      TEXT,
  content      TEXT NOT NULL
);

-- ───────── 모듈① 사업관리 ─────────
CREATE TABLE IF NOT EXISTS milestones (
  milestone_id   TEXT PRIMARY KEY,
  title          TEXT NOT NULL,
  category       TEXT,                           -- 공정/보고/회의/파견·출장
  project_year   INTEGER,
  due_date       TEXT NOT NULL,
  owner          TEXT,
  status         TEXT DEFAULT '예정' CHECK(status IN ('예정','진행중','완료','지연')),
  related_output TEXT,
  note           TEXT,
  due_rule       TEXT
);

CREATE TABLE IF NOT EXISTS stakeholders (
  stakeholder_id TEXT PRIMARY KEY,
  org            TEXT NOT NULL,
  dept           TEXT,
  person_name    TEXT,
  position       TEXT,
  contact        TEXT,                           -- 업무 목적 범위 최소 수집
  category       TEXT,                           -- KOICA/DOH/CHD/모병원/수행기관/공여기관
  valid_from     TEXT,
  valid_to       TEXT                            -- 담당자 변경 이력
);

CREATE TABLE IF NOT EXISTS meetings (         -- 회의록 (v0.5: 대·중·소분류 + 안건·결과·후속조치)
  meeting_id      TEXT PRIMARY KEY,              -- MT-001 …
  meeting_date    TEXT NOT NULL,                 -- YYYY-MM-DD (연도별 탭의 기준)
  meeting_time    TEXT,                          -- HH:MM (선택)
  title           TEXT NOT NULL,                 -- 회의명
  activity        TEXT,                          -- 대분류: 과업(Activity) 이름 — activities 표의 '활동ID 활동명'
  meeting_type    TEXT,                          -- 중분류: 내부회의 / 외부회의
  stakeholder_org TEXT,                          -- 소분류: 이해관계기관 (stakeholders 표, 직접 입력으로 추가 가능)
  location        TEXT,
  participants    TEXT,
  agenda          TEXT,                          -- 회의 주요 안건
  summary         TEXT,                          -- 회의 결과 요약
  follow_up       TEXT,                          -- 후속조치사항 (한 줄에 하나 → action_items 로도 등록)
  author          TEXT,
  file_path       TEXT,                          -- 첨부 원본 파일 (pmc/4_사업관리/문서/회의록/…)
  doc_id          TEXT REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS action_items (        -- 회의 결정사항·후속조치
  action_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  meeting_id   TEXT REFERENCES meetings(meeting_id),
  description  TEXT NOT NULL,
  owner        TEXT,
  due_date     TEXT,
  status       TEXT DEFAULT '미이행' CHECK(status IN ('미이행','진행중','완료')),
  closed_at    TEXT
);

CREATE TABLE IF NOT EXISTS weekly_reports (     -- (v0.4 이전 형식 — 화면에서는 더 이상 쓰지 않음)
  report_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  week_start     TEXT NOT NULL,
  author         TEXT NOT NULL,
  done           TEXT,
  plan           TEXT,
  issues         TEXT,
  related_output TEXT
);

CREATE TABLE IF NOT EXISTS weekly_entries (     -- 주간업무보고 (v0.5): 주차 × 구분(PM/PAO/현지직원/국내활동) 한 칸 = 한 행
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  week_start TEXT NOT NULL,                      -- 그 주 월요일 (YYYY-MM-DD)
  role       TEXT NOT NULL,                      -- 구분(열 이름): settings.yaml weekly.columns
  author     TEXT,                               -- 작성자 이름
  position   TEXT,                               -- 직책
  content    TEXT NOT NULL,                      -- 그 주차 활동내용
  updated_at TEXT,
  UNIQUE(week_start, role)
);

-- ───────── 모듈② 성과관리 ─────────
CREATE TABLE IF NOT EXISTS outputs (             -- 6개 사업산출물
  output_id    TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  description  TEXT,
  progress_pct REAL DEFAULT 0,
  lead_expert  TEXT,
  outcome      TEXT,                             -- 상위 성과(Outcome)
  implementer  TEXT,                             -- 수행기관(현지 기관 / PMC)
  deliverable  TEXT                              -- RFP '사업산출물 형태'
);

CREATE TABLE IF NOT EXISTS sub_outputs (         -- 70여 종 보조산출물(a~f 계열)
  sub_output_id    TEXT PRIMARY KEY,
  output_id        TEXT REFERENCES outputs(output_id),
  series           TEXT,
  name             TEXT NOT NULL,
  due_date         TEXT,
  language         TEXT,                         -- 국문/영문/국·영문
  owner            TEXT,
  status           TEXT DEFAULT '미착수' CHECK(status IN ('미착수','작성중','제출','보완요청','승인')),
  approval_method  TEXT,                         -- POD/OD 승인방법
  quality_criteria TEXT,                         -- POD/OD 품질기준
  submitted_at     TEXT,
  doc_id           TEXT,
  due_rule         TEXT                          -- RFP '생산시점' 원문(기한 계산의 근거)
);

CREATE TABLE IF NOT EXISTS management_docs (     -- 착수·반기·연차 등 관리문서
  mdoc_id   TEXT PRIMARY KEY,
  name      TEXT NOT NULL,
  cycle     TEXT,
  next_due  TEXT,
  language  TEXT,
  owner     TEXT,
  status    TEXT DEFAULT '예정',
  due_rule  TEXT,                                -- RFP '제출시점' 원문
  contents  TEXT                                 -- RFP '포함사항'
);

CREATE TABLE IF NOT EXISTS pdm_indicators (
  indicator_id  TEXT PRIMARY KEY,
  level         TEXT NOT NULL CHECK(level IN ('Impact','Outcome','Output')),
  output_id     TEXT,
  name          TEXT NOT NULL,
  definition    TEXT,
  formula       TEXT,
  unit          TEXT,
  baseline      REAL,
  baseline_year INTEGER,
  target        REAL,
  target_year   INTEGER,
  mov           TEXT,                            -- 입증수단
  data_source   TEXT,
  frequency     TEXT,
  pdm_version   TEXT DEFAULT 'v1.0',
  target_basis  TEXT,                            -- 목표치 선정 근거
  collector     TEXT,                            -- 데이터 수집 주체
  origin        TEXT DEFAULT 'RFP PDM',          -- RFP PDM / 제안사 추가제안 / 개정
  remark        TEXT                             -- 성과점검표 '비고'(N/A 사유, 목표치 미달성 사유 등)
);

CREATE TABLE IF NOT EXISTS indicator_values (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  indicator_id  TEXT REFERENCES pdm_indicators(indicator_id),
  period        TEXT NOT NULL,
  value         REAL,
  verified_by   TEXT,                            -- NULL = 전문가 미검증
  source_doc_id TEXT
);

CREATE TABLE IF NOT EXISTS centers (
  center_id       TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  region          TEXT,
  province        TEXT,
  support_type    TEXT,                          -- 모델링/기본지원/확인필요
  mother_hospital TEXT
);

CREATE TABLE IF NOT EXISTS center_monthly (      -- 센터별 월별 집계 실적(환자 식별정보 없음)
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  center_id     TEXT REFERENCES centers(center_id),
  month         TEXT NOT NULL,                   -- YYYY-MM
  metric        TEXT NOT NULL,
  value         REAL,
  is_sample     INTEGER DEFAULT 0,
  source_doc_id TEXT,
  UNIQUE(center_id, month, metric)
);

-- ───────── 모듈③ AI 사업비서 ─────────
CREATE TABLE IF NOT EXISTS chat_log (            -- 질의응답·출처·전문가 평가(답변 정확도 검증용)
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ts             TEXT DEFAULT CURRENT_TIMESTAMP,
  user_id        TEXT,
  question       TEXT,
  answer         TEXT,
  tool_calls     TEXT,                           -- JSON
  expert_rating  INTEGER,
  expert_comment TEXT
);

CREATE TABLE IF NOT EXISTS ai_questions (        -- AI가 담당자에게 '내는' 점검 질문과 그 답변
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
  trigger_type TEXT,                             -- 기초선누락/기한임박/이상치/후속조치미이행
  target_ref   TEXT,
  assignee     TEXT,
  question     TEXT NOT NULL,
  answer       TEXT,
  answered_at  TEXT,
  status       TEXT DEFAULT '대기',
  UNIQUE(trigger_type, target_ref)
);

-- ───────── 문제보고 ─────────
CREATE TABLE IF NOT EXISTS issue_reports (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT DEFAULT (datetime('now','localtime')),
  author     TEXT,
  menu       TEXT,
  kind       TEXT,
  content    TEXT NOT NULL,
  status     TEXT DEFAULT '접수'
);

-- ───────── RFP·PDM 연계(v0.4) ─────────
CREATE TABLE IF NOT EXISTS activities (          -- PDM 활동 + 사업관리 항목 : 전체 일정표(분기 단위)의 원천
  activity_id  TEXT PRIMARY KEY,
  output_id    TEXT,                             -- 1.1 ~ 3.2, 사업관리는 PM
  name         TEXT NOT NULL,
  implementer  TEXT,
  pmc_role     TEXT,
  start_q      TEXT,                             -- 예: 2027Q1
  end_q        TEXT,
  focus_end_q  TEXT,                             -- 집중 추진 구간의 끝(RFP 일정표의 진한 음영)
  note         TEXT
);

CREATE TABLE IF NOT EXISTS indicator_targets (   -- 성과점검표의 '연간 목표치'
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  indicator_id TEXT NOT NULL,
  year         INTEGER NOT NULL,
  target       REAL,
  note         TEXT,
  UNIQUE(indicator_id, year)
);

CREATE TABLE IF NOT EXISTS experts (             -- 전문가 투입계획(M/D)
  expert_id    TEXT PRIMARY KEY,
  role         TEXT NOT NULL,
  category     TEXT,                             -- 주요 / 일반
  grade        TEXT,
  person_name  TEXT,
  md_domestic  INTEGER,
  md_overseas  INTEGER,
  md_total     INTEGER,
  duties       TEXT
);

CREATE TABLE IF NOT EXISTS risks (               -- 위험관리대장(출발점: PDM 중요가정)
  risk_id      TEXT PRIMARY KEY,
  source       TEXT,
  description  TEXT NOT NULL,
  level        TEXT DEFAULT '중' CHECK(level IN ('상','중','하')),
  status       TEXT DEFAULT '모니터링' CHECK(status IN ('모니터링','발생','해소')),
  mitigation   TEXT,
  owner        TEXT,
  updated_at   TEXT
);

-- ───────── PDM 폴더 원문(v0.5): [5. 성과관리 › 사업산출물]에서 엑셀형 표로 보고 고친다 ─────────
CREATE TABLE IF NOT EXISTS pdm_matrix (          -- 사업논리모형(PDM, 1. PDM.pdf) : 요약·검증지표·검증수단·중요가정 + 검증지표 추가제안(제안서 양식)
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  version     INTEGER DEFAULT 1,                 -- PDM 버전(v1 = RFP 첨부 원본). 버전마다 전체 행을 따로 가진다
  seq         REAL,                              -- 표시 순서(사이에 끼우려면 4.5 처럼 소수 사용)
  level       TEXT NOT NULL,                     -- 기본정보 / 영향(Impact) / 성과(Outcome) / 산출물(Output) / 활동(Activity) / 투입물(Input) / 선행조건(Pre-condition)
  code        TEXT,                              -- 1, 1.1, 1.1.1 …  (기본정보는 항목명)
  summary     TEXT,                              -- Narrative Summary(요약)
  indicators  TEXT,                              -- Objectively Verifiable Indicators(객관적 검증지표) — 여러 개는 줄바꿈
  mov         TEXT,                              -- Means of Verification(검증수단)
  assumptions TEXT,                              -- Important Assumptions(중요가정)
  proposal    TEXT,                              -- 검증지표 추가제안(제안서 '사업논리모형(PDM) 제안' 양식의 빈 칸)
  note        TEXT
);

CREATE TABLE IF NOT EXISTS change_model (        -- 사업변화모델(3. 사업변화모델.pdf) : 결과(영향) → 변화(성과) → 변화(산출물) → 수단(활동) 트리
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  seq         REAL,
  stage       TEXT NOT NULL,                     -- 결과(영향) / 변화(성과) / 변화(산출물) / 수단(활동)
  code        TEXT,
  parent_code TEXT,                              -- 상위 항목 코드(트리 연결)
  content     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pdm_versions (        -- PDM 버전 이력: [새로운 버전 추가]를 누르면 마지막 버전을 복사해 한 줄 늘어난다
  version     INTEGER PRIMARY KEY,
  created_at  TEXT,
  author      TEXT,
  reason      TEXT,                              -- 변경 사유·주요 변경 내용
  status      TEXT DEFAULT '초안' CHECK(status IN ('초안','검토중','확정')),
  approved_at TEXT,                              -- 확정(승인)일
  note        TEXT
);

CREATE TABLE IF NOT EXISTS pdm_evidence (        -- PDM 버전별 근거자료(회의록·공문·조사 결과 등) — 파일은 pmc/5_성과관리/PDM근거/v{n}/
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  version     INTEGER NOT NULL,
  file_name   TEXT NOT NULL,
  file_path   TEXT,
  note        TEXT,
  uploaded_at TEXT
);

CREATE TABLE IF NOT EXISTS pms_meta (            -- 성과점검표(KOICA 성과관리양식 v3.2) 머리글: 사업명(기간/예산), 1~7차년도 작성일
  key   TEXT PRIMARY KEY,
  value TEXT
);
