# Docker      

****: 2026-01-05  
****:  (ddoksori_demo)  
****: Docker Inspect   

---

##    

### 1.  

```yaml
# docker-compose.yml
services:
  backend:
    env_file:
      - ./backend/.env    #  .env   
    environment:
      - DB_HOST=db
      - DB_PORT=5432
```

### 2.  

####    
- `.env`  `.gitignore`  
- Git     

####  
1. **Docker Inspect **
   - `docker inspect ddoksori_backend`     
   - Docker Desktop UI Inspect   
   -       

2. **   **
   -  PC    
   -      
   -     

3. **   **
   -     API  
   -      
   -      

---

##    

###    ()

****:  

****:
-  PC     
-   
-  API   (  )

**  **:  ****
-   `.env`   
-    
- ,     

### / 

****:  

****:
-    
-      
-   (GDPR, PCI-DSS ) 

**  **:  ****
-     
- Secret   

---

##   

###  1: Docker Secrets (Docker Swarm)

** **:    
****:   
** **: 

#### 

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    image: ddoksori-backend:latest
    secrets:
      - db_password
      - openai_api_key
      - anthropic_api_key
    environment:
      - DB_HOST=db
      - DB_USER=postgres
      - DB_PASSWORD_FILE=/run/secrets/db_password
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key

secrets:
  db_password:
    external: true
  openai_api_key:
    external: true
  anthropic_api_key:
    external: true
```

####  

```python
# backend/app/config.py
import os
from pathlib import Path

def read_secret(secret_name: str, default: str = None) -> str:
    """Docker Secret    """
    # Docker Secret  
    secret_file = Path(f"/run/secrets/{secret_name}")
    
    if secret_file.exists():
        return secret_file.read_text().strip()
    
    #  fallback ( )
    env_var = os.getenv(secret_name.upper())
    if env_var:
        return env_var
    
    return default

class Settings:
    DB_PASSWORD = read_secret("db_password", os.getenv("DB_PASSWORD"))
    OPENAI_API_KEY = read_secret("openai_api_key", os.getenv("OPENAI_API_KEY"))
```

#### 
- Docker Inspect Secret   
-   
-   

#### 
- Docker Swarm  
-     

---

###  2: Kubernetes Secrets (K8s )

** **:   (Kubernetes)  
****:   
** **: 

#### 

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ddoksori-secrets
type: Opaque
data:
  db-password: <base64-encoded>
  openai-api-key: <base64-encoded>
  anthropic-api-key: <base64-encoded>
```

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ddoksori-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        image: ddoksori-backend:latest
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: ddoksori-secrets
              key: db-password
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ddoksori-secrets
              key: openai-api-key
```

#### 
- Kubernetes  Secret 
- RBAC  
- etcd  

#### 
- Kubernetes  
-   

---

###  3: AWS Secrets Manager / Azure Key Vault

** **:   ()  
****:   
** **:  

####  (AWS Secrets Manager)

```python
# backend/app/config.py
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name: str, region: str = "ap-northeast-2") -> dict:
    """AWS Secrets Manager Secret """
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region
    )
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        raise e

class Settings:
    #  :  
    # : AWS Secrets Manager 
    if os.getenv("ENV") == "production":
        secrets = get_secret("ddoksori/prod")
        DB_PASSWORD = secrets["db_password"]
        OPENAI_API_KEY = secrets["openai_api_key"]
    else:
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

#### 
-   Secret 
-   
-   (CloudTrail)
-    (IAM)

#### 
-  
-   
-  

---

###  4: .env  +   (:  )

** **:   +    
****:   
** **: 

#### 

```
#  
backend/
 .env.example          # Git  ()
 .env.development      #   (Git )
 .env.staging          #  (Git )
 .env.production       #  (Git ,  )
```

```bash
# .env.example (Git )
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=<YOUR_PASSWORD>

# API Keys
OPENAI_API_KEY=<YOUR_OPENAI_KEY>
ANTHROPIC_API_KEY=<YOUR_ANTHROPIC_KEY>
EMBED_API_URL=http://localhost:8001/embed

# Environment
ENV=development
```

```bash
# .env.development ( )
DB_PASSWORD=postgres
OPENAI_API_KEY=sk-dev-xxxxx
ANTHROPIC_API_KEY=sk-ant-dev-xxxxx
ENV=development
```

```bash
# .env.production (,  )
DB_PASSWORD=<STRONG_RANDOM_PASSWORD>
OPENAI_API_KEY=sk-prod-xxxxx
ANTHROPIC_API_KEY=sk-ant-prod-xxxxx
ENV=production
```

```yaml
# docker-compose.yml ( )
services:
  backend:
    env_file:
      - ./backend/.env.development
```

```yaml
# docker-compose.prod.yml ()
services:
  backend:
    env_file:
      - ./backend/.env.production
```

#### 
-  
-   
-   

#### 
-  Docker Inspect  
-   

---

##    

### Phase 1:  ( )

****:  

** **:
1. `.env.example`   ()
2. README    
3.  API   (  )

### Phase 2:   (MVP)

****:  ,  

** **:  4 ( )

** **:
1. `.env.production`   ()
2.   
3.    (, SSH )
4.   

### Phase 3:  

****: ,  

** **:  2 (Kubernetes Secrets)   3 (AWS Secrets Manager)

** **:
1. Kubernetes   Secret  
2.    
3.   
4.   

### Phase 4: 

****:  ,   

** **:  3 ( Secret ) + HSM

** **:
1. Hardware Security Module (HSM) 
2.   (MFA) 
3.   
4.    (ISO 27001 )

---

##      

### 1. .env.example  

```bash
# backend/.env.example
#  
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=your_secure_password_here

# API Keys ()
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

#  API
EMBED_API_URL=http://localhost:8001/embed

# 
ENV=development
```

### 2. README   

```markdown
##  

1. `.env.example`  `.env`  :
   ```bash
   cp backend/.env.example backend/.env
   ```

2. `.env`    

 ** **:
- `.env`  Git  
-     
- API    
```

### 3.    

```python
# backend/app/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_PASSWORD: str
    OPENAI_API_KEY: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __repr__(self):
        #   
        return f"Settings(DB_PASSWORD='***', OPENAI_API_KEY='***')"
```

---

##    

###   

**  **:  ****
- `.env`    
- `.gitignore`  
-    

**  **:  ** **
-       
- Secret    

###   

1.  `.env.example`  
2.  README   
3.  / API  

###    

1.   `.env`  
2.    
3.    
4.     

###  

- **MVP **:   ( 4)
- ** **: Kubernetes Secrets  AWS Secrets Manager ( 2/3)
- ****:  Secret  + HSM ( 3+)

---

****: Manus AI ( )  
** **: 2026-01-05
