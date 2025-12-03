We are building a single page pdf agent chat agent app. This is the Python/FASTAPI backend and will handle pdf processing and LLM chat respones.

I have copied over a bunch of files from another project that is a chat application that handles medical records content.  Please update these files for this new pdf only chat agent according to the following specs:

- Process pdf
    - The other app handles many file types but this app should only handle pdfs.
    - Maintain existing functionality by chunking by page 
    - Embedding flow
        - use supabase pg vector
        - Ensure pdf content upload triggers a supabase embedding job - implement supabase edge function if necessary
- Agent
    - 4 Tools:
        - Fetch pdf content (search_type config in params)
            - semantic search 
            - grep
        - Create pdf
        - Perplexity search (perplexity_search only)
        - Email PDF to user: agent should be able to generate a pdf document and email it to the user as an attachment along with a text body.
            - Agent receives name and email by asking the user (include this instruction in system prompt)
            - Use google SMPT. Env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, CONTACT_EMAIL




