"""
Tests for File API endpoints.

Uses pytest and httpx for testing FastAPI endpoints.
"""

import asyncio
import io
import pytest
import tempfile
from pathlib import Path

# Check if httpx is available
try:
    from httpx import AsyncClient, ASGITransport
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not HTTPX_AVAILABLE,
    reason="httpx not installed"
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
async def test_app(temp_storage_dir):
    """Create test FastAPI app with temporary storage."""
    import os

    # Set environment variables before importing
    os.environ["CAPE_STORAGE_DIR"] = str(temp_storage_dir)

    from api.main import app
    from api.storage import init_storage, StorageConfig, get_storage

    # Initialize storage with temp directory
    config = StorageConfig(base_dir=temp_storage_dir)
    await init_storage(config)

    yield app

    # Cleanup
    storage = get_storage()
    await storage.shutdown()


@pytest.fixture
async def client(test_app):
    """Create async test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================
# Upload Tests
# ============================================================

class TestFileUpload:
    """Tests for file upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_single_file(self, client):
        """Test uploading a single file."""
        files = {"files": ("test.txt", b"Hello World", "text/plain")}

        response = await client.post("/api/files/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"]
        assert len(data["files"]) == 1
        assert data["files"][0]["original_name"] == "test.txt"

    @pytest.mark.asyncio
    async def test_upload_multiple_files(self, client):
        """Test uploading multiple files."""
        files = [
            ("files", ("file1.txt", b"Content 1", "text/plain")),
            ("files", ("file2.txt", b"Content 2", "text/plain")),
        ]

        response = await client.post("/api/files/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) == 2

    @pytest.mark.asyncio
    async def test_upload_with_session_id(self, client):
        """Test uploading with custom session ID."""
        files = {"files": ("test.txt", b"Hello", "text/plain")}
        data = {"session_id": "custom-session-123"}

        response = await client.post("/api/files/upload", files=files, data=data)

        assert response.status_code == 200
        assert response.json()["session_id"] == "custom-session-123"

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client):
        """Test uploading invalid file type."""
        files = {"files": ("malware.exe", b"evil content", "application/octet-stream")}

        response = await client.post("/api/files/upload", files=files)

        assert response.status_code == 415  # Unsupported Media Type


# ============================================================
# Download Tests
# ============================================================

class TestFileDownload:
    """Tests for file download endpoint."""

    @pytest.mark.asyncio
    async def test_download_file(self, client):
        """Test downloading an uploaded file."""
        # Upload first
        content = b"Test content for download"
        files = {"files": ("download.txt", content, "text/plain")}
        upload_response = await client.post("/api/files/upload", files=files)
        file_id = upload_response.json()["files"][0]["file_id"]

        # Download
        response = await client.get(f"/api/files/{file_id}")

        assert response.status_code == 200
        assert response.content == content
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_download_inline(self, client):
        """Test downloading file inline."""
        files = {"files": ("inline.txt", b"Inline content", "text/plain")}
        upload_response = await client.post("/api/files/upload", files=files)
        file_id = upload_response.json()["files"][0]["file_id"]

        response = await client.get(f"/api/files/{file_id}?inline=true")

        assert response.status_code == 200
        assert "inline" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_download_not_found(self, client):
        """Test downloading non-existent file."""
        response = await client.get("/api/files/non-existent-id")

        assert response.status_code == 404


# ============================================================
# Metadata Tests
# ============================================================

class TestFileMetadata:
    """Tests for file metadata endpoint."""

    @pytest.mark.asyncio
    async def test_get_metadata(self, client):
        """Test getting file metadata."""
        files = {"files": ("meta.txt", b"Metadata test", "text/plain")}
        upload_response = await client.post("/api/files/upload", files=files)
        file_id = upload_response.json()["files"][0]["file_id"]

        response = await client.get(f"/api/files/{file_id}/metadata")

        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == file_id
        assert data["original_name"] == "meta.txt"
        assert data["status"] == "uploaded"


# ============================================================
# Delete Tests
# ============================================================

class TestFileDelete:
    """Tests for file deletion endpoints."""

    @pytest.mark.asyncio
    async def test_delete_file(self, client):
        """Test deleting a file."""
        files = {"files": ("delete.txt", b"Delete me", "text/plain")}
        upload_response = await client.post("/api/files/upload", files=files)
        file_id = upload_response.json()["files"][0]["file_id"]

        # Delete
        response = await client.delete(f"/api/files/{file_id}")
        assert response.status_code == 200

        # Verify deleted
        response = await client.get(f"/api/files/{file_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session(self, client):
        """Test deleting all files in a session."""
        session_id = "session-to-delete"

        # Upload multiple files
        for i in range(3):
            files = {"files": (f"file{i}.txt", f"Content {i}".encode(), "text/plain")}
            await client.post("/api/files/upload", files=files, data={"session_id": session_id})

        # Delete session
        response = await client.delete(f"/api/files/session/{session_id}")
        assert response.status_code == 200
        assert response.json()["deleted_files"] == 3

        # Verify empty
        response = await client.get(f"/api/files/session/{session_id}")
        assert response.json()["total_files"] == 0


# ============================================================
# Session Tests
# ============================================================

class TestSessionFiles:
    """Tests for session file listing."""

    @pytest.mark.asyncio
    async def test_list_session_files(self, client):
        """Test listing files in a session."""
        session_id = "list-session"

        # Upload files
        for name in ["a.txt", "b.txt", "c.txt"]:
            files = {"files": (name, f"Content of {name}".encode(), "text/plain")}
            await client.post("/api/files/upload", files=files, data={"session_id": session_id})

        # List
        response = await client.get(f"/api/files/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["total_files"] == 3


# ============================================================
# Stats Tests
# ============================================================

class TestStorageStats:
    """Tests for storage statistics."""

    @pytest.mark.asyncio
    async def test_get_stats(self, client):
        """Test getting storage statistics."""
        # Upload some files first
        for i in range(2):
            files = {"files": (f"stat{i}.txt", b"Stats test", "text/plain")}
            await client.post("/api/files/upload", files=files)

        response = await client.get("/api/files/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] >= 2
        assert "by_status" in data
        assert "by_type" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
