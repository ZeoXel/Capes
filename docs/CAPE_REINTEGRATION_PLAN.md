# Cape 能力回归 Agent Platform 方案

## 项目关系定位

```
Agent Platform (父)                    Cape/skillslike (子)
─────────────────────                  ─────────────────────
• 框架标准                              • 功能探索
• 前端 UI/UX                           • 能力实现
• 工作区架构                            • 沙箱执行
• 组件设计                              • 文档处理
                    ┌────────────┐
                    │   回归    │
                    │   ════►   │
                    └────────────┘
```

## 核心原则

```
1. 前端不动 - Agent Platform UI 保持现状
2. 能力增强 - Cape 能力注入 Agent Platform
3. 后端替换 - Cape 取代原 agent-v2 的简单实现
4. 渐进迁移 - 保持原有功能可用
```

---

## 回归架构

### 目标状态

```
┌─────────────────────────────────────────────────────────────┐
│              Agent Platform 前端 (不变)                      │
│         /workspace  /studio  /agent  ChatWindow             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Platform API Routes                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 /api/agent-v2  (升级)                  │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐  │  │
│  │  │ 图片工具    │ │ Cape 代理   │ │ 文件管理        │  │  │
│  │  │ (保留)     │ │ (新增)     │ │ (新增)          │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cape 后端服务                             │
│              (独立进程 / 或合并部署)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Registry │ │ Runtime  │ │ Sandbox  │ │ Storage  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 实施步骤

### Step 1: Cape 提供标准化工具接口

**位置**: `/Users/g/Desktop/探索/skillslike/api/routes/tools.py` (新建)

```python
"""
Tools API - OpenAI Function Calling 兼容接口
供 Agent Platform 直接调用
"""

from fastapi import APIRouter
from api.deps import get_registry, get_runtime

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/list")
def list_tools():
    """
    返回 OpenAI Function Calling 格式的工具列表
    Agent Platform 直接使用此格式注册工具
    """
    registry = get_registry()
    tools = []

    for cape in registry.all():
        tools.append({
            "type": "function",
            "function": {
                "name": f"cape_{cape.id.replace('-', '_')}",
                "description": cape.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "任务描述"
                        },
                        "file_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "关联的文件 ID 列表"
                        }
                    },
                    "required": ["task"]
                }
            },
            # 元信息供前端展示
            "meta": {
                "id": cape.id,
                "name": cape.name,
                "tags": cape.metadata.tags if cape.metadata else [],
                "icon": get_cape_icon(cape.id),
            }
        })

    return {"tools": tools, "count": len(tools)}


@router.post("/execute/{tool_name}")
async def execute_tool(tool_name: str, request: ToolExecuteRequest):
    """
    执行工具并返回结果
    统一的执行入口，屏蔽 Cape 内部细节
    """
    cape_id = tool_name.replace("cape_", "").replace("_", "-")
    runtime = get_runtime()

    result = await runtime.execute_async(
        cape_id=cape_id,
        inputs={"task": request.task},
        file_ids=request.file_ids,
        session_id=request.session_id,
    )

    return {
        "success": result.success,
        "output": result.output,
        "files": [
            {
                "file_id": f.file_id,
                "name": f.original_name,
                "url": f"/api/files/{f.file_id}",
                "type": f.content_type,
            }
            for f in result.output_files
        ] if result.output_files else [],
        "execution_time_ms": result.execution_time_ms,
    }


def get_cape_icon(cape_id: str) -> str:
    """返回 Cape 图标 (Lucide icon name)"""
    icons = {
        "xlsx": "table",
        "docx": "file-text",
        "pptx": "presentation",
        "pdf": "file-type",
    }
    return icons.get(cape_id, "box")
```

### Step 2: Agent Platform 动态加载 Cape 工具

**位置**: `/Users/g/Desktop/探索/Agent Platform/web/src/app/api/agent-v2/tools/cape-loader.js` (新建)

```javascript
/**
 * Cape 工具动态加载器
 * 从 Cape 后端获取工具配置，转换为本地格式
 */

const CAPE_API_URL = process.env.CAPE_API_URL || 'http://localhost:8000';

let cachedTools = null;
let cacheTime = 0;
const CACHE_TTL = 60000; // 1 分钟缓存

