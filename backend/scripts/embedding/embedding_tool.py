#!/usr/bin/env python3
"""
임베딩 통합 도구
임베딩 상태 확인, 로컬/원격 임베딩 생성 기능을 통합

사용법:
    python backend/scripts/embedding/embedding_tool.py --check
    python backend/scripts/embedding/embedding_tool.py --generate-local
    python backend/scripts/embedding/embedding_tool.py --generate-remote
    python backend/scripts/embedding/embedding_tool.py --generate-remote --api-url http://localhost:8001/embed
"""

import os
import sys
import json
import psycopg2
import argparse
import requests
import torch
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer
from psycopg2.extras import RealDictCursor

# 환경 변수 로드
backend_dir = Path(__file__).parent.parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# DB 연결 정보
DB_CONFIG = {
    'host': os.getenv('DB_HOST', os.getenv('POSTGRES_HOST', 'localhost')),
    'port': int(os.getenv('DB_PORT', os.getenv('POSTGRES_PORT', 5432))),
    'database': os.getenv('DB_NAME', os.getenv('POSTGRES_DB', 'ddoksori')),
    'user': os.getenv('DB_USER', os.getenv('POSTGRES_USER', 'postgres')),
    'password': os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', 'postgres'))
}


class EmbeddingTool:
    """임베딩 통합 도구"""
    
    def __init__(self):
        self.conn = None
        self._connect()
    
    def _connect(self):
        """데이터베이스 연결"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            raise
    
    def check_status(self):
        """임베딩 상태 확인 (기존 check_embedding_status.py 기능)"""
        cur = self.conn.cursor()
        
        print("=" * 70)
        print("똑소리 프로젝트 - 청킹 및 임베딩 결과 확인")
        print("=" * 70)
        
        # 1. 전체 통계
        print("\n📊 전체 통계")
        print("-" * 70)
        
        cur.execute("SELECT COUNT(*) FROM documents")
        doc_count = cur.fetchone()[0]
        print(f"총 문서 수: {doc_count:,}개")
        
        cur.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cur.fetchone()[0]
        print(f"총 청크 수: {chunk_count:,}개")
        
        cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
        embedded_count = cur.fetchone()[0]
        embedding_rate = (embedded_count / chunk_count * 100) if chunk_count > 0 else 0
        print(f"임베딩된 청크 수: {embedded_count:,}개")
        print(f"임베딩 완료율: {embedding_rate:.2f}%")
        
        if embedding_rate < 100:
            print(f"⚠️  아직 {chunk_count - embedded_count:,}개 청크가 임베딩 대기 중입니다.")
        else:
            print("✅ 모든 청크 임베딩 완료!")
        
        # 2. 문서 유형별 통계
        print("\n📁 문서 유형별 통계")
        print("-" * 70)
        cur.execute("""
            SELECT 
                doc_type,
                COUNT(*) as count
            FROM documents
            GROUP BY doc_type
            ORDER BY doc_type
        """)
        print(f"{'문서 유형':<30} {'문서 수':>15}")
        print("-" * 70)
        for row in cur.fetchall():
            print(f"{row[0]:<30} {row[1]:>15,}개")
        
        # 3. 청크 유형별 통계
        print("\n🔖 청크 유형별 통계 (상위 10개)")
        print("-" * 70)
        cur.execute("""
            SELECT 
                chunk_type,
                COUNT(*) as count,
                AVG(content_length) as avg_length
            FROM chunks
            GROUP BY chunk_type
            ORDER BY count DESC
            LIMIT 10
        """)
        print(f"{'청크 유형':<30} {'청크 수':>15} {'평균 길이':>15}")
        print("-" * 70)
        for row in cur.fetchall():
            chunk_type = row[0] if row[0] else '(null)'
            print(f"{chunk_type:<30} {row[1]:>15,}개 {row[2]:>14.0f}자")
        
        # 4. 청크 길이 분포
        print("\n📏 청크 길이 분포")
        print("-" * 70)
        cur.execute("""
            SELECT 
                MIN(content_length) as min_length,
                AVG(content_length) as avg_length,
                MAX(content_length) as max_length,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY content_length) as median_length
            FROM chunks
        """)
        row = cur.fetchone()
        if row and row[0] is not None:
            print(f"최소 길이: {row[0]:,}자")
            print(f"평균 길이: {row[1]:.0f}자")
            print(f"중앙값: {row[2]:.0f}자")
            print(f"최대 길이: {row[3]:,}자")
        else:
            print("데이터가 없습니다.")
        
        # 5. 출처별 통계
        print("\n🏢 출처별 통계")
        print("-" * 70)
        cur.execute("""
            SELECT 
                source_org,
                COUNT(DISTINCT d.doc_id) as document_count,
                COUNT(c.chunk_id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.doc_id = c.doc_id
            GROUP BY source_org
            ORDER BY document_count DESC
        """)
        print(f"{'출처':<30} {'문서 수':>15} {'청크 수':>15}")
        print("-" * 70)
        for row in cur.fetchall():
            source = row[0] if row[0] else '(null)'
            print(f"{source:<30} {row[1]:>15,}개 {row[2]:>15,}개")
        
        # 6. 임베딩 차원 확인
        print("\n🔢 임베딩 벡터 정보")
        print("-" * 70)
        cur.execute("""
            SELECT DISTINCT 
                embedding_model,
                array_length(embedding::real[], 1) as dimension
            FROM chunks
            WHERE embedding IS NOT NULL
            LIMIT 5
        """)
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"모델: {row[0]}, 차원: {row[1]}")
        else:
            print("임베딩된 청크가 없습니다.")
        
        # 7. 샘플 청크 출력
        print("\n📝 샘플 청크 (5개)")
        print("-" * 70)
        cur.execute("""
            SELECT 
                c.chunk_id,
                d.doc_type,
                c.chunk_type,
                c.content_length,
                LEFT(c.content, 100) as content_preview,
                CASE WHEN c.embedding IS NOT NULL THEN 'YES' ELSE 'NO' END as has_embedding
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            ORDER BY RANDOM()
            LIMIT 5
        """)
        for i, row in enumerate(cur.fetchall(), 1):
            print(f"\n[{i}] {row[0]}")
            print(f"    문서 유형: {row[1]}")
            print(f"    청크 타입: {row[2]}")
            print(f"    길이: {row[3]:,}자")
            print(f"    임베딩: {row[5]}")
            print(f"    내용: {row[4]}...")
        
        # 8. 비정상 데이터 확인
        print("\n⚠️  데이터 품질 확인")
        print("-" * 70)
        
        # 너무 짧은 청크
        cur.execute("SELECT COUNT(*) FROM chunks WHERE content_length < 10")
        short_chunks = cur.fetchone()[0]
        if short_chunks > 0:
            print(f"⚠️  10자 미만 청크: {short_chunks:,}개")
        else:
            print("✅ 10자 미만 청크 없음")
        
        # 너무 긴 청크
        cur.execute("SELECT COUNT(*) FROM chunks WHERE content_length > 5000")
        long_chunks = cur.fetchone()[0]
        if long_chunks > 0:
            print(f"⚠️  5000자 초과 청크: {long_chunks:,}개")
        else:
            print("✅ 5000자 초과 청크 없음")
        
        # 임베딩 누락 청크
        cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
        missing_embeddings = cur.fetchone()[0]
        if missing_embeddings > 0:
            print(f"⚠️  임베딩 누락 청크: {missing_embeddings:,}개")
        else:
            print("✅ 모든 청크 임베딩 완료")
        
        print("\n" + "=" * 70)
        print("확인 완료!")
        print("=" * 70)
        
        cur.close()
    
    def generate_local(self, batch_size=8, device='auto'):
        """로컬에서 증분 임베딩 생성 (기존 generate_embeddings_incremental.py 기능)"""
        start_time = datetime.now()
        
        print("=" * 80)
        print("임베딩 생성 시작 (로컬, 증분 처리)")
        print("=" * 80)
        print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        cur = self.conn.cursor()
        
        # 임베딩 필요한 청크 가져오기
        print("\n임베딩이 필요한 청크 조회 중...")
        cur.execute("""
            SELECT chunk_id, content, doc_id
            FROM chunks
            WHERE drop = FALSE AND embedding IS NULL
            ORDER BY doc_id, chunk_index
        """)
        
        chunks = cur.fetchall()
        print(f"✅ {len(chunks):,}개 청크 발견")
        
        if len(chunks) == 0:
            print("\n🎉 모든 청크가 이미 임베딩되었습니다!")
            cur.close()
            return
        
        # 문서 타입별 통계
        cur.execute("""
            SELECT d.doc_type, COUNT(*) as count
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE AND c.embedding IS NULL
            GROUP BY d.doc_type
            ORDER BY count DESC
        """)
        print("\n문서 타입별 임베딩 필요:")
        for doc_type, count in cur.fetchall():
            print(f"  - {doc_type}: {count:,}개")
        
        # 모델 로드
        print("\n모델 로드 중...")
        if device == 'auto':
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            device = torch.device(device)
        
        print(f"  디바이스: {device}")
        
        if device.type == 'cuda':
            print(f"  GPU 이름: {torch.cuda.get_device_name(0)}")
            print(f"  GPU 메모리: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        
        model_name = 'nlpai-lab/KURE-v1'
        print(f"  모델: {model_name}")
        
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name).to(device)
            model.eval()
            print("✅ 모델 로드 완료")
        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            cur.close()
            return
        
        # 배치 크기 자동 설정
        if device.type == 'cuda':
            gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            if gpu_memory_gb >= 16:
                batch_size = max(batch_size, 32)
            elif gpu_memory_gb >= 8:
                batch_size = max(batch_size, 16)
            else:
                batch_size = max(batch_size, 8)
        else:
            batch_size = max(batch_size, 4)
        
        print(f"  배치 크기: {batch_size}")
        
        # 임베딩 생성
        print(f"\n임베딩 생성 중... (총 {len(chunks):,}개)")
        chunk_ids = [c[0] for c in chunks]
        contents = [c[1] for c in chunks]
        
        embeddings = self._generate_embeddings_local(contents, model, tokenizer, device, batch_size)
        
        print(f"\n✅ 임베딩 생성 완료: {len(embeddings):,}개")
        
        # DB 업데이트
        print("\nDB 업데이트 중...")
        updated = 0
        commit_interval = 100
        
        for idx, (chunk_id, embedding) in enumerate(zip(chunk_ids, embeddings), 1):
            try:
                cur.execute("""
                    UPDATE chunks
                    SET embedding = %s, updated_at = NOW()
                    WHERE chunk_id = %s
                """, (embedding.tolist(), chunk_id))
                
                updated += 1
                
                # 주기적 커밋
                if idx % commit_interval == 0:
                    self.conn.commit()
                    progress = (idx / len(chunk_ids)) * 100
                    print(f"  진행률: {idx:,}/{len(chunk_ids):,} ({progress:.1f}%) - 커밋 완료")
            
            except Exception as e:
                print(f"\n⚠️  청크 {chunk_id} 업데이트 실패: {e}")
        
        # 최종 커밋
        self.conn.commit()
        print(f"✅ DB 업데이트 완료: {updated:,}개 청크")
        
        # 검증
        end_time = datetime.now()
        duration = end_time - start_time
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM chunks 
            WHERE drop = FALSE AND embedding IS NULL
        """)
        remaining = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM chunks 
            WHERE drop = FALSE
        """)
        total = cur.fetchone()[0]
        
        print("\n" + "=" * 80)
        print("임베딩 생성 완료")
        print("=" * 80)
        print(f"  - 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  - 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  - 소요 시간: {duration}")
        print(f"  - 생성된 임베딩: {len(embeddings):,}개")
        print(f"  - 업데이트된 청크: {updated:,}개")
        print(f"  - 남은 청크: {remaining:,}개")
        print(f"  - 전체 청크: {total:,}개")
        print(f"  - 임베딩 커버리지: {((total - remaining) / total * 100):.1f}%")
        
        if remaining == 0:
            print("\n🎉 모든 청크에 임베딩이 생성되었습니다!")
        else:
            print(f"\n⚠️  {remaining:,}개 청크가 아직 임베딩되지 않았습니다.")
        
        cur.close()
    
    def _generate_embeddings_local(self, texts, model, tokenizer, device, batch_size=8):
        """로컬에서 배치 임베딩 생성"""
        embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="임베딩 생성", unit="batch"):
            batch = texts[i:i+batch_size]
            
            try:
                inputs = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors='pt'
                ).to(device)
                
                with torch.no_grad():
                    outputs = model(**inputs)
                    batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                
                embeddings.extend(batch_embeddings)
            
            except Exception as e:
                print(f"\n⚠️  배치 {i//batch_size + 1} 처리 중 오류: {e}")
                # 개별 처리로 fallback
                for text in batch:
                    try:
                        inputs = tokenizer(
                            [text],
                            padding=True,
                            truncation=True,
                            max_length=512,
                            return_tensors='pt'
                        ).to(device)
                        
                        with torch.no_grad():
                            outputs = model(**inputs)
                            embedding = outputs.last_hidden_state[0, 0, :].cpu().numpy()
                        
                        embeddings.append(embedding)
                    except Exception as e2:
                        print(f"  개별 처리도 실패: {e2}")
                        embeddings.append(torch.zeros(1024).numpy())
        
        return embeddings
    
    def generate_remote(self, api_url=None, batch_size=32):
        """원격 API로 임베딩 생성 (기존 embed_existing_chunks.py 기능)"""
        if api_url is None:
            api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
        
        print("=" * 80)
        print("🚀 증분 임베딩 생성 (원격 API 방식)")
        print("=" * 80)
        print(f"API URL: {api_url}")
        
        # API 연결 테스트
        print(f"\n🔌 임베딩 API 연결 테스트: {api_url}")
        try:
            base_url = api_url.rsplit('/', 1)[0]
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()
            print(f"✅ API 연결 성공")
        except requests.exceptions.RequestException as e:
            print(f"❌ API 연결 실패: {e}")
            print("\n다음 단계를 확인하세요:")
            print("1. RunPod에서 임베딩 서버 실행:")
            print("   ssh root@[IP] -p [PORT]")
            print("   uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000")
            print("\n2. 로컬에서 SSH 터널 열기:")
            print("   ssh -L 8001:localhost:8000 root@[IP] -p [PORT] -N &")
            return
        
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # 임베딩 필요한 청크 조회
        print("\n🔍 임베딩이 필요한 청크 조회 중...")
        cur.execute("""
            SELECT chunk_id, content, doc_id
            FROM chunks
            WHERE drop = FALSE 
              AND embedding IS NULL
              AND content IS NOT NULL
              AND LENGTH(TRIM(content)) > 0
            ORDER BY doc_id, chunk_index
        """)
        
        chunks = cur.fetchall()
        print(f"✅ {len(chunks):,}개 청크 발견")
        
        if not chunks:
            print("\n✅ 모든 청크가 이미 임베딩되었습니다!")
            self._verify_result(cur)
            cur.close()
            return
        
        # 문서 타입별 통계
        cur.execute("""
            SELECT d.doc_type, COUNT(*) as count
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE 
              AND c.embedding IS NULL
              AND c.content IS NOT NULL
            GROUP BY d.doc_type
            ORDER BY count DESC
        """)
        
        print("\n문서 타입별:")
        for row in cur.fetchall():
            print(f"  - {row['doc_type']}: {row['count']:,}개")
        
        # 임베딩 생성
        print(f"\n🔮 임베딩 생성 시작: {len(chunks):,}개 청크")
        print(f"  배치 크기: {batch_size}")
        
        start_time = datetime.now()
        stats = {
            'chunks_embedded': 0,
            'errors': []
        }
        
        cur2 = self.conn.cursor()
        
        for i in tqdm(range(0, len(chunks), batch_size), desc="임베딩 생성"):
            batch = chunks[i:i + batch_size]
            chunk_ids = [c['chunk_id'] for c in batch]
            texts = [c['content'] for c in batch]
            
            try:
                # 임베딩 생성
                response = requests.post(
                    api_url,
                    json={"texts": texts},
                    timeout=300
                )
                response.raise_for_status()
                embeddings = response.json()['embeddings']
                
                # DB 업데이트
                update_query = """
                    UPDATE chunks
                    SET embedding = %s::vector,
                        updated_at = NOW()
                    WHERE chunk_id = %s
                """
                
                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    cur2.execute(update_query, (embedding, chunk_id))
                
                self.conn.commit()
                stats['chunks_embedded'] += len(batch)
            
            except Exception as e:
                error_msg = f"배치 {i//batch_size + 1} 실패: {e}"
                print(f"\n❌ {error_msg}")
                stats['errors'].append(error_msg)
                self.conn.rollback()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n✅ 임베딩 생성 완료!")
        print(f"  - 처리된 청크: {stats['chunks_embedded']:,}개")
        print(f"  - 소요 시간: {duration}")
        if duration.total_seconds() > 0:
            print(f"  - 평균 속도: {stats['chunks_embedded'] / duration.total_seconds():.1f} 청크/초")
        
        # 결과 검증
        self._verify_result(cur)
        
        # 오류 요약
        if stats['errors']:
            print(f"\n⚠️  오류 발생: {len(stats['errors'])}개")
            for error in stats['errors'][:5]:
                print(f"  - {error}")
            if len(stats['errors']) > 5:
                print(f"  ... 외 {len(stats['errors']) - 5}개")
        
        cur.close()
        cur2.close()
    
    def _verify_result(self, cur):
        """결과 검증"""
        print("\n" + "=" * 80)
        print("🔍 결과 검증")
        print("=" * 80)
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as embedded,
                COUNT(*) - COUNT(embedding) as not_embedded
            FROM chunks
            WHERE drop = FALSE
        """)
        stats = cur.fetchone()
        
        print(f"\n📦 전체 청크:")
        print(f"  전체:         {stats['total']:,}개")
        print(f"  임베딩 완료:  {stats['embedded']:,}개")
        print(f"  임베딩 대기:  {stats['not_embedded']:,}개")
        
        if stats['total'] > 0:
            coverage = (stats['embedded'] / stats['total']) * 100
            print(f"  커버리지:     {coverage:.1f}%")
            
            if stats['not_embedded'] == 0:
                print("\n🎉 모든 청크에 임베딩이 생성되었습니다!")
            else:
                print(f"\n⚠️  {stats['not_embedded']:,}개 청크가 아직 임베딩되지 않았습니다.")
        
        # 문서 타입별 통계
        cur.execute("""
            SELECT 
                d.doc_type,
                COUNT(*) as total,
                COUNT(c.embedding) as embedded
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE
            GROUP BY d.doc_type
            ORDER BY total DESC
        """)
        
        print(f"\n📊 문서 타입별:")
        for row in cur.fetchall():
            coverage = (row['embedded'] / row['total']) * 100 if row['total'] > 0 else 0
            status = "✅" if coverage == 100 else "⚠️"
            print(f"  {status} {row['doc_type']:<30} {row['embedded']:>6}/{row['total']:<6} ({coverage:>5.1f}%)")
    
    def close(self):
        """연결 종료"""
        if self.conn:
            self.conn.close()


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='임베딩 통합 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python embedding_tool.py --check                    # 임베딩 상태 확인
  python embedding_tool.py --generate-local            # 로컬에서 임베딩 생성
  python embedding_tool.py --generate-local --batch-size 16  # 배치 크기 지정
  python embedding_tool.py --generate-remote           # 원격 API로 임베딩 생성
  python embedding_tool.py --generate-remote --api-url http://localhost:8001/embed
        """
    )
    
    parser.add_argument('--check', action='store_true',
                       help='임베딩 상태 확인')
    parser.add_argument('--generate-local', action='store_true',
                       help='로컬에서 증분 임베딩 생성')
    parser.add_argument('--generate-remote', action='store_true',
                       help='원격 API로 임베딩 생성')
    parser.add_argument('--batch-size', type=int, default=8,
                       help='배치 크기 (기본값: 8)')
    parser.add_argument('--device', type=str, default='auto',
                       help='디바이스 (cuda/cpu/auto, 기본값: auto)')
    parser.add_argument('--api-url', type=str, default=None,
                       help='원격 API URL (기본값: EMBED_API_URL 환경 변수 또는 http://localhost:8001/embed)')
    
    args = parser.parse_args()
    
    # 아무 옵션도 없으면 도움말 출력
    if not any([args.check, args.generate_local, args.generate_remote]):
        parser.print_help()
        return
    
    tool = EmbeddingTool()
    
    try:
        if args.check:
            tool.check_status()
        if args.generate_local:
            tool.generate_local(batch_size=args.batch_size, device=args.device)
        if args.generate_remote:
            tool.generate_remote(api_url=args.api_url, batch_size=args.batch_size)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        tool.close()


if __name__ == "__main__":
    main()
