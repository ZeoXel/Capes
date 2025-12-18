# Cape 代码执行层架构设计

## 1. 设计目标

实现 Claude Skills 的**完整执行能力**，但不局限于 Claude 框架：

- **模型无关**: 任何 LLM 都可以触发代码执行
- **安全隔离**: 沙箱环境，防止恶意代码
- **依赖管理**: 自动安装/管理 Python 包
- **文件系统**: 支持文件读写与临时存储
- **脚本执行**: 支持 scripts/ 目录中的脚本
- **可扩展**: 支持 Python、Node.js 等多运行时

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Cape Runtime                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ LLM Executor │  │Tool Executor │  │ Code Executor│ ◄── 重构  │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│                                             │                   │
├─────────────────────────────────────────────┼───────────────────┤
│                    Execution Layer          │                   │
│  ┌──────────────────────────────────────────▼───────────────┐  │
│  │                  Sandbox Manager                          │  │
│  │  ┌─────────────┬─────────────┬─────────────────────────┐ │  │
│  │  │   Docker    │   Process   │      In-Process         │ │  │
│  │  │   Sandbox   │   Sandbox   │      (Restricted)       │ │  │
│  │  │  (推荐生产) │  (开发/测试) │    (快速原型)          │ │  │
│  │  └─────────────┴─────────────┴─────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Resource Manager                         │  │
│  │  ┌─────────────┬─────────────┬─────────────────────────┐ │  │
│  │  │ File System │ Dependency  │      Environment        │ │  │
│  │  │   Manager   │   Manager   │       Manager           │ │  │
│  │  └─────────────┴─────────────┴─────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 核心组件设计

### 3.1 Sandbox Manager

```python
# cape/runtime/sandbox/manager.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

class SandboxType(str, Enum):
    DOCKER = "docker"       # Docker 容器隔离 (生产推荐)
    PROCESS = "process"     # 子进程隔离 (开发测试)
    INPROCESS = "inprocess" # 进程内执行 (快速原型,不安全)


@dataclass
class SandboxConfig:
    """沙箱配置"""
    type: SandboxType = SandboxType.PROCESS
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    network_enabled: bool = False

    # 文件系统
    work_dir: Optional[Path] = None
    mount_points: Dict[str, str] = None  # host_path -> container_path

    # 依赖
    python_version: str = "3.11"
    pre_installed_packages: list = None


@dataclass
class ExecutionRequest:
    """执行请求"""
    script_path: Optional[Path] = None   # 脚本文件路径
    code: Optional[str] = None           # 内联代码
    entrypoint: Optional[str] = None     # 入口函数
    args: Dict[str, Any] = None          # 参数
    env: Dict[str, str] = None           # 环境变量
    files: Dict[str, bytes] = None       # 输入文件


@dataclass
class ExecutionResponse:
    """执行结果"""
    success: bool
    output: Any = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0
    files_created: Dict[str, bytes] = None  # 输出文件
    error: Optional[str] = None


class BaseSandbox(ABC):
    """沙箱基类"""

    def __init__(self, config: SandboxConfig):
        self.config = config

    @abstractmethod
    async def setup(self) -> None:
        """初始化沙箱环境"""
        pass

    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """执行代码"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass

    @abstractmethod
    async def install_packages(self, packages: list[str]) -> bool:
        """安装 Python 包"""
        pass


class SandboxManager:
    """沙箱管理器 - 根据配置创建合适的沙箱"""

    def __init__(self, default_config: Optional[SandboxConfig] = None):
        self.default_config = default_config or SandboxConfig()
        self._sandboxes: Dict[str, BaseSandbox] = {}

    async def get_sandbox(
        self,
        sandbox_id: str,
        config: Optional[SandboxConfig] = None
    ) -> BaseSandbox:
        """获取或创建沙箱"""
        if sandbox_id in self._sandboxes:
            return self._sandboxes[sandbox_id]

        config = config or self.default_config
        sandbox = self._create_sandbox(config)
        await sandbox.setup()
        self._sandboxes[sandbox_id] = sandbox
        return sandbox

    def _create_sandbox(self, config: SandboxConfig) -> BaseSandbox:
        """创建沙箱实例"""
        if config.type == SandboxType.DOCKER:
            from .docker_sandbox import DockerSandbox
            return DockerSandbox(config)
        elif config.type == SandboxType.PROCESS:
            from .process_sandbox import ProcessSandbox
            return ProcessSandbox(config)
        else:
            from .inprocess_sandbox import InProcessSandbox
            return InProcessSandbox(config)

    async def release_sandbox(self, sandbox_id: str) -> None:
        """释放沙箱"""
        if sandbox_id in self._sandboxes:
            await self._sandboxes[sandbox_id].cleanup()
            del self._sandboxes[sandbox_id]
```

