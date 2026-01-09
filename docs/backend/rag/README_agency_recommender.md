# 기관 추천 로직 (Agency Recommender)

## 개요

사용자의 질문과 검색 결과를 바탕으로 적절한 분쟁조정기관을 추천하는 하이브리드 시스템입니다.

### 지원 기관

1. **한국소비자원 (KCA)** - 일반 소비자 분쟁 조정
2. **한국전자거래분쟁조정위원회 (ECMC)** - 전자상거래 및 통신판매 분쟁 조정  
3. **한국저작권위원회 (KCDRC)** - 저작권 및 콘텐츠 분쟁 조정

---

## 추천 알고리즘

### 하이브리드 접근법 (규칙 기반 70% + 통계 기반 30%)

```python
최종점수 = (규칙점수 × 0.7) + (통계점수 × 0.3)
```

#### 1. 규칙 기반 점수 (Rule-based Scoring)

사용자 질문의 키워드를 분석하여 각 기관에 대한 점수를 계산합니다.

**키워드 카테고리:**

- **ECMC**: 전자상거래, 온라인, 배송, 쿠팡, 네이버, G마켓 등
- **KCDRC**: 저작권, 콘텐츠, 음원, 웹툰, 넷플릭스, 멜론 등
- **KCA**: 전자제품, 가전, 의류, 가구, 학원, 렌탈 등

**점수 계산:**
```python
score = log(1 + match_count) / log(1 + total_keywords)
```

로그 스케일을 사용하여 과도한 키워드 매칭을 방지합니다.

#### 2. 통계 기반 점수 (Statistics-based Scoring)

벡터 검색 결과에서 각 기관이 나타나는 빈도와 유사도를 분석합니다.

**점수 계산:**
```python
score = Σ(rank_weight × similarity)
rank_weight = 1 / (rank + 1)  # 상위 결과에 높은 가중치
```

검색 결과가 없는 경우 규칙 기반 점수만 사용합니다.

---

## 사용법

### 기본 사용

```python
from app.rag.agency_recommender import AgencyRecommender

recommender = AgencyRecommender()

# 기관 추천
query = "쿠팡에서 산 노트북이 불량입니다"
recommendations = recommender.recommend(query, search_results, top_n=2)

for agency_code, score, info in recommendations:
    print(f"{info['name']}: {score:.4f}")
```

### 검색 결과와 함께 사용

```python
from app.rag.retriever import VectorRetriever
from app.rag.agency_recommender import AgencyRecommender

# 벡터 검색
retriever = VectorRetriever(db_config)
search_results = retriever.search(query, top_k=5)

# 기관 추천
recommender = AgencyRecommender()
recommendations = recommender.recommend(query, search_results, top_n=2)
```

### 상세 설명 생성

```python
explanation = recommender.explain_recommendation(query, search_results)

print("추천 기관:")
for rec in explanation['recommendations']:
    print(f"{rec['rank']}순위: {rec['agency_name']}")
    print(f"  점수: {rec['final_score']:.4f}")
    print(f"  설명: {rec['description']}")

print("\n검색 결과 분포:")
for agency, count in explanation['search_results_distribution'].items():
    print(f"  {agency}: {count}건")
```

### 사용자 친화적 텍스트 생성

```python
formatted_text = recommender.format_recommendation_text(query, search_results)
print(formatted_text)
```

**출력 예시:**
```
📌 추천 기관: 한국전자거래분쟁조정위원회
   전자상거래 및 통신판매 관련 분쟁 조정
   (추천 점수: 0.96)

📋 대안 기관: 한국소비자원
   일반 소비자 분쟁 조정 (전자제품, 의류, 식품, 가구 등)
   (추천 점수: 0.48)

📊 검색 결과 통계:
   - 한국전자거래분쟁조정위원회: 3건
   - 한국소비자원: 1건
```

---

## API 통합 예시

### FastAPI 엔드포인트

```python
from fastapi import APIRouter
from app.rag.retriever import VectorRetriever
from app.rag.agency_recommender import AgencyRecommender

router = APIRouter()

@router.post("/recommend-agency")
async def recommend_agency(query: str):
    """기관 추천 API"""
    # 검색 수행
    retriever = VectorRetriever(db_config)
    search_results = retriever.search(query, top_k=5)
    
    # 기관 추천
    recommender = AgencyRecommender()
    explanation = recommender.explain_recommendation(query, search_results)
    
    return {
        "query": query,
        "recommendations": explanation['recommendations'],
        "search_distribution": explanation['search_results_distribution']
    }
```

---

## 커스터마이징

### 가중치 조정

```python
# 규칙 기반 점수를 더 중시 (80:20)
recommender = AgencyRecommender(rule_weight=0.8, stat_weight=0.2)

# 통계 기반 점수를 더 중시 (50:50)
recommender = AgencyRecommender(rule_weight=0.5, stat_weight=0.5)
```

### 키워드 규칙 확장

```python
class CustomAgencyRecommender(AgencyRecommender):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 키워드 추가
        self.KEYWORD_RULES['ecmc'].extend([
            '직구', '해외직접구매', '배대지'
        ])
        
        self.KEYWORD_RULES['kcdrc'].extend([
            '애니메이션', '드라마', 'OTT'
        ])
```

---

## 성능 특성

### 장점

1. **빠른 응답 속도**: 키워드 매칭은 O(n), 통계 계산은 O(k) (k=검색 결과 수)
2. **설명 가능성**: 규칙과 통계 점수를 모두 제공하여 추천 근거 명확
3. **견고성**: 검색 결과가 없어도 규칙 기반으로 추천 가능
4. **확장성**: 새로운 기관이나 키워드 추가 용이

### 제한사항

1. 규칙 기반 키워드는 수동으로 관리 필요
2. 복잡한 다중 도메인 질문의 경우 정확도 저하 가능
3. 신규 기관 추가 시 키워드 규칙 재구성 필요

---

## 테스트

### 단위 테스트

```bash
conda run -n ddoksori python backend/scripts/test_agency_recommender.py
```

**테스트 커버리지:**
- 규칙 기반 점수 계산
- 통계 기반 점수 계산
- 결합 추천
- 설명 생성
- 텍스트 포맷팅
- 엣지 케이스 (검색 결과 없음, 키워드 매칭 없음 등)
- 실제 시나리오

### 통합 테스트 (실제 DB)

```bash
conda run -n ddoksori python backend/scripts/test_agency_with_real_data.py
```

---

## 향후 개선 방향

### 단기 (1-2주)

1. **기계학습 기반 분류기 추가**
   - 키워드 규칙의 한계 보완
   - 훈련 데이터: 기존 사례의 (질문, 기관) 쌍

2. **A/B 테스트 프레임워크**
   - 다양한 가중치 조합 실험
   - 사용자 피드백 수집

### 중기 (1-2개월)

1. **다중 기관 추천 지원**
   - 복잡한 질문에 대해 여러 기관 병렬 제안
   - 예: 온라인 + 저작권 문제

2. **컨텍스트 기반 추천**
   - 사용자 이력 고려
   - 이전 상담 내역 활용

### 장기 (3개월+)

1. **강화학습 기반 최적화**
   - 사용자 선택 피드백으로 가중치 자동 조정
   - 온라인 학습 지원

2. **다국어 지원**
   - 영어, 중국어 등 외국인 소비자 지원

---

## 참고 자료

- [기관 추천 로직 구현 코드](./agency_recommender.py)
- [테스트 스크립트](../../scripts/test_agency_recommender.py)
- [RAG 시스템 전체 계획](../../../.cursor/plans/rag_시스템_검토_및_테스트_d5ed84e3.plan.md)
