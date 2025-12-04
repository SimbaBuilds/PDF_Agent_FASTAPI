-- Create Embedding Infrastructure
-- This migration creates the embedding_jobs table and triggers for automatic embedding generation

-- 1. Create embedding_jobs table to queue embedding generation tasks
CREATE TABLE IF NOT EXISTS embedding_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name TEXT NOT NULL CHECK (table_name IN ('pdf_pages', 'resources')),
    pdf_page_id UUID REFERENCES pdf_pages(id) ON DELETE CASCADE,
    resource_id UUID,  -- For future resource embeddings
    user_id UUID NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Create indexes for embedding_jobs
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_status ON embedding_jobs(status);
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_user_id ON embedding_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_pdf_page_id ON embedding_jobs(pdf_page_id);
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_created_at ON embedding_jobs(created_at);

-- 2. Create function to automatically queue embedding jobs when pdf_pages are inserted
CREATE OR REPLACE FUNCTION queue_pdf_page_embedding()
RETURNS TRIGGER AS $$
BEGIN
    -- Only queue if content is not empty
    IF NEW.content IS NOT NULL AND LENGTH(TRIM(NEW.content)) > 0 THEN
        INSERT INTO embedding_jobs (
            table_name,
            pdf_page_id,
            user_id,
            content,
            status
        ) VALUES (
            'pdf_pages',
            NEW.id,
            NEW.user_id,
            NEW.content,
            'pending'
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Create trigger on pdf_pages to automatically queue embeddings
DROP TRIGGER IF EXISTS trigger_queue_pdf_page_embedding ON pdf_pages;
CREATE TRIGGER trigger_queue_pdf_page_embedding
    AFTER INSERT ON pdf_pages
    FOR EACH ROW
    EXECUTE FUNCTION queue_pdf_page_embedding();

-- 4. Update RPC functions to use new table names (pdf_pages instead of record_pages)
DROP FUNCTION IF EXISTS search_pdf_pages_by_embedding(vector, UUID, UUID, FLOAT, INT);
CREATE OR REPLACE FUNCTION search_pdf_pages_by_embedding(
    query_embedding vector(1536),
    target_user_id UUID,
    target_pdf_id UUID DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    pdf_document_id UUID,
    page_number INT,
    content TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pp.id,
        pp.pdf_document_id,
        pp.page_number,
        pp.content,
        1 - (pp.embedding <=> query_embedding) AS similarity
    FROM pdf_pages pp
    WHERE pp.user_id = target_user_id
        AND (target_pdf_id IS NULL OR pp.pdf_document_id = target_pdf_id)
        AND pp.embedding IS NOT NULL
        AND 1 - (pp.embedding <=> query_embedding) > match_threshold
    ORDER BY pp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

GRANT EXECUTE ON FUNCTION search_pdf_pages_by_embedding TO authenticated;

-- 5. Update text search function
DROP FUNCTION IF EXISTS search_pdf_pages_by_text(UUID, UUID, TEXT, INT);
CREATE OR REPLACE FUNCTION search_pdf_pages_by_text(
    target_user_id UUID,
    target_pdf_id UUID DEFAULT NULL,
    search_pattern TEXT DEFAULT '',
    result_limit INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    pdf_document_id UUID,
    page_number INT,
    content TEXT,
    matches_found BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pp.id,
        pp.pdf_document_id,
        pp.page_number,
        pp.content,
        (LENGTH(pp.content) - LENGTH(REPLACE(LOWER(pp.content), LOWER(search_pattern), '')))
            / NULLIF(LENGTH(search_pattern), 0) AS matches_found
    FROM pdf_pages pp
    WHERE pp.user_id = target_user_id
        AND (target_pdf_id IS NULL OR pp.pdf_document_id = target_pdf_id)
        AND (search_pattern = '' OR pp.content ILIKE '%' || search_pattern || '%')
    ORDER BY
        CASE WHEN search_pattern != ''
            THEN (LENGTH(pp.content) - LENGTH(REPLACE(LOWER(pp.content), LOWER(search_pattern), '')))
                / NULLIF(LENGTH(search_pattern), 0)
            ELSE 0
        END DESC,
        pp.page_number ASC
    LIMIT result_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_pdf_pages_by_text TO authenticated;
