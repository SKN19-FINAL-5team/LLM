--      v2 ()
-- : 2026-01-06
-- RAG     

-- pgvector  
CREATE EXTENSION IF NOT EXISTS vector;

--    ( )
DROP TABLE IF EXISTS chunk_relations CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- ============================================
-- 1. documents :  
-- ============================================
CREATE TABLE documents (
    doc_id VARCHAR(255) PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,  
    -- 'law', 'mediation_case', 'counsel_case', 
    -- 'criteria_item', 'criteria_resolution', 'criteria_warranty', 'criteria_lifespan',
    -- 'guideline_content', 'guideline_ecommerce'
    title TEXT NOT NULL,
    source_org VARCHAR(100),  -- 'KCA', 'ECMC', 'KCDRC', 'statute', 'consumer.go.kr'
    category_path TEXT[],  --     
    url TEXT,
    collected_at TIMESTAMP,
    metadata JSONB,  --   
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

--  
CREATE INDEX idx_documents_doc_type ON documents(doc_type);
CREATE INDEX idx_documents_source_org ON documents(source_org);
CREATE INDEX idx_documents_type_org ON documents(doc_type, source_org);  --  
CREATE INDEX idx_documents_category ON documents USING GIN(category_path);
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);

--  
COMMENT ON TABLE documents IS '  : , , ,   ';
COMMENT ON COLUMN documents.doc_type IS ' : law(), mediation_case(), counsel_case(), criteria_*(), guideline_*()';
COMMENT ON COLUMN documents.category_path IS '   (: {(), , })';
COMMENT ON COLUMN documents.source_org IS ' : KCA(), ECMC(), KCDRC(), statute(), consumer.go.kr(1372)';

-- ============================================
-- 2. chunks :   
-- ============================================
CREATE TABLE chunks (
    chunk_id VARCHAR(255) PRIMARY KEY,
    doc_id VARCHAR(255) NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_total INTEGER NOT NULL,
    chunk_type VARCHAR(50),  -- 'article', 'paragraph', 'item_classification', 'resolution_row', 'decision', 'parties_claim', 'judgment', 'qa_combined' 
    content TEXT NOT NULL,
    content_length INTEGER,
    embedding vector(1024),  -- KURE-v1  (1024)
    drop BOOLEAN DEFAULT FALSE,  --   (  )
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(doc_id, chunk_index),
    CHECK (chunk_index >= 0),  -- 0-based indexing
    CHECK (chunk_total > 0),
    CHECK (chunk_index < chunk_total)
);

--  
CREATE INDEX idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX idx_chunks_type ON chunks(chunk_type);
CREATE INDEX idx_chunks_doc_type ON chunks(doc_id, chunk_type);  --  
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_chunks_embedding_active ON chunks(chunk_type) WHERE embedding IS NOT NULL AND drop = FALSE;  --  

--  
COMMENT ON TABLE chunks IS '   :       ';
COMMENT ON COLUMN chunks.chunk_type IS ' : article(), paragraph(), item_classification(), resolution_row(), decision(), parties_claim(), judgment(), qa_combined() ';
COMMENT ON COLUMN chunks.embedding IS 'KURE-v1   1024  ';
COMMENT ON COLUMN chunks.drop IS ' : TRUE    ( )';

-- ============================================
-- 3. chunk_relations :   
-- ============================================
CREATE TABLE chunk_relations (
    source_chunk_id VARCHAR(255) NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    target_chunk_id VARCHAR(255) NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,  -- 'next', 'prev', 'related', 'cited'
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (source_chunk_id, target_chunk_id, relation_type),
);

--  
CREATE INDEX idx_chunk_relations_source ON chunk_relations(source_chunk_id);
CREATE INDEX idx_chunk_relations_target ON chunk_relations(target_chunk_id);
CREATE INDEX idx_chunk_relations_type ON chunk_relations(relation_type);

--  
COMMENT ON TABLE chunk_relations IS '   : , ,   ';
COMMENT ON COLUMN chunk_relations.relation_type IS ' : next(), prev(), related(), cited()';

-- ============================================
-- 4. :    
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
    c.drop,
    d.doc_type,
    d.title AS doc_title,
    d.source_org,
    d.category_path,
    d.url,
    d.metadata AS doc_metadata
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id;

COMMENT ON VIEW v_chunks_with_documents IS '     ';

-- ============================================
-- 5. :   
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

COMMENT ON FUNCTION search_similar_chunks IS '      ( ,   )';

-- ============================================
-- 6. :   
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
    --    
    SELECT c.doc_id, c.chunk_index 
    INTO target_doc_id, target_index
    FROM chunks c 
    WHERE c.chunk_id = target_chunk_id;
    
    --     
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

COMMENT ON FUNCTION get_chunk_with_context IS '       ( )';

-- ============================================
-- 7.  
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

COMMENT ON VIEW v_data_statistics IS '    ( ,  ,   )';

-- ============================================
-- 8. : updated_at  
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
--  
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '    v2 ()  ';
    RAISE NOTICE '============================================';
    RAISE NOTICE ' :';
    RAISE NOTICE '  - documents:  ';
    RAISE NOTICE '  - chunks:    (drop  )';
    RAISE NOTICE '  - chunk_relations:   ';
    RAISE NOTICE '';
    RAISE NOTICE ' :';
    RAISE NOTICE '  - v_chunks_with_documents:  ';
    RAISE NOTICE '  - v_data_statistics:  ';
    RAISE NOTICE '';
    RAISE NOTICE ' :';
    RAISE NOTICE '  - search_similar_chunks():   (  )';
    RAISE NOTICE '  - get_chunk_with_context():  ';
    RAISE NOTICE '';
    RAISE NOTICE ' :';
    RAISE NOTICE '  - CHECK    (chunk_index >= 0)';
    RAISE NOTICE '  - doc_type  (criteria, guideline )';
    RAISE NOTICE '  - drop   ( )';
    RAISE NOTICE '  -    ( )';
    RAISE NOTICE '  - search_similar_chunks   ( )';
    RAISE NOTICE '============================================';
END $$;
