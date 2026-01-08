# PR #3: RAG 시스템 구축

## 개요

이 PR에서는 Vector DB 검색 기능과 LLM 답변 생성 기능을 구현하여 완전한 RAG (Retrieval-Augmented Generation) 시스템을 구축합니다.

## 변경 사항

### 1. RAG 모듈 구현

#### `backend/app/rag/retriever.py`
Vector DB에서 유사한 청크를 검색하는 모듈입니다.

**주요 기능:**
- `search()`: 코사인 유사도 기반 벡터 검색
- `get_case_chunks()`: 특정 사례의 모든 청크 조회
- 청크 타입 및 기관별 필터링 지원

#### `backend/app/rag/generator.py`
검색된 청크를 바탕으로 LLM 답변을 생성하는 모듈입니다.

**주요 기능:**
- `generate_answer()`: OpenAI GPT 모델을 사용한 답변 생성
- `generate_answer_stream()`: 스트리밍 방식 답변 생성
- 참고 자료 포맷팅 및 프롬프트 엔지니어링

### 2. FastAPI 엔드포인트

#### `backend/app/main.py`

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/` | GET | API 서버 정보 |
| `/health` | GET | 서버 및 DB 상태 확인 |
| `/search` | POST | Vector DB 검색 (LLM 없이 검색만) |
| `/chat` | POST | RAG 기반 챗봇 응답 생성 |
| `/chat/stream` | POST | 스트리밍 방식 챗봇 응답 |
| `/case/{case_uid}` | GET | 특정 사례 전체 조회 |

### 3. 테스트 스크립트

#### `test/integration/test_rag.py`
RAG 시스템의 핵심 기능을 직접 테스트합니다.

- `test_retriever()`: Vector DB 검색 기능 테스트 (API 키 불필요)
- `test_generator()`: LLM 답변 생성 기능 테스트 (API 키 필요)
- `test_full_pipeline()`: 전체 RAG 파이프라인 테스트 (API 키 필요)

#### `test/unit/test_api.py`
FastAPI 서버가 실행 중일 때 HTTP API를 테스트합니다.

- `test_health()`: 헬스 체크
- `test_search()`: 검색 API 테스트
- `test_chat()`: 챗봇 API 테스트 (API 키 필요)

## 설치 및 실행

### 1. 리포지토리 클론 및 브랜치 전환

```bash
git clone https://github.com/Maroco0109/ddoksori_demo.git
cd ddoksori_demo
git checkout feature/pr3-rag-system
```

### 2. 환경 변수 설정

```bash
cd backend
cp .env.example .env
```

`.env` 파일을 열어서 **OpenAI API 키**를 추가합니다:

```env
# 기존 설정은 그대로 유지
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres

# 임베딩 모델 설정
EMBEDDING_MODEL=nlpai-lab/KURE-v1
EMBEDDING_DIMENSION=1024

# ⭐ OpenAI API 키 추가 (필수)
OPENAI_API_KEY=your_openai_api_key_here
```

> **중요:** OpenAI API 키가 없으면 검색 기능만 사용할 수 있고, LLM 답변 생성은 불가능합니다.

### 3. Python 패키지 설치

```bash
# 가상환경 활성화 (Miniconda 사용 시)
conda activate your_env_name

# 패키지 설치
pip install -r requirements.txt
```

**새로 추가된 패키지:**
- `openai==1.58.1`: OpenAI API 클라이언트

### 4. PostgreSQL 및 데이터 준비

PR #2에서 이미 데이터를 임베딩했다면 이 단계는 건너뛰세요.

```bash
# PostgreSQL 실행
cd ..
docker-compose up -d db

