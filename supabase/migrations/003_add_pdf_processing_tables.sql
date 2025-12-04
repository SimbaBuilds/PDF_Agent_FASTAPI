-- PDF Processing Tables Migration
-- This migration adds the tables needed for storing uploaded PDFs and their processed pages.

-- Medical Records table (renamed from medical context for general PDF storage)
-- Stores metadata about uploaded PDF documents
CREATE TABLE IF NOT EXISTS medical_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT DEFAULT 'pdf',
    file_size_bytes BIGINT,
    storage_path TEXT,
    num_pages INT DEFAULT 0,
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user queries
CREATE INDEX IF NOT EXISTS idx_medical_records_user_id ON medical_records(user_id);
CREATE INDEX IF NOT EXISTS idx_medical_records_status ON medical_records(processing_status);

-- Record Pages table
-- Stores individual pages from processed PDFs with their content and embeddings
CREATE TABLE IF NOT EXISTS record_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    medical_record_id UUID NOT NULL REFERENCES medical_records(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    page_number INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(medical_record_id, page_number)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_record_pages_medical_record ON record_pages(medical_record_id);
CREATE INDEX IF NOT EXISTS idx_record_pages_user_id ON record_pages(user_id);
CREATE INDEX IF NOT EXISTS idx_record_pages_user_medical_record ON record_pages(user_id, medical_record_id);

-- Create index on record_pages embedding for faster similarity search
-- Using hnsw for better performance on smaller datasets
CREATE INDEX IF NOT EXISTS idx_record_pages_embedding
    ON record_pages USING hnsw (embedding vector_cosine_ops);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at on medical_records
CREATE TRIGGER update_medical_records_updated_at
    BEFORE UPDATE ON medical_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