export async function loadCapeTools() {
    // 检查缓存
    if (cachedTools && Date.now() - cacheTime < CACHE_TTL) {
        return cachedTools;
    }

    try {
        const res = await fetch(`${CAPE_API_URL}/api/tools/list`);
        if (!res.ok) throw new Error(`Cape API error: ${res.status}`);

        const data = await res.json();

        // 转换为本地工具配置格式
        const tools = {};
        for (const tool of data.tools) {
            const name = tool.function.name;
            tools[name] = {
                name,
                description: tool.function.description,
                parameters: convertParameters(tool.function.parameters),
                meta: tool.meta,
                executor: 'executeCape', // 统一执行器
                source: 'cape',
            };
        }

        cachedTools = tools;
        cacheTime = Date.now();

        console.log(`[Cape Loader] 已加载 ${Object.keys(tools).length} 个 Cape 工具`);
        return tools;

    } catch (error) {
        console.error('[Cape Loader] 加载失败:', error.message);
        return cachedTools || {}; // 返回缓存或空对象
    }
}

function convertParameters(openaiParams) {
    const result = {};
    for (const [key, prop] of Object.entries(openaiParams.properties || {})) {
        result[key] = {
            type: prop.type,
            description: prop.description,
            required: openaiParams.required?.includes(key) || false,
        };
        if (prop.enum) result[key].enum = prop.enum;
    }
    return result;
}

export async function executeCape(toolName, args, sessionState) {
    const res = await fetch(`${CAPE_API_URL}/api/tools/execute/${toolName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            task: args.task,
            file_ids: args.file_ids || sessionState?.uploadedFiles || [],
            session_id: sessionState?.sessionId,
        }),
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Cape 执行失败: ${text}`);
    }

    return await res.json();
}
```

### Step 3: 更新 Agent-V2 路由

**修改**: `/Users/g/Desktop/探索/Agent Platform/web/src/app/api/agent-v2/route.js`

```javascript
// 在文件顶部添加
import { loadCapeTools, executeCape } from './tools/cape-loader.js';

// 修改工具加载逻辑
async function getAllTools() {
    // 原有工具
    const nativeTools = {
        generate_image: TOOL_CONFIGS.generate_image,
        edit_image: TOOL_CONFIGS.edit_image,
    };

    // 动态加载 Cape 工具
    const capeTools = await loadCapeTools();

    return { ...nativeTools, ...capeTools };
}

// 修改工具执行器
async function getToolExecutor(toolName) {
    if (toolName === 'generate_image') return executeGenerateImage;
    if (toolName === 'edit_image') return executeEditImage;
    if (toolName.startsWith('cape_')) return executeCape;
    throw new Error(`未知工具: ${toolName}`);
}

// 在 POST handler 中修改
export async function POST(request) {
    // ...
    const allTools = await getAllTools();
    const tools = convertToolsToFunctions(allTools);
    // ...

    // 工具执行部分
    for (const toolCall of toolCalls) {
        const toolName = toolCall.function.name;
        const executor = await getToolExecutor(toolName);

        // Cape 工具返回结构化数据
        const result = await executor(toolName, toolArgs, sessionState);

        // 处理 Cape 返回的文件
        if (result.files?.length > 0) {
            controller.enqueue(
                encoder.encode(
                    `data: ${JSON.stringify({
                        type: 'files',
                        files: result.files
                    })}\n\n`
                )
            );
        }
        // ...
    }
}
```

### Step 4: 前端添加文件支持

**修改**: `ChatWindow.tsx` 或 `AssistantPanel.tsx`

```tsx
// 添加文件上传状态
const [uploadedFiles, setUploadedFiles] = useState<FileInfo[]>([]);
const fileInputRef = useRef<HTMLInputElement>(null);

// 文件上传处理
const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;

    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    const res = await fetch('/api/cape/files/upload', {
        method: 'POST',
        body: formData,
    });

    const data = await res.json();
    setUploadedFiles(prev => [...prev, ...data.files]);
};

