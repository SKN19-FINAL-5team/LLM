"""
RAG Generator Module
검색된 청크를 바탕으로 LLM을 사용하여 답변을 생성하는 모듈
"""

import os
from typing import List, Dict
from openai import OpenAI


class RAGGenerator:
    """검색된 컨텍스트를 바탕으로 LLM 답변을 생성하는 클래스"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Args:
            api_key: OpenAI API 키 (기본값: 환경변수에서 로드)
            model: 사용할 LLM 모델 이름
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
    def format_context(self, chunks: List[Dict]) -> str:
        """
        검색된 청크들을 LLM에게 전달할 컨텍스트 형식으로 변환
        
        Args:
            chunks: 검색된 청크 리스트
            
        Returns:
            포맷팅된 컨텍스트 문자열
        """
        if not chunks:
            return "관련 자료를 찾을 수 없습니다."
        
        context_parts = []
        
        for idx, chunk in enumerate(chunks, 1):
            case_info = f"[사례 {idx}]"
            if chunk.get('case_no'):
                case_info += f" 사건번호: {chunk['case_no']}"
            if chunk.get('decision_date'):
                case_info += f", 결정일자: {chunk['decision_date']}"
            if chunk.get('agency'):
                agency_name = {
                    'kca': '한국소비자원',
                    'ecmc': '한국전자거래분쟁조정위원회',
                    'kcdrc': '한국저작권위원회'
                }.get(chunk['agency'], chunk['agency'])
                case_info += f", 기관: {agency_name}"
            
            chunk_type_name = {
                'decision': '주문(결정)',
                'parties_claim': '기초사실(당사자 주장)',
                'judgment': '판단(법적 근거)'
            }.get(chunk['chunk_type'], chunk['chunk_type'])
            
            context_parts.append(
                f"{case_info}\n"
                f"[{chunk_type_name}]\n"
                f"{chunk['text']}\n"
                f"(유사도: {chunk.get('similarity', 0):.3f})\n"
            )
        
        return "\n".join(context_parts)
    
    def generate_answer(
        self, 
        query: str, 
        chunks: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> Dict:
        """
        검색된 청크를 바탕으로 답변 생성
        
        Args:
            query: 사용자 질문
            chunks: 검색된 청크 리스트
            temperature: LLM 생성 온도 (0~1, 낮을수록 일관적)
            max_tokens: 최대 생성 토큰 수
            
        Returns:
            답변 및 메타데이터를 포함한 딕셔너리
        """
        # 컨텍스트 포맷팅
        context = self.format_context(chunks)
        
        # 시스템 프롬프트
        system_prompt = """당신은 한국의 소비자 분쟁 조정 전문가입니다. 
아래 "참고 자료"에 제공된 실제 분쟁조정 사례를 바탕으로 사용자의 질문에 답변하세요.

**답변 작성 원칙:**
1. 반드시 제공된 참고 자료의 내용만을 근거로 답변하세요.
2. 참고 자료에 없는 내용은 추측하거나 지어내지 마세요.
3. 관련 사례의 사건번호, 결정 내용, 법적 근거를 명확히 인용하세요.
4. 답변은 명확하고 이해하기 쉽게 작성하세요.
5. 참고 자료가 질문과 관련이 없다면, 솔직하게 "제공된 자료에서 관련 정보를 찾을 수 없습니다"라고 답변하세요."""

        # 사용자 프롬프트
        user_prompt = f"""[참고 자료]
{context}

[사용자 질문]
{query}

위 참고 자료를 바탕으로 사용자의 질문에 답변해 주세요."""

        # LLM 호출
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            
            return {
                'answer': answer,
                'model': self.model,
                'chunks_used': len(chunks),
                'context': context,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            return {
                'answer': f"답변 생성 중 오류가 발생했습니다: {str(e)}",
                'model': self.model,
                'chunks_used': len(chunks),
                'context': context,
                'error': str(e)
            }
    
    def generate_answer_stream(
        self, 
        query: str, 
        chunks: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 1000
    ):
        """
        스트리밍 방식으로 답변 생성 (실시간 출력용)
        
        Args:
            query: 사용자 질문
            chunks: 검색된 청크 리스트
            temperature: LLM 생성 온도
            max_tokens: 최대 생성 토큰 수
            
        Yields:
            답변 텍스트 조각들
        """
        context = self.format_context(chunks)
        
        system_prompt = """당신은 한국의 소비자 분쟁 조정 전문가입니다. 
아래 "참고 자료"에 제공된 실제 분쟁조정 사례를 바탕으로 사용자의 질문에 답변하세요.

**답변 작성 원칙:**
1. 반드시 제공된 참고 자료의 내용만을 근거로 답변하세요.
2. 참고 자료에 없는 내용은 추측하거나 지어내지 마세요.
3. 관련 사례의 사건번호, 결정 내용, 법적 근거를 명확히 인용하세요.
4. 답변은 명확하고 이해하기 쉽게 작성하세요."""

        user_prompt = f"""[참고 자료]
{context}

[사용자 질문]
{query}

