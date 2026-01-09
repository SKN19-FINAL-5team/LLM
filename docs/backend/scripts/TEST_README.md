# RAG 시스템 테스트 스크립트 사용 가이드

## 📋 개요

이 문서는 RAG 시스템의 멀티 스테이지 검색 및 성능을 평가하기 위한 테스트 스크립트 사용법을 안내합니다.

## 🧪 test_multi_stage_rag.py

### 목적

4가지 실제 시나리오를 통해 RAG 시스템의 성능을 평가합니다:

1. **전자제품 환불** (노트북 불량) - 한국소비자원 관할
2. **온라인 거래 분쟁** (배송 지연) - 한국전자거래분쟁조정위원회 관할
3. **서비스 환불** (학원 수강료) - 한국소비자원 관할
4. **콘텐츠 분쟁** (음원 저작권) - 한국저작권위원회 관할

### 평가 지표

- ✅ **검색 정확도**: 유사도 점수 및 분포
- ✅ **검색 결과 수**: 단계별 검색된 청크 개수
- ✅ **기관 추천 정확도**: 올바른 기관 추천 여부
- ✅ **키워드 매칭률**: 예상 키워드와의 일치도
- ✅ **응답 시간**: 검색 시간, 답변 생성 시간, 전체 시간

### 사전 요구사항

1. 데이터베이스에 사례 데이터가 삽입되어 있어야 함
2. 임베딩이 생성되어 있어야 함
3. Conda 가상환경 `ddoksori` 활성화

### 사용법

#### 1. 모든 테스트 케이스 실행

```bash
# Conda 환경 활성화
conda activate ddoksori

# 스크립트 실행
python tests/rag/test_multi_stage_rag.py
```

#### 2. 특정 테스트 케이스만 실행

```bash
# TC001: 전자제품 환불 케이스
python tests/rag/test_multi_stage_rag.py --test-id TC001

# TC002: 온라인 거래 분쟁 케이스
python tests/rag/test_multi_stage_rag.py --test-id TC002

# TC003: 서비스 환불 케이스
python tests/rag/test_multi_stage_rag.py --test-id TC003

# TC004: 콘텐츠 분쟁 케이스
python tests/rag/test_multi_stage_rag.py --test-id TC004
```

#### 3. 결과를 저장하지 않고 실행

```bash
python tests/rag/test_multi_stage_rag.py --no-save
```

#### 4. 커스텀 출력 디렉토리 지정

```bash
python tests/rag/test_multi_stage_rag.py --output-dir ./my_results
```

### 출력 결과

#### 콘솔 출력

스크립트는 실행 중 다음 정보를 출력합니다:

1. **시스템 상태**: 청크 수, 임베딩 상태, 기관별 사례 수
2. **각 테스트 케이스**:
   - 검색 결과 수 및 유사도 통계
   - 기관별/청크 타입별 분포
   - 상위 3개 결과 미리보기
   - 기관 추천 결과 및 일치 여부
   - LLM 답변 미리보기
3. **요약 보고서**:
   - 전체 통계 (성공/실패 수)
   - 기관 추천 정확도
   - 평균 메트릭 (검색 시간, 키워드 매칭률 등)
   - 개별 테스트 결과 요약

#### JSON 결과 파일

기본적으로 결과는 다음 위치에 저장됩니다:

```
backend/evaluation/results/rag_test_results_YYYYMMDD_HHMMSS.json
```

JSON 파일 구조:

```json
{
  "summary": {
    "timestamp": "2026-01-06T...",
    "total_tests": 4,
    "successful_tests": 4,
    "failed_tests": 0,
    "agency_accuracy": 75.0,
    "avg_metrics": {
      "search_time": 0.523,
      "answer_time": 2.145,
      "total_time": 2.668,
      "keyword_match_rate": 0.83,
      "avg_similarity": 0.7234
    }
  },
  "test_results": [
    {
      "test_case_id": "TC001",
      "test_case_name": "전자제품 환불 (노트북 불량)",
      "success": true,
      "recommended_agency": "kca",
      "agency_match": true,
      "keyword_match_rate": 0.85,
      "stages": {
        "full_search": {
          "chunks_count": 10,
          "agency_distribution": {...},
          "avg_similarity": 0.7456
        }
      },
      "answer": {
        "text": "...",
        "generation_time": 2.1
      },
      "metrics": {...}
    }
  ]
}
```

### 테스트 케이스 상세

#### TC001: 전자제품 환불 (노트북 불량)

- **시나리오**: 3개월 전 구매한 노트북이 반복적인 하자 발생
- **예상 기관**: 한국소비자원 (kca)
- **핵심 키워드**: 하자, 수리, 환불, 교환, 제품

#### TC002: 온라인 거래 분쟁 (배송 지연)

- **시나리오**: 온라인 쇼핑몰 구매 후 2주 배송 지연
- **예상 기관**: 한국전자거래분쟁조정위원회 (ecmc)
- **핵심 키워드**: 배송, 지연, 온라인, 전자거래, 환불

#### TC003: 서비스 환불 (학원 수강료)

- **시나리오**: 학원 1년 수강료 선납 후 3개월만에 환불 요청
- **예상 기관**: 한국소비자원 (kca)
- **핵심 키워드**: 학원, 환불, 수강료, 약관, 계약

#### TC004: 콘텐츠 분쟁 (음원 저작권)

- **시나리오**: 유튜브 배경음악 저작권 침해 분쟁
- **예상 기관**: 한국저작권위원회 (kcdrc)
- **핵심 키워드**: 저작권, 음원, 유튜브, 콘텐츠, 분쟁

### 문제 해결

#### 오류: "임베딩이 생성되지 않았습니다"

```bash
# 임베딩 생성 스크립트 실행
python backend/scripts/embedding/embed_data_remote.py
```

#### 오류: "데이터베이스 연결 실패"

`.env` 파일에서 데이터베이스 설정 확인:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres
```

#### 오류: "OpenAI API 키 없음"

`.env` 파일에 OpenAI API 키 추가:

```env
OPENAI_API_KEY=sk-...
```

### 향후 확장

현재 스크립트는 기본 검색 기능을 테스트합니다. 향후 다음 기능이 구현되면 자동으로 테스트됩니다:

- ✨ **멀티 스테이지 검색**: 법령 → 기준 → 사례 순차 검색
- ✨ **Fallback 메커니즘**: 분쟁조정사례 없으면 피해구제사례로 대체
- ✨ **고급 기관 추천**: 규칙 기반 + 검색 결과 통계 하이브리드

## 📊 결과 분석 팁

### 좋은 성능 지표

- ✅ 기관 추천 정확도: **75% 이상**
- ✅ 평균 유사도: **0.65 이상**
- ✅ 키워드 매칭률: **80% 이상**
- ✅ 검색 시간: **1초 이내**
- ✅ 전체 응답 시간: **5초 이내**

### 개선이 필요한 경우

- ⚠️ 기관 추천 정확도 50% 미만 → 청크 타입 필터링 개선 필요
- ⚠️ 평균 유사도 0.5 미만 → 임베딩 품질 또는 청킹 전략 검토
- ⚠️ 검색 시간 2초 이상 → 인덱스 최적화 필요

## 📞 문의

테스트 관련 문의 사항은 프로젝트 이슈 트래커에 등록해주세요.
