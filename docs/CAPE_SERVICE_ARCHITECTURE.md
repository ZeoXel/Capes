# Cape 服务箱架构

## 架构定位

```
                    ┌─────────────────────────────────────┐
                    │         Cape 服务箱                  │
                    │      (Railway 独立部署)              │
                    │                                     │
                    │  • 22+ 能力 (文档/创作/分析)         │
                    │  • 沙箱执行                          │
                    │  • 文件存储                          │
                    │  • 会话管理                          │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │   Agent     │ │   其他      │ │   未来      │
            │  Platform   │ │   项目A     │ │   项目...   │
            │  (前端)     │ │   (前端)    │ │             │
            └─────────────┘ └─────────────┘ └─────────────┘
```

## Cape 服务箱职责

```yaml
提供:
  - /api/chat        # 对话接口 (SSE 流式)
  - /api/capes       # 能力列表/匹配/执行
  - /api/files       # 文件上传/下载/处理
  - /api/tools       # OpenAI 兼容工具接口
  - /api/health      # 健康检查

不提供:
  - 前端 UI
  - 用户认证 (由前端处理)
  - 业务逻辑 (只提供能力)
```

## Agent Platform 改造

### 清理范围

```
删除:
  src/app/api/agent/              # 旧 agent 目录
  src/app/api/agent-v2/           # 旧 agent-v2 目录
    ├── route.js
    ├── tools/
    │   ├── registry.js
    │   ├── generate-image.js
    │   ├── edit-image.js
    │   └── index.js
    ├── session.js
    ├── streaming.js
    └── agent.js

保留:
  src/app/                        # 页面路由
  src/workspace/                  # 工作区组件
  src/app/api/cape/               # Cape 代理 (新建)
```

### 新建代理层

```
src/app/api/cape/
├── chat/route.js                 # 转发到 Cape /api/chat
├── capes/route.js                # 转发到 Cape /api/capes
├── files/[...path]/route.js      # 转发到 Cape /api/files/*
└── health/route.js               # 转发到 Cape /api/health
```

---

## Railway 部署配置

### Dockerfile

```dockerfile
# Cape 服务箱 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# 复制代码
COPY . .

# 创建存储目录
RUN mkdir -p /app/storage/uploads /app/storage/outputs

# 环境变量
ENV PORT=8000
ENV STORAGE_PATH=/app/storage

# 启动
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### railway.toml

```toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[service]
internalPort = 8000
```

### 环境变量 (Railway Dashboard)

```bash
# LLM 配置
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.bltcy.ai/v1
DEFAULT_MODEL=claude-sonnet-4-20250514

# 存储配置
STORAGE_PATH=/app/storage
MAX_FILE_SIZE_MB=50

# CORS (允许的前端域名)
CORS_ORIGINS=https://agent.example.com,http://localhost:3000

# 可选: 外部存储
# S3_BUCKET=cape-files
# S3_ACCESS_KEY=xxx
# S3_SECRET_KEY=xxx
```

---

## Agent Platform 代理实现

### `/api/cape/chat/route.js`

```javascript
/**
 * Cape Chat 代理
 * 直接转发 SSE 流到前端
 */

const CAPE_URL = process.env.CAPE_API_URL || 'https://cape.railway.app';

export async function POST(request) {
    const body = await request.json();

    const res = await fetch(`${CAPE_URL}/api/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
    });

    // 直接转发 SSE 流
    return new Response(res.body, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    });
}
```

### `/api/cape/capes/route.js`

```javascript
/**
 * Cape 能力列表代理
 */

const CAPE_URL = process.env.CAPE_API_URL || 'https://cape.railway.app';

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const query = searchParams.toString();

    const res = await fetch(`${CAPE_URL}/api/capes${query ? `?${query}` : ''}`);
    const data = await res.json();

    return Response.json(data);
}

export async function POST(request) {
    const body = await request.json();

    const res = await fetch(`${CAPE_URL}/api/capes/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    return Response.json(await res.json());
}
```

### `/api/cape/files/[...path]/route.js`

```javascript
/**
 * Cape 文件代理
 * 处理上传、下载、处理请求
 */

const CAPE_URL = process.env.CAPE_API_URL || 'https://cape.railway.app';

export async function GET(request, { params }) {
    const path = params.path.join('/');

    const res = await fetch(`${CAPE_URL}/api/files/${path}`);

    // 文件下载 - 转发响应体和头
    return new Response(res.body, {
        headers: {
            'Content-Type': res.headers.get('Content-Type') || 'application/octet-stream',
            'Content-Disposition': res.headers.get('Content-Disposition') || '',
            'Content-Length': res.headers.get('Content-Length') || '',
        },
    });
}

export async function POST(request, { params }) {
    const path = params.path.join('/');
    const contentType = request.headers.get('Content-Type') || '';

    let fetchOptions = { method: 'POST' };

    if (contentType.includes('multipart/form-data')) {
        // 文件上传 - 转发 FormData
        fetchOptions.body = await request.formData();
    } else {
        // JSON 请求
        fetchOptions.headers = { 'Content-Type': 'application/json' };
        fetchOptions.body = JSON.stringify(await request.json());
    }

    const res = await fetch(`${CAPE_URL}/api/files/${path}`, fetchOptions);
    return Response.json(await res.json());
}

export async function DELETE(request, { params }) {
    const path = params.path.join('/');

    const res = await fetch(`${CAPE_URL}/api/files/${path}`, {
        method: 'DELETE',
    });

    return Response.json(await res.json());
}
```

---

## 前端 Chat 服务改造

### `/src/services/capeService.js` (新建)

```javascript
/**
 * Cape 服务客户端
 * 统一封装所有 Cape API 调用
 */

class CapeService {
    constructor(baseUrl = '/api/cape') {
        this.baseUrl = baseUrl;
    }

    /**
     * 发送聊天消息 (SSE 流式)
     */
    async chat(message, options = {}) {
        const response = await fetch(`${this.baseUrl}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                session_id: options.sessionId,
                model: options.model || 'claude-sonnet-4-20250514',
                stream: true,
                file_ids: options.fileIds || [],
            }),
        });

        return response.body;
    }

    /**
     * 获取能力列表
     */
    async getCapes() {
        const res = await fetch(`${this.baseUrl}/capes`);
        return res.json();
    }

    /**
     * 匹配能力
     */
    async matchCapes(query) {
        const res = await fetch(`${this.baseUrl}/capes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });
        return res.json();
    }

    /**
     * 上传文件
     */
    async uploadFiles(files, sessionId) {
        const formData = new FormData();
        for (const file of files) {
            formData.append('files', file);
        }
        if (sessionId) {
            formData.append('session_id', sessionId);
        }

        const res = await fetch(`${this.baseUrl}/files/upload`, {
            method: 'POST',
            body: formData,
        });
        return res.json();
    }

    /**
     * 获取文件下载 URL
     */
    getFileUrl(fileId) {
        return `${this.baseUrl}/files/${fileId}`;
    }

    /**
     * 健康检查
     */
    async health() {
        const res = await fetch(`${this.baseUrl}/health`);
        return res.json();
    }
}

