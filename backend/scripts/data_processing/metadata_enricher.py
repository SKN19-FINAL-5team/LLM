#!/usr/bin/env python3
"""
메타데이터 보강 모듈

청크의 content를 분석하여 다음을 추출:
1. 키워드 (빈도 기반)
2. 엔티티 (회사명, 제품명 등)
3. 법률 용어
4. 카테고리 태그
"""

import re
from typing import Dict, List, Set
from collections import Counter


class MetadataEnricher:
    """청크 메타데이터 보강"""
    
    def __init__(self):
        # 법률 용어 사전
        self.legal_terms = {
            '소비자', '판매자', '공급자', '계약', '해제', '해지', '취소', '환급',
            '손해배상', '위약금', '품질보증', '하자', '민법', '소비자기본법',
            '전자상거래법', '약관', '청약', '승낙', '이행', '불이행', '채무',
            '채권', '귀책사유', '과실', '손해', '배상', '보상', '금지',
            '의무', '권리', '책임', '위반', '조정', '중재', '합의', '결정',
            '주문', '결론', '판단', '근거', '법령', '조항', '조문', '제', '항'
        }
        
        # 카테고리 키워드 매핑
        self.category_keywords = {
            '전자상거래': ['택배', '배송', '반품', '교환', '환불', '결제', '주문', '취소'],
            '통신서비스': ['휴대폰', '스마트폰', '요금제', '통신', '개통', '해지', '위약금'],
            '자동차': ['자동차', '차량', '정비', '수리', '엔진', '타이어', '부품'],
            '가전제품': ['냉장고', 'TV', '세탁기', '에어컨', '전자레인지', '청소기'],
            '의류': ['옷', '의류', '바지', '셔츠', '재킷', '코트', '신발'],
            '식품': ['음식', '식품', '먹거리', '식재료', '배달음식'],
            '부동산': ['아파트', '주택', '전세', '월세', '매매', '임대'],
            '금융': ['대출', '카드', '보험', '이자', '수수료', '환전'],
            '여행': ['항공권', '호텔', '숙박', '여행', '패키지', '취소수수료'],
            '교육': ['학원', '강의', '수업', '교재', '환불'],
            '의료': ['병원', '의료', '진료', '치료', '약', '처방']
        }
        
        # 제품명/브랜드명 패턴 (특정 제품만 추출)
        self.product_patterns = [
            r'아이폰\s?\d+(?:\s?프로)?',  # 아이폰 14, 아이폰 15 프로
            r'갤럭시\s?[A-Z]?\d+(?:\s?[플러스|울트라])?',  # 갤럭시 S24, 갤럭시 S24 울트라
            r'(?:냉장고|TV|세탁기|에어컨|청소기|전자레인지)(?:\s?[가-힣0-9]+)?',  # 가전제품
            r'LG\s?[A-Z0-9]+',  # LG 제품
            r'Samsung\s?[A-Z0-9]+',  # Samsung 제품
        ]
        
        # 회사명 패턴
        self.company_patterns = [
            r'(?:주식회사|㈜)\s?[가-힣]+',
            r'[가-힣]+(?:주식회사|㈜)',
            r'[가-힣]+\s?(?:코리아|Korea)',
            r'[A-Z][a-z]+\s?(?:Korea|코리아)',
        ]
        
        # 불용어 (키워드 추출 시 제외)
        self.stopwords = {
            '이', '그', '저', '것', '수', '등', '및', '또는', '때', '위해',
            '대한', '있는', '없는', '하는', '되는', '않는', '같은', '다른',
            '전체', '일부', '각', '매', '약', '더', '덜', '좀', '잘', '못'
        }
    
    def extract_keywords(self, content: str, top_k: int = 10) -> List[str]:
        """
        키워드 추출 (빈도 기반)
        
        Args:
            content: 청크 내용
            top_k: 추출할 키워드 개수
        
        Returns:
            키워드 리스트
        """
        # 한글, 영문만 추출 (2글자 이상)
        words = re.findall(r'[가-힣]{2,}|[A-Za-z]{3,}', content)
        
        # 불용어 제거
        words = [w for w in words if w not in self.stopwords]
        
        # 빈도 계산
        word_counts = Counter(words)
        
        # 상위 k개 추출
        keywords = [word for word, count in word_counts.most_common(top_k)]
        
        return keywords
    
    def extract_entities(self, content: str) -> Dict[str, List[str]]:
        """
        엔티티 추출 (회사명, 제품명)
        
        Args:
            content: 청크 내용
        
        Returns:
            엔티티 딕셔너리 {'companies': [...], 'products': [...]}
        """
        entities = {
            'companies': [],
            'products': []
        }
        
        # 회사명 추출
        for pattern in self.company_patterns:
            matches = re.findall(pattern, content)
            entities['companies'].extend(matches)
        
        # 제품명 추출
        for pattern in self.product_patterns:
            matches = re.findall(pattern, content)
            entities['products'].extend(matches)
        
        # 중복 제거
        entities['companies'] = list(set(entities['companies']))
        entities['products'] = list(set(entities['products']))
        
        return entities
    
    def extract_legal_terms(self, content: str) -> List[str]:
        """
        법률 용어 추출
        
        Args:
            content: 청크 내용
        
        Returns:
            법률 용어 리스트
        """
        found_terms = []
        
        for term in self.legal_terms:
            if term in content:
                found_terms.append(term)
        
        return found_terms
    
    def infer_category(self, content: str) -> List[str]:
        """
        카테고리 태깅 (키워드 기반)
        
        Args:
            content: 청크 내용
        
        Returns:
            카테고리 리스트
        """
        categories = []
        
        for category, keywords in self.category_keywords.items():
            # 키워드가 내용에 포함되어 있는지 확인
            match_count = sum(1 for kw in keywords if kw in content)
            
            # 2개 이상 매칭되면 해당 카테고리로 분류
            if match_count >= 2:
                categories.append(category)
        
        return categories
    
    def extract_law_references(self, content: str) -> List[str]:
        """
        법령 참조 추출 (예: "민법 제750조", "소비자기본법 제16조")
        
        Args:
            content: 청크 내용
        
        Returns:
            법령 참조 리스트
        """
        # 패턴: 법령명 + 제 + 숫자 + 조
        pattern = r'[가-힣]+법\s?제\s?\d+조(?:\s?제\s?\d+항)?'
        matches = re.findall(pattern, content)
        
        return list(set(matches))
    
    def extract_dates(self, content: str) -> List[str]:
        """
        날짜 추출 (YYYY-MM-DD, YYYY.MM.DD 등)
        
        Args:
            content: 청크 내용
        
        Returns:
            날짜 리스트
        """
        patterns = [
            r'\d{4}[-./]\d{1,2}[-./]\d{1,2}',  # 2024-01-15
            r'\d{4}년\s?\d{1,2}월\s?\d{1,2}일',  # 2024년 1월 15일
        ]
        
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            dates.extend(matches)
        
        return list(set(dates))
    
    def enrich_chunk_metadata(self, chunk: Dict, extract_all: bool = True) -> Dict:
        """
        청크 메타데이터 보강
        
        Args:
            chunk: 청크 데이터
            extract_all: 모든 메타데이터 추출 여부
        
        Returns:
            메타데이터가 보강된 청크
        """
        content = chunk.get('content', '')
        
        if not content or not content.strip():
            return chunk
        
        # 기존 메타데이터 가져오기 (없으면 빈 딕셔너리)
        metadata = chunk.get('metadata', {})
        
        if extract_all:
            # 1. 키워드 추출
            keywords = self.extract_keywords(content, top_k=10)
            if keywords:
                metadata['keywords'] = keywords
            
            # 2. 엔티티 추출
            entities = self.extract_entities(content)
            if entities['companies'] or entities['products']:
                metadata['entities'] = entities
            
            # 3. 법률 용어 추출
            legal_terms = self.extract_legal_terms(content)
            if legal_terms:
                metadata['legal_terms'] = legal_terms
            
            # 4. 카테고리 태깅
            categories = self.infer_category(content)
            if categories:
                metadata['category_tags'] = categories
            
            # 5. 법령 참조 추출
            law_refs = self.extract_law_references(content)
            if law_refs:
                metadata['law_references'] = law_refs
            
            # 6. 날짜 추출
            dates = self.extract_dates(content)
            if dates:
                metadata['dates'] = dates
        
        # 메타데이터 업데이트
        chunk['metadata'] = metadata
        
        return chunk
    
    def enrich_document_metadata(self, doc_data: Dict, extract_all: bool = True) -> Dict:
        """
        문서의 모든 청크에 대해 메타데이터 보강
        
        Args:
            doc_data: 문서 데이터
            extract_all: 모든 메타데이터 추출 여부
        
        Returns:
            메타데이터가 보강된 문서
        """
        for chunk in doc_data.get('chunks', []):
            self.enrich_chunk_metadata(chunk, extract_all=extract_all)
        
        return doc_data