위 참고 자료를 바탕으로 사용자의 질문에 답변해 주세요."""

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n[오류] 답변 생성 중 문제가 발생했습니다: {str(e)}"
    
    def format_multi_method_context(self, method_results: Dict) -> str:
        """
        여러 검색 방법의 결과를 LLM에게 전달할 컨텍스트 형식으로 변환
        
        Args:
            method_results: MultiMethodRetriever.search_all_methods()의 결과
        
        Returns:
            포맷팅된 컨텍스트 문자열
        """
        context_parts = []
        
        for method_name, method_data in method_results.get('methods', {}).items():
            if not method_data.get('success', False):
                continue
            
            results = method_data.get('results', [])
            if not results:
                continue
            
            context_parts.append(f"\n{'='*80}")
            context_parts.append(f"[{method_name.upper()} 검색 결과]")
            context_parts.append(f"검색된 결과 수: {len(results)}개")
            context_parts.append(f"소요 시간: {method_data.get('elapsed_time', 0):.3f}초")
            context_parts.append(f"{'='*80}\n")
            
            for idx, result in enumerate(results[:5], 1):  # 상위 5개만 표시
                case_info = f"[{method_name.upper()} 결과 {idx}]"
                if result.get('case_no'):
                    case_info += f" 사건번호: {result['case_no']}"
                if result.get('decision_date'):
                    case_info += f", 결정일자: {result['decision_date']}"
                if result.get('agency'):
                    agency_name = {
                        'kca': '한국소비자원',
                        'ecmc': '한국전자거래분쟁조정위원회',
                        'kcdrc': '한국저작권위원회'
                    }.get(result['agency'], result['agency'])
                    case_info += f", 기관: {agency_name}"
                
                chunk_type_name = {
                    'decision': '주문(결정)',
                    'parties_claim': '기초사실(당사자 주장)',
                    'judgment': '판단(법적 근거)'
                }.get(result.get('chunk_type', ''), result.get('chunk_type', 'N/A'))
                
                score = result.get('score', 0.0)
                source = result.get('source', 'N/A')
                
                context_parts.append(
                    f"{case_info}\n"
                    f"출처: {source}, 청크 타입: {chunk_type_name}\n"
                    f"점수: {score:.4f}\n"
                    f"내용: {result.get('text', '')[:500]}\n"
                )
        
        if not context_parts:
            return "관련 자료를 찾을 수 없습니다."
        
        return "\n".join(context_parts)
    
    def generate_comparative_answer(
        self,
        query: str,
        method_results: Dict,
        temperature: float = 0.3,
        max_tokens: int = 1500
    ) -> Dict:
        """
        여러 검색 방법의 결과를 비교 분석하여 최종 답변 생성
        
        Args:
            query: 사용자 질문
            method_results: MultiMethodRetriever.search_all_methods()의 결과
            temperature: LLM 생성 온도
            max_tokens: 최대 생성 토큰 수
        
        Returns:
            답변 및 메타데이터를 포함한 딕셔너리
        """
        # 컨텍스트 포맷팅
        context = self.format_multi_method_context(method_results)
        
        # 검색 방법별 요약
        method_summary = []
        for method_name, method_data in method_results.get('methods', {}).items():
            if method_data.get('success', False):
                method_summary.append(
                    f"- {method_name.upper()}: {method_data.get('count', 0)}개 결과 "
                    f"({method_data.get('elapsed_time', 0):.3f}초)"
                )
            else:
                method_summary.append(
                    f"- {method_name.upper()}: 실패 ({method_data.get('error', 'Unknown error')})"
                )
        
        method_summary_text = "\n".join(method_summary)
        
        # 시스템 프롬프트
        system_prompt = """당신은 한국의 소비자 분쟁 조정 전문가입니다. 
아래 "참고 자료"에는 여러 검색 방법(cosine similarity, BM25, SPLADE, hybrid search)으로 찾은 결과가 포함되어 있습니다.

**답변 작성 원칙:**
1. 각 검색 방법의 결과를 비교 분석하여 가장 관련성 높은 정보를 종합하세요.
2. 검색 방법별로 찾은 결과의 차이점과 공통점을 고려하세요.
3. 반드시 제공된 참고 자료의 내용만을 근거로 답변하세요.
4. 참고 자료에 없는 내용은 추측하거나 지어내지 마세요.
5. 관련 사례의 사건번호, 결정 내용, 법적 근거를 명확히 인용하세요.
6. 답변은 명확하고 이해하기 쉽게 작성하세요.
7. 여러 검색 방법에서 공통으로 나타난 정보는 더 신뢰할 수 있습니다.
8. 참고 자료가 질문과 관련이 없다면, 솔직하게 "제공된 자료에서 관련 정보를 찾을 수 없습니다"라고 답변하세요.

**답변 구조:**
1. 각 검색 방법의 결과를 간단히 요약
2. 가장 관련성 높은 정보를 종합한 최종 답변
3. 참고 출처 명시 (검색 방법, 사건번호 등)"""

        # 사용자 프롬프트
        user_prompt = f"""[검색 방법별 요약]
{method_summary_text}

[참고 자료]
{context}

[사용자 질문]
{query}

위 참고 자료를 바탕으로 각 검색 방법의 결과를 비교 분석하고, 사용자의 질문에 종합적으로 답변해 주세요."""

        # LLM 호출
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            
            return {
                'answer': answer,
                'model': self.model,
                'query': query,
                'methods_used': list(method_results.get('methods', {}).keys()),
                'total_results': sum(
                    m.get('count', 0) 
                    for m in method_results.get('methods', {}).values()
                ),
                'context': context,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            return {
                'answer': f"답변 생성 중 오류가 발생했습니다: {str(e)}",
                'model': self.model,
                'query': query,
                'methods_used': list(method_results.get('methods', {}).keys()),
                'total_results': 0,
                'context': context,
                'error': str(e)
            }
