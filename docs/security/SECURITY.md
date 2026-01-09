#  

         .

##   

### 1. `.env`  

  (API ,   ) `.env`  ,  Git  .

```bash
# .env  
cp backend/.env.example backend/.env

# .env     
```

### 2. `.env.example` 

`.env.example`        .     .

** :**
```env
OPENAI_API_KEY=your_openai_api_key_here
DB_PASSWORD=your_secure_password_here
```

** :**
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  #     
DB_PASSWORD=postgres  #     
```

### 3. Docker Compose  

`docker-compose.yml`     , `.env`  .

```yaml
#  
environment:
  POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}

#  
environment:
  POSTGRES_PASSWORD: postgres  #  
```

## `.gitignore` 

   `.gitignore`  :

- `.env` (   )
- `*.log` ( )
- `__pycache__/`, `node_modules/` ( )
- `.vscode/`, `.idea/` (IDE  )

## `.dockerignore` 

Docker           .

**  :**
- `.env` ( )
- `.git/` (Git )
- `node_modules/`, `__pycache__/` ( )
- `tests/`, `docs/` (  )
- `*.md` (README )

## API  

### OpenAI API 

1. [OpenAI Platform](https://platform.openai.com/api-keys) API  .
2. `.env`  :
   ```env
   OPENAI_API_KEY=sk-proj-your_actual_key_here
   ```
3.       .

###  

1.    (`postgres`)  ,   .
2. `.env`  :
   ```env
   DB_PASSWORD=your_secure_password_here
   ```

##    

       :

1. **DEBUG  **: `DEBUG=False`
2. ** SECRET_KEY **:   
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. **CORS  **:     
4. **HTTPS **: SSL/TLS  
5. **  **: AWS Secrets Manager, Azure Key Vault  

##   

   ,          .

---

** **: 2026-01-04
