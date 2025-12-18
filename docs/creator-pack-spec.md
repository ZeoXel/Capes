# Creator Pack 详细设计

> 内容创作包 - 面向内容创作者的全能工具包

## 1. 概述

### 1.1 目标用户
- 自媒体创作者
- 内容运营
- 新媒体编辑
- 文案策划
- 品牌营销

### 1.2 支持平台
| 平台 | 特点 |
|------|------|
| 微信公众号 | 深度长文、金句、情绪价值 |
| 小红书 | 种草、真诚、闺蜜感、emoji |
| 抖音 | 短平快、有梗、节奏快 |
| 知乎 | 专业、深度、逻辑强 |
| 微博 | 碎片化、话题、互动 |
| B站 | 年轻化、梗文化 |
| 头条 | 数字+利益+猎奇 |

### 1.3 核心场景
| 场景 | 对应 Cape | 频率 |
|------|-----------|------|
| 写文章/笔记 | content-writer | 高 |
| 起标题 | title-generator | 高 |
| 写营销文案 | copywriter | 中 |
| 一稿多发 | content-repurposer | 中 |
| 追热点 | trend-analyzer | 中 |
| SEO 优化 | seo-optimizer | 低 |

---

## 2. Capes 定义

### 2.1 content-writer（内容写手）

**用途**：创作各类自媒体内容

**触发意图**：
- "写文章"、"写内容"、"帮我写"
- "写一篇关于..."

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| topic | string | ✓ | 主题或选题 |
| platform | enum | ✓ | wechat/xiaohongshu/douyin/zhihu/weibo/bilibili/toutiao |
| content_type | enum | - | tutorial/story/list/review/opinion/news |
| tone | enum | - | professional/casual/humorous/emotional/provocative |
| length | enum | - | short/medium/long |
| reference | string | - | 参考资料 |

**平台适配规则**：

| 平台 | 长度 | 风格 | 结构 |
|------|------|------|------|
| 公众号 | 1500-3000字 | 深度、有料、金句多 | 开头悬念→层层递进→金句收尾 |
| 小红书 | 300-800字 | 真诚、种草、闺蜜感 | 痛点共鸣→解决方案→效果展示 |
| 抖音 | 100-300字 | 直接、有梗、节奏快 | 3秒钩子→痛点→干货→引导互动 |
| 知乎 | 1000-5000字 | 专业、有深度、逻辑强 | 先说结论→展开论证→总结升华 |

**输出格式**：
```json
{
  "title": "标题",
  "hook": "开头钩子",
  "body": "正文内容",
  "call_to_action": "互动引导",
  "hashtags": ["标签1", "标签2"]
}
```

---

### 2.2 title-generator（爆款标题）

**用途**：生成高点击率标题

**触发意图**：
- "起标题"、"标题怎么写"
- "爆款标题"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content_summary | string | ✓ | 内容摘要 |
| platform | enum | - | 目标平台 |
| style | enum | - | curiosity/benefit/fear/how-to/list/story/contrast |
| count | int | - | 生成数量 (3-10) |

**标题风格**：
| 风格 | 说明 | 示例 |
|------|------|------|
| curiosity | 好奇型 | "99%的人不知道的..." |
| benefit | 利益型 | "学会这3招，效率翻倍" |
| fear | 恐惧型 | "再不改掉这个习惯，你就..." |
| how-to | 方法型 | "如何在30天内..." |
| list | 数字型 | "2024年必看的10个..." |
| contrast | 对比型 | "从月薪3K到3W，我做对了..." |

**输出格式**：
```json
{
  "titles": [
    {
      "text": "标题文本",
      "style": "benefit",
      "score": 8,
      "reason": "使用了数字+利益点"
    }
  ]
}
```

---

### 2.3 copywriter（营销文案）

**用途**：撰写广告、推广、转化类文案

**触发意图**：
- "写文案"、"广告文案"
- "推广文案"、"卖点提炼"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| product | string | ✓ | 产品/服务名称 |
| selling_points | array | - | 核心卖点 |
| target_audience | string | - | 目标人群 |
| scenario | enum | ✓ | ad/landing/social/email/product_desc/slogan |
| tone | enum | - | professional/playful/luxury/urgent/warm |
| length | enum | - | ultra-short/short/medium/long |

**文案框架**：
- AIDA: 注意→兴趣→欲望→行动
- PAS: 痛点→放大→解决方案
- FAB: 特性→优势→利益
- 4U: 紧迫→独特→超具体→有用

