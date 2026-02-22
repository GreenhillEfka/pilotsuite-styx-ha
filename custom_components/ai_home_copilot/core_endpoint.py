from __future__ import annotations

from urllib.parse import urlparse


DEFAULT_CORE_PORT = 8909


def _safe_int(value: object, fallback: int) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    if 1 <= parsed <= 65535:
        return parsed
    return fallback


def normalize_host_port(
    host: object,
    port: object,
    *,
    default_port: int = DEFAULT_CORE_PORT,
) -> tuple[str, int]:
    """Normalize user-provided host/port values.

    Supports host values like:
    - ``homeassistant.local``
    - ``192.168.30.18``
    - ``192.168.30.18:8909``
    - ``http://192.168.30.18:8909``
    """
    resolved_port = _safe_int(port, default_port)
    raw_host = str(host or "").strip()
    if not raw_host:
        return "", resolved_port

    parsed = (
        urlparse(raw_host)
        if "://" in raw_host
        else urlparse(f"http://{raw_host}")
    )
    hostname = parsed.hostname or raw_host
    if parsed.port:
        resolved_port = parsed.port

    return hostname.strip(), resolved_port


def build_base_url(host: str, port: int) -> str:
    host_clean = (host or "").strip()
    if not host_clean:
        return f"http://localhost:{port}"
    return f"http://{host_clean}:{port}"


def build_candidate_hosts(
    primary_host: str,
    *,
    internal_url: str | None = None,
    external_url: str | None = None,
) -> list[str]:
    """Return ordered host candidates (primary first, then safe fallbacks)."""
    hosts: list[str] = []

    def _add(candidate: str | None) -> None:
        if not candidate:
            return
        c = candidate.strip()
        if not c:
            return
        if c not in hosts:
            hosts.append(c)

    _add(primary_host)

    for url in (internal_url, external_url):
        if not url:
            continue
        try:
            p = urlparse(url)
            _add(p.hostname)
        except Exception:
            continue

    _add("homeassistant.local")
    _add("localhost")
    _add("127.0.0.1")
    return hosts

