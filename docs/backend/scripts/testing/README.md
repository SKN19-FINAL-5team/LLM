# 멀티 스테이지 RAG 테스트

## 📋 테스트 스크립트

### test_multi_stage_rag.py

멀티 스테이지 RAG 시스템을 4가지 테스트 케이스로 검증합니다.

**테스트 케이스:**
1. 전자제품 환불 (노트북 불량)
2. 온라인 거래 분쟁 (배송 지연)
3. 서비스 환불 (학원 수강료)
4. 콘텐츠 분쟁 (음원 저작권)

## 🚀 실행 방법

### 1. 환경 준비

```bash
# Conda 환경 활성화
conda activate ddoksori

# 프로젝트 디렉토리로 이동
cd /home/maroco/ddoksori_demo/backend
```

### 2. 환경 변수 설정

`.env` 파일에 다음 설정이 있는지 확인:

```bash
# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=your_password

# 임베딩 모델
EMBEDDING_MODEL=nlpai-lab/KURE-v1

# OpenAI API (답변 생성용)
OPENAI_API_KEY=your_api_key
```

### 3. 테스트 실행

```bash
# 멀티 스테이지 RAG 테스트 실행
python test/rag/test_multi_stage_rag.py
```

**출력 내용:**
- 각 테스트 케이스별 검색 결과
- Stage별 청크 수 및 유사도
- 기관 추천 결과
- 평가 지표 (정확도, 성능)
- `test_results.json` 파일 저장

### 4. 결과 분석

```bash
# 테스트 결과 분석 (test_results.json 필요)
python scripts/analytics/analyze_rag_results.py
```

**출력 내용:**
- 검색 결과 분포 분석
- 유사도 통계
- 기관 추천 정확도
- 성능 분석
- 개선 제안

## 📊 예상 결과

### 성공적인 실행 예시

```
================================================================================
  🚀 멀티 스테이지 RAG 시스템 테스트 시작
================================================================================

📌 테스트 설정:
  - DB Host: localhost
  - DB Name: ddoksori
  - 테스트 케이스 수: 4개
✅ 검색기 초기화 완료

================================================================================
  테스트 1: 전자제품 환불 (노트북 불량)
================================================================================

**질문:** 온라인에서 노트북을 구매했는데 3일 만에 화면이 안 켜집니다. 환불 받을 수 있나요?
...

[Stage 1] 법령 및 분쟁조정기준 검색 중...
  - 법령: 3건
  - 기준: 3건

[Stage 2] 분쟁조정사례 검색 중...
  - 분쟁조정사례: 5건

[Agency Recommendation] 기관 추천 중...
  - 추천 기관: 한국전자거래분쟁조정위원회 (점수: 0.85)

📊 평가 결과
────────────────────────────────────────────────────────────────────────────────

✅ 검색 결과 요약:
  - 총 청크 수: 11개
  - 분쟁조정사례: 5개
  - Fallback 사용: 아니오

✅ 유사도 분석:
  - 평균 유사도: 0.742

✅ 기관 추천:
  - 추천 기관: ecmc (✓ 정확)
  - 추천 점수: 0.850
```

## 🔧 문제 해결

### 오류: "ModuleNotFoundError: No module named 'app'"

**원인:** Python 경로 설정 문제

**해결:**
```bash
# backend 디렉토리에서 실행하는지 확인
cd /home/maroco/ddoksori_demo/backend
python test/rag/test_multi_stage_rag.py
```

### 오류: "psycopg2.OperationalError: could not connect to server"

**원인:** PostgreSQL 데이터베이스 연결 실패

**해결:**
1. PostgreSQL이 실행 중인지 확인
2. `.env` 파일의 DB 설정 확인
3. DB에 데이터가 로드되었는지 확인

### 오류: "No chunks found"

**원인:** 데이터베이스에 임베딩 데이터가 없음

**해결:**
```bash
# 데이터 임베딩 실행 (먼저 데이터 적재 필요)
python scripts/embedding/embed_data_remote.py
```

### 경고: "Fallback 발동"

**원인:** 분쟁조정사례가 부족함 (정상 동작)

**설명:** 
- Stage 3 Fallback은 분쟁조정사례가 2개 미만일 때 자동으로 피해구제사례를 검색합니다
- 이는 시스템의 정상적인 동작입니다

## 📈 평가 지표

### 1. 검색 결과 수
- 법령: 평균 2-3개
- 기준: 평균 2-3개
- 분쟁조정사례: 평균 3-5개
- **총 청크: 평균 8-12개**

### 2. 유사도
- 평균 유사도: **0.6-0.8** (목표)
- 최소 허용: 0.5

### 3. 기관 추천 정확도
- 목표: **75% 이상**
- 우수: 100%

### 4. 성능
- 평균 검색 시간: **2-3초** (목표)
- 최대 허용: 5초

## 📝 결과 파일

### test_results.json

각 테스트 케이스의 평가 결과를 JSON 형식으로 저장:

```json
[
  {
    "test_id": 1,
    "test_name": "전자제품 환불 (노트북 불량)",
    "total_chunks": 11,
    "law_chunks": 3,
    "criteria_chunks": 3,
    "mediation_chunks": 5,
    "counsel_chunks": 0,
    "used_fallback": false,
    "recommended_agency": "ecmc",
    "agency_correct": true,
    "agency_score": 0.85,
    "avg_similarity": 0.742,
    "max_similarity": 0.891,
    "min_similarity": 0.623,
    "elapsed_time": 2.34,
    "timestamp": "2026-01-06T..."
  },
  ...
]
```

## 🔗 관련 문서

- [멀티 스테이지 RAG 사용 가이드](../../rag/docs/multi_stage_rag_usage.md)
- [RAG 모듈 README](../../app/rag/README.md)
