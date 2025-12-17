"""
Capes Routes - Cape listing and management.
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.deps import get_registry, get_runtime
from api.schemas import CapeResponse, CapeDetailResponse, MatchRequest, MatchResult, MatchResponse


class ExecuteRequest(BaseModel):
    """Request to execute a cape."""
    inputs: Dict[str, Any]


class ExecuteResponse(BaseModel):
    """Response from cape execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    cape_id: str

router = APIRouter(prefix="/api/capes", tags=["capes"])


@router.get("", response_model=List[CapeResponse])
def list_capes(
    source: Optional[str] = Query(None, description="Filter by source (native, skill)"),
    execution_type: Optional[str] = Query(None, description="Filter by type (tool, llm, workflow, hybrid)"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
):
    """
    List all available Capes.

    Supports filtering by source, execution type, and tags.
    """
    registry = get_registry()
    capes = registry.all()

    # Apply filters
    if source:
        capes = [c for c in capes if c.metadata.source.value == source]
    if execution_type:
        capes = [c for c in capes if c.execution.type.value == execution_type]
    if tag:
        capes = [c for c in capes if tag in c.metadata.tags]

    return [CapeResponse.from_cape(c) for c in capes]


@router.get("/{cape_id}", response_model=CapeDetailResponse)
def get_cape(cape_id: str):
    """
    Get detailed information about a specific Cape.
    """
    registry = get_registry()
    cape = registry.get(cape_id)

    if not cape:
        raise HTTPException(status_code=404, detail=f"Cape not found: {cape_id}")

    response = CapeResponse.from_cape(cape)
    return CapeDetailResponse(
        **response.model_dump(),
        interface=cape.interface.model_dump() if cape.interface else {},
        execution_config={
            "type": cape.execution.type.value,
            "timeout_seconds": cape.execution.timeout_seconds,
            "max_retries": cape.execution.max_retries,
            "tools_allowed": cape.execution.tools_allowed,
        },
        safety_config={
            "risk_level": cape.safety.risk_level.value,
            "estimated_cost_usd": cape.safety.estimated_cost_usd,
            "requires_approval": cape.safety.requires_approval,
            "audit_log": cape.safety.audit_log,
        },
    )


@router.post("/match", response_model=MatchResponse)
def match_capes(request: MatchRequest):
    """
    Match user query to relevant Capes.

    Uses semantic and keyword matching to find the best capabilities.
    """
    registry = get_registry()
    results = registry.match(
        query=request.query,
        top_k=request.top_k,
        threshold=request.threshold,
    )

    match_results = [
        MatchResult(
            cape_id=r["cape"].id,
            cape_name=r["cape"].name,
            score=r["score"],
            tags=r["cape"].metadata.tags,
        )
        for r in results
    ]

    return MatchResponse(
        results=match_results,
        query=request.query,
        total_capes=registry.count(),
    )


@router.get("/{cape_id}/adapters")
def get_cape_adapters(cape_id: str):
    """
    Get adapter configurations for a Cape.
    """
    registry = get_registry()
    cape = registry.get(cape_id)

    if not cape:
        raise HTTPException(status_code=404, detail=f"Cape not found: {cape_id}")

    return {
        "cape_id": cape_id,
        "adapters": cape.model_adapters,
        "supported_models": list(cape.model_adapters.keys()),
    }


@router.post("/{cape_id}/execute", response_model=ExecuteResponse)
async def execute_cape(cape_id: str, request: ExecuteRequest):
    """
    Execute a Cape directly with given inputs.

    This bypasses the LLM agent and executes the cape's tool directly.
    Useful for tool-type capes like web-search, pdf-processing, etc.
    """
    registry = get_registry()
    cape = registry.get(cape_id)

    if not cape:
        raise HTTPException(status_code=404, detail=f"Cape not found: {cape_id}")

    runtime = get_runtime()

    try:
        result = await runtime.execute(cape_id, request.inputs)

        return ExecuteResponse(
            success=result.success,
            output=result.output,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
            cape_id=cape_id,
        )
    except Exception as e:
        return ExecuteResponse(
            success=False,
            error=str(e),
            cape_id=cape_id,
        )
