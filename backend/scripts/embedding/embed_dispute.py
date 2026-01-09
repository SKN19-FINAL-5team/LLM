#!/usr/bin/env python3
"""
분쟁조정 사례 데이터 임베딩 파이프라인

분쟁조정 사례 데이터(doc_type='mediation_case')만 처리하는 임베딩 스크립트
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

# 프로젝트 루트를 경로에 추가
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "scripts" / "embedding"))

from embed_data_remote import EmbeddingPipeline, DATA_DIR

load_dotenv()


class DisputeEmbeddingPipeline(EmbeddingPipeline):
    """분쟁조정 사례 데이터만 처리하는 임베딩 파이프라인"""
    
    def process_all_files(self, data_dir: Path = None):
        """분쟁조정 사례 데이터 파일만 처리"""
        if data_dir is None:
            data_dir = DATA_DIR / "dispute_resolution"
        
        print("\n" + "=" * 80)
        print("⚖️  분쟁조정 사례 데이터 임베딩 파이프라인")
        print("=" * 80)
        print(f"데이터 디렉토리: {data_dir}")
        print(f"필터: doc_type = 'mediation_case'")
        
        # JSONL 파일 찾기
        jsonl_files = list(data_dir.glob('*.jsonl'))
        
        if not jsonl_files:
            print(f"❌ {data_dir}에 JSONL 파일이 없습니다.")
            return
        
        print(f"📁 발견된 파일: {len(jsonl_files)}개")
        for f in jsonl_files:
            print(f"  - {f.name}")
        
        # DB 연결
        self.connect_db()
        
        # 각 파일 처리
        for jsonl_file in jsonl_files:
            try:
                self.process_jsonl_file(jsonl_file)
            except Exception as e:
                error_msg = f"{jsonl_file.name} 처리 실패: {e}"
                print(f"❌ {error_msg}")
                self.stats['errors'].append(error_msg)
                import traceback
                traceback.print_exc()
        
        # 최종 통계
        self.print_stats()
        
        # 연결 종료
        self.close_db()
    
    def process_jsonl_file(self, jsonl_file: Path):
        """JSONL 파일 처리 (분쟁조정 사례 데이터 형식)"""
        print("\n" + "=" * 80)
        print(f"파일 처리: {jsonl_file.name}")
        print("=" * 80)
        
        # JSONL 로드
        documents = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    # doc_type이 'mediation_case'인 것만 필터링
                    if doc.get('doc_type') == 'mediation_case':
                        documents.append(doc)
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON 파싱 오류: {e}")
                    continue
        
        if not documents:
            print("⚠️  분쟁조정 사례 문서가 없습니다. 스킵.")
            return
        
        print(f"📊 로드된 분쟁조정 사례 문서: {len(documents)}개")
        
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


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='분쟁조정 사례 데이터 임베딩 파이프라인')
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
        print("📥 분쟁조정 사례 데이터 로드만 수행 (임베딩 제외)")
    else:
        print("🚀 분쟁조정 사례 데이터 임베딩 파이프라인 시작")
    print("=" * 80)
    print(f"데이터베이스: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f"임베딩 API: {embed_api_url}")
    
    # 파이프라인 실행
    try:
        pipeline = DisputeEmbeddingPipeline(db_config, embed_api_url, load_only=args.load_only)
        pipeline.process_all_files()
        
        # 검증
        pipeline.connect_db()
        pipeline.verify_data()
        pipeline.close_db()
        
        print("\n" + "=" * 80)
        print("✅ 분쟁조정 사례 데이터 임베딩 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
