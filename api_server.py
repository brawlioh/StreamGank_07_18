#!/usr/bin/env python3
"""
StreamGank Video Generation API Server
Complete FastAPI server optimized for Railway deployment

Usage:
    python api_server.py                    # Development mode
    uvicorn api_server:app --host 0.0.0.0   # Production mode
"""

import os
import sys
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Import MODULAR functions - Clean API interface
    from video.creatomate_client import check_creatomate_render_status, wait_for_creatomate_completion
    from core.workflow import process_existing_heygen_videos, run_full_workflow
    MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Could not import core modules: {e}")
    logging.warning("🔧 Running in API-only mode - core functionality disabled")
    MODULES_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app initialization
app = FastAPI(
    title="StreamGank Video Generation API",
    description="Professional video generation API for StreamGank platform",
    version="1.4.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for Netlify frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.netlify.app",
        "https://*.netlify.com", 
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://streamgank.com",
        "https://*.streamgank.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class GenerationRequest(BaseModel):
    country: str = Field(..., pattern="^(US|FR|GB|CA|AU|DE|IT|ES|PT)$")
    platform: str = Field(..., min_length=1)
    genre: str = Field(..., min_length=1)
    contentType: str = Field(..., min_length=1)
    template: str = Field(default="auto")
    pauseAfterExtraction: bool = Field(default=False)
    numMovies: int = Field(default=3, ge=1, le=10)
    heygenTemplateId: str = Field(default="")

class StatusCheckRequest(BaseModel):
    creatomateId: str = Field(..., min_length=1)

class HeyGenProcessRequest(BaseModel):
    videoIds: Dict[str, str] = Field(..., min_items=1)

class JobResponse(BaseModel):
    success: bool
    jobId: str
    message: str
    status: str
    queuePosition: Optional[int] = None

# In-memory job storage (in production, use Redis or database)
job_storage: Dict[str, Dict[str, Any]] = {}

# Simple in-memory queue (no Redis dependency needed)
print("ℹ️ Using in-memory job storage (Railway deployment)")

@app.get("/", response_class=HTMLResponse)
async def root():
    """API dashboard with basic interface"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>StreamGank API Server</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; }}
            .status {{ background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
            .links a {{ display: inline-block; margin: 10px; padding: 10px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 StreamGank API Server</h1>
            <div class="status">
                <strong>Status:</strong> ✅ Server Running on Railway<br>
                <strong>Environment:</strong> {'Production' if os.getenv('RAILWAY_ENVIRONMENT') else 'Development'}<br>
                <strong>Version:</strong> 1.4.0<br>
                <strong>Modules:</strong> {'✅ Available' if MODULES_AVAILABLE else '❌ Limited Mode'}
            </div>

            <div class="stats">
                <div class="stat">
                    <h3>{len(job_storage)}</h3>
                    <p>Total Jobs</p>
                </div>
                <div class="stat">
                    <h3>{len([j for j in job_storage.values() if j.get('status') == 'processing'])}</h3>
                    <p>Processing</p>
                </div>
                <div class="stat">
                    <h3>{len([j for j in job_storage.values() if j.get('status') == 'completed'])}</h3>
                    <p>Completed</p>
                </div>
            </div>

            <div class="links">
                <a href="/docs">📖 API Documentation</a>
                <a href="/health">🔍 Health Check</a>
                <a href="/api/queue/status">📊 Queue Status</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/status")
async def status():
    """Simple status endpoint"""
    return {
        "status": "healthy",
        "version": "1.4.0",
        "timestamp": datetime.utcnow().isoformat(),
        "modules_available": MODULES_AVAILABLE,
        "jobs_total": len(job_storage),
        "jobs_processing": len([j for j in job_storage.values() if j.get('status') == 'processing']),
        "jobs_completed": len([j for j in job_storage.values() if j.get('status') == 'completed'])
    }

@app.get("/health")
async def health_check():
    """Detailed health check for Railway"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": {
            "railway": os.getenv('RAILWAY_ENVIRONMENT', 'local'),
            "port": os.getenv('PORT', '8000'),
            "modules_available": MODULES_AVAILABLE,
            "jobs_total": len(job_storage),
            "jobs_processing": len([j for j in job_storage.values() if j.get('status') == 'processing']),
            "jobs_completed": len([j for j in job_storage.values() if j.get('status') == 'completed'])
        }
    }

# =============================================================================
# VIDEO GENERATION ENDPOINTS
# =============================================================================

