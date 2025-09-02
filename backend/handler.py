# handler.py
import os
import tempfile
import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, auth, storage
from pydantic import BaseModel
from fastapi.responses import Response
import requests
from urllib.parse import unquote

# Import resume processing components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv
from src.utils import extract_pdf_text
from src.core.langgraph_orchestrator import LangGraphOrchestrator
from src.core.pdf_docx_generator import PdfDocxGenerator
from src.core.gemini_client import GeminiClient
from src.core.response_logger import ResponseLogger

# Load environment variables
load_dotenv()


# --- Firebase Admin SDK Initialization ---
# IMPORTANT: Create a `serviceAccountKey.json` file in the same directory
# This file is obtained from your Firebase project settings.
# Go to Project Settings -> Service accounts -> Generate new private key
try:
    cred = credentials.Certificate("C:/Users/ayush/PycharmProjects/FastAPIProject1/serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'storageBucket': f'{cred.project_id}.appspot.com'  # Default storage bucket
    })
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
    title="AI Resume Builder API",
    description="""
    API backend for AI-powered resume processing with Firebase integration.
    
    Features:
    - Firebase authentication for user management
    - AI-powered resume optimization using Gemini
    - Resume processing with job description matching
    - Document generation (PDF/DOCX)
    - Firebase Storage integration
    
    Available Endpoints:
    - GET /: Public endpoint
    - GET /api/protected: Protected endpoint requiring authentication
    - POST /process_resume: Process resume with AI (requires authentication)
    - GET /health: Health check endpoint
    """,
    version="2.0.0",
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

class ProcessResumeRequest(BaseModel):
    """Request model for processing resume."""
    resume_firebase_url: str
    job_description_url: str
    
class ProcessResumeResponse(BaseModel):
    """Response model for processed resume."""
    success: bool
    message: str
    docx_url: Optional[str] = None
    pdf_url: Optional[str] = None
    user_name: Optional[str] = None
    company_name: Optional[str] = None

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


# --- Helper Functions ---

def download_file_from_firebase_url(firebase_url: str, local_path: str) -> bool:
    """
    Download a file from Firebase Storage URL to local path.
    """
    try:
        response = requests.get(firebase_url, stream=True)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logging.info(f"Successfully downloaded file to {local_path}")
        return True
    except Exception as e:
        logging.error(f"Error downloading file from {firebase_url}: {e}")
        return False

def upload_file_to_firebase_storage(local_path: str, firebase_path: str) -> Optional[str]:
    """
    Upload a file to Firebase Storage and return the download URL.
    """
    try:
        bucket = storage.bucket()
        blob = bucket.blob(firebase_path)
        
        with open(local_path, 'rb') as f:
            blob.upload_from_file(f)
        
        # Make the blob publicly readable (optional)
        blob.make_public()
        
        download_url = blob.public_url
        logging.info(f"Successfully uploaded file to Firebase: {download_url}")
        return download_url
    except Exception as e:
        logging.error(f"Error uploading file to Firebase: {e}")
        return None

def cleanup_temp_files(*file_paths):
    """Clean up temporary files."""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logging.warning(f"Could not clean up file {file_path}: {e}")


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