### 3.2 Process Sandbox (开发/测试用)

```python
# cape/runtime/sandbox/process_sandbox.py

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from .manager import BaseSandbox, SandboxConfig, ExecutionRequest, ExecutionResponse


class ProcessSandbox(BaseSandbox):
    """
    子进程沙箱 - 在独立子进程中执行代码

    特点:
    - 进程级隔离
    - 支持超时控制
    - 支持资源限制 (通过 resource 模块)
    - 适合开发和测试环境
    """

    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        self.work_dir: Optional[Path] = None
        self.venv_dir: Optional[Path] = None
        self._installed_packages: set = set()

    async def setup(self) -> None:
        """创建工作目录和虚拟环境"""
        # 创建临时工作目录
        self.work_dir = Path(tempfile.mkdtemp(prefix="cape_sandbox_"))

        # 创建虚拟环境 (可选，提升隔离性)
        self.venv_dir = self.work_dir / "venv"

        # 预安装基础包
        if self.config.pre_installed_packages:
            await self.install_packages(self.config.pre_installed_packages)

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """在子进程中执行代码"""
        import time
        start_time = time.time()

        try:
            # 准备执行脚本
            exec_script = self._prepare_script(request)
            script_path = self.work_dir / "_exec.py"
            script_path.write_text(exec_script, encoding="utf-8")

            # 写入输入文件
            if request.files:
                for filename, content in request.files.items():
                    file_path = self.work_dir / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(content)

            # 准备环境变量
            env = {
                "PYTHONPATH": str(self.work_dir),
                **(request.env or {})
            }

            # 执行
            process = await asyncio.create_subprocess_exec(
                "python", str(script_path),
                cwd=str(self.work_dir),
                env={**dict(os.environ), **env},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                return ExecutionResponse(
                    success=False,
                    error=f"Execution timeout ({self.config.timeout_seconds}s)",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            # 解析输出
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # 尝试解析 JSON 结果
            output = None
            result_file = self.work_dir / "_result.json"
            if result_file.exists():
                output = json.loads(result_file.read_text())

            # 收集创建的文件
            files_created = self._collect_output_files(request)

            return ExecutionResponse(
                success=process.returncode == 0,
                output=output,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode,
                execution_time_ms=(time.time() - start_time) * 1000,
                files_created=files_created,
                error=stderr_str if process.returncode != 0 else None,
            )

        except Exception as e:
            return ExecutionResponse(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _prepare_script(self, request: ExecutionRequest) -> str:
        """准备执行脚本"""
        # 包装脚本，捕获结果
        wrapper = '''
import json
import sys
from pathlib import Path

# 设置参数
args = {args}

# 执行用户代码
try:
{code}

    # 保存结果
    if 'result' in dir():
        Path("_result.json").write_text(json.dumps(result, default=str))
except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)
    sys.exit(1)
'''

        # 获取代码
        if request.script_path:
            code = request.script_path.read_text()
        elif request.code:
            code = request.code
        else:
            code = "result = None"

        # 缩进代码
        indented_code = "\n".join("    " + line for line in code.split("\n"))

        return wrapper.format(
            args=json.dumps(request.args or {}),
            code=indented_code
        )

    async def install_packages(self, packages: list[str]) -> bool:
        """安装 Python 包"""
        new_packages = [p for p in packages if p not in self._installed_packages]
        if not new_packages:
            return True

        try:
            process = await asyncio.create_subprocess_exec(
                "pip", "install", *new_packages,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

            if process.returncode == 0:
                self._installed_packages.update(new_packages)
                return True
            return False
        except Exception:
            return False

    def _collect_output_files(self, request: ExecutionRequest) -> Dict[str, bytes]:
        """收集输出文件"""
        files = {}
        # 收集非临时文件
        for path in self.work_dir.rglob("*"):
            if path.is_file() and not path.name.startswith("_"):
                rel_path = path.relative_to(self.work_dir)
                # 跳过输入文件
                if request.files and str(rel_path) in request.files:
                    continue
                files[str(rel_path)] = path.read_bytes()
        return files

    async def cleanup(self) -> None:
        """清理工作目录"""
        if self.work_dir and self.work_dir.exists():
            shutil.rmtree(self.work_dir)
```

