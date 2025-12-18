# Cape 后端接入 Agent Platform 前端执行方案

## 项目对比分析

### Agent Platform (目标前端)

```
位置: /Users/g/Desktop/探索/Agent Platform/web/
框架: Next.js 16 + React 19 + LangChain
特点:
├── 内置 Agent V2 API (/api/agent-v2/)
├── OpenAI Function Calling 格式的工具系统
├── SSE 流式响应
├── 会话状态管理
├── 图片生成/编辑工具
└── 工作区 UI (Studio/Canvas/Chat)
```

### Cape 系统 (现有后端)

```
位置: /Users/g/Desktop/探索/skillslike/
框架: FastAPI + 沙箱执行
特点:
├── 22+ Cape 能力
├── 文档处理 (xlsx, docx, pptx, pdf)
├── 代码执行沙箱
├── 文件上传下载
└── 能力匹配系统
```

---

## 集成架构

### 方案 A: API 代理模式 (推荐)

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Platform 前端                         │
│                     /workspace                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Platform API Routes                       │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │  /api/agent-v2  │  │  /api/cape-proxy (新增)         │   │
│  │  (原有工具)      │  │  代理 Cape API 请求              │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cape 后端 API                              │
│              http://localhost:8000                           │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │
│  │ /api/chat │ │/api/capes │ │/api/files │ │/api/packs │   │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 方案 B: 直接集成模式

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Platform 前端                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              统一 API Routes (合并)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              /api/agent-v2                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │ 图片工具     │  │ Cape 工具   │  │ 文档工具    │  │   │
│  │  │ (原有)      │  │ (新增)      │  │ (新增)      │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cape 后端 API                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 执行计划

### 阶段 1: 环境准备 (30 分钟)

#### 1.1 配置 Cape 后端地址

```bash
# Agent Platform/.env.local 添加
CAPE_API_URL=http://localhost:8000
```

#### 1.2 启动两个服务

```bash
# 终端 1: Cape 后端
cd /Users/g/Desktop/探索/skillslike
uvicorn api.main:app --port 8000

# 终端 2: Agent Platform 前端
cd "/Users/g/Desktop/探索/Agent Platform/web"
bun run dev
```

---

### 阶段 2: 创建 Cape 代理 API (1 小时)

#### 2.1 新建代理路由

```javascript
// Agent Platform/web/src/app/api/cape/[...path]/route.js

const CAPE_API_URL = process.env.CAPE_API_URL || 'http://localhost:8000';

export async function GET(request, { params }) {
    const path = params.path.join('/');
    const url = new URL(request.url);

    const res = await fetch(`${CAPE_API_URL}/api/${path}${url.search}`, {
        headers: {
            'Content-Type': 'application/json',
        },
    });

    const data = await res.json();
    return Response.json(data);
}

export async function POST(request, { params }) {
    const path = params.path.join('/');
    const body = await request.json();

    const res = await fetch(`${CAPE_API_URL}/api/${path}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
    });

    // 处理 SSE 流
    if (res.headers.get('content-type')?.includes('text/event-stream')) {
        return new Response(res.body, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        });
    }

    const data = await res.json();
    return Response.json(data);
}
```

#### 2.2 文件上传代理

```javascript
// Agent Platform/web/src/app/api/cape/files/upload/route.js

export async function POST(request) {
    const formData = await request.formData();

    const res = await fetch(`${process.env.CAPE_API_URL}/api/files/upload`, {
        method: 'POST',
        body: formData,
    });

    const data = await res.json();
    return Response.json(data);
}
```

---

### 阶段 3: 扩展工具注册表 (1.5 小时)

#### 3.1 添加 Cape 工具配置

```javascript
// Agent Platform/web/src/app/api/agent-v2/tools/cape-tools.js

// 从 Cape API 动态加载工具配置
export async function loadCapeTools() {
    const CAPE_API_URL = process.env.CAPE_API_URL || 'http://localhost:8000';

    try {
        const res = await fetch(`${CAPE_API_URL}/api/capes`);
        const capes = await res.json();

        const tools = {};

        for (const cape of capes) {
            tools[`cape_${cape.id}`] = {
                name: `cape_${cape.id}`,
                description: cape.description,
                parameters: buildCapeParameters(cape),
                executor: `executeCape_${cape.id}`,
                capeId: cape.id,
                requiresSession: true,
            };
        }

        return tools;
    } catch (error) {
        console.error('Failed to load Cape tools:', error);
        return {};
    }
}

