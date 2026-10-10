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