### 3.3 Docker Sandbox (生产推荐)

```python
# cape/runtime/sandbox/docker_sandbox.py

import asyncio
import json
import docker
from pathlib import Path
from .manager import BaseSandbox, SandboxConfig, ExecutionRequest, ExecutionResponse


class DockerSandbox(BaseSandbox):
    """
    Docker 容器沙箱 - 完全隔离的执行环境

    特点:
    - 容器级隔离 (文件系统、网络、进程)
    - 资源限制 (CPU、内存)
    - 可复现环境
    - 适合生产环境
    """

    # 预构建的基础镜像
    BASE_IMAGE = "cape-sandbox:python3.11"

    # 基础 Dockerfile
    DOCKERFILE = '''
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    libreoffice-calc \\
    && rm -rf /var/lib/apt/lists/*

# 安装常用 Python 包
RUN pip install --no-cache-dir \\
    openpyxl pandas numpy \\
    python-docx python-pptx \\
    pdfplumber reportlab PyPDF2 \\
    pillow requests

WORKDIR /workspace
'''

    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        self.client = docker.from_env()
        self.container = None
        self.work_dir: Optional[Path] = None

    async def setup(self) -> None:
        """创建 Docker 容器"""
        import tempfile

        # 确保镜像存在
        await self._ensure_image()

        # 创建本地工作目录
        self.work_dir = Path(tempfile.mkdtemp(prefix="cape_docker_"))

        # 启动容器
        self.container = self.client.containers.run(
            self.BASE_IMAGE,
            command="tail -f /dev/null",  # 保持运行
            detach=True,
            volumes={
                str(self.work_dir): {"bind": "/workspace", "mode": "rw"}
            },
            mem_limit=f"{self.config.max_memory_mb}m",
            cpu_period=100000,
            cpu_quota=int(self.config.max_cpu_percent * 1000),
            network_mode="none" if not self.config.network_enabled else "bridge",
        )

    async def _ensure_image(self) -> None:
        """确保基础镜像存在"""
        try:
            self.client.images.get(self.BASE_IMAGE)
        except docker.errors.ImageNotFound:
            # 构建镜像
            import io
            dockerfile = io.BytesIO(self.DOCKERFILE.encode())
            self.client.images.build(
                fileobj=dockerfile,
                tag=self.BASE_IMAGE,
            )

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """在容器中执行代码"""
        import time
        start_time = time.time()

        try:
            # 写入文件到工作目录
            if request.script_path:
                script_content = request.script_path.read_text()
                (self.work_dir / "script.py").write_text(script_content)
            elif request.code:
                (self.work_dir / "script.py").write_text(request.code)

            if request.files:
                for filename, content in request.files.items():
                    file_path = self.work_dir / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(content)

            # 写入参数
            (self.work_dir / "_args.json").write_text(
                json.dumps(request.args or {})
            )

            # 执行
            exec_result = self.container.exec_run(
                ["python", "/workspace/script.py"],
                workdir="/workspace",
                environment=request.env or {},
                demux=True,
            )

            stdout = exec_result.output[0] or b""
            stderr = exec_result.output[1] or b""

            # 读取结果
            output = None
            result_file = self.work_dir / "_result.json"
            if result_file.exists():
                output = json.loads(result_file.read_text())

            # 收集输出文件
            files_created = {}
            for path in self.work_dir.rglob("*"):
                if path.is_file() and not path.name.startswith("_"):
                    rel_path = path.relative_to(self.work_dir)
                    if request.files and str(rel_path) in request.files:
                        continue
                    files_created[str(rel_path)] = path.read_bytes()

            return ExecutionResponse(
                success=exec_result.exit_code == 0,
                output=output,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=exec_result.exit_code,
                execution_time_ms=(time.time() - start_time) * 1000,
                files_created=files_created,
            )

        except Exception as e:
            return ExecutionResponse(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    async def install_packages(self, packages: list[str]) -> bool:
        """在容器中安装包"""
        if not self.container:
            return False

        exec_result = self.container.exec_run(
            ["pip", "install"] + packages
        )
        return exec_result.exit_code == 0

    async def cleanup(self) -> None:
        """停止并删除容器"""
        if self.container:
            self.container.stop()
            self.container.remove()

        if self.work_dir and self.work_dir.exists():
            import shutil
            shutil.rmtree(self.work_dir)
```

### 3.4 增强版 CodeExecutor

