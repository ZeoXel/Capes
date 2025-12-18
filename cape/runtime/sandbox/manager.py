"""
Sandbox Manager - Core abstractions for code execution sandboxes.

Provides:
- SandboxConfig: Configuration for sandbox environments
- ExecutionRequest/Response: Request and response models
- BaseSandbox: Abstract base class for sandbox implementations
- SandboxManager: Factory for creating and managing sandboxes
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SandboxType(str, Enum):
    """Sandbox implementation type."""
    DOCKER = "docker"       # Docker container isolation (production)
    PROCESS = "process"     # Subprocess isolation (development)
    INPROCESS = "inprocess" # In-process execution (fast prototyping, unsafe)


@dataclass
class SandboxConfig:
    """
    Sandbox configuration.

    Attributes:
        type: Sandbox implementation type
        timeout_seconds: Maximum execution time
        max_memory_mb: Memory limit in MB
        max_cpu_percent: CPU usage limit (0-100)
        network_enabled: Whether network access is allowed
        work_dir: Working directory (created if None)
        mount_points: Host paths to mount in sandbox
        python_version: Python version to use
        pre_installed_packages: Packages to pre-install
    """
    type: SandboxType = SandboxType.PROCESS
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    network_enabled: bool = False

    # Filesystem
    work_dir: Optional[Path] = None
    mount_points: Dict[str, str] = field(default_factory=dict)

    # Python environment
    python_version: str = "3.11"
    pre_installed_packages: List[str] = field(default_factory=list)

    # Security
    allow_subprocess: bool = False
    allow_file_write: bool = True
    allowed_paths: List[str] = field(default_factory=list)


@dataclass
class ExecutionRequest:
    """
    Code execution request.

    Attributes:
        script_path: Path to script file to execute
        code: Inline code to execute (if no script_path)
        entrypoint: Entry function name (optional)
        args: Arguments to pass to the script
        env: Environment variables
        files: Input files (filename -> content)
        working_dir: Working directory within sandbox
    """
    script_path: Optional[Path] = None
    code: Optional[str] = None
    entrypoint: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    files: Dict[str, bytes] = field(default_factory=dict)
    working_dir: Optional[str] = None


@dataclass
class ExecutionResponse:
    """
    Code execution response.

    Attributes:
        success: Whether execution succeeded
        output: Parsed output (from _result.json if available)
        stdout: Standard output
        stderr: Standard error
        exit_code: Process exit code
        execution_time_ms: Execution duration in milliseconds
        files_created: Output files (filename -> content)
        error: Error message if failed
    """
    success: bool
    output: Any = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0
    files_created: Dict[str, bytes] = field(default_factory=dict)
    error: Optional[str] = None


class BaseSandbox(ABC):
    """
    Abstract base class for sandbox implementations.

    All sandbox implementations must inherit from this class
    and implement the required abstract methods.
    """

    def __init__(self, config: SandboxConfig):
        """
        Initialize sandbox with configuration.

        Args:
            config: Sandbox configuration
        """
        self.config = config
        self._is_setup = False

    @abstractmethod
    async def setup(self) -> None:
        """
        Initialize sandbox environment.

        Creates working directories, virtual environments, etc.
        Must be called before execute().
        """
        pass

    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute code in the sandbox.

        Args:
            request: Execution request with code and inputs

        Returns:
            ExecutionResponse with results
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up sandbox resources.

        Removes temporary files, stops containers, etc.
        """
        pass

    @abstractmethod
    async def install_packages(self, packages: List[str]) -> bool:
        """
        Install Python packages in the sandbox.

        Args:
            packages: List of package names to install

        Returns:
            True if successful, False otherwise
        """
        pass

    async def __aenter__(self) -> "BaseSandbox":
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup()


class SandboxManager:
    """
    Sandbox factory and lifecycle manager.

    Creates appropriate sandbox instances based on configuration
    and manages their lifecycle.

    Usage:
        manager = SandboxManager()
        sandbox = await manager.get_sandbox("my-sandbox")

        response = await sandbox.execute(ExecutionRequest(
            code="result = 1 + 1"
        ))

        await manager.release_sandbox("my-sandbox")
    """

    def __init__(self, default_config: Optional[SandboxConfig] = None):
        """
        Initialize sandbox manager.

        Args:
            default_config: Default configuration for new sandboxes
        """
        self.default_config = default_config or SandboxConfig()
        self._sandboxes: Dict[str, BaseSandbox] = {}
        self._sandbox_configs: Dict[str, SandboxConfig] = {}

    async def get_sandbox(
        self,
        sandbox_id: str,
        config: Optional[SandboxConfig] = None,
    ) -> BaseSandbox:
        """
        Get or create a sandbox.

        Args:
            sandbox_id: Unique identifier for the sandbox
            config: Configuration (uses default if None)

        Returns:
            Initialized sandbox instance
        """
        if sandbox_id in self._sandboxes:
            return self._sandboxes[sandbox_id]

        config = config or self.default_config
        sandbox = self._create_sandbox(config)

        await sandbox.setup()

        self._sandboxes[sandbox_id] = sandbox
        self._sandbox_configs[sandbox_id] = config

        logger.info(f"Created sandbox: {sandbox_id} (type={config.type.value})")

        return sandbox

    def _create_sandbox(self, config: SandboxConfig) -> BaseSandbox:
        """
        Create sandbox instance based on config type.

        Args:
            config: Sandbox configuration

        Returns:
            Sandbox instance (not yet initialized)
        """
        if config.type == SandboxType.DOCKER:
            try:
                from .docker_sandbox import DockerSandbox
                return DockerSandbox(config)
            except ImportError:
                logger.warning("Docker sandbox not available, falling back to process")
                config.type = SandboxType.PROCESS

        if config.type == SandboxType.PROCESS:
            from .process_sandbox import ProcessSandbox
            return ProcessSandbox(config)

        # Default to in-process
        from .inprocess_sandbox import InProcessSandbox
        return InProcessSandbox(config)

    async def release_sandbox(self, sandbox_id: str) -> None:
        """
        Release and cleanup a sandbox.

        Args:
            sandbox_id: ID of sandbox to release
        """
        if sandbox_id not in self._sandboxes:
            return

        sandbox = self._sandboxes[sandbox_id]

        try:
            await sandbox.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up sandbox {sandbox_id}: {e}")

        del self._sandboxes[sandbox_id]
        del self._sandbox_configs[sandbox_id]

        logger.info(f"Released sandbox: {sandbox_id}")

    async def release_all(self) -> None:
        """Release all sandboxes."""
        sandbox_ids = list(self._sandboxes.keys())
        for sandbox_id in sandbox_ids:
            await self.release_sandbox(sandbox_id)

    def get_sandbox_count(self) -> int:
        """Get number of active sandboxes."""
        return len(self._sandboxes)

    def list_sandboxes(self) -> List[str]:
        """List all active sandbox IDs."""
        return list(self._sandboxes.keys())
