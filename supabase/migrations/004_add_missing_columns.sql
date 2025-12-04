-- Add missing columns to medical_records table

-- Add missing columns
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS original_file_type TEXT;
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS original_filename TEXT;
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS upload_url TEXT;
ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Update the status check constraint to include the new 'processing' status
ALTER TABLE medical_records DROP CONSTRAINT IF EXISTS medical_records_processing_status_check;
ALTER TABLE medical_records ADD CONSTRAINT medical_records_status_check
    CHECK (status IN ('pending', 'processing', 'completed', 'failed'));
