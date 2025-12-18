"""
Docker Sandbox - Container-based code execution environment.

Provides complete isolation through Docker containers:
- Filesystem isolation
- Network isolation (optional)
- Resource limits (CPU, memory)
- Process isolation

Recommended for production environments.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import shutil
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .manager import (
    BaseSandbox,
    SandboxConfig,
    ExecutionRequest,
    ExecutionResponse,
)

logger = logging.getLogger(__name__)


# Default base image name
DEFAULT_IMAGE_NAME = "cape-sandbox"
DEFAULT_IMAGE_TAG = "python3.11"

# Dockerfile for building the base image
DOCKERFILE_CONTENT = '''
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    libreoffice-calc \\
    poppler-utils \\
    pandoc \\
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --no-cache-dir \\
    openpyxl>=3.1.0 \\
    pandas>=2.0.0 \\
    numpy>=1.24.0 \\
    python-docx>=0.8.0 \\
    python-pptx>=0.6.0 \\
    pdfplumber>=0.9.0 \\
    reportlab>=4.0.0 \\
    PyPDF2>=3.0.0 \\
    pillow>=10.0.0 \\
    requests>=2.28.0 \\
    defusedxml>=0.7.0

# Create workspace directory
WORKDIR /workspace

# Default command (keep container running)
CMD ["tail", "-f", "/dev/null"]
'''

# Python wrapper script for execution
WRAPPER_SCRIPT = '''
import json
import sys
import traceback
from pathlib import Path

# Load arguments
args = {}
args_file = Path("_args.json")
if args_file.exists():
    args = json.loads(args_file.read_text())

# Execute user code
result = None
try:
{code}

    # Save result if defined
    if result is not None:
        Path("_result.json").write_text(json.dumps(result, default=str))

except Exception as e:
    error_info = {
        "error": str(e),
        "type": type(e).__name__,
        "traceback": traceback.format_exc(),
    }
    Path("_error.json").write_text(json.dumps(error_info))
    print(f"Error: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
'''


class DockerSandbox(BaseSandbox):
    """
    Docker container sandbox for isolated code execution.

    Provides strong isolation through Docker containers:
    - Filesystem isolation via temporary volumes
    - Network isolation (configurable)
    - CPU and memory limits
    - Process isolation

    Usage:
        config = SandboxConfig(type=SandboxType.DOCKER)
        sandbox = DockerSandbox(config)
        await sandbox.setup()

        response = await sandbox.execute(ExecutionRequest(
            code="result = 1 + 1"
        ))

        await sandbox.cleanup()
    """

    def __init__(self, config: SandboxConfig):
        """
        Initialize Docker sandbox.

        Args:
            config: Sandbox configuration
        """
        super().__init__(config)

        # Docker client (lazy initialization)
        self._client = None
        self._container = None

        # Local work directory for file I/O
        self.work_dir: Optional[Path] = None

        # Image configuration
        self.image_name = f"{DEFAULT_IMAGE_NAME}:{DEFAULT_IMAGE_TAG}"

        # Installed packages tracking
        self._installed_packages: set = set()

    @property
    def client(self):
        """Get or create Docker client (lazy initialization)."""
        if self._client is None:
            try:
                import docker
                self._client = docker.from_env()
            except ImportError:
                raise RuntimeError(
                    "Docker SDK not installed. Install with: pip install docker"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Docker: {e}")
        return self._client

    async def setup(self) -> None:
        """
        Initialize Docker sandbox environment.

        - Ensures base image exists (builds if needed)
        - Creates local work directory
        - Starts container
        """
        if self._is_setup:
            return

        try:
            # Ensure image exists
            await self._ensure_image()

            # Create local work directory
            self.work_dir = Path(tempfile.mkdtemp(prefix="cape_docker_"))

            # Start container
            await self._start_container()

            # Pre-install packages if configured
            if self.config.pre_installed_packages:
                await self.install_packages(self.config.pre_installed_packages)

            self._is_setup = True
            logger.info(f"Docker sandbox setup complete: {self._container.short_id}")

        except Exception as e:
            # Cleanup on failure
            await self.cleanup()
            raise RuntimeError(f"Failed to setup Docker sandbox: {e}")

    async def _ensure_image(self) -> None:
        """Ensure base image exists, build if needed."""
        try:
            self.client.images.get(self.image_name)
            logger.debug(f"Using existing image: {self.image_name}")
        except Exception:
            logger.info(f"Building base image: {self.image_name}")
            await self._build_image()

    async def _build_image(self) -> None:
        """Build the base Docker image."""
        # Create Dockerfile in temp directory
        with tempfile.TemporaryDirectory() as build_dir:
            dockerfile_path = Path(build_dir) / "Dockerfile"
            dockerfile_path.write_text(DOCKERFILE_CONTENT)

            # Build image
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.images.build(
                    path=build_dir,
                    tag=self.image_name,
                    rm=True,
                )
            )

        logger.info(f"Built image: {self.image_name}")

    async def _start_container(self) -> None:
        """Start the Docker container."""
        # Prepare container configuration
        container_config = {
            "image": self.image_name,
            "detach": True,
            "volumes": {
                str(self.work_dir): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            # Resource limits
            "mem_limit": f"{self.config.max_memory_mb}m",
            "cpu_period": 100000,
            "cpu_quota": int(self.config.max_cpu_percent * 1000),
            # Security
            "network_mode": "bridge" if self.config.network_enabled else "none",
            "security_opt": ["no-new-privileges:true"],
            # Keep container running
            "command": ["tail", "-f", "/dev/null"],
        }

        # Add extra mounts if configured
        if self.config.mount_points:
            for host_path, container_path in self.config.mount_points.items():
                container_config["volumes"][host_path] = {
                    "bind": container_path,
                    "mode": "ro",  # Read-only for security
                }

        # Start container
        loop = asyncio.get_event_loop()
        self._container = await loop.run_in_executor(
            None,
            lambda: self.client.containers.run(**container_config)
        )

        logger.debug(f"Started container: {self._container.short_id}")

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute code in the Docker container.

        Args:
            request: Execution request with code and inputs

        Returns:
            ExecutionResponse with results
        """
        if not self._is_setup or not self._container:
            raise RuntimeError("Sandbox not initialized. Call setup() first.")

        start_time = time.time()

        try:
            # Prepare workspace
            await self._prepare_workspace(request)

            # Execute in container
            exit_code, stdout, stderr = await self._exec_in_container(request)

            # Collect results
            output, error = await self._collect_results()

            # Collect output files
            files_created = await self._collect_output_files(request)

            success = exit_code == 0 and error is None

            return ExecutionResponse(
                success=success,
                output=output,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time_ms=(time.time() - start_time) * 1000,
                files_created=files_created,
                error=error or (stderr if not success else None),
            )

        except asyncio.TimeoutError:
            return ExecutionResponse(
                success=False,
                error=f"Execution timeout ({self.config.timeout_seconds}s)",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error(f"Docker execution error: {e}")
            return ExecutionResponse(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        finally:
            # Clean up workspace for next execution
            await self._cleanup_workspace()

    async def _prepare_workspace(self, request: ExecutionRequest) -> None:
        """Prepare workspace directory with script and files."""
        # Write execution script
        if request.script_path and request.script_path.exists():
            code = request.script_path.read_text(encoding="utf-8")
        elif request.code:
            code = request.code
        else:
            code = "result = None"

        # Indent code for wrapper
        indented_code = "\n".join(
            "    " + line if line.strip() else line
            for line in code.split("\n")
        )

        # Create wrapper script
        script_content = WRAPPER_SCRIPT.format(code=indented_code)
        script_path = self.work_dir / "_exec.py"
        script_path.write_text(script_content, encoding="utf-8")

        # Write arguments
        args_path = self.work_dir / "_args.json"
        args_path.write_text(json.dumps(request.args or {}), encoding="utf-8")

        # Write input files
        if request.files:
            for filename, content in request.files.items():
                file_path = self.work_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)

    async def _exec_in_container(
        self, request: ExecutionRequest
    ) -> Tuple[int, str, str]:
        """
        Execute command in container.

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        # Build environment variables
        env_vars = dict(request.env or {})
        env_vars["PYTHONPATH"] = "/workspace"

        # Execute with timeout
        loop = asyncio.get_event_loop()

        async def run_exec():
            return await loop.run_in_executor(
                None,
                lambda: self._container.exec_run(
                    cmd=["python", "/workspace/_exec.py"],
                    workdir="/workspace",
                    environment=env_vars,
                    demux=True,
                )
            )

        try:
            exec_result = await asyncio.wait_for(
                run_exec(),
                timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError:
            # Try to kill the execution
            await self._kill_running_processes()
            raise

        # Parse output
        stdout_bytes = exec_result.output[0] or b""
        stderr_bytes = exec_result.output[1] or b""

        return (
            exec_result.exit_code,
            stdout_bytes.decode("utf-8", errors="replace"),
            stderr_bytes.decode("utf-8", errors="replace"),
        )

    async def _kill_running_processes(self) -> None:
        """Kill running processes in container after timeout."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._container.exec_run(
                    cmd=["pkill", "-9", "python"],
                    user="root",
                )
            )
        except Exception as e:
            logger.warning(f"Failed to kill processes: {e}")

    async def _collect_results(self) -> Tuple[Any, Optional[str]]:
        """
        Collect execution results from workspace.

        Returns:
            Tuple of (output, error)
        """
        output = None
        error = None

        # Check for result file
        result_file = self.work_dir / "_result.json"
        if result_file.exists():
            try:
                output = json.loads(result_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse result: {e}")

        # Check for error file
        error_file = self.work_dir / "_error.json"
        if error_file.exists():
            try:
                error_info = json.loads(error_file.read_text(encoding="utf-8"))
                error = error_info.get("error", "Unknown error")
            except json.JSONDecodeError:
                error = "Execution failed with unknown error"

        return output, error

    async def _collect_output_files(
        self, request: ExecutionRequest
    ) -> Dict[str, bytes]:
        """Collect output files from workspace."""
        files = {}

        # Skip internal files and input files
        skip_files = {"_exec.py", "_args.json", "_result.json", "_error.json"}
        input_files = set(request.files.keys()) if request.files else set()

        for path in self.work_dir.rglob("*"):
            if path.is_file():
                rel_path = str(path.relative_to(self.work_dir))

                # Skip internal and input files
                if path.name in skip_files or rel_path in input_files:
                    continue

                try:
                    files[rel_path] = path.read_bytes()
                except Exception as e:
                    logger.warning(f"Failed to read output file {rel_path}: {e}")

        return files

    async def _cleanup_workspace(self) -> None:
        """Clean up workspace after execution."""
        if not self.work_dir:
            return

        # Remove all files except the directory itself
        for item in self.work_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                logger.warning(f"Failed to cleanup {item}: {e}")

    async def install_packages(self, packages: List[str]) -> bool:
        """
        Install Python packages in the container.

        Args:
            packages: List of package names to install

        Returns:
            True if successful
        """
        if not self._container:
            return False

        # Filter out already installed packages
        new_packages = [p for p in packages if p not in self._installed_packages]
        if not new_packages:
            return True

        logger.info(f"Installing packages: {new_packages}")

        try:
            loop = asyncio.get_event_loop()
            exec_result = await loop.run_in_executor(
                None,
                lambda: self._container.exec_run(
                    cmd=["pip", "install", "--no-cache-dir"] + new_packages,
                )
            )

            if exec_result.exit_code == 0:
                self._installed_packages.update(new_packages)
                return True
            else:
                logger.error(
                    f"Failed to install packages: {exec_result.output.decode()}"
                )
                return False

        except Exception as e:
            logger.error(f"Package installation error: {e}")
            return False

    async def cleanup(self) -> None:
        """Stop and remove container, cleanup workspace."""
        # Stop and remove container
        if self._container:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self._container.stop(timeout=5)
                )
                await loop.run_in_executor(
                    None,
                    lambda: self._container.remove(force=True)
                )
                logger.debug(f"Removed container: {self._container.short_id}")
            except Exception as e:
                logger.error(f"Error stopping container: {e}")
            finally:
                self._container = None

        # Remove work directory
        if self.work_dir and self.work_dir.exists():
            try:
                shutil.rmtree(self.work_dir)
            except Exception as e:
                logger.error(f"Error removing work directory: {e}")
            finally:
                self.work_dir = None

        self._is_setup = False

    def get_container_id(self) -> Optional[str]:
        """Get the container ID if running."""
        return self._container.short_id if self._container else None

    async def get_container_stats(self) -> Optional[Dict[str, Any]]:
        """Get container resource usage statistics."""
        if not self._container:
            return None

        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None,
                lambda: self._container.stats(stream=False)
            )

            # Parse CPU and memory usage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]

            cpu_percent = 0.0
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * 100.0

            memory_usage = stats["memory_stats"].get("usage", 0)
            memory_limit = stats["memory_stats"].get("limit", 1)
            memory_percent = (memory_usage / memory_limit) * 100.0

            return {
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage_mb": round(memory_usage / (1024 * 1024), 2),
                "memory_limit_mb": round(memory_limit / (1024 * 1024), 2),
                "memory_percent": round(memory_percent, 2),
            }

        except Exception as e:
            logger.warning(f"Failed to get container stats: {e}")
            return None


