# 똑소리 프로젝트 문서 인덱스

**작성일**: 2026-01-07  
**버전**: v1.0  
**최종 업데이트**: 2026-01-07

---

## 문서 개요

본 인덱스는 똑소리 프로젝트의 모든 문서를 체계적으로 정리하여 빠른 접근을 지원합니다.

---

## 1. 프로젝트 개요

| 문서 | 설명 | 대상 독자 |
|------|------|-----------|
| [`README.md`](../README.md) | 프로젝트 전체 개요 및 시작 가이드 | 전체 |
| [`docs/ENV_SETUP.md`](./ENV_SETUP.md) | 환경 설정 가이드 | 개발자 |

---

## 2. PM 문서 (Product Management)

### 2.1 전략 및 계획

| 문서 | 작성일 | 주요 내용 |
|------|--------|-----------|
| [`프로젝트_진행_상황_분석.md`](./pm/프로젝트_진행_상황_분석.md) | 2026-01-07 | 현재 구현 상태, 데이터 통계, 기술 부채 |
| [`RAG_시스템_개선_로드맵.md`](./pm/RAG_시스템_개선_로드맵.md) | 2026-01-07 | 4개 Phase 개선 계획, ROI 분석 |
| [`긴급_조치_완료_보고서_2026-01-07.md`](./pm/긴급_조치_완료_보고서_2026-01-07.md) | 2026-01-07 | 법령/기준 데이터 추가, 메타데이터 키워드 추출 완료 |
| [`하이브리드_검색_테스트_보고서_2026-01-07.md`](./pm/하이브리드_검색_테스트_보고서_2026-01-07.md) | 2026-01-07 | 테스트 결과 (60% 성공률), 오류 수정, 개선 권고 |
| [`테스트_완료_요약_2026-01-07.md`](./pm/테스트_완료_요약_2026-01-07.md) | 2026-01-07 | Executive Summary: Law/Case Retriever 검색 실패 진단 |
| [`법률전문가_관점_평가_보고서_2026-01-07.md`](./pm/법률전문가_관점_평가_보고서_2026-01-07.md) | 2026-01-07 | Law/Case Retriever 개선, 30개 테스트 케이스, Agency Filter 문제 발견 |
| [`최종_평가_보고서_Agency_Filter_수정_후_2026-01-07.md`](./pm/최종_평가_보고서_Agency_Filter_수정_후_2026-01-07.md) | 2026-01-07 | Agency Filter 수정, 30개 테스트 완료, 성공률 33.3%, 개선 방향 제시 |
| [`Phase1_개선_완료_보고서_2026-01-07.md`](./pm/Phase1_개선_완료_보고서_2026-01-07.md) | 2026-01-07 | 가중치 재조정 완료, Law 34.6% (+19%), 전체 41.3% (+8%), Phase 2 계획 |
| [`전체_작업_완료_요약_2026-01-07.md`](./pm/전체_작업_완료_요약_2026-01-07.md) | 2026-01-07 | ⭐ 최종 요약: 계획서 100% 완료, 11개 파일, 5개 보고서, Phase 2 준비 |
| [`Phase2_Criteria_특화_개선_완료_보고서_2026-01-07.md`](./pm/Phase2_Criteria_특화_개선_완료_보고서_2026-01-07.md) | 2026-01-07 | ⭐⭐ Phase 2 완료: Criteria 0%→85.7%, Law 35%→54%, 전체 41%→54% |
| [`실행_가이드_2026-01-07.md`](./pm/실행_가이드_2026-01-07.md) | 2026-01-07 | 스크립트 실행 방법, 문제 해결, 임베딩 생성 가이드 |
| [`간단한_임베딩_실행_가이드.md`](./pm/간단한_임베딩_실행_가이드.md) | 2026-01-07 | 기존 방식으로 간단하게 임베딩 생성하는 방법 |
| [`요구사항_명확화_및_최종_계획.md`](./planning/요구사항_명확화_및_최종_계획.md) | - | 요구사항 정의 |

### 2.2 PR 계획

