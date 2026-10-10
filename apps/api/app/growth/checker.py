import asyncio
import json
import logging

import httpx

logger = logging.getLogger(__name__)

AI_BOTS = ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended', 'CCBot']


def _parse_llm_json(raw: str) -> dict:
    """Strip optional markdown fences and parse first JSON object from LLM output."""
    text = raw.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        end = len(lines) - 1
        while end > 0 and not lines[end].strip().startswith('```'):
            end -= 1
        text = '\n'.join(lines[1:end]).strip()
    start = text.find('{')
    stop = text.rfind('}')
    if start != -1 and stop != -1:
        text = text[start:stop + 1]
    return json.loads(text)


async def check_robots(domain: str) -> dict:
    domain = domain.replace('https://', '').replace('http://', '').strip('/')
    url = f'https://{domain}/robots.txt'

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {'domain': domain, 'robots_found': False,
                        'bots': [{'bot': b, 'allowed': True} for b in AI_BOTS],
                        'ai_blocked_count': 0}
            text = resp.text
    except Exception:
        return {'domain': domain, 'robots_found': False,
                'bots': [{'bot': b, 'allowed': True} for b in AI_BOTS],
                'ai_blocked_count': 0}

    lines = [l.strip() for l in text.splitlines()]
    bots = []
    blocked = 0

    for bot in AI_BOTS:
        allowed = True
        capture = False
        for line in lines:
            low = line.lower()
            if low.startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip().lower()
                capture = (agent == bot.lower() or agent == '*')
            elif capture and low.startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                if path == '/':
                    allowed = False
        bots.append({'bot': bot, 'allowed': allowed})
        if not allowed:
            blocked += 1

    return {'domain': domain, 'robots_found': True, 'bots': bots, 'ai_blocked_count': blocked}


async def check_llms_txt(domain: str) -> dict:
    domain = domain.replace('https://', '').replace('http://', '').strip('/')
    found = {'llms_txt': False, 'llms_full_txt': False}

    for key, path in [('llms_txt', '/llms.txt'), ('llms_full_txt', '/llms-full.txt')]:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(f'https://{domain}{path}')
                if resp.status_code == 200 and len(resp.text.strip()) > 0:
                    found[key] = True
        except Exception:
            pass

    return {'domain': domain, 'llms_txt': found['llms_txt'], 'llms_full_txt': found['llms_full_txt']}


async def check_structured_data(domain: str) -> dict:
    domain = domain.replace('https://', '').replace('http://', '').strip('/')
    url = f'https://{domain}'
    result = {'domain': domain, 'json_ld': False, 'meta_description': False, 'h1': False}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0 (EvoAgent-VisibilityBot)'})
            html = resp.text.lower()
    except Exception:
        return result

    if 'application/ld+json' in html:
        result['json_ld'] = True
    if 'name="description"' in html or "name='description'" in html:
        result['meta_description'] = True
    if '<h1' in html:
        result['h1'] = True

    return result


async def check_content_readable(domain: str) -> dict:
    from app.evosmart.tools import jina_read

    domain = domain.replace('https://', '').replace('http://', '').strip('/')
    url = f'https://{domain}'
    result = {'domain': domain, 'readable': False, 'text_length': 0}

    try:
        text = await jina_read(url)
        length = len((text or '').strip())
        result['text_length'] = length
        result['readable'] = length >= 500
    except Exception:
        pass

    return result


async def check_recommendation(domain: str) -> dict:
    from app.evosmart.tools import jina_read, serper_search
    from app.chat.router import _call_with_fallback
    from app.core.config import settings

    domain = domain.replace('https://', '').replace('http://', '').strip('/')
    url = f'https://{domain}'

    def _fail(reason: str) -> dict:
        return {'domain': domain, 'recommendation_score': 0, 'reasons': [reason]}

    # Step 1: fetch homepage text
    try:
        text = await jina_read(url)
        if not text or len(text.strip()) < 100:
            return _fail('Not enough homepage content to analyze.')
    except Exception:
        return _fail('Failed to fetch homepage content.')

    # LLM call 1: infer product_name, category, one_line_desc
    try:
        raw1, _, _ = await _call_with_fallback(
            messages=[{
                'role': 'user',
                'content': (
                    'Extract product info from this homepage text. '
                    'Return ONLY a JSON object with keys: product_name, category, one_line_desc.\n\n'
                    f'Text:\n{text[:2000]}'
                ),
            }],
            system_prompt='You are a product analyst. Return only valid JSON, no markdown, no explanation.',
            max_tokens=200,
        )
        product_info = _parse_llm_json(raw1)
        category = product_info.get('category', '').strip()
        one_line_desc = product_info.get('one_line_desc', '').strip()
    except Exception as exc:
        logger.warning('check_recommendation LLM call 1 failed: %s', exc)
        return _fail('Could not infer product category from homepage.')

    # Serper search — skip gracefully if key missing or call fails
    search_results: list[dict] = []
    if settings.SERPER_API_KEY and category:
        try:
            search_results = await serper_search(
                f'best {category} tools', settings.SERPER_API_KEY, num=5
            )
        except Exception as exc:
            logger.warning('check_recommendation serper failed: %s', exc)

    # LLM call 2: recommendation_score + reasons
    try:
        serper_text = (
            '\n'.join(f"- {r['title']}: {r['snippet']}" for r in search_results)
            if search_results
            else 'No search results available.'
        )
        prompt = (
            f'Product: {one_line_desc}\n\n'
            f'Top results for "best {category} tools":\n{serper_text}\n\n'
            f'Estimate how likely AI assistants are to recommend this product when users ask about '
            f'{category} tools. '
            'Return ONLY JSON: {"recommendation_score": <0-100>, "reasons": ["reason1", "reason2"]}'
        )
        raw2, _, _ = await _call_with_fallback(
            messages=[{'role': 'user', 'content': prompt}],
            system_prompt='You are an AI visibility analyst. Return only valid JSON, no markdown.',
            max_tokens=300,
        )
        score_data = _parse_llm_json(raw2)
        rec_score = max(0, min(100, int(score_data.get('recommendation_score', 0))))
        reasons = score_data.get('reasons', [])
        return {'domain': domain, 'recommendation_score': rec_score, 'reasons': reasons}
    except Exception as exc:
        logger.warning('check_recommendation LLM call 2 failed: %s', exc)
        return _fail('Could not compute recommendation score.')