# 데이터 임베딩 (PR #2에서 완료했다면 생략)
cd backend
python scripts/embed_data.py
```

### 5. FastAPI 서버 실행

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

서버가 정상적으로 실행되면 다음 URL에서 API 문서를 확인할 수 있습니다:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 테스트 방법

### 방법 1: Python 테스트 스크립트 실행

#### 검색 기능만 테스트 (API 키 불필요)

```bash
cd backend
python tests/test_rag.py
```

이 스크립트는 다음을 테스트합니다:
1. Vector DB 검색 기능 (API 키 불필요)
2. LLM 답변 생성 기능 (API 키 필요 - 없으면 건너뜀)
3. 전체 RAG 파이프라인 (API 키 필요 - 없으면 건너뜀)

#### API 엔드포인트 테스트 (서버 실행 필요)

먼저 서버를 실행한 후, 새 터미널에서:

```bash
cd backend
python tests/test_api.py
```

### 방법 2: cURL로 API 테스트

#### 헬스 체크

```bash
curl http://localhost:8000/health
```

#### 검색 API (API 키 불필요)

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "에어컨 설치 불량으로 누수가 발생했습니다.",
    "top_k": 3
  }'
```

#### 챗봇 API (API 키 필요)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "휴대폰 액정이 자연 파손되었는데 무상 수리가 가능한가요?",
    "top_k": 5
  }'
```

### 방법 3: Swagger UI로 테스트

1. 브라우저에서 http://localhost:8000/docs 접속
2. 각 엔드포인트를 클릭하여 "Try it out" 버튼 클릭
3. 파라미터 입력 후 "Execute" 버튼 클릭

## 예상 결과

### 검색 API 응답 예시

```json
{
  "query": "에어컨 설치 불량으로 누수가 발생했습니다.",
  "results_count": 3,
  "results": [
    {
      "chunk_uid": "kca_merged:123_decision",
      "case_uid": "kca_merged:123",
      "chunk_type": "decision",
      "text": "피신청인은 신청인에게...",
      "case_no": "2021일가456",
      "decision_date": "2021.06.15",
      "agency": "kca",
      "similarity": 0.8542
    }
  ]
}
```

### 챗봇 API 응답 예시

```json
{
  "answer": "네, 에어컨 설치 불량으로 인한 누수 피해는 배상받으실 수 있습니다. 관련 사례(사건번호 2021일가456)에 따르면...",
  "chunks_used": 5,
  "model": "gpt-4o-mini",
  "sources": [
    {
      "case_no": "2021일가456",
      "agency": "kca",
      "decision_date": "2021.06.15",
      "chunk_type": "decision",
      "similarity": 0.8542
    }
  ]
}
```

## 기술 스택

- **Vector DB**: PostgreSQL 16 + pgvector (코사인 유사도 검색)
- **임베딩 모델**: KURE-v1 (nlpai-lab/KURE-v1, 1024차원)
- **LLM**: OpenAI GPT-4o-mini
- **웹 프레임워크**: FastAPI
- **Python 라이브러리**:
  - `sentence-transformers`: 임베딩 생성
  - `openai`: OpenAI API 클라이언트
  - `psycopg2-binary`: PostgreSQL 연결
  - `pgvector`: pgvector 확장 지원

## 다음 단계 (PR #4)

PR #4에서는 멀티 에이전트 시스템을 구축하여 더 복잡한 질의 처리 및 대화 관리 기능을 추가합니다.

## 문제 해결

### OpenAI API 키 오류

```
Error: The api_key client option must be set
```

**해결 방법:** `.env` 파일에 유효한 OpenAI API 키를 설정하세요.

### 검색 결과가 없음

```
죄송합니다. 관련된 분쟁조정 사례를 찾을 수 없습니다.
```

**원인:** 
1. 데이터가 DB에 임베딩되지 않았습니다.
2. 질문이 너무 추상적이거나 데이터와 관련이 없습니다.

**해결 방법:**
1. `python scripts/embed_data.py`를 실행하여 데이터를 임베딩하세요.
2. 더 구체적인 질문을 시도해보세요.

### GPU 사용 안 됨

**확인 방법:**
```python
import torch
print(torch.cuda.is_available())  # True여야 함
```

**해결 방법:** PR #2 설정 가이드의 GPU 설정 부분을 참고하세요.
