from fastapi import APIRouter

from .meetings import router as meetings_router
from .structured import router as structured_router
from .zoho import router as zoho_router

router = APIRouter()
router.include_router(meetings_router, prefix="/meetings", tags=["meetings"])
router.include_router(structured_router, prefix="/structured", tags=["structured"])
router.include_router(zoho_router, prefix="/zoho", tags=["zoho"])