// 渲染文件附件
{uploadedFiles.length > 0 && (
    <div className="flex gap-2 p-2 border-t border-slate-200">
        {uploadedFiles.map(file => (
            <div key={file.file_id} className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded text-xs">
                <FileIcon size={12} />
                <span className="max-w-[100px] truncate">{file.name}</span>
                <button onClick={() => removeFile(file.file_id)}>
                    <X size={10} />
                </button>
            </div>
        ))}
    </div>
)}

// 渲染消息中的文件
const renderFiles = (files: FileInfo[]) => (
    <div className="flex flex-wrap gap-2 mt-2">
        {files.map(file => (
            <a
                key={file.file_id}
                href={file.url}
                download={file.name}
                className="flex items-center gap-1 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 rounded-lg text-xs text-blue-600"
            >
                <Download size={12} />
                <span>{file.name}</span>
            </a>
        ))}
    </div>
);
```

### Step 5: 添加文件代理路由

**新建**: `/Users/g/Desktop/探索/Agent Platform/web/src/app/api/cape/files/[...path]/route.js`

```javascript
const CAPE_API_URL = process.env.CAPE_API_URL || 'http://localhost:8000';

export async function GET(request, { params }) {
    const path = params.path.join('/');
    const res = await fetch(`${CAPE_API_URL}/api/files/${path}`);

    return new Response(res.body, {
        headers: {
            'Content-Type': res.headers.get('Content-Type') || 'application/octet-stream',
            'Content-Disposition': res.headers.get('Content-Disposition') || '',
        },
    });
}

export async function POST(request, { params }) {
    const path = params.path.join('/');

    // 文件上传特殊处理
    if (path === 'upload') {
        const formData = await request.formData();
        const res = await fetch(`${CAPE_API_URL}/api/files/upload`, {
            method: 'POST',
            body: formData,
        });
        return Response.json(await res.json());
    }

    // 其他 POST 请求
    const body = await request.json();
    const res = await fetch(`${CAPE_API_URL}/api/files/${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    return Response.json(await res.json());
}
```

---

## 环境配置

### Agent Platform `.env.local`

```bash
# 原有配置
OPENAI_BASE_URL="https://api.bltcy.ai"
OPENAI_API_KEY="sk-xxx"

# 新增 Cape 配置
CAPE_API_URL="http://localhost:8000"
```

### 启动脚本

```bash
#!/bin/bash
# start-dev.sh

# 启动 Cape 后端
echo "🚀 Starting Cape Backend..."
cd /Users/g/Desktop/探索/skillslike
uvicorn api.main:app --port 8000 &
CAPE_PID=$!

# 等待 Cape 启动
sleep 3

# 启动 Agent Platform 前端
echo "🚀 Starting Agent Platform..."
cd "/Users/g/Desktop/探索/Agent Platform/web"
bun run dev &
NEXT_PID=$!

echo "✅ Services started:"
echo "   Cape Backend: http://localhost:8000"
echo "   Agent Platform: http://localhost:3000"

# 优雅退出
trap "kill $CAPE_PID $NEXT_PID 2>/dev/null" EXIT
wait
```

---

## 变更文件清单

### Cape 项目 (skillslike)

```
新增:
  api/routes/tools.py          # OpenAI 兼容工具接口

修改:
  api/main.py                  # 注册 tools router
```

### Agent Platform 项目

```
新增:
  src/app/api/agent-v2/tools/cape-loader.js    # Cape 工具加载器
  src/app/api/cape/files/[...path]/route.js    # 文件代理
  src/workspace/hooks/useFileUpload.ts         # 文件上传 Hook

修改:
  src/app/api/agent-v2/route.js                # 集成 Cape 工具
  src/workspace/tabs/studio/components/        # UI 文件支持
  .env.local                                   # 添加 CAPE_API_URL
```

---

## 验证清单

- [ ] Cape `/api/tools/list` 返回工具列表
- [ ] Cape `/api/tools/execute/cape_xlsx` 可执行
- [ ] Agent Platform 能加载 Cape 工具
- [ ] 前端能显示 Cape 工具选项
- [ ] 文件上传 → Cape 处理 → 下载 完整流程
- [ ] 原有图片工具仍然可用

---

*方案版本: v2.0*
*更新时间: 2025-12-18*
*定位: Cape 能力回归 Agent Platform 主干*
