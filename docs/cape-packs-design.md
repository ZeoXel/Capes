# Cape Packs 设计方案

> 以场景区分的 AI 能力包，可封入工作流、工具、脚本等，应对特定场景需求

## 1. 设计理念

### 1.1 核心洞察

预设大量 Cape 存在问题：
- 使用频次呈长尾分布，80% 几乎无人用
- 需求杂乱具体，难以契合每个用户
- 维护成本高，更新不及时

更好的策略：
```
核心预设（高频通用） + 用户自建（个性化）
```

### 1.2 Cape Pack 定义

Cape Pack（能力包）是一组相关能力的集合，包含：

| 组件 | 说明 |
|------|------|
| **Capes** | 原子能力，可独立调用 |
| **Workflows** | 预设工作流，串联多个 Cape |
| **Tools** | 外部工具集成 |
| **Scripts** | 自动化脚本 |
| **Context** | 共享上下文、模板、知识库 |

### 1.3 设计原则

1. **少而精** - 每个 Pack 只包含真正高频的能力
2. **可组合** - Cape 之间可自由组合
3. **零配置可用** - 默认行为覆盖 80% 场景
4. **渐进增强** - 高级用户可深度定制

---

## 2. Pack 架构

### 2.1 目录结构

```
packs/
├── office-pack/                    # 职场效能包
│   ├── pack.yaml                   # Pack 元信息
│   ├── capes/                      # 能力定义
│   │   ├── doc-writer.yaml
│   │   ├── slide-maker.yaml
│   │   ├── sheet-analyst.yaml
│   │   ├── meeting-assistant.yaml
│   │   └── email-composer.yaml
│   ├── workflows/                  # 工作流
│   │   └── workflows.yaml
│   ├── tools/                      # 工具配置
│   │   └── tools.yaml
│   └── context/                    # 知识上下文
│       ├── templates/
│       └── knowledge/
│
├── creator-pack/                   # 内容创作包
│   ├── pack.yaml
│   ├── capes/
│   │   ├── content-writer.yaml
│   │   ├── title-generator.yaml
│   │   ├── copywriter.yaml
│   │   ├── content-repurposer.yaml
│   │   ├── trend-analyzer.yaml
│   │   └── seo-optimizer.yaml
│   ├── workflows/
│   ├── tools/
│   └── context/
│
└── [future-packs]/
```

### 2.2 Pack 元信息 (pack.yaml)

```yaml
name: office-pack
display_name: 职场效能包
version: 1.0.0
icon: briefcase
color: "#3B82F6"

description: |
  面向职场人士的综合办公能力包

target_users:
  - 企业员工
  - 管理者
  - 行政人员

scenarios:
  - 撰写报告和方案
  - 制作演示文稿
  - 处理数据表格
  - 会议记录与跟进

capes:
  - doc-writer
  - slide-maker
  - sheet-analyst
  - meeting-assistant
  - email-composer

dependencies:
  required: []
  optional:
    - calendar-api
    - email-api
```

---

## 3. 优先级规划

### 3.1 第一批 (P0)

| Pack | 目标用户 | 核心能力 |
|------|----------|----------|
| **Office Pack** | 职场人士 | 文档、PPT、表格、会议、邮件 |
| **Creator Pack** | 内容创作者 | 写作、标题、改写、热点、SEO |

### 3.2 第二批 (P1)

| Pack | 目标用户 | 核心能力 |
|------|----------|----------|
| Developer Pack | 开发者 | 代码生成、审查、文档 |
| Research Pack | 研究者 | 调研、总结、对比 |

### 3.3 第三批 (P2)

| Pack | 目标用户 |
|------|----------|
| Sales Pack | 销售商务 |
| Student Pack | 学生 |
| 垂直行业包 | 特定行业 |

---

## 4. 技术实现

### 4.1 Cape 执行类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `llm` | 纯 LLM 生成 | 写作、分析、建议 |
| `tool` | 工具调用 | 文件操作、API 调用 |
| `code` | 代码执行 | 数据处理、计算 |
| `workflow` | 多步编排 | 复杂流程 |
| `hybrid` | 混合模式 | 综合任务 |

### 4.2 模型适配

每个 Cape 支持多模型适配：

```yaml
model_adapters:
  openai:
    model: gpt-4o
    temperature: 0.7
    system_prompt: |
      ...
  claude:
    model: claude-3-5-sonnet
    temperature: 0.7
    system_prompt: |
      ...
  generic:
    prompt_template: |
      ...
```

### 4.3 意图匹配

通过 `intents` 字段触发 Cape：

```yaml
metadata:
  intents:
    - 写报告
    - 帮我写
    - 撰写文档
```

---

## 5. 用户体验设计

### 5.1 无感使用

用户无需了解 Cape/Pack 概念：
- 直接表达需求 → 系统自动匹配合适的 Cape
- 结果直接呈现 → 无需关心执行过程

### 5.2 渐进披露

1. **新手**：直接使用，系统自动选择
2. **进阶**：可以指定 Cape，调整参数
3. **高级**：可以创建自定义 Cape

### 5.3 偏好学习（后续实现）

- 自动从对话中提取用户风格偏好
- 保存常用 prompt 为可复用片段
- 记住用户的格式、语气习惯

---

## 6. 后续规划

### 6.1 短期
- [x] 设计 Cape Pack 架构
- [ ] 实现 Office Pack 核心 Capes
- [ ] 实现 Creator Pack 核心 Capes
- [ ] 集成测试

### 6.2 中期
- [ ] Workflow 编排引擎
- [ ] 工具集成框架
- [ ] 偏好学习系统

### 6.3 长期
- [ ] Cape Builder（用户自建）
- [ ] Pack 市场/社区分享
- [ ] 多租户支持
