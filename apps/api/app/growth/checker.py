import asyncio
import json
import logging
import re
from html.parser import HTMLParser

import httpx

from app.growth.url_guard import safe_get

logger = logging.getLogger(__name__)

AI_BOTS = ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended', 'CCBot']
_BROWSER_UA = 'Mozilla/5.0 (EvoAgent-VisibilityBot)'


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
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await safe_get(client, url)
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
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await safe_get(client, f'https://{domain}{path}')
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
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await safe_get(client, url, headers={'User-Agent': _BROWSER_UA})
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


class _SignalParser(HTMLParser):
    """Collects title, meta descriptions, JSON-LD blocks and the first H1 from homepage HTML."""

    _END_TAGS = {'title': 'title', 'script': 'json_ld', 'h1': 'h1'}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.meta: dict[str, str] = {}
        self.json_ld: list[str] = []
        self.h1 = ''
        self._capture: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'meta':
            key = (a.get('name') or a.get('property') or '').lower()
            if key in _META_KEYS and key not in self.meta:
                self.meta[key] = a.get('content', '').strip()
        elif self._capture is None:
            if tag == 'title' and not self.title:
                self._capture = 'title'
            elif tag == 'script' and a.get('type', '').lower().startswith('application/ld+json'):
                self._capture = 'json_ld'
            elif tag == 'h1' and not self.h1:
                self._capture = 'h1'

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture is None or self._END_TAGS.get(tag) != self._capture:
            return
        text = ''.join(self._buf)
        if self._capture == 'json_ld':
            self.json_ld.append(text)
        else:
            setattr(self, self._capture, ' '.join(text.split()))
        self._capture = None
        self._buf = []


_META_KEYS = {'description', 'og:description', 'og:title', 'og:site_name'}
_JSON_LD_FIELDS = ('name', 'description', 'serviceType', 'applicationCategory', 'category')
_MAX_JSON_LD_FACTS = 5


def _json_ld_facts(blocks: list[str]) -> list[str]:
    """Flatten JSON-LD into short 'Type: field=value; ...' lines describing the site."""
    items: list = []
    for block in blocks:
        try:
            data = json.loads(block)
        except ValueError:
            continue
        stack = [data]
        while stack:
            node = stack.pop(0)
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                items.append(node)
                if isinstance(node.get('@graph'), list):
                    stack.extend(node['@graph'])

    facts = []
    for item in items:
        fields = [
            f'{f}={str(item[f]).strip()[:200]}'
            for f in _JSON_LD_FIELDS
            if isinstance(item.get(f), str) and item[f].strip()
        ]
        if fields:
            types = item.get('@type', 'Thing')
            label = ', '.join(map(str, types)) if isinstance(types, list) else str(types)
            facts.append(f"{label}: {'; '.join(fields)}")
    return facts[:_MAX_JSON_LD_FACTS]


def extract_site_signals(html: str) -> dict:
    """Pull the signals that say what a site does: title, meta/OG description, H1, JSON-LD."""
    parser = _SignalParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # malformed HTML — keep whatever was parsed
        logger.debug('extract_site_signals parse error: %s', exc)
    return {
        'title': parser.title[:200],
        'description': (parser.meta.get('description') or parser.meta.get('og:description', ''))[:300],
        'site_name': parser.meta.get('og:site_name', '')[:100],
        'h1': parser.h1[:200],
        'json_ld': _json_ld_facts(parser.json_ld),
    }


_MD_LINK_RE = re.compile(r'!?\[([^\]]*)\]\([^)]*\)')
_JINA_HEADER_PREFIXES = ('Title:', 'URL Source:', 'Markdown Content:')


def content_excerpt(text: str, limit: int = 1500) -> str:
    """
    Keep prose lines from Jina markdown, dropping navigation menus.
    Nav items are short link labels ('Tools', 'Pricing'); prose lines are long sentences.
    """
    kept: list[str] = []
    seen: set[str] = set()
    total = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(_JINA_HEADER_PREFIXES):
            continue
        plain = ' '.join(_MD_LINK_RE.sub(r'\1', stripped).strip(' *#>-|').split())
        if len(plain) < 40 or len(plain.split()) < 6 or plain in seen:
            continue
        seen.add(plain)
        kept.append(plain)
        total += len(plain) + 1
        if total >= limit:
            break
    return '\n'.join(kept)[:limit]


_GENERIC_CATEGORY_WORDS = {
    'tool', 'tools', 'software', 'product', 'products', 'platform', 'platforms', 'service',
    'services', 'app', 'apps', 'application', 'applications', 'website', 'websites', 'web',
    'saas', 'solution', 'solutions', 'technology', 'company', 'business', 'online',
    'other', 'unknown', 'none', 'null', 'n/a',
}


def clean_category(raw: object) -> str | None:
    """Normalize the LLM category; None if missing, too long, or only generic words like 'Tools'."""
    if not isinstance(raw, str):
        return None
    cat = ' '.join(raw.split()).strip(' ."\'').lower()
    cat = re.sub(r'^(the )?best ', '', cat)
    words = cat.split()
    if not words or len(words) > 6 or len(cat) > 60:
        return None
    if all(w in _GENERIC_CATEGORY_WORDS for w in words):
        return None
    return cat


