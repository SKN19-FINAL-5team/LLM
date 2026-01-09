-- ============================================
-- : SPLADE Sparse Vector  
-- : 2026-01-08
-- : chunks  SPLADE sparse vector    
-- ============================================

-- 1. chunks  splade_sparse_vector  
-- JSONB  {token_id: weight}  
-- : {"1234": 2.5, "5678": 1.8, ...}
ALTER TABLE chunks 
ADD COLUMN IF NOT EXISTS splade_sparse_vector JSONB;

-- 2. SPLADE    
ALTER TABLE chunks
ADD COLUMN IF NOT EXISTS splade_model VARCHAR(50) DEFAULT 'naver/splade-v3';

-- 3. SPLADE     
ALTER TABLE chunks
ADD COLUMN IF NOT EXISTS splade_encoded BOOLEAN DEFAULT FALSE;

-- 4.  
COMMENT ON COLUMN chunks.splade_sparse_vector IS 'SPLADE sparse vector: {token_id: weight}  JSONB. 0     ';
COMMENT ON COLUMN chunks.splade_model IS ' SPLADE  ';
COMMENT ON COLUMN chunks.splade_encoded IS 'SPLADE   ';

-- 5. GIN   (JSONB  )
-- token_id    
CREATE INDEX IF NOT EXISTS idx_chunks_splade_vector_gin 
ON chunks USING GIN (splade_sparse_vector);

-- 6. splade_encoded  (  )
CREATE INDEX IF NOT EXISTS idx_chunks_splade_encoded 
ON chunks(splade_encoded) 
WHERE splade_encoded = FALSE;

-- 7.   + SPLADE      
CREATE INDEX IF NOT EXISTS idx_chunks_splade_active 
ON chunks(doc_id, chunk_type) 
WHERE splade_encoded = TRUE AND drop = FALSE;

-- 8. : SPLADE sparse vector   
--  : SELECT * FROM chunks WHERE splade_vector_contains_token(splade_sparse_vector, '1234');
CREATE OR REPLACE FUNCTION splade_vector_contains_token(
    sparse_vec JSONB,
    token_id TEXT
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN sparse_vec ? token_id;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 9. : SPLADE sparse vector dot product  (PostgreSQL )
-- :    ,   Python    
CREATE OR REPLACE FUNCTION splade_vector_dot_product(
    vec1 JSONB,
    vec2 JSONB
) RETURNS FLOAT AS $$
DECLARE
    result FLOAT := 0.0;
    key TEXT;
BEGIN
    -- vec1    vec2     
    FOR key IN SELECT jsonb_object_keys(vec1)
    LOOP
        IF vec2 ? key THEN
            result := result + (vec1->>key)::FLOAT * (vec2->>key)::FLOAT;
        END IF;
    END LOOP;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 10.   
ANALYZE chunks;

--   
DO $$
BEGIN
    RAISE NOTICE ' SPLADE sparse vector  .';
    RAISE NOTICE '   - splade_sparse_vector  (JSONB)';
    RAISE NOTICE '   - GIN   ';
    RAISE NOTICE '   -  : encode_splade_vectors.py   ';
END $$;
