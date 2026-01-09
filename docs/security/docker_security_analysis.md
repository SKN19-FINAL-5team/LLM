# Docker 환경변수 보안 분석 및 개선 방안

**작성일**: 2026-01-05  
**프로젝트**: 똑소리 (ddoksori_demo)  
**이슈**: Docker Inspect를 통한 환경변수 노출

---

## 🔍 현재 상황 분석

### 1. 현재 구조

```yaml
# docker-compose.yml
services:
  backend:
    env_file:
      - ./backend/.env    # ⚠️ .env 파일 직접 참조
    environment:
      - DB_HOST=db
      - DB_PORT=5432
```

### 2. 보안 문제점

#### ✅ 잘 된 부분
- `.env` 파일이 `.gitignore`에 포함되어 있음
- Git 저장소에 민감 정보가 커밋되지 않음

#### ❌ 문제점
1. **Docker Inspect 노출**
   - `docker inspect ddoksori_backend` 명령으로 모든 환경변수 확인 가능
   - Docker Desktop UI의 Inspect 탭에서 평문으로 노출
   - 컨테이너에 접근 권한이 있는 누구나 확인 가능

2. **로컬 개발 환경에서의 위험**
   - 개발자 PC가 해킹당하면 모든 키 노출
   - 화면 공유 시 실수로 노출 가능
   - 로그에 환경변수가 기록될 수 있음

3. **프로덕션 배포 시 위험**
   - 서버 침입 시 모든 API 키 노출
   - 컨테이너 탈취 시 민감 정보 유출
   - 로그 수집 시스템에 환경변수 노출 가능

---

## 🎯 환경별 보안 수준

### 로컬 개발 환경 (현재)

**위험도**: 🟡 중간

**이유**:
- 개발자 PC는 일반적으로 신뢰할 수 있는 환경
- 외부 접근이 제한됨
- 개발용 API 키 사용 (프로덕션 키와 분리)

**현재 방식의 적절성**: ✅ **적절함**
- 로컬 개발에서는 `.env` 파일 사용이 표준
- 개발 편의성과 보안의 균형
- 단, 프로덕션 키를 사용하지 않아야 함

### 스테이징/프로덕션 환경

**위험도**: 🔴 높음

**이유**:
- 서버는 외부 공격 대상
- 컨테이너 탈취 시 모든 키 노출
- 규정 준수 (GDPR, PCI-DSS 등) 필요

**현재 방식의 적절성**: ❌ **부적절함**
- 프로덕션에서는 더 강력한 보안 필요
- Secret 관리 시스템 필수

---

## 🛡 개선 방안

### 방안 1: Docker Secrets (Docker Swarm)

**적용 대상**: 프로덕션 환경  
**난이도**: 중간  
**보안 수준**: 높음

#### 구현

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

#### 코드 수정

```python
# backend/app/config.py
import os
from pathlib import Path

def read_secret(secret_name: str, default: str = None) -> str:
    """Docker Secret 또는 환경변수에서 값 읽기"""
    # Docker Secret 파일 경로
    secret_file = Path(f"/run/secrets/{secret_name}")
    
    if secret_file.exists():
        return secret_file.read_text().strip()
    
    # 환경변수 fallback (로컬 개발용)
    env_var = os.getenv(secret_name.upper())
    if env_var:
        return env_var
    
    return default

class Settings:
    DB_PASSWORD = read_secret("db_password", os.getenv("DB_PASSWORD"))
    OPENAI_API_KEY = read_secret("openai_api_key", os.getenv("OPENAI_API_KEY"))
```

#### 장점
- Docker Inspect로 Secret 내용 확인 불가
- 암호화된 상태로 저장
- 컨테이너 내부에서만 복호화

#### 단점
- Docker Swarm 모드 필요
- 로컬 개발 환경에서는 사용 어려움

---

### 방안 2: Kubernetes Secrets (K8s 환경)

**적용 대상**: 프로덕션 환경 (Kubernetes)  
**난이도**: 중간  
**보안 수준**: 높음

#### 구현

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

#### 장점
- Kubernetes 네이티브 Secret 관리
- RBAC로 접근 제어
- etcd 암호화 지원

#### 단점
- Kubernetes 환경 필요
- 초기 설정 복잡

---

### 방안 3: AWS Secrets Manager / Azure Key Vault

**적용 대상**: 프로덕션 환경 (클라우드)  
**난이도**: 중간  
**보안 수준**: 매우 높음

#### 구현 (AWS Secrets Manager)

