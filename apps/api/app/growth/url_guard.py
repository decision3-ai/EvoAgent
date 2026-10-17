"""
SSRF guard for the public visibility check.

validate_domain   — syntactic check + DNS resolution; every resolved address must be public
safe_get          — GET pinned to the validated IP (no DNS rebinding), manual redirects
                    with each hop re-validated, body capped, total time capped
"""

import asyncio
import ipaddress
import re
import socket

import httpx

from app.core.config import settings

_DNS_TIMEOUT_SECONDS = 5
_TOTAL_TIMEOUT_SECONDS = 15  # per safe_get call, including all redirects
_MAX_REDIRECTS = 5
# Dropped when re-wrapping a streamed body: it is already decoded and possibly truncated
_STALE_BODY_HEADERS = ('content-encoding', 'content-length', 'transfer-encoding')
_LABEL_RE = re.compile(r'^(?!-)[a-z0-9-]{1,63}(?<!-)$')
_TLD_RE = re.compile(r'^(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$')


class UnsafeDomainError(ValueError):
    """Domain/URL is not a plain public hostname — message is safe to return to the client."""


def _check_hostname(host: str) -> str:
    """Return the normalized ASCII hostname or raise UnsafeDomainError."""
    if not host:
        raise UnsafeDomainError('Domain is empty.')
    try:
        ipaddress.ip_address(host.strip('[]'))
    except ValueError:
        pass
    else:
        raise UnsafeDomainError('IP addresses are not allowed — enter a domain name.')
    if ':' in host:
        raise UnsafeDomainError('Ports are not allowed — enter a plain domain like example.com.')
    if any(c in host for c in '/?#\\'):
        raise UnsafeDomainError('Paths and query strings are not allowed — enter a plain domain like example.com.')
    if '@' in host or any(c.isspace() for c in host):
        raise UnsafeDomainError('Invalid domain — enter a plain domain like example.com.')

    try:
        host = host.encode('idna').decode('ascii').lower()
    except UnicodeError:
        raise UnsafeDomainError('Invalid domain name.')

    if host == 'localhost' or host.endswith('.localhost'):
        raise UnsafeDomainError('localhost is not allowed.')

    labels = host.split('.')
    if (
        len(host) > 253
        or len(labels) < 2
        or not all(_LABEL_RE.match(label) for label in labels)
        or not _TLD_RE.match(labels[-1])  # also rejects numeric forms like 127.1 or 2130706433
    ):
        raise UnsafeDomainError('Invalid domain name — enter a plain domain like example.com.')
    return host


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address):
        # Unwrap IPv6 forms that embed an IPv4 address
        embedded = ip.ipv4_mapped or ip.sixtofour or (ip.teredo[1] if ip.teredo else None)
        if embedded is not None and not _is_public_ip(embedded):
            return False
    return ip.is_global and not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # includes 169.254.169.254 metadata endpoint
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _getaddrinfo(host: str) -> list[tuple]:
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        loop.getaddrinfo(host, None, type=socket.SOCK_STREAM),
        timeout=_DNS_TIMEOUT_SECONDS,
    )


async def _resolve_public(host: str) -> str:
    """
    Resolve host via DNS; raise if it does not resolve or ANY address is non-public.
    Returns one validated address for the caller to connect to — IPv4 preferred,
    since our hosting may not have IPv6 connectivity.
    """
    try:
        infos = await _getaddrinfo(host)
    except (socket.gaierror, asyncio.TimeoutError, UnicodeError):
        raise UnsafeDomainError(f'Domain {host} could not be resolved.')

    if not infos:
        raise UnsafeDomainError(f'Domain {host} could not be resolved.')

    addresses = []
    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0].split('%', 1)[0])  # drop IPv6 scope id
        if not _is_public_ip(ip):
            raise UnsafeDomainError(f'Domain {host} resolves to a non-public address.')
        addresses.append(ip)
    preferred = next((ip for ip in addresses if ip.version == 4), addresses[0])
    return str(preferred)


async def validate_domain(raw: str) -> str:
    """
    Validate user input as a plain public hostname. Returns the normalized hostname.
    Accepts an optional http(s):// prefix and a single trailing slash; nothing else.
    """
    host = raw.strip().lower()
    for scheme in ('https://', 'http://'):
        if host.startswith(scheme):
            host = host[len(scheme):]
            break
    if host.endswith('/'):
        host = host[:-1]

    host = _check_hostname(host)
    await _resolve_public(host)
    return host


async def validate_url(url: str) -> tuple[httpx.URL, str]:
    """
    Validate a full URL (e.g. a redirect target): http(s), default port, public host.
    Returns (URL with normalized host, validated IP to connect to).
    """
    try:
        parsed = httpx.URL(url)
    except Exception:
        raise UnsafeDomainError('Invalid URL.')
    if parsed.scheme not in ('http', 'https'):
        raise UnsafeDomainError('Only http and https URLs are allowed.')
    if parsed.port is not None:  # httpx reports None for the scheme's default port
        raise UnsafeDomainError('Non-default ports are not allowed.')
    if parsed.userinfo:
        raise UnsafeDomainError('Credentials in URLs are not allowed.')
    host = _check_hostname(parsed.host)
    ip = await _resolve_public(host)
    return parsed.copy_with(host=host), ip


async def _read_capped(resp: httpx.Response) -> bytes:
    """Read the decoded body, stopping once GROWTH_MAX_RESPONSE_BYTES have been read."""
    limit = settings.GROWTH_MAX_RESPONSE_BYTES
    body = bytearray()
    async for chunk in resp.aiter_bytes():
        body += chunk
        if len(body) >= limit:
            break
    return bytes(body[:limit])


async def safe_get(
    client: httpx.AsyncClient, url: str, *, headers: dict[str, str] | None = None
) -> httpx.Response:
    """
    GET with SSRF protections:
      - DNS is resolved once per hop and the connection is pinned to the validated IP;
        Host header and TLS SNI/certificate verification still use the original hostname
      - redirects are followed manually, each hop re-validated
      - body is truncated at GROWTH_MAX_RESPONSE_BYTES
      - the whole call, redirects included, is capped at _TOTAL_TIMEOUT_SECONDS (TimeoutError)
    """
    async with asyncio.timeout(_TOTAL_TIMEOUT_SECONDS):
        for _ in range(_MAX_REDIRECTS + 1):
            target, ip = await validate_url(url)
            async with client.stream(
                'GET',
                target.copy_with(host=ip),
                headers={**(headers or {}), 'Host': target.host},
                follow_redirects=False,
                extensions={'sni_hostname': target.host},
            ) as resp:
                if resp.is_redirect:
                    url = str(target.join(resp.headers['location']))
                    continue
                body = await _read_capped(resp)
                return httpx.Response(
                    resp.status_code,
                    headers=[
                        (k, v) for k, v in resp.headers.multi_items()
                        if k.lower() not in _STALE_BODY_HEADERS
                    ],
                    content=body,
                    request=httpx.Request('GET', target),
                )
        raise UnsafeDomainError('Too many redirects.')
