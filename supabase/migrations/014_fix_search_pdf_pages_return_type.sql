-- Fix type mismatch in search_pdf_pages_by_text function
-- The matches_found column was declared as BIGINT but returning INTEGER

CREATE OR REPLACE FUNCTION search_pdf_pages_by_text(
    target_user_id UUID,
    target_pdf_id UUID DEFAULT NULL,
    search_pattern TEXT DEFAULT '',
    result_limit INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    pdf_document_id UUID,
    page_number INT,
    content TEXT,
    matches_found BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pp.id,
        pp.pdf_document_id,
        pp.page_number,
        pp.content,
        ((LENGTH(pp.content) - LENGTH(REPLACE(LOWER(pp.content), LOWER(search_pattern), '')))
            / NULLIF(LENGTH(search_pattern), 0))::BIGINT AS matches_found
    FROM pdf_pages pp
    WHERE pp.user_id = target_user_id
        AND (target_pdf_id IS NULL OR pp.pdf_document_id = target_pdf_id)
        AND (search_pattern = '' OR pp.content ILIKE '%' || search_pattern || '%')
    ORDER BY
        CASE WHEN search_pattern != ''
            THEN (LENGTH(pp.content) - LENGTH(REPLACE(LOWER(pp.content), LOWER(search_pattern), '')))
                / NULLIF(LENGTH(search_pattern), 0)
            ELSE 0
        END DESC,
        pp.page_number ASC
    LIMIT result_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_pdf_pages_by_text TO authenticated;
