"""
API Routes
"""

from api.routes.capes import router as capes_router
from api.routes.chat import router as chat_router
from api.routes.models import router as models_router
from api.routes.packs import router as packs_router
from api.routes.files import router as files_router

__all__ = [
    "capes_router",
    "chat_router",
    "models_router",
    "packs_router",
    "files_router",
]
