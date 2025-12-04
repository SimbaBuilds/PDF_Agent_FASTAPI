-- Add pdf_document_id column to embedding_jobs table
-- This links embedding jobs to their parent PDF document for status tracking

ALTER TABLE embedding_jobs
ADD COLUMN pdf_document_id UUID REFERENCES pdf_documents(id) ON DELETE CASCADE;

-- Create index for efficient queries
CREATE INDEX idx_embedding_jobs_pdf_document_id ON embedding_jobs(pdf_document_id);

-- Create index for checking completion status
CREATE INDEX idx_embedding_jobs_status_pdf_document ON embedding_jobs(pdf_document_id, status);
