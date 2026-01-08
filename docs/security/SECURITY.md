# 보안 가이드라인

이 문서는 프로젝트의 보안 관련 설정 및 모범 사례를 설명합니다.

## 환경 변수 관리

### 1. `.env` 파일 사용

모든 민감한 정보(API 키, 데이터베이스 비밀번호 등)는 `.env` 파일에 저장하고, 절대로 Git에 커밋하지 마세요.

```bash
# .env 파일 생성
cp backend/.env.example backend/.env

# .env 파일 편집하여 실제 값 입력
```

### 2. `.env.example` 파일

`.env.example` 파일은 필요한 환경 변수의 목록과 형식을 보여주는 템플릿입니다. 실제 값이 아닌 플레이스홀더를 사용합니다.

**올바른 예시:**
```env
OPENAI_API_KEY=your_openai_api_key_here
DB_PASSWORD=your_secure_password_here
```

**잘못된 예시:**
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # 실제 키처럼 보이는 예시는 피하세요
DB_PASSWORD=postgres  # 실제 비밀번호를 예시로 사용하지 마세요
```

### 3. Docker Compose 환경 변수

`docker-compose.yml`에서는 환경 변수를 직접 하드코딩하지 않고, `.env` 파일에서 읽어옵니다.

```yaml
# 올바른 방법
environment:
  POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}

# 잘못된 방법
environment:
  POSTGRES_PASSWORD: postgres  # 하드코딩 금지
```

## `.gitignore` 설정

다음 파일들은 반드시 `.gitignore`에 포함되어야 합니다:

- `.env` (모든 환경 변수 파일)
- `*.log` (로그 파일)
- `__pycache__/`, `node_modules/` (의존성 캐시)
- `.vscode/`, `.idea/` (IDE 설정 파일)

## `.dockerignore` 설정

Docker 이미지를 빌드할 때 불필요한 파일을 제외하여 이미지 크기를 줄이고 보안을 강화합니다.

**제외해야 할 파일:**
- `.env` (환경 변수)
- `.git/` (Git 히스토리)
- `node_modules/`, `__pycache__/` (의존성 캐시)
- `tests/`, `docs/` (테스트 및 문서)
- `*.md` (README 등)

## API 키 관리

### OpenAI API 키

1. [OpenAI Platform](https://platform.openai.com/api-keys)에서 API 키를 생성합니다.
2. `.env` 파일에 추가합니다:
   ```env
   OPENAI_API_KEY=sk-proj-your_actual_key_here
   ```
3. 절대로 코드나 문서에 실제 키를 포함하지 마세요.

### 데이터베이스 비밀번호

1. 개발 환경에서도 기본 비밀번호(`postgres`)를 사용하지 말고, 안전한 비밀번호를 생성합니다.
2. `.env` 파일에 추가합니다:
   ```env
   DB_PASSWORD=your_secure_password_here
   ```

## 프로덕션 배포 시 주의사항

프로덕션 환경에 배포할 때는 다음 사항을 반드시 확인하세요:

1. **DEBUG 모드 비활성화**: `DEBUG=False`
2. **강력한 SECRET_KEY 사용**: 랜덤 문자열 생성
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. **CORS 설정 제한**: 신뢰할 수 있는 도메인만 허용
4. **HTTPS 사용**: SSL/TLS 인증서 적용
5. **환경 변수 암호화**: AWS Secrets Manager, Azure Key Vault 등 사용

## 보안 문제 보고

보안 취약점을 발견하신 경우, 공개 이슈 트래커에 게시하지 말고 프로젝트 관리자에게 직접 연락해 주세요.

---

**최종 수정일**: 2026-01-04
