from fastapi import APIRouter, HTTPException, Request, status
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limits
from app.growth.schemas import VisibilityRequest, VisibilityReport
from app.growth.checker import compute_report
from app.growth.url_guard import UnsafeDomainError, validate_domain

router = APIRouter()


@router.post('/visibility-check', response_model=VisibilityReport)
async def visibility_check(request: Request, payload: VisibilityRequest) -> VisibilityReport:
    await enforce_rate_limits(
        request,
        prefix='growth',
        per_hour=settings.GROWTH_CHECK_LIMIT_PER_HOUR,
        daily_cap=settings.GROWTH_DAILY_CAP,
        daily_detail='Visibility check daily limit reached — try again tomorrow',
    )

    # SSRF guard — must pass before any outbound request (fetches, Jina, Serper, OpenRouter)
    try:
        domain = await validate_domain(payload.domain)
    except UnsafeDomainError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    report = await compute_report(domain)

    robots = report['robots']
    llms = report['llms']
    structured = report['structured']
    content = report['content']

    return VisibilityReport(
        domain=robots['domain'],
        robots_found=robots['robots_found'],
        bots=robots['bots'],
        ai_blocked_count=robots['ai_blocked_count'],
        llms_txt=llms['llms_txt'],
        llms_full_txt=llms['llms_full_txt'],
        json_ld=structured['json_ld'],
        meta_description=structured['meta_description'],
        h1=structured['h1'],
        content_readable=content['readable'],
        content_length=content['text_length'],
        score=report['score'],
        recommendation_score=report['recommendation_score'],
        recommendation_reasons=report['recommendation_reasons'],
        top_3_fixes=report['top_3_fixes'],
    )
