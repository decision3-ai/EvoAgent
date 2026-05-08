"""
EvoSmart router — direct Gemini API integration.

POST /api/v1/evosmart/chat
Stateless: history is passed by the client each request.
Model: gemini-2.5-flash-preview-04-17
"""

import logging

import google.generativeai as genai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

_GEMINI_MODEL = 'gemini-2.5-flash-preview-04-17'
_TIMEOUT_SECONDS = 120


class HistoryMessage(BaseModel):
    role: str   # 'user' or 'model'
    content: str


class EvoSmartChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []


def _build_history(history: list[HistoryMessage]) -> list[dict]:
    result = []
    for msg in history:
        if msg.role not in ('user', 'model'):
            continue
        result.append({'role': msg.role, 'parts': [msg.content]})
    return result


@router.post('/chat')
async def evosmart_chat(body: EvoSmartChatRequest) -> dict:
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail='GEMINI_API_KEY not configured')

    genai.configure(api_key=settings.GEMINI_API_KEY)

    model = genai.GenerativeModel(
        model_name=_GEMINI_MODEL,
        generation_config=genai.GenerationConfig(
            temperature=1.0,
        ),
    )

    chat = model.start_chat(history=_build_history(body.history))

    response = await chat.send_message_async(
        body.message,
        stream=False,
        request_options={'timeout': _TIMEOUT_SECONDS},
    )

    return {'reply': response.text}
