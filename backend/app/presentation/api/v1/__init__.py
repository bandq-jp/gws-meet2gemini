from fastapi import APIRouter

from .meetings import router as meetings_router
from .structured import router as structured_router
from .zoho import router as zoho_router
from .settings import router as settings_router
from .custom_schemas import router as custom_schemas_router

router = APIRouter()
router.include_router(meetings_router, prefix="/meetings", tags=["meetings"])
router.include_router(structured_router, prefix="/structured", tags=["structured"])
router.include_router(zoho_router, prefix="/zoho", tags=["zoho"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
router.include_router(custom_schemas_router)
router.include_router(ai_costs_router, prefix="/ai-costs", tags=["ai-costs"])
