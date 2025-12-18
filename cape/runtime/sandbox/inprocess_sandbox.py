"""
In-Process Sandbox - Execute code directly in current process.

Features:
- Fastest execution (no subprocess overhead)
- Direct access to Python environment
- Useful for development and testing
- WARNING: Not secure for untrusted code!
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
import time
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .manager import (
    BaseSandbox,
    ExecutionRequest,
    ExecutionResponse,
    SandboxConfig,
)

logger = logging.getLogger(__name__)


class InProcessSandbox(BaseSandbox):
    """
    In-process sandbox for fast code execution.

    Executes code directly in the current Python process.
    This is the fastest option but provides NO security isolation.

    Use only for:
    - Development and testing
    - Trusted code
    - Quick prototyping

    DO NOT use for:
    - Untrusted user code
    - Production environments
    - Security-sensitive applications
    """

    def __init__(self, config: SandboxConfig):
        """Initialize in-process sandbox."""
        super().__init__(config)
        self.work_dir: Optional[Path] = None
        self._installed_packages: Set[str] = set()
        self._original_cwd: Optional[str] = None

    async def setup(self) -> None:
        """Create working directory."""
        if self._is_setup:
            return

        # Create temporary working directory
        if self.config.work_dir:
            self.work_dir = Path(self.config.work_dir)
            self.work_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.work_dir = Path(tempfile.mkdtemp(prefix="cape_inprocess_"))

        self._original_cwd = os.getcwd()

        logger.debug(f"InProcessSandbox work_dir: {self.work_dir}")
        logger.warning(
            "InProcessSandbox provides NO security isolation. "
            "Do not use for untrusted code!"
        )

        self._is_setup = True

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute code in current process.

        WARNING: This provides no isolation. Use only for trusted code.
        """
        if not self._is_setup:
            await self.setup()

        start_time = time.time()

        # Prepare execution directory
        exec_dir = self._prepare_execution(request)

        # Capture stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_stdout = StringIO()
        captured_stderr = StringIO()

        # Prepare execution namespace
        namespace: Dict[str, Any] = {
            "__builtins__": __builtins__,
            "args": request.args or {},
            "inputs": request.args or {},
        }

        result = None
        error = None

        try:
            # Change to execution directory
            os.chdir(exec_dir)

            # Add to Python path
            if str(exec_dir) not in sys.path:
                sys.path.insert(0, str(exec_dir))

            # Redirect output
            sys.stdout = captured_stdout
            sys.stderr = captured_stderr

            # Get code
            code = self._get_code(request, exec_dir)

            # Execute
            exec(code, namespace)

            # Get result
            result = namespace.get("result") or namespace.get("output")

            return ExecutionResponse(
                success=True,
                output=result,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue(),
                exit_code=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                files_created=self._collect_output_files(exec_dir, request),
            )

        except Exception as e:
            logger.error(f"InProcess execution failed: {e}")
            import traceback
            error_trace = traceback.format_exc()

            return ExecutionResponse(
                success=False,
                output=result,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue() + "\n" + error_trace,
                exit_code=1,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            # Restore working directory
            if self._original_cwd:
                os.chdir(self._original_cwd)

    def _prepare_execution(self, request: ExecutionRequest) -> Path:
        """Prepare execution directory."""
        exec_id = f"exec_{int(time.time() * 1000)}"
        exec_dir = self.work_dir / exec_id
        exec_dir.mkdir(parents=True, exist_ok=True)

        # Write input files
        if request.files:
            for filename, content in request.files.items():
                file_path = exec_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    file_path.write_bytes(content)
                else:
                    file_path.write_text(content, encoding="utf-8")

        return exec_dir

    def _get_code(self, request: ExecutionRequest, exec_dir: Path) -> str:
        """Get code from request."""
        if request.script_path and request.script_path.exists():
            code = request.script_path.read_text(encoding="utf-8")

            # Copy sibling scripts
            if request.script_path.parent.name == "scripts":
                scripts_dir = exec_dir / "scripts"
                scripts_dir.mkdir(exist_ok=True)

                for sibling in request.script_path.parent.glob("*.py"):
                    dest = scripts_dir / sibling.name
                    dest.write_text(sibling.read_text(encoding="utf-8"), encoding="utf-8")

                code = f"import sys; sys.path.insert(0, 'scripts')\n{code}"

            if request.entrypoint:
                code += f"\n\nresult = {request.entrypoint}(**args)"

            return code

        elif request.code:
            code = request.code
            if request.entrypoint:
                code += f"\n\nresult = {request.entrypoint}(**args)"
            return code

        return "result = None"

    def _collect_output_files(
        self,
        exec_dir: Path,
        request: ExecutionRequest,
    ) -> Dict[str, bytes]:
        """Collect output files."""
        files = {}
        input_files = set(request.files.keys()) if request.files else set()

        for path in exec_dir.rglob("*"):
            if not path.is_file():
                continue

            if path.name.startswith("_"):
                continue

            rel_path = str(path.relative_to(exec_dir))

            if rel_path in input_files:
                continue

            if "__pycache__" in rel_path:
                continue

            try:
                files[rel_path] = path.read_bytes()
            except Exception:
                pass

        return files

    async def install_packages(self, packages: List[str]) -> bool:
        """
        Install packages using pip (blocking).

        Note: This installs to the system Python, not isolated.
        """
        import subprocess

        new_packages = [p for p in packages if p not in self._installed_packages]
        if not new_packages:
            return True

        logger.info(f"Installing packages: {new_packages}")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet"] + new_packages,
                capture_output=True,
                timeout=120,
            )

            if result.returncode == 0:
                self._installed_packages.update(new_packages)
                return True
            else:
                logger.error(f"Failed to install: {result.stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Package installation error: {e}")
            return False

    async def cleanup(self) -> None:
        """Remove working directory."""
        if self.work_dir and self.work_dir.exists():
            try:
                shutil.rmtree(self.work_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup: {e}")

        self._is_setup = False

    async def run_code(
        self,
        code: str,
        args: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResponse:
        """Quick code execution helper."""
        return await self.execute(ExecutionRequest(
            code=code,
            args=args or {},
        ))
