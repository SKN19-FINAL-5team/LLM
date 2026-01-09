# RAG CLI 사용 가이드

**작성일**: 2026-01-09  
**목적**: LLM 통합 RAG CLI 시스템 사용 방법 및 예시

---

## 📋 목차

1. [개요](#개요)
2. [사전 준비](#사전-준비)
3. [기본 사용법](#기본-사용법)
4. [고급 사용법](#고급-사용법)
5. [Golden Set 사용](#golden-set-사용)
6. [검색 방법 선택](#검색-방법-선택)
7. [트러블슈팅](#트러블슈팅)
8. [참고 문서](#참고-문서)

---

## 개요

RAG CLI는 여러 검색 방법(cosine similarity, BM25, SPLADE, hybrid search)을 통합하여 실행하고, LLM(GPT-4o-mini)이 결과를 비교 분석하여 최종 답변을 생성하는 CLI 도구입니다.

### 주요 기능

- **다중 검색 방법 통합**: cosine, BM25, SPLADE, hybrid search를 한 번에 실행
- **LLM 비교 분석**: 각 검색 방법의 결과를 LLM이 비교 분석하여 최종 답변 생성
- **Golden Set 지원**: 미리 정의된 테스트 쿼리 세트에서 선택하여 실행
- **유연한 옵션**: 검색 방법 선택, Top-K 조정 등 다양한 옵션 제공

### 시스템 아키텍처

```
사용자 질문 (CLI)
    ↓
MultiMethodRetriever
    ├─ Cosine Similarity 검색
    ├─ BM25 검색
    ├─ SPLADE 검색
    └─ Hybrid Search 검색
    ↓
각 검색 방법별 결과 수집
    ↓
RAGGenerator.generate_comparative_answer()
    ├─ 각 검색 방법의 결과를 구조화
    ├─ LLM에 비교 분석 프롬프트 전달
    └─ 최종 답변 생성
    ↓
CLI에 텍스트 출력
```

---

## 사전 준비

### 1. 환경 변수 설정

`.env` 파일에 OpenAI API 키가 설정되어 있어야 합니다:

```bash
# backend/.env 파일 확인
cd /home/maroco/LLM/backend
cat .env | grep OPENAI_API_KEY
```

**필수 설정**:
```env
OPENAI_API_KEY=your_openai_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres
```

### 2. Conda 환경 활성화

```bash
conda activate dsr
```

### 3. 데이터베이스 확인

PostgreSQL 데이터베이스가 실행 중이어야 합니다:

```bash
# Docker 컨테이너 확인
docker ps | grep ddoksori_db

# 데이터베이스 연결 테스트
psql -h localhost -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks;"
```

---

## 기본 사용법

### 방법 1: 직접 질문 입력

```bash
cd /home/maroco/LLM/backend
conda activate dsr
python scripts/cli/rag_cli.py --query "냉장고를 구매한 지 1개월이 지났는데 냉동실이 작동하지 않습니다. 무상 수리가 가능한가요?"
```

**출력 예시**:
```
================================================================================
질문: 냉장고를 구매한 지 1개월이 지났는데 냉동실이 작동하지 않습니다. 무상 수리가 가능한가요?
================================================================================

🔧 검색 시스템 초기화 중...
✅ BM25 Retriever 초기화 완료
✅ SPLADE Retriever 초기화 완료

🔍 검색 실행 중... (top_k=10)

검색 결과 요약:
  ✅ COSINE: 10개 결과 (0.234초)
  ✅ BM25: 8개 결과 (0.156초)
  ✅ SPLADE: 7개 결과 (0.312초)
  ✅ HYBRID: 10개 결과 (0.445초)

🤖 LLM 답변 생성 중...

================================================================================
답변
================================================================================
[검색 방법별 요약]
- COSINE: 10개 결과 (0.234초)
- BM25: 8개 결과 (0.156초)
- SPLADE: 7개 결과 (0.312초)
- HYBRID: 10개 결과 (0.445초)

[종합 답변]
각 검색 방법에서 찾은 결과를 종합하면, 냉장고 구매 후 1개월 이내에 냉동실이 작동하지 않는 경우 무상 수리가 가능합니다.

COSINE 검색에서 찾은 기준에 따르면, 가전제품의 품질보증기간은 일반적으로 1년이며, 이 기간 내 발생한 하자는 무상 수리 대상입니다. BM25 검색에서도 유사한 기준을 확인할 수 있었습니다.

HYBRID 검색 결과에서 실제 분쟁조정 사례를 확인한 결과, 구매 후 1개월 이내 발생한 하자에 대해서는 무상 수리가 인정된 사례가 다수 있습니다.

[참고 출처]
- 검색 방법: COSINE, BM25, HYBRID
- 사건번호: KCA-2024-001234
- 기준: 가전제품 품질보증 기준 제3조

--------------------------------------------------------------------------------
메타데이터
--------------------------------------------------------------------------------
모델: gpt-4o-mini
사용된 검색 방법: cosine, bm25, splade, hybrid
총 검색 결과 수: 35개
토큰 사용량:
  - 프롬프트: 2,345
  - 완성: 456
  - 총합: 2,801
================================================================================
```

### 방법 2: 대화형 모드

질문을 직접 입력하지 않으면 대화형 모드로 전환됩니다:

```bash
python scripts/cli/rag_cli.py
```

```
RAG CLI - 질문을 입력하세요 (종료: Ctrl+C 또는 'quit')
--------------------------------------------------------------------------------

질문: 온라인 쇼핑몰에서 환불을 거부당했습니다.
```

---

## 고급 사용법

### Top-K 조정

각 검색 방법별로 반환할 최대 결과 수를 조정할 수 있습니다:

```bash
# Top-K를 5로 설정 (기본값: 10)
python scripts/cli/rag_cli.py --query "질문" --top-k 5
```

### LLM 모델 변경

다른 LLM 모델을 사용할 수 있습니다 (OpenAI API 지원 모델):

```bash
# GPT-4 사용
python scripts/cli/rag_cli.py --query "질문" --model gpt-4

# GPT-3.5-turbo 사용
python scripts/cli/rag_cli.py --query "질문" --model gpt-3.5-turbo
```

---

## Golden Set 사용

### Golden Set에서 쿼리 선택

미리 정의된 테스트 쿼리 세트에서 선택하여 실행할 수 있습니다:

```bash
python scripts/cli/rag_cli.py --golden-set
```

**출력 예시**:
```
================================================================================
Golden Set 쿼리 목록
================================================================================

[1] Q001
    질문: 냉장고를 구매한 지 1개월이 지났는데 냉동실이 작동하지 않습니다. 무상 수리가 가능한가요?
    유형: product_specific, 난이도: easy

[2] Q002
    질문: 온라인으로 구매한 화장품이 알레르기를 유발했습니다. 환불 가능한가요?
    유형: practical, 난이도: easy

[3] Q003
    질문: 민법 제750조의 내용을 알려주세요.
    유형: legal, 난이도: easy

...

================================================================================
총 30개 쿼리
================================================================================

쿼리를 선택하세요:
  - 번호 입력: 해당 쿼리 선택
  - 'all' 입력: 모든 쿼리 반환 (배치 모드)
  - 'q' 또는 'quit' 입력: 취소

선택: 1
```

### 배치 모드 (모든 쿼리 실행)

Golden Set의 모든 쿼리를 순차적으로 실행할 수 있습니다:

```bash
python scripts/cli/rag_cli.py --golden-set
# 선택 프롬프트에서 'all' 입력
```

### 커스텀 Golden Set 경로

다른 Golden Set 파일을 사용할 수 있습니다:

```bash
python scripts/cli/rag_cli.py --golden-set --golden-set-path /path/to/custom_golden_set.json
```

---

## 검색 방법 선택

특정 검색 방법만 실행할 수 있습니다:

### Cosine Similarity만 사용

```bash
python scripts/cli/rag_cli.py --query "질문" --methods cosine
```

### Cosine과 Hybrid만 사용

```bash
python scripts/cli/rag_cli.py --query "질문" --methods cosine hybrid
```

### 사용 가능한 검색 방법

- `cosine`: Cosine Similarity (벡터 유사도 검색)
- `bm25`: BM25 (키워드 기반 검색)
- `splade`: SPLADE (Sparse Lexical and Expansion 검색)
- `hybrid`: Hybrid Search (질문 유형별 전문 검색기 조합)

**참고**: BM25와 SPLADE는 선택적 기능입니다. 초기화에 실패하면 해당 방법은 건너뜁니다.

---

## 명령줄 옵션 전체 목록

```bash
python scripts/cli/rag_cli.py --help
```

**주요 옵션**:

| 옵션 | 단축 | 설명 | 기본값 |
|------|------|------|--------|
| `--query` | `-q` | 사용자 질문 (직접 입력) | - |
| `--golden-set` | `-g` | Golden set에서 쿼리 선택 | False |
| `--top-k` | `-k` | 각 검색 방법별 최대 결과 수 | 10 |
| `--methods` | `-m` | 실행할 검색 방법 선택 | 모두 실행 |
| `--model` | - | 사용할 LLM 모델 | gpt-4o-mini |
| `--golden-set-path` | - | Golden set JSON 파일 경로 | 기본 경로 |

---

## 트러블슈팅

### 문제 1: OPENAI_API_KEY 오류

**증상**:
```
❌ OPENAI_API_KEY가 설정되지 않았습니다.
   .env 파일에 실제 API 키를 입력하세요.
```

**해결 방법**:
1. `backend/.env` 파일 확인
2. `OPENAI_API_KEY=your_openai_api_key_here` 부분을 실제 API 키로 교체

### 문제 2: 데이터베이스 연결 실패

**증상**:
```
❌ 데이터베이스 연결 실패: ...
```

**해결 방법**:
1. PostgreSQL 컨테이너 실행 확인:
   ```bash
   docker ps | grep ddoksori_db
   ```
2. 컨테이너가 실행 중이 아니면 시작:
   ```bash
   docker-compose up -d db
   ```
3. `.env` 파일의 DB 설정 확인

### 문제 3: BM25/SPLADE 초기화 실패

**증상**:
```
⚠️  BM25 Retriever 초기화 실패: ...
⚠️  SPLADE Retriever 초기화 실패: ...
```

**해결 방법**:
- BM25와 SPLADE는 선택적 기능입니다. 초기화에 실패해도 cosine과 hybrid 검색은 정상 작동합니다.
- 필요한 경우 해당 모듈의 의존성을 설치하거나 설정을 확인하세요.

### 문제 4: Golden Set 파일을 찾을 수 없음

**증상**:
```
❌ Golden set 파일을 찾을 수 없습니다: ...
```

**해결 방법**:
1. 기본 경로 확인: `backend/evaluation/datasets/gold_real_consumer_cases.json`
2. 파일이 없으면 `--golden-set-path` 옵션으로 다른 경로 지정
3. 또는 직접 `--query` 옵션으로 질문 입력

### 문제 5: 검색 결과가 없음

**증상**:
```
검색 결과 요약:
  ✅ COSINE: 0개 결과
  ✅ BM25: 0개 결과
  ...
```

**해결 방법**:
1. 데이터베이스에 데이터가 있는지 확인:
   ```bash
   psql -h localhost -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks;"
   ```
2. 임베딩이 생성되었는지 확인:
   ```bash
   psql -h localhost -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;"
   ```
3. 데이터가 없으면 임베딩 프로세스를 실행하세요.

---

## 사용 예시

### 예시 1: 법령 조문 질문

```bash
python scripts/cli/rag_cli.py --query "민법 제750조의 내용을 알려주세요." --methods cosine hybrid
```

### 예시 2: 제품별 기준 질문

```bash
python scripts/cli/rag_cli.py --query "냉장고 품질보증 기준은 무엇인가요?" --top-k 5
```

### 예시 3: 분쟁 사례 질문

```bash
python scripts/cli/rag_cli.py --query "온라인 쇼핑몰 환불 거부 사례" --methods cosine bm25 hybrid
```

### 예시 4: Golden Set에서 선택

```bash
python scripts/cli/rag_cli.py --golden-set
# 프롬프트에서 원하는 번호 입력
```

---

## 참고 문서

- [RAG 아키텍처 가이드](../guides/rag_architecture_expert_view.md)
- [임베딩 프로세스 가이드](../guides/embedding_process_guide.md)
- [Vector DB 관리 가이드](../guides/Vector_DB_관리_가이드.md)
- [하이브리드 검색 가이드](../backend/rag/HYBRID_SEARCH_GUIDE.md)

---

## 구현 파일 위치

- **CLI 스크립트**: `backend/scripts/cli/rag_cli.py`
- **MultiMethodRetriever**: `backend/app/rag/multi_method_retriever.py`
- **RAGGenerator**: `backend/app/rag/generator.py`
- **Golden Set Loader**: `backend/scripts/cli/golden_set_loader.py`
- **Golden Set 데이터**: `backend/evaluation/datasets/gold_real_consumer_cases.json`

---

**작성자**: AI Assistant  
**최종 수정일**: 2026-01-09
