# RunPod GPU 임베딩 및 RAG 테스트 완전 가이드

## 1. SSH 키 다운로드 및 RunPod 연결

### 1.1. SSH 키 다운로드
- **공용 계정**의 Google Drive 의 .ssh 폴더 다운로드
- 1.1.1. 을 참고하여 SSH 키 저장 위치에 그대로 저장

### 1.1.1 환경별 SSH 키 저장 위치

SSH 키는 각 환경의 홈 디렉토리 아래 `.ssh` 폴더에 저장됩니다. 환경별 실제 경로는 다음과 같습니다:

- # 키 권한 설정 (중요!)
chmod 600 ~/.ssh/runpod_key
chmod 644 ~/.ssh/runpod_key.pub

| 환경 | 홈 디렉토리 | SSH 키 저장 경로 | 실제 경로 예시 |
|------|------------|-----------------|---------------|
| **WSL2** | `~` 또는 `$HOME` | `~/.ssh/runpod_key` | `/home/user/.ssh/runpod_key` |
| **Mac OS** | `~` 또는 `$HOME` | `~/.ssh/runpod_key` | `/Users/user/.ssh/runpod_key` |
| **Windows 11 (Git Bash)** | `~` | `~/.ssh/runpod_key` | `/c/Users/user/.ssh/runpod_key` |
| **Windows 11 (PowerShell)** | `$env:USERPROFILE` | `$env:USERPROFILE\.ssh\runpod_key` | `C:\Users\user\.ssh\runpod_key` |

### 1.2. Runpod 인스턴스 생성

1. Runpod 로그인
2. Pod 생성
    - 권장 GPU : A40 (VRAM 48gb 이상)
3. 템플릿 선택
    - `Runpod PyTorch 2.8` 이상의 템플릿 선택
    - `SPLADE` 모델은 `PyTorch 2.6` 이상의 템플릿 필요
4. `SSH terminal access` 체크되어있는지 확인! (체크 되어있어야 함)

### 1.3. SSH와 로컬 연결

- powershell, bash, zsh, Git Bash 사용
- `SSH over exposed TCP` 에 적힌 명령어 참고

```bash
ssh root@[IP ADDRESS] -p [PORT] -i ~/.ssh/runpod_key
```

### 1.4. 패키지 설치
```bash
pip install fastapi uvicorn sentence-transformers hf_transfer
```

### 1.5. 임베딩 모델용 API 서버 코드 작성
- cat... 부터 EOF 까지 복사해서 그대로 enter

```bash
# RunPod 터미널에서 실행
cat > runpod_embed_server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch
from typing import List
import traceback

# GPU 확인 및 모델 로드
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Loading model on {device}...")

model = SentenceTransformer('nlpai-lab/KURE-v1', device=device)
print(f"✅ Model loaded successfully on {device}!")

app = FastAPI(title="KURE-v1 Embedding API")

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]

@app.post("/embed", response_model=EmbedResponse)
def embed_texts(request: EmbedRequest):
    try:
        embeddings = model.encode(
            request.texts,
            convert_to_tensor=False,
            show_progress_bar=False
        ).tolist()
        return EmbedResponse(embeddings=embeddings)
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Embedding server is running", "device": device}
EOF
```

### 1.6. KURE-v1 모델용 서버 실행
```bash
# RunPod 터미널에서 실행
# 이 터미널 창은 계속 열어두어야 합니다
uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
```

### 1.7. SSH 터널 설정
- 새로운 powershell, Git Bash, bash, zsh 창을 열어서 사용용

```bash
# 로컬 PC에서 새 터미널 창 열기
# 임베딩 서버 터널과 별도로 SPLADE 서버 터널 설정
# 아래 명령어에서 [사용자명], [IP주소], [포트번호]를 실제 값으로 교체
ssh -L 8001:localhost:8000 [사용자명]@[IP주소] -p [포트번호]

# 예시:
# ssh -L 8002:localhost:8002 root@xxx-xxx-xxx-xxx.runpod.io -p 12345

# 이 터미널 창은 계속 열어두어야 합니다
```

### 1.8. 모델 연결 테스트
- 새로 연 powershell, git bash, bash, zsh 에서 실행
```bash
# 로컬 PC의 새 터미널에서 실행
curl http://localhost:8001/

# 성공 시: {"message":"Embedding server is running","device":"cuda"}
```

## 2. SPLADE 모델 연결
### 2.1. SSH 연결

- powershell, bash, zsh, Git Bash 사용
- `SSH over exposed TCP` 에 적힌 명령어 참고
- **### 1.3 에서 사용한 명령어와 동일하게**

```bash
ssh root@[IP ADDRESS] -p [PORT] -i ~/.ssh/runpod_key
```

### 2.2. 필요한 패키지 설치
```bash
# RunPod 터미널에서 실행
# sentence-transformers 5.0.0 이상 필요
pip install sentence-transformers fastapi uvicorn hf_transfer python-dotenv
```

- **SPLADE 모델 사용을 위한 HF_TOKEN 입력
```bash
# HuggingFace 토큰이 필요한 경우 (gated 모델 접근용)
export HF_TOKEN=your_token_here
```

