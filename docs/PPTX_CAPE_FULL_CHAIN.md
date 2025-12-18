# PPTX Cape 全链路实现详解

> 以 PowerPoint 演示文稿处理能力为例，展示从用户请求到文件输出的完整执行链路。

## 链路概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户交互层                                      │
│  [用户输入: "帮我创建一份关于AI的PPT"] + [上传模板文件]                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端处理                                        │
│  ChatInput → 文件上传 → API 请求                                            │
│  web/src/components/chat/input.tsx                                          │
│  web/src/lib/api.ts                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API 网关                                        │
│  POST /api/chat (SSE) + POST /api/files/upload                              │
│  api/routes/chat.py + api/routes/files.py                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              能力匹配                                        │
│  CapeRegistry.match("创建PPT") → pptx (score: 0.85)                         │
│  cape/registry/registry.py + cape/registry/matcher.py                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LLM Agent                                       │
│  加载 pptx 的 system_prompt → 规划执行步骤                                    │
│  cape/agent/langchain.py                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              代码执行                                        │
│  SandboxManager → ProcessSandbox/DockerSandbox                              │
│  执行 scripts/inventory.py, rearrange.py, replace.py                         │
│  cape/runtime/sandbox/                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              文件输出                                        │
│  FileStorage.save_output() → /storage/outputs/{session_id}/                 │
│  api/storage.py                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              结果返回                                        │
│  SSE Event: cape_end → content → done                                       │
│  前端展示生成的 PPT 下载链接                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 第一层：Cape 定义

### 文件位置
```
packs/document-pack/capes/pptx.yaml
```

### 核心结构

```yaml
id: pptx
name: PowerPoint 演示文稿处理
version: "1.0.0"

# 1. 元数据 - 用于匹配和展示
metadata:
  tags: [powerpoint, presentation, pptx, slides]
  intents:
    - 创建PPT
    - 编辑演示文稿
    - 制作幻灯片

# 2. 接口定义 - 输入输出规范
interface:
  input_schema:
    type: object
    properties:
      task: { type: string }
      file_path: { type: string }
      template_path: { type: string }
  output_schema:
    type: object
    properties:
      output_file: { type: string }

# 3. 执行配置 - 运行时行为
execution:
  type: hybrid          # LLM + 代码混合执行
  entrypoint: scripts/inventory.py
  timeout_seconds: 180
  tools_allowed: [file_read, file_write, code_execute, bash]

# 4. 模型适配器 - 多模型支持
model_adapters:
  claude:
    system_prompt: |
      你是 PowerPoint 演示文稿处理专家...
  openai:
    system_prompt: |
      You are a PowerPoint presentation expert...

# 5. 代码适配器 - 脚本和依赖
code_adapter:
  scripts:
    - scripts/thumbnail.py    # 生成缩略图
    - scripts/rearrange.py    # 重排幻灯片
    - scripts/inventory.py    # 提取文本清单
    - scripts/replace.py      # 替换文本
  dependencies:
    - python-pptx
    - pillow
    - defusedxml
```

---

## 第二层：前端交互

### 2.1 文件上传组件

```typescript
// web/src/components/chat/file-attachment.tsx

export function FileDropZone({ onFilesSelected }) {
  const handleDrop = (e: React.DragEvent) => {
    const files = Array.from(e.dataTransfer.files);
    onFilesSelected(files);  // 触发上传
  };
  // ...
}
```

### 2.2 聊天输入处理

```typescript
// web/src/components/chat/input.tsx

const handleFileSelect = async (e) => {
  const files = Array.from(e.target.files);

  // 1. 显示上传进度
  setPendingFiles(files.map(f => ({ file: f, progress: 0 })));

  // 2. 调用上传 API
  const response = await api.uploadFiles(files, sessionId);

  // 3. 更新已上传文件列表
  setUploadedFiles(response.files);
};

const handleSubmit = () => {
  // 发送消息时附带文件信息
  onSend(value, uploadedFiles);
};
```

### 2.3 API 客户端

```typescript
// web/src/lib/api.ts

class ApiClient {
  // 上传文件
  async uploadFiles(files: File[], sessionId?: string): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach(f => formData.append("files", f));
    if (sessionId) formData.append("session_id", sessionId);

    const res = await fetch(`${this.baseUrl}/api/files/upload`, {
      method: "POST",
      body: formData,
    });
    return res.json();
  }

  // 流式聊天
  async *chat(message: string, model: string): AsyncGenerator<ChatEvent> {
    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, model, stream: true }),
    });

    // 解析 SSE 事件流
    const reader = res.body.getReader();
    // ... 解析 event: xxx, data: xxx
  }
}
```