```python
# cape/runtime/executors/code_executor.py

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from cape.runtime.context import ExecutionContext, ExecutionResult
from cape.runtime.sandbox.manager import (
    SandboxManager,
    SandboxConfig,
    SandboxType,
    ExecutionRequest,
)

logger = logging.getLogger(__name__)


class EnhancedCodeExecutor:
    """
    增强版代码执行器

    支持:
    - 多种沙箱模式 (Docker/Process/InProcess)
    - scripts/ 目录执行
    - 依赖自动安装
    - 文件 I/O
    - 超时与资源限制
    """

    def __init__(
        self,
        sandbox_type: SandboxType = SandboxType.PROCESS,
        sandbox_config: Optional[SandboxConfig] = None,
    ):
        self.sandbox_type = sandbox_type
        self.sandbox_config = sandbox_config or SandboxConfig(type=sandbox_type)
        self.sandbox_manager = SandboxManager(self.sandbox_config)

        # 预装的包 (document skills 需要)
        self.default_packages = [
            "openpyxl", "pandas", "numpy",
            "python-docx", "python-pptx",
            "pdfplumber", "reportlab", "PyPDF2",
        ]

    async def execute(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """执行 Cape 代码"""
        import time
        start_time = time.time()

        try:
            # 获取沙箱
            sandbox_id = f"{cape.id}_{context.trace_id}"
            sandbox = await self.sandbox_manager.get_sandbox(
                sandbox_id,
                self._build_sandbox_config(cape)
            )

            # 安装依赖
            dependencies = self._get_dependencies(cape)
            if dependencies:
                await sandbox.install_packages(dependencies)

            # 准备执行请求
            request = self._build_execution_request(cape, inputs, context)

            # 执行
            response = await sandbox.execute(request)

            # 处理输出文件
            if response.files_created:
                context.set("output_files", response.files_created)

            return ExecutionResult(
                success=response.success,
                output=response.output or response.stdout,
                error=response.error,
                execution_time_ms=response.execution_time_ms,
                metadata={
                    "stdout": response.stdout,
                    "stderr": response.stderr,
                    "exit_code": response.exit_code,
                    "files_created": list(response.files_created.keys()) if response.files_created else [],
                }
            )

        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        finally:
            # 清理沙箱 (可选保留以复用)
            # await self.sandbox_manager.release_sandbox(sandbox_id)
            pass

    def _build_sandbox_config(self, cape: "Cape") -> SandboxConfig:
        """根据 Cape 构建沙箱配置"""
        config = SandboxConfig(
            type=self.sandbox_type,
            timeout_seconds=cape.execution.timeout_seconds,
        )

        # 从 Cape 元数据获取配置
        if cape.model_adapters.get("code"):
            code_config = cape.model_adapters["code"]
            if "memory_mb" in code_config:
                config.max_memory_mb = code_config["memory_mb"]
            if "network" in code_config:
                config.network_enabled = code_config["network"]

        return config

    def _get_dependencies(self, cape: "Cape") -> list[str]:
        """获取 Cape 依赖"""
        deps = set(self.default_packages)

        # 从 Cape 配置获取
        if cape.model_adapters.get("code"):
            code_config = cape.model_adapters["code"]
            if "dependencies" in code_config:
                deps.update(code_config["dependencies"])

        # 从元数据获取
        if hasattr(cape, "metadata") and hasattr(cape.metadata, "dependencies"):
            deps.update(cape.metadata.dependencies or [])

        return list(deps)

    def _build_execution_request(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionRequest:
        """构建执行请求"""
        request = ExecutionRequest(args=inputs)

        # 代码来源优先级: entrypoint > code > model_adapters.code
        cape_path = getattr(cape, "_path", None)

        if cape.execution.entrypoint and cape_path:
            # 从 scripts/ 加载
            script_path = cape_path / cape.execution.entrypoint
            if script_path.exists():
                request.script_path = script_path
                # 同时加载同目录的其他脚本
                scripts_dir = script_path.parent
                request.files = {}
                for f in scripts_dir.glob("*.py"):
                    if f != script_path:
                        request.files[f.name] = f.read_bytes()

        elif cape.execution.code:
            request.code = cape.execution.code

        elif cape.model_adapters.get("code"):
            code_config = cape.model_adapters["code"]
            if "script" in code_config:
                request.code = code_config["script"]

        # 添加输入文件
        input_files = inputs.get("_files", {})
        if input_files:
            request.files = request.files or {}
            request.files.update(input_files)

        return request
```

