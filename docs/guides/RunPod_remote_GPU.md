# RunPod GPU 원격 활용 종합 가이드

**작성자**: Manus AI  
**최종 수정일**: 2026-01-04

이 문서는 로컬 개발 환경(WSL2)에서 RunPod의 강력한 GPU를 원격으로 활용하여 데이터 임베딩 작업을 수행하는 전체 과정을 상세하게 안내합니다. 지금까지 나눈 대화 내용을 바탕으로, 발생했던 모든 문제와 해결 과정을 포함한 최종 가이드입니다.

---

## 🎯 목표

로컬 PC의 개발 환경은 그대로 유지하면서, 계산 집약적인 임베딩 작업만 RunPod의 고성능 GPU에서 처리하여 작업 속도를 대폭 향상시키는 것을 목표로 합니다.

### 💡 핵심 아키텍처: SSH 포트 포워딩

```
로컬 PC (WSL2)                    RunPod GPU 인스턴스
┌─────────────────┐               ┌──────────────────┐
│ embed_data.py   │ ─SSH 터널─→  │ FastAPI 서버     │
│ (데이터 처리)   │               │ (KURE-v1 모델)   │
│                 │               │                  │
│ PostgreSQL (로컬)│ ←─임베딩 결과─ │ GPU 계산         │
└─────────────────┘               └──────────────────┘
```

**작동 원리:**
1.  **RunPod**: 간단한 FastAPI 서버를 배포하여, 텍스트를 입력받아 임베딩 벡터를 반환하는 API를 제공합니다.
2.  **로컬 PC**: SSH 터널을 통해 로컬의 특정 포트(예: 8001)를 RunPod 서버의 포트(8000)에 안전하게 연결합니다.
3.  **실행**: 로컬의 파이썬 스크립트는 `localhost:8001`로 임베딩 요청을 보냅니다. 이 요청은 SSH 터널을 통해 RunPod GPU로 전달되고, 계산된 결과만 다시 로컬로 돌아와 데이터베이스에 저장됩니다.

**장점:**
-   **보안**: 모든 통신이 SSH로 암호화되어 안전합니다.
-   **단순성**: 별도의 방화벽이나 공인 IP 설정이 필요 없습니다.
-   **편의성**: VSCode, 로컬 데이터베이스 등 기존 개발 환경을 그대로 사용할 수 있습니다.

---

## 📚 1부: RunPod 인스턴스 설정 및 서버 배포

### 1. RunPod 인스턴스 생성