@app.post("/api/generate")
async def generate_video(request: GenerationRequest, background_tasks: BackgroundTasks):
    """Generate video with background processing"""
    try:
        logger.info(f"📨 Received generation request: {request.dict()}")
        
        # Generate unique job ID
        job_id = f"job_{int(datetime.utcnow().timestamp())}_{os.urandom(4).hex()}"
        
        # Store job in memory (in production, use persistent storage)
        job_storage[job_id] = {
            "id": job_id,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "parameters": {
                "country": request.country,
                "platform": request.platform,
                "genre": request.genre,
                "contentType": request.contentType,
                "template": request.template,
                "pauseAfterExtraction": request.pauseAfterExtraction,
                "numMovies": request.numMovies,
                "heygenTemplateId": request.heygenTemplateId
            },
            "progress": 0,
            "current_step": "Initializing...",
            "results": None,
            "error": None
        }
        
        # Process job directly in FastAPI using background task
        if MODULES_AVAILABLE:
            logger.info(f"🚀 Starting background processing for job {job_id}")
            background_tasks.add_task(process_video_generation, job_id, request)
            job_storage[job_id].update({
                "status": "processing", 
                "current_step": "Starting video generation..."
            })
        else:
            logger.error(f"❌ Core modules not available - cannot process job {job_id}")
            job_storage[job_id].update({
                "status": "failed",
                "error": "Core modules not available",
                "current_step": "Failed to start processing"
            })
        
        # Calculate queue stats for GUI
        pending_jobs = len([j for j in job_storage.values() if j.get('status') == 'queued'])
        processing_jobs = len([j for j in job_storage.values() if j.get('status') == 'processing'])
        completed_jobs = len([j for j in job_storage.values() if j.get('status') == 'completed'])
        failed_jobs = len([j for j in job_storage.values() if j.get('status') == 'failed'])
        
        return {
            "success": True,
            "jobId": job_id,
            "message": "Job queued successfully - processing will be handled by background worker",
            "status": "queued",
            "queuePosition": pending_jobs,
            "queueStatus": {
                "pending": pending_jobs,
                "processing": processing_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating generation job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get job status by ID"""
    try:
        if job_id not in job_storage:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = job_storage[job_id]
        return {
            "success": True,
            "job": job
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_video_generation(job_id: str, request: GenerationRequest):
    """Background task to process video generation"""
    try:
        logger.info(f"🎬 Processing video generation job {job_id}")
        
        # Update job status to processing
        job_storage[job_id].update({
            "status": "processing",
            "progress": 10,
            "current_step": "Starting video generation workflow..."
        })
        
        # Call the main workflow function with correct parameter order
        # run_full_workflow(num_movies, country, genre, platform, content_type, ...)
        result = await asyncio.get_event_loop().run_in_executor(
            None, 
            run_full_workflow,
            request.numMovies,        # num_movies (first parameter)
            request.country,          # country
            request.genre,            # genre  
            request.platform,         # platform
            request.contentType,      # content_type
            None,                     # output (not needed)
            False,                    # skip_scroll_video
            None,                     # smooth_scroll (use default)
            None,                     # scroll_distance (use default)
            "heygen_last3s",          # poster_timing_mode
            request.template if request.template != "auto" else None,  # heygen_template_id
            request.pauseAfterExtraction  # pause_after_extraction
        )
        
        # Update job with results
        job_storage[job_id].update({
            "status": "completed",
            "progress": 100,
            "current_step": "Video generation completed!",
            "results": result,
            "videoUrl": result.get("video_url") if result else None,
            "creatomateId": result.get("creatomate_id") if result else None
        })
        
        logger.info(f"✅ Video generation job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error processing video generation job {job_id}: {str(e)}")
        job_storage[job_id].update({
            "status": "failed",
            "progress": 0,
            "current_step": f"Video generation failed: {str(e)}",
            "error": str(e)
        })

# =============================================================================
# QUEUE MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/api/queue/status")
async def get_queue_status():
    """Get queue statistics (compatible with GUI expectations)"""
    try:
        # Calculate queue statistics from job storage
        pending = len([j for j in job_storage.values() if j.get('status') == 'pending'])
        processing = len([j for j in job_storage.values() if j.get('status') == 'processing'])
        completed = len([j for j in job_storage.values() if j.get('status') == 'completed'])
        failed = len([j for j in job_storage.values() if j.get('status') == 'failed'])
        
        return {
            "success": True,
            "stats": {
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "total": len(job_storage)
            }
        }
    except Exception as e:
        logger.error(f"❌ Error getting queue status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/platforms/{country}")
async def get_platforms(country: str):
    """Get available platforms for a country"""
    try:
        logger.info(f"🌍 Fetching platforms for country: {country}")
        
        # Platform mapping for different countries
        platforms_map = {
            "US": ["Netflix", "Prime Video", "Hulu", "Max", "Disney+", "Apple TV+", "Free"],
            "FR": ["Netflix", "Prime Video", "Disney+", "Max", "Apple TV+", "Free"],
            "GB": ["Netflix", "Prime Video", "Disney+", "Apple TV+", "Free"],
            "CA": ["Netflix", "Prime Video", "Disney+", "Apple TV+", "Free"],
            "DE": ["Netflix", "Prime Video", "Disney+", "Apple TV+", "Free"],
            "IT": ["Netflix", "Prime Video", "Disney+", "Apple TV+", "Free"],
            "ES": ["Netflix", "Prime Video", "Disney+", "Apple TV+", "Free"],
            "PT": ["Netflix", "Prime Video", "Disney+", "Apple TV+", "Free"]
        }
        
        platforms = platforms_map.get(country.upper(), ["Netflix", "Prime Video", "Free"])
        
        return {
            "success": True,
            "platforms": platforms,
            "country": country
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting platforms for {country}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/genres/{country}")
async def get_genres(country: str):
    """Get available genres for a country"""
    try:
        logger.info(f"🎭 Fetching genres for country: {country}")
        
        # Genre mapping for different countries
        if country.upper() == "FR":
            genres = ["Action", "Comédie", "Drame", "Horreur", "Thriller", "Romance", "Science-fiction", "Documentaire"]
        else:
            genres = ["Action", "Comedy", "Drama", "Horror", "Thriller", "Romance", "Sci-Fi", "Documentary"]
        
        return {
            "success": True,
            "genres": genres,
            "country": country
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting genres for {country}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/validate-url")
async def validate_url(request: Request):
    """Validate StreamGank URL"""
    try:
        body = await request.json()
        url = body.get("url", "")
        
        logger.info(f"🔍 Validating URL: {url}")
        
        # Basic URL validation
        if not url or not url.startswith("https://streamgank.com"):
            return {
                "success": False,
                "message": "Invalid StreamGank URL"
            }
        
        return {
            "success": True,
            "message": "URL is valid",
            "url": url
        }
        
    except Exception as e:
        logger.error(f"❌ Error validating URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# MAIN APPLICATION
# =============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting StreamGank API server on port {port}")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload for production
        log_level="info"
    )