def _format_signals(domain: str, signals: dict, excerpt: str) -> str:
    lines = [f'Domain: {domain}']
    for label, key in [('Page title', 'title'), ('Site name', 'site_name'),
                       ('Meta description', 'description'), ('H1', 'h1')]:
        if signals.get(key):
            lines.append(f'{label}: {signals[key]}')
    if signals.get('json_ld'):
        lines.append('JSON-LD:\n' + '\n'.join(f'- {f}' for f in signals['json_ld']))
    if excerpt:
        lines.append(f'Homepage text excerpt:\n{excerpt}')
    return '\n'.join(lines)


async def _fetch_homepage_html(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await safe_get(client, url, headers={'User-Agent': _BROWSER_UA})
            return resp.text if resp.status_code == 200 else ''
    except Exception as exc:
        logger.warning('check_recommendation homepage fetch failed for %s: %s', url, exc)
        return ''


_CATEGORY_PROMPT = (
    'Identify what product this website offers, using the homepage signals below.\n'
    'Return ONLY a JSON object with keys:\n'
    '- product_name: the brand or product name\n'
    '- category: a short, specific noun phrase (2-5 words, lowercase) for the kind of product, '
    'phrased the way a user would search after the word "best" — e.g. "frontend hosting platform", '
    '"project management software", "email marketing service". Use the established category '
    'users search for, not the site\'s current tagline or buzzwords: if you recognise the brand, '
    'use the category it is best known for. Never a navigation label or a generic word like '
    '"tools", "software" or "platform" on its own. Use null if the signals do not make it clear.\n'
    '- one_line_desc: one sentence describing what the product does\n\n'
)

_SCORING_RUBRIC = (
    'Score how likely AI assistants (ChatGPT, Claude, Perplexity, Gemini) are to recommend this '
    'product when a user asks for the best {category}.\n\n'
    'Rubric — pick the band first, then a score inside it:\n'
    '- 85-100: category leader; a default answer for this category\n'
    '- 65-84: well-known, frequently recommended option for this category\n'
    '- 40-64: credible, established option, but not usually in the top recommendations\n'
    '- 15-39: niche or little-known; rarely mentioned for this category\n'
    '- 0-14: unknown, or the product does not really fit this category\n'
    'Judge mainly on how widely known and recommended the brand is for this category. Use the '
    'search results as supporting evidence only: missing from these few results does not by itself '
    'make a well-known product niche. Then adjust within the band for how clearly the homepage '
    'communicates the category.\n\n'
    'Return ONLY JSON: {{"recommendation_score": <integer 0-100>, '
    '"reasons": ["<short reason>", "<short reason>"]}}'
)


async def check_recommendation(domain: str) -> dict:
    from app.evosmart.tools import jina_read, serper_search
    from app.chat.router import _call_with_fallback
    from app.core.config import settings

    domain = domain.replace('https://', '').replace('http://', '').strip('/')
    url = f'https://{domain}'

    def _fail(reason: str) -> dict:
        return {'domain': domain, 'recommendation_score': 0, 'reasons': [reason]}

    # Step 1: homepage signals (HTML via SSRF-safe fetch) + nav-free readable text (Jina)
    html, text = await asyncio.gather(_fetch_homepage_html(url), jina_read(url))
    signals = extract_site_signals(html)
    excerpt = content_excerpt(text or '')
    has_signals = any(signals[k] for k in ('title', 'description', 'h1', 'json_ld'))
    if not has_signals and len(excerpt) < 100:
        return _fail('Not enough homepage content to analyze.')

    # LLM call 1: infer product_name, category, one_line_desc
    try:
        raw1, _, _ = await _call_with_fallback(
            messages=[{
                'role': 'user',
                'content': _CATEGORY_PROMPT + _format_signals(domain, signals, excerpt),
            }],
            system_prompt='You are a product analyst. Return only valid JSON, no markdown, no explanation.',
            max_tokens=200,
            temperature=0,
        )
        product_info = _parse_llm_json(raw1)
        category = clean_category(product_info.get('category'))
        product_name = str(product_info.get('product_name') or domain).strip()
        one_line_desc = str(product_info.get('one_line_desc') or '').strip()
    except Exception as exc:
        logger.warning('check_recommendation LLM call 1 failed: %s', exc)
        return _fail('Could not infer product category from homepage.')

    # No real category — searching a generic term ("best tools") would give a meaningless score
    if not category:
        logger.info('check_recommendation no usable category for %s: %r', domain, product_info.get('category'))
        return _fail('Could not determine a clear product category from the homepage, so the recommendation check was skipped.')

    # Serper search — skip gracefully if key missing or call fails
    query = f'best {category}'
    search_results: list[dict] = []
    if settings.SERPER_API_KEY:
        try:
            search_results = await serper_search(query, settings.SERPER_API_KEY, num=5)
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
            f'Product: {product_name} ({domain}) — {one_line_desc}\n'
            f'Category: {category}\n\n'
            f'Top search results for "{query}":\n{serper_text}\n\n'
            + _SCORING_RUBRIC.format(category=category)
        )
        raw2, _, _ = await _call_with_fallback(
            messages=[{'role': 'user', 'content': prompt}],
            system_prompt='You are an AI visibility analyst. Return only valid JSON, no markdown.',
            max_tokens=300,
            temperature=0,
        )
        score_data = _parse_llm_json(raw2)
        rec_score = max(0, min(100, int(score_data.get('recommendation_score', 0))))
        reasons = [str(r) for r in score_data.get('reasons', []) if r]
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
