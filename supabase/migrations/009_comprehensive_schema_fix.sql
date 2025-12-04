-- Comprehensive schema fix for PDF processing
-- This migration aligns the database schema with the pdf_processor code

-- 1. Fix pdf_documents table - make storage_path nullable since code doesn't always set it
ALTER TABLE pdf_documents ALTER COLUMN storage_path DROP NOT NULL;

-- 2. Create pdf_pages table if it doesn't exist
CREATE TABLE IF NOT EXISTS pdf_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pdf_document_id UUID NOT NULL REFERENCES pdf_documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    page_number INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pdf_document_id, page_number)
);

-- 3. Create indexes for pdf_pages
CREATE INDEX IF NOT EXISTS idx_pdf_pages_pdf_document ON pdf_pages(pdf_document_id);
CREATE INDEX IF NOT EXISTS idx_pdf_pages_user_id ON pdf_pages(user_id);
CREATE INDEX IF NOT EXISTS idx_pdf_pages_user_pdf_document ON pdf_pages(user_id, pdf_document_id);

-- 4. Create index on pdf_pages embedding for faster similarity search
CREATE INDEX IF NOT EXISTS idx_pdf_pages_embedding
    ON pdf_pages USING hnsw (embedding vector_cosine_ops);

-- 5. Ensure status values are correct in pdf_documents
-- (Already done in previous migrations, but ensuring here)
DO $$
BEGIN
    -- The constraint should already exist from migration 006
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pdf_documents_status_check'
        AND conrelid = 'pdf_documents'::regclass
    ) THEN
        ALTER TABLE pdf_documents ADD CONSTRAINT pdf_documents_status_check
            CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'uploaded'));
    END IF;
END $$;
