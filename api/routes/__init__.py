"""
API Routes
"""

from api.routes.capes import router as capes_router
from api.routes.chat import router as chat_router
from api.routes.models import router as models_router

__all__ = ["capes_router", "chat_router", "models_router"]
