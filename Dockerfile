# Cape 服务箱 Dockerfile
# 用于 Railway 部署

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目代码
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    # 核心依赖
    "pydantic>=2.5.0" \
    "pyyaml>=6.0" \
    "jinja2>=3.1.0" \
    "httpx>=0.25.0" \
    # API 服务
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "python-multipart>=0.0.6" \
    # LangChain Agent
    "langchain>=0.1.0" \
    "langchain-openai>=0.0.5" \
    # 文档处理
    "openpyxl>=3.1.0" \
    "python-pptx>=0.6.21" \
    "python-docx>=1.1.0" \
    "PyPDF2>=3.0.0" \
    "pandas>=2.0.0" \
    # Web 搜索 (Tavily primary + DDG fallback)
    "tavily-python>=0.5.0" \
    "duckduckgo-search>=6.0.0" \
    # 可选: embeddings (如需语义匹配)
    # "sentence-transformers>=2.2.2" \
    && pip install --no-cache-dir .

# 创建存储目录
RUN mkdir -p /app/storage/uploads /app/storage/outputs /app/storage/temp

# 设置环境变量
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV STORAGE_PATH=/app/storage

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
