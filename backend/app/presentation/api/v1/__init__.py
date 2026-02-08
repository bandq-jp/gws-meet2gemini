from fastapi import APIRouter

from .meetings import router as meetings_router
from .structured import router as structured_router
from .zoho import router as zoho_router
from .settings import router as settings_router
from .custom_schemas import router as custom_schemas_router
from .marketing import router as marketing_router
from .marketing_v2 import router as marketing_v2_router
from .image_gen import router as image_gen_router
from .feedback import router as feedback_router

router = APIRouter()
router.include_router(meetings_router, prefix="/meetings", tags=["meetings"])
router.include_router(structured_router, prefix="/structured", tags=["structured"])
router.include_router(zoho_router, prefix="/zoho", tags=["zoho"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
router.include_router(custom_schemas_router)
router.include_router(marketing_router)
router.include_router(marketing_v2_router)
router.include_router(image_gen_router)
router.include_router(feedback_router)
