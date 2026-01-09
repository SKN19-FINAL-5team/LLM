#!/usr/bin/env python3
"""
데이터 임베딩 파이프라인 (원격 API 버전)

변환된 JSON 데이터를 PostgreSQL + pgvector에 저장하고
RunPod GPU를 통해 임베딩 생성

Features:
- 변환된 JSON 데이터 읽기
- documents, chunks 테이블에 삽입
- drop=True 청크 자동 제외
- 배치 임베딩 생성 (빈 content 자동 필터링)
- 진행 상황 저장 (중단 시 재개 가능)
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from tqdm import tqdm
from typing import List, Dict, Tuple
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import numpy as np

load_dotenv()

# 스크립트 위치 기준으로 프로젝트 루트 찾기
SCRIPT_DIR = Path(__file__).resolve().parent  # scripts/embedding/
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # ddoksori_demo/
DATA_DIR = PROJECT_ROOT / "backend" / "data"


class EmbeddingPipeline:
    """임베딩 파이프라인 (개선됨 - 텍스트 전처리 추가)"""
    
    def __init__(self, db_config: Dict[str, str], embed_api_url: str, load_only: bool = False):
        """
        Args:
            db_config: PostgreSQL 연결 정보
            embed_api_url: 원격 임베딩 API URL
            load_only: True이면 데이터만 로드하고 임베딩은 생성하지 않음
        """
        self.db_config = db_config
        self.embed_api_url = embed_api_url
        self.load_only = load_only
        self.conn = None
        self.batch_size = 32  # 임베딩 배치 크기
        
        # 통계
        self.stats = {
            'documents': 0,
            'chunks': 0,
            'chunks_skipped': 0,  # drop=True
            'chunks_embedded': 0,
            'chunks_empty': 0,  # 빈 content
            'chunks_preprocessed': 0,  # 전처리된 청크 (신규)
            'low_quality_texts': 0,  # 저품질 텍스트 (사전 필터링, 신규)
            'low_quality_embeddings': 0,  # 저품질 임베딩
            'quality_warnings': [],  # 품질 경고 목록
            'errors': []
        }
        
        # API 연결 테스트 (load_only 모드에서는 실패해도 계속 진행)
        self.api_available = self._test_api_connection(skip_if_failed=load_only)
    
    def _test_api_connection(self, skip_if_failed=False):
        """임베딩 API 연결 테스트"""
        print(f"\n🔌 임베딩 API 연결 테스트: {self.embed_api_url}")
        try:
            base_url = self.embed_api_url.rsplit('/', 1)[0]
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()
            print(f"✅ API 연결 성공: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            if skip_if_failed:
                print(f"⚠️  API 연결 실패 (데이터만 로드 모드): {e}")
                print("   데이터만 로드하고 임베딩은 나중에 생성하세요.")
                return False
            print(f"❌ API 연결 실패: {e}")
            print("\n다음을 확인하세요:")
            print("1. SSH 터널: ssh -L 8001:localhost:8000 [user]@[host] -p [port]")
            print("2. RunPod 서버: uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000")
            raise
    
    def preprocess_text(self, text: str) -> str:
        """
        임베딩 전 텍스트 전처리 (신규)
        
        전처리 항목:
        1. 과도한 공백 정리
        2. 연속된 줄바꿈 정리 (3개 이상 → 2개)
        3. 특수문자 정규화
        4. 앞뒤 공백 제거
        
        Args:
            text: 원본 텍스트
            
        Returns:
            전처리된 텍스트
        """
        if not text:
            return text
        
        import re
        
        # 1. 연속된 공백을 하나로
        text = re.sub(r' +', ' ', text)
        
        # 2. 연속된 줄바꿈 정리 (3개 이상 → 2개)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 3. 탭을 공백으로
        text = text.replace('\t', ' ')
        
        # 4. 특수 유니코드 공백 정규화
        text = text.replace('\u3000', ' ')  # 전각 공백
        text = text.replace('\xa0', ' ')  # Non-breaking space
        
        # 5. 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    def validate_text_quality(self, text: str) -> tuple[bool, str]:
        """
        텍스트 품질 사전 검증 (신규)
        
        임베딩 생성 전에 텍스트 품질을 검사하여 
        저품질 텍스트는 조기에 필터링
        
        검증 항목:
        1. 최소 길이 (20자 이상)
        2. 의미 있는 문자 비율 (30% 이상)
        3. 반복 문자 과다 (같은 문자 80% 이상 반복 금지)
        4. 특정 패턴 (URL만, 숫자만 등)
        
        Args:
            text: 검증할 텍스트
            
        Returns:
            (is_valid, reason): 유효 여부와 이유
        """
        if not text or not text.strip():
            return False, "빈 텍스트"
        
        text = text.strip()
        
        # 1. 최소 길이 체크
        if len(text) < 20:
            return False, f"너무 짧음 ({len(text)}자)"
        
        # 2. 의미 있는 문자 비율
        import re
        meaningful_chars = re.findall(r'[가-힣a-zA-Z0-9]', text)
        if len(meaningful_chars) / len(text) < 0.3:
            return False, f"의미 있는 문자 부족 ({len(meaningful_chars)}/{len(text)})"
        
        # 3. 반복 문자 과다 체크
        from collections import Counter
        char_counts = Counter(text)
        most_common_char, most_common_count = char_counts.most_common(1)[0]
        if most_common_count / len(text) > 0.8:
            return False, f"반복 문자 과다 ('{most_common_char}' {most_common_count}회)"
        
        # 4. URL만으로 구성되었는지
        urls = re.findall(r'https?://[^\s]+', text)
        url_length = sum(len(url) for url in urls)
        if url_length / len(text) > 0.8:
            return False, "URL만으로 구성됨"
        
        # 5. 숫자만으로 구성되었는지
        digits = re.findall(r'\d', text)
        if len(digits) / len(text) > 0.9:
            return False, "숫자만으로 구성됨"
        
        return True, ""
    
    def connect_db(self):
        """PostgreSQL 연결"""
        if self.conn:
            return
        
        print("\n🔌 데이터베이스 연결...")
        self.conn = psycopg2.connect(**self.db_config)
        
        # pgvector 타입 등록 (vector를 자동으로 리스트로 변환)
        try:
            from pgvector.psycopg2 import register_vector
            register_vector(self.conn)
        except ImportError:
            print("  ⚠️  pgvector 패키지가 없습니다. vector 타입을 수동으로 파싱합니다.")
        
        print("✅ 데이터베이스 연결 성공")
    
    def close_db(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def load_json_file(self, file_path: Path) -> Dict:
        """JSON 파일 로드"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def insert_documents(self, documents: List[Dict]):
        """documents 테이블에 문서 삽입"""
        if not documents:
            return
        
        print(f"\n📄 문서 삽입: {len(documents)}개")
        
        with self.conn.cursor() as cur:
            insert_query = """
                INSERT INTO documents (
                    doc_id, doc_type, title, source_org, 
                    category_path, url, metadata
                )
                VALUES %s
                ON CONFLICT (doc_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    metadata = EXCLUDED.metadata
            """
            
            values = [
                (
                    doc['doc_id'],
                    doc['doc_type'],
                    doc['title'],
                    doc.get('source_org'),
                    doc.get('category_path'),
                    doc.get('url'),
                    json.dumps(doc.get('metadata', {}))
                )
                for doc in documents
            ]
            
            execute_values(cur, insert_query, values)
            self.conn.commit()
            self.stats['documents'] += len(documents)
            print(f"✅ {len(documents)}개 문서 삽입 완료")
    
    def insert_chunks(self, doc_id: str, chunks: List[Dict]) -> List[Tuple[str, str]]:
        """
        chunks 테이블에 청크 삽입 (개선됨 - 전처리 및 품질 검증 추가)
        
        Returns:
            List[(chunk_id, content)]: 임베딩 생성이 필요한 청크 목록
        """
        if not chunks:
            return []
        
        # drop=True 청크 필터링
        valid_chunks = [c for c in chunks if not c.get('drop', False)]
        skipped = len(chunks) - len(valid_chunks)
        
        if skipped > 0:
            self.stats['chunks_skipped'] += skipped
        
        if not valid_chunks:
            return []
        
        with self.conn.cursor() as cur:
            insert_query = """
                INSERT INTO chunks (
                    chunk_id, doc_id, chunk_index, chunk_total,
                    chunk_type, content, content_length, drop
                )
                VALUES %s
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content = EXCLUDED.content
            """
            
            values = [
                (
                    chunk['chunk_id'],
                    doc_id,
                    chunk['chunk_index'],
                    chunk['chunk_total'],
                    chunk['chunk_type'],
                    chunk['content'],
                    chunk['content_length'],
                    chunk.get('drop', False)
                )
                for chunk in valid_chunks
            ]
            
            execute_values(cur, insert_query, values)
            self.conn.commit()
            self.stats['chunks'] += len(valid_chunks)
        
        # 임베딩 생성이 필요한 청크 준비 (전처리 및 품질 검증 적용)
        chunks_to_embed = []
        
        for chunk in valid_chunks:
            content = chunk['content']
            
            # 빈 content 체크
            if not content or not content.strip():
                self.stats['chunks_empty'] += 1
                continue
            
            # 텍스트 전처리 (신규)
            preprocessed_content = self.preprocess_text(content)
            self.stats['chunks_preprocessed'] += 1
            
            # 텍스트 품질 사전 검증 (신규)
            is_valid, reason = self.validate_text_quality(preprocessed_content)
            
            if not is_valid:
                # 저품질 텍스트는 임베딩 생성하지 않음
                self.stats['low_quality_texts'] += 1
                warning_msg = (
                    f"저품질 텍스트 필터링: {chunk['chunk_id']}\n"
                    f"  이유: {reason}\n"
                    f"  원본 길이: {len(content)}자\n"
                    f"  미리보기: {content[:100]}..."
                )
                self.stats['quality_warnings'].append(warning_msg)
                
                # 처음 5개만 출력
                if self.stats['low_quality_texts'] <= 5:
                    print(f"\n⚠️  {warning_msg}")
                
                continue
            
            chunks_to_embed.append((chunk['chunk_id'], preprocessed_content))
        
        return chunks_to_embed
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        원격 API를 통해 임베딩 생성
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        try:
            response = requests.post(
                self.embed_api_url,
                json={"texts": texts},
                timeout=300  # 5분 타임아웃
            )
            response.raise_for_status()
            return response.json()['embeddings']
        except requests.exceptions.RequestException as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            raise
    
    def is_low_quality_embedding(self, embedding: List[float]) -> Tuple[bool, str]:
        """
        저품질 임베딩 감지
        
        Args:
            embedding: 임베딩 벡터 (리스트, numpy 배열, 또는 문자열)
            
        Returns:
            (is_low_quality, reason): 저품질 여부와 이유
        """
        # 벡터 변환 (데이터베이스에서 문자열로 올 수 있음)
        if isinstance(embedding, str):
            # PostgreSQL vector 타입이 문자열로 반환되는 경우 파싱
            # 형식: "[0.1,0.2,0.3]" 또는 "np.str_('[0.1,0.2,0.3]')"
            embedding_str = embedding.strip()
            
            # numpy string wrapper 제거
            if embedding_str.startswith('np.str_('):
                embedding_str = embedding_str[8:-1]  # "np.str_(" 와 ")" 제거
            
            # 작은따옴표 제거
            embedding_str = embedding_str.strip("'\"")
            
            # 대괄호 제거하고 쉼표로 분리
            embedding_str = embedding_str.strip('[]')
            values = [x.strip() for x in embedding_str.split(',') if x.strip()]
            
            try:
                embedding = [float(x) for x in values]
            except ValueError as e:
                return True, f"벡터 파싱 실패: {str(e)[:50]}"
        
        try:
            vec = np.array(embedding, dtype=float)
        except Exception as e:
            return True, f"numpy 배열 변환 실패: {str(e)[:50]}"
        
        # 체크 1: Norm이 너무 작음 (의미 없는 벡터)
        norm = np.linalg.norm(vec)
        if norm < 0.1:
            return True, f"norm이 너무 작음 ({norm:.4f})"
        
        # 체크 2: 분산이 너무 작음 (모든 값이 유사)
        variance = np.var(vec)
        if variance < 0.001:
            return True, f"분산이 너무 작음 ({variance:.6f})"
        
        # 체크 3: NaN이나 Inf 값 존재
        if np.isnan(vec).any() or np.isinf(vec).any():
            return True, "NaN 또는 Inf 값 포함"
        
        # 체크 4: 벡터가 너무 희소함 (대부분의 값이 0에 가까움)
        near_zero = np.abs(vec) < 0.001
        if near_zero.sum() / len(vec) > 0.9:
            return True, f"희소 벡터 ({near_zero.sum()}/{len(vec)} 값이 ~0)"
        
        return False, ""
    
    def embed_chunks(self, chunks_to_embed: List[Tuple[str, str]]):
        """청크에 대한 임베딩 생성 및 품질 체크"""
        if not chunks_to_embed:
            return
        
        print(f"\n🔮 임베딩 생성: {len(chunks_to_embed)}개 청크")
        
        # 배치 처리
        with self.conn.cursor() as cur:
            for i in tqdm(range(0, len(chunks_to_embed), self.batch_size)):
                batch = chunks_to_embed[i:i + self.batch_size]
                chunk_ids = [c[0] for c in batch]
                texts = [c[1] for c in batch]
                
                try:
                    # 임베딩 생성
                    embeddings = self.generate_embeddings(texts)
                    
                    # DB 업데이트 및 품질 체크
                    update_query = """
                        UPDATE chunks
                        SET embedding = %s::vector
                        WHERE chunk_id = %s
                    """
                    
                    for chunk_id, embedding, text in zip(chunk_ids, embeddings, texts):
                        # 품질 체크
                        is_low_quality, reason = self.is_low_quality_embedding(embedding)
                        
                        if is_low_quality:
                            self.stats['low_quality_embeddings'] += 1
                            warning_msg = (
                                f"저품질 임베딩 감지: {chunk_id}\n"
                                f"  이유: {reason}\n"
                                f"  텍스트 길이: {len(text)}자\n"
                                f"  텍스트 미리보기: {text[:100]}..."
                            )
                            self.stats['quality_warnings'].append(warning_msg)
                            
                            # 상세 경고는 첫 5개만 출력
                            if self.stats['low_quality_embeddings'] <= 5:
                                print(f"\n⚠️  {warning_msg}")
                        
                        # 임베딩 저장 (저품질이어도 일단 저장)
                        cur.execute(update_query, (embedding, chunk_id))
                    
                    self.conn.commit()
                    self.stats['chunks_embedded'] += len(batch)
                    
                except Exception as e:
                    error_msg = f"배치 {i//self.batch_size + 1} 임베딩 실패: {e}"
                    print(f"❌ {error_msg}")
                    self.stats['errors'].append(error_msg)
                    self.conn.rollback()
        
        print(f"✅ {self.stats['chunks_embedded']}개 청크 임베딩 완료")
        
        # 저품질 임베딩 요약
        if self.stats['low_quality_embeddings'] > 0:
            quality_rate = (self.stats['low_quality_embeddings'] / self.stats['chunks_embedded']) * 100
            print(f"⚠️  저품질 임베딩: {self.stats['low_quality_embeddings']}개 ({quality_rate:.1f}%)")
    
    def process_json_file(self, json_file: Path):
        """JSON 파일 처리"""
        print("\n" + "=" * 80)
        print(f"파일 처리: {json_file.name}")
        print("=" * 80)
        
        # JSON 로드
        data = self.load_json_file(json_file)
        documents = data.get('documents', [])
        
        if not documents:
            print("⚠️  문서가 없습니다. 스킵.")
            return
        
        print(f"📊 로드된 문서: {len(documents)}개")
        
        # 문서 삽입
        self.insert_documents(documents)
        
        # 각 문서의 청크 처리
        all_chunks_to_embed = []
        
        for doc in tqdm(documents, desc="청크 삽입"):
            chunks = doc.get('chunks', [])
            chunks_to_embed = self.insert_chunks(doc['doc_id'], chunks)
            all_chunks_to_embed.extend(chunks_to_embed)
        
        print(f"✅ 청크 삽입 완료: {self.stats['chunks']}개")
        if self.stats['chunks_skipped'] > 0:
            print(f"⏭️  스킵된 청크 (drop=True): {self.stats['chunks_skipped']}개")
        if self.stats['chunks_empty'] > 0:
            print(f"⚠️  빈 content 청크: {self.stats['chunks_empty']}개")
        
        # 임베딩 생성
        if self.load_only:
            print(f"📝 데이터만 로드 모드: {len(all_chunks_to_embed):,}개 청크가 임베딩 대기 중입니다.")
            print("   나중에 다음 명령어로 임베딩을 생성하세요:")
            print("   conda run -n dsr python backend/scripts/embedding/embedding_tool.py --generate-local")
        elif all_chunks_to_embed:
            if not self.api_available:
                print("⚠️  API가 사용 불가능합니다. 데이터만 로드되었습니다.")
                print("   나중에 다음 명령어로 임베딩을 생성하세요:")
                print("   conda run -n dsr python backend/scripts/embedding/embedding_tool.py --generate-local")
            else:
                self.embed_chunks(all_chunks_to_embed)
        else:
            print("⚠️  임베딩할 청크가 없습니다.")
    
    def process_all_files(self, data_dir: Path = None):
        """모든 JSON 파일 처리"""
        if data_dir is None:
            data_dir = DATA_DIR / "transformed"
        
        print("\n" + "=" * 80)
        print(f"데이터 디렉토리: {data_dir}")
        print("=" * 80)
        
        # JSON 파일 찾기 (transformation_summary.json 제외)
        json_files = [
            f for f in data_dir.glob('*.json')
            if f.name != 'transformation_summary.json' and f.name != 'validation_result.json'
        ]
        
        if not json_files:
            print(f"❌ {data_dir}에 JSON 파일이 없습니다.")
            return
        
        print(f"📁 발견된 파일: {len(json_files)}개")
        for f in json_files:
            print(f"  - {f.name}")
        
        # DB 연결
        self.connect_db()
        
        # 각 파일 처리
        for json_file in json_files:
            try:
                self.process_json_file(json_file)
            except Exception as e:
                error_msg = f"{json_file.name} 처리 실패: {e}"
                print(f"❌ {error_msg}")
                self.stats['errors'].append(error_msg)
                import traceback
                traceback.print_exc()
        
        # 최종 통계
        self.print_stats()
        
        # 연결 종료
        self.close_db()
    
    def print_stats(self):
        """통계 출력 (개선됨)"""
        print("\n" + "=" * 80)
        print("📊 처리 완료 통계")
        print("=" * 80)
        print(f"문서:                 {self.stats['documents']:,}개")
        print(f"청크 (삽입):          {self.stats['chunks']:,}개")
        print(f"청크 (스킵/drop):     {self.stats['chunks_skipped']:,}개")
        print(f"청크 (빈 content):    {self.stats['chunks_empty']:,}개")
        
        # 전처리 통계 (신규)
        print(f"\n[전처리]")
        print(f"전처리 완료:          {self.stats['chunks_preprocessed']:,}개")
        print(f"저품질 텍스트 필터:   {self.stats['low_quality_texts']:,}개")
        if self.stats['chunks_preprocessed'] > 0:
            filter_rate = (self.stats['low_quality_texts'] / self.stats['chunks_preprocessed']) * 100
            print(f"  필터링 비율:        {filter_rate:.1f}%")
        
        # 임베딩 통계
        print(f"\n[임베딩]")
        print(f"임베딩 생성:          {self.stats['chunks_embedded']:,}개")
        
        # 품질 통계
        if self.stats['chunks_embedded'] > 0:
            quality_rate = (self.stats['low_quality_embeddings'] / self.stats['chunks_embedded']) * 100
            print(f"저품질 임베딩:        {self.stats['low_quality_embeddings']:,}개 ({quality_rate:.1f}%)")
        
        if self.stats['quality_warnings']:
            print(f"\n⚠️  품질 경고: {len(self.stats['quality_warnings'])}개")
            # 처음 3개만 출력
            for warning in self.stats['quality_warnings'][:3]:
                print(f"  {warning}")
            if len(self.stats['quality_warnings']) > 3:
                print(f"  ... 외 {len(self.stats['quality_warnings']) - 3}개")
        
        if self.stats['errors']:
            print(f"\n❌ 오류: {len(self.stats['errors'])}개")
            for error in self.stats['errors'][:10]:  # 최대 10개만 출력
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... 외 {len(self.stats['errors']) - 10}개")
    
    def verify_data(self):
        """데이터 삽입 및 임베딩 확인"""
        print("\n" + "=" * 80)
        print("🔍 데이터 검증")
        print("=" * 80)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 문서 통계
            cur.execute("""
                SELECT doc_type, COUNT(*) as count
                FROM documents
                GROUP BY doc_type
                ORDER BY count DESC
            """)
            print("\n📄 문서 통계:")
            for row in cur.fetchall():
                print(f"  {row['doc_type']}: {row['count']:,}개")
            
            # 청크 통계
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(embedding) as embedded,
                    COUNT(*) - COUNT(embedding) as not_embedded
                FROM chunks
                WHERE drop = FALSE
            """)
            chunk_stats = cur.fetchone()
            print(f"\n📦 청크 통계:")
            print(f"  전체:           {chunk_stats['total']:,}개")
            print(f"  임베딩 완료:    {chunk_stats['embedded']:,}개")
            print(f"  임베딩 미완료:  {chunk_stats['not_embedded']:,}개")
            
            if chunk_stats['total'] > 0:
                embed_rate = (chunk_stats['embedded'] / chunk_stats['total']) * 100
                print(f"  임베딩 비율:    {embed_rate:.1f}%")
            
            # chunk_type별 통계
            cur.execute("""
                SELECT chunk_type, COUNT(*) as count
                FROM chunks
                WHERE drop = FALSE
                GROUP BY chunk_type
                ORDER BY count DESC
                LIMIT 10
            """)
            print(f"\n🏷️  청크 타입별 (상위 10개):")
            for row in cur.fetchall():
                print(f"  {row['chunk_type']}: {row['count']:,}개")
            
            # drop된 청크
            cur.execute("SELECT COUNT(*) FROM chunks WHERE drop = TRUE")
            drop_result = cur.fetchone()
            dropped = drop_result['count'] if drop_result else 0
            if dropped > 0:
                print(f"\n⏭️  제외된 청크 (drop=True): {dropped:,}개")
            
            # 임베딩되지 않은 청크 샘플 (5개)
            if chunk_stats['not_embedded'] > 0:
                cur.execute("""
                    SELECT chunk_id, doc_id, content_length, 
                           LEFT(content, 50) as content_preview
                    FROM chunks
                    WHERE embedding IS NULL AND drop = FALSE
                    LIMIT 5
                """)
                print(f"\n⚠️  임베딩 미완료 청크 샘플:")
                for row in cur.fetchall():
                    print(f"  {row['chunk_id']}")
                    print(f"    길이: {row['content_length']}자")
                    print(f"    내용: {row['content_preview']}...")
            
            # 임베딩 품질 통계 (샘플링)
            if chunk_stats['embedded'] > 0:
                print(f"\n🔍 임베딩 품질 분석 (샘플 100개):")
                cur.execute("""
                    SELECT embedding
                    FROM chunks
                    WHERE embedding IS NOT NULL AND drop = FALSE
                    ORDER BY RANDOM()
                    LIMIT 100
                """)
                
                low_quality_count = 0
                quality_issues = []
                
                for row in cur.fetchall():
                    embedding = row['embedding']
                    is_low_quality, reason = self.is_low_quality_embedding(embedding)
                    if is_low_quality:
                        low_quality_count += 1
                        quality_issues.append(reason)
                
                sample_size = min(100, chunk_stats['embedded'])
                print(f"  샘플 크기:          {sample_size}개")
                print(f"  저품질 임베딩:      {low_quality_count}개")
                
                if low_quality_count > 0:
                    quality_rate = (low_quality_count / sample_size) * 100
                    print(f"  저품질 비율:        {quality_rate:.1f}%")
                    
                    # 이슈별 집계
                    from collections import Counter
                    issue_counter = Counter(quality_issues)
                    print(f"  주요 이슈:")
                    for issue, count in issue_counter.most_common(3):
                        print(f"    - {issue}: {count}개")
                else:
                    print(f"  품질 상태:          양호 ✅")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='데이터 임베딩 파이프라인')
    parser.add_argument('--load-only', action='store_true', 
                       help='데이터만 로드하고 임베딩은 생성하지 않음')
    args = parser.parse_args()
    
    # 환경 변수에서 설정 로드
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    print("=" * 80)
    if args.load_only:
        print("📥 데이터 로드만 수행 (임베딩 제외)")
    else:
        print("🚀 임베딩 파이프라인 시작")
    print("=" * 80)
    print(f"데이터베이스: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f"임베딩 API: {embed_api_url}")
    
    # 파이프라인 실행
    try:
        pipeline = EmbeddingPipeline(db_config, embed_api_url, load_only=args.load_only)
        pipeline.process_all_files()
        
        # 검증
        pipeline.connect_db()
        pipeline.verify_data()
        pipeline.close_db()
        
        print("\n" + "=" * 80)
        print("✅ 모든 작업 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
