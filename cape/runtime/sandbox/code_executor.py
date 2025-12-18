"""
Enhanced Code Executor - Execute Cape code using sandbox infrastructure.

Features:
- Multiple sandbox backends (Docker, Process, InProcess)
- Automatic dependency installation
- Scripts directory support
- File I/O handling
- Timeout and resource limits
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from cape.runtime.context import ExecutionContext, ExecutionResult
from .manager import (
    SandboxManager,
    SandboxConfig,
    SandboxType,
    ExecutionRequest,
)

if TYPE_CHECKING:
    from cape.core.models import Cape

logger = logging.getLogger(__name__)


# Default packages for document processing
DEFAULT_PACKAGES = [
    "openpyxl",      # Excel
    "pandas",        # Data processing
    "python-docx",   # Word documents
    "python-pptx",   # PowerPoint
    "pdfplumber",    # PDF reading
    "reportlab",     # PDF generation
    "PyPDF2",        # PDF manipulation
    "pillow",        # Image processing
]


class EnhancedCodeExecutor:
    """
    Enhanced code executor with sandbox support.

    Provides secure, isolated code execution with:
    - Multiple sandbox backends
    - Automatic dependency management
    - Script directory support
    - File I/O handling

    Usage:
        executor = EnhancedCodeExecutor(sandbox_type=SandboxType.PROCESS)

        result = await executor.execute(
            cape=my_cape,
            inputs={"data": "hello"},
            context=execution_context,
        )
    """

    def __init__(
        self,
        sandbox_type: SandboxType = SandboxType.PROCESS,
        sandbox_config: Optional[SandboxConfig] = None,
        default_packages: Optional[List[str]] = None,
        auto_install_deps: bool = True,
    ):
        """
        Initialize enhanced code executor.

        Args:
            sandbox_type: Type of sandbox to use
            sandbox_config: Custom sandbox configuration
            default_packages: Packages to pre-install
            auto_install_deps: Whether to auto-install detected dependencies
        """
        self.sandbox_type = sandbox_type
        self.default_packages = default_packages or DEFAULT_PACKAGES
        self.auto_install_deps = auto_install_deps

        # Build config
        if sandbox_config:
            self.sandbox_config = sandbox_config
        else:
            self.sandbox_config = SandboxConfig(
                type=sandbox_type,
                pre_installed_packages=self.default_packages,
            )

        # Create manager
        self.sandbox_manager = SandboxManager(self.sandbox_config)

        # Track sandbox usage
        self._sandbox_cache: Dict[str, str] = {}  # cape_id -> sandbox_id

    async def execute(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """
        Execute Cape code in sandbox.

        Args:
            cape: Cape to execute
            inputs: Input parameters
            context: Execution context

        Returns:
            ExecutionResult with output
        """
        start_time = time.time()

        try:
            # Get or create sandbox
            sandbox_id = self._get_sandbox_id(cape, context)
            sandbox_config = self._build_sandbox_config(cape)
            sandbox = await self.sandbox_manager.get_sandbox(sandbox_id, sandbox_config)

            # Install dependencies
            if self.auto_install_deps:
                deps = self._get_dependencies(cape)
                if deps:
                    await sandbox.install_packages(deps)

            # Build execution request
            request = self._build_execution_request(cape, inputs, context)

            # Execute
            response = await sandbox.execute(request)

            # Store output files in context
            if response.files_created:
                context.set("output_files", response.files_created)

            # Build result
            return ExecutionResult(
                success=response.success,
                output=response.output or response.stdout.strip(),
                error=response.error,
                execution_time_ms=response.execution_time_ms,
                metadata={
                    "stdout": response.stdout,
                    "stderr": response.stderr,
                    "exit_code": response.exit_code,
                    "files_created": list(response.files_created.keys()),
                    "sandbox_id": sandbox_id,
                },
            )

        except Exception as e:
            logger.error(f"Enhanced code execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _get_sandbox_id(self, cape: "Cape", context: ExecutionContext) -> str:
        """Generate sandbox ID for cape execution."""
        # Reuse sandbox for same cape (optional optimization)
        # return self._sandbox_cache.get(cape.id) or f"{cape.id}_{context.trace_id}"

        # Always create new sandbox for isolation
        return f"{cape.id}_{context.trace_id}_{int(time.time() * 1000)}"

    def _build_sandbox_config(self, cape: "Cape") -> SandboxConfig:
        """Build sandbox config from Cape."""
        config = SandboxConfig(
            type=self.sandbox_type,
            timeout_seconds=cape.execution.timeout_seconds,
            pre_installed_packages=self.default_packages,
        )

        # Override from Cape's code adapter config
        code_config = cape.model_adapters.get("code", {})
        if code_config:
            if "memory_mb" in code_config:
                config.max_memory_mb = code_config["memory_mb"]
            if "network" in code_config:
                config.network_enabled = code_config["network"]
            if "timeout" in code_config:
                config.timeout_seconds = code_config["timeout"]

        return config

    def _get_dependencies(self, cape: "Cape") -> List[str]:
        """Get dependencies from Cape configuration."""
        deps = set(self.default_packages)

        # From code adapter config
        code_config = cape.model_adapters.get("code", {})
        if "dependencies" in code_config:
            deps.update(code_config["dependencies"])

        # From Cape metadata
        if hasattr(cape.metadata, "dependencies"):
            deps.update(cape.metadata.dependencies or [])

        return list(deps)

    def _build_execution_request(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionRequest:
        """Build execution request from Cape and inputs."""
        request = ExecutionRequest(args=inputs.copy())

        # Get Cape path
        cape_path = getattr(cape, "_path", None)

        # Priority: entrypoint > code > model_adapters.code.script
        if cape.execution.entrypoint and cape_path:
            script_path = cape_path / cape.execution.entrypoint
            if script_path.exists():
                request.script_path = script_path

                # Also include other scripts from same directory
                scripts_dir = script_path.parent
                if scripts_dir.name == "scripts":
                    request.files = request.files or {}
                    for f in scripts_dir.glob("*.py"):
                        if f != script_path:
                            request.files[f"scripts/{f.name}"] = f.read_bytes()

        elif cape.execution.code:
            request.code = cape.execution.code

        elif "code" in cape.model_adapters:
            code_config = cape.model_adapters["code"]
            if "script" in code_config:
                request.code = code_config["script"]

        # Handle input files from inputs
        if "_files" in inputs:
            request.files = request.files or {}
            request.files.update(inputs.pop("_files"))

        # Set entrypoint function if specified
        if cape.execution.entrypoint and "." in cape.execution.entrypoint:
            # Format: module.function
            request.entrypoint = cape.execution.entrypoint.split(".")[-1]

        return request

    def validate_inputs(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
    ) -> Optional[str]:
        """Validate inputs against Cape schema."""
        schema = cape.interface.input_schema
        required = schema.required

        for field in required:
            if field not in inputs and field != "_files":
                return f"Missing required field: {field}"

        return None

    async def cleanup(self) -> None:
        """Release all sandboxes."""
        await self.sandbox_manager.release_all()


# Factory function
def create_code_executor(
    sandbox_type: str = "process",
    **kwargs,
) -> EnhancedCodeExecutor:
    """
    Create code executor with specified sandbox type.

    Args:
        sandbox_type: "docker", "process", or "inprocess"
        **kwargs: Additional arguments for EnhancedCodeExecutor

    Returns:
        EnhancedCodeExecutor instance
    """
    type_map = {
        "docker": SandboxType.DOCKER,
        "process": SandboxType.PROCESS,
        "inprocess": SandboxType.INPROCESS,
    }

    return EnhancedCodeExecutor(
        sandbox_type=type_map.get(sandbox_type, SandboxType.PROCESS),
        **kwargs,
    )
