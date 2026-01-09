# 데이터 임베딩 파이프라인

## 개요

이 스크립트는 JSONL 형식의 분쟁조정 사례 데이터를 읽어서 KURE-v1 모델로 임베딩을 생성하고, PostgreSQL + pgvector에 저장합니다.

## 사전 준비

1. **PostgreSQL + pgvector 실행**
   ```bash
   docker-compose up -d postgres
   ```

2. **환경 변수 설정**
   
   `backend/.env` 파일을 생성하고 다음 내용을 입력합니다:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ddoksori
   DB_USER=postgres
   DB_PASSWORD=postgres
   ```

3. **Python 패키지 설치**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

## 실행 방법

```bash
cd backend
python scripts/embed_data.py
```

## 처리 과정

1. **모델 로드**: KURE-v1 임베딩 모델을 Hugging Face에서 다운로드
2. **스키마 초기화**: `database/schema_v2_final.sql`을 실행하여 테이블 생성
3. **데이터 로드**: `data/` 디렉토리의 모든 `.jsonl` 파일 읽기
4. **Cases 삽입**: 사례 메타데이터를 `cases` 테이블에 저장
5. **Chunks 임베딩 및 삽입**: 
   - 각 청크의 텍스트를 KURE-v1로 임베딩 (1024차원)
   - 임베딩 벡터와 함께 `chunks` 테이블에 저장
6. **검증**: 삽입된 데이터 통계 출력

## 데이터 구조

### Cases 테이블
- `case_uid`: 사례 고유 ID
- `case_no`: 사건번호
- `decision_date`: 결정일자
- `agency`: 발행 기관 (kca, ecmc, kcdrc)
- `source`: 데이터 출처

### Chunks 테이블
- `chunk_uid`: 청크 고유 ID
- `case_uid`: 연결된 사례 ID
- `chunk_type`: 청크 타입 (decision, parties_claim, judgment)
- `text`: 텍스트 내용
- `embedding`: KURE-v1 임베딩 벡터 (1024차원)

## 예상 소요 시간

- 총 3,358개 청크 처리
- GPU 사용 시: 약 5-10분
- CPU 사용 시: 약 20-30분

## 문제 해결

### pgvector 확장 오류
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 메모리 부족
배치 크기를 줄입니다:
```python
pipeline.embed_and_insert_chunks(records, batch_size=16)
```

### KURE-v1 모델 다운로드 실패
Hugging Face 토큰이 필요한 경우:
```bash
export HF_TOKEN=your_token_here
```
