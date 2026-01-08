"""
SPLADE Sparse Vector 사전 인코딩 파이프라인
모든 chunk에 대해 SPLADE sparse vector를 생성하여 RDB에 저장
"""

import os
import sys
import json
import psycopg2
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np

# 프로젝트 루트 경로 추가
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# 환경 변수 로드
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# SPLADE 모듈 import
try:
    from scripts.splade.test_splade_naver import NaverSPLADERetriever
    from scripts.splade.test_splade_remote import RemoteSPLADERetriever
    SPLADE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  SPLADE 모듈을 찾을 수 없습니다: {e}")
    SPLADE_AVAILABLE = False


class SPLADEEncodingPipeline:
    """SPLADE sparse vector 인코딩 파이프라인"""
    
    def __init__(
        self,
        db_config: Dict,
        batch_size: int = 32,
        use_remote: bool = False,
        api_url: str = None,
        device: str = None
    ):
        """
        Args:
            db_config: 데이터베이스 연결 설정
            batch_size: 배치 크기 (기본값: 32)
            use_remote: 원격 API 서버 사용 여부
            api_url: 원격 API URL (use_remote=True일 때)
            device: 로컬 모드에서 사용할 디바이스 ('cuda' 또는 'cpu')
        """
        self.db_config = db_config
        self.batch_size = batch_size
        self.conn = None
        self.splade_retriever = None
        
        # SPLADE Retriever 초기화
        if use_remote:
            if api_url is None:
                api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
            try:
                self.splade_retriever = RemoteSPLADERetriever(api_url=api_url)
                print(f"✅ 원격 SPLADE API 서버 사용: {api_url}")
            except Exception as e:
                print(f"⚠️  원격 API 서버 연결 실패: {e}")
                print("   로컬 모드로 전환 시도...")
                use_remote = False
        
        if not use_remote:
            try:
                self.splade_retriever = NaverSPLADERetriever(device=device)
                self.splade_retriever.load_model()
                print(f"✅ 로컬 SPLADE 모델 사용: device={self.splade_retriever.device}")
            except Exception as e:
                print(f"❌ SPLADE 모델 로드 실패: {e}")
                raise RuntimeError("SPLADE 모델을 사용할 수 없습니다.")
    
    def connect_db(self):
        """데이터베이스 연결"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False
    
    def get_chunks_to_encode(
        self,
        doc_type: Optional[str] = None,
        limit: Optional[int] = None,
        skip_encoded: bool = True
    ) -> List[Tuple[str, str]]:
        """
        인코딩이 필요한 chunk 목록 가져오기
        
        Args:
            doc_type: 문서 타입 필터 (None이면 전체)
            limit: 최대 개수 (None이면 전체)
            skip_encoded: 이미 인코딩된 chunk 건너뛰기
        
        Returns:
            (chunk_id, content) 튜플 리스트
        """
        self.connect_db()
        cur = self.conn.cursor()
        
        where_clauses = []
        params = []
        
        if skip_encoded:
            where_clauses.append("(splade_encoded IS NULL OR splade_encoded = FALSE)")
        
        if doc_type:
            where_clauses.append("d.doc_type = %s")
            params.append(doc_type)
        
        where_clauses.append("c.drop = FALSE")
        where_clauses.append("c.content IS NOT NULL")
        where_clauses.append("LENGTH(TRIM(c.content)) > 0")
        
        where_sql = " AND ".join(where_clauses)
        
        limit_sql = ""
        if limit:
            limit_sql = f"LIMIT {limit}"
        
        sql = f"""
            SELECT c.chunk_id, c.content
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE {where_sql}
            ORDER BY c.chunk_id
            {limit_sql}
        """
        
        cur.execute(sql, params)
        results = cur.fetchall()
        cur.close()
        
        return results
    
    def sparse_vector_to_jsonb(self, sparse_vec: np.ndarray, threshold: float = 0.0) -> Dict[str, float]:
        """
        Sparse vector를 JSONB 형식으로 변환
        0이 아닌 값만 저장하여 공간 효율적
        
        Args:
            sparse_vec: Sparse vector (numpy array)
            threshold: 저장할 최소 가중치 임계값
        
        Returns:
            {token_id: weight} 형태의 딕셔너리
        """
        # 0이 아닌 인덱스 찾기
        non_zero_indices = np.where(sparse_vec > threshold)[0]
        
        # JSONB 형식으로 변환 (문자열 키로 저장)
        result = {}
        for idx in non_zero_indices:
            weight = float(sparse_vec[idx])
            if weight > threshold:
                result[str(idx)] = weight
        
        return result
    
    def encode_batch(self, chunks: List[Tuple[str, str]]) -> List[Dict]:
        """
        배치로 chunk 인코딩
        
        Args:
            chunks: (chunk_id, content) 튜플 리스트
        
        Returns:
            인코딩 결과 리스트 [{chunk_id, sparse_vector, success}, ...]
        """
        if not chunks:
            return []
        
        chunk_ids = [c[0] for c in chunks]
        contents = [c[1] for c in chunks]
        
        results = []
        
        try:
            # 배치 인코딩
            if hasattr(self.splade_retriever, 'encode_documents_batch'):
                # RemoteSPLADERetriever의 배치 인코딩 사용
                sparse_vectors = self.splade_retriever.encode_documents_batch(contents)
            else:
                # NaverSPLADERetriever의 개별 인코딩 사용
                sparse_vectors = []
                for content in contents:
                    try:
                        vec = self.splade_retriever.encode_document(content)
                        sparse_vectors.append(vec)
                    except Exception as e:
                        print(f"  ⚠️  인코딩 실패 (chunk_id 일부): {e}")
                        sparse_vectors.append(None)
            
            # 결과 변환
            for chunk_id, sparse_vec in zip(chunk_ids, sparse_vectors):
                if sparse_vec is None:
                    results.append({
                        'chunk_id': chunk_id,
                        'sparse_vector': None,
                        'success': False
                    })
                    continue
                
                # JSONB 형식으로 변환
                sparse_jsonb = self.sparse_vector_to_jsonb(sparse_vec)
                
                results.append({
                    'chunk_id': chunk_id,
                    'sparse_vector': sparse_jsonb,
                    'success': True
                })
        
        except Exception as e:
            print(f"  ⚠️  배치 인코딩 오류: {e}")
            # 개별 인코딩으로 폴백
            for chunk_id, content in chunks:
                try:
                    sparse_vec = self.splade_retriever.encode_document(content)
                    sparse_jsonb = self.sparse_vector_to_jsonb(sparse_vec)
                    results.append({
                        'chunk_id': chunk_id,
                        'sparse_vector': sparse_jsonb,
                        'success': True
                    })
                except Exception as e2:
                    print(f"  ⚠️  개별 인코딩 실패 (chunk_id: {chunk_id[:50]}...): {e2}")
                    results.append({
                        'chunk_id': chunk_id,
                        'sparse_vector': None,
                        'success': False
                    })
        
        return results
    
    def save_encoded_vectors(self, encoded_results: List[Dict]):
        """
        인코딩된 sparse vector를 DB에 저장
        
        Args:
            encoded_results: encode_batch()의 결과
        """
        if not encoded_results:
            return
        
        self.connect_db()
        cur = self.conn.cursor()
        
        model_name = 'naver/splade-v3'
        if hasattr(self.splade_retriever, 'model_name'):
            model_name = self.splade_retriever.model_name
        
        success_count = 0
        fail_count = 0
        
        for result in encoded_results:
            chunk_id = result['chunk_id']
            sparse_vector = result['sparse_vector']
            success = result['success']
            
            if success and sparse_vector:
                try:
                    # JSONB로 변환하여 저장
                    sparse_jsonb = json.dumps(sparse_vector)
                    
                    cur.execute("""
                        UPDATE chunks
                        SET 
                            splade_sparse_vector = %s::jsonb,
                            splade_model = %s,
                            splade_encoded = TRUE,
                            updated_at = NOW()
                        WHERE chunk_id = %s
                    """, (sparse_jsonb, model_name, chunk_id))
                    
                    success_count += 1
                except Exception as e:
                    print(f"  ⚠️  DB 저장 실패 (chunk_id: {chunk_id[:50]}...): {e}")
                    fail_count += 1
            else:
                # 실패한 경우 플래그만 업데이트 (나중에 재시도 가능)
                try:
                    cur.execute("""
                        UPDATE chunks
                        SET splade_encoded = FALSE
                        WHERE chunk_id = %s
                    """, (chunk_id,))
                    fail_count += 1
                except Exception as e:
                    print(f"  ⚠️  플래그 업데이트 실패 (chunk_id: {chunk_id[:50]}...): {e}")
        
        self.conn.commit()
        cur.close()
        
        return success_count, fail_count
    
    def encode_all_chunks(
        self,
        doc_type: Optional[str] = None,
        limit: Optional[int] = None,
        resume: bool = True
    ):
        """
        모든 chunk에 대해 SPLADE 인코딩 수행
        
        Args:
            doc_type: 문서 타입 필터
            limit: 최대 처리 개수
            resume: 이미 인코딩된 chunk 건너뛰기
        """
        print("\n" + "=" * 80)
        print("SPLADE Sparse Vector 인코딩 시작")
        print("=" * 80)
        
        # 인코딩 대상 chunk 가져오기
        chunks = self.get_chunks_to_encode(
            doc_type=doc_type,
            limit=limit,
            skip_encoded=resume
        )
        
        total_chunks = len(chunks)
        if total_chunks == 0:
            print("✅ 인코딩할 chunk가 없습니다.")
            return
        
        print(f"\n📊 인코딩 대상: {total_chunks}개 chunk")
        if doc_type:
            print(f"   문서 타입: {doc_type}")
        
        # 배치 처리
        total_success = 0
        total_fail = 0
        
        with tqdm(total=total_chunks, desc="인코딩 진행") as pbar:
            for i in range(0, total_chunks, self.batch_size):
                batch = chunks[i:i + self.batch_size]
                
                # 배치 인코딩
                encoded_results = self.encode_batch(batch)
                
                # DB 저장
                success_count, fail_count = self.save_encoded_vectors(encoded_results)
                
                total_success += success_count
                total_fail += fail_count
                
                pbar.update(len(batch))
                pbar.set_postfix({
                    '성공': total_success,
                    '실패': total_fail,
                    '진행률': f"{total_success + total_fail}/{total_chunks}"
                })
        
        # 최종 통계
        print("\n" + "=" * 80)
        print("인코딩 완료")
        print("=" * 80)
        print(f"✅ 성공: {total_success}개")
        print(f"❌ 실패: {total_fail}개")
        print(f"📊 총 처리: {total_success + total_fail}개 / {total_chunks}개")
        
        if total_fail > 0:
            print(f"\n⚠️  실패한 chunk는 나중에 재시도할 수 있습니다.")
    
    def get_statistics(self) -> Dict:
        """인코딩 통계 정보 조회"""
        self.connect_db()
        cur = self.conn.cursor()
        
        # 전체 통계
        cur.execute("""
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(CASE WHEN splade_encoded = TRUE THEN 1 END) as encoded_chunks,
                COUNT(CASE WHEN splade_encoded = FALSE OR splade_encoded IS NULL THEN 1 END) as unencoded_chunks
            FROM chunks
            WHERE drop = FALSE
        """)
        total_stats = cur.fetchone()
        
        # 문서 타입별 통계
        cur.execute("""
            SELECT 
                d.doc_type,
                COUNT(*) as total,
                COUNT(CASE WHEN c.splade_encoded = TRUE THEN 1 END) as encoded
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE
            GROUP BY d.doc_type
            ORDER BY total DESC
        """)
        doc_type_stats = cur.fetchall()
        
        cur.close()
        
        return {
            'total': {
                'total_chunks': total_stats[0],
                'encoded_chunks': total_stats[1],
                'unencoded_chunks': total_stats[2],
                'encode_rate': (total_stats[1] / total_stats[0] * 100) if total_stats[0] > 0 else 0
            },
            'by_doc_type': [
                {
                    'doc_type': row[0],
                    'total': row[1],
                    'encoded': row[2],
                    'rate': (row[2] / row[1] * 100) if row[1] > 0 else 0
                }
                for row in doc_type_stats
            ]
        }


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SPLADE Sparse Vector 인코딩 파이프라인')
    parser.add_argument('--doc-type', type=str, help='문서 타입 필터 (예: law, criteria_*)')
    parser.add_argument('--limit', type=int, help='최대 처리 개수')
    parser.add_argument('--batch-size', type=int, default=32, help='배치 크기 (기본값: 32)')
    parser.add_argument('--remote', action='store_true', help='원격 API 서버 사용')
    parser.add_argument('--api-url', type=str, help='원격 API URL')
    parser.add_argument('--device', type=str, choices=['cuda', 'cpu'], help='로컬 모드 디바이스')
    parser.add_argument('--no-resume', action='store_true', help='이미 인코딩된 chunk도 재인코딩')
    parser.add_argument('--stats-only', action='store_true', help='통계만 조회하고 종료')
    
    args = parser.parse_args()
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # 파이프라인 초기화
    try:
        pipeline = SPLADEEncodingPipeline(
            db_config=db_config,
            batch_size=args.batch_size,
            use_remote=args.remote,
            api_url=args.api_url,
            device=args.device
        )
    except Exception as e:
        print(f"❌ 파이프라인 초기화 실패: {e}")
        sys.exit(1)
    
    # 통계만 조회
    if args.stats_only:
        stats = pipeline.get_statistics()
        print("\n📊 SPLADE 인코딩 통계")
        print("=" * 80)
        print(f"전체 chunk: {stats['total']['total_chunks']}개")
        print(f"인코딩 완료: {stats['total']['encoded_chunks']}개")
        print(f"인코딩 미완료: {stats['total']['unencoded_chunks']}개")
        print(f"인코딩 완료율: {stats['total']['encode_rate']:.1f}%")
        print("\n문서 타입별:")
        for dt in stats['by_doc_type']:
            print(f"  {dt['doc_type']}: {dt['encoded']}/{dt['total']} ({dt['rate']:.1f}%)")
        return
    
    # 인코딩 수행
    pipeline.encode_all_chunks(
        doc_type=args.doc_type,
        limit=args.limit,
        resume=not args.no_resume
    )
    
    # 최종 통계 출력
    stats = pipeline.get_statistics()
    print("\n📊 최종 통계")
    print("=" * 80)
    print(f"인코딩 완료율: {stats['total']['encode_rate']:.1f}%")
    
    # 연결 종료
    if pipeline.conn:
        pipeline.conn.close()


if __name__ == "__main__":
    main()