---

## 第三层：API 处理

### 3.1 文件上传端点

```python
# api/routes/files.py

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    cape_id: Optional[str] = Form(None),
):
    """上传文件到服务器"""
    storage = get_storage()

    # 生成或使用现有 session_id
    session_id = session_id or str(uuid4())

    uploaded = []
    for file in files:
        # 验证文件类型和大小
        validate_file(file)

        # 保存文件
        metadata = await storage.save_upload(
            file=file,
            session_id=session_id,
            cape_id=cape_id,
        )
        uploaded.append(metadata)

    return UploadResponse(
        files=[FileResponse.from_metadata(m) for m in uploaded],
        session_id=session_id,
    )
```

### 3.2 聊天端点 (SSE)

```python
# api/routes/chat.py

@router.post("")
async def chat(request: ChatRequest):
    """处理聊天请求，支持 SSE 流式响应"""

    if request.stream:
        return StreamingResponse(
            generate_sse_events(
                message=request.message,
                model=request.model,
                session_id=request.session_id,
            ),
            media_type="text/event-stream",
        )
    else:
        # 非流式响应
        return await process_chat_sync(request)


async def generate_sse_events(message, model, session_id):
    """生成 SSE 事件流"""

    # 1. 发送 session 事件
    yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"

    # 2. 创建 Agent 并执行
    agent = create_agent(model)

    async for event in agent.astream_events(message):
        if event["event"] == "on_tool_start":
            # 3. 发送 cape_start 事件
            cape_id = event["name"].replace("cape_", "")
            yield f"event: cape_start\ndata: {json.dumps({'cape_id': cape_id})}\n\n"

        elif event["event"] == "on_tool_end":
            # 4. 发送 cape_end 事件
            yield f"event: cape_end\ndata: {json.dumps({'duration_ms': ...})}\n\n"

        elif event["event"] == "on_chat_model_stream":
            # 5. 发送 content 事件
            content = event["data"]["chunk"].content
            yield f"event: content\ndata: {json.dumps({'text': content})}\n\n"

    # 6. 发送 done 事件
    yield f"event: done\ndata: {json.dumps({'total_duration_ms': ...})}\n\n"
```

---

## 第四层：能力匹配

### 4.1 Registry 加载 Cape

```python
# cape/registry/registry.py

class CapeRegistry:
    def __init__(self, packs_dir):
        self._capes = {}
        self._load_packs_dir(packs_dir)

    def _load_packs_dir(self, packs_dir):
        """加载 packs/document-pack/"""
        for pack_path in packs_dir.iterdir():
            pack_file = pack_path / "pack.yaml"
            if pack_file.exists():
                self._load_pack(pack_path, pack_file)

    def _load_pack(self, pack_path, pack_file):
        """加载单个 Pack"""
        # 加载 pack.yaml
        pack_data = yaml.safe_load(pack_file.read_text())

        # 加载 capes/ 目录下的所有 Cape
        capes_dir = pack_path / "capes"
        for cape_file in capes_dir.glob("*.yaml"):
            cape = Cape.from_dict(yaml.safe_load(cape_file.read_text()))
            self.register(cape)  # 注册 pptx cape
```

### 4.2 意图匹配

```python
# cape/registry/matcher.py

class CapeMatcher:
    def match(self, query: str, top_k: int = 5) -> List[Dict]:
        """匹配用户意图到 Cape"""

        results = []
        for cape in self.capes:
            score = 0.0

            # 1. 关键词匹配 (intents)
            for intent in cape.metadata.intents:
                if intent in query:
                    score += 0.5

            # 2. 标签匹配 (tags)
            for tag in cape.metadata.tags:
                if tag in query.lower():
                    score += 0.3

            # 3. 示例匹配 (examples)
            for example in cape.metadata.examples:
                similarity = self._compute_similarity(query, example)
                score += similarity * 0.2

            if score > 0:
                results.append({"cape": cape, "score": score})

        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
```

**匹配示例**：

| 用户输入 | 匹配结果 | 分数 |
|----------|----------|------|
| "创建一份PPT" | pptx | 0.85 |
| "帮我做演示文稿" | pptx | 0.75 |
| "制作幻灯片" | pptx | 0.80 |

