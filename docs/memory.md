# LangChain Agent 多工具 / 多模型统一上下文实践参考

> 目标：  
> 在 **同一对话框** 中，实现  
> - 多 capes 调用  
> - 多模型切换（GPT / Claude / 本地）  
> - 上下文语义连贯  
> - 可控、可扩展、可 Debug 的记忆体系  
>
> 核心原则：**上下文不是 LLM 的功能，而是系统的一等公民**

---

## 一、核心结论（先记住）

- ❌ 不依赖 LangChain 内置 Memory
- ❌ 不把历史对话“全量塞回模型”
- ✅ 自己维护 Conversation State
- ✅ 不同模型 ≠ 不同上下文，只是 **不同投喂策略**

---

## 二、整体架构图（文字版）


User Input

↓

Conversation State Manager  ←——（统一上下文）

↓

Prompt Builder（按模型适配）

↓

Agent / LLM

↓

Tool Calls（携带 context）

↓

Observation

↓

State Update（摘要 / 事实 / 任务）

````
---

## 三、Conversation State（核心数据结构）

### 1. 总体结构

```ts
type ConversationState = {
  session_id: string
  turns: Turn[]          // 原始对话（冷数据）
  summaries: Summary[]   // 语义摘要（热数据）
  facts: Fact[]          // 稳定事实
  tasks: Task[]          // 当前目标 / 子目标
}
````

---

### **2. Turn（完整但不常用）**

```
type Turn = {
  role: "user" | "assistant" | "tool"
  content: string
  timestamp: number
}
```

用途：

- Debug
    
- 回放
    
- 重建摘要
    
- 不建议每次都喂给 LLM
    

---

### **3. Summary（真正的上下文）**

```
type Summary = {
  content: string
  covers_turns: number[]
  created_at: number
}
```

示例：

```
用户正在构建一个 LangChain Agent 平台，
目标是支持多模型与多 tools 的统一上下文。
当前关注点是：上下文记忆的工程实现方式。
```

> ⚠️ Summary 是 **LLM 的主要上下文来源**

---

### **4. Fact（长期记忆）**

```
type Fact = {
  key: string
  value: string
}
```

示例：

```
{
  "key": "tech_stack",
  "value": "Next.js + LangChain + Supabase"
}
```

特点：

- 稳定
    
- 可直接结构化
    
- 长期保留
    

---

### **5. Task（对齐 Agent 行为）**

```
type Task = {
  id: string
  goal: string
  status: "active" | "done" | "paused"
}
```

示例：

```
当前任务：设计统一的上下文记忆架构
```

---

## **四、Prompt Builder（最关键）**

  

> Prompt Builder ≠ Prompt Template

> 而是 **上下文裁剪与拼装器**

---

### **1. 通用 Prompt Builder**

```
function buildPrompt(
  state: ConversationState,
  userInput: string
) {
  return `
你是一个多工具 AI Agent。

【对话背景摘要】
${latestSummaries(state)}

【已知事实】
${factsToText(state.facts)}

【当前任务】
${activeTasksToText(state.tasks)}

【用户输入】
${userInput}
`
}
```

---

### **2. 不同模型，不同裁剪策略**

|**模型**|**策略**|
|---|---|
|Claude|多条 Summary + Facts|
|GPT-4|Summary + 最近 3～5 轮|
|本地模型|单条 Summary|

```
function buildClaudePrompt(state, input) {}
function buildGPTPrompt(state, input) {}
```

> ❗State 不变，Prompt 变化

---

## **五、Tool 不是“裸函数”**

  

### **错误示范 ❌**

```
tool.run({ query })
```

### **正确示范 ✅**

```
tool.run({
  query,
  context: {
    summary: latestSummaries(state),
    facts: state.facts,
    task: currentTask(state)
  }
})
```

原则：

  

> **Tool 也应该是 context-aware 的 Agent 组件**

---

## **六、上下文更新机制（每一轮）**

  

### **标准流程**

1. 追加 Turn
    
2. 判断是否需要生成新 Summary
    
3. 抽取 Facts / Tasks（可选）
    
4. 更新 State
    

---

### **示例：生成新 Summary**

```
const summary = await summarizerLLM.invoke(`
请将以下对话压缩为一条上下文摘要：

${recentTurns(state)}
`)
```

> 建议用：

  

- 同模型
    
- 或更便宜的模型
    
- 温度低
    

---

## **七、为什么不用 LangChain Memory**

|**原因**|**说明**|
|---|---|
|Agent 绑定|Memory 绑定 executor|
|不可控|自动塞历史|
|多模型割裂|不可共享|
|难 Debug|不透明|

> LangChain Memory 适合 Demo，不适合系统级 Agent

---

## **八、推荐的落地顺序**

1. ✅ 实现 ConversationState
    
2. ✅ 写 Prompt Builder
    
3. ✅ Tool 接受 context
    
4. ⏳ 再考虑 LangGraph / Planner
    
5. ❌ 最后才考虑“智能记忆”
    

---

## **九、你最终会获得什么**

- 模型可随意替换
    
- Tool 可独立演化
    
- 上下文可 Debug / 回放
    
- Agent 行为可解释
    

  

> **这是 Agent 工程和 Prompt 工程的分水岭**

---

## **十、延伸阅读 / 下一步**

- ConversationState → 存 Supabase / Redis
    
- Summary → 分层（短 / 中 / 长期）
    
- Task → Planner / Executor
    
- State → 多 Agent 共享（协作）
    

---

## **结语**

  

> **不要让 LLM 管记忆**

> **让系统管，LLM 只是使用者**
