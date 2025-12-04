-- Remove duplicate embedding job creation trigger
-- The application code now handles embedding job creation with proper pdf_document_id population
-- This trigger was creating duplicate jobs and not populating pdf_document_id

-- Drop the trigger
DROP TRIGGER IF EXISTS trigger_queue_pdf_page_embedding ON pdf_pages;

-- Drop the trigger function
DROP FUNCTION IF EXISTS queue_pdf_page_embedding();

-- Add comment explaining the change
COMMENT ON TABLE embedding_jobs IS 'Embedding jobs are now queued via application code in batch_queue_embedding_jobs_for_pdf_pages(). The database trigger was removed to prevent duplicates and ensure pdf_document_id is populated correctly.';