| 문서 | PR 번호 | 주요 기능 |
|------|---------|-----------|
| [`docs/setup/PR2_SETUP.md`](./setup/PR2_SETUP.md) | PR#2 | 데이터 수집 및 임베딩 |
| [`docs/setup/PR3_SETUP.md`](./setup/PR3_SETUP.md) | PR#3 | RAG 시스템 구축 |
| [`docs/planning/PR4_PLANNING.md`](./planning/PR4_PLANNING.md) | PR#4 | 멀티 에이전트 설계 |
| [`docs/setup/PR4_README.md`](./setup/PR4_README.md) | PR#4 | PR4 준비 상태 |

---

## 3. 기술 문서 (Technical)

### 3.1 아키텍처

| 문서 | 작성일 | 주요 내용 |
|------|--------|-----------|
| [`MAS_아키텍처_평가_보고서.md`](./technical/MAS_아키텍처_평가_보고서.md) | 2026-01-07 | README vs PR4 설계 비교, 권고사항 |
| [`MAS_구현_가이드.md`](./technical/MAS_구현_가이드.md) | 2026-01-07 | LangGraph 기반 MAS 구현 단계별 가이드 |
| [`rag_architecture_expert_view.md`](./guides/rag_architecture_expert_view.md) | - | RAG 아키텍처 전문가 관점 |

### 3.2 평가 보고서

| 문서 | 작성일 | 주요 내용 |
|------|--------|-----------|
| [`vector_db_스키마_평가_보고서.md`](./technical/vector_db_스키마_평가_보고서.md) | 2026-01-07 | 5가지 성능 테스트 결과, 인덱스 분석 |
| [`청킹_로직_평가_보고서.md`](./technical/청킹_로직_평가_보고서.md) | 2026-01-07 | 청크 품질 분석, 개선 권고사항 |
| [`SPLADE_적용_평가_보고서.md`](./technical/SPLADE_적용_평가_보고서.md) | 2026-01-07 | SPLADE 적용 평가, 보류 권고 |

### 3.3 데이터베이스

| 문서 | 작성일 | 주요 내용 |
|------|--------|-----------|
| [`backend/database/schema_v2_final.sql`](../backend/database/schema_v2_final.sql) | 2026-01-06 | 통합 스키마 v2 |
| [`backend/database/docs/데이터_변환_가이드.md`](../backend/database/docs/데이터_변환_가이드.md) | 2026-01-06 | 데이터 변환 프로세스 |
| [`backend/database/docs/스키마_설계_근거.md`](../backend/database/docs/스키마_설계_근거.md) | - | 스키마 설계 철학 |
| [`Vector_DB_관리_가이드.md`](./guides/Vector_DB_관리_가이드.md) | - | Vector DB 운영 가이드 |

---

## 4. 개발 가이드

### 4.1 백엔드

| 문서 | 주요 내용 |
|------|-----------|
| [`backend/app/rag/HYBRID_SEARCH_GUIDE.md`](../backend/app/rag/HYBRID_SEARCH_GUIDE.md) | 하이브리드 검색 사용 가이드 |
| [`backend/evaluation/README.md`](../backend/evaluation/README.md) | RAG 평가 시스템 가이드 |
| [`backend/evaluation/EVALUATION_GUIDE.md`](../backend/evaluation/EVALUATION_GUIDE.md) | 평가 상세 가이드 |
| [`backend/scripts/TEST_README.md`](../backend/scripts/TEST_README.md) | 스크립트 테스트 가이드 |

### 4.2 인프라

| 문서 | 주요 내용 |
|------|-----------|
| [`RunPod_remote_GPU.md`](./guides/RunPod_remote_GPU.md) | RunPod GPU 서버 설정 |
| [`docker_security_analysis.md`](./security/docker_security_analysis.md) | Docker 보안 분석 |
| [`SECURITY.md`](./security/SECURITY.md) | 보안 정책 |

---

## 5. 테스트

### 5.1 테스트 코드

| 파일 | 테스트 대상 |
|------|-------------|
| [`tests/unit/test_vector_db_schema.py`](../tests/unit/test_vector_db_schema.py) | Vector DB 스키마 성능 |
| [`tests/unit/test_chunking_quality.py`](../tests/unit/test_chunking_quality.py) | 청킹 품질 |
| [`tests/unit/test_api.py`](../tests/unit/test_api.py) | FastAPI 엔드포인트 |
| [`tests/integration/test_rag.py`](../tests/integration/test_rag.py) | RAG 파이프라인 |
| [`tests/integration/test_rag_v2.py`](../tests/integration/test_rag_v2.py) | RAG V2 파이프라인 |

