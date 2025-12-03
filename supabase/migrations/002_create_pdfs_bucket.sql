-- Migration: Create 'pdfs' storage bucket for PDF documents
-- This bucket will store generated PDF documents for users

-- Create the storage bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'pdfs',
    'pdfs',
    false,  -- Not public by default, will use signed URLs
    52428800,  -- 50MB file size limit
    ARRAY['application/pdf']  -- Only allow PDF files
)
ON CONFLICT (id) DO NOTHING;

-- Create storage policy to allow authenticated users to upload their own PDFs
CREATE POLICY "Users can upload their own PDFs"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'pdfs' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Create storage policy to allow users to read their own PDFs
CREATE POLICY "Users can read their own PDFs"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'pdfs' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Create storage policy to allow users to delete their own PDFs
CREATE POLICY "Users can delete their own PDFs"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'pdfs' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Create storage policy to allow service role full access
CREATE POLICY "Service role has full access to pdfs bucket"
ON storage.objects
FOR ALL
TO service_role
USING (bucket_id = 'pdfs')
WITH CHECK (bucket_id = 'pdfs');

-- Grant necessary permissions
GRANT ALL ON storage.buckets TO authenticated;
GRANT ALL ON storage.buckets TO service_role;