### 2.3. SPLADE 모델용 서버 코드 작성
- cat... 부터 EOF 까지 복사해서 그대로 enter

```bash
# RunPod 터미널에서 실행
# 프로젝트 코드가 있다면 그대로 사용, 없다면 아래 코드 작성
cat > runpod_splade_server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import numpy as np
from typing import List
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# transformers 라이브러리 확인
try:
    from sentence_transformers import SparseEncoder
    print(f"✅ SparseEncoder 사용 가능")
except ImportError as e:
    print(f"❌ SparseEncoder import 실패: {e}")
    print("   pip install --upgrade sentence-transformers>=5.0.0")
    raise

# HuggingFace 토큰 확인
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')

# 모델 로드 (GPU 사용)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🔧 Loading SPLADE model on {device}...")

try:
    model = SparseEncoder(
        "naver/splade-v3",
        token=HF_TOKEN if HF_TOKEN else None,
        trust_remote_code=True
    )
    print(f"✅ SPLADE model loaded successfully on {device}!")
except Exception as e:
    print(f"❌ Error loading SPLADE model: {e}")
    raise

# FastAPI 앱 생성
app = FastAPI(title="SPLADE Sparse Encoder API")

# 요청/응답 모델 정의
class EncodeRequest(BaseModel):
    texts: List[str]

class EncodeResponse(BaseModel):
    embeddings: List[List[float]]
    shapes: List[List[int]]

# 유틸리티 함수
def sparse_to_dense(sparse_vec, vocab_size=30522):
    """Sparse tensor를 dense numpy array로 변환"""
    if isinstance(sparse_vec, torch.Tensor):
        if sparse_vec.is_sparse:
            sparse_vec = sparse_vec.to_dense()
        sparse_vec = sparse_vec.cpu().numpy()
    if len(sparse_vec.shape) > 1:
        return sparse_vec[0]
    return sparse_vec

# 인코딩 엔드포인트
@app.post("/encode_query", response_model=EncodeResponse)
def encode_query(request: EncodeRequest):
    """쿼리 텍스트를 Sparse Vector로 인코딩"""
    try:
        query_embeddings = model.encode_query(request.texts)
        dense_embeddings = []
        for emb in query_embeddings:
            dense_emb = sparse_to_dense(emb)
            dense_embeddings.append(dense_emb.tolist())
        return EncodeResponse(
            embeddings=dense_embeddings,
            shapes=[list(emb.shape) for emb in query_embeddings]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query encoding error: {str(e)}")

@app.post("/encode_document", response_model=EncodeResponse)
def encode_document(request: EncodeRequest):
    """문서 텍스트를 Sparse Vector로 인코딩"""
    try:
        doc_embeddings = model.encode_document(request.texts)
        dense_embeddings = []
        for emb in doc_embeddings:
            dense_emb = sparse_to_dense(emb)
            dense_embeddings.append(dense_emb.tolist())
        return EncodeResponse(
            embeddings=dense_embeddings,
            shapes=[list(emb.shape) for emb in doc_embeddings]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document encoding error: {str(e)}")

@app.get("/")
def root():
    return {
        "message": "SPLADE Sparse Encoder API is running",
        "device": device,
        "model": "naver/splade-v3",
        "cuda_available": torch.cuda.is_available()
    }

@app.get("/health")
def health():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "device": device,
        "cuda_available": torch.cuda.is_available()
    }
EOF
```

### 2.4. SPLADE 서버 실행

```bash
# RunPod 터미널에서 실행
# ⚠️ 중요: 임베딩 서버와 다른 포트 사용 (8002)
# 이 터미널 창은 계속 열어두어야 합니다
uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8002
```

### 2.5. SSH 터널 설정

```bash
# 로컬 PC에서 새 터미널 창 열기
# 임베딩 서버 터널과 별도로 SPLADE 서버 터널 설정
# 아래 명령어에서 [사용자명], [IP주소], [포트번호]를 실제 값으로 교체
ssh -L 8002:localhost:8002 [사용자명]@[IP주소] -p [포트번호]

# 예시:
# ssh -L 8002:localhost:8002 root@xxx-xxx-xxx-xxx.runpod.io -p 12345

# 이 터미널 창은 계속 열어두어야 합니다
```

## 3. Docker 및 데이터베이스 설정
- 해당 작업은 Runpod Linux가 아닌, 로컬 환경에서 진행됩니다.

### 3.1. Docker Desktop 연결 확인
```bash
# Docker 실행 상태 확인
docker ps

# Docker Compose 실행
docker-compose up -d db
```

### 3.2. PostgreSQL 컨테이너 상태 확인

```bash
# 컨테이너 실행 상태 확인
docker ps | grep ddoksori_db

# 또는 docker-compose 사용
docker-compose ps db

# 로그 확인
docker logs ddoksori_db
```

### 3.3. 스키마 생성

```bash
# 스키마 파일 존재 확인
ls -la backend/database/schema_v2_final.sql

# 스키마 실행 (cat과 파이프 사용 - zsh/bash 모두 호환)
cat backend/database/schema_v2_final.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

#### 3.3.1. SPLADE 마이그레이션 실행 (SPLADE 사용 시 필수)

```bash
# SPLADE 마이그레이션 파일 존재 확인
ls -la backend/database/migrations/002_add_splade_sparse_vector.sql

