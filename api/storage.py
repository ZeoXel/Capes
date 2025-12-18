"""
File Storage Manager - Handles file upload, download, and lifecycle.

Provides:
- Temporary file storage for Cape execution
- Session-based file management
- Automatic cleanup of expired files
- Support for multiple storage backends (local, future: S3)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class StorageBackend(str, Enum):
    """Storage backend type."""
    LOCAL = "local"
    # Future: S3 = "s3"


class FileStatus(str, Enum):
    """File lifecycle status."""
    UPLOADED = "uploaded"      # Just uploaded, not processed
    PROCESSING = "processing"  # Being processed by Cape
    COMPLETED = "completed"    # Processing complete, output available
    EXPIRED = "expired"        # Past retention period
    DELETED = "deleted"        # Manually deleted


@dataclass
class FileMetadata:
    """Metadata for stored files."""
    file_id: str
    original_name: str
    stored_name: str
    content_type: str
    size_bytes: int
    checksum: str  # MD5
    status: FileStatus
    session_id: Optional[str]
    created_at: datetime
    expires_at: datetime
    cape_id: Optional[str] = None
    is_output: bool = False  # True if this is an output file from Cape execution
    source_file_id: Optional[str] = None  # For output files, the input file ID
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_id": self.file_id,
            "original_name": self.original_name,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "status": self.status.value,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "cape_id": self.cape_id,
            "is_output": self.is_output,
            "source_file_id": self.source_file_id,
        }


@dataclass
class StorageConfig:
    """Storage configuration."""
    backend: StorageBackend = StorageBackend.LOCAL
    base_dir: Optional[Path] = None
    max_file_size_mb: int = 50
    retention_hours: int = 24
    allowed_extensions: List[str] = field(default_factory=lambda: [
        # Documents
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".odt", ".ods", ".odp",
        # Text
        ".txt", ".md", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml",
        # Images
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg",
        # Archives
        ".zip", ".tar", ".gz",
    ])
    cleanup_interval_minutes: int = 30


class FileStorageError(Exception):
    """File storage error."""
    pass


class FileNotFoundError(FileStorageError):
    """File not found error."""
    pass


class FileTooLargeError(FileStorageError):
    """File too large error."""
    pass


class InvalidFileTypeError(FileStorageError):
    """Invalid file type error."""
    pass


class FileStorage:
    """
    File storage manager.

    Handles file upload, download, and lifecycle management.
    Supports session-based file organization and automatic cleanup.

    Usage:
        storage = FileStorage(config)
        await storage.initialize()

        # Upload file
        metadata = await storage.upload(
            file_content,
            filename="data.xlsx",
            session_id="session-123",
        )

        # Download file
        content, metadata = await storage.download(file_id)

        # List session files
        files = await storage.list_session_files(session_id)

        # Cleanup
        await storage.cleanup_expired()
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """
        Initialize storage manager.

        Args:
            config: Storage configuration
        """
        self.config = config or StorageConfig()

        # Set default base directory
        if self.config.base_dir is None:
            self.config.base_dir = Path.cwd() / ".cape_storage"

        # In-memory metadata index
        self._files: Dict[str, FileMetadata] = {}
        self._session_files: Dict[str, List[str]] = {}  # session_id -> file_ids

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize storage (create directories, start cleanup task)."""
        if self._initialized:
            return

        # Create storage directories
        self.config.base_dir.mkdir(parents=True, exist_ok=True)
        (self.config.base_dir / "uploads").mkdir(exist_ok=True)
        (self.config.base_dir / "outputs").mkdir(exist_ok=True)
        (self.config.base_dir / "temp").mkdir(exist_ok=True)

        # Load existing file metadata
        await self._load_metadata()

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        self._initialized = True
        logger.info(f"FileStorage initialized at {self.config.base_dir}")

    async def shutdown(self) -> None:
        """Shutdown storage (stop cleanup task)."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        self._initialized = False

    async def upload(
        self,
        content: Union[bytes, BinaryIO],
        filename: str,
        session_id: Optional[str] = None,
        cape_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> FileMetadata:
        """
        Upload a file.

        Args:
            content: File content (bytes or file-like object)
            filename: Original filename
            session_id: Session ID for grouping files
            cape_id: Cape ID that will process this file
            content_type: MIME type (auto-detected if not provided)

        Returns:
            FileMetadata for uploaded file

        Raises:
            FileTooLargeError: If file exceeds size limit
            InvalidFileTypeError: If file type not allowed
        """
        # Validate extension
        ext = Path(filename).suffix.lower()
        if ext not in self.config.allowed_extensions:
            raise InvalidFileTypeError(
                f"File type '{ext}' not allowed. "
                f"Allowed types: {', '.join(self.config.allowed_extensions)}"
            )

        # Read content
        if hasattr(content, "read"):
            data = content.read()
        else:
            data = content

        # Validate size
        size_mb = len(data) / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            raise FileTooLargeError(
                f"File size ({size_mb:.1f}MB) exceeds limit "
                f"({self.config.max_file_size_mb}MB)"
            )

        # Generate file ID and stored name
        file_id = str(uuid.uuid4())
        checksum = hashlib.md5(data).hexdigest()
        stored_name = f"{file_id}{ext}"

        # Detect content type
        if not content_type:
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # Determine storage path
        storage_dir = self.config.base_dir / "uploads"
        if session_id:
            storage_dir = storage_dir / session_id
            storage_dir.mkdir(parents=True, exist_ok=True)

        file_path = storage_dir / stored_name

        # Write file
        file_path.write_bytes(data)

        # Create metadata
        now = datetime.utcnow()
        metadata = FileMetadata(
            file_id=file_id,
            original_name=filename,
            stored_name=stored_name,
            content_type=content_type,
            size_bytes=len(data),
            checksum=checksum,
            status=FileStatus.UPLOADED,
            session_id=session_id,
            created_at=now,
            expires_at=now + timedelta(hours=self.config.retention_hours),
            cape_id=cape_id,
        )

        # Index metadata
        self._files[file_id] = metadata
        if session_id:
            if session_id not in self._session_files:
                self._session_files[session_id] = []
            self._session_files[session_id].append(file_id)

        # Persist metadata
        await self._save_metadata(metadata)

        logger.info(f"Uploaded file: {filename} -> {file_id} ({size_mb:.2f}MB)")

        return metadata

    async def download(self, file_id: str) -> Tuple[bytes, FileMetadata]:
        """
        Download a file.

        Args:
            file_id: File ID

        Returns:
            Tuple of (file content, metadata)

        Raises:
            FileNotFoundError: If file not found
        """
        metadata = self._files.get(file_id)
        if not metadata:
            raise FileNotFoundError(f"File not found: {file_id}")

        # Determine file path
        if metadata.is_output:
            base_dir = self.config.base_dir / "outputs"
        else:
            base_dir = self.config.base_dir / "uploads"

        if metadata.session_id:
            file_path = base_dir / metadata.session_id / metadata.stored_name
        else:
            file_path = base_dir / metadata.stored_name

        if not file_path.exists():
            raise FileNotFoundError(f"File not found on disk: {file_id}")

        content = file_path.read_bytes()

        return content, metadata

    async def get_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata."""
        return self._files.get(file_id)

    async def update_status(
        self,
        file_id: str,
        status: FileStatus,
        cape_id: Optional[str] = None,
    ) -> Optional[FileMetadata]:
        """Update file status."""
        metadata = self._files.get(file_id)
        if not metadata:
            return None

        metadata.status = status
        if cape_id:
            metadata.cape_id = cape_id

        await self._save_metadata(metadata)

        return metadata

    async def save_output(
        self,
        content: bytes,
        filename: str,
        session_id: str,
        source_file_id: Optional[str] = None,
        cape_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> FileMetadata:
        """
        Save output file from Cape execution.

        Args:
            content: File content
            filename: Output filename
            session_id: Session ID
            source_file_id: Original input file ID
            cape_id: Cape that generated this output
            content_type: MIME type

        Returns:
            FileMetadata for output file
        """
        # Generate file ID
        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix.lower()
        stored_name = f"{file_id}{ext}"
        checksum = hashlib.md5(content).hexdigest()

        # Detect content type
        if not content_type:
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # Storage path
        storage_dir = self.config.base_dir / "outputs" / session_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = storage_dir / stored_name

        # Write file
        file_path.write_bytes(content)

        # Create metadata
        now = datetime.utcnow()
        metadata = FileMetadata(
            file_id=file_id,
            original_name=filename,
            stored_name=stored_name,
            content_type=content_type,
            size_bytes=len(content),
            checksum=checksum,
            status=FileStatus.COMPLETED,
            session_id=session_id,
            created_at=now,
            expires_at=now + timedelta(hours=self.config.retention_hours),
            cape_id=cape_id,
            is_output=True,
            source_file_id=source_file_id,
        )

        # Index
        self._files[file_id] = metadata
        if session_id not in self._session_files:
            self._session_files[session_id] = []
        self._session_files[session_id].append(file_id)

        await self._save_metadata(metadata)

        logger.info(f"Saved output: {filename} -> {file_id}")

        return metadata

    async def list_session_files(
        self,
        session_id: str,
        include_outputs: bool = True,
    ) -> List[FileMetadata]:
        """List all files in a session."""
        file_ids = self._session_files.get(session_id, [])
        files = []

        for file_id in file_ids:
            metadata = self._files.get(file_id)
            if metadata:
                if not include_outputs and metadata.is_output:
                    continue
                files.append(metadata)

        return sorted(files, key=lambda f: f.created_at)

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file."""
        metadata = self._files.get(file_id)
        if not metadata:
            return False

        # Determine file path
        if metadata.is_output:
            base_dir = self.config.base_dir / "outputs"
        else:
            base_dir = self.config.base_dir / "uploads"

        if metadata.session_id:
            file_path = base_dir / metadata.session_id / metadata.stored_name
        else:
            file_path = base_dir / metadata.stored_name

        # Delete file
        if file_path.exists():
            file_path.unlink()

        # Update metadata
        metadata.status = FileStatus.DELETED
        await self._save_metadata(metadata)

        # Remove from index
        del self._files[file_id]
        if metadata.session_id and metadata.session_id in self._session_files:
            try:
                self._session_files[metadata.session_id].remove(file_id)
            except ValueError:
                pass

        logger.info(f"Deleted file: {file_id}")

        return True

    async def delete_session(self, session_id: str) -> int:
        """Delete all files in a session."""
        file_ids = self._session_files.get(session_id, []).copy()
        deleted = 0

        for file_id in file_ids:
            if await self.delete_file(file_id):
                deleted += 1

        # Remove session directory
        for subdir in ["uploads", "outputs"]:
            session_dir = self.config.base_dir / subdir / session_id
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)

        if session_id in self._session_files:
            del self._session_files[session_id]

        logger.info(f"Deleted session {session_id}: {deleted} files")

        return deleted

    async def cleanup_expired(self) -> int:
        """Clean up expired files."""
        now = datetime.utcnow()
        expired = []

        for file_id, metadata in self._files.items():
            if metadata.expires_at < now and metadata.status != FileStatus.DELETED:
                expired.append(file_id)

        deleted = 0
        for file_id in expired:
            if await self.delete_file(file_id):
                deleted += 1

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired files")

        return deleted

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_size = 0
        by_status = {}
        by_type = {}

        for metadata in self._files.values():
            total_size += metadata.size_bytes

            status = metadata.status.value
            by_status[status] = by_status.get(status, 0) + 1

            ext = Path(metadata.original_name).suffix.lower()
            by_type[ext] = by_type.get(ext, 0) + 1

        return {
            "total_files": len(self._files),
            "total_sessions": len(self._session_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_status": by_status,
            "by_type": by_type,
            "storage_path": str(self.config.base_dir),
        }

    # ========================================
    # Internal methods
    # ========================================

    async def _load_metadata(self) -> None:
        """Load metadata from disk."""
        metadata_dir = self.config.base_dir / ".metadata"
        if not metadata_dir.exists():
            return

        import json

        for meta_file in metadata_dir.glob("*.json"):
            try:
                data = json.loads(meta_file.read_text())
                metadata = FileMetadata(
                    file_id=data["file_id"],
                    original_name=data["original_name"],
                    stored_name=data["stored_name"],
                    content_type=data["content_type"],
                    size_bytes=data["size_bytes"],
                    checksum=data["checksum"],
                    status=FileStatus(data["status"]),
                    session_id=data.get("session_id"),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    expires_at=datetime.fromisoformat(data["expires_at"]),
                    cape_id=data.get("cape_id"),
                    is_output=data.get("is_output", False),
                    source_file_id=data.get("source_file_id"),
                )

                # Only load non-deleted files
                if metadata.status != FileStatus.DELETED:
                    self._files[metadata.file_id] = metadata

                    if metadata.session_id:
                        if metadata.session_id not in self._session_files:
                            self._session_files[metadata.session_id] = []
                        self._session_files[metadata.session_id].append(metadata.file_id)

            except Exception as e:
                logger.warning(f"Failed to load metadata {meta_file}: {e}")

        logger.info(f"Loaded {len(self._files)} file metadata")

    async def _save_metadata(self, metadata: FileMetadata) -> None:
        """Save metadata to disk."""
        import json

        metadata_dir = self.config.base_dir / ".metadata"
        metadata_dir.mkdir(exist_ok=True)

        meta_file = metadata_dir / f"{metadata.file_id}.json"
        meta_file.write_text(json.dumps(metadata.to_dict(), indent=2))

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval_minutes * 60)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")


# Global storage instance
_storage: Optional[FileStorage] = None


def get_storage() -> FileStorage:
    """Get or create file storage instance."""
    global _storage
    if _storage is None:
        _storage = FileStorage()
    return _storage


async def init_storage(config: Optional[StorageConfig] = None) -> FileStorage:
    """Initialize file storage."""
    global _storage
    _storage = FileStorage(config)
    await _storage.initialize()
    return _storage
