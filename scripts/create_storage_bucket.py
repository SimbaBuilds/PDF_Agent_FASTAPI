#!/usr/bin/env python3
"""
Script to create the 'pdfs' storage bucket in Supabase.
This should be run once to initialize the storage bucket.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

from supabase import create_client


def create_pdfs_bucket():
    """Create the 'pdfs' storage bucket."""

    print("=" * 70)
    print("📦 Supabase Storage Bucket Creation")
    print("=" * 70)

    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials!")
        print("   Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file")
        return False

    print(f"\n1️⃣  Connecting to Supabase...")
    print(f"   URL: {supabase_url[:30]}...")

    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")

        # Check if bucket already exists
        print(f"\n2️⃣  Checking if 'pdfs' bucket exists...")

        try:
            buckets = supabase.storage.list_buckets()
            existing_bucket = next((b for b in buckets if b.get('name') == 'pdfs' or b.get('id') == 'pdfs'), None)

            if existing_bucket:
                print(f"✅ Bucket 'pdfs' already exists!")
                print(f"   ID: {existing_bucket.get('id')}")
                print(f"   Name: {existing_bucket.get('name')}")
                print(f"   Public: {existing_bucket.get('public', False)}")
                return True
        except Exception as e:
            print(f"   Note: Could not list buckets: {str(e)}")

        # Create the bucket
        print(f"\n3️⃣  Creating 'pdfs' bucket...")

        bucket_options = {
            "public": False,  # Not public - will use signed URLs
            "file_size_limit": 52428800,  # 50MB
            "allowed_mime_types": ["application/pdf"]
        }

        result = supabase.storage.create_bucket(
            "pdfs",
            options=bucket_options
        )

        print(f"✅ Bucket created successfully!")
        print(f"   Name: pdfs")
        print(f"   Public: False (uses signed URLs)")
        print(f"   Max file size: 50MB")
        print(f"   Allowed types: PDF only")

        # Verify bucket was created
        print(f"\n4️⃣  Verifying bucket creation...")
        buckets = supabase.storage.list_buckets()
        pdfs_bucket = next((b for b in buckets if b.get('name') == 'pdfs' or b.get('id') == 'pdfs'), None)

        if pdfs_bucket:
            print(f"✅ Verification successful!")
            print(f"   Bucket 'pdfs' is ready to use")
            return True
        else:
            print(f"⚠️  Bucket was created but not found in list")
            return False

    except Exception as e:
        print(f"\n❌ Error creating bucket: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    print("\n🧪 Creating Supabase Storage Bucket for PDFs\n")

    success = create_pdfs_bucket()

    print("\n" + "=" * 70)
    if success:
        print("✅ Setup Complete!")
        print("=" * 70)
        print("\nThe 'pdfs' bucket is ready to use.")
        print("You can now:")
        print("1. Upload PDFs via the application")
        print("2. Test PDF generation with Supabase storage")
        print("3. Send PDFs via email")
    else:
        print("❌ Setup Failed")
        print("=" * 70)
        print("\nPlease check the errors above and:")
        print("1. Verify your Supabase credentials")
        print("2. Ensure you're using the service role key")
        print("3. Check Supabase dashboard for any issues")
    print("=" * 70)


if __name__ == "__main__":
    main()
