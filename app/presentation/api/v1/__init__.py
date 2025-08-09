from fastapi import APIRouter

from .meetings import router as meetings_router
from .structured import router as structured_router

router = APIRouter()
router.include_router(meetings_router, prefix="/meetings", tags=["meetings"])
router.include_router(structured_router, prefix="/structured", tags=["structured"])
