-- 똑소리 프로젝트 통합 데이터베이스 스키마 v2 (최종)
-- 작성일: 2026-01-06
-- RAG 시스템 최적화를 위한 개선된 스키마

-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 기존 테이블 삭제 (개발 환경용)
DROP TABLE IF EXISTS chunk_relations CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- ============================================
-- 1. documents 테이블: 문서 메타데이터
-- ============================================
CREATE TABLE documents (
    doc_id VARCHAR(255) PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,  
    -- 'law', 'mediation_case', 'counsel_case', 
    -- 'criteria_item', 'criteria_resolution', 'criteria_warranty', 'criteria_lifespan',
    -- 'guideline_content', 'guideline_ecommerce'
    title TEXT NOT NULL,
    source_org VARCHAR(100),  -- 'KCA', 'ECMC', 'KCDRC', 'statute', 'consumer.go.kr'
    category_path TEXT[],  -- 배열 타입으로 카테고리 경로 저장
    url TEXT,
    collected_at TIMESTAMP,
    metadata JSONB,  -- 유연한 메타데이터 저장
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_documents_doc_type ON documents(doc_type);
CREATE INDEX idx_documents_source_org ON documents(source_org);
CREATE INDEX idx_documents_type_org ON documents(doc_type, source_org);  -- 복합 인덱스
CREATE INDEX idx_documents_category ON documents USING GIN(category_path);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);

-- 코멘트 추가
COMMENT ON TABLE documents IS '문서 메타데이터 테이블: 법령, 상담사례, 분쟁조정사례, 기준의 기본 정보';
COMMENT ON COLUMN documents.doc_type IS '문서 유형: law(법령), mediation_case(분쟁조정사례), counsel_case(피해구제사례), criteria_*(기준), guideline_*(가이드라인)';
COMMENT ON COLUMN documents.category_path IS '카테고리 경로 배열 (예: {상품(재화), 농수축산물, 란류})';
COMMENT ON COLUMN documents.source_org IS '출처 기관: KCA(한국소비자원), ECMC(전자거래분쟁조정위원회), KCDRC(지역분쟁조정위원회), statute(법령), consumer.go.kr(1372)';

-- ============================================
-- 2. chunks 테이블: 청크 및 임베딩
-- ============================================
CREATE TABLE chunks (
    chunk_id VARCHAR(255) PRIMARY KEY,
    doc_id VARCHAR(255) NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_total INTEGER NOT NULL,
    chunk_type VARCHAR(50),  -- 'article', 'paragraph', 'item_classification', 'resolution_row', 'decision', 'parties_claim', 'judgment', 'qa_combined' 등
    content TEXT NOT NULL,
    content_length INTEGER,
    embedding vector(1024),  -- KURE-v1 차원 (1024)
    drop BOOLEAN DEFAULT FALSE,  -- 삭제 플래그 (검색에서 제외할 청크)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(doc_id, chunk_index),
    CHECK (chunk_index >= 0),  -- 0-based indexing
    CHECK (chunk_total > 0),
    CHECK (chunk_index < chunk_total)
);

-- 인덱스 생성
CREATE INDEX idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX idx_chunks_type ON chunks(chunk_type);
CREATE INDEX idx_chunks_doc_type ON chunks(doc_id, chunk_type);  -- 복합 인덱스
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_embedding_active ON chunks(chunk_type) WHERE embedding IS NOT NULL AND drop = FALSE;  -- 활성 청크만

-- 코멘트 추가
COMMENT ON TABLE chunks IS '청크 및 임베딩 테이블: 문서를 의미 단위로 분할한 청크와 벡터 임베딩';
COMMENT ON COLUMN chunks.chunk_type IS '청크 유형: article(조문), paragraph(항), item_classification(품목분류), resolution_row(해결기준), decision(결정), parties_claim(당사자주장), judgment(판단), qa_combined(질의응답) 등';
COMMENT ON COLUMN chunks.embedding IS 'KURE-v1 모델로 생성된 1024차원 벡터 임베딩';
COMMENT ON COLUMN chunks.drop IS '삭제 플래그: TRUE인 경우 검색에서 제외 (데이터는 보존)';