def test_enricher():
    """테스트 함수"""
    enricher = MetadataEnricher()
    
    # 테스트 청크
    test_chunk = {
        'chunk_id': 'test:001',
        'chunk_type': 'judgment',
        'content': '''
        소비자가 주식회사 삼성전자에서 구매한 갤럭시 S24 스마트폰에 하자가 발생하여
        환불을 요청하였으나 판매자가 이를 거부한 사건입니다.
        민법 제750조에 따르면 불법행위로 인한 손해배상 책임이 있으며,
        소비자기본법 제16조에서는 소비자의 권리를 보호하고 있습니다.
        2024년 1월 15일에 계약이 체결되었고, 배송은 2024.01.20에 완료되었습니다.
        ''',
        'content_length': 200,
        'drop': False
    }
    
    # 메타데이터 보강
    enriched = enricher.enrich_chunk_metadata(test_chunk)
    
    print("=" * 80)
    print("메타데이터 보강 테스트")
    print("=" * 80)
    print(f"\n원본 청크 ID: {test_chunk['chunk_id']}")
    print(f"내용 길이: {len(test_chunk['content'])}자")
    
    metadata = enriched['metadata']
    
    print(f"\n📌 키워드 ({len(metadata.get('keywords', []))}개):")
    for kw in metadata.get('keywords', []):
        print(f"  - {kw}")
    
    print(f"\n🏢 엔티티:")
    entities = metadata.get('entities', {})
    if entities.get('companies'):
        print(f"  회사명: {', '.join(entities['companies'])}")
    if entities.get('products'):
        print(f"  제품명: {', '.join(entities['products'])}")
    
    print(f"\n⚖️  법률 용어 ({len(metadata.get('legal_terms', []))}개):")
    for term in metadata.get('legal_terms', [])[:10]:
        print(f"  - {term}")
    
    print(f"\n📂 카테고리 태그:")
    for cat in metadata.get('category_tags', []):
        print(f"  - {cat}")
    
    print(f"\n📜 법령 참조:")
    for ref in metadata.get('law_references', []):
        print(f"  - {ref}")
    
    print(f"\n📅 날짜:")
    for date in metadata.get('dates', []):
        print(f"  - {date}")


if __name__ == '__main__':
    test_enricher()
