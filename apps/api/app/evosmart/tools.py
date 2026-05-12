"""
EvoSmart research tools.

serper_search — Google search via Serper API
jina_read    — Clean text extraction via Jina Reader (no key needed)
"""

import logging

import httpx

logger = logging.getLogger(__name__)

_SERPER_URL = 'https://google.serper.dev/search'
_JINA_BASE = 'https://r.jina.ai/'
_MAX_CONTENT_CHARS = 3000


async def serper_search(query: str, api_key: str, num: int = 5) -> list[dict]:
    """Return top `num` organic results: [{title, link, snippet}]."""
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    payload = {'q': query, 'num': num}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(_SERPER_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get('organic', [])[:num]:
        results.append({
            'title': item.get('title', ''),
            'link': item.get('link', ''),
            'snippet': item.get('snippet', ''),
        })
    return results


async def jina_read(url: str) -> str:
    """Extract clean text from a URL via Jina Reader. Returns up to _MAX_CONTENT_CHARS."""
    jina_url = f'{_JINA_BASE}{url}'
    headers = {'Accept': 'text/plain'}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(jina_url, headers=headers)
            resp.raise_for_status()
            return resp.text[:_MAX_CONTENT_CHARS]
    except Exception as exc:
        logger.warning('jina_read failed for %s: %s', url, exc)
        return ''
