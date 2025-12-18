"""
Cape API Server - Main FastAPI application.

Usage:
    cd skillslike
    uvicorn api.main:app --reload --port 8000

Or with environment variables:
    OPENAI_API_KEY=sk-xxx OPENAI_BASE_URL=https://api.bltcy.ai/v1 uvicorn api.main:app --reload
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_settings, get_registry, get_runtime
from api.routes.capes import router as capes_router
from api.routes.chat import router as chat_router
from api.routes.models import router as models_router
from api.routes.packs import router as packs_router
from api.schemas import StatsResponse

# Create app
app = FastAPI(
    title="Cape API",
    description="API for Cape (Capability Package) System - Model-agnostic capability execution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(capes_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(packs_router)


@app.get("/")
def root():
    """API root - health check and info."""
    registry = get_registry()
    return {
        "name": "Cape API",
        "version": "1.0.0",
        "status": "healthy",
        "total_capes": registry.count(),
        "docs": "/docs",
    }


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    """Get system statistics."""
    registry = get_registry()
    runtime = get_runtime()

    summary = registry.summary()
    metrics = runtime.get_metrics()

    return StatsResponse(
        total_capes=summary["total"],
        total_packs=summary.get("total_packs", 0),
        total_executions=metrics["execution_count"],
        success_rate=100.0,  # TODO: track actual success rate
        avg_execution_time_ms=0,  # TODO: track
        total_tokens=metrics["total_tokens"],
        total_cost_usd=metrics["total_cost_usd"],
        by_source=summary["by_source"],
        by_type=summary["by_type"],
        by_pack=summary.get("by_pack", {}),
    )


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    print("🚀 Cape API starting...")

    # Pre-load registry and runtime
    registry = get_registry()
    runtime = get_runtime()

    print(f"✅ Loaded {registry.count()} Capes")
    print(f"✅ Runtime initialized with {len(runtime._tool_registry)} tools")
    print(f"✅ Default model: {settings.default_model}")
    print("🎉 Cape API ready!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
