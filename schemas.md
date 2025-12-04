create table public.pdf_documents (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  original_filename text not null,
  sanitized_filename text null,
  file_size_bytes bigint not null,
  storage_path text not null,
  storage_url text null,
  status text not null default 'uploaded'::text,
  processing_started_at timestamp with time zone null,
  processing_completed_at timestamp with time zone null,
  processing_error text null,
  num_pages integer null,
  content_summary text null,
  metadata jsonb null default '{}'::jsonb,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  title text null,
  original_file_type text null,
  upload_url text null,
  constraint pdf_documents_pkey primary key (id),
  constraint pdf_documents_user_id_fkey foreign KEY (user_id) references auth.users (id) on delete CASCADE,
  constraint pdf_documents_status_check check (
    (
      status = any (
        array[
          'pending'::text,
          'processing'::text,
          'completed'::text,
          'failed'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_pdf_documents_user_id on public.pdf_documents using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_pdf_documents_status on public.pdf_documents using btree (status) TABLESPACE pg_default;

create index IF not exists idx_pdf_documents_created_at on public.pdf_documents using btree (created_at desc) TABLESPACE pg_default;