# SPLADE 마이그레이션 실행
cat backend/database/migrations/002_add_splade_sparse_vector.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

### 3.4. 생성된 스키마 확인

```bash
# 테이블 목록 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\dt"

# pgvector 확장 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# documents 테이블 구조 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d documents"

# chunks 테이블 구조 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d chunks"

# SPLADE 컬럼 확인 (SPLADE 마이그레이션 실행 후)
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'chunks' 
AND column_name LIKE 'splade%'
ORDER BY column_name;
"
```

### 3.5. 환경 변수 설정

```bash
cd backend
cp .env.example .env
```
- backend/.env 파일 열어서 수정
- 사용할 API KEY 입력
    - **2026-01-09 기준 필요한 키**
        - OPENAI_API_KEY
        - HF_TOKEN

## 4. 데이터 타입별 임베딩 생성
### 4.1 Conda 환경 활성화

```bash
# 프로젝트 루트 디렉토리로 이동
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Conda 환경 활성화
conda activate dsr

# 또는 conda run 사용
# python ...
```

### 4.2 Law 데이터 임베딩

```bash
# 법령 데이터 임베딩
python backend/scripts/embedding/embed_law.py
```

### 4.3 Criteria 데이터 임베딩

```bash
# 기준 데이터 임베딩
python backend/scripts/embedding/embed_criteria.py
```

### 4.4 Dispute 데이터 임베딩

```bash
# 분쟁조정 사례 데이터 임베딩
python backend/scripts/embedding/embed_dispute.py
```

### 4.5 Compensation 데이터 임베딩

```bash
# 피해구제 사례 데이터 임베딩
python backend/scripts/embedding/embed_compensation.py
```

### 4.6 임베딩 상태 확인

```bash
# 전체 통계 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    COUNT(embedding)::float / COUNT(*) * 100 as embed_rate
FROM chunks;
"

# 문서 타입별 분포
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    d.doc_type,
    COUNT(DISTINCT d.doc_id) as doc_count,
    COUNT(c.chunk_id) as chunk_count
FROM documents d
LEFT JOIN chunks c ON d.doc_id = c.doc_id
GROUP BY d.doc_type
ORDER BY doc_count DESC;
"
```

### 5. SPLADE 인코딩

```bash
# SPLADE sparse vector 인코딩 (원격 API 사용)
python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002

# 특정 문서 타입만 인코딩
python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002 --doc-type law
```

### 6. RAG 테스트

### 6.1 Law RAG 테스트

```bash
# 법령 데이터 RAG 테스트
python tests/rag/test_rag_law.py
```

**출력 예시:**
```
검색 전략: Vector Similarity Search with doc_type='law' filter
필터 조건:
  - doc_type: law
  - chunk_types: None (모든 청크 타입)
  - agencies: None (모든 기관)

검색 결과:
[결과 1] 유사도: 0.8523
  청크 타입: article
  내용: [법령] 민법 [조문] 제750조 고의 또는 과실로 인한 위법행위로...
```

### 5.2 Criteria RAG 테스트

```bash
# 기준 데이터 RAG 테스트
python tests/rag/test_rag_criteria.py
```

**출력 예시:**
```
검색 전략: Vector Similarity Search with doc_type LIKE 'criteria_%' filter
필터 조건:
  - doc_type: criteria_item, criteria_resolution, criteria_warranty, criteria_lifespan
  - chunk_types: None (모든 청크 타입)
  - agencies: None (모든 기관)

검색 결과:
[결과 1] 유사도: 0.7845
  청크 타입: item_classification
  내용: [품목] 가전제품 [기준] 내용연수 5년...
```

### 5.3 Dispute RAG 테스트

```bash
# 분쟁조정 사례 데이터 RAG 테스트
python tests/rag/test_rag_dispute.py
```

**출력 예시:**
```
검색 전략: Vector Similarity Search with doc_type='mediation_case' filter
필터 조건:
  - doc_type: mediation_case
  - chunk_types: None (모든 청크 타입)
  - agencies: None (모든 기관)

검색 결과:
[결과 1] 유사도: 0.9123
  청크 타입: decision
  기관: KCA
  사건번호: 2024-001
  내용: 소비자는 온라인 쇼핑몰에서 구매한 제품의 하자로 인해...
```

### 5.4 Compensation RAG 테스트

```bash
# 피해구제 사례 데이터 RAG 테스트
python tests/rag/test_rag_compensation.py
```

**출력 예시:**
```
검색 전략: Vector Similarity Search with doc_type='consumer_counsel_case' filter
필터 조건:
  - doc_type: consumer_counsel_case
  - chunk_types: None (모든 청크 타입)
  - agencies: None (모든 기관)

검색 결과:
[결과 1] 유사도: 0.7654
  청크 타입: qa_combined
  기관: consumer.go.kr
  내용: [질문] 환불 관련 문의 [답변] 전자상거래법에 따라...
```