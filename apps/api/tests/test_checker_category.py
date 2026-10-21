"""
Tests for the recommendation check's category extraction — stdlib unittest, no network.

Run inside the api container:
    docker exec agentevo_api_1 sh -c "python -m unittest discover -s tests -v"
"""

import json
import unittest
from unittest import mock

from app.core.config import settings
from app.growth import checker
from app.growth.checker import check_recommendation, clean_category, content_excerpt, extract_site_signals

FAKE_HTML = """<!doctype html>
<html>
<head>
  <title>Acme Deploy - Ship web apps in seconds</title>
  <meta name="description" content="Acme Deploy is a frontend hosting platform with global CDN and preview deployments.">
  <meta property="og:site_name" content="Acme Deploy">
  <script type="application/ld+json">
    {"@context": "https://schema.org", "@graph": [
      {"@type": "Organization", "name": "Acme Inc."},
      {"@type": ["Service", "Product"], "name": "Acme Deploy", "serviceType": "Frontend hosting platform"}
    ]}
  </script>
  <script type="application/ld+json">{ not valid json </script>
</head>
<body>
  <nav><a href="/products">Products</a><a href="/tools">Tools</a><a href="/pricing">Pricing</a></nav>
  <svg><title>logo</title></svg>
  <h1>Deploy your <span>frontend</span> &amp; ship faster</h1>
</body>
</html>
"""

# Shape of Jina Reader output: header lines, then a nav menu before any prose
FAKE_JINA = """Title: Acme Deploy - Ship web apps in seconds

URL Source: https://acme.dev/

Markdown Content:
Products

*   [Hosting](https://acme.dev/hosting)
*   [CDN](https://acme.dev/cdn)

Tools

*   [CLI](https://acme.dev/cli)

Acme Deploy builds and hosts your frontend on a global edge network with instant rollbacks.
Every pull request gets its own preview URL so your team can review changes before they ship.
"""


class ExtractSiteSignalsTest(unittest.TestCase):
    def test_extracts_title_meta_h1_and_json_ld(self):
        signals = extract_site_signals(FAKE_HTML)
        self.assertEqual(signals['title'], 'Acme Deploy - Ship web apps in seconds')
        self.assertIn('frontend hosting platform', signals['description'])
        self.assertEqual(signals['site_name'], 'Acme Deploy')
        self.assertEqual(signals['h1'], 'Deploy your frontend & ship faster')
        self.assertIn('Organization: name=Acme Inc.', signals['json_ld'])
        self.assertIn(
            'Service, Product: name=Acme Deploy; serviceType=Frontend hosting platform',
            signals['json_ld'],
        )

    def test_empty_or_garbage_html(self):
        for html in ('', '<<<not html', '<html><head><title>'):
            signals = extract_site_signals(html)
            self.assertEqual(signals['json_ld'], [])
            self.assertEqual(signals['h1'], '')


class ContentExcerptTest(unittest.TestCase):
    def test_drops_nav_menu_and_jina_header(self):
        excerpt = content_excerpt(FAKE_JINA)
        self.assertNotIn('Tools', excerpt)
        self.assertNotIn('Title:', excerpt)
        self.assertTrue(excerpt.startswith('Acme Deploy builds and hosts your frontend'))
        self.assertIn('preview URL', excerpt)


class CleanCategoryTest(unittest.TestCase):
    def test_rejects_generic_or_missing(self):
        for raw in ('Tools', 'tools', ' Software ', 'SaaS platform', 'best tools', '', None, 42,
                    'a very long category that goes on and on forever'):
            self.assertIsNone(clean_category(raw), raw)

    def test_normalizes_real_category(self):
        self.assertEqual(clean_category('Frontend Hosting Platform.'), 'frontend hosting platform')
        self.assertEqual(clean_category('best project management software'), 'project management software')


def _llm_reply(payload: dict) -> tuple[str, int, str]:
    return json.dumps(payload), 10, 'fake-model'


class CheckRecommendationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.llm = mock.AsyncMock()
        self.serper = mock.AsyncMock(return_value=[
            {'title': 'Best frontend hosting platforms', 'snippet': 'Acme Deploy, Netlify, ...', 'link': 'https://x.dev'},
        ])
        patches = [
            mock.patch.object(checker, '_fetch_homepage_html', mock.AsyncMock(return_value=FAKE_HTML)),
            mock.patch('app.evosmart.tools.jina_read', mock.AsyncMock(return_value=FAKE_JINA)),
            mock.patch('app.evosmart.tools.serper_search', self.serper),
            mock.patch('app.chat.router._call_with_fallback', self.llm),
            mock.patch.object(settings, 'SERPER_API_KEY', 'test-key'),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    async def test_category_from_signals_drives_search(self):
        self.llm.side_effect = [
            _llm_reply({'product_name': 'Acme Deploy', 'category': 'Frontend hosting platform',
                        'one_line_desc': 'Hosts frontends.'}),
            _llm_reply({'recommendation_score': 72, 'reasons': ['Listed in results']}),
        ]
        result = await check_recommendation('https://acme.dev/')

        self.assertEqual(result, {'domain': 'acme.dev', 'recommendation_score': 72, 'reasons': ['Listed in results']})
        self.serper.assert_awaited_once_with('best frontend hosting platform', 'test-key', num=5)

        # Category prompt sees the HTML signals, not the nav menu
        category_prompt = self.llm.await_args_list[0].kwargs['messages'][0]['content']
        self.assertIn('Meta description: Acme Deploy is a frontend hosting platform', category_prompt)
        self.assertIn('serviceType=Frontend hosting platform', category_prompt)
        self.assertNotIn('[CLI]', category_prompt)

        score_prompt = self.llm.await_args_list[1].kwargs['messages'][0]['content']
        self.assertIn('Category: frontend hosting platform', score_prompt)
        self.assertIn('Rubric', score_prompt)
        for call in self.llm.await_args_list:
            self.assertEqual(call.kwargs['temperature'], 0)

    async def test_generic_category_skips_search(self):
        self.llm.side_effect = [
            _llm_reply({'product_name': 'Acme', 'category': 'Tools', 'one_line_desc': ''}),
        ]
        result = await check_recommendation('acme.dev')

        self.serper.assert_not_awaited()
        self.assertEqual(self.llm.await_count, 1)
        self.assertEqual(result['recommendation_score'], 0)
        self.assertIn('skipped', result['reasons'][0])


if __name__ == '__main__':
    unittest.main()
