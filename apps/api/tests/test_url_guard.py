"""
Tests for app.growth.url_guard — stdlib unittest, no network.

Run inside the api container:
    docker exec agentevo_api_1 sh -c "python -m unittest discover -s tests -v"
"""

import asyncio
import socket
import unittest
from unittest import mock

import httpx

from app.core.config import settings
from app.growth import url_guard
from app.growth.url_guard import UnsafeDomainError, safe_get, validate_domain

PUBLIC_IP = '93.184.215.14'
PUBLIC_IPV6 = '2606:2800:21f:cb07:6820:80da:af6b:8b2c'


def fake_dns(table: dict[str, str | list[str]]):
    """Replacement for url_guard._getaddrinfo backed by a hostname -> IP(s) table, in DNS order."""
    async def _getaddrinfo(host: str) -> list[tuple]:
        if host not in table:
            raise socket.gaierror('not found')
        ips = table[host] if isinstance(table[host], list) else [table[host]]
        return [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', (ip, 0, 0, 0)) if ':' in ip
            else (socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 0))
            for ip in ips
        ]
    return _getaddrinfo


class UrlGuardTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests: list[httpx.Request] = []

    def client(self, handler) -> httpx.AsyncClient:
        def record(request: httpx.Request):
            self.requests.append(request)
            return handler(request)
        return httpx.AsyncClient(transport=httpx.MockTransport(record))

    async def test_domain_resolving_to_loopback_is_rejected(self):
        with mock.patch.object(url_guard, '_getaddrinfo', fake_dns({'evil.example': '127.0.0.1'})):
            with self.assertRaisesRegex(UnsafeDomainError, 'non-public'):
                await validate_domain('evil.example')
            async with self.client(lambda r: httpx.Response(200)) as client:
                with self.assertRaisesRegex(UnsafeDomainError, 'non-public'):
                    await safe_get(client, 'https://evil.example/')
        self.assertEqual(self.requests, [])  # nothing was sent

    async def test_redirect_to_metadata_ip_is_rejected(self):
        dns = fake_dns({'good.example': PUBLIC_IP})
        redirect = lambda r: httpx.Response(302, headers={'Location': 'http://169.254.169.254/latest/meta-data/'})
        with mock.patch.object(url_guard, '_getaddrinfo', dns):
            async with self.client(redirect) as client:
                with self.assertRaisesRegex(UnsafeDomainError, 'IP addresses are not allowed'):
                    await safe_get(client, 'https://good.example/')
        self.assertEqual(len(self.requests), 1)  # the redirect target was never requested

    async def test_redirect_to_hostname_resolving_to_metadata_ip_is_rejected(self):
        dns = fake_dns({'good.example': PUBLIC_IP, 'meta.example': '169.254.169.254'})
        redirect = lambda r: httpx.Response(301, headers={'Location': 'https://meta.example/'})
        with mock.patch.object(url_guard, '_getaddrinfo', dns):
            async with self.client(redirect) as client:
                with self.assertRaisesRegex(UnsafeDomainError, 'non-public'):
                    await safe_get(client, 'https://good.example/')
        self.assertEqual(len(self.requests), 1)

    async def test_oversized_response_is_truncated_and_not_fully_read(self):
        chunk = b'x' * 64 * 1024
        sent = 0

        async def endless_body():
            nonlocal sent
            for _ in range(1000):  # ~64 MB if fully consumed
                sent += len(chunk)
                yield chunk

        with mock.patch.object(url_guard, '_getaddrinfo', fake_dns({'big.example': PUBLIC_IP})):
            async with self.client(lambda r: httpx.Response(200, content=endless_body())) as client:
                resp = await safe_get(client, 'https://big.example/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.content), settings.GROWTH_MAX_RESPONSE_BYTES)
        self.assertLess(sent, settings.GROWTH_MAX_RESPONSE_BYTES + 2 * len(chunk))

    async def test_connection_is_pinned_to_validated_ip(self):
        with mock.patch.object(url_guard, '_getaddrinfo', fake_dns({'good.example': PUBLIC_IP})):
            async with self.client(lambda r: httpx.Response(200, text='ok')) as client:
                resp = await safe_get(client, 'https://good.example/robots.txt')
        sent = self.requests[0]
        self.assertEqual(sent.url.host, PUBLIC_IP)
        self.assertEqual(sent.url.path, '/robots.txt')
        self.assertEqual(sent.headers['Host'], 'good.example')
        self.assertEqual(sent.extensions['sni_hostname'], 'good.example')
        self.assertEqual(resp.text, 'ok')
        self.assertEqual(resp.url.host, 'good.example')

    async def test_ipv4_preferred_even_when_ipv6_resolves_first(self):
        dns = fake_dns({'dual.example': [PUBLIC_IPV6, PUBLIC_IP]})
        with mock.patch.object(url_guard, '_getaddrinfo', dns):
            async with self.client(lambda r: httpx.Response(200)) as client:
                await safe_get(client, 'https://dual.example/')
        self.assertEqual(self.requests[0].url.host, PUBLIC_IP)

    async def test_ipv6_used_when_no_ipv4(self):
        with mock.patch.object(url_guard, '_getaddrinfo', fake_dns({'v6.example': [PUBLIC_IPV6]})):
            async with self.client(lambda r: httpx.Response(200)) as client:
                await safe_get(client, 'https://v6.example/')
        self.assertEqual(self.requests[0].url.host, PUBLIC_IPV6)

    async def test_all_addresses_validated_even_if_ipv4_is_public(self):
        dns = fake_dns({'mixed.example': [PUBLIC_IP, '::1']})
        with mock.patch.object(url_guard, '_getaddrinfo', dns):
            async with self.client(lambda r: httpx.Response(200)) as client:
                with self.assertRaisesRegex(UnsafeDomainError, 'non-public'):
                    await safe_get(client, 'https://mixed.example/')
        self.assertEqual(self.requests, [])

    async def test_total_timeout_covers_redirect_chain(self):
        async def slow_redirect(request):
            await asyncio.sleep(0.3)
            return httpx.Response(302, headers={'Location': '/next'})

        with mock.patch.object(url_guard, '_getaddrinfo', fake_dns({'slow.example': PUBLIC_IP})), \
                mock.patch.object(url_guard, '_TOTAL_TIMEOUT_SECONDS', 0.5):
            async with httpx.AsyncClient(transport=httpx.MockTransport(slow_redirect)) as client:
                with self.assertRaises(TimeoutError):
                    await safe_get(client, 'https://slow.example/')


if __name__ == '__main__':
    unittest.main()
