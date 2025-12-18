# 元视角评估：Cape 与 Agent Platform 集成优化方案

## 一、架构对比分析

### 1.1 核心设计哲学差异

| 维度 | Cape 系统 | Agent Platform |
|------|-----------|----------------|
| **设计理念** | 能力中心化 (Capability-Centric) | 对话中心化 (Conversation-Centric) |
| **执行模式** | 声明式 YAML + 沙箱执行 | 命令式 JS + 直接调用 |
| **扩展方式** | 新增 Cape YAML 文件 | 修改代码注册工具 |
| **状态管理** | Session + FileStorage + StateManager | SessionState (内存) |
| **LLM 集成** | LangChain Agent (完整) | OpenAI Function Calling (手动) |

### 1.2 技术栈对比

```
Cape 系统                              Agent Platform
──────────────────────────────────────────────────────────────
Python 3.11+                           Node.js 20+
FastAPI                                Next.js 16
LangChain (langchain-openai)           @langchain/* (未充分使用)
Pydantic (数据模型)                     Zod (schema 验证)
YAML (能力定义)                         JS Object (工具配置)
subprocess/Docker (沙箱)               fetch API (远程调用)
文件系统存储                            无持久化
1125 行 API 代码                        ~500 行 API 代码
```

### 1.3 优劣势矩阵

#### Cape 系统优势
```
✅ 能力抽象完整 - YAML 定义 interface/execution/model_adapters
✅ 沙箱隔离执行 - 支持代码安全执行
✅ 多模型适配 - 同一 Cape 支持 Claude/GPT/通用
✅ 文件全生命周期 - 上传/处理/存储/下载完整链路
✅ 能力匹配系统 - 语义搜索 + 意图匹配
✅ 可扩展 Packs - 组织化能力包管理
```

#### Cape 系统劣势
```
❌ 部署复杂 - 需要 Python 环境 + 依赖
❌ 冷启动慢 - 首次加载 Registry 需时间
❌ 前端简陋 - 仅临时演示用途
❌ 无 UI 组件库 - 界面重用性差
```

#### Agent Platform 优势
```
✅ 前端成熟 - 完整的 Workspace/Studio/Chat UI
✅ 部署简单 - Next.js 一体化
✅ 响应快速 - 无沙箱开销
✅ UI 组件丰富 - 画布/编辑器/预览等
✅ 实时流式 - SSE 流畅体验
```

#### Agent Platform 劣势
```
❌ 能力有限 - 仅图片生成/编辑两个工具
❌ 工具耦合 - 工具定义散落在代码中
❌ 无沙箱 - 无法执行用户代码
❌ 无文件处理 - 缺少文档处理能力
❌ 状态易失 - 内存存储，重启丢失
```

---

## 二、集成瓶颈识别

### 2.1 协议差异

```
Cape SSE Events:                    Agent Platform SSE Events:
─────────────────                   ─────────────────────────
event: session                      (无)
event: cape_match                   (无)
event: cape_start                   event: status (thinking/generating)
event: content                      event: content
event: cape_end                     event: images
event: done                         event: done
event: error                        event: error
```

**问题**: SSE 事件协议不兼容，需要适配层。

### 2.2 工具定义格式差异

```yaml
# Cape YAML 格式
interface:
  input_schema:
    type: object
    properties:
      task:
        type: string
        description: 任务描述
    required: [task]
```

```javascript
// Agent Platform JS 格式
{
  name: "tool_name",
  parameters: {
    task: {
      type: "string",
      description: "任务描述",
      required: true
    }
  }
}
```

**问题**: Schema 定义格式不同，需要转换器。

### 2.3 执行模式差异

```
Cape 执行流程:
User → Agent → Tool Call → Sandbox → Output File → SSE

Agent Platform 执行流程:
User → LLM → Tool Call → API Call → JSON Response → SSE
```

**问题**: Cape 产出文件，Agent Platform 期望即时 JSON。

---

## 三、优化方案

### 3.1 架构层优化

