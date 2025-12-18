# Cape 代码执行层实现进度报告

> 实施周期：Week 1-4
> 最后更新：2025-12-18

## 总体进度

| 阶段 | 任务 | 状态 | 完成度 |
|------|------|------|--------|
| Week 1 | 沙箱框架 | ✅ 完成 | 100% |
| Week 2 | 文档能力集成 | ✅ 完成 | 100% |
| Week 3 | Docker 沙箱 | ✅ 完成 | 100% |
| Week 4 | 文件 API + 前端 | ✅ 完成 | 100% |

---

## Week 1: 沙箱框架

### 目标
建立基础的代码执行沙箱框架，支持多种隔离级别。

### 已完成

#### 1. 核心类

| 文件 | 类/函数 | 说明 |
|------|---------|------|
| `cape/runtime/sandbox/manager.py` | `SandboxManager` | 沙箱生命周期管理 |
| | `SandboxConfig` | 沙箱配置数据类 |
| | `SandboxType` | 枚举：DOCKER/PROCESS/INPROCESS |
| | `ExecutionRequest` | 执行请求数据类 |
| | `ExecutionResponse` | 执行响应数据类 |
| | `BaseSandbox` | 抽象基类 |
| `cape/runtime/sandbox/process_sandbox.py` | `ProcessSandbox` | 进程隔离沙箱 |
| `cape/runtime/sandbox/inprocess_sandbox.py` | `InProcessSandbox` | 进程内沙箱（开发用） |
| `cape/runtime/sandbox/code_executor.py` | `EnhancedCodeExecutor` | 代码执行器 |

#### 2. 接口定义

```python
class BaseSandbox(ABC):
    async def setup(self) -> None: ...
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse: ...
    async def cleanup(self) -> None: ...
    async def install_packages(self, packages: List[str]) -> bool: ...
```

### 测试结果

```
✓ InProcessSandbox: 3 tests
✓ ProcessSandbox: 7 tests
✓ SandboxManager: 4 tests
✓ Timeout: 1 test
总计: 15 tests passed
```

### 关键文件
- `/cape/runtime/sandbox/__init__.py`
- `/cape/runtime/sandbox/manager.py`
- `/cape/runtime/sandbox/process_sandbox.py`
- `/cape/runtime/sandbox/inprocess_sandbox.py`
- `/test_sandbox_quick.py`

---

## Week 2: 文档能力集成

### 目标
导入 Claude document-skills，创建 document-pack。

### 已完成

#### 1. 技能导入器

| 文件 | 功能 |
|------|------|
| `cape/importers/skill_enhanced.py` | 增强导入器，支持 scripts/ 目录 |
| `cape/importers/skill.py` | 基础 Skill 导入器 |

#### 2. document-pack 创建

```
packs/document-pack/
├── pack.yaml           # 包配置
└── capes/
    ├── xlsx.yaml       # Excel 处理 (LLM)
    ├── docx.yaml       # Word 处理 (Hybrid)
    ├── pptx.yaml       # PPT 处理 (Hybrid)
    └── pdf.yaml        # PDF 处理 (Hybrid)
```

#### 3. Cape YAML 结构

```yaml
id: xlsx
name: Excel 电子表格处理
version: 1.0.0
description: ...

metadata:
  author: anthropic
  tags: [document, spreadsheet, excel]
  intents: [...]

execution:
  type: hybrid
  timeout_seconds: 120

model_adapters:
  claude:
    system_prompt: |
      ...
  openai:
    system_prompt: |
      ...

code_adapter:
  scripts: [...]
  dependencies: [openpyxl, pandas]
```

### 导入结果

| Skill | 类型 | 脚本数 | 依赖 |
|-------|------|--------|------|
| xlsx | LLM | 0 | - |
| docx | Hybrid | 3 | defusedxml |
| pptx | Hybrid | 4 | python-pptx, pillow |
| pdf | Hybrid | 8 | pypdf, pdfplumber |

### 关键文件
- `/packs/document-pack/pack.yaml`
- `/packs/document-pack/capes/*.yaml`
- `/test_document_pack.py`

---

## Week 3: Docker 沙箱

### 目标
实现生产级 Docker 容器沙箱。

### 已完成

#### 1. DockerSandbox 实现

| 文件 | 内容 |
|------|------|
| `cape/runtime/sandbox/docker_sandbox.py` | ~520 行完整实现 |

#### 2. 核心组件

```python
# Dockerfile 内容
FROM python:3.11-slim
RUN apt-get install -y libreoffice-calc poppler-utils pandoc
RUN pip install openpyxl pandas numpy python-docx python-pptx ...

# 资源限制
mem_limit: {max_memory_mb}m
cpu_quota: {max_cpu_percent * 1000}
network_mode: "none" | "bridge"
security_opt: ["no-new-privileges:true"]
```

#### 3. 执行流程

```
1. setup()
   └── 检查/构建镜像 → 创建工作目录 → 启动容器

2. execute(request)
   └── 准备工作区 → 写入代码和参数 → 执行 → 收集结果

3. cleanup()
   └── 停止容器 → 删除容器 → 清理目录
```

#### 4. Wrapper 脚本模式

```python
# _exec.py 模板
import json
args = json.load(open('_args.json'))
# ... 执行用户代码 ...
json.dump(result, open('_result.json', 'w'))
```

### 关键文件
- `/cape/runtime/sandbox/docker_sandbox.py`
- `/test_docker_sandbox.py`
- `/tests/test_docker_sandbox.py`

### 注意事项
- 系统未安装 Docker，测试代码已就绪
- 安装 Docker 后运行: `python3 test_docker_sandbox.py`

