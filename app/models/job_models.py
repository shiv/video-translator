"""
Pydantic models for job management and tracking.
"""

from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class JobStatus(BaseModel):
    """Enumeration of possible job statuses."""
    UPLOADED: Literal["uploaded"] = "uploaded"
    PROCESSING: Literal["processing"] = "processing" 
    COMPLETED: Literal["completed"] = "completed"
    FAILED: Literal["failed"] = "failed"
    CANCELLED: Literal["cancelled"] = "cancelled"


class JobMetadata(BaseModel):
    """Metadata associated with a job."""
    file_format: Optional[str] = None
    duration_seconds: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None
    
    # Translation parameters
    stt_engine: Optional[str] = None
    stt_model: Optional[str] = None
    translation_engine: Optional[str] = None
    translation_model: Optional[str] = None
    tts_engine: Optional[str] = None
    
    # Processing metadata
    progress_stage: Optional[str] = None
    progress_percentage: Optional[float] = None


class JobCreate(BaseModel):
    """Model for creating a new job."""
    original_filename: str = Field(..., description="Original filename of uploaded video")
    source_language: Optional[str] = Field(None, description="Source language code (auto-detected if not provided)")
    target_language: str = Field(..., description="Target language code for translation")
    input_file_path: str = Field(..., description="Path to uploaded input file")
    input_file_size: int = Field(..., description="Size of input file in bytes")
    
    # Translation parameters
    stt_engine: str = Field("auto", description="Speech-to-text engine")
    stt_model: str = Field("medium", description="STT model name")
    translation_engine: str = Field("nllb", description="Translation engine")
    translation_model: str = Field("nllb-200-1.3B", description="Translation model name")
    tts_engine: str = Field("mms", description="Text-to-speech engine")
    
    # Optional metadata
    job_metadata: Optional[JobMetadata] = None


class JobUpdate(BaseModel):
    """Model for updating job fields."""
    status: Optional[str] = None
    source_language: Optional[str] = None
    output_file_path: Optional[str] = None
    output_file_size: Optional[int] = None
    processing_time_seconds: Optional[int] = None
    error_message: Optional[str] = None
    job_metadata: Optional[JobMetadata] = None
    completed_at: Optional[datetime] = None


class Job(BaseModel):
    """Complete job model with all fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique job identifier")
    original_filename: str = Field(..., description="Original filename of uploaded video")
    source_language: Optional[str] = Field(None, description="Source language code")
    target_language: str = Field(..., description="Target language code for translation")
    status: str = Field("uploaded", description="Current job status")
    
    # File paths and sizes
    input_file_path: str = Field(..., description="Path to input file")
    output_file_path: Optional[str] = Field(None, description="Path to output file")
    input_file_size: int = Field(..., description="Size of input file in bytes")
    output_file_size: Optional[int] = Field(None, description="Size of output file in bytes")
    
    # Processing information
    processing_time_seconds: Optional[int] = Field(None, description="Total processing time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    
    # Translation parameters
    stt_engine: str = Field("auto", description="Speech-to-text engine")
    stt_model: str = Field("medium", description="STT model name")
    translation_engine: str = Field("nllb", description="Translation engine")
    translation_model: str = Field("nllb-200-1.3B", description="Translation model name")
    tts_engine: str = Field("mms", description="Text-to-speech engine")
    
    # Metadata and timestamps
    job_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional job metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    
    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    """API response model for job information."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    original_filename: str = Field(..., description="Original filename")
    source_language: Optional[str] = Field(None, description="Source language")
    target_language: str = Field(..., description="Target language")
    
    # Progress information
    progress_stage: Optional[str] = Field(None, description="Current processing stage")
    progress_percentage: Optional[float] = Field(None, description="Progress percentage (0-100)")
    
    # File information
    input_file_size: int = Field(..., description="Input file size in bytes")
    output_file_size: Optional[int] = Field(None, description="Output file size in bytes")
    
    # Processing information
    processing_time_seconds: Optional[int] = Field(None, description="Processing time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Download URLs (populated by API)
    download_url: Optional[str] = Field(None, description="Download URL for completed job")
    preview_url: Optional[str] = Field(None, description="Preview URL for job")


class ProgressUpdate(BaseModel):
    """Model for real-time progress updates via WebSocket."""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current status")
    stage: str = Field(..., description="Current processing stage")
    percentage: float = Field(0.0, description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Progress message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    
    # Optional detailed information
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    error_details: Optional[str] = Field(None, description="Error details if applicable") 