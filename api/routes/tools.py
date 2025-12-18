"""
Tools Routes - OpenAI Function Calling 兼容的工具 API。

为 Agent Platform 提供标准化的工具接口，无需修改前端代码即可接入 Cape 能力。
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import get_registry, get_runtime


router = APIRouter(prefix="/api/tools", tags=["tools"])


# ============ Schema Models ============

class ToolParameter(BaseModel):
    """工具参数定义 (OpenAI 格式)"""
    type: str
    description: str
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class ToolFunction(BaseModel):
    """OpenAI Function Calling 格式的工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolDefinition(BaseModel):
    """完整的工具定义"""
    type: str = "function"
    function: ToolFunction


class ToolMeta(BaseModel):
    """工具元信息"""
    source: str  # cape, native, mcp
    category: str
    tags: List[str]
    cape_id: Optional[str] = None


class UnifiedTool(BaseModel):
    """统一工具格式 (含元信息)"""
    name: str
    description: str
    parameters: Dict[str, ToolParameter]
    meta: ToolMeta


class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    arguments: Dict[str, Any]
    session_id: Optional[str] = None


class ToolExecuteResponse(BaseModel):
    """工具执行响应"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float
    output_files: Optional[List[Dict[str, Any]]] = None


# ============ Helper Functions ============

def cape_schema_to_openai(cape) -> ToolDefinition:
    """将 Cape 的 interface 转换为 OpenAI Function Calling 格式"""
    input_schema = cape.interface.input_schema if cape.interface else {}

    properties = {}
    required = []

    if isinstance(input_schema, dict):
        props = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        for key, prop in props.items():
            properties[key] = {
                "type": prop.get("type", "string"),
                "description": prop.get("description", ""),
            }
            if "enum" in prop:
                properties[key]["enum"] = prop["enum"]

    return ToolDefinition(
        type="function",
        function=ToolFunction(
            name=f"cape_{cape.id.replace('-', '_')}",
            description=cape.description,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            }
        )
    )


def cape_to_unified(cape) -> UnifiedTool:
    """将 Cape 转换为统一工具格式"""
    input_schema = cape.interface.input_schema if cape.interface else {}

    parameters = {}
    if isinstance(input_schema, dict):
        props = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])

        for key, prop in props.items():
            parameters[key] = ToolParameter(
                type=prop.get("type", "string"),
                description=prop.get("description", ""),
                enum=prop.get("enum"),
                default=prop.get("default"),
            )

    return UnifiedTool(
        name=f"cape_{cape.id.replace('-', '_')}",
        description=cape.description,
        parameters=parameters,
        meta=ToolMeta(
            source="cape",
            category=cape.metadata.tags[0] if cape.metadata.tags else "general",
            tags=cape.metadata.tags,
            cape_id=cape.id,
        )
    )


# ============ API Endpoints ============

@router.get("/openai", response_model=List[ToolDefinition])
def get_openai_tools(
    category: Optional[str] = None,
    include: Optional[str] = None,
):
    """
    获取 OpenAI Function Calling 格式的工具列表。

    直接返回可用于 OpenAI API 的 tools 数组。

    Args:
        category: 按分类过滤 (document, office, creator)
        include: 只包含指定工具 (逗号分隔的 cape_id)

    Returns:
        OpenAI Function Calling 格式的工具数组

    Example Response:
        [
            {
                "type": "function",
                "function": {
                    "name": "cape_xlsx",
                    "description": "Excel 表格处理...",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "任务描述"}
                        },
                        "required": ["task"]
                    }
                }
            }
        ]
    """
    registry = get_registry()
    capes = registry.all()

    # 过滤
    if include:
        include_ids = [i.strip() for i in include.split(",")]
        capes = [c for c in capes if c.id in include_ids]

    if category:
        capes = [c for c in capes if category in c.metadata.tags]

    return [cape_schema_to_openai(c) for c in capes]


@router.get("/schema", response_model=List[UnifiedTool])
def get_unified_tools(
    category: Optional[str] = None,
):
    """
    获取统一格式的工具列表 (含元信息)。

    Returns:
        统一格式的工具数组，包含 meta 信息
    """
    registry = get_registry()
    capes = registry.all()

    if category:
        capes = [c for c in capes if category in c.metadata.tags]

    return [cape_to_unified(c) for c in capes]


@router.get("/categories")
def get_tool_categories():
    """
    获取所有工具分类。

    Returns:
        分类列表及各分类的工具数量
    """
    registry = get_registry()
    capes = registry.all()

    categories = {}
    for cape in capes:
        for tag in cape.metadata.tags:
            if tag not in categories:
                categories[tag] = []
            categories[tag].append(cape.id)

    return {
        "categories": [
            {"name": name, "count": len(tools), "tools": tools}
            for name, tools in categories.items()
        ],
        "total_tools": len(capes),
    }


@router.post("/execute/{tool_name}", response_model=ToolExecuteResponse)
async def execute_tool(tool_name: str, request: ToolExecuteRequest):
    """
    执行指定工具。

    工具名格式: cape_{cape_id} (下划线替代横线)

    Args:
        tool_name: 工具名称 (如 cape_xlsx, cape_pptx)
        request: 执行参数

    Returns:
        执行结果，包含 result 和可能的 output_files

    Example:
        POST /api/tools/execute/cape_xlsx
        {
            "arguments": {
                "task": "创建一个销售报表",
                "data": {"Q1": 1000, "Q2": 1500}
            }
        }
    """
    # 解析 cape_id
    if not tool_name.startswith("cape_"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tool name: {tool_name}. Expected format: cape_{{cape_id}}"
        )

    cape_id = tool_name.replace("cape_", "").replace("_", "-")

    registry = get_registry()
    cape = registry.get(cape_id)

    if not cape:
        raise HTTPException(status_code=404, detail=f"Cape not found: {cape_id}")

    runtime = get_runtime()
    start_time = time.time()

    try:
        result = await runtime.execute(cape_id, request.arguments)
        execution_time = (time.time() - start_time) * 1000

        # 提取输出文件
        output_files = None
        if hasattr(result, 'output_files') and result.output_files:
            output_files = [
                {
                    "file_id": f.file_id,
                    "name": f.original_name,
                    "url": f"/api/files/{f.file_id}",
                }
                for f in result.output_files
            ]

        return ToolExecuteResponse(
            success=result.success if hasattr(result, 'success') else True,
            result=result.output if hasattr(result, 'output') else result,
            execution_time_ms=execution_time,
            output_files=output_files,
        )

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return ToolExecuteResponse(
            success=False,
            error=str(e),
            execution_time_ms=execution_time,
        )


@router.get("/{tool_name}")
def get_tool_detail(tool_name: str):
    """
    获取单个工具的详细信息。
    """
    if not tool_name.startswith("cape_"):
        raise HTTPException(status_code=400, detail="Invalid tool name format")

    cape_id = tool_name.replace("cape_", "").replace("_", "-")

    registry = get_registry()
    cape = registry.get(cape_id)

    if not cape:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    return {
        "openai_format": cape_schema_to_openai(cape),
        "unified_format": cape_to_unified(cape),
        "raw_cape": {
            "id": cape.id,
            "name": cape.name,
            "description": cape.description,
            "interface": cape.interface.model_dump() if cape.interface else {},
            "execution": {
                "type": cape.execution.type.value,
                "timeout_seconds": cape.execution.timeout_seconds,
            },
            "model_adapters": list(cape.model_adapters.keys()),
        }
    }
