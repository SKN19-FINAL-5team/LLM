#    

## 

       .    `.env`      .

##  

### 1.    

```bash
# backend  
cd backend

# .env.example  .env  
cp .env.example .env

# .env     
nano .env  #    
```

**   (PR #1):**
- `DATABASE_URL`: PostgreSQL   (  )
- `SECRET_KEY`: JWT    (   )

**  :**
- `OPENAI_API_KEY`: OpenAI API  (PR #3 )
- `ANTHROPIC_API_KEY`: Anthropic API  (PR #3 , )
- `LANGCHAIN_API_KEY`: LangSmith API  (PR #8 , )

### 2.    

```bash
# frontend  
cd frontend

# .env.example  .env  
cp .env.example .env

# .env     
nano .env  #    
```

**  :**
- `VITE_API_URL`:  API   (: `http://localhost:8000`)

## Docker Compose  

Docker Compose  , `docker-compose.yml`     , `.env`     .

```bash
#   
docker-compose up --build
```

##  

- `.env`   Git  . (`.gitignore`   )
- API    .
-        CI/CD   .

## SECRET_KEY  

Python   SECRET_KEY   :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

  `backend/.env`  `SECRET_KEY` .
