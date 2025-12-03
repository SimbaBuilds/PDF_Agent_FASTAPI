-- PDF Agent Schema Migration
-- This migration sets up the database schema for the PDF Agent application.

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Generated PDFs table
-- Stores PDFs created by the agent (summaries, reports)
CREATE TABLE IF NOT EXISTS generated_pdfs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title TEXT NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('summary', 'report')),
    source_pdf_ids UUID[] DEFAULT '{}',
    storage_path TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user queries
CREATE INDEX IF NOT EXISTS idx_generated_pdfs_user_id ON generated_pdfs(user_id);

-- Email history table
-- Tracks emails sent with PDF attachments
CREATE TABLE IF NOT EXISTS email_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    recipient_email TEXT NOT NULL,
    recipient_name TEXT,
    subject TEXT,
    pdf_id UUID REFERENCES generated_pdfs(id),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    error_message TEXT,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user queries
CREATE INDEX IF NOT EXISTS idx_email_history_user_id ON email_history(user_id);

-- RPC function for searching PDF pages by embedding
-- This function performs vector similarity search on record_pages
CREATE OR REPLACE FUNCTION search_pdf_pages_by_embedding(
    query_embedding vector(1536),
    target_user_id UUID,
    target_pdf_id UUID DEFAULT NULL,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    medical_record_id UUID,
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
        rp.id,
        rp.medical_record_id,
        rp.page_number,
        rp.content,
        1 - (rp.embedding <=> query_embedding) AS similarity
    FROM record_pages rp
    WHERE rp.user_id = target_user_id
        AND (target_pdf_id IS NULL OR rp.medical_record_id = target_pdf_id)
        AND rp.embedding IS NOT NULL
        AND 1 - (rp.embedding <=> query_embedding) > match_threshold
    ORDER BY rp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION search_pdf_pages_by_embedding TO authenticated;

-- RPC function for text/grep search on PDF pages
-- This function performs text pattern matching without requiring embeddings
CREATE OR REPLACE FUNCTION search_pdf_pages_by_text(
    target_user_id UUID,
    target_pdf_id UUID DEFAULT NULL,
    search_pattern TEXT DEFAULT '',
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    medical_record_id UUID,
    page_number INT,
    content TEXT,
    match_count BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rp.id,
        rp.medical_record_id,
        rp.page_number,
        rp.content,
        (LENGTH(rp.content) - LENGTH(REPLACE(LOWER(rp.content), LOWER(search_pattern), '')))
            / NULLIF(LENGTH(search_pattern), 0) AS match_count
    FROM record_pages rp
    WHERE rp.user_id = target_user_id
        AND (target_pdf_id IS NULL OR rp.medical_record_id = target_pdf_id)
        AND (search_pattern = '' OR rp.content ILIKE '%' || search_pattern || '%')
    ORDER BY
        CASE WHEN search_pattern != ''
            THEN (LENGTH(rp.content) - LENGTH(REPLACE(LOWER(rp.content), LOWER(search_pattern), '')))
                / NULLIF(LENGTH(search_pattern), 0)
            ELSE 0
        END DESC,
        rp.page_number ASC
    LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION search_pdf_pages_by_text TO authenticated;

-- Add embedding column to record_pages if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'record_pages' AND column_name = 'embedding'
    ) THEN
        ALTER TABLE record_pages ADD COLUMN embedding vector(1536);
    END IF;
END $$;

-- Create index on record_pages embedding for faster similarity search
CREATE INDEX IF NOT EXISTS idx_record_pages_embedding
    ON record_pages USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Create index on record_pages for user and medical_record lookups
CREATE INDEX IF NOT EXISTS idx_record_pages_user_medical_record
    ON record_pages(user_id, medical_record_id);
