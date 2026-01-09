# 똑소리 프로젝트 - RAG 시스템 설정 및 실행 가이드

**작성일**: 2026-01-05  
**버전**: v2.0  
**대상**: PR #4 - 멀티 에이전트 시스템 준비

---

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [사전 준비](#사전-준비)
3. [데이터베이스 설정](#데이터베이스-설정)
4. [임베딩 파이프라인 실행](#임베딩-파이프라인-실행)
5. [RAG 검색 테스트](#rag-검색-테스트)
6. [트러블슈팅](#트러블슈팅)

---

## 🎯 시스템 개요

### 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    RAG 시스템 v2                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [데이터 소스]                                          │
│    ├─ 법령 (13개 법령, 5,455 청크)                      │
│    ├─ 피해구제사례 (3개 파일, 13,544 청크)              │
│    └─ 분쟁조정사례 (4개 파일, 11,755 청크)              │
│                                                         │
│  [임베딩 파이프라인]                                    │
│    ├─ KURE-v1 모델 (768차원)                           │
│    ├─ 배치 처리 (32개/배치)                            │
│    └─ RunPod GPU 지원 (원격 API)                       │
│                                                         │
│  [데이터베이스]                                         │
│    ├─ PostgreSQL + pgvector                            │
│    ├─ documents 테이블 (메타데이터)                    │
│    ├─ chunks 테이블 (청크 + 임베딩)                    │
│    └─ chunk_relations 테이블 (청크 간 관계)            │
│                                                         │
│  [검색 시스템]                                          │
│    ├─ 벡터 검색 (코사인 유사도)                        │
│    ├─ 키워드 검색 (전문 검색)                          │
│    ├─ 하이브리드 검색 (벡터 + 키워드)                  │
│    ├─ 멀티 소스 검색 (데이터 유형별 가중치)            │
│    └─ 컨텍스트 확장 (주변 청크 포함)                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 주요 개선 사항

1. **통합 스키마**: 3가지 데이터 유형을 하나의 스키마로 통합
2. **청크 타입 세분화**: 법령(article), 상담(question/answer), 분쟁조정(overview/claim/decision)
3. **청크 간 관계**: next/prev 관계를 명시적으로 관리
4. **다양한 검색 전략**: 벡터, 키워드, 하이브리드, 멀티 소스 검색 지원
5. **컨텍스트 확장**: 검색된 청크의 주변 청크를 자동으로 포함

---

## 🛠 사전 준비

### 1. 환경 변수 설정

`.env` 파일을 프로젝트 루트에 생성하고 다음 내용을 입력하세요:

```bash
# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres

# 임베딩 API 설정 (RunPod 또는 로컬)
EMBED_API_URL=http://localhost:8001/embed

# OpenAI API (LLM 답변 생성용, 선택 사항)
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Python 패키지 설치

```bash
cd backend
pip install -r requirements.txt
```

**주요 패키지**:
- `psycopg2-binary`: PostgreSQL 연결
- `python-dotenv`: 환경 변수 관리
- `requests`: HTTP 요청 (임베딩 API)
- `tqdm`: 진행 상황 표시

### 3. Docker Compose 실행

PostgreSQL 데이터베이스를 Docker로 실행:

```bash
cd /path/to/ddoksori_demo
docker-compose up -d
```

데이터베이스 연결 확인:

```bash
docker exec -it ddoksori_db psql -U postgres -d ddoksori -c "SELECT version();"
```

---

## 🗄 데이터베이스 설정

### 1. 스키마 초기화

**자동 초기화** (임베딩 파이프라인 실행 시 자동으로 수행됨):
```bash
cd backend
python scripts/embed_pipeline_v2.py
```

**수동 초기화** (필요시):
```bash
docker exec -i ddoksori_db psql -U postgres -d ddoksori < database/schema_v2_final.sql
```

### 2. 스키마 구조 확인

```bash
docker exec -it ddoksori_db psql -U postgres -d ddoksori
```

```sql
-- 테이블 목록 확인
\dt

-- 테이블 구조 확인
\d documents
\d chunks
\d chunk_relations

-- 뷰 확인
\dv

-- 함수 확인
\df
```

---

## 🚀 임베딩 파이프라인 실행

### 방법 1: 로컬 실행 (임베딩 API 없이)

임베딩 없이 데이터만 삽입:

```bash
cd backend
python scripts/embed_pipeline_v2.py
```

**결과**: 문서와 청크가 데이터베이스에 삽입되지만, `embedding` 필드는 NULL로 남습니다.

### 방법 2: RunPod GPU 사용 (권장)

#### 2-1. RunPod 서버 실행

1. RunPod 인스턴스에 SSH 접속
2. 임베딩 서버 실행:

```bash
# RunPod 인스턴스에서
cd /workspace
pip install fastapi uvicorn sentence-transformers torch

# 서버 코드 업로드 (로컬에서)
scp backend/runpod_embed_server.py [user]@[runpod_ip]:/workspace/

# 서버 실행 (RunPod에서)
uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
```

#### 2-2. SSH 터널 연결

로컬 PC에서 새 터미널 열고:

```bash
ssh -L 8001:localhost:8000 [user]@[runpod_ip] -p [port]
```

#### 2-3. 임베딩 파이프라인 실행

로컬 PC에서:

```bash
cd backend
export EMBED_API_URL=http://localhost:8001/embed
python scripts/embed_pipeline_v2.py
```

### 실행 과정

```
============================================================
똑소리 프로젝트 - 임베딩 파이프라인 v2
============================================================

[1/6] 임베딩 API 연결 테스트: http://localhost:8001/embed
✅ API 연결 성공: {'message': 'Embedding server is running', 'device': 'cuda'}

[2/6] PostgreSQL 연결 중...
✅ 데이터베이스 연결 성공

[3/6] 데이터베이스 스키마 초기화: .../schema_v2_final.sql
✅ 스키마 초기화 완료

[4/6] 법령 데이터 처리 중...
   발견된 법령 파일: 13개
✅ 법령 데이터 처리 완료: 문서 13개, 청크 5455개

[4/6] 피해구제사례 데이터 처리 중...
   발견된 상담사례 파일: 3개
✅ 피해구제사례 처리 완료: 문서 6772개, 청크 13544개

[4/6] 분쟁조정사례 데이터 처리 중...
   발견된 분쟁조정사례 파일: 4개
✅ 분쟁조정사례 처리 완료: 문서 3918개, 청크 11755개

[5/6] 문서 메타데이터 삽입 중: 10703개
✅ 문서 메타데이터 삽입 완료

[6/6] 청크 임베딩 및 삽입 중: 30754개
임베딩 배치 처리: 100%|██████████| 962/962 [15:23<00:00]
✅ 청크 임베딩 및 삽입 완료

[추가] 청크 간 관계 생성 중...
✅ 청크 간 관계 생성 완료

============================================================
데이터 통계
============================================================
데이터 유형         출처        문서 수    청크 수    평균 길이    임베딩 완료
------------------------------------------------------------
law             statute         13      5455       450.2       5455
counsel_case    KCA           6772     13544       320.5      13544
mediation_case  KCA           2500      7500       380.1       7500
mediation_case  ECMC           800      2400       370.8       2400
mediation_case  KCDRC          618      1855       365.3       1855
============================================================

✅ 모든 작업 완료!
```

---

## 🔍 RAG 검색 테스트

### 1. 기본 테스트

```bash
cd /home/maroco/LLM
python tests/integration/test_rag_v2.py
```

### 2. 테스트 모드 선택

```
============================================================
똑소리 프로젝트 - RAG 시스템 테스트 v2
============================================================

실행 모드를 선택하세요:
1. 전체 테스트 (6개 시나리오)
2. 빠른 테스트 (단일 쿼리)

선택 (1 또는 2): 
```

### 3. 전체 테스트 시나리오

#### 시나리오 1: 환불 관련 일반 문의
- **쿼리**: "온라인으로 구매한 제품이 불량이에요. 환불 받을 수 있나요?"
- **기대**: 상담사례 + 법령 정보

#### 시나리오 2: 법률 해석 질문
- **쿼리**: "소비자기본법에서 소비자의 권리는 무엇인가요?"
- **기대**: 법령 데이터 우선

#### 시나리오 3: 유사 사례 검색
- **쿼리**: "아파트 누수로 인한 손해배상 사례가 있나요?"
- **기대**: 분쟁조정사례 우선

#### 시나리오 4: 감가상각 계산 문의
- **쿼리**: "가전제품 감가상각은 어떻게 계산하나요?"
- **기대**: 상담사례 (구체적 계산 방법)

#### 시나리오 5: 전자상거래 관련 법령
- **쿼리**: "전자상거래에서 청약철회는 언제까지 가능한가요?"
- **기대**: 법령 + 상담사례

#### 시나리오 6: 분쟁조정 절차
- **쿼리**: "소비자분쟁조정위원회에 신청하려면 어떻게 해야 하나요?"
- **기대**: 상담사례 + 법령

### 4. 평가 지표

각 시나리오마다 다음 지표를 출력합니다:

- **커버리지**: 기대한 문서 유형이 검색 결과에 포함된 비율
- **다양성**: 검색 결과의 문서 유형 다양성
- **권장 검색 방법**: 해당 시나리오에 가장 적합한 검색 방법

---

## 🔧 트러블슈팅

### 문제 1: `psycopg2.OperationalError: could not connect to server`

**원인**: PostgreSQL 컨테이너가 실행되지 않음

**해결**:
```bash
docker-compose up -d
docker ps  # 컨테이너 상태 확인
```

### 문제 2: `requests.exceptions.ConnectionError: Connection refused`

**원인**: 임베딩 API 서버가 실행되지 않음

**해결**:
1. RunPod 서버에서 `uvicorn` 실행 확인
2. SSH 터널 연결 확인
3. 로컬에서 `curl http://localhost:8001/` 테스트

### 문제 3: `psycopg2.errors.UndefinedTable: relation "documents" does not exist`

**원인**: 데이터베이스 스키마가 초기화되지 않음

**해결**:
```bash
docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql
```

### 문제 4: 임베딩 속도가 너무 느림

**원인**: 배치 크기가 GPU에 비해 작음

**해결**: `embed_pipeline_v2.py`에서 `batch_size` 조정
```python
pipeline.embed_and_insert_chunks(all_chunks, batch_size=64)  # 기본 32 → 64
```

### 문제 5: `ERROR: extension "vector" does not exist`

**원인**: pgvector 확장이 설치되지 않음

**해결**:
```bash
docker exec -it ddoksori_db psql -U postgres -d ddoksori -c "CREATE EXTENSION vector;"
```

---

## 📊 데이터 통계 확인

### SQL 쿼리로 확인

```sql
-- 전체 통계
SELECT * FROM v_data_statistics;

-- 문서 수
SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type;

-- 청크 수
SELECT d.doc_type, COUNT(c.chunk_id) 
FROM chunks c 
JOIN documents d ON c.doc_id = d.doc_id 
GROUP BY d.doc_type;

-- 임베딩 완료율
SELECT 
    d.doc_type,
    COUNT(c.chunk_id) AS total_chunks,
    COUNT(c.embedding) AS embedded_chunks,
    ROUND(COUNT(c.embedding)::numeric / COUNT(c.chunk_id) * 100, 2) AS completion_rate
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
GROUP BY d.doc_type;
```

---

## 🎯 다음 단계

1. ✅ 데이터베이스 설정 완료
2. ✅ 임베딩 파이프라인 실행 완료
3. ✅ RAG 검색 테스트 완료
4. ⏭️ **PR #4**: 멀티 에이전트 시스템 구현
5. ⏭️ **PR #5**: LLM 통합 및 답변 생성
6. ⏭️ **PR #6**: 평가 시스템 구축

---

## 📚 참고 문서

- [RAG 개선 제안서](../rag_improvement_proposal.md)
- [데이터 분석 보고서](../data_analysis_report.md)
- [RunPod GPU 활용 가이드](../runpod_comprehensive_guide.md)
- [프로젝트 계획서](../mas_chatbot_project_plan.md)

---

**작성자**: RAG 시스템 전문가  
**최종 수정**: 2026-01-05
