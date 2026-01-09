# RunPod GPU    

****: Manus AI  
** **: 2026-01-04

    (WSL2) RunPod  GPU          .     ,        .

---

##  

 PC    ,     RunPod  GPU        .

###   : SSH  

```
 PC (WSL2)                    RunPod GPU 
               
 embed_data.py    SSH →   FastAPI      
 ( )                   (KURE-v1 )   
                                                  
 PostgreSQL () ←   GPU          
               
```

** :**
1.  **RunPod**:  FastAPI  ,      API .
2.  ** PC**: SSH     (: 8001) RunPod  (8000)  .
3.  ****:    `localhost:8001`   .   SSH   RunPod GPU ,       .

**:**
-   ****:   SSH  .
-   ****:    IP   .
-   ****: VSCode,          .

---

##  1: RunPod     

### 1. RunPod  

1.  **RunPod **: [RunPod](https://www.runpod.io/) .
2.  **GPU **: `Secure Cloud`  `Community Cloud` GPU .
    -   ** GPU**: `NVIDIA RTX 4090`  `NVIDIA A100` (PyTorch    )
    -   ****: `NVIDIA RTX 5090`   GPU PyTorch       . (3  )
3.  ** **: `RunPod Pytorch 2.2`   PyTorch  .
4.  **  **:    `Deploy` .

### 2. SSH   

1.  `My Pods`  .
2.    `Connect`  .
3.  `Connect via SSH`  SSH   . (: `ssh user@host -p port`)

### 3.  API  

1.  **RunPod SSH **:  PC (WSL2)   RunPod  .

2.  **  **:
    ```bash
    pip install fastapi uvicorn sentence-transformers torch
    ```

3.  **API   **: `runpod_embed_server.py`  .
    ```bash
    nano runpod_embed_server.py
    ```
      :
    ```python
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from sentence_transformers import SentenceTransformer
    import torch
    from typing import List
    import traceback

    # GPU    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Loading model on {device}...")

    model = SentenceTransformer('nlpai-lab/KURE-v1', device=device)
    print(f" Model loaded successfully on {device}!")

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
            print(f" Embedding error: {e}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    def root():
        return {"message": "Embedding server is running", "device": device}
    ```

4.  ** **: `uvicorn`  .
    ```bash
    uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
    ```
    **     .**

---

##  2:     

### 1. SSH  

1.   PC **  **(WSL2) .
2.  SSH  . (1 2   )
    ```bash
    ssh -L 8001:localhost:8000 []@[IP ] -p []
    ```
    **     .**

### 2.    

1.   `backend/scripts/`  `embed_data_remote.py`  .
2.    .        API   .

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
                print(f" API connection successful: {response.json()}")
            except requests.exceptions.RequestException as e:
                print(f" API connection failed: {e}")
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
            # ... (  )

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
                        print(f"\n Error calling embedding API: {e}")
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

        # ... (process_all_files, main        )

    def main():
        load_dotenv()
        db_config = { # ... }
        embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
        pipeline = EmbeddingPipeline(db_config, embed_api_url)
        # ...
    ```
    *(   `embed_data_remote.py`  )*

### 3.   ()

    ,      .     .

```bash
# 1. PostgreSQL  
docker exec -it ddoksori_db psql -U postgres -d ddoksori

# 2.   
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS cases CASCADE;

# 3. 
\q
```

### 4.   

     .

```bash
cd ~/ddoksori_demo/backend
python scripts/embed_data_remote.py
```

 , RunPod  SSH        .

---

##  3: 

###  1: `psycopg2.errors.DuplicateTable` 
-   ****:    .
-   ****:  **2 3**   .

###  2: ` API connection failed` 
-   ****:   RunPod   .
-   ****:
    1.  RunPod   `uvicorn`   .
    2.  SSH       .
    3.     `curl http://localhost:8001/`   .

###  3: `500 Internal Server Error` 
-   ****: RunPod    .  GPU PyTorch   .
-   ** **: RunPod `uvicorn`     .
    ```
    NVIDIA GeForce RTX 5090 ... is not compatible with the current PyTorch installation.
    ```
-   ** **:
    1.  **GPU  ()**:   `RTX 4090`    GPU  .
    2.  **PyTorch Nightly **: RunPod     PyTorch .
        ```bash
        pip uninstall torch -y
        pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124
        ```
    3.  **CPU   ()**: `runpod_embed_server.py` `device = 'cpu'`  .

###  4:    
-   ****:   GPU    .
-   ****:  `embed_data_remote.py` `batch_size` . (: 16, 32, 64, 128)

---

        GPU        .       .