export const capeService = new CapeService();
export default capeService;
```

### 更新 `ChatWindow.tsx`

```tsx
import { capeService } from '@/services/capeService';

// 替换原有的 sendMessage 逻辑
const sendMessage = async (text: string) => {
    setIsLoading(true);
    setMessages(prev => [...prev, { role: 'user', text }]);

    try {
        const stream = await capeService.chat(text, {
            sessionId,
            fileIds: uploadedFiles.map(f => f.file_id),
        });

        const reader = stream.getReader();
        const decoder = new TextDecoder();
        let assistantText = '';
        let receivedFiles = [];

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                const data = JSON.parse(line.slice(6));

                switch (data.type || data.event) {
                    case 'session':
                        setSessionId(data.session_id);
                        break;

                    case 'content':
                        assistantText += data.text;
                        // 实时更新消息
                        setMessages(prev => {
                            const updated = [...prev];
                            const lastIdx = updated.length - 1;
                            if (updated[lastIdx]?.role === 'model') {
                                updated[lastIdx].text = assistantText;
                            } else {
                                updated.push({ role: 'model', text: assistantText });
                            }
                            return updated;
                        });
                        break;

                    case 'cape_end':
                        // Cape 执行完成，可能有文件输出
                        if (data.output_files?.length) {
                            receivedFiles.push(...data.output_files);
                        }
                        break;

                    case 'done':
                        // 如果有文件，添加到消息
                        if (receivedFiles.length) {
                            setMessages(prev => {
                                const updated = [...prev];
                                const lastIdx = updated.length - 1;
                                if (updated[lastIdx]?.role === 'model') {
                                    updated[lastIdx].files = receivedFiles;
                                }
                                return updated;
                            });
                        }
                        break;
                }
            }
        }
    } catch (error) {
        console.error('Chat error:', error);
        setMessages(prev => [...prev, {
            role: 'model',
            text: `错误: ${error.message}`
        }]);
    } finally {
        setIsLoading(false);
        setUploadedFiles([]); // 清空已上传文件
    }
};
```

---

## 执行清单

### Phase 1: Cape 准备 (当前项目)

```bash
# 确保 Cape 可独立运行
cd /Users/g/Desktop/探索/skillslike

# 创建 Dockerfile
# 创建 railway.toml
# 测试本地 Docker 构建

docker build -t cape-service .
docker run -p 8000:8000 -e OPENAI_API_KEY=xxx cape-service
```

### Phase 2: Agent Platform 清理

```bash
cd "/Users/g/Desktop/探索/Agent Platform/web"

# 删除旧 agent 代码
rm -rf src/app/api/agent
rm -rf src/app/api/agent-v2

# 创建 Cape 代理
mkdir -p src/app/api/cape/chat
mkdir -p src/app/api/cape/capes
mkdir -p src/app/api/cape/files

# 创建服务层
touch src/services/capeService.js
```

### Phase 3: 前端适配

```bash
# 更新 ChatWindow / AssistantPanel
# 使用 capeService 替换原有调用
# 添加文件上传 UI
```

### Phase 4: 部署

```bash
# Cape -> Railway
# Agent Platform -> Vercel

# 配置环境变量
# CAPE_API_URL=https://cape-xxx.railway.app
```

---

## 文件变更总览

### Cape 项目 (新增)

```
Dockerfile                    # Docker 构建文件
railway.toml                  # Railway 配置
```

### Agent Platform (删除)

```
src/app/api/agent/            # 整个目录
src/app/api/agent-v2/         # 整个目录
```

### Agent Platform (新增)

```
src/app/api/cape/
├── chat/route.js
├── capes/route.js
├── files/[...path]/route.js
└── health/route.js

src/services/
└── capeService.js
```

### Agent Platform (修改)

```
src/workspace/tabs/studio/components/ChatWindow.tsx
src/workspace/tabs/studio/components/AssistantPanel.tsx
.env.local  # 添加 CAPE_API_URL
```

---

*架构版本: v3.0*
*设计原则: Cape 独立服务化，前端轻量代理*
