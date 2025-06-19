"""
Job management API routes for the AI Video Translation Service.
Handles upload, status tracking, download, and job CRUD operations.
"""

import os
import aiofiles
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime

from app.models.job_models import Job, JobCreate, JobUpdate, JobResponse, JobMetadata
from app.models.translation_models import UploadRequest, UploadResponse, JobListResponse
from app.services.database_service import get_database_service
from app.services.job_queue_service import get_job_queue_service
from app.services.util import get_env_var

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["jobs"])

# File size limit (200MB)
MAX_FILE_SIZE = 200 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    request: Request,
    file: UploadFile = File(..., description="Video file to translate (MP4 format, max 200MB)"),
    target_language: str = Form(..., description="Target language for translation (ISO 639-3 code)"),
    source_language: Optional[str] = Form(None, description="Source language (auto-detect if not provided)"),
    stt_engine: str = Form("auto", description="Speech-to-text engine (auto, faster-whisper, transformers)"),
    stt_model: str = Form("medium", description="Whisper model size (medium, large-v2, large-v3)"),
    translation_engine: str = Form("nllb", description="Translation engine (nllb)"),
    translation_model: str = Form("nllb-200-1.3B", description="NLLB model size (nllb-200-1.3B, nllb-200-3.3B)"),
    tts_engine: str = Form("mms", description="Text-to-speech engine (mms, openai, api)")
):
    """
    Upload a video file for translation and create a processing job.
    
    This endpoint:
    1. Validates and saves the uploaded file
    2. Creates a job record in the database
    3. Submits the job for async processing
    4. Returns job information with tracking URLs
    """
    
    # Validate file size
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file.size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)"
        )
    
    # Validate file format
    if not file.filename or not file.filename.lower().endswith('.mp4'):
        raise HTTPException(
            status_code=400,
            detail="Only MP4 video files are supported"
        )
    
    try:
        # Create uploads directory if it doesn't exist
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(uploads_dir, safe_filename)
        
        # Save uploaded file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        file_size = len(content)
        
        # Validate file size after reading
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)  # Clean up
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)"
            )
        
        # Create job metadata
        job_metadata = JobMetadata(
            file_format="mp4",
            stt_engine=stt_engine,
            stt_model=stt_model,
            translation_engine=translation_engine,
            translation_model=translation_model,
            tts_engine=tts_engine,
            progress_stage="uploaded",
            progress_percentage=0.0
        )
        
        # Create job in database
        job_create = JobCreate(
            original_filename=file.filename,
            source_language=source_language,
            target_language=target_language,
            input_file_path=file_path,
            input_file_size=file_size,
            stt_engine=stt_engine,
            stt_model=stt_model,
            translation_engine=translation_engine,
            translation_model=translation_model,
            tts_engine=tts_engine,
            job_metadata=job_metadata
        )
        
        db_service = await get_database_service()
        job = await db_service.create_job(job_create)
        
        # Submit job for processing
        job_queue = get_job_queue_service()
        await job_queue.submit_job(job)
        
        # Build response URLs
        base_url = str(request.base_url).rstrip('/')
        status_url = f"{base_url}/api/v1/jobs/{job.id}/status"
        websocket_url = f"ws://{request.headers.get('host', 'localhost')}/api/v1/jobs/{job.id}/progress"
        
        # Create processing config
        processing_config = {
            "source_language": source_language,
            "target_language": target_language,
            "stt_engine": stt_engine,
            "stt_model": stt_model,
            "translation_engine": translation_engine,
            "translation_model": translation_model,
            "tts_engine": tts_engine
        }
        
        logger.info(f"Created and submitted job {job.id} for file {file.filename}")
        
        return UploadResponse(
            job_id=job.id,
            status="uploaded",
            original_filename=file.filename,
            file_size=file_size,
            status_url=status_url,
            websocket_url=websocket_url,
            processing_config=processing_config,
            created_at=job.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/jobs/{job_id}/status", response_model=JobResponse)
async def get_job_status(
    request: Request,
    job_id: str
):
    """
    Get the current status and information for a specific job.
    
    Returns detailed job information including progress, timestamps,
    and download URLs when available.
    """
    
    try:
        db_service = await get_database_service()
        job = await db_service.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Extract progress information from metadata
        progress_stage = None
        progress_percentage = None
        
        if job.job_metadata:
            progress_stage = job.job_metadata.get("progress_stage")
            progress_percentage = job.job_metadata.get("progress_percentage")
        
        # Build download and preview URLs
        base_url = str(request.base_url).rstrip('/')
        download_url = None
        preview_url = f"{base_url}/api/v1/jobs/{job_id}/preview"
        
        if job.status == "completed" and job.output_file_path:
            download_url = f"{base_url}/api/v1/jobs/{job_id}/download"
        
        return JobResponse(
            job_id=job.id,
            status=job.status,
            original_filename=job.original_filename,
            source_language=job.source_language,
            target_language=job.target_language,
            progress_stage=progress_stage,
            progress_percentage=progress_percentage,
            input_file_size=job.input_file_size,
            output_file_size=job.output_file_size,
            processing_time_seconds=job.processing_time_seconds,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            download_url=download_url,
            preview_url=preview_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/jobs/{job_id}/download")
async def download_translated_video(job_id: str):
    """
    Download the translated video file for a completed job.
    
    Returns the processed video file as a downloadable response.
    Only available for jobs with status 'completed'.
    """
    
    try:
        db_service = await get_database_service()
        job = await db_service.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        if job.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not completed (status: {job.status})"
            )
        
        if not job.output_file_path or not os.path.exists(job.output_file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Output file for job {job_id} not found"
            )
        
        # Generate download filename
        download_filename = f"translated_{job.original_filename}"
        
        logger.info(f"Serving download for job {job_id}: {job.output_file_path}")
        
        return FileResponse(
            path=job.output_file_path,
            filename=download_filename,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"attachment; filename={download_filename}",
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Download failed: {str(e)}"
        )


@router.get("/jobs/{job_id}/preview")
async def get_job_preview(job_id: str):
    """
    Get preview information for a job (Phase 4 feature placeholder).
    
    Currently returns basic metadata. In Phase 4, this will be enhanced
    with video thumbnails, clips, and detailed preview information.
    """
    
    try:
        db_service = await get_database_service()
        job = await db_service.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Basic preview information (Phase 3 implementation)
        preview_info = {
            "job_id": job.id,
            "status": job.status,
            "original_filename": job.original_filename,
            "file_size_mb": round(job.input_file_size / (1024 * 1024), 2),
            "source_language": job.source_language,
            "target_language": job.target_language,
            "created_at": job.created_at,
            "metadata": job.job_metadata,
            "preview_note": "Enhanced preview with thumbnails and clips available in Phase 4"
        }
        
        return JSONResponse(content=preview_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview failed for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Preview failed: {str(e)}"
        )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of jobs per page")
):
    """
    List jobs with optional filtering and pagination.
    
    Supports filtering by status and pagination for managing large numbers of jobs.
    """
    
    try:
        db_service = await get_database_service()
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get jobs and total count
        jobs = await db_service.list_jobs(status=status, limit=page_size, offset=offset)
        total_count = await db_service.count_jobs(status=status)
        
        # Convert jobs to dict format
        jobs_data = []
        for job in jobs:
            job_dict = {
                "job_id": job.id,
                "status": job.status,
                "original_filename": job.original_filename,
                "source_language": job.source_language,
                "target_language": job.target_language,
                "file_size": job.input_file_size,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "completed_at": job.completed_at,
                "processing_time_seconds": job.processing_time_seconds,
                "error_message": job.error_message
            }
            jobs_data.append(job_dict)
        
        logger.info(f"Listed {len(jobs)} jobs (page {page}, status filter: {status})")
        
        return JobListResponse(
            jobs=jobs_data,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a job and remove it from processing.
    
    Cancels active processing and marks the job as cancelled.
    Files are not automatically deleted.
    """
    
    try:
        db_service = await get_database_service()
        job = await db_service.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        if job.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} cannot be cancelled (status: {job.status})"
            )
        
        # Try to cancel from job queue
        job_queue = get_job_queue_service()
        cancelled = await job_queue.cancel_job(job_id)
        
        if not cancelled:
            # Job wasn't in active processing, update database directly
            await db_service.update_job(
                job_id,
                JobUpdate(status="cancelled", completed_at=datetime.utcnow())
            )
        
        logger.info(f"Cancelled job {job_id}")
        
        return {"message": f"Job {job_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str):
    """
    Get detailed information about a specific job.
    
    Returns comprehensive job information including all metadata,
    processing parameters, and file information.
    """
    
    try:
        db_service = await get_database_service()
        job = await db_service.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Return complete job information
        job_details = {
            "id": job.id,
            "original_filename": job.original_filename,
            "source_language": job.source_language,
            "target_language": job.target_language,
            "status": job.status,
            "input_file_path": job.input_file_path,
            "output_file_path": job.output_file_path,
            "input_file_size": job.input_file_size,
            "output_file_size": job.output_file_size,
            "processing_time_seconds": job.processing_time_seconds,
            "error_message": job.error_message,
            "stt_engine": job.stt_engine,
            "stt_model": job.stt_model,
            "translation_engine": job.translation_engine,
            "translation_model": job.translation_model,
            "tts_engine": job.tts_engine,
            "job_metadata": job.job_metadata,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "completed_at": job.completed_at
        }
        
        return JSONResponse(content=job_details)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job details {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job details: {str(e)}"
        )


@router.get("/queue/status")
async def get_queue_status():
    """
    Get current job queue status and statistics.
    
    Returns information about active jobs, queue size, and processing capacity.
    """
    
    try:
        job_queue = get_job_queue_service()
        queue_status = job_queue.get_queue_status()
        
        # Get database statistics
        db_service = await get_database_service()
        db_stats = {
            "total_jobs": await db_service.count_jobs(),
            "uploaded_jobs": await db_service.count_jobs("uploaded"),
            "processing_jobs": await db_service.count_jobs("processing"),
            "completed_jobs": await db_service.count_jobs("completed"),
            "failed_jobs": await db_service.count_jobs("failed"),
            "cancelled_jobs": await db_service.count_jobs("cancelled")
        }
        
        return {
            "queue": queue_status,
            "database": db_stats,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue status: {str(e)}"
        ) 