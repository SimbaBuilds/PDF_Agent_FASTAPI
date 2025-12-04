FO:     Waiting for application startup.
INFO:     Application startup complete.
02:38:57 INFO     [api]                Incoming request - Origin: No Origin header, User-Agent: node, Path: /api/upload_pdfs
02:38:57 INFO     [app]                Creating Supabase client for environment: ConnectionPoolConfig(max_connections=20, max_keepalive_connections=5, keepalive_expiry=30.0, connect_timeout=10.0, read_timeout=15.0, write_timeout=15.0, pool_timeout=10.0)
02:38:57 WARNING  [app]                Connection warmup failed (will retry on first use): {'message': "Could not find the table 'public.user_profiles' in the schema cache", 'code': 'PGRST205', 'hint': None, 'details': None}
02:38:57 INFO     [app]                Supabase singleton client created successfully with 20 max connections
02:38:57 INFO     [api]                Received PDF upload request: files_count=1, request_id=web-pdf-1764837537347-wlo83hnvu
02:38:57 INFO     [api]                Creating 1 placeholder medical records for user 703b410f-f50c-4bc8-b9a3-0991fed5a023
02:38:57 INFO     [api]                Successfully created 1 placeholder records
02:38:57 INFO     [api]                Queued background PDF processing for 1 files
02:38:57 INFO     [api:cache_cleanup_success] Cache cleaned up for request_id: 70014a35-0586-4356-aee9-9f8cb397b537
02:38:57 INFO     [api]                Request completed: POST /api/upload_pdfs
INFO:     127.0.0.1:53100 - "POST /api/upload_pdfs HTTP/1.1" 200 OK
02:38:57 INFO     [api]                Starting background PDF processing for request web-pdf-1764837537347-wlo83hnvu
02:38:57 INFO     [api]                Processing PDF 1/1: Cameron_Hightower_Resume_ATS_PUBLIC_POLICY.pdf
02:38:57 INFO     [api]                Processing file for existing record ba4d8e04-6e74-40eb-b28e-3cbe57ae6aea: Cameron_Hightower_Resume_ATS_PUBLIC_POLICY.pdf
02:38:59 INFO     [api]                About to batch queue 3 embedding jobs for record ba4d8e04-6e74-40eb-b28e-3cbe57ae6aea
02:38:59 INFO     [search:batch_queue_embedding_jobs_start] Batch queuing 3 embedding jobs for record pages
02:38:59 ERROR    [search:batch_queue_embedding_jobs_error] Failed to batch queue embedding jobs: Object of type UUID is not JSON serializable
02:38:59 WARNING  [api]                Failed to batch queue 3 embedding jobs for record ba4d8e04-6e74-40eb-b28e-3cbe57ae6aea
02:38:59 INFO     [api]                Updated medical record ba4d8e04-6e74-40eb-b28e-3cbe57ae6aea with 3 pages
02:38:59 INFO     [api]                Successfully processed file Cameron_Hightower_Resume_ATS_PUBLIC_POLICY.pdf for record ba4d8e04-6e74-40eb-b28e-3cbe57ae6aea in 1.58s
02:38:59 INFO     [api]                Successfully processed PDF: Cameron_Hightower_Resume_ATS_PUBLIC_POLICY.pdf
02:38:59 INFO     [api]                Background PDF processing completed for request web-pdf-1764837537347-wlo83hnvu
