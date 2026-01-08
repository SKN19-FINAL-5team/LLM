# 환경 변수 설정 가이드

## 개요

이 프로젝트는 백엔드와 프론트엔드에서 각각 환경 변수를 사용합니다. 개발을 시작하기 전에 `.env` 파일을 생성하고 필요한 값을 설정해야 합니다.

## 설정 방법

### 1. 백엔드 환경 변수 설정

```bash
# backend 디렉토리로 이동
cd backend

# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일을 편집하여 실제 값 입력
nano .env  # 또는 선호하는 에디터 사용
```

**필수 설정 항목 (PR #1):**
- `DATABASE_URL`: PostgreSQL 연결 문자열 (기본값 사용 가능)
- `SECRET_KEY`: JWT 토큰 생성용 비밀키 (랜덤 문자열 생성 권장)

**추후 필요 항목:**
- `OPENAI_API_KEY`: OpenAI API 키 (PR #3부터 필요)
- `ANTHROPIC_API_KEY`: Anthropic API 키 (PR #3부터 필요, 선택사항)
- `LANGCHAIN_API_KEY`: LangSmith API 키 (PR #8부터 필요, 선택사항)

### 2. 프론트엔드 환경 변수 설정

```bash
# frontend 디렉토리로 이동
cd frontend

# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일을 편집하여 실제 값 입력
nano .env  # 또는 선호하는 에디터 사용
```

**필수 설정 항목:**
- `VITE_API_URL`: 백엔드 API 서버 주소 (기본값: `http://localhost:8000`)

## Docker Compose 사용 시

Docker Compose를 사용하는 경우, `docker-compose.yml` 파일에서 환경 변수를 직접 설정하거나, `.env` 파일을 통해 주입할 수 있습니다.

```bash
# 프로젝트 루트에서 실행
docker-compose up --build
```

## 보안 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요. (`.gitignore`에 이미 추가되어 있음)
- API 키와 비밀키는 안전하게 보관하세요.
- 프로덕션 환경에서는 환경 변수를 서버 설정 또는 CI/CD 파이프라인을 통해 주입하세요.

## SECRET_KEY 생성 방법

Python을 사용하여 안전한 SECRET_KEY를 생성할 수 있습니다:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

생성된 문자열을 `backend/.env` 파일의 `SECRET_KEY`에 입력하세요.
