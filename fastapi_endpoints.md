# FastAPI Backend Endpoints for PDF Agent

This document provides the complete FastAPI backend implementation for the PDF Agent Next.js application.

## Table of Contents
- [Configuration](#configuration)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
- [Setup Instructions](#setup-instructions)

---

## Configuration

### Environment Variables (`.env`)

```bash
# Get this from Supabase Dashboard → Settings → API → JWT Settings → JWT Secret
SUPABASE_JWT_SECRET=your-jwt-secret-here

# Your Supabase project URL
SUPABASE_URL=https://onqgmkffynfqucqgwjiw.supabase.co

# Optional: for downloading PDFs from Supabase Storage
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**IMPORTANT**: The `SUPABASE_JWT_SECRET` is NOT the anon key. Find it in:
- Supabase Dashboard → Settings → API → JWT Settings → JWT Secret

### Requirements (`requirements.txt`)

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.10.0
PyJWT==2.9.0
python-multipart==0.0.12
python-dotenv==1.0.1
```

---

## Complete FastAPI Implementation

### Main Application (`main.py`)

```python
from fastapi import FastAPI, HTTPException, Depends, Header, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import jwt
import os
import json
from datetime import datetime

app = FastAPI()
security = HTTPBearer()

# ============================================
# CONFIGURATION
# ============================================
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")

if not SUPABASE_JWT_SECRET:
    raise ValueError("SUPABASE_JWT_SECRET must be set in environment variables")

# ============================================
# AUTHENTICATION
# ============================================
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify Supabase JWT token and return the decoded payload
    """
    token = credentials.credentials

    try:
        # Decode and verify the JWT token
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"  # Supabase uses this audience
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def get_user_id(payload: Dict[str, Any] = Depends(verify_token)) -> str:
    """
    Extract user ID from JWT payload
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    return user_id

# ============================================
# MODELS
# ============================================
class ChatMessageModel(BaseModel):
    role: str
    content: str
    timestamp: int

class ChatRequest(BaseModel):
    message: str
    timestamp: int
    history: List[ChatMessageModel]
    document_ids: Optional[List[str]] = []
    request_id: Optional[str] = None

class ProcessPDFsDocument(BaseModel):
    id: str
    url: str
    filename: str
    size_bytes: int

class ProcessPDFsRequest(BaseModel):
    documents: List[ProcessPDFsDocument]
    request_id: Optional[str] = None

# ============================================
# CHAT ENDPOINT
# ============================================
@app.post("/api/chat")
async def chat(
    json_data: str = Form(...),
    user_id: str = Depends(get_user_id)
):
    """
    Chat endpoint that receives messages and returns AI responses

    Expected FormData:
    - json_data: JSON string containing ChatRequest data
    - Authorization header: Bearer <supabase_access_token>
    """
    try:
        # Parse the JSON data from FormData
        data = json.loads(json_data)
        chat_request = ChatRequest(**data)

        print(f"Chat request from user {user_id}: {chat_request.message[:50]}...")
        print(f"Request ID: {chat_request.request_id}")
        print(f"Document IDs: {chat_request.document_ids}")
        print(f"History length: {len(chat_request.history)}")

        # ============================================
        # YOUR AI PROCESSING LOGIC GOES HERE
        # ============================================
        # 1. Retrieve PDFs using document_ids
        # 2. Process PDFs and extract relevant context
        # 3. Build prompt with context and chat history
        # 4. Call your LLM (OpenAI, Anthropic, etc.)
        # 5. Generate response

        # Example response (replace with actual AI logic)
        response_text = f"Received your message: {chat_request.message}. Processing {len(chat_request.document_ids)} documents."
        sources = []  # List of source references from PDFs

        # ============================================
        # RETURN RESPONSE
        # ============================================
        return {
            "response": response_text,
            "timestamp": int(datetime.now().timestamp() * 1000),
            "sources": sources,
            "request_id": chat_request.request_id
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {str(e)}")
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ============================================
# PROCESS PDFs ENDPOINT
# ============================================
@app.post("/api/process_pdfs")
async def process_pdfs(
    json_data: str = Form(...),
    user_id: str = Depends(get_user_id)
):
    """
    Process PDF documents endpoint

    Expected FormData:
    - json_data: JSON string containing ProcessPDFsRequest data
    - Authorization header: Bearer <supabase_access_token>
    """
    try:
        # Parse the JSON data from FormData
        data = json.loads(json_data)
        request = ProcessPDFsRequest(**data)

        print(f"Process PDFs request from user {user_id}")
        print(f"Request ID: {request.request_id}")
        print(f"Documents to process: {len(request.documents)}")

        processed_documents = []

        for doc in request.documents:
            print(f"Processing document: {doc.filename} ({doc.id})")

            # ============================================
            # YOUR PDF PROCESSING LOGIC GOES HERE
            # ============================================
            # 1. Download PDF from doc.url (it's a signed Supabase URL)
            # 2. Extract text/content from PDF
            # 3. Process/chunk the content
            # 4. Store embeddings in vector database
            # 5. Generate summary

            # Example result (replace with actual processing)
            processed_documents.append({
                "id": doc.id,
                "num_pages": 10,  # Replace with actual page count
                "summary": f"Summary of {doc.filename}",  # Replace with actual summary
                "status": "completed"
            })

        # ============================================
        # RETURN RESPONSE
        # ============================================
        return {
            "message": f"Successfully processed {len(processed_documents)} PDFs",
            "documents_processed": processed_documents,
            "request_id": request.request_id,
            "timestamp": int(datetime.now().timestamp() * 1000)
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {str(e)}")
    except Exception as e:
        print(f"Process PDFs error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# ============================================
# HEALTH CHECK
# ============================================
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": int(datetime.now().timestamp() * 1000)
    }

# ============================================
# TEST ENDPOINT (for debugging auth)
# ============================================
@app.get("/api/test-auth")
async def test_auth(user_id: str = Depends(get_user_id), payload: Dict = Depends(verify_token)):
    """
    Test endpoint to verify authentication is working
    """
    return {
        "message": "Authentication successful",
        "user_id": user_id,
        "token_payload": payload
    }
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in your FastAPI project root:

```bash
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-dashboard
SUPABASE_URL=https://onqgmkffynfqucqgwjiw.supabase.co
```

**To get your JWT Secret:**
1. Go to Supabase Dashboard
2. Navigate to Settings → API
3. Scroll to JWT Settings section
4. Copy the JWT Secret (NOT the anon key!)

### 3. Run the Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Test Authentication

Use the test endpoint to verify your JWT secret is configured correctly:

```bash
curl -X GET "http://localhost:8000/api/test-auth" \
  -H "Authorization: Bearer YOUR_SUPABASE_ACCESS_TOKEN"
```

You should get:
```json
{
  "message": "Authentication successful",
  "user_id": "user-uuid-here",
  "token_payload": { ... }
}
```

---

## Authentication Flow

### How It Works

1. **Next.js Frontend** → Gets user session from Supabase
2. **Next.js API Route** → Extracts `session.access_token`
3. **FastAPI Backend** → Receives token in `Authorization: Bearer <token>` header
4. **JWT Verification** → FastAPI decodes token using `SUPABASE_JWT_SECRET`
5. **User ID Extraction** → Gets `user_id` from JWT payload's `sub` field
6. **Request Processing** → Proceeds with authenticated request

### Token Structure

The Supabase access token is a JWT with this structure:

```json
{
  "sub": "user-uuid",           // User ID
  "aud": "authenticated",       // Audience
  "role": "authenticated",      // Role
  "iat": 1234567890,           // Issued at
  "exp": 1234571490            // Expires at
}
```

---

## Error Handling

### Common Issues

#### 1. "Invalid or expired token"
- **Cause**: Wrong `SUPABASE_JWT_SECRET` or expired token
- **Fix**: Verify you're using JWT Secret (not anon key) from Supabase Dashboard

#### 2. "Token has expired"
- **Cause**: Token has exceeded its expiration time
- **Fix**: Frontend should refresh the session before making requests

#### 3. "Authentication failed"
- **Cause**: Malformed token or incorrect algorithm
- **Fix**: Ensure token is being sent correctly from Next.js

---

## Next.js Integration

Your Next.js API routes already send the correct format. They:

1. ✅ Use `createSupabaseAppServerClient()` to get Supabase instance
2. ✅ Call `supabase.auth.getUser()` to authenticate user
3. ✅ Call `supabase.auth.getSession()` to get session token
4. ✅ Send `Authorization: Bearer ${session.access_token}` header
5. ✅ Send FormData with `json_data` field

Example from your code (`app/api/chat/route.ts`):

```typescript
const response = await fetch(`${FASTAPI_BACKEND_URL}/api/chat`, {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${session.access_token}`,
  },
  body: formData,
})
```

---

## Key Points

1. **JWT Secret**: Use the JWT Secret from Supabase Dashboard, NOT the anon key
2. **FormData Format**: Next.js sends FormData with `json_data` field
3. **User ID**: Extracted from JWT payload's `sub` field
4. **Dependencies**: FastAPI uses dependency injection for clean auth
5. **Error Codes**: Returns 401 for auth failures, 400 for bad requests, 500 for server errors

---

## Testing Checklist

- [ ] Environment variables configured (`.env` file)
- [ ] JWT Secret is correct (from Supabase Dashboard)
- [ ] FastAPI server is running on correct port (8000)
- [ ] Next.js `FASTAPI_BACKEND_URL` points to FastAPI server
- [ ] Test auth endpoint returns successful response
- [ ] Chat endpoint receives and processes messages
- [ ] Process PDFs endpoint receives and processes documents
