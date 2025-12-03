# Supabase Development Utilities

This directory contains development utilities for managing and exploring my Supabase database.

##  Usage

Each time you use this script:

Run commands using the scripts in supabase_admin.py. Here are some examples:

   ```bash
   # Create a new conversation
   python supabase_admin/supabase_admin.py create conversations --data '{"user_id": "user-uuid", "title": "New Conversation"}'

   # Read a specific conversation
   python supabase_admin/supabase_admin.py read conversations --id "conversation-uuid"

   # Read all conversations (limited to 5)
   python supabase_admin/supabase_admin.py read-all conversations --limit 5

   # Update a conversation
   python supabase_admin/supabase_admin.py update conversations --id "conversation-uuid" --data '{"title": "Updated Title"}'

   # Delete a conversation
   python supabase_admin/supabase_admin.py delete conversations --id "conversation-uuid"

   # Alter table structure examples
   python supabase_admin/supabase_admin.py alter users --operation add --column nickname --type text --nullable
   python supabase_admin/supabase_admin.py alter products --operation drop --column old_field
   python supabase_admin/supabase_admin.py alter orders --operation modify --column status --type varchar --default 'pending'
   ```

## Available Commands

The script supports the following commands:

- `create <table>` --data '<json>': Create a new record
- `read <table>` --id '<uuid>': Read a single record
- `read-all <table>` [--limit N]: Read multiple records
- `update <table>` --id '<uuid>' --data '<json>': Update a record
- `delete <table>` --id '<uuid>': Delete a record
- `alter <table>` --operation <add|drop|modify> --column <name> [--type <type>] [--nullable] [--default <value>]: Alter table structure

## Important Notes

1. The script uses the Supabase service role key which has full database access
2. If any migration scripts needs to be run, let the human developer (not you the AI) know and they'll run them in the Supabase SQL Editor 
3. Credentials are loaded from the `.env` file in the Mobile_Jarvis_Backend root directory
4. JSON data must be properly escaped when passed as command-line arguments
5. Be cautious when using delete operations as they cannot be undone


## On Completion

If any tables were added or their schemas changed, make necessary changes to the front end tables.ts and back end tables.py