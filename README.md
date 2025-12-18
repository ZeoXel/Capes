# Cape

**C**laude **A**gent **P**ack **E**ngine - 模型无关的 AI 能力执行框架

Cape 实现了 Claude Skills 的全量能力，但不局限于 Claude 框架，支持任意 LLM 后端。

## 特性

- **多模型支持** - 支持 OpenAI、Anthropic、Google 等多种 LLM
- **代码执行沙箱** - 安全的代码执行环境（进程隔离/Docker 容器）
- **文档处理能力** - 完整的 Office 文档处理（Excel/Word/PPT/PDF）
- **能力包管理** - 模块化的能力组织和分发
- **文件上传下载** - 完整的文件生命周期管理
- **现代前端** - Next.js 16 + React 19 + TypeScript

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                    Next.js 16 + React 19                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│                    FastAPI + SSE Streaming                   │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   /api/chat  │  /api/capes  │  /api/packs  │  /api/files    │
└──────────────┴──────────────┴──────────────┴────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Cape Runtime                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│  CapeRegistry   │  SandboxManager │    Model Adapters       │
│  (能力注册)      │  (沙箱管理)      │    (模型适配)            │
└─────────────────┴─────────────────┴─────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Sandbox Layer                           │
├─────────────────┬─────────────────┬─────────────────────────┤
│  InProcessSandbox│ ProcessSandbox │   DockerSandbox         │
│  (开发/测试)      │  (进程隔离)     │   (生产环境)             │
└─────────────────┴─────────────────┴─────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+ / Bun
- Docker (可选，用于生产环境)

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd skillslike

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd web && bun install
```

### 启动服务

```bash
# 启动 API 服务 (端口 8000)
uvicorn api.main:app --port 8000

# 启动前端开发服务器 (端口 3000)
cd web && bun run dev
```

访问 http://localhost:3000 即可使用。

## 项目结构

```
skillslike/
├── api/                    # FastAPI 后端
│   ├── main.py            # 应用入口
│   ├── storage.py         # 文件存储管理
│   ├── routes/            # API 路由
│   │   ├── chat.py        # 聊天 SSE 流
│   │   ├── capes.py       # 能力管理
│   │   ├── packs.py       # 能力包管理
│   │   ├── files.py       # 文件上传下载
│   │   └── models.py      # 模型配置
│   └── schemas.py         # Pydantic 模型
│
├── cape/                   # 核心框架
│   ├── core/              # 核心模型
│   │   └── models.py      # Cape/Pack 数据结构
│   ├── runtime/           # 运行时
│   │   ├── sandbox/       # 沙箱实现
│   │   │   ├── manager.py         # 沙箱管理器
│   │   │   ├── process_sandbox.py # 进程沙箱
│   │   │   ├── inprocess_sandbox.py # 进程内沙箱
│   │   │   └── docker_sandbox.py  # Docker 沙箱
│   │   └── registry.py    # 能力注册表
│   └── importers/         # 导入器
│       ├── skill.py       # Skill 导入
│       └── skill_enhanced.py # 增强导入
│
├── packs/                  # 能力包
│   ├── document-pack/     # 文档处理包
│   │   ├── pack.yaml      # 包配置
│   │   └── capes/         # 能力定义
│   │       ├── xlsx.yaml  # Excel 处理
│   │       ├── docx.yaml  # Word 处理
│   │       ├── pptx.yaml  # PPT 处理
│   │       └── pdf.yaml   # PDF 处理
│   └── office-pack/       # 办公能力包
│
├── web/                    # 前端应用
│   ├── src/
│   │   ├── app/           # Next.js 页面
│   │   ├── components/    # React 组件
│   │   │   ├── chat/      # 聊天组件
│   │   │   │   ├── input.tsx          # 输入框
│   │   │   │   ├── message.tsx        # 消息显示
│   │   │   │   └── file-attachment.tsx # 文件附件
│   │   │   └── ui/        # UI 组件
│   │   ├── lib/           # 工具库
│   │   │   └── api.ts     # API 客户端
│   │   └── data/          # 类型定义
│   │       └── types.ts
│   └── package.json
│
├── docs/                   # 文档
│   └── code-execution-layer-design.md
│
└── tests/                  # 测试
    ├── test_sandbox_quick.py
    ├── test_docker_sandbox.py
    └── test_file_api.py
```

## API 端点

### 聊天

```
POST /api/chat              # 发送消息（支持 SSE 流）
```

### 能力管理

```
GET  /api/capes             # 列出所有能力
GET  /api/capes/{id}        # 获取能力详情
POST /api/capes/match       # 意图匹配
```

### 能力包

```
GET  /api/packs             # 列出所有能力包
GET  /api/packs/{name}      # 获取能力包详情
```

### 文件管理

```
POST   /api/files/upload              # 上传文件
GET    /api/files/{id}                # 下载文件
GET    /api/files/{id}/metadata       # 获取元数据
DELETE /api/files/{id}                # 删除文件
GET    /api/files/session/{id}        # 列出会话文件
DELETE /api/files/session/{id}        # 删除会话文件
POST   /api/files/{id}/process        # 用 Cape 处理文件
GET    /api/files/stats               # 存储统计
```

## 能力包 (Packs)

### document-pack

专业文档处理包，包含：

| Cape | 功能 | 类型 |
|------|------|------|
| xlsx | Excel 电子表格处理 | LLM |
| docx | Word 文档处理 | Hybrid |
| pptx | PowerPoint 演示文稿 | Hybrid |
| pdf  | PDF 文档处理 | Hybrid |

### 创建自定义 Cape

```yaml
# packs/my-pack/capes/my-cape.yaml
id: my-cape
name: 我的能力
version: 1.0.0
description: 自定义能力描述

metadata:
  tags: [custom, example]
  intents:
    - 执行某个操作
    - 处理某类数据

execution:
  type: hybrid  # llm | code | hybrid
  timeout_seconds: 60

model_adapters:
  claude:
    system_prompt: |
      你是一个专业的助手...
  openai:
    system_prompt: |
      You are a professional assistant...
```

## 沙箱安全级别

| 级别 | 类型 | 适用场景 |
|------|------|----------|
| L1 | InProcessSandbox | 开发/测试 |
| L2 | ProcessSandbox | 轻量隔离 |
| L3 | DockerSandbox | 生产环境 |

## 开发

### 运行测试

```bash
# 沙箱测试
python3 test_sandbox_quick.py

# 文件 API 测试
python3 test_file_api.py

# Docker 沙箱测试 (需要 Docker)
python3 test_docker_sandbox.py
```

### 构建前端

```bash
cd web
bun run build
```

## 配置

### 环境变量

```bash
# API
CAPE_STORAGE_PATH=./storage    # 文件存储路径
CAPE_MAX_FILE_SIZE=52428800    # 最大文件大小 (50MB)
CAPE_FILE_EXPIRE_HOURS=24      # 文件过期时间

# 前端
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 技术栈

**后端**
- Python 3.11+
- FastAPI
- Pydantic
- aiofiles

**前端**
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- Framer Motion

**沙箱**
- Docker (可选)
- subprocess

## License

MIT
