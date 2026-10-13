"""Bounded HTTPS retrieval with DNS pinned to validated public addresses.

httpcore connects to the validated IP; sni_hostname preserves TLS verification
against the original hostname. Redirects and environment proxies are disabled.
Never include upstream exceptions or URLs in user-facing messages.
"""
import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

import httpx

LIMIT = 2_000_000


def destination(raw):
    if len(raw) > 2048 or any(ord(c) < 33 for c in raw):
        raise ValueError("Invalid source URL")
    parsed = urlsplit(raw)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment or parsed.port not in (None, 443)):
        raise ValueError("A public HTTPS source on port 443 is required")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global
                            or ipaddress.ip_address(a[4][0]).is_multicast for a in addresses):
        raise ValueError("Private or reserved destinations are blocked")
    address = addresses[0][4][0]
    authority = f"[{address}]" if ":" in address else address
    return parsed.hostname, urlunsplit(("https", authority, parsed.path or "/", parsed.query, ""))


async def fetch(raw):
    return await asyncio.wait_for(_fetch(raw), timeout=20)


async def _fetch(raw):
    host, pinned = await asyncio.to_thread(destination, raw)
    async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=5), follow_redirects=False,
                                 trust_env=False) as client:
        async with client.stream("GET", pinned, headers={"Host": host},
                                 extensions={"sni_hostname": host}) as response:
            if response.status_code != 200:
                raise ValueError("Source request failed")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > LIMIT:
                    raise ValueError("Source exceeds 2 MB")
            return bytes(body)
