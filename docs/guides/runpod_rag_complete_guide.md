# RunPod GPU 임베딩 및 RAG 테스트 완전 가이드

**작성일**: 2026-01-07  
**목적**: SSH 키 생성부터 RunPod GPU 연결, 데이터 임베딩, RAG 테스트까지 전체 프로세스를 하나의 문서에서 명령어만 복사-붙여넣기로 실행 가능하도록 정리

---

## 📋 목차

1. [SSH 키 생성 및 RunPod 연결](#1-ssh-키-생성-및-runpod-연결)
2. [Docker 및 데이터베이스 설정](#2-docker-및-데이터베이스-설정)
3. [RunPod 임베딩 서버 설정](#3-runpod-임베딩-서버-설정)
3A. [RunPod SPLADE 서버 설정](#3a-runpod-splade-서버-설정)
4. [데이터 타입별 임베딩 생성](#4-데이터-타입별-임베딩-생성)
5. [데이터 타입별 RAG 테스트](#5-데이터-타입별-rag-테스트)
6. [환경별 설정 가이드](#6-환경별-설정-가이드)

---

## 1. SSH 키 생성 및 RunPod 연결

### 1.1 SSH 키 생성

```bash
# 프로젝트 루트 디렉토리로 이동
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# SSH 키 생성 (이미 있으면 스킵)
ssh-keygen -t ed25519 -C "runpod-key" -f ~/.ssh/runpod_key -N ""

# 공개키 확인
cat ~/.ssh/runpod_key.pub
```

### 1.2 RunPod 인스턴스 생성

1. [RunPod](https://www.runpod.io/)에 로그인
2. `Secure Cloud` 또는 `Community Cloud`에서 GPU 선택
   - **권장 GPU**: `NVIDIA RTX 4090` 또는 `NVIDIA A100`
3. 템플릿 선택: `RunPod Pytorch 2.2` 또는 최신 PyTorch 템플릿
4. 디스크 용량 설정 후 `Deploy` 클릭

### 1.3 SSH 접속 정보 확인

1. `My Pods` 페이지에서 생성된 인스턴스의 `Connect` 버튼 클릭
2. `Connect via SSH` 탭에서 SSH 연결 명령어 복사
   - 예: `ssh root@xxx-xxx-xxx-xxx.runpod.io -p 12345`

### 1.4 SSH 터널 연결

```bash
# 로컬 PC에서 새 터미널 창 열기
# 아래 명령어에서 [사용자명], [IP주소], [포트번호]를 실제 값으로 교체
ssh -L 8001:localhost:8000 [사용자명]@[IP주소] -p [포트번호]

# 예시:
# ssh -L 8001:localhost:8000 root@xxx-xxx-xxx-xxx.runpod.io -p 12345

# 이 터미널 창은 계속 열어두어야 합니다
```

### 1.5 SSH 연결 상태 확인

```bash
# 새 터미널에서 SSH 터널 연결 확인
curl http://localhost:8001/

# 연결 성공 시 RunPod 서버 응답이 표시됩니다
# 연결 실패 시 "Connection refused" 오류가 표시됩니다
```

---

## 2. Docker 및 데이터베이스 설정

### 2.1 Docker Desktop 연결 확인

```bash
# 프로젝트 루트 디렉토리로 이동
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker 실행 상태 확인
docker ps

# Docker Compose 실행
docker-compose up -d db
```

### 2.2 PostgreSQL 컨테이너 상태 확인

```bash
# 컨테이너 실행 상태 확인
docker ps | grep ddoksori_db

# 또는 docker-compose 사용
docker-compose ps db

# 로그 확인
docker logs ddoksori_db
```

### 2.3 스키마 생성

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 스키마 파일 존재 확인
ls -la backend/database/schema_v2_final.sql

# 스키마 실행 (cat과 파이프 사용 - zsh/bash 모두 호환)
cat backend/database/schema_v2_final.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

### 2.4 생성된 스키마 확인

```bash
# 테이블 목록 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\dt"

# pgvector 확장 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# documents 테이블 구조 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d documents"

# chunks 테이블 구조 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d chunks"
```

### 2.5 환경 변수 설정

```bash
# backend/.env 파일 생성 또는 확인
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cat > backend/.env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres

# 임베딩 API 설정 (원격 GPU 사용 시)
EMBED_API_URL=http://localhost:8001/embed

# SPLADE API 설정 (원격 GPU 사용 시)
SPLADE_API_URL=http://localhost:8002
EOF

# 환경 변수 확인
cat backend/.env
```

---

## 3. RunPod 임베딩 서버 설정

### 3.1 RunPod에 SSH 접속

```bash
# 1.4에서 복사한 SSH 명령어 사용
ssh [사용자명]@[IP주소] -p [포트번호]

# 예시:
# ssh root@xxx-xxx-xxx-xxx.runpod.io -p 12345
```

### 3.2 필요한 패키지 설치

```bash
# RunPod 터미널에서 실행
pip install fastapi uvicorn sentence-transformers torch
```

### 3.3 API 서버 코드 작성

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

### 3.4 서버 실행

```bash
# RunPod 터미널에서 실행
# 이 터미널 창은 계속 열어두어야 합니다
uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
```

### 3.5 서버 연결 테스트

```bash
# 로컬 PC의 새 터미널에서 실행
curl http://localhost:8001/

# 성공 시: {"message":"Embedding server is running","device":"cuda"}
```

---

## 3A. RunPod SPLADE 서버 설정

SPLADE (Sparse Lexical And Expansion) 모델은 Dense Vector와 Sparse Vector의 장점을 결합한 하이브리드 검색 모델입니다. 법령 및 기준 데이터의 정확 매칭에 특히 유리합니다.

### 3A.1 RunPod에 SSH 접속 (이미 접속했다면 스킵)

```bash
# 1.4에서 복사한 SSH 명령어 사용
ssh [사용자명]@[IP주소] -p [포트번호]

# 예시:
# ssh root@xxx-xxx-xxx-xxx.runpod.io -p 12345
```

### 3A.2 필요한 패키지 설치

```bash
# RunPod 터미널에서 실행
# sentence-transformers 5.0.0 이상 필요
pip install --upgrade sentence-transformers>=5.0.0 transformers>=4.41.0 torch>=2.6 fastapi uvicorn

# HuggingFace 토큰이 필요한 경우 (gated 모델 접근용)
# export HF_TOKEN=your_token_here
```

### 3A.3 SPLADE 서버 코드 확인

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

### 3A.4 SPLADE 서버 실행

```bash
# RunPod 터미널에서 실행
# ⚠️ 중요: 임베딩 서버와 다른 포트 사용 (8002)
# 이 터미널 창은 계속 열어두어야 합니다
uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8002
```

**참고**: 임베딩 서버와 SPLADE 서버를 동시에 실행하려면:
- 임베딩 서버: 포트 8000
- SPLADE 서버: 포트 8002

### 3A.5 SSH 터널 설정 (SPLADE 서버용)

```bash
# 로컬 PC에서 새 터미널 창 열기
# 임베딩 서버 터널과 별도로 SPLADE 서버 터널 설정
# 아래 명령어에서 [사용자명], [IP주소], [포트번호]를 실제 값으로 교체
ssh -L 8002:localhost:8002 [사용자명]@[IP주소] -p [포트번호]

# 예시:
# ssh -L 8002:localhost:8002 root@xxx-xxx-xxx-xxx.runpod.io -p 12345

# 이 터미널 창은 계속 열어두어야 합니다
```

**참고**: 두 서버를 동시에 사용하려면 두 개의 SSH 터널이 필요합니다:
- 터미널 1: `ssh -L 8001:localhost:8000 ...` (임베딩 서버)
- 터미널 2: `ssh -L 8002:localhost:8002 ...` (SPLADE 서버)

### 3A.6 SPLADE 서버 연결 테스트

```bash
# 로컬 PC의 새 터미널에서 실행
curl http://localhost:8002/

# 성공 시: {"message":"SPLADE Sparse Encoder API is running","device":"cuda","model":"naver/splade-v3","cuda_available":true}

# 헬스 체크
curl http://localhost:8002/health
```

### 3A.7 로컬 환경에서 SPLADE API 사용

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 환경 변수 확인
cat backend/.env | grep SPLADE_API_URL

# SPLADE 인코딩 테스트 스크립트 실행
conda run -n dsr python backend/scripts/splade/test_splade_remote.py
```

**출력 예시:**
```
✅ SPLADE API 서버 연결 성공!
Query: 민법 제750조 불법행위
✅ Encoded (shape: (30522,), non-zero: 123)
```

### 3A.8 SPLADE 인코딩 파이프라인 실행

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# SPLADE sparse vector 인코딩 (원격 API 사용)
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002

# 특정 문서 타입만 인코딩
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002 --doc-type law

# 인코딩 통계만 확인
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --stats-only

# 로컬 모드 사용 (원격 API 없이)
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --device cuda
```

---

## 4. 데이터 타입별 임베딩 생성

### 4.1 Conda 환경 활성화

```bash
# 프로젝트 루트 디렉토리로 이동
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Conda 환경 활성화
conda activate dsr

# 또는 conda run 사용
# conda run -n dsr python ...
```

### 4.2 Law 데이터 임베딩

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 법령 데이터 임베딩
conda run -n dsr python backend/scripts/embedding/embed_law.py
```

### 4.3 Criteria 데이터 임베딩

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 기준 데이터 임베딩
conda run -n dsr python backend/scripts/embedding/embed_criteria.py
```

### 4.4 Dispute 데이터 임베딩

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 분쟁조정 사례 데이터 임베딩
conda run -n dsr python backend/scripts/embedding/embed_dispute.py
```

### 4.5 Compensation 데이터 임베딩

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 피해구제 사례 데이터 임베딩
conda run -n dsr python backend/scripts/embedding/embed_compensation.py
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

---

## 5. 데이터 타입별 RAG 테스트

### 5.1 Law RAG 테스트

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 법령 데이터 RAG 테스트
conda run -n dsr python tests/rag/test_rag_law.py
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
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 기준 데이터 RAG 테스트
conda run -n dsr python tests/rag/test_rag_criteria.py
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
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 분쟁조정 사례 데이터 RAG 테스트
conda run -n dsr python tests/rag/test_rag_dispute.py
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
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 피해구제 사례 데이터 RAG 테스트
conda run -n dsr python tests/rag/test_rag_compensation.py
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

---

## 6. 환경별 설정 가이드

각 운영체제 환경에 맞는 설정 방법을 안내합니다.

### 6.1 WSL2 (Windows Subsystem for Linux 2)

WSL2는 Windows 11에서 Linux 환경을 실행하는 가장 권장되는 방법입니다.

#### 6.1.1 SSH 키 생성 및 설정

```bash
# WSL2 터미널에서 실행
# 프로젝트 루트 디렉토리로 이동
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# SSH 디렉토리 생성 (없는 경우)
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# SSH 키 생성
ssh-keygen -t ed25519 -C "runpod-key" -f ~/.ssh/runpod_key -N ""

# 키 권한 설정 (중요!)
chmod 600 ~/.ssh/runpod_key
chmod 644 ~/.ssh/runpod_key.pub

# 공개키 확인
cat ~/.ssh/runpod_key.pub
```

#### 6.1.2 Docker Desktop 연결

```bash
# WSL2에서 Docker Desktop 연결 확인
# Docker Desktop이 실행 중이어야 합니다

# Docker 실행 상태 확인
docker ps

# Docker Compose 실행
docker-compose up -d db

# Docker Desktop이 연결되지 않은 경우:
# 1. Windows에서 Docker Desktop 실행
# 2. Docker Desktop > Settings > Resources > WSL Integration
# 3. 사용 중인 WSL 배포판 활성화
```

#### 6.1.3 경로 처리

```bash
# WSL2에서는 Unix 경로 사용
# 프로젝트 경로 예시: /home/maroco/LLM

# Windows 경로와의 변환 (필요한 경우)
# Windows 경로: C:\Users\maroco\LLM
# WSL 경로: /mnt/c/Users/maroco/LLM 또는 /home/maroco/LLM

# 프로젝트 루트 확인
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
pwd
```

#### 6.1.4 Conda 환경 설정

```bash
# Conda 설치 확인
conda --version

# 환경 목록 확인
conda env list

# dsr 환경 활성화
conda activate dsr

# 또는 conda run 사용
conda run -n dsr python --version
```

#### 6.1.5 SSH 터널 설정

```bash
# WSL2 터미널에서 실행
# 임베딩 서버 터널
ssh -L 8001:localhost:8000 [사용자명]@[IP주소] -p [포트번호]

# SPLADE 서버 터널 (별도 터미널)
ssh -L 8002:localhost:8002 [사용자명]@[IP주소] -p [포트번호]
```

### 6.2 Mac 환경

#### 6.2.1 SSH 키 생성 및 설정

```bash
# 터미널에서 실행
# 프로젝트 루트 디렉토리로 이동
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# SSH 디렉토리 확인
ls -la ~/.ssh

# SSH 키 생성
ssh-keygen -t ed25519 -C "runpod-key" -f ~/.ssh/runpod_key -N ""

# 키 권한 설정
chmod 600 ~/.ssh/runpod_key
chmod 644 ~/.ssh/runpod_key.pub

# 공개키 확인
cat ~/.ssh/runpod_key.pub
```

#### 6.2.2 Docker Desktop 설정

```bash
# Docker Desktop 설치 확인
docker --version

# Docker Desktop 실행 확인
docker ps

# Docker Compose 실행
docker-compose up -d db

# Docker Desktop이 설치되지 않은 경우:
# 1. https://www.docker.com/products/docker-desktop 에서 다운로드
# 2. Apple Silicon (M1/M2) Mac: Apple Silicon용 다운로드
# 3. Intel Mac: Intel용 다운로드
```

#### 6.2.3 경로 처리

```bash
# Mac은 Unix 경로 사용
# 프로젝트 경로 예시: /Users/maroco/LLM

# 프로젝트 루트 확인
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
pwd
```

#### 6.2.4 Conda 환경 설정

```bash
# Conda 설치 확인 (Anaconda 또는 Miniconda)
conda --version

# 환경 목록 확인
conda env list

# dsr 환경 활성화
conda activate dsr

# 또는 conda run 사용
conda run -n dsr python --version
```

#### 6.2.5 SSH 터널 설정

```bash
# 터미널에서 실행
# 임베딩 서버 터널
ssh -L 8001:localhost:8000 [사용자명]@[IP주소] -p [포트번호]

# SPLADE 서버 터널 (별도 터미널)
ssh -L 8002:localhost:8002 [사용자명]@[IP주소] -p [포트번호]
```

### 6.3 Windows 11 환경

Windows 11에서는 WSL2 사용을 강력히 권장합니다. WSL2를 사용하지 않는 경우 아래 방법을 참고하세요.

#### 6.3.1 WSL2 사용 권장

```bash
# PowerShell (관리자 권한)에서 실행
wsl --install

# 설치 후 재부팅
# 재부팅 후 WSL2 사용 (위의 6.1 섹션 참고)
```

#### 6.3.2 Git Bash 또는 PowerShell에서 SSH 키 생성

**Git Bash 사용:**
```bash
# Git Bash에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# SSH 키 생성
ssh-keygen -t ed25519 -C "runpod-key" -f ~/.ssh/runpod_key -N ""

# 공개키 확인
cat ~/.ssh/runpod_key.pub
```

**PowerShell 사용:**
```powershell
# PowerShell에서 실행
# SSH 키 생성
ssh-keygen -t ed25519 -C "runpod-key" -f $env:USERPROFILE\.ssh\runpod_key -N ""

# 공개키 확인
Get-Content $env:USERPROFILE\.ssh\runpod_key.pub
```

#### 6.3.3 Docker Desktop 설정

```powershell
# PowerShell에서 실행
# Docker Desktop 설치 확인
docker --version

# Docker Desktop 실행 확인
docker ps

# Docker Compose 실행
docker-compose up -d db

# Docker Desktop이 설치되지 않은 경우:
# 1. https://www.docker.com/products/docker-desktop 에서 다운로드
# 2. WSL 2 backend 사용 권장
```

#### 6.3.4 경로 처리

```powershell
# PowerShell에서는 Windows 경로 사용
# 프로젝트 경로 예시: C:\Users\maroco\LLM

# Git Bash에서는 Unix 스타일 경로 사용
# 프로젝트 경로 예시: /c/Users/maroco/LLM

# 프로젝트 루트 확인 (Git Bash)
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
pwd
```

#### 6.3.5 Conda 환경 설정

**Anaconda Prompt 사용:**
```cmd
# Anaconda Prompt에서 실행
conda activate dsr

# 또는 conda run 사용
conda run -n dsr python --version
```

**PowerShell에서 Conda 사용:**
```powershell
# PowerShell에서 실행
# Conda 초기화 (처음 한 번만)
conda init powershell

# 새 PowerShell 창에서
conda activate dsr
```

#### 6.3.6 SSH 터널 설정

**Git Bash 사용:**
```bash
# Git Bash에서 실행
ssh -L 8001:localhost:8000 [사용자명]@[IP주소] -p [포트번호]
```

**PowerShell 사용:**
```powershell
# PowerShell에서 실행
ssh -L 8001:localhost:8000 [사용자명]@[IP주소] -p [포트번호]
```

### 6.4 환경별 주의사항 요약

| 환경 | SSH 키 경로 | Docker | 경로 형식 | Conda | 권장 |
|------|------------|--------|-----------|-------|------|
| **WSL2** | `~/.ssh/` | Docker Desktop (WSL Integration) | Unix (`/home/...`) | conda activate | ✅ 권장 |
| **Mac** | `~/.ssh/` | Docker Desktop | Unix (`/Users/...`) | conda activate | ✅ 권장 |
| **Windows 11** | `%USERPROFILE%\.ssh\` | Docker Desktop (WSL 2 backend) | Windows (`C:\...`) | Anaconda Prompt | ⚠️ WSL2 권장 |

---

## 🔧 트러블슈팅

### 문제 1: SSH 연결 실패

**증상**: `Connection refused` 또는 `Permission denied`

**해결**:
```bash
# SSH 키 권한 확인
chmod 600 ~/.ssh/runpod_key

# SSH 연결 테스트
ssh -v [사용자명]@[IP주소] -p [포트번호]
```

### 문제 2: SSH 터널 연결 실패

**증상**: `curl http://localhost:8001/` 실패

**해결**:
1. SSH 터널 터미널이 실행 중인지 확인
2. RunPod 서버가 실행 중인지 확인 (RunPod 터미널에서 `uvicorn` 확인)
3. 포트 충돌 확인: `lsof -i :8001`

### 문제 3: 데이터베이스 연결 실패

**증상**: `psycopg2.OperationalError`

**해결**:
```bash
# Docker 컨테이너 상태 확인
docker ps | grep ddoksori_db

# 컨테이너 재시작
docker-compose restart db

# 연결 테스트
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT version();"
```

### 문제 4: 임베딩 API 연결 실패

**증상**: `❌ API 연결 실패`

**해결**:
1. SSH 터널 확인
2. RunPod 서버 실행 확인
3. 로컬에서 테스트: `curl http://localhost:8001/`

### 문제 5: 스키마 생성 실패

**증상**: `No such file or directory`

**해결**:
```bash
# 프로젝트 루트에서 실행 확인
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
pwd

# 파일 존재 확인
ls -la backend/database/schema_v2_final.sql

# 절대 경로 사용
cat "$(pwd)/backend/database/schema_v2_final.sql" | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

### 문제 6: SPLADE API 연결 실패

**증상**: `Connection refused` 또는 `API 서버 연결 실패`

**해결**:
```bash
# 1. SSH 터널 확인 (포트 8002)
# 별도 터미널에서 실행 중인지 확인
ssh -L 8002:localhost:8002 [사용자명]@[IP주소] -p [포트번호]

# 2. RunPod에서 SPLADE 서버 실행 확인
# RunPod 터미널에서 확인
ps aux | grep uvicorn | grep 8002

# 3. 로컬에서 연결 테스트
curl http://localhost:8002/health

# 4. 포트 충돌 확인
lsof -i :8002  # Mac/Linux
netstat -ano | findstr :8002  # Windows
```

### 문제 7: SPLADE 모델 로드 실패

**증상**: `torch.load` 오류 또는 `CVE-2025-32434` 오류

**해결**:
```bash
# RunPod 터미널에서 실행
# PyTorch 버전 확인
python -c "import torch; print(torch.__version__)"

# PyTorch 2.6 이상으로 업그레이드
pip install --upgrade torch>=2.6

# 또는 CUDA 버전에 맞게 설치
pip install torch>=2.6 --index-url https://download.pytorch.org/whl/cu121

# sentence-transformers 업그레이드
pip install --upgrade sentence-transformers>=5.0.0
```

### 문제 8: WSL2에서 Docker 연결 실패

**증상**: `Cannot connect to the Docker daemon`

**해결**:
1. Windows에서 Docker Desktop 실행 확인
2. Docker Desktop > Settings > Resources > WSL Integration
3. 사용 중인 WSL 배포판 활성화 (예: Ubuntu)
4. WSL2 터미널 재시작
5. Docker 연결 확인: `docker ps`

### 문제 9: Windows에서 경로 오류

**증상**: `No such file or directory` 또는 경로 관련 오류

**해결**:
```bash
# Git Bash 사용 권장
# 또는 WSL2 사용 권장

# PowerShell에서 경로 변환
# Windows 경로: C:\Users\maroco\LLM
# Git Bash 경로: /c/Users/maroco/LLM
# WSL2 경로: /home/maroco/LLM (권장)
```

---

## 📝 체크리스트

전체 프로세스 완료 확인:

### 기본 설정
- [ ] SSH 키 생성 완료
- [ ] RunPod 인스턴스 생성 및 SSH 접속 성공
- [ ] SSH 터널 연결 성공 (임베딩: `curl http://localhost:8001/` 성공)
- [ ] Docker 컨테이너 실행 확인
- [ ] 스키마 생성 완료 (documents, chunks 테이블 존재)
- [ ] pgvector 확장 활성화 확인

### 임베딩 서버
- [ ] RunPod 임베딩 서버 실행 중
- [ ] 임베딩 서버 연결 테스트 성공

### SPLADE 서버 (선택사항)
- [ ] RunPod SPLADE 서버 실행 중
- [ ] SPLADE 서버 SSH 터널 연결 성공 (`curl http://localhost:8002/` 성공)
- [ ] SPLADE 서버 연결 테스트 성공

### 데이터 임베딩
- [ ] Law 데이터 임베딩 완료
- [ ] Criteria 데이터 임베딩 완료
- [ ] Dispute 데이터 임베딩 완료
- [ ] Compensation 데이터 임베딩 완료
- [ ] SPLADE 인코딩 완료 (선택사항)

### RAG 테스트
- [ ] Law RAG 테스트 성공
- [ ] Criteria RAG 테스트 성공
- [ ] Dispute RAG 테스트 성공
- [ ] Compensation RAG 테스트 성공
- [ ] SPLADE 검색 테스트 성공 (선택사항)

---

**업데이트**: 2026-01-07  
**최종 업데이트**: 2026-01-09 (SPLADE 섹션 및 환경별 가이드 추가)
