"""
Query Analyzer Module
사용자 질문을 분석하여 검색에 필요한 메타정보 추출
"""

import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum


class QueryType(Enum):
    """질문 유형"""
    LEGAL = "legal"               # 법률 질문 (법령, 조문)
    PRACTICAL = "practical"       # 실무 질문 (사례 중심)
    PRODUCT_SPECIFIC = "product_specific"  # 품목별 기준 질문
    GENERAL = "general"           # 일반 질문


@dataclass
class QueryAnalysis:
    """쿼리 분석 결과"""
    query_type: QueryType
    extracted_items: List[str]       # 추출된 품목명
    extracted_articles: List[Dict]   # 추출된 조문 정보
    keywords: List[str]              # 핵심 키워드
    dispute_types: List[str]         # 분쟁 유형
    law_names: List[str]            # 법령명
    has_amount: bool                # 금액 포함 여부
    has_date: bool                  # 날짜 포함 여부


class QueryAnalyzer:
    """쿼리 분석기"""
    
    # 법률 키워드
    LEGAL_KEYWORDS = {
        '법', '법률', '법령', '조', '항', '호', '규정', '시행령', '시행규칙',
        '민법', '상법', '소비자기본법', '전자상거래법', '약관규제법',
        '제', '조문', '규칙', '기준'
    }
    
    # 실무 키워드
    PRACTICAL_KEYWORDS = {
        '사례', '상담', '질문', '답변', '경험', '어떻게', '방법',
        '해야', '하나요', '알려주세요', '도와주세요', '문의',
        '궁금', '어찌', '어떻게'
    }
    
    # 품목 관련 키워드 (Criteria 데이터 기반 확장 - 총 200+ 품목)
    PRODUCT_KEYWORDS = {
        # 일반 용어
        '제품', '상품', '물건', '품목', '재화',
        
        # 가전제품 (주요)
        '냉장고', '세탁기', '에어컨', '에어콘', 'TV', '텔레비전', '스마트폰', '휴대폰', 
        '노트북', '컴퓨터', '데스크탑', '모니터', '프린터', '청소기', '전기청소기',
        '전자레인지', '전자렌지', '밥솥', '전기밥솥', '전기압력밥솥', '가스레인지',
        '정수기', '공기청정기', '가습기', '제습기', '선풍기', '난로', '전기난로',
        '보일러', '온수기', '전기온수기', '냉온수기', '냉수기', '비데', '안마의자',
        '식기세척기', '식기건조기', '의류건조기', '의류관리기', '다리미', '전기다리미',
        '전기장판', '전기담요', '믹서기', '전기믹서', '쥬서기', '핸드블랜더',
        '전기주전자', '전기포트', '전기토스터', '전기오븐', '전기튀김기', '전기프라이팬',
        '면도기', '전기면도기', '헤어드라이어', '드라이어', '고데기', '전기머리인두',
        '카메라', '비디오카메라', '캠코더', '빔프로젝터', '빔', '복사기', '팩시밀리',
        '워드프로세서', '타자기', 'DVD플레이어', 'VTR', 'MP3플레이어', '녹음기',
        '라디오', '전축', '홈시어터', '스피커', '헤드폰', '이어폰',
        '태블릿', '패드', '스마트워치', '웨어러블', '네비게이션', '네비',
        
        # 가구
        '침대', '소파', '책상', '의자', '책장', '책꽂이', '장롱', '옷장', '신발장',
        '식탁', '테이블', '찬장', '싱크대', '화장대', '서랍장', '장식장', '문갑',
        '캐비넷', '파일링캐비넷', '소파베드', '침구',
        
        # 의류/신발
        '옷', '의류', '의상', '셔츠', '와이셔츠', '티셔츠', '바지', '청바지', '치마', 
        '스커트', '재킷', '자켓', '점퍼', '코트', '패딩', '파카', '조끼', '베스트',
        '스웨터', '니트', '가디건', '내의', '속옷', '양말', '스타킹',
        '한복', '정장', '양복', '드레스', '원피스', '블라우스',
        '신발', '구두', '운동화', '스니커즈', '샌들', '슬리퍼', '부츠', '하이힐',
        '등산화', '등산용품', '고무신',
        '가방', '핸드백', '백팩', '배낭', '크로스백', '숄더백', '클러치', '지갑',
        '가죽가방', '천가방', '책가방',
        '넥타이', '타이', '벨트', '혁대', '머플러', '스카프', '모자',
        
        # 식품
        '계란', '달걀', '메추리알', '우유', '두유', '요구르트', '치즈', '버터',
        '고기', '소고기', '돼지고기', '닭고기', '생선', '해산물', '조개', '새우',
        '쌀', '밥', '빵', '식빵', '라면', '국수', '냉면', '당면', '파스타',
        '김치', '된장', '고추장', '간장', '식초', '참기름', '식용유', '기름',
        '두부', '연두부', '유부', '콩', '팥', '밤', '견과류',
        '야채', '채소', '과일', '과실', '사과', '배', '감', '귤', '감귤', '오렌지',
        '바나나', '포도', '딸기', '수박', '참외', '멜론', '복숭아', '자두', '살구',
        '파인애플', '키위', '망고', '토마토', '당근', '양파', '마늘', '대파', '파',
        '배추', '양배추', '상추', '시금치', '오이', '호박', '고추', '피망', '가지',
        '버섯', '목이버섯', '표고버섯', '감자', '고구마',
        '과자', '비스킷', '쿠키', '케이크', '초콜릿', '캔디', '사탕', '껌',
        '음료수', '주스', '쥬스', '탄산음료', '사이다', '콜라', '커피', '차', '녹차',
        
        # 화장품/생활용품
        '화장품', '샴푸', '린스', '트리트먼트', '바디워시', '비누', '세제', '치약',
        '로션', '크림', '에센스', '스킨', '토너', '클렌징', '팩', '마스크팩',
        '립스틱', '립글로스', '틴트', '파운데이션', '비비크림', '파우더', '아이섀도우',
        '마스카라', '아이라이너', '볼터치', '블러셔', '매니큐어', '네일', '향수',
        '칫솔', '면도기', '면도날', '화장지', '휴지', '물티슈', '물휴지', 
        '생리대', '기저귀', '일회용기저귀',
        
        # 주방용품
        '냄비', '프라이팬', '후라이팬', '압력솥', '찜통', '찜기', '주전자',
        '식기', '그릇', '접시', '컵', '머그컵', '수저', '젓가락', '포크', '나이프',
        '도마', '칼', '식칼', '가위', '주방가위', '조리도구',
        '믹서', '믹서기', '블렌더', '강판', '거품기',
        '보온병', '텀블러', '물통', '도시락', '도시락통', '밀폐용기',
        
        # 전자/통신
        '핸드폰', '휴대전화', '피쳐폰', '갤럭시', '아이폰',
        '무선전화기', '유선전화기', '인터폰', '도어폰', '초인종',
        '충전기', '배터리', '건전지', '어댑터', '케이블', '선', 
        '키보드', '마우스', 'USB', '하드디스크', 'SSD', '메모리',
        
        # 자동차/이동수단
        '자동차', '차', '승용차', '트럭', '화물차', '승합차', 'SUV', '세단',
        '오토바이', '모터사이클', '스쿠터', '자전거', '전기자전거', '킥보드',
        '타이어', '바퀴', '휠', '배터리',
        
        # 스포츠/레저
        '운동기구', '헬스기구', '러닝머신', '트레드밀', '아령', '덤벨', '바벨',
        '자전거', '인라인', '스케이트', '롤러스케이트', '스키', '보드', '스노보드',
        '골프채', '골프공', '골프용품', '라켓', '테니스라켓', '배드민턴라켓',
        '낚시대', '낚싯대', '낚시용품', '텐트', '침낭', '등산용품', '배낭',
        
        # 기타
        '장난감', '완구', '인형', '피규어', '레고', '블록', '퍼즐',
        '악기', '피아노', '기타', '바이올린', '키보드',
        '시계', '손목시계', '벽시계', '탁상시계', '알람시계',
        '안경', '선글라스', '돋보기', '렌즈', '콘택트렌즈',
        '우산', '양산', '장우산', '접이식우산',
        '이불', '베개', '베갯잇', '시트', '침구류', '담요', '모포', '전기장판',
        '카펫', '러그', '매트', '발매트', '요가매트',
        '화분', '화병', '꽃', '식물', '선인장',
        '액자', '그림', '시계', '거울', '전신거울',
        '전화기', '유선전화', '무선전화', '팩스',
    }
    
    # 품목명 유사어 매핑 (검색 정확도 향상)
    PRODUCT_SYNONYMS = {
        '냉방기': '에어컨',
        '냉난방기': '에어컨',
        '에어콘': '에어컨',
        '세탁기계': '세탁기',
        '세탁기기': '세탁기',
        '냉동고': '냉장고',
        '냉장냉동고': '냉장고',
        '피씨': '컴퓨터',
        'PC': '컴퓨터',
        '퍼스널컴퓨터': '컴퓨터',
        '데스크탑': '컴퓨터',
        '노트북': '노트북컴퓨터',
        '핸드폰': '휴대폰',
        '스마트폰': '휴대폰',
        '갤럭시': '휴대폰',
        '아이폰': '휴대폰',
        '텔레비전': 'TV',
        '텔레비젼': 'TV',
        '티비': 'TV',
        '전자렌지': '전자레인지',
        '전자레인지': '전자레인지',
        '레인지': '전자레인지',
        '밥통': '밥솥',
        '전기밥통': '밥솥',
        '청소기': '전기청소기',
        '진공청소기': '전기청소기',
        '공기정화기': '공기청정기',
        '공청기': '공기청정기',
        '정수기': '정수기',
        '워터': '정수기',
        '달걀': '계란',
        '에그': '계란',
        '소고기': '고기',
        '돼지고기': '고기',
        '닭고기': '고기',
        '구두': '신발',
        '운동화': '신발',
        '샌들': '신발',
        '침대': '침대',
        '매트리스': '침대',
    }
    
    # 분쟁 유형 키워드
    DISPUTE_TYPE_KEYWORDS = {
        '환불': ['환불', '환급', '되돌려', '돌려받', '반환'],
        '교환': ['교환', '바꿔', '다른것', '새것'],
        '수리': ['수리', 'A/S', 'AS', '고쳐', '수선', '보수'],
        '파손': ['파손', '깨졌', '부서졌', '손상', '파손됨'],
        '불량': ['불량', '하자', '결함', '문제', '이상', '고장'],
        '지연': ['지연', '늦게', '안옴', '안왔', '배송지연'],
        '취소': ['취소', '철회', '해지', '해제'],
        '변질': ['변질', '상했', '썩었', '부패'],
        '오배송': ['오배송', '잘못', '다른물건'],
    }
    
    # 주요 법령명
    LAW_NAMES = [
        '민법', '상법', '소비자기본법', '전자상거래법', 
        '전자상거래 등에서의 소비자보호에 관한 법률',
        '약관의 규제에 관한 법률', '약관규제법',
        '할부거래에 관한 법률', '방문판매 등에 관한 법률',
        '제조물 책임법', '제조물책임법',
        '표시·광고의 공정화에 관한 법률',
        '콘텐츠산업 진흥법', '저작권법'
    ]
    
    def __init__(self):
        """초기화"""
        pass
    
    def analyze(self, query: str) -> QueryAnalysis:
        """
        쿼리 분석 메인 함수
        
        Args:
            query: 사용자 질문
        
        Returns:
            QueryAnalysis 객체
        """
        query_lower = query.lower()
        
        # 1. 질문 유형 분류
        query_type = self._classify_query_type(query, query_lower)
        
        # 2. 조문 추출
        extracted_articles = self._extract_law_articles(query)
        
        # 3. 품목명 추출
        extracted_items = self._extract_product_names(query, query_lower)
        
        # 4. 키워드 추출
        keywords = self._extract_keywords(query, query_lower)
        
        # 5. 분쟁 유형 추론
        dispute_types = self._infer_dispute_types(query, query_lower)
        
        # 6. 법령명 추출
        law_names = self._extract_law_names(query)
        
        # 7. 금액/날짜 포함 여부
        has_amount = bool(re.search(r'\d+\s*만?\s*원', query))
        has_date = bool(re.search(r'\d{4}[년.-]', query))
        
        return QueryAnalysis(
            query_type=query_type,
            extracted_items=extracted_items,
            extracted_articles=extracted_articles,
            keywords=keywords,
            dispute_types=dispute_types,
            law_names=law_names,
            has_amount=has_amount,
            has_date=has_date
        )
    
    def _classify_query_type(self, query: str, query_lower: str) -> QueryType:
        """
        질문 유형 분류
        
        우선순위:
        1. 조문 언급 또는 법령명 → LEGAL
        2. 품목명 + 분쟁유형 → PRODUCT_SPECIFIC
        3. 실무 키워드 많음 → PRACTICAL
        4. 기본 → GENERAL
        """
        # 조문 패턴 확인
        has_article = bool(re.search(r'제\s*\d+\s*조', query))
        
        # 법령명 확인
        has_law_name = any(law_name in query for law_name in self.LAW_NAMES)
        
        # 법률 키워드 카운트
        legal_count = sum(1 for kw in self.LEGAL_KEYWORDS if kw in query_lower)
        
        # 품목 키워드 카운트
        product_count = sum(1 for kw in self.PRODUCT_KEYWORDS if kw in query_lower)
        
        # 실무 키워드 카운트
        practical_count = sum(1 for kw in self.PRACTICAL_KEYWORDS if kw in query_lower)
        
        # 분쟁 유형 키워드 확인
        has_dispute_type = any(
            any(kw in query_lower for kw in keywords)
            for keywords in self.DISPUTE_TYPE_KEYWORDS.values()
        )
        
        # 우선순위에 따른 분류
        if has_article or has_law_name or legal_count >= 2:
            return QueryType.LEGAL
        
        if product_count >= 1 and has_dispute_type:
            return QueryType.PRODUCT_SPECIFIC
        
        if practical_count >= 2 or '사례' in query_lower:
            return QueryType.PRACTICAL
        
        return QueryType.GENERAL
    
    def _extract_law_articles(self, query: str) -> List[Dict]:
        """
        조문 정보 추출
        
        패턴:
        - "제123조" -> {law_name: None, article_no: "제123조"}
        - "민법 제750조" -> {law_name: "민법", article_no: "제750조"}
        - "제10조 제2항" -> {law_name: None, article_no: "제10조", paragraph_no: "제2항"}
        """
        articles = []
        
        # 패턴 1: "법령명 제N조"
        pattern1 = r'([가-힣\s]+법[률령]?)\s*(제\s*\d+\s*조)'
        matches1 = re.findall(pattern1, query)
        for law_name, article_no in matches1:
            law_name = law_name.strip()
            article_no = re.sub(r'\s+', '', article_no)
            articles.append({
                'law_name': law_name,
                'article_no': article_no,
                'paragraph_no': None
            })
        
        # 패턴 2: "제N조 제M항"
        pattern2 = r'(제\s*\d+\s*조)\s*(제\s*\d+\s*항)?'
        matches2 = re.findall(pattern2, query)
        for article_no, paragraph_no in matches2:
            article_no = re.sub(r'\s+', '', article_no)
            paragraph_no = re.sub(r'\s+', '', paragraph_no) if paragraph_no else None
            
            # 이미 추가된 조문인지 확인
            if not any(a['article_no'] == article_no for a in articles):
                articles.append({
                    'law_name': None,
                    'article_no': article_no,
                    'paragraph_no': paragraph_no
                })
        
        return articles
    
    def _extract_product_names(self, query: str, query_lower: str) -> List[str]:
        """
        품목명 추출 (개선됨 - Phase 2)
        
        방법:
        1. 사전 기반 직접 매칭 (PRODUCT_KEYWORDS)
        2. 조사 포함 패턴 매칭 ("냉장고가", "세탁기를" 등)
        3. 유사어 매핑 (PRODUCT_SYNONYMS)
        4. 문맥 기반 추출 ("~을/를 구매", "~이/가 고장" 등)
        """
        items = set()
        
        # 1. 사전 기반 직접 매칭 (정확 매칭)
        for product in self.PRODUCT_KEYWORDS:
            product_lower = product.lower()
            # 정확한 단어 경계 확인 (부분 매칭 방지)
            if product_lower in query_lower:
                # "냉장고같은" 같은 오탐지 제외
                idx = query_lower.find(product_lower)
                # 앞뒤 문자 확인
                before_ok = (idx == 0 or not query_lower[idx-1].isalnum())
                after_ok = (idx + len(product_lower) >= len(query_lower) or 
                           not query_lower[idx + len(product_lower)].isalnum())
                
                if before_ok and after_ok:
                    items.add(product)
        
        # 2. 조사 포함 패턴 매칭 (한국어 특화)
        # "냉장고가", "세탁기를", "에어컨의", "TV는" 등
        for product in self.PRODUCT_KEYWORDS:
            patterns = [
                rf'{product}(?:가|를|을|는|은|의|에|과|와|도|만|부터|까지)',
                rf'{product}(?:이|가)\s',
                rf'{product}\s*(?:구매|구입|샀|산|사려|살|사고)',
            ]
            for pattern in patterns:
                if re.search(pattern, query):
                    items.add(product)
                    break
        
        # 3. 유사어 매핑 적용
        for synonym, standard in self.PRODUCT_SYNONYMS.items():
            if synonym.lower() in query_lower:
                items.add(standard)
        
        # 4. 문맥 기반 추출 (추가 패턴)
        context_patterns = [
            (r'([가-힣a-zA-Z0-9]+)(?:을|를)\s*(?:구매|샀|산|구입|주문)', 'purchase'),
            (r'([가-힣a-zA-Z0-9]+)(?:이|가)\s*(?:고장|파손|불량|문제|하자)', 'defect'),
            (r'([가-힣a-zA-Z0-9]+)(?:을|를)\s*(?:환불|교환|반품|수리)', 'dispute'),
            (r'([가-힣a-zA-Z0-9]+)\s*(?:품질보증|보증기간|AS|에이에스)', 'warranty'),
        ]
        
        for pattern, category in context_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                item = match.strip()
                # 길이 제한 및 일반 용어 제외
                if (2 <= len(item) <= 15 and 
                    item not in ['제품', '상품', '물건', '품목', '재화', '물품', '이것', '그것', '저것']):
                    # PRODUCT_KEYWORDS에 있는지 확인
                    if item in self.PRODUCT_KEYWORDS or item in self.PRODUCT_SYNONYMS:
                        items.add(item)
        
        # 5. 결과 정제
        # - 일반 용어 제거
        generic_terms = {'제품', '상품', '물건', '품목', '재화', '전자제품', '가전제품', '식품', '의류', '가구'}
        items = items - generic_terms
        
        # 최대 5개, 길이순 정렬 (짧은 것이 더 구체적일 가능성)
        return sorted(list(items), key=len)[:5]
    
    def _extract_keywords(self, query: str, query_lower: str) -> List[str]:
        """
        핵심 키워드 추출
        
        방법:
        1. 명사 추출 (간단한 패턴 기반)
        2. 중요 용어 가중치
        """
        keywords = set()
        
        # 단어 분리 (간단한 토큰화)
        words = re.findall(r'[가-힣a-zA-Z0-9]+', query)
        
        for word in words:
            if len(word) >= 2:
                keywords.add(word)
        
        # 상위 15개만 반환
        return list(keywords)[:15]
    
    def _infer_dispute_types(self, query: str, query_lower: str) -> List[str]:
        """
        분쟁 유형 추론
        
        키워드 매칭을 통해 분쟁 유형 추정
        """
        dispute_types = []
        
        for dispute_type, keywords in self.DISPUTE_TYPE_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                dispute_types.append(dispute_type)
        
        return dispute_types
    
    def _extract_law_names(self, query: str) -> List[str]:
        """법령명 추출"""
        law_names = []
        
        for law_name in self.LAW_NAMES:
            if law_name in query:
                law_names.append(law_name)
        
        return law_names


# 편의 함수
def analyze_query(query: str) -> QueryAnalysis:
    """쿼리 분석 편의 함수"""
    analyzer = QueryAnalyzer()
    return analyzer.analyze(query)
