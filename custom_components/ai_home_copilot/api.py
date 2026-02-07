from __future__ import annotations

from dataclasses import dataclass

import aiohttp

from .const import HEADER_AUTH


@dataclass
class CopilotStatus:
    ok: bool | None
    version: str | None


class CopilotApiError(Exception):
    pass


class CopilotApiClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, token: str | None):
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._token:
            headers[HEADER_AUTH] = self._token
        return headers

    async def _get_json(self, path: str) -> dict:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise CopilotApiError(f"HTTP {resp.status} for {url}: {body[:200]}")
                return await resp.json()
        except asyncio.TimeoutError as e:
            raise CopilotApiError(f"Timeout calling {url}") from e
        except aiohttp.ClientError as e:
            raise CopilotApiError(f"Client error calling {url}: {e}") from e

    async def async_get_status(self) -> CopilotStatus:
        health: dict | None = None
        version: dict | None = None

        ok: bool | None = None
        ver: str | None = None

        try:
            health = await self._get_json("/health")
            ok_val = health.get("ok")
            ok = bool(ok_val) if ok_val is not None else None
        except CopilotApiError:
            ok = None

        try:
            version = await self._get_json("/version")
            # allow either {"version": "x"} or {"data": {"version": "x"}}
            if isinstance(version.get("version"), str):
                ver = version.get("version")
            elif isinstance(version.get("data"), dict) and isinstance(version["data"].get("version"), str):
                ver = version["data"].get("version")
            else:
                # fallback to stringified payload
                ver = None
        except CopilotApiError:
            ver = None

        return CopilotStatus(ok=ok, version=ver)


import asyncio  # keep at end to avoid circulars in some HA loaders
