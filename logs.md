03:37:15 INFO     [api]                Incoming request - Origin: No Origin header, User-Agent: node, Path: /api/upload_pdfs
03:37:15 INFO     [api]                Received PDF upload request: files_count=1, request_id=web-pdf-1764841035873-qqjvk68by
03:37:15 INFO     [api]                Creating 1 placeholder medical records for user 703b410f-f50c-4bc8-b9a3-0991fed5a023
03:37:16 INFO     [api]                Successfully created 1 placeholder records
03:37:16 INFO     [api]                Queued background PDF processing for 1 files
03:37:16 INFO     [api:cache_cleanup_success] Cache cleaned up for request_id: bbb22a9f-a801-4a59-baf6-689673918350
03:37:16 INFO     [api]                Request completed: POST /api/upload_pdfs
INFO:     127.0.0.1:50074 - "POST /api/upload_pdfs HTTP/1.1" 200 OK
03:37:16 INFO     [api]                Starting background PDF processing for request web-pdf-1764841035873-qqjvk68by
03:37:16 INFO     [api]                Processing PDF 1/1: Pearce_etal.pdf
03:37:16 INFO     [api]                Processing file for existing record 819a2255-eb06-4681-b695-4123d2a7b701: Pearce_etal.pdf
03:37:19 INFO     [api]                About to batch queue 15 embedding jobs for record 819a2255-eb06-4681-b695-4123d2a7b701
03:37:19 INFO     [search:batch_queue_embedding_jobs_start] Batch queuing 15 embedding jobs for record pages
03:37:19 ERROR    [search:batch_queue_embedding_jobs_error] Failed to batch queue embedding jobs: {'message': 'unsupported Unicode escape sequence', 'code': '22P05', 'hint': None, 'details': '\\u0000 cannot be converted to text.'}
03:37:19 WARNING  [api]                Failed to batch queue 15 embedding jobs for record 819a2255-eb06-4681-b695-4123d2a7b701
03:37:20 INFO     [api]                Updated medical record 819a2255-eb06-4681-b695-4123d2a7b701 with 15 pages
03:37:20 INFO     [api]                Successfully processed file Pearce_etal.pdf for record 819a2255-eb06-4681-b695-4123d2a7b701 in 4.04s
03:37:20 INFO     [api]                Successfully processed PDF: Pearce_etal.pdf
03:37:20 INFO     [api]                Background PDF processing completed for request web-pdf-1764841035873-qqjvk68by











