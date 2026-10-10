from fastapi import APIRouter
from app.growth.schemas import VisibilityRequest, VisibilityReport
from app.growth.checker import check_robots, check_llms_txt

router = APIRouter()


@router.post('/visibility-check', response_model=VisibilityReport)
async def visibility_check(payload: VisibilityRequest) -> VisibilityReport:
    robots = await check_robots(payload.domain)
    llms = await check_llms_txt(payload.domain)

    return VisibilityReport(
        domain=robots['domain'],
        robots_found=robots['robots_found'],
        bots=robots['bots'],
        ai_blocked_count=robots['ai_blocked_count'],
        llms_txt=llms['llms_txt'],
        llms_full_txt=llms['llms_full_txt'],
    )
