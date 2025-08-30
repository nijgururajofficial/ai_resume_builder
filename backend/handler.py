# handler.py
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, auth
from pydantic import BaseModel
from fastapi.responses import Response


# --- Firebase Admin SDK Initialization ---
# IMPORTANT: Create a `serviceAccountKey.json` file in the same directory
# This file is obtained from your Firebase project settings.
# Go to Project Settings -> Service accounts -> Generate new private key
try:
    cred = credentials.Certificate("C:/Users/ayush/PycharmProjects/FastAPIProject1/serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("DEBUG: Firebase Admin SDK initialized successfully")
    print(f"DEBUG: Service account project ID: {cred.project_id}")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    print("Please make sure 'serviceAccountKey.json' is present in the root directory.")
    print("Also ensure the service account key matches your Firebase project.")
    # You might want to exit or handle this more gracefully in a real app
    # For this example, we'll let it raise an error if the file is missing.


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Firebase Authentication API",
    description="""
    API backend for Firebase authentication demonstration.
    
    Features:
    - Firebase authentication for user management
    - Protected and public endpoints
    - JWT token validation
    
    Available Endpoints:
    - GET /: Public endpoint
    - GET /api/protected: Protected endpoint requiring authentication
    """,
    version="1.0.0",
)

# --- CORS Middleware ---
# This allows the frontend (running on a different domain/port) to communicate with this backend.
origins = [
    "http://localhost:3000",
    "http://localhost:8080", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://localhost:5500",  # Common Live Server port
    "http://127.0.0.1:5500",
    "*"  # Allow all origins for development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*", "Authorization", "Content-Type"],
    expose_headers=["*"]
)

# Debug middleware to log all requests
@app.middleware("http")
async def debug_requests(request: Request, call_next):
    print(f"DEBUG: Incoming {request.method} request to {request.url.path}")
    print(f"DEBUG: Headers: {dict(request.headers)}")
    if "authorization" in request.headers:
        auth_header = request.headers["authorization"]
        print(f"DEBUG: Authorization header found: {auth_header[:50]}...")
    else:
        print("DEBUG: No Authorization header found")
    
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response


# --- Security Dependency ---
# This scheme will look for an 'Authorization' header with a 'Bearer' token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(BaseModel):
    """Pydantic model to represent user data from Firebase token."""
    uid: str
    email: str | None = None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to verify Firebase ID token and get user data.
    
    This function is injected into protected routes. It takes the Bearer token
    from the Authorization header, verifies it with Firebase, and returns
    the user's data. If the token is invalid or expired, it raises an HTTPException.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(f"DEBUG: Received token (first 50 chars): {token[:50]}...")
        print(f"DEBUG: Token length: {len(token)}")
        
        # Verify the token against the Firebase Auth API.
        decoded_token = auth.verify_id_token(token)
        print(f"DEBUG: Token verified successfully for user: {decoded_token.get('email')}")
        
        user = User(uid=decoded_token.get("uid"), email=decoded_token.get("email"))
        return user
    except Exception as e:
        # This can happen if the token is expired, malformed, etc.
        print(f"DEBUG: Token verification failed with error: {e}")
        print(f"DEBUG: Error type: {type(e).__name__}")
        raise credentials_exception



# --- API Endpoints ---

@app.get("/")
def read_root():
    """Publicly accessible endpoint."""
    return {"message": "Hello from the Firebase Authentication API! This is a public endpoint."}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

@app.get("/api/protected")
def read_protected_data(current_user: User = Depends(get_current_user)):
    """
    Protected endpoint that requires a valid Firebase ID token.
    
    The `Depends(get_current_user)` part ensures that this function only
    runs if `get_current_user` successfully validates the token.
    The user's data is then available in the `current_user` variable.
    """
    print("inside protected route", User)
    return {
        "message": f"Hello {current_user.email}! This is a protected message.",
        "user_id": current_user.uid
    }

@app.get("/health")
async def say_hello():
    return {"message": "Health OK"}

# To run this app:
# 1. Install dependencies: pip install "fastapi[all]" firebase-admin
# 2. Save the code as `handler.py`.
# 3. Place your `serviceAccountKey.json` in the same directory.
# 4. Run the server: uvicorn handler:app --reload
