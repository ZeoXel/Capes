"""
Models Routes - Available models listing.
"""

from fastapi import APIRouter

from api.deps import AVAILABLE_MODELS, get_settings
from api.schemas import ModelInfo, ModelsResponse

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=ModelsResponse)
def list_models():
    """
    List all available LLM models.

    Returns models from OpenAI, Google (Gemini), and Anthropic (Claude).
    """
    settings = get_settings()

    models = [ModelInfo(**m) for m in AVAILABLE_MODELS]

    return ModelsResponse(
        models=models,
        default_model=settings.default_model,
    )


@router.get("/{model_id}")
def get_model(model_id: str):
    """
    Get details for a specific model.
    """
    for m in AVAILABLE_MODELS:
        if m["id"] == model_id:
            return ModelInfo(**m)

    return {"error": f"Model not found: {model_id}"}


@router.get("/providers/{provider}")
def list_models_by_provider(provider: str):
    """
    List models by provider (openai, google, anthropic).
    """
    models = [
        ModelInfo(**m)
        for m in AVAILABLE_MODELS
        if m["provider"] == provider
    ]

    return {
        "provider": provider,
        "models": models,
        "count": len(models),
    }
