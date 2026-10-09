from fastapi import APIRouter
from app.growth.schemas import VisibilityRequest, VisibilityReport
from app.growth.checker import check_robots

router = APIRouter()


@router.post('/visibility-check', response_model=VisibilityReport)
async def visibility_check(payload: VisibilityRequest) -> VisibilityReport:
    result = await check_robots(payload.domain)
    return VisibilityReport(**result)
