import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
from fastmcp import FastMCP

from app.rag import VectorRetriever, RAGGenerator

#   
load_dotenv()

app = FastAPI(
    title=" API",
    version="0.3.0",
    description="    RAG  API"
)

# CORS 
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

# RAG  
retriever = VectorRetriever(db_config)
generator = RAGGenerator()


# Request/Response 
class ChatRequest(BaseModel):
    message: str
    top_k: Optional[int] = 5
    chunk_types: Optional[List[str]] = None
    agencies: Optional[List[str]] = None


class ChatResponse(BaseModel):
    answer: str
    chunks_used: int
    model: str
    sources: List[dict]


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    chunk_types: Optional[List[str]] = None
    agencies: Optional[List[str]] = None


# API 
@app.get("/")
async def root():
    return {
        "message": " API    .",
        "version": "0.3.0",
        "features": ["RAG ", "LLM  "]
    }


@app.get("/health")
async def health_check():
    """  """
    try:
        # DB  
        retriever.connect_db()
        retriever.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/search")
async def search(request: SearchRequest):
    """
    Vector DB    (LLM    )
    
    Args:
        query:  
        top_k:    
        chunk_types:    (: ['decision', 'reasoning'])
        agencies:   (: ['kca', 'ecmc'])
    
    Returns:
          
    """
    try:
        chunks = retriever.search(
            query=request.query,
            top_k=request.top_k,
            chunk_types=request.chunk_types,
            agencies=request.agencies
        )
        
        return {
            "query": request.query,
            "results_count": len(chunks),
            "results": chunks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"   : {str(e)}")
    finally:
        retriever.close()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG    
    
    Args:
        message:  
        top_k:    
        chunk_types:   
        agencies:  
    
    Returns:
        LLM     
    """
    try:
        # 1. Vector DB   
        chunks = retriever.search(
            query=request.message,
            top_k=request.top_k,
            chunk_types=request.chunk_types,
            agencies=request.agencies
        )
        
        if not chunks:
            return ChatResponse(
                answer=".      .   ?",
                chunks_used=0,
                model=generator.model,
                sources=[]
            )
        
        # 2. LLM  
        result = generator.generate_answer(
            query=request.message,
            chunks=chunks
        )
        
        # 3.  
        sources = [
            {
                'case_no': chunk.get('case_no'),
                'agency': chunk.get('agency'),
                'decision_date': chunk.get('decision_date'),
                'chunk_type': chunk.get('chunk_type'),
                'similarity': chunk.get('similarity')
            }
            for chunk in chunks
        ]
        
        return ChatResponse(
            answer=result['answer'],
            chunks_used=result['chunks_used'],
            model=result['model'],
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"    : {str(e)}")
    finally:
        retriever.close()


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    RAG     
    
    Args:
        message:  
        top_k:    
        chunk_types:   
        agencies:  
    
    Returns:
          
    """
    try:
        # Vector DB   
        chunks = retriever.search(
            query=request.message,
            top_k=request.top_k,
            chunk_types=request.chunk_types,
            agencies=request.agencies
        )
        
        if not chunks:
            async def no_results():
                yield ".      ."
            return StreamingResponse(no_results(), media_type="text/plain")
        
        #   
        return StreamingResponse(
            generator.generate_answer_stream(
                query=request.message,
                chunks=chunks
            ),
            media_type="text/plain"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"    : {str(e)}")
    finally:
        retriever.close()


@app.get("/case/{case_uid}")
async def get_case(case_uid: str):
    """
        
    
    Args:
        case_uid:   ID
    
    Returns:
           
    """
    try:
        chunks = retriever.get_case_chunks(case_uid)
        
        if not chunks:
            raise HTTPException(status_code=404, detail="   .")
        
        return {
            "case_uid": case_uid,
            "chunks_count": len(chunks),
            "chunks": chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"    : {str(e)}")
    finally:
        retriever.close()

mcp = FastMCP.from_fastapi(app)

if __name__ == "__main__":
    mcp.run()