---

## 第五层：LLM Agent

### 5.1 Agent 创建

```python
# cape/agent/langchain.py

def create_langchain_agent(capes_dir, llm):
    """创建 LangChain Agent"""

    # 1. 加载 Registry
    registry = CapeRegistry(packs_dir=capes_dir)

    # 2. 将 Cape 转换为 LangChain Tool
    tools = []
    for cape in registry.all():
        tool = create_cape_tool(cape)
        tools.append(tool)

    # 3. 创建 Agent
    agent = create_tool_calling_agent(llm, tools)
    return AgentExecutor(agent=agent, tools=tools)


def create_cape_tool(cape: Cape):
    """将 Cape 转换为 LangChain Tool"""

    # 获取对应模型的 system_prompt
    adapter = cape.model_adapters.get("openai", {})
    system_prompt = adapter.get("system_prompt", "")

    @tool(name=f"cape_{cape.id}")
    async def cape_tool(task: str, **kwargs):
        """执行 Cape"""
        # 使用沙箱执行代码
        return await execute_cape(cape, task, kwargs)

    cape_tool.__doc__ = f"{cape.description}\n\n{system_prompt}"
    return cape_tool
```

### 5.2 Agent 执行流程

```
用户: "帮我创建一份关于AI的PPT，包含5页"

Agent 思考:
1. 分析任务 → 需要创建 PPT
2. 搜索可用工具 → 找到 cape_pptx
3. 读取 system_prompt → 了解工作流程
4. 规划步骤:
   - 使用 html2pptx 工作流
   - 创建 5 张幻灯片的 HTML
   - 转换为 PPTX

Agent 调用:
tool: cape_pptx
args: {
  "task": "创建关于AI的5页演示文稿",
  "content": {
    "title": "人工智能简介",
    "slides": [...]
  }
}
```

---

## 第六层：沙箱执行

### 6.1 沙箱管理器

```python
# cape/runtime/sandbox/manager.py

class SandboxManager:
    async def create(self, config: SandboxConfig) -> BaseSandbox:
        """根据配置创建合适的沙箱"""

        if config.type == SandboxType.DOCKER:
            return DockerSandbox(config)
        elif config.type == SandboxType.PROCESS:
            return ProcessSandbox(config)
        else:
            return InProcessSandbox(config)

    async def execute(self, cape: Cape, inputs: dict) -> ExecutionResponse:
        """执行 Cape 代码"""

        # 1. 创建沙箱
        config = SandboxConfig(
            type=SandboxType.PROCESS,
            timeout_seconds=cape.execution.timeout_seconds,
        )
        sandbox = await self.create(config)

        # 2. 安装依赖
        await sandbox.install_packages(cape.code_adapter.dependencies)

        # 3. 执行代码
        request = ExecutionRequest(
            code=self._build_execution_code(cape, inputs),
            inputs=inputs,
        )
        response = await sandbox.execute(request)

        # 4. 清理
        await sandbox.cleanup()

        return response
```

### 6.2 ProcessSandbox 执行

```python
# cape/runtime/sandbox/process_sandbox.py

class ProcessSandbox(BaseSandbox):
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """在子进程中执行代码"""

        # 1. 准备工作目录
        work_dir = self._create_work_dir()

        # 2. 写入代码和输入
        code_file = work_dir / "_exec.py"
        code_file.write_text(self._wrap_code(request.code))

        args_file = work_dir / "_args.json"
        args_file.write_text(json.dumps(request.inputs))

        # 3. 启动子进程
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(code_file),
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # 4. 等待完成（带超时）
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            return ExecutionResponse(success=False, error="Timeout")

        # 5. 读取结果
        result_file = work_dir / "_result.json"
        if result_file.exists():
            result = json.loads(result_file.read_text())
            return ExecutionResponse(success=True, output=result)

        return ExecutionResponse(success=False, error=stderr.decode())
```

### 6.3 DockerSandbox 执行 (生产环境)

```python
# cape/runtime/sandbox/docker_sandbox.py

class DockerSandbox(BaseSandbox):
    DOCKERFILE = '''
    FROM python:3.11-slim
    RUN pip install python-pptx pillow defusedxml
    '''

    async def setup(self):
        """启动 Docker 容器"""
        self.container = self.client.containers.run(
            image="cape-sandbox:python3.11",
            detach=True,
            volumes={self.work_dir: {"bind": "/workspace"}},
            mem_limit="512m",
            network_mode="none",  # 禁用网络
        )

    async def execute(self, request):
        """在容器中执行"""
        # 写入代码到 /workspace/_exec.py
        # 执行 container.exec_run()
        # 读取 /workspace/_result.json
```