1.  **RunPod 로그인**: [RunPod](https://www.runpod.io/)에 로그인합니다.
2.  **GPU 선택**: `Secure Cloud` 또는 `Community Cloud`에서 GPU를 선택합니다.
    -   **권장 GPU**: `NVIDIA RTX 4090` 또는 `NVIDIA A100` (PyTorch 안정 버전과 호환성이 좋음)
    -   **주의**: `NVIDIA RTX 5090`과 같은 최신 GPU는 PyTorch 안정 버전과 호환성 문제가 있을 수 있습니다. (3부 트러블슈팅 참조)
3.  **템플릿 선택**: `RunPod Pytorch 2.2` 또는 최신 PyTorch 템플릿을 선택합니다.
4.  **설정 및 배포**: 디스크 용량을 설정하고 `Deploy`를 클릭합니다.

### 2. SSH 접속 정보 확인

1.  `My Pods` 페이지로 이동합니다.
2.  생성된 인스턴스에서 `Connect` 버튼을 클릭합니다.
3.  `Connect via SSH` 탭에서 SSH 연결 명령어를 복사합니다. (예: `ssh user@host -p port`)

### 3. 임베딩 API 서버 배포

1.  **RunPod에 SSH 접속**: 로컬 PC의 터미널(WSL2)에서 복사한 명령어로 RunPod 인스턴스에 접속합니다.

2.  **필요한 패키지 설치**:
    ```bash
    pip install fastapi uvicorn sentence-transformers torch
    ```

3.  **API 서버 코드 작성**: `runpod_embed_server.py` 파일을 생성합니다.
    ```bash
    nano runpod_embed_server.py
    ```
    다음 코드를 붙여넣습니다:
    ```python
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
    ```

4.  **서버 실행**: `uvicorn`으로 서버를 실행합니다.
    ```bash
    uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
    ```
    **이 터미널 창은 계속 열어두어야 합니다.**

---

## 💻 2부: 로컬 환경 설정 및 실행

### 1. SSH 터널 연결

1.  로컬 PC에서 **새 터미널 창**(WSL2)을 엽니다.
2.  SSH 터널을 연결합니다. (1부 2단계에서 복사한 명령어 사용)
    ```bash
    ssh -L 8001:localhost:8000 [사용자명]@[IP 주소] -p [포트번호]
    ```
    **이 터미널 창도 계속 열어두어야 합니다.**

### 2. 로컬 임베딩 스크립트 준비

1.  프로젝트의 `backend/scripts/` 디렉토리에 `embed_data_remote.py` 파일을 생성합니다.
2.  다음 코드를 붙여넣습니다. 이 코드는 로컬에서 모델을 로드하는 대신 원격 API를 호출하도록 수정된 버전입니다.

    ```python
    # embed_data_remote.py
    import os
    import json
    import psycopg2
    from psycopg2.extras import execute_values
    from tqdm import tqdm
    from typing import List, Dict
    from dotenv import load_dotenv
    import requests

    class EmbeddingPipeline:
        def __init__(self, db_config: Dict[str, str], embed_api_url: str = "http://localhost:8001/embed"):
            self.db_config = db_config
            self.embed_api_url = embed_api_url
            self.conn = None
            self.test_api_connection()

        def test_api_connection(self):
            print(f"Testing connection to embedding API: {self.embed_api_url}")
            try:
                base_url = self.embed_api_url.rsplit('/', 1)[0]
                response = requests.get(base_url, timeout=5)
                response.raise_for_status()
                print(f"✅ API connection successful: {response.json()}")
            except requests.exceptions.RequestException as e:
                print(f"❌ API connection failed: {e}")
                raise

        def connect_db(self):
            print("Connecting to PostgreSQL...")
            self.conn = psycopg2.connect(**self.db_config)
            print("Connected to database.")

        def init_schema(self, schema_path: str):
            print(f"Initializing database schema from {schema_path}...")
            with self.conn.cursor() as cur:
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                cur.execute(schema_sql)
            self.conn.commit()
            print("Schema initialized successfully.")

        def load_jsonl(self, file_path: str) -> List[Dict]:
            print("Loading JSONL file...")
            with open(file_path, 'r', encoding='utf-8') as f:
                return [json.loads(line) for line in f]

        def insert_cases(self, records: List[Dict]):
            # ... (기존 코드와 동일)

        def embed_and_insert_chunks(self, records: List[Dict], batch_size: int = 32):
            print(f"Embedding and inserting {len(records)} chunks...")
            valid_records = [r for r in records if not r.get('drop', False)]
            print(f"Filtered to {len(valid_records)} valid chunks (drop=False).")

            with self.conn.cursor() as cur:
                for i in tqdm(range(0, len(valid_records), batch_size), desc="Embedding batches"):
                    batch_records = valid_records[i:i+batch_size]
                    texts = [r['content'] for r in batch_records]
                    
                    try:
                        response = requests.post(self.embed_api_url, json={"texts": texts}, timeout=60)
                        response.raise_for_status()
                        embeddings = response.json()['embeddings']
                    except requests.exceptions.RequestException as e:
                        print(f"\n❌ Error calling embedding API: {e}")
                        continue

                    values_to_insert = []
                    for idx, record in enumerate(batch_records):
                        values_to_insert.append((
                            record['case_uid'],
                            record['chunk_id'],
                            record['chunk_type'],
                            record['content'],
                            embeddings[idx]
                        ))
                    
                    execute_values(
                        cur,
                        "INSERT INTO chunks (case_uid, chunk_id, chunk_type, content, embedding) VALUES %s ON CONFLICT (chunk_id) DO NOTHING",
                        values_to_insert
                    )
            self.conn.commit()
            print("Embedding and insertion complete.")

        # ... (process_all_files, main 함수 등 나머지 코드는 기존과 거의 동일하게 유지)

    def main():
        load_dotenv()
        db_config = { # ... }
        embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
        pipeline = EmbeddingPipeline(db_config, embed_api_url)
        # ...
    ```
    *(전체 코드는 제공된 `embed_data_remote.py` 파일 참조)*

### 3. 데이터베이스 초기화 (필요시)

이전에 임베딩을 실행한 적이 있다면, 데이터베이스에 테이블이 이미 존재하여 오류가 발생합니다. 다음 명령어로 기존 테이블을 삭제합니다.

```bash
# 1. PostgreSQL 컨테이너 접속
docker exec -it ddoksori_db psql -U postgres -d ddoksori

# 2. 기존 테이블 삭제
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS cases CASCADE;

# 3. 종료
\q
```

### 4. 임베딩 스크립트 실행

모든 준비가 완료되면 로컬에서 스크립트를 실행합니다.

```bash
cd ~/ddoksori_demo/backend
python scripts/embed_data_remote.py
```

스크립트가 실행되면, RunPod 서버와 SSH 터널 터미널에서 통신이 발생하는 것을 확인할 수 있습니다.

---

## 🔧 3부: 트러블슈팅

### 문제 1: `psycopg2.errors.DuplicateTable` 오류
-   **원인**: 데이터베이스에 테이블이 이미 존재합니다.
-   **해결**: 위 **2부 3단계**를 참고하여 데이터베이스를 초기화하세요.

### 문제 2: `❌ API connection failed` 오류
-   **원인**: 로컬 스크립트가 RunPod 서버에 연결하지 못했습니다.
-   **해결**:
    1.  RunPod 서버 터미널에서 `uvicorn`이 실행 중인지 확인하세요.
    2.  SSH 터널 터미널이 연결 상태를 유지하고 있는지 확인하세요.
    3.  로컬의 새 터미널에서 `curl http://localhost:8001/` 명령어로 연결을 테스트하세요.

### 문제 3: `500 Internal Server Error` 발생
-   **원인**: RunPod 서버 내부에서 오류가 발생했습니다. 대부분 GPU와 PyTorch 버전 호환성 문제입니다.
-   **로그 확인**: RunPod의 `uvicorn` 터미널에 출력된 에러 로그를 확인하세요.
    ```
    NVIDIA GeForce RTX 5090 ... is not compatible with the current PyTorch installation.
    ```
-   **해결 방법**:
    1.  **GPU 변경 (권장)**: 인스턴스를 종료하고 `RTX 4090` 등 호환성이 좋은 GPU로 다시 생성하세요.
    2.  **PyTorch Nightly 설치**: RunPod 터미널에서 다음 명령어로 최신 PyTorch를 설치하세요.
        ```bash
        pip uninstall torch -y
        pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124
        ```
    3.  **CPU 모드 전환 (임시)**: `runpod_embed_server.py`에서 `device = 'cpu'`로 강제 변경하세요.

### 문제 4: 임베딩 속도가 여전히 느림
-   **원인**: 배치 크기가 GPU에 비해 너무 작거나 큽니다.
-   **해결**: 로컬의 `embed_data_remote.py`에서 `batch_size`를 조절하세요. (예: 16, 32, 64, 128)

---

이 가이드를 통해 로컬 환경의 편의성과 원격 고성능 GPU의 장점을 모두 활용하여 효율적으로 개발을 진행할 수 있습니다. 궁금한 점이 있다면 언제든지 다시 질문해 주세요.
