"""
Pydantic models for the AI Video Translation Service.
Contains data models for jobs, requests, and responses.
"""

from .job_models import (
    Job,
    JobCreate,
    JobStatus,
    JobResponse,
    JobUpdate,
    ProgressUpdate,
    JobMetadata
)

from .translation_models import (
    TranslationRequest,
    TranslationResult,
    UploadRequest,
    UploadResponse
)

__all__ = [
    # Job models
    "Job",
    "JobCreate", 
    "JobStatus",
    "JobResponse",
    "JobUpdate",
    "ProgressUpdate",
    "JobMetadata",
    
    # Translation models
    "TranslationRequest",
    "TranslationResult", 
    "UploadRequest",
    "UploadResponse"
] 