```python
# backend/app/config.py
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name: str, region: str = "ap-northeast-2") -> dict:
    """AWS Secrets Manager에서 Secret 가져오기"""
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
    # 로컬 개발: 환경변수 사용
    # 프로덕션: AWS Secrets Manager 사용
    if os.getenv("ENV") == "production":
        secrets = get_secret("ddoksori/prod")
        DB_PASSWORD = secrets["db_password"]
        OPENAI_API_KEY = secrets["openai_api_key"]
    else:
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

#### 장점
- 중앙 집중식 Secret 관리
- 자동 로테이션 지원
- 감사 로그 (CloudTrail)
- 세밀한 접근 제어 (IAM)

#### 단점
- 클라우드 종속
- 추가 비용 발생
- 네트워크 지연

---

### 방안 4: .env 파일 + 환경 분리 (권장: 현재 단계)

**적용 대상**: 로컬 개발 + 초기 배포  
**난이도**: 낮음  
**보안 수준**: 중간

#### 구현

```
# 디렉토리 구조
backend/
├── .env.example          # Git에 커밋 (템플릿)
├── .env.development      # 로컬 개발용 (Git 제외)
├── .env.staging          # 스테이징용 (Git 제외)
└── .env.production       # 프로덕션용 (Git 제외, 서버에서만 생성)
```

```bash
# .env.example (Git에 커밋)
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
# .env.development (로컬 개발용)
DB_PASSWORD=postgres
OPENAI_API_KEY=sk-dev-xxxxx
ANTHROPIC_API_KEY=sk-ant-dev-xxxxx
ENV=development
```

```bash
# .env.production (프로덕션용, 서버에서만 생성)
DB_PASSWORD=<STRONG_RANDOM_PASSWORD>
OPENAI_API_KEY=sk-prod-xxxxx
ANTHROPIC_API_KEY=sk-ant-prod-xxxxx
ENV=production
```

```yaml
# docker-compose.yml (로컬 개발)
services:
  backend:
    env_file:
      - ./backend/.env.development
```

```yaml
# docker-compose.prod.yml (프로덕션)
services:
  backend:
    env_file:
      - ./backend/.env.production
```

#### 장점
- 구현 간단
- 환경별 설정 분리
- 개발 편의성 유지

#### 단점
- 여전히 Docker Inspect로 확인 가능
- 파일 관리 필요

---

## 📋 단계별 개선 로드맵

### Phase 1: 현재 (로컬 개발)

**상태**: ✅ 적절함

**조치 사항**:
1. `.env.example` 파일 생성 (템플릿)
2. README에 환경변수 설정 가이드 추가
3. 개발용 API 키 사용 (프로덕션 키와 분리)

### Phase 2: 초기 배포 (MVP)

**목표**: 빠른 배포, 기본 보안

**권장 방안**: 방안 4 (환경 분리)

**조치 사항**:
1. `.env.production` 파일 생성 (서버에서만)
2. 강력한 비밀번호 사용
3. 서버 접근 제한 (방화벽, SSH 키)
4. 정기적인 키 로테이션

### Phase 3: 성장 단계

**목표**: 확장성, 보안 강화

**권장 방안**: 방안 2 (Kubernetes Secrets) 또는 방안 3 (AWS Secrets Manager)

**조치 사항**:
1. Kubernetes 또는 클라우드 Secret 관리 도입
2. 자동 키 로테이션 설정
3. 감사 로그 활성화
4. 보안 스캔 자동화

### Phase 4: 엔터프라이즈

**목표**: 규정 준수, 최고 수준 보안

**권장 방안**: 방안 3 (클라우드 Secret 관리) + HSM

**조치 사항**:
1. Hardware Security Module (HSM) 사용
2. 다중 인증 (MFA) 필수
3. 정기 보안 감사
4. 규정 준수 인증 (ISO 27001 등)

---

## 🎯 즉시 적용 가능한 개선 사항

### 1. .env.example 파일 생성

```bash
# backend/.env.example
# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=your_secure_password_here

# API Keys (개발용)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# 임베딩 API
EMBED_API_URL=http://localhost:8001/embed

# 환경
ENV=development
```

### 2. README에 보안 가이드 추가

```markdown
## 환경변수 설정

1. `.env.example`을 복사하여 `.env` 파일 생성:
   ```bash
   cp backend/.env.example backend/.env
   ```

2. `.env` 파일에 실제 값 입력

⚠️ **보안 주의사항**:
- `.env` 파일을 Git에 커밋하지 마세요
- 프로덕션 환경에서는 강력한 비밀번호 사용
- API 키는 개발용과 프로덕션용을 분리하세요
```

### 3. 민감 정보 로깅 방지

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
        # 민감 정보 마스킹
        return f"Settings(DB_PASSWORD='***', OPENAI_API_KEY='***')"
```

---

## 💡 결론 및 권장사항

### 현재 상황 평가

**로컬 개발 환경**: ✅ **적절함**
- `.env` 파일 사용은 표준 관행
- `.gitignore`에 포함되어 있음
- 개발 편의성과 보안의 균형

**프로덕션 배포 계획**: ⚠️ **개선 필요**
- 현재 방식으로 프로덕션 배포 시 보안 위험
- Secret 관리 시스템 도입 필요

### 즉시 조치 사항

1. ✅ `.env.example` 파일 생성
2. ✅ README에 보안 가이드 추가
3. ✅ 개발용/프로덕션용 API 키 분리

### 배포 전 필수 조치

1. 🔒 환경별 `.env` 파일 분리
2. 🔒 강력한 비밀번호 사용
3. 🔒 서버 접근 제한
4. 🔒 정기적인 키 로테이션 계획

### 장기 계획

- **MVP 단계**: 환경 분리 (방안 4)
- **성장 단계**: Kubernetes Secrets 또는 AWS Secrets Manager (방안 2/3)
- **엔터프라이즈**: 클라우드 Secret 관리 + HSM (방안 3+)

---

**작성자**: Manus AI (보안 전문가)  
**최종 수정**: 2026-01-05
