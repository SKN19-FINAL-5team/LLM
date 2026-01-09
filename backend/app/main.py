import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
from fastmcp import FastMCP

from app.rag import VectorRetriever, RAGGenerator

# 환경 변수 로드
load_dotenv()

app = FastAPI(
    title="똑소리 API",
    version="0.3.0",
    description="한국 소비자 분쟁 조정 RAG 챗봇 API"
)

# CORS 설정
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 설정
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

# RAG 컴포넌트 초기화
retriever = VectorRetriever(db_config)
generator = RAGGenerator()


# Request/Response 모델
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


# API 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "똑소리 API 서버가 정상적으로 실행 중입니다.",
        "version": "0.3.0",
        "features": ["RAG 검색", "LLM 답변 생성"]
    }


@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    try:
        # DB 연결 테스트
        retriever.connect_db()
        retriever.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/search")
async def search(request: SearchRequest):
    """
    Vector DB에서 유사한 사례 검색 (LLM 답변 생성 없이 검색만)
    
    Args:
        query: 검색 쿼리
        top_k: 반환할 최대 결과 수
        chunk_types: 필터링할 청크 타입 (예: ['decision', 'reasoning'])
        agencies: 필터링할 기관 (예: ['kca', 'ecmc'])
    
    Returns:
        검색된 청크 리스트
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
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")
    finally:
        retriever.close()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    RAG 기반 챗봇 응답 생성
    
    Args:
        message: 사용자 질문
        top_k: 검색할 최대 청크 수
        chunk_types: 필터링할 청크 타입
        agencies: 필터링할 기관
    
    Returns:
        LLM이 생성한 답변 및 참고 자료
    """
    try:
        # 1. Vector DB에서 유사 청크 검색
        chunks = retriever.search(
            query=request.message,
            top_k=request.top_k,
            chunk_types=request.chunk_types,
            agencies=request.agencies
        )
        
        if not chunks:
            return ChatResponse(
                answer="죄송합니다. 관련된 분쟁조정 사례를 찾을 수 없습니다. 다른 질문을 해주시겠어요?",
                chunks_used=0,
                model=generator.model,
                sources=[]
            )
        
        # 2. LLM으로 답변 생성
        result = generator.generate_answer(
            query=request.message,
            chunks=chunks
        )
        
        # 3. 응답 포맷팅
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
        raise HTTPException(status_code=500, detail=f"답변 생성 중 오류 발생: {str(e)}")
    finally:
        retriever.close()


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    RAG 기반 스트리밍 챗봇 응답 생성
    
    Args:
        message: 사용자 질문
        top_k: 검색할 최대 청크 수
        chunk_types: 필터링할 청크 타입
        agencies: 필터링할 기관
    
    Returns:
        실시간 스트리밍 응답
    """
    try:
        # Vector DB에서 유사 청크 검색
        chunks = retriever.search(
            query=request.message,
            top_k=request.top_k,
            chunk_types=request.chunk_types,
            agencies=request.agencies
        )
        
        if not chunks:
            async def no_results():
                yield "죄송합니다. 관련된 분쟁조정 사례를 찾을 수 없습니다."
            return StreamingResponse(no_results(), media_type="text/plain")
        
        # 스트리밍 답변 생성
        return StreamingResponse(
            generator.generate_answer_stream(
                query=request.message,
                chunks=chunks
            ),
            media_type="text/plain"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"답변 생성 중 오류 발생: {str(e)}")
    finally:
        retriever.close()


@app.get("/case/{case_uid}")
async def get_case(case_uid: str):
    """
    특정 사례의 전체 정보 조회
    
    Args:
        case_uid: 사례 고유 ID
    
    Returns:
        해당 사례의 모든 청크
    """
    try:
        chunks = retriever.get_case_chunks(case_uid)
        
        if not chunks:
            raise HTTPException(status_code=404, detail="사례를 찾을 수 없습니다.")
        
        return {
            "case_uid": case_uid,
            "chunks_count": len(chunks),
            "chunks": chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사례 조회 중 오류 발생: {str(e)}")
    finally:
        retriever.close()

mcp = FastMCP.from_fastapi(app)

if __name__ == "__main__":
    mcp.run()