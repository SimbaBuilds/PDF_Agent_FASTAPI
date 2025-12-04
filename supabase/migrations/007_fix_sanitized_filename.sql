-- Fix sanitized_filename column to allow NULL or provide default
-- The pdf_processor doesn't set this field

ALTER TABLE pdf_documents ALTER COLUMN sanitized_filename DROP NOT NULL;
