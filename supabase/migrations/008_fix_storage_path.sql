-- Fix storage_path column to allow NULL
-- The pdf_processor doesn't use this field

ALTER TABLE pdf_documents ALTER COLUMN storage_path DROP NOT NULL;
