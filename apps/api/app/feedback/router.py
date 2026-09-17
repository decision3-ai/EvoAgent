from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user_id
from app.feedback.models import AgentFeedback
from app.feedback.schemas import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.post('/', response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AgentFeedback:
    row = AgentFeedback(
        session_id=payload.session_id,
        user_id=user_id,
        agent_name=payload.agent_name,
        task_type=payload.task_type,
        model_used=payload.model_used,
        system_prompt=payload.system_prompt,
        user_input=payload.user_input,
        agent_output=payload.agent_output,
        feedback_type=payload.feedback_type,
        corrected_output=payload.corrected_output,
        confidence_score=payload.confidence_score,
        rating=payload.rating,
        extra_metadata=payload.extra_metadata,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