## 4. Skill 导入增强

```python
# cape/importers/skill_enhanced.py

from pathlib import Path
from typing import Dict, Any, List, Optional
from cape.core.models import Cape, CapeExecution, ExecutionType
from cape.importers.skill import SkillImporter


class EnhancedSkillImporter(SkillImporter):
    """
    增强版 Skill 导入器

    新增功能:
    - 完整 scripts/ 导入
    - 依赖检测
    - 执行类型推断
    """

    def _build_cape(
        self,
        skill_path: Path,
        frontmatter: Dict[str, Any],
        body: str,
    ) -> Cape:
        """构建 Cape，增强代码执行支持"""

        # 调用基类构建
        cape = super()._build_cape(skill_path, frontmatter, body)

        # 检测并增强代码执行配置
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            # 发现所有脚本
            scripts = list(scripts_dir.glob("*.py"))

            if scripts:
                # 设置执行类型
                cape.execution.type = ExecutionType.HYBRID

                # 设置主入口点
                main_scripts = [s for s in scripts if s.stem in ("main", "run", "execute")]
                if main_scripts:
                    cape.execution.entrypoint = f"scripts/{main_scripts[0].name}"
                else:
                    cape.execution.entrypoint = f"scripts/{scripts[0].name}"

                # 检测依赖
                dependencies = self._detect_dependencies(scripts)

                # 添加代码适配器
                cape.model_adapters["code"] = {
                    "scripts": [f"scripts/{s.name}" for s in scripts],
                    "dependencies": dependencies,
                    "entrypoint": cape.execution.entrypoint,
                }

        return cape

    def _detect_dependencies(self, scripts: List[Path]) -> List[str]:
        """从脚本中检测依赖"""
        import re

        dependencies = set()

        # 常见包映射
        package_map = {
            "openpyxl": "openpyxl",
            "pandas": "pandas",
            "numpy": "numpy",
            "docx": "python-docx",
            "pptx": "python-pptx",
            "pdfplumber": "pdfplumber",
            "reportlab": "reportlab",
            "PyPDF2": "PyPDF2",
            "PIL": "pillow",
            "cv2": "opencv-python",
        }

        for script in scripts:
            content = script.read_text()

            # 匹配 import 语句
            imports = re.findall(r'^(?:from|import)\s+(\w+)', content, re.MULTILINE)

            for imp in imports:
                if imp in package_map:
                    dependencies.add(package_map[imp])

        return list(dependencies)
```

## 5. 使用示例

### 5.1 导入 Document Skills

```python
from cape.importers.skill_enhanced import EnhancedSkillImporter
from cape.registry import CapeRegistry

# 克隆 anthropics/skills 仓库后
importer = EnhancedSkillImporter()

# 导入 document skills
xlsx_cape = importer.import_skill(Path("./anthropic-skills/skills/xlsx"))
docx_cape = importer.import_skill(Path("./anthropic-skills/skills/docx"))
pptx_cape = importer.import_skill(Path("./anthropic-skills/skills/pptx"))
pdf_cape = importer.import_skill(Path("./anthropic-skills/skills/pdf"))

# 注册到 Registry
registry = CapeRegistry()
registry.register(xlsx_cape)
registry.register(docx_cape)
registry.register(pptx_cape)
registry.register(pdf_cape)
```

### 5.2 执行 Document Cape

```python
from cape.runtime import CapeRuntime
from cape.runtime.executors.code_executor import EnhancedCodeExecutor
from cape.runtime.sandbox.manager import SandboxType

# 创建运行时
runtime = CapeRuntime(registry=registry)

# 替换默认的 CodeExecutor
runtime._executors[ExecutionType.CODE] = EnhancedCodeExecutor(
    sandbox_type=SandboxType.DOCKER  # 生产环境
)
runtime._executors[ExecutionType.HYBRID] = HybridExecutor(
    code_executor=runtime._executors[ExecutionType.CODE],
    ...
)

# 执行 Excel 处理
result = await runtime.execute(
    "xlsx-handler",
    inputs={
        "_files": {
            "input.xlsx": xlsx_bytes,
        },
        "task": "分析销售数据并生成图表",
    }
)

# 获取输出文件
if result.success:
    output_files = result.metadata.get("files_created", {})
    output_xlsx = output_files.get("output.xlsx")
```

## 6. 安全考量

### 6.1 沙箱隔离级别