-- ============================================
-- 3. chunk_relations 테이블: 청크 간 관계
-- ============================================
CREATE TABLE chunk_relations (
    source_chunk_id VARCHAR(255) NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    target_chunk_id VARCHAR(255) NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,  -- 'next', 'prev', 'related', 'cited'
    confidence FLOAT DEFAULT 1.0,  -- 관계 신뢰도 (0.0 ~ 1.0)
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (source_chunk_id, target_chunk_id, relation_type),
    CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

-- 인덱스 생성
CREATE INDEX idx_chunk_relations_source ON chunk_relations(source_chunk_id);
CREATE INDEX idx_chunk_relations_target ON chunk_relations(target_chunk_id);
CREATE INDEX idx_chunk_relations_type ON chunk_relations(relation_type);

-- 코멘트 추가
COMMENT ON TABLE chunk_relations IS '청크 간 관계 테이블: 순서, 참조, 연관 관계 관리';
COMMENT ON COLUMN chunk_relations.relation_type IS '관계 유형: next(다음), prev(이전), related(연관), cited(인용)';

-- ============================================
-- 4. 뷰: 문서와 청크 통합 조회
-- ============================================
CREATE OR REPLACE VIEW v_chunks_with_documents AS
SELECT 
    c.chunk_id,
    c.doc_id,
    c.chunk_index,
    c.chunk_total,
    c.chunk_type,
    c.content,
    c.content_length,
    c.embedding,
    c.embedding_model,
    c.drop,
    d.doc_type,
    d.title AS doc_title,
    d.source_org,
    d.category_path,
    d.url,
    d.metadata AS doc_metadata
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id;

COMMENT ON VIEW v_chunks_with_documents IS '청크와 문서 메타데이터를 통합 조회하는 뷰';

-- ============================================
-- 5. 함수: 벡터 유사도 검색
-- ============================================
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(1024),
    doc_type_filter VARCHAR(50) DEFAULT NULL,
    chunk_type_filter VARCHAR(50) DEFAULT NULL,
    source_org_filter VARCHAR(100) DEFAULT NULL,
    top_k INTEGER DEFAULT 10,
    min_similarity FLOAT DEFAULT 0.0
)
RETURNS TABLE (
    chunk_id VARCHAR(255),
    doc_id VARCHAR(255),
    chunk_type VARCHAR(50),
    content TEXT,
    doc_title TEXT,
    doc_type VARCHAR(50),
    source_org VARCHAR(100),
    category_path TEXT[],
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.chunk_id,
        c.doc_id,
        c.chunk_type,
        c.content,
        d.title AS doc_title,
        d.doc_type,
        d.source_org,
        d.category_path,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    JOIN documents d ON c.doc_id = d.doc_id
    WHERE 
        c.drop = FALSE
        AND c.embedding IS NOT NULL
        AND (doc_type_filter IS NULL OR d.doc_type = doc_type_filter)
        AND (chunk_type_filter IS NULL OR c.chunk_type = chunk_type_filter)
        AND (source_org_filter IS NULL OR d.source_org = source_org_filter)
        AND (1 - (c.embedding <=> query_embedding)) >= min_similarity
    ORDER BY c.embedding <=> query_embedding
    LIMIT top_k;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_similar_chunks IS '벡터 유사도 기반 청크 검색 함수 (코사인 유사도, 다중 필터 지원)';

-- ============================================
-- 6. 함수: 청크 컨텍스트 확장
-- ============================================
CREATE OR REPLACE FUNCTION get_chunk_with_context(
    target_chunk_id VARCHAR(255),
    window_size INTEGER DEFAULT 1
)
RETURNS TABLE (
    chunk_id VARCHAR(255),
    doc_id VARCHAR(255),
    chunk_index INTEGER,
    chunk_type VARCHAR(50),
    content TEXT,
    is_target BOOLEAN
) AS $$
DECLARE
    target_doc_id VARCHAR(255);
    target_index INTEGER;
BEGIN
    -- 타겟 청크 정보 조회
    SELECT c.doc_id, c.chunk_index 
    INTO target_doc_id, target_index
    FROM chunks c 
    WHERE c.chunk_id = target_chunk_id;
    
    -- 타겟 청크와 주변 청크 반환
    RETURN QUERY
    SELECT 
        c.chunk_id,
        c.doc_id,
        c.chunk_index,
        c.chunk_type,
        c.content,
        (c.chunk_id = target_chunk_id) AS is_target
    FROM chunks c
    WHERE 
        c.doc_id = target_doc_id
        AND c.chunk_index >= (target_index - window_size)
        AND c.chunk_index <= (target_index + window_size)
        AND c.drop = FALSE
    ORDER BY c.chunk_index;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_chunk_with_context IS '특정 청크와 주변 청크를 함께 조회하는 함수 (컨텍스트 윈도우)';

-- ============================================
-- 7. 통계 뷰
-- ============================================
CREATE OR REPLACE VIEW v_data_statistics AS
SELECT 
    d.doc_type,
    d.source_org,
    COUNT(DISTINCT d.doc_id) AS document_count,
    COUNT(c.chunk_id) AS chunk_count,
    COUNT(CASE WHEN c.drop = FALSE THEN 1 END) AS active_chunk_count,
    AVG(c.content_length) AS avg_chunk_length,
    COUNT(CASE WHEN c.embedding IS NOT NULL THEN 1 END) AS embedded_chunk_count
FROM documents d
LEFT JOIN chunks c ON d.doc_id = c.doc_id
GROUP BY d.doc_type, d.source_org
ORDER BY d.doc_type, d.source_org;

COMMENT ON VIEW v_data_statistics IS '데이터 유형별 통계 정보 (문서 수, 청크 수, 평균 길이 등)';

-- ============================================
-- 8. 트리거: updated_at 자동 업데이트
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chunks_updated_at
    BEFORE UPDATE ON chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 완료 메시지
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '똑소리 프로젝트 데이터베이스 스키마 v2 (최종) 생성 완료';
    RAISE NOTICE '============================================';
    RAISE NOTICE '생성된 테이블:';
    RAISE NOTICE '  - documents: 문서 메타데이터';
    RAISE NOTICE '  - chunks: 청크 및 임베딩 (drop 플래그 추가)';
    RAISE NOTICE '  - chunk_relations: 청크 간 관계';
    RAISE NOTICE '';
    RAISE NOTICE '생성된 뷰:';
    RAISE NOTICE '  - v_chunks_with_documents: 통합 조회';
    RAISE NOTICE '  - v_data_statistics: 통계 정보';
    RAISE NOTICE '';
    RAISE NOTICE '생성된 함수:';
    RAISE NOTICE '  - search_similar_chunks(): 벡터 검색 (다중 필터 지원)';
    RAISE NOTICE '  - get_chunk_with_context(): 컨텍스트 확장';
    RAISE NOTICE '';
    RAISE NOTICE '주요 변경사항:';
    RAISE NOTICE '  - CHECK 제약 조건 수정 (chunk_index >= 0)';
    RAISE NOTICE '  - doc_type 확장 (criteria, guideline 추가)';
    RAISE NOTICE '  - drop 컬럼 추가 (삭제 플래그)';
    RAISE NOTICE '  - 복합 인덱스 추가 (성능 최적화)';
    RAISE NOTICE '  - search_similar_chunks 함수 개선 (다중 필터)';
    RAISE NOTICE '============================================';
END $$;