---

## 第七层：PPTX 脚本执行

### 7.1 脚本功能

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `thumbnail.py` | 生成幻灯片缩略图 | .pptx | .png 文件 |
| `inventory.py` | 提取所有文本 | .pptx | .json 清单 |
| `rearrange.py` | 复制/重排幻灯片 | .pptx + 序列 | .pptx |
| `replace.py` | 批量替换文本 | .pptx + .json | .pptx |

### 7.2 执行示例：基于模板创建

```python
# Agent 生成的执行代码

import subprocess
import json

# 步骤 1: 生成模板缩略图
subprocess.run([
    "python", "scripts/thumbnail.py",
    "template.pptx"
])

# 步骤 2: 提取文本清单
subprocess.run([
    "python", "scripts/inventory.py",
    "template.pptx", "text-inventory.json"
])

# 步骤 3: 重排幻灯片 (选择 0, 3, 5, 7 号)
subprocess.run([
    "python", "scripts/rearrange.py",
    "template.pptx", "working.pptx", "0,3,5,7"
])

# 步骤 4: 准备替换内容
replacements = {
    "{{title}}": "人工智能简介",
    "{{subtitle}}": "AI 技术概览",
    "{{bullet1}}": "机器学习基础",
    # ...
}
with open("replacement.json", "w") as f:
    json.dump(replacements, f)

# 步骤 5: 应用替换
subprocess.run([
    "python", "scripts/replace.py",
    "working.pptx", "replacement.json", "output.pptx"
])

# 返回结果
result = {"output_file": "output.pptx", "slides": 4}
```

### 7.3 html2pptx 工作流（无模板）

```python
# Agent 生成的 HTML 转 PPTX 代码

from pptx import Presentation
from pptx.util import Inches, Pt

# 创建演示文稿
prs = Presentation()

# 幻灯片 1: 标题页
slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白布局
title = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(1))
title.text_frame.paragraphs[0].text = "人工智能简介"
title.text_frame.paragraphs[0].font.size = Pt(44)

# 幻灯片 2: 内容页
slide = prs.slides.add_slide(prs.slide_layouts[6])
# 双栏布局
left_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(4), Inches(4))
left_box.text = "机器学习\n• 监督学习\n• 无监督学习"

right_box = slide.shapes.add_textbox(Inches(5), Inches(1.5), Inches(4), Inches(4))
right_box.text = "深度学习\n• CNN\n• RNN"

# ... 更多幻灯片

# 保存
prs.save("output.pptx")
```

---

## 第八层：文件输出与返回

### 8.1 保存输出文件

```python
# api/storage.py

class FileStorage:
    async def save_output(
        self,
        content: bytes,
        filename: str,
        session_id: str,
        cape_id: str,
    ) -> FileMetadata:
        """保存 Cape 执行输出的文件"""

        # 生成文件 ID
        file_id = str(uuid4())

        # 保存到 outputs 目录
        output_dir = self.base_path / "outputs" / session_id
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / f"{file_id}_{filename}"
        file_path.write_bytes(content)

        # 创建元数据
        metadata = FileMetadata(
            file_id=file_id,
            original_name=filename,
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            size_bytes=len(content),
            status=FileStatus.COMPLETED,
            session_id=session_id,
            cape_id=cape_id,
            is_output=True,
        )

        # 保存元数据
        await self._save_metadata(metadata)

        return metadata
```

### 8.2 SSE 结果返回

```python
# api/routes/chat.py

async def generate_sse_events(...):
    # ... 执行完成后

    # 发送输出文件信息
    output_files = await get_output_files(session_id)

    yield f"""event: cape_end
data: {json.dumps({
    "cape_id": "pptx",
    "duration_ms": 3500,
    "output_files": [
        {
            "file_id": "abc123",
            "filename": "output.pptx",
            "download_url": "/api/files/abc123"
        }
    ]
})}

"""

    # 发送完成事件
    yield f"""event: done
data: {json.dumps({
    "total_duration_ms": 5000,
    "session_id": session_id
})}

"""
```

### 8.3 前端接收与展示