@app.post("/process_resume", response_model=ProcessResumeResponse)
async def process_resume(
    request: ProcessResumeRequest,
    current_user: User = Depends(get_current_user)
) -> ProcessResumeResponse:
    """
    Process a resume using Firebase Storage URL and job description URL.
    
    This endpoint:
    1. Downloads the resume PDF from Firebase Storage
    2. Processes it using the AI resume builder pipeline
    3. Uploads the generated DOCX and PDF files back to Firebase Storage
    4. Returns the download URLs
    """
    logging.info(f"Processing resume for user {current_user.uid}")
    
    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()
    temp_resume_path = None
    temp_docx_path = None
    temp_pdf_path = None
    
    try:
        # --- 1. Download resume from Firebase ---
        temp_resume_path = os.path.join(temp_dir, "resume.pdf")
        
        if not download_file_from_firebase_url(request.resume_firebase_url, temp_resume_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to download resume from Firebase URL"
            )
        
        # --- 2. Extract text from PDF ---
        resume_text = extract_pdf_text(temp_resume_path)
        if not resume_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from resume PDF"
            )
        
        # --- 3. Initialize AI services ---
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GEMINI_API_KEY environment variable not set"
            )
        
        gemini_client = GeminiClient(api_key=api_key)
        orchestrator = LangGraphOrchestrator(gemini_client)
        
        # --- 4. Run resume processing pipeline ---
        logging.info("Starting resume generation pipeline...")
        final_content = orchestrator.run(
            resume_txt=resume_text,
            job_description_url=request.job_description_url
        )
        
        if not final_content or 'markdown_resume' not in final_content or not final_content['markdown_resume']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Pipeline failed to generate resume content"
            )
        
        # --- 5. Generate DOCX and PDF files ---
        markdown_resume = final_content['markdown_resume']
        
        # Extract user name and company name
        company_name = final_content.get('job_analysis', {}).get('company_name', 'Company').replace(' ', '')
        user_name = final_content.get('user_profile', {}).get('name', 'User').replace(' ', '')
        
        # Create file names with timestamp
        date_str = datetime.now().strftime("%d%m")
        base_filename = f"{user_name}-{company_name}-{date_str}"
        
        # Generate DOCX and PDF
        generator = PdfDocxGenerator(markdown_content=markdown_resume)
        
        temp_docx_path = os.path.join(temp_dir, f"{base_filename}.docx")
        generator.to_docx(temp_docx_path)
        
        temp_pdf_path = os.path.join(temp_dir, f"{base_filename}.pdf")
        generator.to_pdf(temp_pdf_path)
        
        # --- 6. Upload generated files to Firebase Storage ---
        firebase_base_path = f"processed_resumes/{current_user.uid}/{base_filename}"
        
        docx_firebase_path = f"{firebase_base_path}.docx"
        pdf_firebase_path = f"{firebase_base_path}.pdf"
        
        docx_url = upload_file_to_firebase_storage(temp_docx_path, docx_firebase_path)
        pdf_url = upload_file_to_firebase_storage(temp_pdf_path, pdf_firebase_path)
        
        if not docx_url or not pdf_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload generated files to Firebase Storage"
            )
        
        logging.info(f"Successfully processed resume for user {current_user.uid}")
        
        return ProcessResumeResponse(
            success=True,
            message="Resume processed successfully",
            docx_url=docx_url,
            pdf_url=pdf_url,
            user_name=user_name,
            company_name=company_name
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Unexpected error processing resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
    finally:
        # --- 7. Cleanup temporary files ---
        cleanup_temp_files(temp_resume_path, temp_docx_path, temp_pdf_path)
        try:
            if temp_dir and os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            logging.warning(f"Could not remove temp directory {temp_dir}: {e}")

@app.get("/user_processed_resumes")
async def get_user_processed_resumes(current_user: User = Depends(get_current_user)):
    """
    Get a list of processed resumes for the current user from Firebase Storage.
    """
    try:
        bucket = storage.bucket()
        prefix = f"processed_resumes/{current_user.uid}/"
        
        blobs = bucket.list_blobs(prefix=prefix)
        
        files = []
        for blob in blobs:
            # Extract filename and get download URL
            filename = blob.name.split('/')[-1]  # Get just the filename
            download_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.now() + timedelta(hours=1),
                method="GET"
            )
            
            files.append({
                "filename": filename,
                "download_url": download_url,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "size": blob.size
            })
        
        return {
            "success": True,
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        logging.error(f"Error retrieving user files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user files: {str(e)}"
        )

# To run this app:
# 1. Install dependencies: pip install "fastapi[all]" firebase-admin
# 2. Save the code as `handler.py`.
# 3. Place your `serviceAccountKey.json` in the same directory.
# 4. Run the server: uvicorn handler:app --reload