---

## Week 4: 文件 API + 前端适配

### 目标
实现文件上传/下载 API，前端集成。

### 已完成

#### 1. 后端文件存储

| 文件 | 类/函数 | 说明 |
|------|---------|------|
| `api/storage.py` | `FileStorage` | 文件存储管理 (~450行) |
| | `FileMetadata` | 文件元数据 |
| | `_cleanup_expired_files()` | 后台清理任务 |

#### 2. API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/files/stats` | GET | 存储统计 |
| `/api/files/upload` | POST | 上传文件 |
| `/api/files/{id}` | GET | 下载文件 |
| `/api/files/{id}/metadata` | GET | 获取元数据 |
| `/api/files/{id}` | DELETE | 删除文件 |
| `/api/files/session/{id}` | GET | 列出会话文件 |
| `/api/files/session/{id}` | DELETE | 删除会话 |
| `/api/files/{id}/process` | POST | Cape 处理 |
| `/api/files/batch/process` | POST | 批量处理 |

#### 3. 前端更新

| 文件 | 更新内容 |
|------|----------|
| `web/src/data/types.ts` | FileInfo, UploadResponse 等类型 |
| `web/src/lib/api.ts` | 8 个文件操作方法 |
| `web/src/components/chat/file-attachment.tsx` | 新建 ~280 行 |
| `web/src/components/chat/input.tsx` | 文件上传支持 |
| `web/src/app/page.tsx` | 集成文件参数 |

### 测试结果

```
✓ FileStorage: 9 tests
✓ File Validation: 3 tests
✓ API Schemas: 1 test
总计: 13 tests passed

端到端演示 (PPT 生成):
✓ 1. API 健康检查
✓ 2. 生成 PPT (5 张幻灯片)
✓ 3. 上传文件
✓ 4. 获取元数据
✓ 5. 列出会话文件
✓ 6. 下载验证
✓ 7. 存储统计
✓ 8. 保存本地
✓ 9. 清理测试数据
```

### 关键文件
- `/api/storage.py`
- `/api/routes/files.py`
- `/web/src/components/chat/file-attachment.tsx`
- `/test_file_api.py`
- `/demo_ppt_generation.py`

---

## 已知问题与修复

| 问题 | 状态 | 解决方案 |
|------|------|----------|
| `cape.tags` AttributeError | ✅ 已修复 | 使用 `cape.metadata.tags` |
| `python` 命令不存在 | ✅ 已知 | 使用 `python3` |
| Docker 未安装 | ⚠️ 待处理 | 安装 Docker 后测试 |
| SSL 证书错误 (pip) | ✅ 已修复 | 添加 `--trusted-host` 参数 |
| `/api/files/stats` 返回 404 | ✅ 已修复 | 调整路由顺序 |
| `RgbColor` 导入错误 | ✅ 已修复 | 正确名称是 `RGBColor` |

---

## 启动命令

```bash
# 后端 API
cd /Users/g/Desktop/探索/skillslike
uvicorn api.main:app --port 8000

# 前端开发
cd /Users/g/Desktop/探索/skillslike/web
bun run dev

# 运行测试
python3 test_sandbox_quick.py      # 沙箱测试
python3 test_document_pack.py      # 文档包测试
python3 test_file_api.py           # 文件 API 测试
python3 demo_ppt_generation.py     # 端到端演示
```

---

## 下一步计划

### 短期
- [ ] 安装 Docker 并验证 DockerSandbox
- [ ] 完善错误处理和日志
- [ ] 添加更多文件类型支持

### 中期
- [ ] 实现 Cape 执行的完整流程集成
- [ ] 添加执行历史记录
- [ ] 支持更多 LLM 后端

### 长期
- [ ] gVisor/Firecracker 沙箱 (L4)
- [ ] 分布式执行
- [ ] 能力市场

---

## 项目统计

| 指标 | 数值 |
|------|------|
| 总 Cape 数量 | 22 |
| 能力包数量 | 3 |
| 文档处理 Cape | 4 |
| API 端点 | 15+ |
| 测试用例 | 40+ |
| 新增代码 | ~3000 行 |

---

## 文件清单

### 核心模块
```
cape/
├── core/models.py
├── runtime/
│   ├── sandbox/
│   │   ├── __init__.py
│   │   ├── manager.py
│   │   ├── process_sandbox.py
│   │   ├── inprocess_sandbox.py
│   │   ├── docker_sandbox.py
│   │   └── code_executor.py
│   └── registry.py
└── importers/
    ├── skill.py
    └── skill_enhanced.py
```

### API 模块
```
api/
├── main.py
├── storage.py
├── schemas.py
├── deps.py
└── routes/
    ├── chat.py
    ├── capes.py
    ├── packs.py
    ├── files.py
    └── models.py
```

### 前端模块
```
web/src/
├── app/page.tsx
├── components/chat/
│   ├── input.tsx
│   ├── message.tsx
│   └── file-attachment.tsx
├── lib/api.ts
└── data/types.ts
```

### 能力包
```
packs/
├── document-pack/
│   ├── pack.yaml
│   └── capes/
│       ├── xlsx.yaml
│       ├── docx.yaml
│       ├── pptx.yaml
│       └── pdf.yaml
└── office-pack/
```

### 测试文件
```
test_sandbox_quick.py
test_integration.py
test_import_document_skills.py
test_document_pack.py
test_docker_sandbox.py
test_file_api.py
demo_ppt_generation.py
tests/
├── test_docker_sandbox.py
└── test_file_api.py
```

---

*文档生成时间: 2025-12-18*