async def compute_report(domain: str) -> dict:
    robots, llms, structured, content, recommendation = await asyncio.gather(
        check_robots(domain),
        check_llms_txt(domain),
        check_structured_data(domain),
        check_content_readable(domain),
        check_recommendation(domain),
    )

    # Sub-scores
    robots_score = max(0, 20 - robots['ai_blocked_count'] * 4)

    llms_score = 0
    if llms['llms_txt']:
        llms_score += 10
    if llms['llms_full_txt']:
        llms_score += 5

    structured_score = 0
    if structured['json_ld']:
        structured_score += 10
    if structured['meta_description']:
        structured_score += 5
    if structured['h1']:
        structured_score += 5

    content_score = 20 if content['readable'] else int(min(content['text_length'] / 500, 1) * 20)
    rec_score = int(recommendation['recommendation_score'] / 100 * 25)

    total = robots_score + llms_score + structured_score + content_score + rec_score

    # Top 3 fixes: only include areas that actually have a problem (score < max)
    areas = []

    if robots['ai_blocked_count'] > 0:
        areas.append({
            'score': robots_score,
            'max': 20,
            'issue': f'{robots["ai_blocked_count"]} AI bot(s) are blocked in robots.txt',
            'fix': 'Remove or relax Disallow rules for GPTBot, ClaudeBot, PerplexityBot, Google-Extended, and CCBot.',
        })

    if llms_score < 15:
        missing_llms = []
        if not llms['llms_txt']:
            missing_llms.append('/llms.txt')
        if not llms['llms_full_txt']:
            missing_llms.append('/llms-full.txt')
        areas.append({
            'score': llms_score,
            'max': 15,
            'issue': f'Missing {" and ".join(missing_llms)}',
            'fix': 'Add /llms.txt with a concise product summary and /llms-full.txt with full documentation.',
        })

    if structured_score < 20:
        missing_tags = []
        if not structured['json_ld']:
            missing_tags.append('JSON-LD schema')
        if not structured['meta_description']:
            missing_tags.append('meta description')
        if not structured['h1']:
            missing_tags.append('H1 heading')
        areas.append({
            'score': structured_score,
            'max': 20,
            'issue': f'Missing {", ".join(missing_tags)} on homepage',
            'fix': 'Add JSON-LD schema, a meta description, and a prominent H1 heading to your homepage.',
        })

    if content_score < 20:
        areas.append({
            'score': content_score,
            'max': 20,
            'issue': f'Homepage has only {content["text_length"]} characters of readable text (500+ needed)',
            'fix': 'Ensure your homepage has 500+ words of structured, readable content for AI crawlers.',
        })

    if rec_score < 25:
        areas.append({
            'score': rec_score,
            'max': 25,
            'issue': f'Low AI recommendation visibility ({recommendation["recommendation_score"]}/100)',
            'fix': 'Create content that matches how AI assistants describe top tools in your category.',
        })

    areas_sorted = sorted(areas, key=lambda a: a['max'] - a['score'], reverse=True)
    top_3_fixes = [
        {
            'issue': a['issue'],
            'fix': a['fix'],
            'evoagent_cta': 'EvoAgent ti ovo generira i održava.',
        }
        for a in areas_sorted[:3]
    ]

    return {
        'robots': robots,
        'llms': llms,
        'structured': structured,
        'content': content,
        'recommendation': recommendation,
        'score': total,
        'recommendation_score': recommendation['recommendation_score'],
        'recommendation_reasons': recommendation['reasons'],
        'top_3_fixes': top_3_fixes,
    }
