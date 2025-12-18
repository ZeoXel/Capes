# Office Pack 详细设计

> 职场效能包 - 面向职场人士的综合办公能力包

## 1. 概述

### 1.1 目标用户
- 企业员工
- 管理者
- 行政人员
- 项目经理

### 1.2 核心场景
| 场景 | 对应 Cape | 频率 |
|------|-----------|------|
| 撰写报告/方案 | doc-writer | 高 |
| 制作 PPT | slide-maker | 高 |
| 数据分析 | sheet-analyst | 中 |
| 会议记录 | meeting-assistant | 中 |
| 邮件沟通 | email-composer | 高 |

---

## 2. Capes 定义

### 2.1 doc-writer（文档写手）

**用途**：撰写各类职场文档

**触发意图**：
- "写报告"、"写方案"、"写总结"
- "帮我写..."、"撰写..."

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task | string | ✓ | 写作任务描述 |
| type | enum | - | report/proposal/summary/memo/letter/notice |
| context | string | - | 背景信息 |
| tone | enum | - | formal/professional/casual |
| length | enum | - | brief/standard/detailed |

**输出格式**：Markdown 文档

**系统提示词要点**：
- 结构清晰，层次分明
- 语言专业，表达准确
- 根据文档类型调整风格

---

### 2.2 slide-maker（演示文稿）

**用途**：从大纲或内容生成 PPT 结构

**触发意图**：
- "做PPT"、"做幻灯片"
- "演示文稿"、"汇报材料"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic | string | ✓ | 主题 |
| content | string | - | 原始内容或大纲 |
| slides_count | int | - | 页数 (3-30) |
| style | enum | - | business/creative/minimal/academic |
| audience | string | - | 目标听众 |

**输出格式**：结构化 JSON（标题、内容、备注、视觉建议）

**系统提示词要点**：
- 每页一个核心观点
- 6×6 原则
- 故事线清晰

---

### 2.3 sheet-analyst（表格分析）

**用途**：数据处理、分析、可视化建议

**触发意图**：
- "分析数据"、"处理表格"
- "做图表"、"数据透视"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data | file/string | ✓ | 数据文件或文本 |
| task | enum | ✓ | analyze/clean/transform/visualize/formula |
| question | string | - | 具体问题 |

**输出格式**：分析报告 + 建议 + 公式

**执行类型**：hybrid（代码分析 + LLM 解读）

---

### 2.4 meeting-assistant（会议助手）

**用途**：会议记录、纪要生成、待办提取

**触发意图**：
- "会议纪要"、"会议记录"
- "整理会议"、"待办事项"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string/file | ✓ | 会议录音转写或笔记 |
| meeting_type | enum | - | standup/review/planning/brainstorm/decision |
| participants | array | - | 参会人员 |

**输出格式**：
```json
{
  "summary": "摘要",
  "key_points": ["要点1", "要点2"],
  "decisions": ["决策1"],
  "action_items": [
    {"task": "任务", "owner": "负责人", "deadline": "截止"}
  ],
  "next_steps": ["下一步"]
}
```

---

### 2.5 email-composer（邮件助手）

**用途**：撰写、回复、优化商务邮件

**触发意图**：
- "写邮件"、"回复邮件"
- "邮件怎么写"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task | enum | ✓ | compose/reply/polish/translate |
| purpose | string | ✓ | 邮件目的 |
| recipient | string | - | 收件人角色 |
| context | string | - | 背景或原邮件 |
| tone | enum | - | formal/friendly/urgent/apologetic |

**输出格式**：
```json
{
  "subject": "主题",
  "body": "正文",
  "tips": ["发送建议"]
}
```

---

## 3. Workflows

### 3.1 周报生成流 (weekly-report)

```
用户输入工作内容
    ↓
doc-writer 整理为周报格式
    ↓
用户确认/修改
    ↓
输出最终周报
```

### 3.2 会议全流程 (meeting-flow)

```
doc-writer 生成议程
    ↓
meeting-assistant 整理记录
    ↓
meeting-assistant 生成纪要
    ↓
email-composer 生成跟进邮件
```

### 3.3 数据报表流 (data-report)

```
sheet-analyst 分析数据
    ↓
sheet-analyst 生成图表建议
    ↓
doc-writer 撰写分析报告
    ↓
slide-maker 生成汇报 PPT
```

---

## 4. 知识上下文

### 4.1 模板库

| 模板 | 用途 |
|------|------|
| weekly-report.md | 工作周报 |
| project-report.md | 项目汇报 |
| meeting-minutes.md | 会议纪要 |
| business-email.md | 商务邮件 |
| proposal.md | 项目方案 |

### 4.2 知识库

| 文档 | 内容 |
|------|------|
| formal-writing.md | 公文写作规范 |
| business-etiquette.md | 商务礼仪 |
| data-viz-guide.md | 数据可视化最佳实践 |

---

## 5. 实现清单

### Phase 1：核心 Cape
- [ ] doc-writer.yaml
- [ ] slide-maker.yaml
- [ ] email-composer.yaml

### Phase 2：数据能力
- [ ] sheet-analyst.yaml
- [ ] meeting-assistant.yaml

### Phase 3：工作流
- [ ] workflows.yaml
- [ ] 模板文件

### Phase 4：集成测试
- [ ] 端到端测试
- [ ] 意图匹配测试
