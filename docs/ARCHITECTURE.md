# Cape System 架构文档

> 版本: 1.0.0 | 更新日期: 2024-03

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [后端架构](#3-后端架构)
4. [前端架构](#4-前端架构)
5. [API 设计](#5-api-设计)
6. [数据模型](#6-数据模型)
7. [通信协议](#7-通信协议)
8. [部署架构](#8-部署架构)
9. [扩展性设计](#9-扩展性设计)

---

## 1. 项目概述

### 1.1 项目目标

Cape (Capability Package) System 是一个模型无关的能力抽象系统，旨在：

- **统一能力定义**: 使用标准格式定义可执行能力（不仅仅是提示词）
- **多模型支持**: 通过适配器支持 OpenAI、Claude、Gemini 等多种模型
- **自动意图识别**: 根据用户输入自动匹配最相关的能力
- **无缝 Skill 导入**: 兼容 Claude SKILL.md 格式，可直接导入使用
- **LangChain 集成**: 提供 LangChain 工具包，与 Agent 无缝协作

### 1.2 核心概念

| 概念 | 说明 |
|------|------|
| **Cape** | Capability Package，能力包，定义一个可执行能力的完整规范 |
| **Skill** | Claude 的 SKILL.md 格式，可导入为 Cape |
| **Registry** | 能力注册表，管理所有 Cape 的加载、查询、匹配 |
| **Runtime** | 执行引擎，负责 Cape 的实际执行 |
| **Adapter** | 模型适配器，将 Cape 适配到不同 LLM |
| **Executor** | 执行器，处理不同类型的执行（tool/llm/workflow/hybrid） |

### 1.3 技术栈

**后端**:
- Python 3.10+
- Pydantic 2.x (数据验证)
- LangChain / LangGraph (Agent 框架)
- FastAPI (API 服务)
- sentence-transformers (语义匹配，可选)

**前端**:
- Next.js 14+ (React 框架)
- TypeScript
- Tailwind CSS
- Framer Motion (动画)
- Lucide Icons

**支持的 LLM**:
- OpenAI: gpt-4-turbo, gpt-4o, gpt-4.1, gpt-5
- Google: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash
- Anthropic: claude-3-5-sonnet, claude-3-5-haiku, claude-3-haiku

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户界面层                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     Next.js Web Application                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │   │
│  │  │   Chat   │  │  Capes   │  │ Settings │  │    Model      │   │   │
│  │  │   View   │  │  Config  │  │  Panel   │  │   Selector    │   │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘   │   │
│  │       └─────────────┴─────────────┴────────────────┘            │   │
│  │                            │                                     │   │
│  │                     API Client (lib/api.ts)                      │   │
│  └─────────────────────────────┬───────────────────────────────────┘   │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │ HTTP / SSE
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              API 服务层                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      FastAPI Server                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │   /capes    │  │   /chat     │  │      /models            │  │   │
│  │  │   Routes    │  │   Routes    │  │      Routes             │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │   │
│  │         └────────────────┼─────────────────────┘                 │   │
│  │                          │                                       │   │
│  │                   Dependencies (deps.py)                         │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            核心引擎层                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │   Registry   │  │   Matcher    │  │         Runtime              │  │
│  │              │  │              │  │  ┌────────────────────────┐  │  │
│  │ • load()     │  │ • keyword    │  │  │      Executors         │  │  │
│  │ • get()      │  │ • semantic   │  │  │  ┌────┐ ┌────┐ ┌────┐  │  │  │
│  │ • match()    │  │ • scoring    │  │  │  │Tool│ │LLM │ │Flow│  │  │  │
│  │ • all()      │  │              │  │  │  └────┘ └────┘ └────┘  │  │  │
│  └──────┬───────┘  └──────┬───────┘  │  └────────────────────────┘  │  │
│         │                 │          │               │               │  │
│         └─────────────────┴──────────┴───────────────┘               │  │
│                                      │                                  │
│                              Adapters                                   │
│                    ┌─────────┬─────────┬─────────┐                     │
│                    │ OpenAI  │  Claude │ Generic │                     │
│                    └─────────┴─────────┴─────────┘                     │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            数据存储层                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │   capes/*.yaml   │  │  skills/*.md     │  │   执行日志/指标      │  │
│  │   (原生 Cape)     │  │  (导入 Skill)    │  │   (可选持久化)       │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入 "帮我审查这段代码"
         │
         ▼
┌─────────────────┐
│  1. API 接收    │ POST /api/chat
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 意图匹配    │ Registry.match("帮我审查这段代码")
└────────┬────────┘ → 返回 [{cape: code-review, score: 0.87}, ...]
         │
         ▼
┌─────────────────┐
│  3. Agent 决策  │ LangChain Agent 选择调用 cape_code_review 工具
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. 执行 Cape   │ Runtime.execute("code-review", {content: ...})
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. 调用 LLM    │ OpenAI/Gemini/Claude Adapter
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. 流式返回    │ SSE: content chunks + execution metadata
└────────┬────────┘
         │
         ▼
    前端显示结果
```

---

## 3. 后端架构

### 3.1 目录结构

```
cape/
├── __init__.py
├── core/                          # 核心数据模型
│   ├── __init__.py
│   └── models.py                  # Cape, CapeResult, Enums
│
├── registry/                      # 能力注册表
│   ├── __init__.py
│   ├── registry.py                # CapeRegistry
│   └── matcher.py                 # CapeMatcher (意图匹配)
│
├── runtime/                       # 执行引擎
│   ├── __init__.py
│   ├── runtime.py                 # CapeRuntime
│   ├── context.py                 # ExecutionContext
│   └── executors.py               # Tool/LLM/Workflow/Hybrid Executors
│
├── adapters/                      # 模型适配器
│   ├── __init__.py
│   ├── base.py                    # BaseAdapter, AdapterConfig
│   ├── openai.py                  # OpenAIAdapter (支持工具调用)
│   ├── claude.py                  # ClaudeAdapter
│   └── generic.py                 # GenericAdapter
│
├── importers/                     # 导入器
│   ├── __init__.py
│   └── skill.py                   # SkillImporter (SKILL.md → Cape)
│
└── agent/                         # Agent 集成
    ├── __init__.py
    ├── agent.py                   # CapeAgent
    └── langchain.py               # LangChain 工具包
```

### 3.2 核心组件

#### 3.2.1 CapeRegistry

```python
class CapeRegistry:
    """能力注册表 - 管理所有 Cape 的加载、查询、匹配"""

    def __init__(
        self,
        capes_dir: Path,           # cape.yaml 目录
        skills_dir: Path,          # SKILL.md 目录
        auto_load: bool = True,    # 自动加载
        use_embeddings: bool = True # 启用语义匹配
    ):
        self._capes: Dict[str, Cape] = {}
        self.matcher = CapeMatcher(use_embeddings)
        self.skill_importer = SkillImporter()

    # 核心方法
    def register(self, cape: Cape): ...
    def get(self, cape_id: str) -> Cape: ...
    def all(self) -> List[Cape]: ...
    def match(self, query: str, top_k: int = 5) -> List[MatchResult]: ...
    def match_best(self, query: str) -> Cape: ...
```

#### 3.2.2 CapeRuntime

```python
class CapeRuntime:
    """执行引擎 - 负责 Cape 的实际执行"""

    def __init__(
        self,
        registry: CapeRegistry,
        adapter_factory: Callable[[str], BaseAdapter]
    ):
        self._executors = {
            ExecutionType.TOOL: ToolExecutor(),
            ExecutionType.CODE: CodeExecutor(),
            ExecutionType.LLM: LLMExecutor(adapter_factory),
            ExecutionType.WORKFLOW: WorkflowExecutor(self),
            ExecutionType.HYBRID: HybridExecutor(...),
        }

    async def execute(
        self,
        cape_id: str,
        inputs: Dict[str, Any],
        model: str = None
    ) -> CapeResult: ...

    def execute_sync(self, ...) -> CapeResult: ...
```

#### 3.2.3 OpenAIAdapter

```python
class OpenAIAdapter(BaseAdapter):
    """OpenAI 模型适配器 - 支持工具调用"""

    # 支持的模型及成本
    COSTS = {
        "gpt-5": {"input": 0.02, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-2.5-flash": {"input": 0.00015, "output": 0.0006},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        ...
    }

    async def execute(
        self,
        prompt: str,
        context: ExecutionContext,
        tools: List[Dict] = None  # OpenAI 工具格式
    ) -> AdapterResponse: ...

    def _format_tools_for_api(self, tools) -> List[Dict]:
        """转换为 OpenAI 工具调用格式"""
        # {type: "function", function: {name, description, parameters}}
```

#### 3.2.4 LangChain 集成

```python
class CapeToolkit:
    """LangChain 工具包"""

    def __init__(
        self,
        capes_dir: Path,
        skills_dir: Path,
        include_router: bool = True
    ):
        self.registry = CapeRegistry(capes_dir, skills_dir)
        self.runtime = CapeRuntime(registry, adapter_factory)

    def get_tools(self) -> List[StructuredTool]:
        """获取 LangChain 工具列表"""
        tools = []
        if self.include_router:
            tools.append(CapeRouterTool(...))
        for cape in self.registry.all():
            tools.append(CapeTool(cape.id, ...))
        return tools


def create_langchain_agent(
    capes_dir: Path,
    skills_dir: Path,
    llm: BaseChatModel
) -> CompiledGraph:
    """创建 LangChain Agent"""
    toolkit = CapeToolkit(capes_dir, skills_dir)
    tools = toolkit.get_tools()
    return create_react_agent(llm, tools, system_prompt)
```

---

## 4. 前端架构

### 4.1 目录结构

```
web/
├── src/
│   ├── app/                       # Next.js App Router
│   │   ├── layout.tsx             # 根布局
│   │   ├── page.tsx               # 主页面
│   │   └── globals.css            # 全局样式
│   │
│   ├── components/                # React 组件
│   │   ├── ui/                    # 基础 UI 组件
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   └── badge.tsx
│   │   ├── chat/                  # 聊天相关
│   │   │   ├── message.tsx        # 消息气泡
│   │   │   ├── input.tsx          # 输入框
│   │   │   └── cape-panel.tsx     # Cape 选择面板
│   │   ├── cape-card.tsx          # Cape 卡片
│   │   └── model-selector.tsx     # 模型选择器 (新增)
│   │
│   ├── lib/                       # 工具库
│   │   ├── utils.ts               # 通用工具
│   │   └── api.ts                 # API 客户端 (新增)
│   │
│   ├── hooks/                     # React Hooks
│   │   └── use-chat.ts            # 聊天 Hook (新增)
│   │
│   └── data/                      # 数据定义
│       └── types.ts               # TypeScript 类型
│
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

### 4.2 核心组件

#### 4.2.1 主页面 (page.tsx)

```tsx
export default function HomePage() {
  // 状态
  const [viewMode, setViewMode] = useState<"chat" | "capabilities">("chat");
  const [capes, setCapes] = useState<Cape[]>([]);
  const [enabledCapes, setEnabledCapes] = useState<Set<string>>(new Set());
  const [model, setModel] = useState("gemini-2.5-flash");

  // 聊天 Hook
  const { messages, sendMessage, isStreaming } = useChat();

  // 加载 Capes
  useEffect(() => {
    api.getCapes().then(setCapes);
  }, []);

  return (
    <div className="h-screen flex flex-col">
      <Header viewMode={viewMode} onViewChange={setViewMode} />

      {viewMode === "chat" ? (
        <ChatView messages={messages} isStreaming={isStreaming} />
      ) : (
        <CapesConfigView capes={capes} enabledCapes={enabledCapes} />
      )}

      <ChatInput onSend={(msg) => sendMessage(msg, model)} />
    </div>
  );
}
```

#### 4.2.2 消息组件 (message.tsx)

```tsx
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  status: "pending" | "streaming" | "complete" | "error";
  execution?: {
    cape_id: string;
    cape_name: string;
    status: "running" | "completed" | "failed";
    duration_ms?: number;
  };
}

export function MessageItem({ message }: { message: Message }) {
  return (
    <div className={cn("flex gap-3", message.role === "user" && "flex-row-reverse")}>
      <Avatar role={message.role} />
      <div>
        {message.execution?.status === "running" && (
          <CapeRunningIndicator capeName={message.execution.cape_name} />
        )}
        <MessageBubble content={message.content} role={message.role} />
        {message.execution?.status === "completed" && (
          <ExecutionSummary execution={message.execution} />
        )}
      </div>
    </div>
  );
}
```

#### 4.2.3 API 客户端 (lib/api.ts) - 新增

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = {
  // 获取所有 Capes
  getCapes: async (): Promise<Cape[]> => {
    const res = await fetch(`${API_BASE}/api/capes`);
    return res.json();
  },

  // 获取可用模型
  getModels: async (): Promise<Model[]> => {
    const res = await fetch(`${API_BASE}/api/models`);
    return res.json();
  },

  // 发送消息 (SSE 流式)
  chat: async function* (
    message: string,
    model: string,
    enabledCapes: string[]
  ): AsyncGenerator<ChatEvent> {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, model, enabled_capes: enabledCapes }),
    });

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      for (const line of chunk.split("\n")) {
        if (line.startsWith("data: ")) {
          yield JSON.parse(line.slice(6));
        }
      }
    }
  },

  // 意图匹配
  match: async (query: string): Promise<MatchResult[]> => {
    const res = await fetch(`${API_BASE}/api/match`, {
      method: "POST",
      body: JSON.stringify({ query }),
    });
    return res.json();
  },
};
```

#### 4.2.4 聊天 Hook (hooks/use-chat.ts) - 新增

```typescript
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = async (
    content: string,
    model: string,
    enabledCapes: string[]
  ) => {
    // 1. 添加用户消息
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date(),
      status: "complete",
    };
    setMessages(prev => [...prev, userMessage]);

    // 2. 创建 Assistant 消息占位
    const assistantId = `assistant-${Date.now()}`;
    const assistantMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      status: "streaming",
    };
    setMessages(prev => [...prev, assistantMessage]);
    setIsStreaming(true);

    // 3. 流式接收响应
    try {
      for await (const event of api.chat(content, model, enabledCapes)) {
        switch (event.type) {
          case "cape_start":
            setMessages(prev => prev.map(m =>
              m.id === assistantId
                ? { ...m, execution: { ...event, status: "running" } }
                : m
            ));
            break;

          case "content":
            setMessages(prev => prev.map(m =>
              m.id === assistantId
                ? { ...m, content: m.content + event.text }
                : m
            ));
            break;

          case "cape_end":
            setMessages(prev => prev.map(m =>
              m.id === assistantId
                ? { ...m, execution: { ...m.execution, ...event, status: "completed" } }
                : m
            ));
            break;

          case "done":
            setMessages(prev => prev.map(m =>
              m.id === assistantId
                ? { ...m, status: "complete" }
                : m
            ));
            break;
        }
      }
    } catch (error) {
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, status: "error", content: "发生错误，请重试" }
          : m
      ));
    } finally {
      setIsStreaming(false);
    }
  };

  return { messages, sendMessage, isStreaming };
}
```

---

## 5. API 设计

### 5.1 端点总览

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/capes` | 获取所有 Cape 列表 |
| GET | `/api/capes/{id}` | 获取单个 Cape 详情 |
| POST | `/api/chat` | 发送消息，SSE 流式响应 |
| POST | `/api/match` | 意图匹配 |
| GET | `/api/models` | 获取可用模型列表 |
| GET | `/api/stats` | 获取系统统计 |

### 5.2 详细定义

#### GET /api/capes

**Response** `200 OK`:
```json
[
  {
    "id": "code-review",
    "name": "Code Review Assistant",
    "version": "1.0.0",
    "description": "AI 驱动的代码审查...",
    "execution_type": "llm",
    "risk_level": "low",
    "source": "skill",
    "tags": ["code", "review", "ai"],
    "intent_patterns": ["审查代码", "代码审查", "review"],
    "model_adapters": ["openai", "claude"],
    "estimated_cost": 0.03,
    "timeout_seconds": 60,
    "created_at": "2024-03-01T12:00:00Z",
    "updated_at": "2024-03-19T16:00:00Z"
  }
]
```

#### POST /api/chat

**Request**:
```json
{
  "message": "帮我审查这段代码: def add(a,b): return a+b",
  "model": "gemini-2.5-flash",
  "enabled_capes": ["code-review", "code-analyzer"]
}
```

**Response** `200 OK` (SSE Stream):
```
event: cape_match
data: {"cape_id": "code-review", "cape_name": "Code Review", "score": 0.87}

event: cape_start
data: {"cape_id": "code-review", "cape_name": "Code Review Assistant"}

event: content
data: {"text": "代码审查结果：\n\n"}

event: content
data: {"text": "1. **函数命名**: `add` 命名清晰\n"}

event: content
data: {"text": "2. **改进建议**: 添加类型注解\n"}

event: cape_end
data: {"cape_id": "code-review", "duration_ms": 1250, "tokens_used": 450, "cost_usd": 0.0012}

event: done
data: {"total_duration_ms": 1320}
```

#### POST /api/match

**Request**:
```json
{
  "query": "处理 PDF 文件",
  "top_k": 5,
  "threshold": 0.3
}
```

**Response** `200 OK`:
```json
[
  {"cape_id": "pdf-processor", "cape_name": "PDF Processor", "score": 0.92},
  {"cape_id": "data-transformer", "cape_name": "Data Transformer", "score": 0.45}
]
```

#### GET /api/models

**Response** `200 OK`:
```json
[
  {
    "id": "gemini-2.5-flash",
    "name": "Gemini 2.5 Flash",
    "provider": "google",
    "speed": "fast",
    "cost_tier": "low",
    "supports_tools": true
  },
  {
    "id": "gpt-4-turbo",
    "name": "GPT-4 Turbo",
    "provider": "openai",
    "speed": "medium",
    "cost_tier": "medium",
    "supports_tools": true
  }
]
```

---

## 6. 数据模型

### 6.1 后端模型 (Python)

```python
# cape/core/models.py

class ExecutionType(str, Enum):
    TOOL = "tool"           # 直接工具调用
    WORKFLOW = "workflow"   # 多步骤工作流
    CODE = "code"           # 代码执行
    LLM = "llm"             # LLM 生成
    HYBRID = "hybrid"       # 混合模式

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SourceType(str, Enum):
    NATIVE = "native"       # 原生 Cape
    SKILL = "skill"         # 从 SKILL.md 导入
    OPENAI_FUNC = "openai_func"
    MCP_TOOL = "mcp_tool"
    CUSTOM = "custom"

class Cape(BaseModel):
    # 核心标识
    id: str
    name: str
    version: str = "1.0.0"
    description: str

    # 元数据
    metadata: CapeMetadata

    # 接口定义
    interface: CapeInterface

    # 执行配置
    execution: CapeExecution

    # 安全控制
    safety: CapeSafety

    # 模型适配器
    model_adapters: Dict[str, Dict[str, Any]]

class CapeResult(BaseModel):
    cape_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    tokens_used: int = 0
    cost_usd: float = 0
```

### 6.2 前端模型 (TypeScript)

```typescript
// web/src/data/types.ts

export type ExecutionType = "tool" | "workflow" | "code" | "llm" | "hybrid";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type SourceType = "native" | "skill" | "openai_func" | "mcp_tool" | "custom";

export interface Cape {
  id: string;
  name: string;
  version: string;
  description: string;
  execution_type: ExecutionType;
  risk_level: RiskLevel;
  source: SourceType;
  tags: string[];
  intent_patterns: string[];
  model_adapters: string[];
  estimated_cost?: number;
  timeout_seconds?: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  status: "pending" | "streaming" | "complete" | "error";
  execution?: CapeExecution;
}

export interface CapeExecution {
  cape_id: string;
  cape_name: string;
  status: "running" | "completed" | "failed";
  duration_ms?: number;
  tokens_used?: number;
  cost_usd?: number;
  error?: string;
}

export interface Model {
  id: string;
  name: string;
  provider: "openai" | "google" | "anthropic";
  speed: "fast" | "medium" | "slow";
  cost_tier: "low" | "medium" | "high";
  supports_tools: boolean;
}
```

### 6.3 模型映射

后端 Cape → 前端 Cape 的字段映射：

| 后端 | 前端 |
|------|------|
| `cape.id` | `id` |
| `cape.name` | `name` |
| `cape.version` | `version` |
| `cape.description` | `description` |
| `cape.execution.type.value` | `execution_type` |
| `cape.safety.risk_level.value` | `risk_level` |
| `cape.metadata.source.value` | `source` |
| `cape.metadata.tags` | `tags` |
| `cape.metadata.intents` | `intent_patterns` |
| `list(cape.model_adapters.keys())` | `model_adapters` |
| `cape.safety.estimated_cost_usd` | `estimated_cost` |
| `cape.execution.timeout_seconds` | `timeout_seconds` |

---

## 7. 通信协议

### 7.1 SSE 事件格式

聊天接口使用 Server-Sent Events (SSE) 进行流式响应：

```
event: <event_type>
data: <json_payload>

```

#### 事件类型

| 事件类型 | 说明 | Payload |
|----------|------|---------|
| `cape_match` | Cape 匹配结果 | `{cape_id, cape_name, score}` |
| `cape_start` | 开始执行 Cape | `{cape_id, cape_name}` |
| `content` | 内容片段 | `{text}` |
| `cape_end` | 执行完成 | `{cape_id, duration_ms, tokens_used, cost_usd}` |
| `error` | 错误 | `{message, code}` |
| `done` | 流结束 | `{total_duration_ms}` |

### 7.2 完整流式示例

```
// 用户发送: "帮我审查这段代码: def add(a,b): return a+b"

event: cape_match
data: {"cape_id":"code-review","cape_name":"Code Review Assistant","score":0.87}

event: cape_start
data: {"cape_id":"code-review","cape_name":"Code Review Assistant"}

event: content
data: {"text":"## 代码审查结果\n\n"}

event: content
data: {"text":"针对您的代码 `def add(a,b): return a+b`，以下是审查意见：\n\n"}

event: content
data: {"text":"### 优点\n- 函数命名清晰\n- 逻辑简洁\n\n"}

event: content
data: {"text":"### 改进建议\n1. 添加类型注解\n2. 添加文档字符串\n"}

event: cape_end
data: {"cape_id":"code-review","duration_ms":1250,"tokens_used":320,"cost_usd":0.0008}

event: done
data: {"total_duration_ms":1320}
```

---

## 8. 部署架构

### 8.1 开发环境

```
┌─────────────────┐     ┌─────────────────┐
│  Next.js Dev    │────▶│  FastAPI Dev    │
│  localhost:3000 │     │  localhost:8000 │
└─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  第三方 LLM API  │
                        │  api.bltcy.ai   │
                        └─────────────────┘
```

### 8.2 生产环境

```
                        ┌─────────────────┐
                        │     Nginx       │
                        │  (反向代理/SSL)  │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
     ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
     │   Next.js SSR   │ │   FastAPI x N   │ │  静态资源 CDN   │
     │   (Vercel/SST)  │ │   (Docker/K8s)  │ │                 │
     └─────────────────┘ └────────┬────────┘ └─────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Redis 缓存    │
                         │  (会话/结果)    │
                         └─────────────────┘
```

### 8.3 环境变量

**后端 (api/.env)**:
```bash
# LLM API
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.bltcy.ai/v1

# 默认模型
DEFAULT_MODEL=gemini-2.5-flash

# 服务配置
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

**前端 (web/.env.local)**:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 9. 扩展性设计

### 9.1 添加新 Cape

1. 创建目录: `capes/my-cape/`
2. 编写定义: `cape.yaml`

```yaml
id: my-cape
name: My Custom Cape
version: "1.0.0"
description: |
  描述这个能力做什么。
  When to use: 什么时候触发这个能力。

metadata:
  tags: [custom, example]
  intents:
    - 触发关键词1
    - 触发关键词2

interface:
  input_schema:
    type: object
    properties:
      content:
        type: string
        description: 输入内容
    required: [content]

execution:
  type: llm
  timeout_seconds: 60

safety:
  risk_level: low
  estimated_cost_usd: 0.01

model_adapters:
  openai:
    model: gemini-2.5-flash
    temperature: 0.3
    system_prompt: |
      你是一个专门处理 XXX 的助手...
```

### 9.2 添加新模型适配器

1. 继承 `BaseAdapter`
2. 实现 `execute()` 方法
3. 注册到 `adapter_factory`

```python
# cape/adapters/my_adapter.py
class MyAdapter(BaseAdapter):
    @property
    def name(self) -> str:
        return "my_model"

    async def execute(
        self,
        prompt: str,
        context: ExecutionContext,
        tools: List[Dict] = None
    ) -> AdapterResponse:
        # 实现模型调用逻辑
        ...
```

### 9.3 添加新执行器

1. 继承 `BaseExecutor`
2. 实现 `execute()` 方法
3. 注册到 `CapeRuntime`

```python
# cape/runtime/executors.py
class MyExecutor(BaseExecutor):
    async def execute(
        self,
        cape: Cape,
        inputs: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        # 实现执行逻辑
        ...
```

---

## 附录

### A. 测试的模型兼容性

| 模型 | 工具调用 | LangChain Agent | 推荐度 |
|------|---------|-----------------|--------|
| gpt-4-turbo | ✅ | ✅ | ⭐⭐⭐ |
| gpt-4o | ✅ | ✅ | ⭐⭐⭐ |
| gpt-4.1 | ✅ | ✅ | ⭐⭐⭐ |
| gpt-5 | ✅ | ⚠️ 循环问题 | ⭐⭐ |
| gemini-2.5-pro | ✅ | ✅ | ⭐⭐⭐ |
| gemini-2.5-flash | ✅ | ✅ | ⭐⭐⭐ (默认) |
| gemini-2.0-flash | ✅ | ✅ | ⭐⭐⭐ |
| claude-3-5-sonnet | ✅ | ✅ | ⭐⭐⭐ |
| claude-3-5-haiku | ✅ | ✅ | ⭐⭐⭐ |
| claude-3-haiku | ✅ | ✅ | ⭐⭐⭐ |

### B. 性能指标

| 指标 | 目标 | 当前 |
|------|------|------|
| Cape 加载时间 | < 100ms | ✅ ~50ms |
| 意图匹配时间 | < 50ms | ✅ ~30ms (关键词) |
| API 响应延迟 | < 200ms (首字节) | 待测 |
| 并发用户数 | 100+ | 待测 |

### C. 相关文档

- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Next.js 文档](https://nextjs.org/docs)
- [OpenAI 工具调用](https://platform.openai.com/docs/guides/function-calling)
