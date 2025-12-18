"""
Process Sandbox - Execute code in isolated subprocess.

Features:
- Process-level isolation
- Timeout control
- Resource limits via subprocess
- Suitable for development and testing
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .manager import (
    BaseSandbox,
    ExecutionRequest,
    ExecutionResponse,
    SandboxConfig,
)

logger = logging.getLogger(__name__)


class ProcessSandbox(BaseSandbox):
    """
    Subprocess-based sandbox for code execution.

    Executes Python code in an isolated subprocess with:
    - Separate process space
    - Timeout control
    - Working directory isolation
    - Input/output file handling

    Best for development and testing environments.
    For production, consider DockerSandbox.
    """

    # Wrapper script template
    WRAPPER_TEMPLATE = '''
import json
import sys
import os
from pathlib import Path

# Change to working directory
os.chdir("{work_dir}")

# Load arguments
args = {args_json}

# Make args available as global
globals()['args'] = args
globals()['inputs'] = args

# Execute user code
_result = None
_error = None

try:
{indented_code}

    # Capture result
    if 'result' in dir():
        _result = result
    elif 'output' in dir():
        _result = output

except Exception as e:
    _error = str(e)
    print(f"Error: {{e}}", file=sys.stderr)
    import traceback
    traceback.print_exc()

# Save result
result_data = {{
    "success": _error is None,
    "result": _result,
    "error": _error,
}}

try:
    Path("_result.json").write_text(
        json.dumps(result_data, default=str, ensure_ascii=False),
        encoding="utf-8"
    )
except Exception as e:
    print(f"Failed to write result: {{e}}", file=sys.stderr)

# Exit with appropriate code
sys.exit(0 if _error is None else 1)
'''

    def __init__(self, config: SandboxConfig):
        """Initialize process sandbox."""
        super().__init__(config)
        self.work_dir: Optional[Path] = None
        self._installed_packages: Set[str] = set()
        self._python_path: str = sys.executable

    async def setup(self) -> None:
        """Create working directory and initialize environment."""
        if self._is_setup:
            return

        # Create temporary working directory
        if self.config.work_dir:
            self.work_dir = Path(self.config.work_dir)
            self.work_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.work_dir = Path(tempfile.mkdtemp(prefix="cape_sandbox_"))

        logger.debug(f"ProcessSandbox work_dir: {self.work_dir}")

        # Pre-install packages
        if self.config.pre_installed_packages:
            await self.install_packages(self.config.pre_installed_packages)

        self._is_setup = True

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute code in subprocess.

        Args:
            request: Execution request

        Returns:
            ExecutionResponse with results
        """
        if not self._is_setup:
            await self.setup()

        start_time = time.time()

        try:
            # Prepare execution
            exec_dir = self._prepare_execution(request)
            script_path = exec_dir / "_runner.py"

            # Build environment
            env = self._build_environment(request)

            # Execute subprocess
            process = await asyncio.create_subprocess_exec(
                self._python_path,
                str(script_path),
                cwd=str(exec_dir),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ExecutionResponse(
                    success=False,
                    error=f"Execution timeout ({self.config.timeout_seconds}s)",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # Parse results
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Read result file
            output = None
            result_file = exec_dir / "_result.json"
            if result_file.exists():
                try:
                    result_data = json.loads(result_file.read_text(encoding="utf-8"))
                    output = result_data.get("result")
                    if result_data.get("error"):
                        stderr_str = result_data["error"] + "\n" + stderr_str
                except json.JSONDecodeError:
                    pass

            # Collect output files
            files_created = self._collect_output_files(exec_dir, request)

            execution_time = (time.time() - start_time) * 1000

            return ExecutionResponse(
                success=process.returncode == 0,
                output=output,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode or 0,
                execution_time_ms=execution_time,
                files_created=files_created,
                error=stderr_str if process.returncode != 0 and not output else None,
            )

        except Exception as e:
            logger.error(f"Process execution failed: {e}")
            return ExecutionResponse(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _prepare_execution(self, request: ExecutionRequest) -> Path:
        """
        Prepare execution directory with code and files.

        Returns:
            Path to execution directory
        """
        # Create execution subdirectory
        exec_id = f"exec_{int(time.time() * 1000)}"
        exec_dir = self.work_dir / exec_id
        exec_dir.mkdir(parents=True, exist_ok=True)

        # Get code to execute
        code = self._get_code(request, exec_dir)

        # Write input files
        if request.files:
            for filename, content in request.files.items():
                file_path = exec_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    file_path.write_bytes(content)
                else:
                    file_path.write_text(content, encoding="utf-8")

        # Create wrapper script
        indented_code = "\n".join("    " + line for line in code.split("\n"))

        wrapper = self.WRAPPER_TEMPLATE.format(
            work_dir=str(exec_dir).replace("\\", "\\\\"),
            args_json=json.dumps(request.args or {}, ensure_ascii=False),
            indented_code=indented_code,
        )

        runner_path = exec_dir / "_runner.py"
        runner_path.write_text(wrapper, encoding="utf-8")

        return exec_dir

    def _get_code(self, request: ExecutionRequest, exec_dir: Path) -> str:
        """
        Get code from request.

        Handles script_path, code, and entrypoint.
        """
        if request.script_path and request.script_path.exists():
            # Copy script and related files
            script_content = request.script_path.read_text(encoding="utf-8")

            # Copy sibling scripts if in a scripts directory
            if request.script_path.parent.name == "scripts":
                scripts_dir = exec_dir / "scripts"
                scripts_dir.mkdir(exist_ok=True)

                for sibling in request.script_path.parent.glob("*.py"):
                    dest = scripts_dir / sibling.name
                    dest.write_text(sibling.read_text(encoding="utf-8"), encoding="utf-8")

                # Add scripts dir to path in code
                script_content = f"import sys; sys.path.insert(0, 'scripts')\n{script_content}"

            # Handle entrypoint function
            if request.entrypoint:
                script_content += f"\n\nresult = {request.entrypoint}(**args)"

            return script_content

        elif request.code:
            code = request.code

            # Handle entrypoint function
            if request.entrypoint:
                code += f"\n\nresult = {request.entrypoint}(**args)"

            return code

        else:
            return "result = None"

    def _build_environment(self, request: ExecutionRequest) -> Dict[str, str]:
        """Build subprocess environment variables."""
        env = dict(os.environ)

        # Add Python path
        env["PYTHONPATH"] = str(self.work_dir)

        # Add request environment
        if request.env:
            env.update(request.env)

        # Disable Python buffering for real-time output
        env["PYTHONUNBUFFERED"] = "1"

        return env

    def _collect_output_files(
        self,
        exec_dir: Path,
        request: ExecutionRequest,
    ) -> Dict[str, bytes]:
        """
        Collect output files created during execution.

        Excludes:
        - Internal files (_runner.py, _result.json)
        - Input files
        """
        files = {}
        input_files = set(request.files.keys()) if request.files else set()

        for path in exec_dir.rglob("*"):
            if not path.is_file():
                continue

            # Skip internal files
            if path.name.startswith("_"):
                continue

            rel_path = str(path.relative_to(exec_dir))

            # Skip input files
            if rel_path in input_files:
                continue

            # Skip __pycache__
            if "__pycache__" in rel_path:
                continue

            try:
                files[rel_path] = path.read_bytes()
            except Exception as e:
                logger.warning(f"Failed to read output file {rel_path}: {e}")

        return files

    async def install_packages(self, packages: List[str]) -> bool:
        """
        Install Python packages using pip.

        Args:
            packages: Package names to install

        Returns:
            True if successful
        """
        # Filter already installed
        new_packages = [p for p in packages if p not in self._installed_packages]
        if not new_packages:
            return True

        logger.info(f"Installing packages: {new_packages}")

        try:
            process = await asyncio.create_subprocess_exec(
                self._python_path,
                "-m", "pip", "install", "--quiet", *new_packages,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120,  # 2 minutes for package installation
            )

            if process.returncode == 0:
                self._installed_packages.update(new_packages)
                logger.info(f"Successfully installed: {new_packages}")
                return True
            else:
                logger.error(f"Failed to install packages: {stderr.decode()}")
                return False

        except asyncio.TimeoutError:
            logger.error("Package installation timeout")
            return False
        except Exception as e:
            logger.error(f"Package installation error: {e}")
            return False

    async def cleanup(self) -> None:
        """Remove working directory and cleanup resources."""
        if self.work_dir and self.work_dir.exists():
            try:
                shutil.rmtree(self.work_dir)
                logger.debug(f"Cleaned up work_dir: {self.work_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup work_dir: {e}")

        self._is_setup = False
        self._installed_packages.clear()

    async def run_script(
        self,
        script_path: Path,
        args: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, bytes]] = None,
    ) -> ExecutionResponse:
        """
        Convenience method to run a script file.

        Args:
            script_path: Path to Python script
            args: Arguments to pass
            files: Input files

        Returns:
            ExecutionResponse
        """
        return await self.execute(ExecutionRequest(
            script_path=script_path,
            args=args or {},
            files=files or {},
        ))

    async def run_code(
        self,
        code: str,
        args: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, bytes]] = None,
    ) -> ExecutionResponse:
        """
        Convenience method to run inline code.

        Args:
            code: Python code to execute
            args: Arguments available as 'args' dict
            files: Input files

        Returns:
            ExecutionResponse
        """
        return await self.execute(ExecutionRequest(
            code=code,
            args=args or {},
            files=files or {},
        ))
