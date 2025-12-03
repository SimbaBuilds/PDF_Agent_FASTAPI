#!/usr/bin/env python3
"""
Test script for the search_record_pages_by_embedding RPC function.
Tests vector similarity search on medical record content.
"""

import json
import os
import sys
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from supabase import create_client, Client
from app.services.semantic_search import semantic_search_service

# Configuration
USER_ID = "703b410f-f50c-4bc8-b9a3-0991fed5a023"
TEST_QUERY = "anesthesia"

def get_supabase_client() -> Client:
    """Get Supabase client using environment variables."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables are required")

    return create_client(url, key)

def test_rpc_function():
    """Test the search_record_pages_by_embedding RPC function."""

    print("🧪 Testing search_record_pages_by_embedding RPC Function")
    print("=" * 60)
    print(f"User ID: {USER_ID}")
    print(f"Query: '{TEST_QUERY}'")
    print("-" * 60)

    try:
        # Initialize Supabase client
        print("Initializing Supabase client...")
        supabase = get_supabase_client()
        print("✅ Supabase client connected")

        # First, check if the user has any record_pages
        print(f"\nChecking record_pages for user {USER_ID}...")
        pages_result = supabase.from_('record_pages').select('id, medical_record_id, page_number, content, embedding').eq('user_id', USER_ID).limit(5).execute()

        if not pages_result.data:
            print("❌ No record_pages found for this user")
            return

        print(f"✅ Found {len(pages_result.data)} record_pages for user")

        # Show sample data
        for i, page in enumerate(pages_result.data[:2]):
            has_embedding = page.get('embedding') is not None
            content_preview = page.get('content', '')[:100] + "..." if len(page.get('content', '')) > 100 else page.get('content', '')
            print(f"  Page {i+1}: ID={page['id'][:8]}..., Page={page['page_number']}, Has_Embedding={has_embedding}")
            print(f"    Content: {content_preview}")

        # Generate query embedding
        print(f"\nGenerating embedding for query: '{TEST_QUERY}'...")
        try:
            query_embedding = semantic_search_service._generate_query_embedding(TEST_QUERY)
            print(f"✅ Query embedding generated (dimension: {len(query_embedding)})")
        except Exception as e:
            print(f"❌ Failed to generate query embedding: {e}")
            return

        # Test the RPC function
        print(f"\nTesting RPC function: search_record_pages_by_embedding")
        print(f"Parameters:")
        print(f"  - query_embedding: {len(query_embedding)}-dimensional vector")
        print(f"  - target_user_id: {USER_ID}")
        print(f"  - target_medical_record_id: None (search all)")
        print(f"  - match_threshold: 0.3")
        print(f"  - match_count: 5")

        rpc_result = supabase.rpc('search_record_pages_by_embedding', {
            'query_embedding': query_embedding,
            'target_user_id': USER_ID,
            'target_medical_record_id': None,
            'match_threshold': 0.3,
            'match_count': 5
        }).execute()

        print(f"\n📊 RPC Function Results:")
        print("-" * 40)

        if not rpc_result.data:
            print("❌ No results returned from RPC function")
            print("This could mean:")
            print("  1. No record_pages have embeddings generated yet")
            print("  2. No content matches the similarity threshold")
            print("  3. The query doesn't match any medical content")
            return

        print(f"✅ Found {len(rpc_result.data)} matching pages")

        # Display results
        for i, result in enumerate(rpc_result.data):
            print(f"\nResult {i+1}:")
            print(f"  Page ID: {result['id']}")
            print(f"  Medical Record ID: {result['medical_record_id']}")
            print(f"  Page Number: {result['page_number']}")
            print(f"  Similarity Score: {result['similarity_score']:.4f}")
            print(f"  Medical Record Title: {result.get('medical_record_title', 'N/A')}")
            print(f"  File Type: {result.get('medical_record_file_type', 'N/A')}")

            # Show content preview
            content = result.get('content', '')
            if content:
                content_preview = content[:200] + "..." if len(content) > 200 else content
                print(f"  Content Preview: {content_preview}")

                # Highlight anesthesia mentions
                anesthesia_mentions = content.lower().count('anesthesia') + content.lower().count('anesthetic')
                if anesthesia_mentions > 0:
                    print(f"  🎯 Contains {anesthesia_mentions} anesthesia-related mentions")

        # Test with specific medical record ID if we have results
        if rpc_result.data:
            first_record_id = rpc_result.data[0]['medical_record_id']
            print(f"\n🔍 Testing search within specific medical record: {first_record_id}")

            specific_result = supabase.rpc('search_record_pages_by_embedding', {
                'query_embedding': query_embedding,
                'target_user_id': USER_ID,
                'target_medical_record_id': first_record_id,
                'match_threshold': 0.2,  # Lower threshold for more results
                'match_count': 3
            }).execute()

            print(f"✅ Found {len(specific_result.data) if specific_result.data else 0} pages in specific medical record")

        print(f"\n🎉 RPC function test completed successfully!")

    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback
        traceback.print_exc()

def verify_environment():
    """Verify that required environment variables are present."""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPENAI_API_KEY"  # Needed for embedding generation
    ]

    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add these to your .env file")
        return False

    print("✅ All required environment variables found")
    return True

def main():
    """Main function."""

    print("🧪 Record Pages RPC Function Test")
    print("=" * 60)

    # Verify environment first
    if verify_environment():
        test_rpc_function()
    else:
        print("\n🛑 Test aborted due to missing environment variables")

if __name__ == "__main__":
    main()