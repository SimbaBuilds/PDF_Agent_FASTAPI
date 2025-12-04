-- Create trigger to update PDF document status when all embeddings complete
-- This ensures pdf_documents.status only changes to 'completed' after all embedding jobs finish

CREATE OR REPLACE FUNCTION update_pdf_document_status_on_embedding_completion()
RETURNS TRIGGER AS $$
DECLARE
    pending_jobs_count INTEGER;
BEGIN
    -- Only proceed if this job was just marked as completed and has a pdf_document_id
    IF NEW.status = 'completed' AND NEW.pdf_document_id IS NOT NULL THEN

        -- Count how many jobs for this PDF are still not completed
        SELECT COUNT(*)
        INTO pending_jobs_count
        FROM embedding_jobs
        WHERE pdf_document_id = NEW.pdf_document_id
        AND status NOT IN ('completed', 'failed');

        -- If no pending jobs remain, update PDF document status to completed
        IF pending_jobs_count = 0 THEN
            UPDATE pdf_documents
            SET
                status = 'completed',
                updated_at = NOW()
            WHERE id = NEW.pdf_document_id
            AND status = 'processing';  -- Only update if currently processing

            -- Log for debugging
            RAISE NOTICE 'Updated PDF document % to completed after all embeddings finished', NEW.pdf_document_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger that fires after embedding job status updates
DROP TRIGGER IF EXISTS trigger_update_pdf_on_embedding_complete ON embedding_jobs;

CREATE TRIGGER trigger_update_pdf_on_embedding_complete
AFTER UPDATE OF status ON embedding_jobs
FOR EACH ROW
WHEN (NEW.status = 'completed' AND NEW.pdf_document_id IS NOT NULL)
EXECUTE FUNCTION update_pdf_document_status_on_embedding_completion();
