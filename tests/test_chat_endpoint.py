#!/usr/bin/env python3
"""
Test script for the chat endpoint using real Supabase client and JWT authentication.
Supports CLI usage to specify custom test prompts.
"""

import json
import requests
import time
import jwt
import os
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import production logging system
from app.utils.logging.logging_config import setup_logging_from_env, setup_logging_with_custom_file

# Configuration
DEFAULT_PORT = 8000
BASE_URL = "http://localhost:8000"
USER_ID = "703b410f-f50c-4bc8-b9a3-0991fed5a023"
# USER_ID = "f8ac1669-7e9e-4d9e-bb9d-bebd806ce58e"

TEST_MESSAGE = "Please draft an email to Bennet that contains a description about me based on what you know about me."


def generate_test_jwt_token(user_id: str) -> str:
    """Generate a test JWT token for the given user ID."""
    
    # Get Supabase JWT secret from environment
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise ValueError("SUPABASE_JWT_SECRET environment variable not found")
    
    # Create minimal payload without timing issues
    import time
    current_time = int(time.time())
    
    payload = {
        'iss': 'supabase',
        'sub': user_id,
        'aud': 'authenticated',
        'exp': current_time + 3600,  # 1 hour from now
        'iat': current_time - 300,   # 5 minutes ago
        'role': 'authenticated',
        'email': f'test-{user_id}@example.com'
    }
    
    # Generate token
    token = jwt.encode(payload, jwt_secret, algorithm='HS256')
    return token

def test_chat_endpoint(message=None, log_file=None, timeout=360, integration_in_progress=False, port=DEFAULT_PORT):
    """Test the chat endpoint with real authentication and Supabase client."""
    
    test_message = message or TEST_MESSAGE
    
    # Setup production logging system with custom file if specified
    # This will capture ALL application logs but the test script itself won't log
    if log_file:
        # Ensure log file has .log extension
        if not log_file.endswith('.log'):
            log_file += '.log'
        setup_logging_with_custom_file(log_file)
        print(f"📝 Application logs will be written to: logs/{log_file}")
        print(f"📝 This captures logs from chat endpoint, agents, and all application components")
    else:
        setup_logging_from_env()
        print(f"📝 Application logs will be written to: logs/app.log")
        print(f"📝 This captures logs from chat endpoint, agents, and all application components")
    
    base_url = f"http://localhost:{port}"
    
    print(f"Testing chat endpoint with real Supabase client")
    print(f"Base URL: {base_url}")
    print(f"User ID: {USER_ID}")
    print(f"Message: '{test_message}'")
    print(f"Integration in Progress: {integration_in_progress}")
    print("-" * 50)
    
    try:
        # Generate JWT token
        print("Generating JWT token...")
        token = generate_test_jwt_token(USER_ID)
        print(f"✅ JWT token generated successfully")
        
        # Prepare the request data with proper Message format
        current_timestamp = int(time.time())
        
        # Create message in the format expected by the Message model
        user_message = {
            "role": "user",
            "content": test_message,
            "type": "text",
            "timestamp": current_timestamp
        }
        
        chat_request = {
            "message": test_message,
            "timestamp": current_timestamp,
            "history": [user_message],  # Include the message in history with proper format
            "preferences": None,
            "request_id": f"test_{current_timestamp}",
            "integration_in_progress": integration_in_progress
        }
        
        # Convert to JSON string as required by the form data
        json_data = json.dumps(chat_request)
        
        # Prepare the form data
        form_data = {
            "json_data": json_data
        }
        
        # Headers with JWT token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        print(f"Making request to {base_url}/api/chat...")
        print(f"Request ID: {chat_request['request_id']}")
        print("📝 Application logging will now capture all processing...")
        
        # Make the request - this will trigger all the application logging
        response = requests.post(
            f"{base_url}/api/chat",
            data=form_data,
            headers=headers,
            timeout=timeout
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("\n🎉 SUCCESS - Chat endpoint responded successfully!")
            print("=" * 50)
            print(f"Response: {response_data.get('response', 'No response field')}")
            print(f"Timestamp: {response_data.get('timestamp', 'No timestamp')}")
            print(f"Settings Updated: {response_data.get('settings_updated', False)}")
            print(f"Integration In Progress: {response_data.get('integration_in_progress', False)}")
            
        elif response.status_code == 401:
            print(f"\n🔐 AUTH ERROR - Status Code: {response.status_code}")
            print("This likely means:")
            print("1. JWT secret is incorrect")
            print("2. User doesn't exist in user_profiles table")
            print("3. Token format is invalid")
            print(f"Response: {response.text}")
            
        else:
            print(f"\n❌ ERROR - Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except ValueError as e:
        print(f"\n⚙️  CONFIGURATION ERROR: {e}")
        print("Make sure your .env file contains SUPABASE_JWT_SECRET")
        
    except requests.exceptions.Timeout:
        print(f"\n⏰ TIMEOUT - Request took longer than {timeout} seconds")
        print("The chat agent might be processing a complex request")
        
    except requests.exceptions.ConnectionError:
        print(f"\n🔌 CONNECTION ERROR - Could not connect to {base_url}")
        print("Make sure your FastAPI server is running:")
        print("  python -m app.main")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST ERROR: {e}")
        
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

def verify_environment():
    """Verify that required environment variables are present."""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY", 
        "SUPABASE_JWT_SECRET"
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
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Test the chat endpoint with custom prompts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_chat_endpoint.py
  python test_chat_endpoint.py --prompt "What's the weather like today?"
  python test_chat_endpoint.py -p "Help me write a Python function"
  python test_chat_endpoint.py -l "my_test" -t 300
  python test_chat_endpoint.py --log-file "debug_session" --timeout 60
  python test_chat_endpoint.py -i --prompt "Set up Gmail integration"
  python test_chat_endpoint.py --integration-in-progress -p "Complete integration setup"
  python test_chat_endpoint.py --port 8080
  python test_chat_endpoint.py --port 3000 -p "Test on custom port"
  
Note: The log file will contain logs from the application code (chat endpoint, 
agents, services, etc.) but NOT from this test script itself.
        """
    )
    
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        help="Custom test prompt to send to the chat endpoint"
    )
    
    parser.add_argument(
        "-l", "--log-file",
        type=str,
        help="Name of the log file for application logs (without .log extension, will be added automatically)"
    )
    
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=360,
        help="Request timeout in seconds (default: 360)"
    )
    
    parser.add_argument(
        "-i", "--integration-in-progress",
        action="store_true",
        help="Set integration_in_progress flag to True (uses INTEGRATION_COMPLETION_LLM)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port number for the server (default: {DEFAULT_PORT})"
    )
    
    args = parser.parse_args()
    
    print("🧪 Chat Endpoint Test Script (Real Auth + Supabase)")
    print("=" * 60)
    
    # Verify environment first
    if verify_environment():
        test_chat_endpoint(
            message=args.prompt, 
            log_file=args.log_file, 
            timeout=args.timeout,
            integration_in_progress=args.integration_in_progress,
            port=args.port
        )
    else:
        print("\n🛑 Test aborted due to missing environment variables")

if __name__ == "__main__":
    main()


# python tests/test_chat_endpoint.py
# python tests/test_chat_endpoint.py -p "Hi" -t 240
# python tests/test_chat_endpoint.py -i -p "Let’s complete the integration for Outlook Calendar"
# python test_chat_endpoint.py --port 3000