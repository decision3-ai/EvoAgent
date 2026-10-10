from fastapi import APIRouter
from app.growth.schemas import VisibilityRequest, VisibilityReport
from app.growth.checker import compute_report

router = APIRouter()


@router.post('/visibility-check', response_model=VisibilityReport)
async def visibility_check(payload: VisibilityRequest) -> VisibilityReport:
    report = await compute_report(payload.domain)

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
