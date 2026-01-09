# RunPod GPU 임베딩 및 RAG 테스트 완전 가이드

**작성일**: 2026-01-07  
**목적**: Docker 스키마 생성부터 RunPod GPU 연결, 데이터 임베딩, RAG 테스트까지 전체 프로세스를 순서대로 안내

---

## 📋 목차

1. [Docker 및 데이터베이스 설정](#1-docker-및-데이터베이스-설정)
2. [SSH 키 다운로드 및 RunPod 연결](#2-ssh-키-다운로드-및-runpod-연결)
3. [RunPod 서버 설정](#3-runpod-서버-설정)
4. [데이터 임베딩 생성](#4-데이터-임베딩-생성)
5. [RAG 테스트](#5-rag-테스트)
6. [트러블슈팅](#6-트러블슈팅)

---

## 1. Docker 및 데이터베이스 설정

### 1.1 Docker 컨테이너 실행

```bash
# 프로젝트 루트 디렉토리로 이동
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker 실행 상태 확인
docker ps

# PostgreSQL 컨테이너 실행
docker-compose up -d db

# 컨테이너 상태 확인
docker ps | grep ddoksori_db
```

### 1.2 스키마 생성

```bash
# 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 기본 스키마 실행
cat backend/database/schema_v2_final.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori

# SPLADE 마이그레이션 실행 (SPLADE 사용 시 필수)
cat backend/database/migrations/002_add_splade_sparse_vector.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

**SPLADE 마이그레이션 내용:**
- `splade_sparse_vector` (JSONB): SPLADE sparse vector 저장
- `splade_model` (VARCHAR): 사용된 모델 버전
- `splade_encoded` (BOOLEAN): 인코딩 완료 여부 플래그
- GIN 인덱스 및 관련 함수

### 1.3 스키마 확인

```bash
# 테이블 목록 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\dt"

# chunks 테이블 구조 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d chunks"

# SPLADE 컬럼 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'chunks' 
AND column_name LIKE 'splade%';
"
```

### 1.4 환경 변수 설정

```bash
# backend/.env 파일 생성
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
```

---

## 2. SSH 키 다운로드 및 RunPod 연결

### 2.1 SSH 키 다운로드

**⚠️ 중요**: 공용 계정(`skn19.final.5team@gmail.com`)의 Google Drive에서 SSH 키를 다운로드하여 사용합니다.

**방법 1: gdown 사용 (권장)**

```bash
# gdown 설치
pip install gdown

# SSH 디렉토리 생성
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Google Drive에서 .ssh 폴더 다운로드
# ⚠️ [FOLDER_ID]를 실제 Google Drive 폴더 ID로 교체하세요
gdown --folder https://drive.google.com/drive/folders/[FOLDER_ID] -O ~/.ssh --remaining-ok

# 키 권한 설정
chmod 600 ~/.ssh/runpod_key
chmod 644 ~/.ssh/runpod_key.pub
```

**방법 2: Google Drive 웹 UI에서 직접 다운로드**

1. Google Drive에 로그인: `skn19.final.5team@gmail.com` 계정으로 접속
2. `.ssh` 폴더를 ZIP으로 다운로드
3. 압축 해제 후 `~/.ssh`로 복사
4. 위의 키 권한 설정 명령어 실행

### 2.2 RunPod 인스턴스 생성

1. [RunPod](https://www.runpod.io/)에 로그인
2. `Secure Cloud` 또는 `Community Cloud`에서 GPU 선택
   - **권장 GPU**: `NVIDIA RTX 4090` 또는 `NVIDIA A100`
3. 템플릿 선택: `RunPod Pytorch 2.8` 또는 최신 PyTorch 템플릿
   - **SPLADE 사용 시**: PyTorch 2.6 이상 필요
4. 디스크 용량 설정 후 `Deploy` 클릭
5. **중요**: 인스턴스 생성 시 `SSH Key` 드롭다운에서 SSH 키 선택

### 2.3 SSH 접속 정보 확인

1. `My Pods` 페이지에서 생성된 인스턴스의 `Connect` 버튼 클릭
2. `Connect via SSH` 탭에서 SSH 연결 명령어 복사
   - 예: `ssh root@xxx.xxx.xxx.xxx -p xxxxx -i ~/.ssh/runpod_key`

### 2.4 SSH 터널 연결

**임베딩 서버용 터널:**
```bash
# 새 터미널 창에서 실행 (계속 열어두기)
ssh -i ~/.ssh/runpod_key -L 8001:localhost:8000 [사용자명]@[IP주소] -p [포트번호]
```

**SPLADE 서버용 터널 (별도 터미널):**
```bash
# 새 터미널 창에서 실행 (계속 열어두기)
ssh -i ~/.ssh/runpod_key -L 8002:localhost:8002 [사용자명]@[IP주소] -p [포트번호]
```

### 2.5 SSH 터널 연결 확인

```bash
# 임베딩 서버 확인
curl http://localhost:8001/

# SPLADE 서버 확인 (설정한 경우)
curl http://localhost:8002/
```

---

## 3. RunPod 서버 설정

### 3.1 임베딩 서버 설정

#### 3.1.1 RunPod에 SSH 접속

```bash
# 2.3에서 복사한 SSH 명령어 사용
ssh -i ~/.ssh/runpod_key [사용자명]@[IP주소] -p [포트번호]
```

#### 3.1.2 패키지 설치 및 서버 실행

```bash
# RunPod 터미널에서 실행
pip install fastapi uvicorn sentence-transformers hf_transfer

# API 서버 코드 작성
cat > runpod_embed_server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch
from typing import List
import traceback

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

# 서버 실행 (이 터미널은 계속 열어두기)
uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
```

#### 3.1.3 연결 테스트

```bash
# 로컬 PC의 새 터미널에서 실행
curl http://localhost:8001/
# 성공 시: {"message":"Embedding server is running","device":"cuda"}
```

### 3.2 SPLADE 서버 설정 (선택사항)

SPLADE (Sparse Lexical And Expansion) 모델은 Dense Vector와 Sparse Vector의 장점을 결합한 하이브리드 검색 모델입니다.

#### 3.2.1 패키지 설치 및 서버 실행

```bash
# RunPod 터미널에서 실행 (새 터미널 또는 screen/tmux 사용)
# sentence-transformers 5.0.0 이상 필요
pip install sentence-transformers fastapi uvicorn hf_transfer python-dotenv

# HuggingFace 토큰 설정 (필요한 경우)
# export HF_TOKEN=your_token_here

# SPLADE 서버 코드 작성
cat > runpod_splade_server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import numpy as np
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from sentence_transformers import SparseEncoder
    print(f"✅ SparseEncoder 사용 가능")
except ImportError as e:
    print(f"❌ SparseEncoder import 실패: {e}")
    print("   pip install --upgrade sentence-transformers>=5.0.0")
    raise

HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')

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

app = FastAPI(title="SPLADE Sparse Encoder API")

class EncodeRequest(BaseModel):
    texts: List[str]

class EncodeResponse(BaseModel):
    embeddings: List[List[float]]
    shapes: List[List[int]]

def sparse_to_dense(sparse_vec, vocab_size=30522):
    """Sparse tensor를 dense numpy array로 변환"""
    if isinstance(sparse_vec, torch.Tensor):
        if sparse_vec.is_sparse:
            sparse_vec = sparse_vec.to_dense()
        sparse_vec = sparse_vec.cpu().numpy()
    if len(sparse_vec.shape) > 1:
        return sparse_vec[0]
    return sparse_vec

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
    return {
        "status": "healthy",
        "device": device,
        "cuda_available": torch.cuda.is_available()
    }
EOF

# 서버 실행 (이 터미널은 계속 열어두기)
uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8002
```

#### 3.2.2 연결 테스트

```bash
# 로컬 PC의 새 터미널에서 실행
curl http://localhost:8002/
curl http://localhost:8002/health

# SPLADE 인코딩 테스트
conda run -n dsr python backend/scripts/splade/test_splade_remote.py
```

---

## 4. 데이터 임베딩 생성

### 4.1 Dense Vector 임베딩

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Law 데이터 임베딩
conda run -n dsr python backend/scripts/embedding/embed_law.py

# Criteria 데이터 임베딩
conda run -n dsr python backend/scripts/embedding/embed_criteria.py

# Dispute 데이터 임베딩
conda run -n dsr python backend/scripts/embedding/embed_dispute.py

# Compensation 데이터 임베딩
conda run -n dsr python backend/scripts/embedding/embed_compensation.py
```

### 4.2 SPLADE Sparse Vector 인코딩 (선택사항)

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 전체 데이터 SPLADE 인코딩 (원격 API 사용)
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002

# 특정 문서 타입만 인코딩
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002 --doc-type law

# 인코딩 통계만 확인
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --stats-only
```

### 4.3 임베딩 상태 확인

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

## 5. RAG 테스트

### 5.1 Law RAG 테스트

```bash
# 프로젝트 루트에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

conda run -n dsr python tests/rag/test_rag_law.py
```

### 5.2 Criteria RAG 테스트

```bash
conda run -n dsr python tests/rag/test_rag_criteria.py
```

### 5.3 Dispute RAG 테스트

```bash
conda run -n dsr python tests/rag/test_rag_dispute.py
```

### 5.4 Compensation RAG 테스트

```bash
conda run -n dsr python tests/rag/test_rag_compensation.py
```

---

## 6. 트러블슈팅

### 문제 1: SSH 연결 실패

**증상**: `Connection refused` 또는 `Permission denied`

**해결**:
```bash
# SSH 키 권한 확인 및 수정
chmod 700 ~/.ssh
chmod 600 ~/.ssh/runpod_key
chmod 644 ~/.ssh/runpod_key.pub

# SSH 연결 테스트
ssh -i ~/.ssh/runpod_key -v [사용자명]@[IP주소] -p [포트번호]
```

### 문제 2: SSH 터널 연결 실패

**증상**: `curl http://localhost:8001/` 실패

**해결**:
1. SSH 터널 터미널이 실행 중인지 확인
2. RunPod 서버가 실행 중인지 확인
3. 포트 충돌 확인: `lsof -i :8001` (Mac/Linux) 또는 `netstat -ano | findstr :8001` (Windows)

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

### 문제 4: 스키마 생성 실패

**증상**: `No such file or directory`

**해결**:
```bash
# 프로젝트 루트에서 실행 확인
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 파일 존재 확인
ls -la backend/database/schema_v2_final.sql

# 절대 경로 사용
cat "$(pwd)/backend/database/schema_v2_final.sql" | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

### 문제 5: SPLADE 인코딩 시 "column splade_encoded does not exist" 오류

**증상**: `psycopg2.errors.UndefinedColumn: column "splade_encoded" does not exist`

**해결**:
```bash
# SPLADE 마이그레이션 실행
cat backend/database/migrations/002_add_splade_sparse_vector.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori

# 마이그레이션 확인
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'chunks' 
AND column_name LIKE 'splade%';
"
```

### 문제 6: SPLADE 모델 로드 실패

**증상**: `torch.load` 오류 또는 `CVE-2025-32434` 오류

**해결**:
```bash
# RunPod 터미널에서 실행
# PyTorch 버전 확인
python -c "import torch; print(torch.__version__)"

# PyTorch 2.6 이상으로 업그레이드
pip install --upgrade torch>=2.6

# sentence-transformers 업그레이드
pip install --upgrade sentence-transformers>=5.0.0
```

### 문제 7: Google Drive에서 SSH 키 다운로드 실패

**증상**: `gdown` 명령어 실패

**해결**:
```bash
# gdown 설치 확인
pip install --upgrade gdown

# Google Drive 웹 UI에서 직접 다운로드
# 1. skn19.final.5team@gmail.com 계정으로 로그인
# 2. .ssh 폴더를 ZIP으로 다운로드
# 3. 압축 해제 후 ~/.ssh로 복사
```

---

## 📝 체크리스트

### 기본 설정
- [ ] Docker 컨테이너 실행 확인
- [ ] 스키마 생성 완료 (documents, chunks 테이블 존재)
- [ ] SPLADE 마이그레이션 실행 완료 (SPLADE 사용 시)
- [ ] 환경 변수 설정 완료

### RunPod 연결
- [ ] SSH 키 다운로드 완료
- [ ] RunPod 인스턴스 생성 및 SSH 접속 성공
- [ ] SSH 터널 연결 성공 (임베딩: `curl http://localhost:8001/` 성공)
- [ ] SPLADE 서버 SSH 터널 연결 성공 (SPLADE 사용 시)

### 서버 실행
- [ ] RunPod 임베딩 서버 실행 중
- [ ] RunPod SPLADE 서버 실행 중 (SPLADE 사용 시)

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

---

**업데이트**: 2026-01-09  
**최종 업데이트**: 2026-01-09 (순서 재정리 및 중복 제거)
