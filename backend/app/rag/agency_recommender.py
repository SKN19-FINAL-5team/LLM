"""
Agency Recommender Module
사용자 질문과 검색 결과를 바탕으로 적절한 분쟁조정기관을 추천하는 모듈
"""

from typing import List, Dict, Tuple
from collections import Counter


class AgencyRecommender:
    """기관 추천 클래스 (규칙 기반 + 검색 결과 통계)"""
    
    # 기관 정보
    AGENCIES = {
        'kca': {
            'name': '한국소비자원',
            'full_name': '한국소비자원 (Korea Consumer Agency)',
            'description': '일반 소비자 분쟁 조정 (전자제품, 의류, 식품, 가구 등)'
        },
        'ecmc': {
            'name': '한국전자거래분쟁조정위원회',
            'full_name': '한국전자거래분쟁조정위원회 (Electronic Commerce Mediation Committee)',
            'description': '전자상거래 및 통신판매 관련 분쟁 조정'
        },
        'kcdrc': {
            'name': '한국저작권위원회',
            'full_name': '한국저작권위원회 (Korea Copyright Commission)',
            'description': '저작권 및 콘텐츠 관련 분쟁 조정'
        }
    }
    
    # 규칙 기반 키워드 (각 기관별)
    KEYWORD_RULES = {
        'ecmc': [
            # 전자상거래 관련
            '전자상거래', '인터넷', '온라인', '통신판매', '쇼핑몰',
            '배송', '택배', '반품', '교환', '환불',
            '오픈마켓', '소셜커머스', '이커머스',
            # 플랫폼
            '쿠팡', '네이버', '11번가', 'G마켓', '옥션',
            '인터넷쇼핑', '온라인쇼핑', '모바일쇼핑',
            # 배송/물류
            '배송지연', '배송오류', '미배송', '파손배송',
            '무통장입금', '결제오류', '전자결제'
        ],
        'kcdrc': [
            # 저작권 관련
            '저작권', '콘텐츠', '음원', '음악', '영상',
            '웹툰', '만화', '소설', '전자책',
            # 플랫폼
            '멜론', '지니', '벅스', '유튜브', '넷플릭스',
            '왓챠', '티빙', '웨이브', '네이버웹툰', '카카오페이지',
            # 저작권 문제
            '무단사용', '무단복제', '표절', '저작권침해',
            '구독취소', '이용권', '멤버십', '스트리밍'
        ],
        'kca': [
            # 일반 소비재
            '전자제품', '가전제품', '노트북', '스마트폰', '컴퓨터',
            '의류', '신발', '가구', '침대', '소파',
            '식품', '화장품', '건강기능식품',
            # 서비스
            '학원', '교육', '헬스', '피트니스', '수강료',
            '렌탈', '리스', '할부', '제조물',
            # 일반 분쟁
            '환불거부', '불량', '하자', '수리', 'A/S',
            '품질보증', '제조물책임'
        ]
    }
    
    def __init__(self, rule_weight: float = 0.7, stat_weight: float = 0.3):
        """
        Args:
            rule_weight: 규칙 기반 가중치 (기본값: 0.7)
            stat_weight: 검색 결과 통계 가중치 (기본값: 0.3)
        """
        self.rule_weight = rule_weight
        self.stat_weight = stat_weight
    
    def calculate_rule_scores(self, query: str) -> Dict[str, float]:
        """
        규칙 기반 점수 계산 (키워드 매칭)
        
        Args:
            query: 사용자 질문
            
        Returns:
            각 기관별 점수 (0~1 정규화)
        """
        query_lower = query.lower()
        scores = {'kca': 0.0, 'ecmc': 0.0, 'kcdrc': 0.0}
        
        # 각 기관별 키워드 매칭
        for agency, keywords in self.KEYWORD_RULES.items():
            match_count = 0
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    match_count += 1
            
            # 점수 계산 (매칭된 키워드 수에 비례)
            if match_count > 0:
                # 매칭 수에 로그 스케일 적용 (과도한 점수 방지)
                import math
                scores[agency] = math.log1p(match_count) / math.log1p(len(keywords))
        
        # KCA를 기본 점수로 설정 (모든 기관의 점수가 0일 경우 대비)
        if all(score == 0 for score in scores.values()):
            scores['kca'] = 0.3  # 기본 점수
        
        # 정규화 (0~1 범위)
        max_score = max(scores.values())
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}
        
        return scores
    
    def calculate_stat_scores(self, search_results: List[Dict]) -> Dict[str, float]:
        """
        검색 결과 통계 기반 점수 계산
        
        Args:
            search_results: 검색된 청크 리스트
            
        Returns:
            각 기관별 점수 (0~1 정규화)
        """
        if not search_results:
            return {'kca': 0.0, 'ecmc': 0.0, 'kcdrc': 0.0}
        
        # 기관별 출현 빈도 및 가중치 계산
        agency_scores = {'kca': 0.0, 'ecmc': 0.0, 'kcdrc': 0.0}
        
        for idx, chunk in enumerate(search_results):
            agency = chunk.get('agency', '').lower()
            if agency in agency_scores:
                # 순위에 따른 가중치 (상위 결과일수록 높은 가중치)
                rank_weight = 1.0 / (idx + 1)
                
                # 유사도 가중치
                similarity = chunk.get('similarity', 0.0)
                
                # 최종 점수 = 순위 가중치 * 유사도
                agency_scores[agency] += rank_weight * similarity
        
        # 정규화 (0~1 범위)
        total = sum(agency_scores.values())
        if total > 0:
            agency_scores = {k: v / total for k, v in agency_scores.items()}
        
        return agency_scores
    
    def recommend(
        self, 
        query: str, 
        search_results: List[Dict] = None,
        top_n: int = 2
    ) -> List[Tuple[str, float, Dict]]:
        """
        기관 추천 (규칙 + 통계 결합)
        
        Args:
            query: 사용자 질문
            search_results: 검색된 청크 리스트 (선택사항)
            top_n: 반환할 추천 기관 수 (기본값: 2)
            
        Returns:
            [(기관코드, 최종점수, 상세정보), ...] 형태의 리스트 (점수 내림차순)
        """
        # 규칙 기반 점수
        rule_scores = self.calculate_rule_scores(query)
        
        # 검색 결과 통계 점수
        stat_scores = {'kca': 0.0, 'ecmc': 0.0, 'kcdrc': 0.0}
        if search_results:
            stat_scores = self.calculate_stat_scores(search_results)
        
        # 최종 점수 계산 (가중 평균)
        final_scores = {}
        for agency in ['kca', 'ecmc', 'kcdrc']:
            final_scores[agency] = (
                self.rule_weight * rule_scores[agency] +
                self.stat_weight * stat_scores[agency]
            )
        
        # 점수 순으로 정렬
        sorted_agencies = sorted(
            final_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 상위 N개 반환 (대문자로 변환하여 DB와 일치시킴)
        recommendations = []
        for agency_code, score in sorted_agencies[:top_n]:
            agency_info = self.AGENCIES[agency_code].copy()
            agency_info['rule_score'] = rule_scores[agency_code]
            agency_info['stat_score'] = stat_scores[agency_code]
            # DB의 source_org는 대문자 (KCA, ECMC)이므로 대문자로 변환
            recommendations.append((agency_code.upper(), score, agency_info))
        
        return recommendations
    
    def explain_recommendation(
        self, 
        query: str, 
        search_results: List[Dict] = None
    ) -> Dict:
        """
        추천 결과에 대한 상세 설명 생성
        
        Args:
            query: 사용자 질문
            search_results: 검색된 청크 리스트
            
        Returns:
            추천 근거 및 상세 정보를 포함한 딕셔너리
        """
        recommendations = self.recommend(query, search_results, top_n=3)
        
        # 검색 결과 통계
        agency_distribution = {}
        if search_results:
            agency_counts = Counter(
                chunk.get('agency', 'unknown') 
                for chunk in search_results
            )
            agency_distribution = dict(agency_counts)
        
        return {
            'recommendations': [
                {
                    'agency_code': code,
                    'agency_name': info['name'],
                    'full_name': info['full_name'],
                    'description': info['description'],
                    'final_score': score,
                    'rule_score': info['rule_score'],
                    'stat_score': info['stat_score'],
                    'rank': idx + 1
                }
                for idx, (code, score, info) in enumerate(recommendations)
            ],
            'search_results_distribution': agency_distribution,
            'weights': {
                'rule_weight': self.rule_weight,
                'stat_weight': self.stat_weight
            }
        }
    
    def get_agency_info(self, agency_code: str) -> Dict:
        """
        특정 기관의 정보 반환
        
        Args:
            agency_code: 기관 코드 ('kca', 'ecmc', 'kcdrc')
            
        Returns:
            기관 정보 딕셔너리
        """
        return self.AGENCIES.get(agency_code.lower(), {})
    
    def format_recommendation_text(
        self, 
        query: str, 
        search_results: List[Dict] = None
    ) -> str:
        """
        추천 결과를 사용자 친화적인 텍스트로 포맷팅
        
        Args:
            query: 사용자 질문
            search_results: 검색된 청크 리스트
            
        Returns:
            포맷팅된 추천 텍스트
        """
        explanation = self.explain_recommendation(query, search_results)
        recommendations = explanation['recommendations']
        
        if not recommendations:
            return "적절한 기관을 찾을 수 없습니다."
        
        # 1순위 기관
        primary = recommendations[0]
        text_parts = [
            f"📌 추천 기관: {primary['agency_name']}",
            f"   {primary['description']}",
            f"   (추천 점수: {primary['final_score']:.2f})",
            ""
        ]
        
        # 2순위 기관 (있는 경우)
        if len(recommendations) > 1:
            secondary = recommendations[1]
            text_parts.extend([
                f"📋 대안 기관: {secondary['agency_name']}",
                f"   {secondary['description']}",
                f"   (추천 점수: {secondary['final_score']:.2f})",
                ""
            ])
        
        # 검색 결과 통계 (있는 경우)
        if explanation['search_results_distribution']:
            text_parts.append("📊 검색 결과 통계:")
            for agency, count in explanation['search_results_distribution'].items():
                agency_name = self.AGENCIES.get(agency, {}).get('name', agency)
                text_parts.append(f"   - {agency_name}: {count}건")
        
        return "\n".join(text_parts)


# 편의 함수
def recommend_agency(
    query: str, 
    search_results: List[Dict] = None,
    top_n: int = 2
) -> List[Tuple[str, float, Dict]]:
    """
    기관 추천 편의 함수
    
    Args:
        query: 사용자 질문
        search_results: 검색된 청크 리스트
        top_n: 반환할 추천 기관 수
        
    Returns:
        추천 기관 리스트
    """
    recommender = AgencyRecommender()
    return recommender.recommend(query, search_results, top_n)


def explain_agency_recommendation(
    query: str, 
    search_results: List[Dict] = None
) -> Dict:
    """
    기관 추천 설명 편의 함수
    
    Args:
        query: 사용자 질문
        search_results: 검색된 청크 리스트
        
    Returns:
        추천 근거 및 상세 정보
    """
    recommender = AgencyRecommender()
    return recommender.explain_recommendation(query, search_results)
