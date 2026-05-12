"""
EvoSmart router — Deep Research Engine powered by Gemini.

POST /api/v1/evosmart/chat
Stateless: history is passed by the client each request.
Public endpoint — no JWT auth.

Flow:
  1. Quick routing call: does this message need research? (YES/NO)
  2a. NO  → direct Gemini chat, same as before.
  2b. YES → Serper search → parallel Jina reads → Gemini with context.
"""

import asyncio
import logging

import google.generativeai as genai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.evosmart.tools import jina_read, serper_search

logger = logging.getLogger(__name__)
router = APIRouter()

_GEMINI_MODEL = 'gemini-2.5-flash'
_TIMEOUT_SECONDS = 120
_RESEARCH_SOURCES = 3

# Configure once at module load
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

_ROUTER_PROMPT = """\
You are a query classifier. Reply with exactly one word: YES or NO.
YES = the user wants current facts, news, research, prices, events, or anything \
that requires up-to-date information from the web.
NO = greeting, small talk, math, coding help, opinions, or anything answerable \
from training data alone.
Query: {message}"""

_RESEARCH_SYSTEM = """\
You are a direct research engine. Rules:
- Lead with the answer, no preamble.
- Cite sources inline as [1], [2], etc.
- No flattery, no filler, no sycophancy.
- Be concise. If you don't know, say so."""


class HistoryMessage(BaseModel):
    role: str   # 'user' or 'model'
    content: str


class EvoSmartChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = []


def _build_history(history: list[HistoryMessage]) -> list[dict]:
    return [
        {'role': msg.role, 'parts': [msg.content]}
        for msg in history
        if msg.role in ('user', 'model')
    ]


async def _needs_research(message: str) -> bool:
    """Single-token routing call — cheap and fast."""
    try:
        model = genai.GenerativeModel(
            model_name=_GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=1024,  # thinking model needs budget before output
            ),
        )
        resp = await model.generate_content_async(
            _ROUTER_PROMPT.format(message=message),
            request_options={'timeout': 20},
        )
        candidate = resp.candidates[0]
        text = ''.join(
            p.text for p in candidate.content.parts
            if hasattr(p, 'text') and not getattr(p, 'thought', False)
        )
        return text.strip().upper().startswith('YES')
    except Exception as exc:
        logger.warning('_needs_research failed, defaulting to NO: %s', exc)
        return False


async def _build_research_context(message: str) -> tuple[str, list[dict]]:
    """Search + parallel Jina reads. Returns (context_block, sources)."""
    if not settings.SERPER_API_KEY:
        raise HTTPException(status_code=503, detail='SERPER_API_KEY not configured')

    results = await serper_search(message, settings.SERPER_API_KEY, num=_RESEARCH_SOURCES)
    if not results:
        return '', []

    urls = [r['link'] for r in results]
    contents = await asyncio.gather(*[jina_read(url) for url in urls])

    blocks = []
    for i, (res, content) in enumerate(zip(results, contents), start=1):
        snippet = content.strip() or res['snippet']
        blocks.append(
            f"[{i}] {res['title']}\nURL: {res['link']}\n{snippet}"
        )

    context = 'RESEARCH SOURCES:\n\n' + '\n\n---\n\n'.join(blocks)
    return context, results


@router.post('/chat')
async def evosmart_chat(body: EvoSmartChatRequest) -> dict:
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail='GEMINI_API_KEY not configured')

    research_mode = await _needs_research(body.message)

    if research_mode:
        context, sources = await _build_research_context(body.message)

        system_with_context = f"{_RESEARCH_SYSTEM}\n\n{context}" if context else _RESEARCH_SYSTEM

        model = genai.GenerativeModel(
            model_name=_GEMINI_MODEL,
            system_instruction=system_with_context,
            generation_config=genai.GenerationConfig(temperature=0.7),
        )
        chat = model.start_chat(history=_build_history(body.history))
        response = await chat.send_message_async(
            body.message,
            stream=False,
            request_options={'timeout': _TIMEOUT_SECONDS},
        )
        return {
            'reply': response.text,
            'research_mode': True,
            'sources': [{'title': s['title'], 'url': s['link']} for s in sources],
        }

    # Direct chat — no tools, no overhead
    model = genai.GenerativeModel(
        model_name=_GEMINI_MODEL,
        generation_config=genai.GenerationConfig(temperature=1.0),
    )
    chat = model.start_chat(history=_build_history(body.history))
    response = await chat.send_message_async(
        body.message,
        stream=False,
        request_options={'timeout': _TIMEOUT_SECONDS},
    )
    return {'reply': response.text, 'research_mode': False, 'sources': []}
