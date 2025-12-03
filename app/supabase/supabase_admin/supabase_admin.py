from supabase import create_client, Client
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv
from pathlib import Path
import argparse
import json

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Debug prints
print("Loading .env from:", env_path)
print("SUPABASE_URL:", os.getenv("SUPABASE_URL"))
print("SUPABASE_SERVICE_ROLE_KEY:", os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


class SupabaseAdmin:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )

    def get_client(self):
        return self.supabase 

    def create_record(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in the specified table."""
        try:
            response = self.supabase.table(table_name).insert(data).execute()
            return response.data[0]
        except Exception as e:
            print(f"Error creating record: {str(e)}")
            raise

    def read_record(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record from the specified table by ID."""
        try:
            response = self.supabase.table(table_name).select("*").eq("id", record_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error reading record: {str(e)}")
            raise

    def read_records(self, table_name: str, limit: int = None) -> List[Dict[str, Any]]:
        """Read multiple records from the specified table."""
        try:
            query = self.supabase.table(table_name).select("*")
            if limit:
                query = query.limit(limit)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error reading records: {str(e)}")
            raise

    def update_record(self, table_name: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record in the specified table."""
        try:
            response = self.supabase.table(table_name).update(data).eq("id", record_id).execute()
            return response.data[0]
        except Exception as e:
            print(f"Error updating record: {str(e)}")
            raise

    def delete_record(self, table_name: str, record_id: str) -> bool:
        """Delete a record from the specified table."""
        try:
            self.supabase.table(table_name).delete().eq("id", record_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting record: {str(e)}")
            raise

    def alter_table(self, table_name: str, operation: str, column_name: str, column_type: str = None, nullable: bool = True, default: str = None) -> bool:
        """Alter a table structure.
        
        Args:
            table_name: Name of the table to alter
            operation: One of 'add', 'drop', 'modify'
            column_name: Name of the column to add/modify/drop
            column_type: SQL type for the column (required for add/modify)
            nullable: Whether the column can be null (for add/modify)
            default: Default value for the column (for add/modify)
        """
        try:
            if operation == 'add':
                if not column_type:
                    raise ValueError("column_type is required for add operation")
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                if not nullable:
                    sql += " NOT NULL"
                if default is not None:
                    sql += f" DEFAULT {default}"
            elif operation == 'drop':
                sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
            elif operation == 'modify':
                if not column_type:
                    raise ValueError("column_type is required for modify operation")
                sql = f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {column_type}"
                if not nullable:
                    sql += f", ALTER COLUMN {column_name} SET NOT NULL"
                else:
                    sql += f", ALTER COLUMN {column_name} DROP NOT NULL"
                if default is not None:
                    sql += f", ALTER COLUMN {column_name} SET DEFAULT {default}"
            else:
                raise ValueError(f"Invalid operation: {operation}")

            print(f"Executing SQL: {sql}")
            # Execute the SQL using the execute_ddl function
            response = self.supabase.rpc('execute_ddl', {'ddl_command': sql}).execute()
            return True
        except Exception as e:
            print(f"Error altering table: {str(e)}")
            raise

    def list_tables(self) -> List[str]:
        """List all tables in the public schema."""
        try:
            # First try to get a list of tables by querying any table
            response = self.supabase.table('curriculum_plans').select('*', count='exact').limit(0).execute()
            print("Tables found in schema")
            return True
        except Exception as e:
            if 'relation "public.curriculum_plans" does not exist' in str(e):
                print("Table curriculum_plans does not exist")
            print(f"Error listing tables: {str(e)}")
            return False

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a specific table."""
        try:
            response = self.supabase.rpc('get_table_info', {'p_table_name': table_name}).execute()
            return response.data
        except Exception as e:
            print(f"Error getting table info: {str(e)}")
            raise

def explore_database():
    """Explore the database structure and content."""
    admin = SupabaseAdmin()
    
    try:
        # Get sample data from conversations table
        print("\nFetching sample records from conversations table:")
        response = admin.supabase.from_('conversations').select('*').limit(5).execute()
        if response.data:
            print("\nSample records:")
            for record in response.data:
                print(f"  {record}")
        else:
            print("No records found in the conversations table")
            
    except Exception as e:
        print(f"Error exploring database: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Supabase Admin CLI')
    parser.add_argument('action', choices=['create', 'read', 'read-all', 'update', 'delete', 'alter'],
                      help='Action to perform')
    parser.add_argument('table', help='Table name')
    parser.add_argument('--id', help='Record ID for read/update/delete operations')
    parser.add_argument('--data', help='JSON data for create/update operations')
    parser.add_argument('--limit', type=int, help='Limit for read-all operation')
    parser.add_argument('--operation', choices=['add', 'drop', 'modify'], help='Alter table operation')
    parser.add_argument('--column', help='Column name for alter operation')
    parser.add_argument('--type', help='Column type for alter operation')
    parser.add_argument('--nullable', action='store_true', help='Make column nullable')
    parser.add_argument('--default', help='Default value for column')

    args = parser.parse_args()
    admin = SupabaseAdmin()

    try:
        if args.action == 'alter':
            if not args.operation or not args.column:
                print("Error: --operation and --column are required for alter operation")
                return
            result = admin.alter_table(
                args.table,
                args.operation,
                args.column,
                args.type,
                args.nullable,
                args.default
            )
            print(f"Successfully altered table {args.table}")
            return 0

        elif args.action == 'create':
            if not args.data:
                print("Error: --data is required for create operation")
                return
            data = json.loads(args.data)
            result = admin.create_record(args.table, data)
            print(json.dumps(result, indent=2))

        elif args.action == 'read':
            if not args.id:
                print("Error: --id is required for read operation")
                return
            result = admin.read_record(args.table, args.id)
            print(json.dumps(result, indent=2))

        elif args.action == 'read-all':
            result = admin.read_records(args.table, args.limit)
            print(json.dumps(result, indent=2))

        elif args.action == 'update':
            if not args.id or not args.data:
                print("Error: --id and --data are required for update operation")
                return
            data = json.loads(args.data)
            result = admin.update_record(args.table, args.id, data)
            print(json.dumps(result, indent=2))

        elif args.action == 'delete':
            if not args.id:
                print("Error: --id is required for delete operation")
                return
            result = admin.delete_record(args.table, args.id)
            print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main()) 



# Must define the following fucntions in Supabase DB:

# BEGIN
#     RETURN QUERY
#     SELECT 
#         c.column_name::text,
#         c.data_type::text,
#         c.is_nullable::boolean,
#         c.column_default::text
#     FROM information_schema.columns c
#     WHERE c.table_schema = 'public'
#     AND c.table_name = p_table_name;
# END;


# BEGIN
#   EXECUTE ddl_command;
# END;
