"""
Pydantic models for translation requests and responses.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class UploadRequest(BaseModel):
    """Model for file upload request parameters."""
    target_language: str = Field(..., description="Target language for translation (ISO 639-3 code)")
    source_language: Optional[str] = Field(None, description="Source language (auto-detect if not provided)")
    
    # Engine configuration
    stt_engine: str = Field("auto", description="Speech-to-text engine (auto, faster-whisper, transformers)")
    stt_model: str = Field("medium", description="Whisper model size (medium, large-v2, large-v3)")
    translation_engine: str = Field("nllb", description="Translation engine (nllb)")
    translation_model: str = Field("nllb-200-1.3B", description="NLLB model size (nllb-200-1.3B)")
    tts_engine: str = Field("mms", description="Text-to-speech engine (mms, openai, api)")


class UploadResponse(BaseModel):
    """Response model for successful file upload."""
    job_id: str = Field(..., description="Unique job identifier for tracking")
    status: str = Field("uploaded", description="Initial job status")
    original_filename: str = Field(..., description="Original filename of uploaded file")
    file_size: int = Field(..., description="File size in bytes")
    
    # URLs for tracking and management
    status_url: str = Field(..., description="URL to check job status")
    download_url: Optional[str] = Field(None, description="Download URL (available when completed)")
    websocket_url: str = Field(..., description="WebSocket URL for real-time progress")
    
    # Processing configuration
    processing_config: Dict[str, Any] = Field(..., description="Configuration used for processing")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")


class TranslationRequest(BaseModel):
    """Model for translation request (used internally by services)."""
    source_language: Optional[str] = None
    target_language: str
    input_file_path: str
    output_file_path: str
    
    # Engine configuration
    stt_engine: str = "auto"
    stt_model: str = "medium"
    translation_engine: str = "nllb"
    translation_model: str = "nllb-200-1.3B"
    tts_engine: str = "mms"
    
    # Processing options
    device: Optional[str] = None
    cpu_threads: Optional[int] = None
    
    class Config:
        from_attributes = True


class TranslationResult(BaseModel):
    """Model for translation result (used internally by services)."""
    success: bool
    output_file_path: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    
    # Detected/processed information
    detected_language: Optional[str] = None
    output_file_size: Optional[int] = None
    
    # Processing metadata
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response model for listing jobs."""
    jobs: List[Dict[str, Any]] = Field(..., description="List of jobs")
    total_count: int = Field(..., description="Total number of jobs")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Number of jobs per page")
    
    
class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking") 