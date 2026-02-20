"""
LLM Provider abstraction for PilotSuite.

Supports multiple backends with automatic fallback:
  1. Ollama  (local, default, privacy-first)
  2. OpenAI-compatible API  (cloud fallback -- OpenClaw, OpenAI, any /v1/ endpoint)

Config (addon options -> conversation section):
  ollama_url:       http://localhost:11434
  ollama_model:     qwen3:4b
  cloud_api_url:    https://api.openai.com/v1  (or OpenClaw URL)
  cloud_api_key:    sk-...
  cloud_model:      gpt-4o-mini  (or openclaw model)
  prefer_local:     true  (try Ollama first, fall back to cloud)
"""

import logging
import os
import time

import requests as http_requests

logger = logging.getLogger(__name__)

# Retry settings for transient failures
_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 1.0  # seconds


class LLMProvider:
    """Unified LLM chat interface with Ollama-first fallback to cloud."""

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """Load config from environment (called once at init and on explicit refresh)."""
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
        self.cloud_api_url = os.environ.get("CLOUD_API_URL", "")
        self.cloud_api_key = os.environ.get("CLOUD_API_KEY", "")
        self.cloud_model = os.environ.get("CLOUD_MODEL", "")
        self.prefer_local = os.environ.get("PREFER_LOCAL", "true").lower() == "true"
        self.timeout = int(os.environ.get("LLM_TIMEOUT", "120"))

    def reload_config(self):
        """Explicitly reload config from environment (e.g. after settings change)."""
        self._load_config()
        logger.info("LLM provider config reloaded")

    def chat(self, messages: list, tools: list = None,
             model: str = None, temperature: float = None,
             max_tokens: int = None) -> dict:
        """Send a chat request. Returns Ollama-style message dict.

        Returns:
            {"content": str, "tool_calls": list|None, "provider": str}
        """
        if self.prefer_local:
            result = self._try_ollama(messages, tools, model, temperature, max_tokens)
            if result is not None:
                return result
            if self.cloud_api_url:
                logger.info("Ollama unavailable, falling back to cloud API")
                return self._try_cloud(messages, tools, model, temperature, max_tokens)
            return {"content": self._offline_msg(), "tool_calls": None, "provider": "none"}
        else:
            if self.cloud_api_url:
                result = self._try_cloud(messages, tools, model, temperature, max_tokens)
                if result is not None:
                    return result
            return self._try_ollama(messages, tools, model, temperature, max_tokens) or {
                "content": self._offline_msg(), "tool_calls": None, "provider": "none"
            }

    @property
    def active_model(self) -> str:
        return self.ollama_model

    @property
    def has_cloud_fallback(self) -> bool:
        return bool(self.cloud_api_url and self.cloud_api_key)

    def status(self) -> dict:
        """Return provider status info."""
        ollama_ok = self._ping_ollama()
        return {
            "ollama_available": ollama_ok,
            "ollama_url": self.ollama_url,
            "ollama_model": self.ollama_model,
            "cloud_configured": self.has_cloud_fallback,
            "cloud_api_url": self.cloud_api_url or None,
            "cloud_model": self.cloud_model or None,
            "prefer_local": self.prefer_local,
            "active_provider": "ollama" if ollama_ok else ("cloud" if self.has_cloud_fallback else "none"),
        }

    # ------------------------------------------------------------------
    # Ollama backend
    # ------------------------------------------------------------------

    def _ping_ollama(self) -> bool:
        try:
            resp = http_requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def _try_ollama(self, messages, tools, model, temperature, max_tokens):
        model = model or self.ollama_model
        payload = {"model": model, "messages": messages, "stream": False}
        opts = {}
        if temperature is not None:
            opts["temperature"] = temperature
        if max_tokens is not None:
            opts["num_predict"] = max_tokens
        if opts:
            payload["options"] = opts
        if tools:
            payload["tools"] = tools

        last_err = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = http_requests.post(
                    f"{self.ollama_url}/api/chat", json=payload, timeout=self.timeout,
                )
                if resp.status_code != 200:
                    logger.warning("Ollama %s: %s", resp.status_code, resp.text[:200])
                    return None
                msg = resp.json().get("message", {})
                logger.info("LLM response via ollama/%s", model)
                return {
                    "content": msg.get("content", ""),
                    "tool_calls": msg.get("tool_calls"),
                    "provider": "ollama",
                }
            except http_requests.exceptions.ConnectionError as e:
                last_err = e
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.info("Ollama connection failed, retry %d/%d in %.1fs",
                                attempt + 1, _MAX_RETRIES, delay)
                    time.sleep(delay)
                    continue
                logger.warning("Ollama not reachable at %s after %d retries",
                               self.ollama_url, _MAX_RETRIES)
                return None
            except http_requests.exceptions.Timeout:
                logger.warning("Ollama timeout after %ds", self.timeout)
                return None
            except Exception:
                logger.exception("Ollama error")
                return None
        return None

    # ------------------------------------------------------------------
    # Cloud / OpenAI-compatible backend (OpenClaw, OpenAI, etc.)
    # ------------------------------------------------------------------

    def _try_cloud(self, messages, tools, model, temperature, max_tokens):
        if not self.cloud_api_url or not self.cloud_api_key:
            return None

        model = model or self.cloud_model or "gpt-4o-mini"
        headers = {
            "Authorization": f"Bearer {self.cloud_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages, "stream": False}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        url = self.cloud_api_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/chat/completions"

        try:
            resp = http_requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                # Sanitize: don't log full response which might echo the API key
                logger.warning("Cloud API %s (model=%s)", resp.status_code, model)
                return None
            data = resp.json()
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            logger.info("LLM response via cloud/%s", model)
            return {
                "content": msg.get("content", ""),
                "tool_calls": msg.get("tool_calls"),
                "provider": "cloud",
            }
        except Exception:
            logger.exception("Cloud API error (url=%s)", url)
            return None

    def _offline_msg(self) -> str:
        return (
            f"Kein LLM-Provider verfuegbar. Ollama ({self.ollama_url}) nicht erreichbar"
            + (", Cloud-API nicht konfiguriert." if not self.cloud_api_url
               else f", Cloud-API ebenfalls nicht erreichbar.")
            + " Bitte pruefe die Addon-Konfiguration."
        )