#### 方案 A: Cape 适配 Agent Platform (推荐)

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Platform 前端                       │
│              (保持现有 UI/UX 不变)                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               统一 Tool Abstraction Layer                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Image Tools │  │ Cape Proxy  │  │ Future Tools        │  │
│  │ (原生)      │  │ (适配器)    │  │ (可扩展)            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cape 后端 (独立部署)                        │
│         能力执行 + 文件存储 + 沙箱管理                         │
└─────────────────────────────────────────────────────────────┘
```

**优点**:
- 最小改动 Agent Platform 前端
- 复用 Cape 全部能力
- 关注点分离清晰

#### 方案 B: Cape 提供 OpenAI Function Calling 兼容 API

```python
# Cape 新增 /api/tools/openai 端点
@router.get("/api/tools/openai")
def get_openai_tools():
    """返回 OpenAI Function Calling 格式的工具列表"""
    capes = registry.all()
    return [cape_to_openai_function(cape) for cape in capes]

@router.post("/api/tools/execute/{tool_name}")
def execute_tool(tool_name: str, arguments: dict):
    """执行工具并返回 JSON 结果"""
    cape_id = tool_name.replace("cape_", "")
    result = runtime.execute(cape_id, arguments)
    return {"result": result, "files": result.output_files}
```

**优点**:
- Cape 侧改动
- Agent Platform 零改动接入
- 标准化接口

### 3.2 协议层优化

#### 统一 SSE 协议

```typescript
// 统一事件类型
type SSEEventType =
  | 'session'           // 会话创建
  | 'status'            // 状态变更 (thinking/processing/generating)
  | 'tool_start'        // 工具开始执行
  | 'tool_progress'     // 工具执行进度 (0-100)
  | 'tool_end'          // 工具执行完成
  | 'content'           // 文本内容
  | 'files'             // 文件输出 (新增)
  | 'images'            // 图片输出
  | 'error'             // 错误
  | 'done';             // 完成

// 统一事件结构
interface SSEEvent {
  type: SSEEventType;
  data: {
    // 根据 type 不同
    text?: string;           // content
    files?: FileInfo[];      // files
    images?: ImageInfo[];    // images
    progress?: number;       // tool_progress
    tool_name?: string;      // tool_start/end
    error?: string;          // error
    session_id?: string;     // session/done
  };
}
```

#### 创建协议适配器

```typescript
// Agent Platform 侧
class CapeSSEAdapter {
  static transform(capeEvent: CapeSSEEvent): AgentSSEEvent {
    switch (capeEvent.type) {
      case 'cape_start':
        return { type: 'status', data: { status: 'processing' } };
      case 'cape_end':
        // 如果有文件输出，发送 files 事件
        if (capeEvent.data.output_files?.length) {
          return { type: 'files', data: { files: capeEvent.data.output_files } };
        }
        return { type: 'status', data: { status: 'done' } };
      default:
        return capeEvent; // 透传
    }
  }
}
```

### 3.3 数据层优化

#### Cape 侧: 添加即时结果模式

```yaml
# cape.yaml 新增配置
execution:
  type: hybrid
  result_mode: immediate  # 新增: immediate | file | both

  # immediate: 直接返回 JSON 结果 (适合小数据)
  # file: 只返回文件引用 (适合大文件)
  # both: 同时返回结果和文件
```

```python
# 执行时根据 result_mode 决定返回格式
class CapeRuntime:
    def execute(self, cape_id: str, inputs: dict) -> ExecutionResult:
        cape = self.registry.get(cape_id)
        result = self._run_sandbox(cape, inputs)

        if cape.execution.result_mode == 'immediate':
            return ExecutionResult(
                data=result.data,  # 直接返回数据
                files=None
            )
        elif cape.execution.result_mode == 'file':
            return ExecutionResult(
                data=None,
                files=result.output_files
            )
        else:  # both
            return ExecutionResult(
                data=result.data,
                files=result.output_files
            )
```

### 3.4 工具注册优化

#### 统一工具描述格式

```typescript
// 共享工具描述 Schema (TypeScript/Zod)
const ToolSchema = z.object({
  name: z.string(),
  description: z.string(),
  parameters: z.record(z.object({
    type: z.enum(['string', 'number', 'boolean', 'array', 'object']),
    description: z.string(),
    required: z.boolean().optional(),
    enum: z.array(z.string()).optional(),
    default: z.any().optional(),
  })),
  // 元信息
  meta: z.object({
    source: z.enum(['native', 'cape', 'mcp']),
    category: z.string(),
    tags: z.array(z.string()),
  }).optional(),
});
```

#### Cape 导出统一格式

```python
# Cape 新增 /api/tools/schema 端点
@router.get("/api/tools/schema")
def get_unified_tools():
    """返回统一格式的工具列表"""
    capes = registry.all()
    return [
        {
            "name": f"cape_{cape.id}",
            "description": cape.description,
            "parameters": convert_to_unified_schema(cape.interface.input_schema),
            "meta": {
                "source": "cape",
                "category": cape.metadata.tags[0] if cape.metadata.tags else "general",
                "tags": cape.metadata.tags,
            }
        }
        for cape in capes
    ]