function buildCapeParameters(cape) {
    // 根据 Cape 的 interface.input_schema 构建参数
    const params = {
        task: {
            type: 'string',
            description: '要执行的任务描述',
            required: true,
        },
    };

    // 如果是文档类 Cape，添加文件参数
    if (['xlsx', 'docx', 'pptx', 'pdf'].includes(cape.id)) {
        params.file_id = {
            type: 'string',
            description: '要处理的文件 ID（从上传接口获取）',
            optional: true,
        };
    }

    return params;
}
```

#### 3.2 创建 Cape 执行器

```javascript
// Agent Platform/web/src/app/api/agent-v2/tools/cape-executor.js

const CAPE_API_URL = process.env.CAPE_API_URL || 'http://localhost:8000';

export async function executeCape(capeId, args, sessionState) {
    console.log(`[Cape] 执行 Cape: ${capeId}`, args);

    // 如果有文件，先处理文件
    if (args.file_id) {
        const processRes = await fetch(
            `${CAPE_API_URL}/api/files/${args.file_id}/process`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cape_id: capeId,
                    inputs: { task: args.task },
                }),
            }
        );

        const result = await processRes.json();
        return JSON.stringify(result);
    }

    // 否则直接执行 Cape
    const res = await fetch(`${CAPE_API_URL}/api/capes/${capeId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            inputs: { task: args.task, ...args },
        }),
    });

    const result = await res.json();
    return JSON.stringify(result);
}
```

#### 3.3 更新工具注册表

```javascript
// Agent Platform/web/src/app/api/agent-v2/tools/registry.js

import { loadCapeTools } from './cape-tools.js';

// 原有工具
export const TOOL_CONFIGS = {
    generate_image: { /* ... */ },
    edit_image: { /* ... */ },
};

// 动态加载 Cape 工具
let capeToolsLoaded = false;
let capeTools = {};

export async function getAllTools() {
    if (!capeToolsLoaded) {
        capeTools = await loadCapeTools();
        capeToolsLoaded = true;
    }

    return {
        ...TOOL_CONFIGS,
        ...capeTools,
    };
}
```

---

### 阶段 4: 更新 Agent 路由 (1 小时)

#### 4.1 修改 System Prompt

```javascript
// Agent Platform/web/src/app/api/agent-v2/route.js

const SYSTEM_PROMPT = `你是用户的智能创意助理，拥有以下能力：

## 图片创作
1. generate_image - 从零生成新图片
2. edit_image - 修改已有图片

## 文档处理 (Cape 能力)
3. cape_xlsx - Excel 电子表格处理
4. cape_docx - Word 文档处理
5. cape_pptx - PowerPoint 演示文稿处理
6. cape_pdf - PDF 文档处理

## 使用规则
- 创作图片：使用 generate_image 或 edit_image
- 处理文档：使用对应的 cape_xxx 工具
- 用户上传文件后，会获得 file_id，使用该 ID 调用文档工具

交互原则：
- 理解用户意图，选择合适的工具
- 对于文档任务，引导用户上传文件
- 返回结果时提供下载链接
`;
```

#### 4.2 添加 Cape 工具执行器

```javascript
// Agent Platform/web/src/app/api/agent-v2/route.js

import { executeCape } from './tools/cape-executor.js';

// 工具执行器映射
const TOOL_EXECUTORS = {
    generate_image: executeGenerateImage,
    edit_image: executeEditImage,

    // Cape 工具执行器
    cape_xlsx: (args, session) => executeCape('xlsx', args, session),
    cape_docx: (args, session) => executeCape('docx', args, session),
    cape_pptx: (args, session) => executeCape('pptx', args, session),
    cape_pdf: (args, session) => executeCape('pdf', args, session),
};
```

---

### 阶段 5: 前端集成 (2 小时)

#### 5.1 创建文件上传 Hook

```typescript
// Agent Platform/web/src/workspace/hooks/useFileUpload.ts

import { useState } from 'react';

interface UploadedFile {
    file_id: string;
    original_name: string;
    content_type: string;
    size_bytes: number;
}

export function useFileUpload() {
    const [uploading, setUploading] = useState(false);
    const [files, setFiles] = useState<UploadedFile[]>([]);

    const upload = async (fileList: FileList) => {
        setUploading(true);

        const formData = new FormData();
        for (const file of fileList) {
            formData.append('files', file);
        }

        try {
            const res = await fetch('/api/cape/files/upload', {
                method: 'POST',
                body: formData,
            });

            const data = await res.json();
            setFiles((prev) => [...prev, ...data.files]);
            return data.files;
        } finally {
            setUploading(false);
        }
    };

    const clear = () => setFiles([]);

    return { files, uploading, upload, clear };
}
```

#### 5.2 扩展 ChatWindow 组件

```tsx
// 在 ChatWindow.tsx 中添加文件上传支持

import { useFileUpload } from '../hooks/useFileUpload';
import { Paperclip, FileText, X } from 'lucide-react';

// 在组件内添加
const { files, uploading, upload, clear } = useFileUpload();

// 添加文件输入
<input
    type="file"
    ref={fileInputRef}
    className="hidden"
    multiple
    accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
    onChange={(e) => e.target.files && upload(e.target.files)}
/>

// 添加附件按钮
<button
    onClick={() => fileInputRef.current?.click()}
    className="p-2 hover:bg-slate-100 rounded-full"
    title="上传文件"
>
    <Paperclip size={16} />
</button>

// 显示已上传文件
{files.length > 0 && (
    <div className="flex flex-wrap gap-2 p-2 border-t">
        {files.map((file) => (
            <div key={file.file_id} className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded text-xs">
                <FileText size={12} />
                <span>{file.original_name}</span>
                <button onClick={() => removeFile(file.file_id)}>
                    <X size={12} />
                </button>
            </div>
        ))}
    </div>
)}

// 发送消息时附带文件 ID
const handleSend = () => {
    const fileIds = files.map((f) => f.file_id);
    onSendMessage(input, fileIds);
    setInput('');
    clear();
};
```

#### 5.3 处理 Cape 工具结果

```tsx
// 在 Agent 响应处理中添加

// 处理文档输出
if (event.type === 'cape_result') {
    const result = JSON.parse(event.data);

    if (result.output_files?.length > 0) {
        // 显示下载链接
        const downloadLinks = result.output_files.map((file) => ({
            name: file.original_name,
            url: `/api/cape/files/${file.file_id}`,
        }));

        setMessages((prev) => [
            ...prev,
            {
                role: 'model',
                text: '文档处理完成！',
                attachments: downloadLinks,
            },
        ]);
    }
}
```

---

### 阶段 6: 会话状态同步 (30 分钟)

#### 6.1 扩展会话状态

```javascript
// Agent Platform/web/src/app/api/agent-v2/session.js

class SessionState {
    constructor() {
        this.lastImages = [];
        this.uploadedFiles = [];  // 新增
        this.capeOutputs = [];    // 新增
    }

    updateUploadedFiles(files) {
        this.uploadedFiles = files;
    }

    addCapeOutput(output) {
        this.capeOutputs.push(output);
    }

    getLatestFile() {
        return this.uploadedFiles[this.uploadedFiles.length - 1];
    }
}
```

---

## 文件变更清单

### Agent Platform 新增文件

```
src/app/api/
├── cape/
│   ├── [...path]/route.js          # Cape API 代理
│   └── files/upload/route.js       # 文件上传代理

src/app/api/agent-v2/tools/
├── cape-tools.js                   # Cape 工具配置加载
└── cape-executor.js                # Cape 执行器

src/workspace/hooks/
└── useFileUpload.ts                # 文件上传 Hook
```

### Agent Platform 修改文件

```
src/app/api/agent-v2/
├── route.js                        # 添加 Cape 工具支持
├── tools/registry.js               # 扩展工具注册表
└── session.js                      # 扩展会话状态

src/workspace/tabs/studio/components/
├── ChatWindow.tsx                  # 添加文件上传 UI
└── AssistantPanel.tsx              # 添加文件上传 UI

.env.local                          # 添加 CAPE_API_URL
```

---

## 测试验证

### 测试用例 1: 基础连接

```bash
# 验证 Cape API 代理
curl http://localhost:3000/api/cape/capes
# 期望: 返回 Cape 列表
```

### 测试用例 2: 文件上传

```bash
# 上传测试文件
curl -X POST http://localhost:3000/api/cape/files/upload \
  -F "files=@test.xlsx"
# 期望: 返回 file_id
```

### 测试用例 3: 文档处理

```
用户: "帮我处理这个 Excel 文件" [附件: test.xlsx]
Agent: 调用 cape_xlsx 工具
结果: 返回处理后的文件下载链接
```

### 测试用例 4: PPT 生成

```
用户: "帮我创建一份关于 AI 的 PPT，5 页"
Agent: 调用 cape_pptx 工具
结果: 返回生成的 PPT 下载链接
```

---

## 时间估算

| 阶段 | 任务 | 时间 |
|------|------|------|
| 1 | 环境准备 | 30 分钟 |
| 2 | Cape 代理 API | 1 小时 |
| 3 | 扩展工具注册表 | 1.5 小时 |
| 4 | 更新 Agent 路由 | 1 小时 |
| 5 | 前端集成 | 2 小时 |
| 6 | 会话状态同步 | 30 分钟 |
| - | 测试调试 | 1 小时 |
| **总计** | | **7.5 小时** |

---

## 后续优化

1. **能力面板** - 在前端添加 Cape 能力列表展示
2. **进度显示** - 显示文档处理进度
3. **预览功能** - 支持文档在线预览
4. **批量处理** - 支持多文件批量处理
5. **历史记录** - 保存处理历史和输出文件

---

*方案制定时间: 2025-12-18*
