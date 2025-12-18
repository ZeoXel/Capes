"""
Files Routes - File upload, download, and management.

Provides:
- POST /api/files/upload - Upload file(s)
- GET /api/files/{file_id} - Download file
- GET /api/files/{file_id}/metadata - Get file metadata
- DELETE /api/files/{file_id} - Delete file
- GET /api/files/session/{session_id} - List session files
- DELETE /api/files/session/{session_id} - Delete session files
- POST /api/files/{file_id}/process - Process file with Cape
- GET /api/files/stats - Get storage statistics
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from api.deps import get_registry, get_runtime
from api.storage import (
    FileStorage,
    FileMetadata,
    FileStatus,
    get_storage,
    FileNotFoundError as StorageFileNotFoundError,
    FileTooLargeError,
    InvalidFileTypeError,
)


# ============================================================
# Schemas
# ============================================================

class FileResponse(BaseModel):
    """File metadata response."""
    file_id: str
    original_name: str
    content_type: str
    size_bytes: int
    status: str
    session_id: Optional[str] = None
    created_at: str
    expires_at: str
    cape_id: Optional[str] = None
    is_output: bool = False
    download_url: str

    @classmethod
    def from_metadata(cls, metadata: FileMetadata) -> "FileResponse":
        """Create from FileMetadata."""
        return cls(
            file_id=metadata.file_id,
            original_name=metadata.original_name,
            content_type=metadata.content_type,
            size_bytes=metadata.size_bytes,
            status=metadata.status.value,
            session_id=metadata.session_id,
            created_at=metadata.created_at.isoformat(),
            expires_at=metadata.expires_at.isoformat(),
            cape_id=metadata.cape_id,
            is_output=metadata.is_output,
            download_url=f"/api/files/{metadata.file_id}",
        )


class UploadResponse(BaseModel):
    """Upload response."""
    files: List[FileResponse]
    session_id: str
    total_size_bytes: int


class ProcessRequest(BaseModel):
    """Request to process file with Cape."""
    cape_id: str = Field(..., description="Cape ID to use for processing")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Additional inputs")
    output_format: Optional[str] = Field(default=None, description="Desired output format")


class ProcessResponse(BaseModel):
    """Response from file processing."""
    success: bool
    input_file: FileResponse
    output_files: List[FileResponse] = Field(default_factory=list)
    execution_time_ms: float = 0
    error: Optional[str] = None
    cape_id: str
    session_id: str


class SessionFilesResponse(BaseModel):
    """Session files response."""
    session_id: str
    files: List[FileResponse]
    total_files: int
    total_size_bytes: int


class StorageStatsResponse(BaseModel):
    """Storage statistics response."""
    total_files: int
    total_sessions: int
    total_size_mb: float
    by_status: Dict[str, int]
    by_type: Dict[str, int]


# ============================================================
# Router
# ============================================================

router = APIRouter(prefix="/api/files", tags=["files"])


# Static routes first (before dynamic {file_id} routes)
@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats():
    """Get storage statistics."""
    storage = get_storage()
    stats = await storage.get_stats()

    return StorageStatsResponse(
        total_files=stats["total_files"],
        total_sessions=stats["total_sessions"],
        total_size_mb=stats["total_size_mb"],
        by_status=stats["by_status"],
        by_type=stats["by_type"],
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(..., description="Files to upload"),
    session_id: Optional[str] = Form(None, description="Session ID (generated if not provided)"),
    cape_id: Optional[str] = Form(None, description="Cape ID for processing"),
):
    """
    Upload one or more files.

    Files are stored temporarily and associated with a session.
    They can then be processed with a Cape.

    Supported file types:
    - Documents: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
    - Text: TXT, MD, CSV, JSON, XML, YAML
    - Images: PNG, JPG, GIF, WebP, SVG
    - Archives: ZIP, TAR, GZ

    Max file size: 50MB per file
    """
    storage = get_storage()

    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    uploaded_files = []
    total_size = 0

    for file in files:
        try:
            content = await file.read()

            metadata = await storage.upload(
                content=content,
                filename=file.filename or "unnamed",
                session_id=session_id,
                cape_id=cape_id,
                content_type=file.content_type,
            )

            uploaded_files.append(FileResponse.from_metadata(metadata))
            total_size += metadata.size_bytes

        except FileTooLargeError as e:
            raise HTTPException(status_code=413, detail=str(e))
        except InvalidFileTypeError as e:
            raise HTTPException(status_code=415, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    return UploadResponse(
        files=uploaded_files,
        session_id=session_id,
        total_size_bytes=total_size,
    )


@router.get("/{file_id}")
async def download_file(
    file_id: str,
    inline: bool = Query(False, description="Display inline instead of download"),
):
    """
    Download a file by ID.

    Returns the file content with appropriate headers.
    Use `inline=true` to display in browser instead of downloading.
    """
    storage = get_storage()

    try:
        content, metadata = await storage.download(file_id)
    except StorageFileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    # Set content disposition
    if inline:
        disposition = f'inline; filename="{metadata.original_name}"'
    else:
        disposition = f'attachment; filename="{metadata.original_name}"'

    return Response(
        content=content,
        media_type=metadata.content_type,
        headers={
            "Content-Disposition": disposition,
            "Content-Length": str(metadata.size_bytes),
            "X-File-Id": metadata.file_id,
            "X-File-Checksum": metadata.checksum,
        },
    )


@router.get("/{file_id}/metadata", response_model=FileResponse)
async def get_file_metadata(file_id: str):
    """Get file metadata without downloading content."""
    storage = get_storage()

    metadata = await storage.get_metadata(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    return FileResponse.from_metadata(metadata)


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete a file."""
    storage = get_storage()

    success = await storage.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    return {"success": True, "file_id": file_id}


