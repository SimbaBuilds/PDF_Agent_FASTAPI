-- Add missing columns to pdf_documents table (new version since tables were renamed)

-- Add missing columns if they don't exist
ALTER TABLE pdf_documents ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE pdf_documents ADD COLUMN IF NOT EXISTS original_file_type TEXT;
ALTER TABLE pdf_documents ADD COLUMN IF NOT EXISTS original_filename TEXT;
ALTER TABLE pdf_documents ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';
ALTER TABLE pdf_documents ADD COLUMN IF NOT EXISTS upload_url TEXT;
ALTER TABLE pdf_documents ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Drop old constraint if exists
ALTER TABLE pdf_documents DROP CONSTRAINT IF EXISTS medical_records_processing_status_check;
ALTER TABLE pdf_documents DROP CONSTRAINT IF EXISTS pdf_documents_processing_status_check;
ALTER TABLE pdf_documents DROP CONSTRAINT IF EXISTS pdf_documents_status_check;

-- Add the status check constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pdf_documents_status_check'
        AND conrelid = 'pdf_documents'::regclass
    ) THEN
        ALTER TABLE pdf_documents ADD CONSTRAINT pdf_documents_status_check
            CHECK (status IN ('pending', 'processing', 'completed', 'failed'));
    END IF;
END $$;