```typescript
// web/src/hooks/use-chat.ts

async function* processStream(response) {
  for await (const event of parseSSE(response)) {
    switch (event.type) {
      case "cape_end":
        // 更新消息，显示输出文件
        updateMessage({
          execution: {
            cape_id: event.cape_id,
            status: "completed",
            output_files: event.output_files,
          }
        });
        break;

      case "done":
        // 完成，显示下载按钮
        break;
    }
  }
}
```

```tsx
// web/src/components/chat/message.tsx

function MessageItem({ message }) {
  return (
    <div>
      {message.content}

      {message.execution?.output_files?.map(file => (
        <a
          key={file.file_id}
          href={`/api/files/${file.file_id}`}
          download={file.filename}
          className="flex items-center gap-2 p-2 bg-green-50 rounded"
        >
          <FileIcon />
          <span>{file.filename}</span>
          <DownloadIcon />
        </a>
      ))}
    </div>
  );
}
```

---

## 完整时序图

```
用户                前端              API                Registry          Agent             Sandbox           Storage
 │                   │                 │                   │                 │                 │                 │
 │ "创建AI的PPT"      │                 │                   │                 │                 │                 │
 │──────────────────>│                 │                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │ POST /api/chat  │                   │                 │                 │                 │
 │                   │────────────────>│                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │ match("创建PPT")   │                 │                 │                 │
 │                   │                 │──────────────────>│                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │ return pptx       │                 │                 │                 │
 │                   │                 │<──────────────────│                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │ create_agent()                      │                 │                 │
 │                   │                 │─────────────────────────────────────>                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │ SSE: session    │                   │                 │                 │                 │
 │                   │<────────────────│                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │                   │ call cape_pptx  │                 │                 │
 │                   │                 │                   │<────────────────│                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │ SSE: cape_start │                   │                 │                 │                 │
 │                   │<────────────────│                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │                   │                 │ execute()       │                 │
 │                   │                 │                   │                 │────────────────>│                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │ [运行 python-pptx]
 │                   │                 │                   │                 │                 │─────────────────│
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │                   │                 │ result          │                 │
 │                   │                 │                   │                 │<────────────────│                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │ save_output()   │
 │                   │                 │                   │                 │                 │────────────────>│
 │                   │                 │                   │                 │                 │                 │
 │                   │ SSE: cape_end   │                   │                 │                 │                 │
 │                   │<────────────────│                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │ SSE: content    │                   │                 │                 │                 │
 │                   │<────────────────│                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │ SSE: done       │                   │                 │                 │                 │
 │                   │<────────────────│                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │ 显示下载链接       │                 │                   │                 │                 │                 │
 │<──────────────────│                 │                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │ 点击下载           │                 │                   │                 │                 │                 │
 │──────────────────>│                 │                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │ GET /api/files/{id}                 │                 │                 │                 │
 │                   │────────────────>│                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │ get_file()      │
 │                   │                 │────────────────────────────────────────────────────────────────────────>│
 │                   │                 │                   │                 │                 │                 │
 │                   │ output.pptx     │                   │                 │                 │                 │
 │                   │<────────────────│                   │                 │                 │                 │
 │                   │                 │                   │                 │                 │                 │
 │ [保存文件]         │                 │                   │                 │                 │                 │
 │<──────────────────│                 │                 │                 │                 │                 │
```

---

## 关键文件清单

| 层级 | 文件 | 职责 |
|------|------|------|
| Cape 定义 | `packs/document-pack/capes/pptx.yaml` | 能力配置 |
| 前端输入 | `web/src/components/chat/input.tsx` | 用户交互 |
| 前端文件 | `web/src/components/chat/file-attachment.tsx` | 文件上传 |
| API 客户端 | `web/src/lib/api.ts` | HTTP 请求 |
| 聊天路由 | `api/routes/chat.py` | SSE 流处理 |
| 文件路由 | `api/routes/files.py` | 文件上传下载 |
| 能力注册 | `cape/registry/registry.py` | Cape 加载 |
| 意图匹配 | `cape/registry/matcher.py` | 查询匹配 |
| 沙箱管理 | `cape/runtime/sandbox/manager.py` | 沙箱创建 |
| 进程沙箱 | `cape/runtime/sandbox/process_sandbox.py` | 代码执行 |
| Docker沙箱 | `cape/runtime/sandbox/docker_sandbox.py` | 生产执行 |
| 文件存储 | `api/storage.py` | 文件管理 |

---

*文档生成时间: 2025-12-18*
