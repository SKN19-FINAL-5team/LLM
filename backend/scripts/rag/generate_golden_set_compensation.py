#!/usr/bin/env python3
"""
피해구제 사례 데이터 Golden Set 생성 스크립트

실제 데이터베이스에서 피해구제 사례 데이터를 샘플링하여
쿼리와 관련 청크를 추출하여 golden set JSON 파일 생성
"""

import os
import sys
import json
import psycopg2
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
import argparse
from datetime import datetime
import re

# 프로젝트 루트를 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))

from app.rag import VectorRetriever

load_dotenv()


class CompensationGoldenSetGenerator:
    """피해구제 사례 데이터 Golden Set 생성기"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.retriever = VectorRetriever(db_config)
    
    def connect_db(self):
        """데이터베이스 연결"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def close_db(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
        self.retriever.close()
    
    def extract_query_from_chunk(self, content: str) -> str:
        """
        청크 내용을 기반으로 자연스러운 쿼리 생성
        
        Args:
            content: 청크 내용
        
        Returns:
            생성된 쿼리 문자열
        """
        query_parts = []
        content_clean = content.strip()
        
        # 질문/답변 형식에서 질문 부분 추출 시도
        if '[질문]' in content_clean or 'Q:' in content_clean:
            # 질문 부분 추출
            q_match = re.search(r'\[질문\](.*?)(?:\[답변\]|$)', content_clean, re.DOTALL)
            if not q_match:
                q_match = re.search(r'Q:\s*(.*?)(?:A:|$)', content_clean, re.DOTALL)
            if q_match:
                question = q_match.group(1).strip()
                # 질문에서 핵심 키워드 추출
                keywords = re.findall(r'[가-힣]{2,}', question[:100])
                if keywords:
                    query_parts.extend(keywords[:5])
        
        # 문의 관련 키워드
        inquiry_keywords = ['문의', '질문', '상담', '환불', '교환', '수리', '배상', 
                           '보증', '기간', '기준', '계산', '방법']
        found_keywords = [k for k in inquiry_keywords if k in content_clean]
        if found_keywords:
            query_parts.extend(found_keywords[:3])
        
        # 일반 키워드 추출
        if not query_parts:
            keywords = re.findall(r'[가-힣]{2,4}', content_clean[:200])
            keywords = [k for k in keywords if len(k) >= 2][:5]
            query_parts.extend(keywords)
        
        query = ' '.join(query_parts) if query_parts else content_clean[:50]
        return query.strip()
    
    def find_related_chunks(self, query: str, source_chunk_id: str, top_k: int = 10) -> List[str]:
        """
        쿼리와 관련된 청크 찾기 (벡터 검색 사용)
        
        Args:
            query: 검색 쿼리
            source_chunk_id: 원본 청크 ID (제외)
            top_k: 반환할 최대 결과 수
        
        Returns:
            관련 청크 ID 리스트
        """
        try:
            # 벡터 검색으로 관련 청크 찾기
            results = self.retriever.search(query=query, top_k=top_k * 2)
            
            # doc_type이 'consumer_counsel_case' 또는 'counsel_case'인 것만 필터링 및 source_chunk_id 제외
            related_chunk_ids = []
            for result in results:
                source = result.get('source', '')
                if source in ('consumer_counsel_case', 'counsel_case') and result.get('chunk_uid') != source_chunk_id:
                    related_chunk_ids.append(result.get('chunk_uid'))
                    if len(related_chunk_ids) >= top_k:
                        break
            
            return related_chunk_ids
        except Exception as e:
            print(f"  ⚠️  관련 청크 검색 오류: {e}")
            return []
    
    def generate_golden_set(self, num_samples: int = 20) -> List[Dict]:
        """
        Golden Set 생성
        
        Args:
            num_samples: 생성할 샘플 수
        
        Returns:
            Golden set 리스트
        """
        self.connect_db()
        
        print(f"\n💰 피해구제 사례 데이터 Golden Set 생성")
        print(f"샘플 수: {num_samples}개")
        print("=" * 80)
        
        # 데이터베이스에서 피해구제 사례 청크 샘플링
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.chunk_type,
                d.title,
                d.metadata->>'case_sn' as case_sn,
                d.source_org as agency,
                d.doc_type
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type IN ('consumer_counsel_case', 'counsel_case')
                AND c.drop = FALSE
                AND c.embedding IS NOT NULL
                AND c.content IS NOT NULL
                AND LENGTH(c.content) > 50
            ORDER BY RANDOM()
            LIMIT %s
        """, (num_samples,))
        
        samples = cur.fetchall()
        cur.close()
        
        if not samples:
            print("❌ 샘플 데이터를 찾을 수 없습니다.")
            return []
        
        print(f"✅ {len(samples)}개 샘플 추출 완료")
        
        golden_set = []
        
        for idx, (chunk_id, doc_id, content, chunk_type, title, case_sn, agency, doc_type) in enumerate(samples, 1):
            print(f"\n[{idx}/{len(samples)}] 처리 중: {chunk_id[:50]}...")
            
            # 쿼리 생성
            query = self.extract_query_from_chunk(content)
            print(f"  생성된 쿼리: {query}")
            
            # 관련 청크 찾기
            related_chunk_ids = self.find_related_chunks(query, chunk_id, top_k=5)
            print(f"  관련 청크: {len(related_chunk_ids)}개")
            
            # 원본 청크도 포함
            all_chunk_ids = [chunk_id] + related_chunk_ids
            all_doc_ids = [doc_id]
            
            # 관련 문서 ID 수집
            for rel_chunk_id in related_chunk_ids:
                cur = self.conn.cursor()
                cur.execute("SELECT doc_id FROM chunks WHERE chunk_id = %s", (rel_chunk_id,))
                rel_doc = cur.fetchone()
                cur.close()
                if rel_doc and rel_doc[0] not in all_doc_ids:
                    all_doc_ids.append(rel_doc[0])
            
            golden_item = {
                "query": query,
                "expected_chunk_ids": all_chunk_ids[:10],  # 최대 10개
                "expected_doc_ids": all_doc_ids[:5],  # 최대 5개
                "metadata": {
                    "source_chunk_id": chunk_id,
                    "source_doc_id": doc_id,
                    "chunk_type": chunk_type,
                    "doc_type": doc_type,
                    "case_sn": case_sn,
                    "agency": agency,
                    "title": title,
                    "content_preview": content[:200] if content else None
                }
            }
            
            golden_set.append(golden_item)
        
        return golden_set
    
    def save_golden_set(self, golden_set: List[Dict], output_file: Path):
        """Golden Set을 JSON 파일로 저장"""
        output_data = {
            "metadata": {
                "data_type": "compensation",
                "doc_type": "consumer_counsel_case,counsel_case",
                "generated_at": datetime.now().isoformat(),
                "num_samples": len(golden_set)
            },
            "golden_set": golden_set
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Golden Set 저장 완료: {output_file}")
        print(f"   총 {len(golden_set)}개 샘플")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='피해구제 사례 데이터 Golden Set 생성')
    parser.add_argument('--num-samples', type=int, default=20,
                       help='생성할 샘플 수 (기본값: 20)')
    parser.add_argument('--output', type=str, default='golden_set_compensation.json',
                       help='출력 파일 경로 (기본값: golden_set_compensation.json)')
    args = parser.parse_args()
    
    # 환경 변수에서 설정 로드
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # 출력 파일 경로
    script_dir = Path(__file__).parent
    output_file = script_dir / args.output
    
    # Golden Set 생성
    generator = CompensationGoldenSetGenerator(db_config)
    
    try:
        golden_set = generator.generate_golden_set(num_samples=args.num_samples)
        
        if golden_set:
            generator.save_golden_set(golden_set, output_file)
        else:
            print("❌ Golden Set 생성 실패")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        generator.close_db()


if __name__ == "__main__":
    main()