| 级别 | 实现方式 | 隔离能力 | 适用场景 |
|------|---------|---------|---------|
| L1 | InProcess | 无 | 开发调试 |
| L2 | Process | 进程隔离 | 开发测试 |
| L3 | Docker | 容器隔离 | 生产环境 |
| L4 | gVisor/Firecracker | 内核隔离 | 高安全需求 |

### 6.2 安全策略

```python
@dataclass
class SecurityPolicy:
    """安全策略"""

    # 文件系统
    allow_file_read: bool = True
    allow_file_write: bool = True
    allowed_paths: List[str] = None  # 白名单路径

    # 网络
    allow_network: bool = False
    allowed_hosts: List[str] = None

    # 系统调用
    allow_subprocess: bool = False
    allow_env_access: bool = False

    # 资源
    max_execution_time: int = 30
    max_memory_mb: int = 512
    max_output_size_mb: int = 10
```

## 7. 实施路线

```
Week 1: 基础框架
├── ProcessSandbox 实现
├── EnhancedCodeExecutor 实现
├── EnhancedSkillImporter 实现
└── 单元测试

Week 2: Document Skills 集成
├── 克隆 anthropics/skills
├── 导入 4 个 document skills
├── 创建 document-pack
└── 端到端测试

Week 3: Docker 沙箱
├── DockerSandbox 实现
├── 基础镜像构建
├── 资源限制测试
└── 性能优化

Week 4: API 与前端
├── 文件上传 API
├── 文件下载 API
├── 前端文件处理 UI
└── 集成测试
```

## 8. 依赖清单

```
# 基础依赖
docker>=6.0.0        # Docker SDK
asyncio              # 异步执行

# Document Skills 依赖 (预装在沙箱中)
openpyxl>=3.1.0      # Excel
pandas>=2.0.0        # 数据处理
python-docx>=0.8.0   # Word
python-pptx>=0.6.0   # PowerPoint
pdfplumber>=0.9.0    # PDF 读取
reportlab>=4.0.0     # PDF 生成
PyPDF2>=3.0.0        # PDF 处理

# 可选 (xlsx 公式重算)
libreoffice          # 系统安装
```

## 9. 文件上传/下载 API

### 9.1 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/files/upload` | POST | 上传文件 |
| `/api/files/{file_id}` | GET | 下载文件 |
| `/api/files/{file_id}/metadata` | GET | 获取文件元数据 |
| `/api/files/{file_id}` | DELETE | 删除文件 |
| `/api/files/session/{session_id}` | GET | 列出会话文件 |
| `/api/files/session/{session_id}` | DELETE | 删除会话所有文件 |
| `/api/files/{file_id}/process` | POST | 使用 Cape 处理文件 |
| `/api/files/batch/process` | POST | 批量处理文件 |
| `/api/files/stats` | GET | 获取存储统计 |

### 9.2 文件存储管理

```python
# api/storage.py

class FileStorage:
    """文件存储管理器"""

    async def upload(content, filename, session_id, cape_id) -> FileMetadata
    async def download(file_id) -> Tuple[bytes, FileMetadata]
    async def save_output(content, filename, session_id, source_file_id) -> FileMetadata
    async def list_session_files(session_id) -> List[FileMetadata]
    async def delete_file(file_id) -> bool
    async def cleanup_expired() -> int
```

### 9.3 支持的文件类型

- **文档**: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, ODS, ODP
- **文本**: TXT, MD, CSV, TSV, JSON, XML, YAML
- **图片**: PNG, JPG, JPEG, GIF, BMP, WebP, SVG
- **压缩**: ZIP, TAR, GZ

### 9.4 文件处理流程

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   Upload   │────▶│   Store    │────▶│  Process   │────▶│  Download  │
│   File     │     │  (session) │     │  (Cape)    │     │   Output   │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
     │                   │                  │                  │
     ▼                   ▼                  ▼                  ▼
 POST /upload      FileStorage      POST /process      GET /{file_id}
 multipart/form    .cape_storage/   sandbox exec       Content-Disposition
```

### 9.5 使用示例

```bash
# 上传文件
curl -X POST http://localhost:8000/api/files/upload \
  -F "files=@data.xlsx" \
  -F "session_id=session-123"

# 使用 Cape 处理
curl -X POST http://localhost:8000/api/files/{file_id}/process \
  -H "Content-Type: application/json" \
  -d '{"cape_id": "xlsx", "inputs": {"task": "分析销售数据"}}'

# 下载结果
curl -O http://localhost:8000/api/files/{output_file_id}
```