@router.get("/session/{session_id}", response_model=SessionFilesResponse)
async def list_session_files(
    session_id: str,
    include_outputs: bool = Query(True, description="Include output files"),
):
    """List all files in a session."""
    storage = get_storage()

    files = await storage.list_session_files(session_id, include_outputs)

    total_size = sum(f.size_bytes for f in files)

    return SessionFilesResponse(
        session_id=session_id,
        files=[FileResponse.from_metadata(f) for f in files],
        total_files=len(files),
        total_size_bytes=total_size,
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete all files in a session."""
    storage = get_storage()

    deleted = await storage.delete_session(session_id)

    return {
        "success": True,
        "session_id": session_id,
        "deleted_files": deleted,
    }


@router.post("/{file_id}/process", response_model=ProcessResponse)
async def process_file(file_id: str, request: ProcessRequest):
    """
    Process a file with a Cape.

    This uploads the file to the Cape's execution environment,
    runs the Cape, and returns any output files.

    Example use cases:
    - Process Excel file with xlsx cape
    - Convert document with docx cape
    - Extract text from PDF with pdf cape
    """
    storage = get_storage()
    registry = get_registry()
    runtime = get_runtime()

    # Get file metadata
    metadata = await storage.get_metadata(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")

    # Verify cape exists
    cape = registry.get(request.cape_id)
    if not cape:
        raise HTTPException(status_code=404, detail=f"Cape not found: {request.cape_id}")

    # Download file content
    try:
        content, _ = await storage.download(file_id)
    except StorageFileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File content not found: {file_id}")

    # Update file status
    await storage.update_status(file_id, FileStatus.PROCESSING, request.cape_id)

    # Prepare inputs for cape execution
    inputs = dict(request.inputs)
    inputs["_files"] = {metadata.original_name: content}

    if request.output_format:
        inputs["output_format"] = request.output_format

    # Execute cape
    try:
        result = await runtime.execute(request.cape_id, inputs)

        # Save output files
        output_files = []
        session_id = metadata.session_id or str(uuid.uuid4())

        if result.success and hasattr(result, "metadata") and result.metadata:
            files_created = result.metadata.get("files_created", {})

            if isinstance(files_created, dict):
                for filename, file_content in files_created.items():
                    if isinstance(file_content, bytes):
                        output_metadata = await storage.save_output(
                            content=file_content,
                            filename=filename,
                            session_id=session_id,
                            source_file_id=file_id,
                            cape_id=request.cape_id,
                        )
                        output_files.append(FileResponse.from_metadata(output_metadata))

        # Update input file status
        await storage.update_status(
            file_id,
            FileStatus.COMPLETED if result.success else FileStatus.UPLOADED,
        )

        return ProcessResponse(
            success=result.success,
            input_file=FileResponse.from_metadata(metadata),
            output_files=output_files,
            execution_time_ms=result.execution_time_ms or 0,
            error=result.error,
            cape_id=request.cape_id,
            session_id=session_id,
        )

    except Exception as e:
        await storage.update_status(file_id, FileStatus.UPLOADED)
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")


# ============================================================
# Batch Operations
# ============================================================

class BatchProcessRequest(BaseModel):
    """Batch process request."""
    file_ids: List[str] = Field(..., description="File IDs to process")
    cape_id: str = Field(..., description="Cape ID")
    inputs: Dict[str, Any] = Field(default_factory=dict)


class BatchProcessResponse(BaseModel):
    """Batch process response."""
    results: List[ProcessResponse]
    total_processed: int
    successful: int
    failed: int


@router.post("/batch/process", response_model=BatchProcessResponse)
async def batch_process_files(request: BatchProcessRequest):
    """Process multiple files with a Cape."""
    results = []
    successful = 0
    failed = 0

    for file_id in request.file_ids:
        try:
            process_request = ProcessRequest(
                cape_id=request.cape_id,
                inputs=request.inputs,
            )
            result = await process_file(file_id, process_request)
            results.append(result)

            if result.success:
                successful += 1
            else:
                failed += 1

        except HTTPException as e:
            failed += 1
            results.append(ProcessResponse(
                success=False,
                input_file=FileResponse(
                    file_id=file_id,
                    original_name="unknown",
                    content_type="unknown",
                    size_bytes=0,
                    status="error",
                    created_at="",
                    expires_at="",
                    is_output=False,
                    download_url="",
                ),
                error=e.detail,
                cape_id=request.cape_id,
                session_id="",
            ))

    return BatchProcessResponse(
        results=results,
        total_processed=len(request.file_ids),
        successful=successful,
        failed=failed,
    )