async def check_docker_available() -> Tuple[bool, str]:
    """
    Check if Docker is available and running.

    Returns:
        Tuple of (is_available, message)
    """
    try:
        import docker
        client = docker.from_env()
        client.ping()
        version = client.version()
        return True, f"Docker {version.get('Version', 'unknown')} available"
    except ImportError:
        return False, "Docker SDK not installed (pip install docker)"
    except Exception as e:
        return False, f"Docker not available: {e}"


async def build_base_image(force: bool = False) -> bool:
    """
    Build the base Docker image for sandboxes.

    Args:
        force: Force rebuild even if image exists

    Returns:
        True if successful
    """
    try:
        import docker
        client = docker.from_env()

        image_name = f"{DEFAULT_IMAGE_NAME}:{DEFAULT_IMAGE_TAG}"

        # Check if image exists
        if not force:
            try:
                client.images.get(image_name)
                logger.info(f"Image already exists: {image_name}")
                return True
            except docker.errors.ImageNotFound:
                pass

        # Build image
        logger.info(f"Building image: {image_name}")

        with tempfile.TemporaryDirectory() as build_dir:
            dockerfile_path = Path(build_dir) / "Dockerfile"
            dockerfile_path.write_text(DOCKERFILE_CONTENT)

            client.images.build(
                path=build_dir,
                tag=image_name,
                rm=True,
            )

        logger.info(f"Successfully built: {image_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to build image: {e}")
        return False
