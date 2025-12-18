"""
Cape Sandbox Module - Secure code execution environments.

Provides isolated execution environments for running Cape scripts safely.
Supports multiple sandbox backends: Docker, Process, and InProcess.
"""

from .manager import (
    SandboxManager,
    SandboxConfig,
    SandboxType,
    ExecutionRequest,
    ExecutionResponse,
    BaseSandbox,
)
from .process_sandbox import ProcessSandbox
from .inprocess_sandbox import InProcessSandbox
from .code_executor import EnhancedCodeExecutor, create_code_executor

# Docker sandbox (optional - requires docker package)
try:
    from .docker_sandbox import (
        DockerSandbox,
        check_docker_available,
        build_base_image,
    )
    _DOCKER_AVAILABLE = True
except ImportError:
    DockerSandbox = None
    check_docker_available = None
    build_base_image = None
    _DOCKER_AVAILABLE = False

__all__ = [
    # Manager
    "SandboxManager",
    "SandboxConfig",
    "SandboxType",
    "ExecutionRequest",
    "ExecutionResponse",
    "BaseSandbox",
    # Sandboxes
    "ProcessSandbox",
    "InProcessSandbox",
    "DockerSandbox",
    # Docker utilities
    "check_docker_available",
    "build_base_image",
    # Executor
    "EnhancedCodeExecutor",
    "create_code_executor",
]
