"""D3RCP Bridge client — fire-and-forget x402 payment trigger."""

import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def trigger_x402_payment(
    session_id: str,
    user_id: str,
    prompt_length: int,
) -> dict | None:
    """POST to D3RCP bridge /pay endpoint. Never raises — always returns None on failure."""
    if not settings.D3RCP_BRIDGE_URL:
        return None

    url = settings.D3RCP_BRIDGE_URL.rstrip('/') + '/d3rcp/pay'
    body = {
        'session_id': session_id,
        'user_id': user_id,
        'metadata': {
            'source': 'evoagent-chat',
            'prompt_length': prompt_length,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body)
            if resp.status_code >= 400:
                logger.warning(
                    'x402_payment_failed session=%s status=%d body=%s',
                    session_id, resp.status_code, resp.text[:200],
                )
                return None
            return resp.json()
    except Exception as exc:
        logger.warning('x402_payment_error session=%s error=%s', session_id, exc)
        return None
