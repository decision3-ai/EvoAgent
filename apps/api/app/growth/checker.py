import httpx

AI_BOTS = ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended', 'CCBot']


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