```

---

## 四、推荐实施路径

### Phase 1: 协议对齐 (1 天)

```
目标: Cape API 输出 OpenAI Function Calling 兼容格式

任务:
1. Cape 新增 /api/tools/schema 端点
2. Cape 新增 /api/tools/execute 端点 (同步执行)
3. 统一 SSE 事件格式
4. 测试: curl 验证接口兼容性
```

### Phase 2: 代理层搭建 (1 天)

```
目标: Agent Platform 能调用 Cape 工具

任务:
1. 创建 /api/cape-proxy/ 路由
2. 实现 SSE 转发和事件转换
3. 实现文件上传代理
4. 测试: 通过 Agent Platform 调用 Cape
```

### Phase 3: 前端集成 (1 天)

```
目标: 完整的用户体验

任务:
1. ChatWindow 添加文件上传
2. 添加文件下载链接渲染
3. 显示 Cape 执行状态
4. 测试: 端到端文档处理流程
```

### Phase 4: 优化迭代 (持续)

```
目标: 生产就绪

任务:
1. 错误处理和重试
2. 进度显示优化
3. 文件预览功能
4. 性能监控
```

---

## 五、技术债务与长期建议

### 5.1 当前技术债务

| 债务项 | 所在项目 | 影响 | 优先级 |
|--------|----------|------|--------|
| LangChain 未充分利用 | Agent Platform | 重复造轮子 | 中 |
| 状态无持久化 | Agent Platform | 重启丢失会话 | 高 |
| 硬编码工具配置 | Agent Platform | 扩展困难 | 高 |
| 前端临时性 | Cape | 无法生产使用 | 高 |
| 缺少监控 | 两者 | 无法排障 | 中 |

### 5.2 长期架构建议

#### 建议 1: 采用 MCP (Model Context Protocol)

```
未来架构:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Claude     │     │   ChatGPT    │     │   其他 LLM   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  MCP Server   │
                    │  (统一能力)   │
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Cape     │  │ 图片工具  │  │ 其他工具  │
        │ 文档处理 │  │ 生成编辑  │  │ ...      │
        └──────────┘  └──────────┘  └──────────┘
```

**优点**: 标准化协议，多 LLM 兼容，生态支持

#### 建议 2: 微服务化 Cape

```
服务拆分:
┌──────────────────────────────────────────────────────────┐
│                     API Gateway                          │
│                  (统一入口/鉴权/限流)                     │
└──────────────────────────────────────────────────────────┘
              │              │              │
              ▼              ▼              ▼
       ┌───────────┐  ┌───────────┐  ┌───────────┐
       │ Registry  │  │ Executor  │  │ Storage   │
       │ Service   │  │ Service   │  │ Service   │
       │ (能力发现) │  │ (沙箱执行) │  │ (文件存储) │
       └───────────┘  └───────────┘  └───────────┘
```

**优点**: 独立扩缩容，故障隔离，按需部署

#### 建议 3: 共享 UI 组件库

```
创建独立 UI 包:
@skillslike/ui
├── ChatWindow
├── FileUploader
├── ToolStatus
├── FilePreview
├── MarkdownRenderer
└── ...

// 两个项目都可以使用
import { ChatWindow } from '@skillslike/ui';
```

**优点**: UI 一致性，减少重复，便于维护

---

## 六、结论

### 最优集成策略

```
短期 (本周):
  Cape 提供 OpenAI 兼容 API → Agent Platform 零改动接入

中期 (本月):
  1. 统一 SSE 协议
  2. 前端添加文件支持
  3. 状态持久化

长期 (季度):
  1. 迁移到 MCP 协议
  2. 微服务化重构
  3. 共享组件库
```

### 关键成功因素

1. **协议优先** - 先对齐协议，再集成代码
2. **最小改动** - 通过适配层桥接，避免大重构
3. **渐进增强** - 先跑通基础流程，再优化体验
4. **保持解耦** - Cape 和 Agent Platform 保持独立演进能力

---

*评估时间: 2025-12-18*
*评估范围: 架构设计、技术选型、集成方案*