### 5.2 테스트 데이터

| 파일 | 설명 |
|------|------|
| [`backend/evaluation/datasets/gold_v1.json`](../backend/evaluation/datasets/gold_v1.json) | 기본 Golden Dataset |
| [`backend/evaluation/datasets/gold_real_consumer_cases.json`](../backend/evaluation/datasets/gold_real_consumer_cases.json) | 실전 시나리오 30개 |

---

## 6. 구현 완료 보고서

| 문서 | 작성일 | 주요 내용 |
|------|--------|-----------|
| [`reports/RAG_하이브리드_검색_개선_구현_보고서.md`](./reports/RAG_하이브리드_검색_개선_구현_보고서.md) | 2026-01-07 | RAG 검색 시스템 개선 완료 보고 |
| [`reports/작업_완료_보고서_2026-01-07.md`](./reports/작업_완료_보고서_2026-01-07.md) | 2026-01-07 | 작업 완료 보고서 |
| [`reports/RAG_검색_시스템_진단_및_수정_보고서.md`](./reports/RAG_검색_시스템_진단_및_수정_보고서.md) | - | 문제 진단 및 수정 |

---

## 7. 문서 읽기 순서 추천

### 7.1 신규 개발자

1. [`README.md`](../README.md) - 프로젝트 전체 개요
2. [`docs/setup/ENV_SETUP.md`](./setup/ENV_SETUP.md) - 환경 설정
3. [`docs/setup/PR3_SETUP.md`](./setup/PR3_SETUP.md) - RAG 시스템 이해
4. [`MAS_구현_가이드.md`](./technical/MAS_구현_가이드.md) - MAS 구현 시작

### 7.2 Product Manager

1. [`프로젝트_진행_상황_분석.md`](./pm/프로젝트_진행_상황_분석.md) - 현재 상태
2. [`RAG_시스템_개선_로드맵.md`](./pm/RAG_시스템_개선_로드맵.md) - 개선 계획
3. [`MAS_아키텍처_평가_보고서.md`](./technical/MAS_아키텍처_평가_보고서.md) - 아키텍처 결정

### 7.3 QA/테스터

1. [`tests/README.md`](../tests/README.md) - 테스트 가이드
2. [`backend/evaluation/README.md`](../backend/evaluation/README.md) - 평가 시스템
3. [`vector_db_스키마_평가_보고서.md`](./technical/vector_db_스키마_평가_보고서.md) - 성능 벤치마크
4. [`청킹_로직_평가_보고서.md`](./technical/청킹_로직_평가_보고서.md) - 품질 평가

---

## 8. 문서 업데이트 이력

| 일자 | 업데이트 내용 | 작성자 |
|------|---------------|--------|
| 2026-01-07 | 초기 인덱스 생성, PM/기술 문서 추가 | PM |
| 2026-01-07 | 긴급 조치 완료 보고서 추가 (법령/기준 데이터, 메타데이터) | PM |
| 2026-01-08 | SPLADE PoC 완료 보고서 추가 | PM |
| 2026-01-08 | SPLADE 최종 성능 비교 및 향후 개선 방향 검토 보고서 추가 | PM |
| - | - | - |

---

## 9. 문서 작성 가이드

### 9.1 문서 네이밍

- **PM 문서**: 한글 이름 (예: `프로젝트_진행_상황_분석.md`)
- **기술 문서**: 영문 또는 한글 (예: `MAS_구현_가이드.md`)
- **코드**: 영문 (예: `test_vector_db_schema.py`)

### 9.2 문서 위치

- **전략/계획**: `docs/pm/`
- **기술 문서**: `docs/technical/`
- **환경 설정**: `docs/`
- **구현 보고**: `backend/`

### 9.3 문서 템플릿

```markdown
# 문서 제목

**작성일**: YYYY-MM-DD  
**작성자**: 이름  
**문서 유형**: 유형  
**버전**: v1.0

---

## Executive Summary

...

## 주요 내용

...

---

**작성자**: 이름  
**최종 업데이트**: YYYY-MM-DD
```

---

**작성자**: Multi-Agent System Product Manager  
**최종 업데이트**: 2026-01-07