**输出格式**：
```json
{
  "headline": "主标题",
  "subheadline": "副标题",
  "body": "正文",
  "cta": "行动召唤",
  "variations": []
}
```

---

### 2.4 content-repurposer（内容改写）

**用途**：一稿多用，适配多平台分发

**触发意图**：
- "改写"、"换个平台发"
- "一稿多发"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| original | string | ✓ | 原始内容 |
| source_platform | string | - | 原内容平台 |
| target_platforms | array | ✓ | 目标平台列表 |
| preserve | enum | - | meaning/style/both |

**输出格式**：
```json
{
  "versions": [
    {
      "platform": "xiaohongshu",
      "title": "适配标题",
      "content": "适配内容",
      "hashtags": ["标签"],
      "adaptation_notes": "改编说明"
    }
  ]
}
```

---

### 2.5 trend-analyzer（热点分析）

**用途**：追踪热点，分析选题机会

**触发意图**：
- "今天有什么热点"
- "热点分析"、"选题建议"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| domain | string | - | 关注领域 |
| platforms | array | - | 数据来源平台 |
| purpose | enum | - | content_idea/hot_chase/trend_report |

**执行类型**：hybrid（工具抓取 + LLM 分析）

**输出格式**：
```json
{
  "trends": [
    {
      "topic": "话题",
      "heat": 85,
      "trend": "rising",
      "content_angles": ["角度1", "角度2"],
      "risk_level": "safe"
    }
  ],
  "recommendations": [
    {
      "topic": "推荐选题",
      "angle": "切入角度",
      "reason": "推荐原因",
      "urgency": "today"
    }
  ]
}
```

---

### 2.6 seo-optimizer（SEO 优化）

**用途**：优化内容的搜索可见性

**触发意图**：
- "SEO优化"、"关键词"
- "搜索优化"

**输入参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | string | ✓ | 待优化内容 |
| target_keywords | array | - | 目标关键词 |
| platform | enum | - | google/baidu/xiaohongshu/zhihu/douyin |

**输出格式**：
```json
{
  "score": 75,
  "issues": ["问题1"],
  "suggestions": ["建议1"],
  "optimized_title": "优化后标题",
  "optimized_content": "优化后内容",
  "keyword_density": {},
  "meta_description": "摘要"
}
```

---

## 3. Workflows

### 3.1 爆款内容生成流 (viral-content-flow)

```
用户输入主题
    ↓
trend-analyzer 分析热度和角度
    ↓
title-generator 生成 5 个标题
    ↓
用户选择标题
    ↓
content-writer 创作内容
    ↓
seo-optimizer 优化检查
    ↓
用户确认/修改
```

### 3.2 多平台分发流 (multi-platform-flow)

```
用户提供原始内容
    ↓
content-repurposer 生成各平台版本
    ↓
title-generator 为每个平台生成标题
    ↓
输出所有版本
```

### 3.3 每日选题流 (daily-topic-flow)

```
trend-analyzer 获取今日热点
    ↓
结合用户领域分析切入点
    ↓
输出选题推荐列表
```

---

## 4. 知识上下文

### 4.1 平台指南

| 文档 | 内容 |
|------|------|
| xiaohongshu-guide.md | 小红书运营规范 |
| wechat-guide.md | 公众号运营指南 |
| douyin-guide.md | 抖音内容规范 |
| zhihu-guide.md | 知乎写作指南 |

### 4.2 模板库

| 模板 | 用途 |
|------|------|
| 种草模板 | 小红书产品推荐 |
| 教程模板 | 干货教程类 |
| 测评模板 | 产品测评 |
| 观点模板 | 观点输出类 |

### 4.3 素材库

| 素材 | 用途 |
|------|------|
| title-formulas.md | 标题公式库 |
| hooks.md | 开头钩子库 |
| cta.md | CTA 话术库 |

---

## 5. 实现清单

### Phase 1：核心写作
- [ ] content-writer.yaml
- [ ] title-generator.yaml
- [ ] copywriter.yaml

### Phase 2：分发改写
- [ ] content-repurposer.yaml
- [ ] seo-optimizer.yaml

### Phase 3：热点分析
- [ ] trend-analyzer.yaml
- [ ] 热点数据接入

### Phase 4：工作流
- [ ] workflows.yaml
- [ ] 知识库文件
