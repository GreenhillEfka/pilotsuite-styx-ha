"""
LLM Provider abstraction for PilotSuite.

Supports multiple backends with automatic fallback:
  1. Ollama  (local, default, privacy-first)
  2. OpenAI-compatible API  (cloud fallback -- OpenClaw, OpenAI, any /v1/ endpoint)

Config (addon options -> conversation section):
  ollama_url:       http://localhost:11434
  ollama_model:     qwen3:0.6b
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
_CLOUD_MODEL_PREFIXES = (
    "gpt-",
    "o1",
    "o3",
    "claude",
    "gemini",
    "deepseek",
)
_DEFAULT_OLLAMA_MODEL = "qwen3:0.6b"


class LLMProvider:
    """Unified LLM chat interface with Ollama-first fallback to cloud."""

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """Load config from environment (called once at init and on explicit refresh)."""
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        configured_ollama_model = str(os.environ.get("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL) or "").strip()
        if not configured_ollama_model:
            configured_ollama_model = _DEFAULT_OLLAMA_MODEL
        self.cloud_api_url = os.environ.get("CLOUD_API_URL", "")
        self.cloud_api_key = os.environ.get("CLOUD_API_KEY", "")
        self.cloud_model = os.environ.get("CLOUD_MODEL", "")
        self.prefer_local = os.environ.get("PREFER_LOCAL", "true").lower() == "true"
        self.timeout = int(os.environ.get("LLM_TIMEOUT", "120"))
        self._last_ollama_issue = "unknown"
        self.ollama_model_configured = configured_ollama_model
        self.ollama_model_overridden = False
        self.ollama_model = configured_ollama_model

        # Guardrail: users sometimes set cloud-only model names (e.g. gpt-4o-mini)
        # into the local Ollama model option. That creates endless local 404s and
        # "no provider" errors despite a healthy Ollama runtime.
        if self._is_cloud_model_name(configured_ollama_model):
            self.ollama_model = _DEFAULT_OLLAMA_MODEL
            self.ollama_model_overridden = True
            logger.warning(
                "Configured OLLAMA_MODEL '%s' looks cloud-only; forcing local fallback '%s'",
                configured_ollama_model,
                self.ollama_model,
            )

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
            if self.has_cloud_fallback:
                logger.info("Ollama unavailable, falling back to cloud API")
                cloud = self._try_cloud(messages, tools, model, temperature, max_tokens)
                if cloud is not None:
                    return cloud
            return {"content": self._offline_msg(), "tool_calls": None, "provider": "none"}
        else:
            if self.has_cloud_fallback:
                result = self._try_cloud(messages, tools, model, temperature, max_tokens)
                if result is not None:
                    return result
            result = self._try_ollama(messages, tools, model, temperature, max_tokens)
            if result is not None:
                return result
            return {"content": self._offline_msg(), "tool_calls": None, "provider": "none"}

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
            "ollama_model_configured": self.ollama_model_configured,
            "ollama_model_overridden": self.ollama_model_overridden,
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
        requested_model = (model or self.ollama_model or "").strip()
        alias_models = {"", "pilotsuite", "default", "auto", "local", "ollama"}
        candidate_models: list[str] = []
        explicit_cloud_model = self._is_cloud_model_name(requested_model)

        # If a cloud-style model is requested but cloud fallback is unavailable,
        # transparently map to configured local model to avoid repeated 404 noise.
        if (
            explicit_cloud_model
            and not self.has_cloud_fallback
            and self.ollama_model
        ):
            candidate_models.append(self.ollama_model)
            logger.info(
                "Requested model '%s' looks cloud-only; using local model '%s' instead",
                requested_model,
                self.ollama_model,
            )
        elif requested_model.lower() in alias_models:
            if self.ollama_model:
                candidate_models.append(self.ollama_model)
        else:
            candidate_models.append(requested_model)
            # Explicit external model requests should fall back to cloud when configured.
            # Only try the configured local model as second chance if no cloud fallback exists.
            if not self.has_cloud_fallback and self.ollama_model and self.ollama_model not in candidate_models:
                candidate_models.append(self.ollama_model)

        if not candidate_models and self.ollama_model:
            candidate_models = [self.ollama_model]

        opts = {}
        if temperature is not None:
            opts["temperature"] = temperature
        if max_tokens is not None:
            opts["num_predict"] = max_tokens

        for i, candidate_model in enumerate(candidate_models):
            should_try_next_model = False
            payload = {"model": candidate_model, "messages": messages, "stream": False}
            if opts:
                payload["options"] = opts
            if tools:
                payload["tools"] = tools

            for attempt in range(_MAX_RETRIES + 1):
                try:
                    resp = http_requests.post(
                        f"{self.ollama_url}/api/chat", json=payload, timeout=self.timeout,
                    )
                    if resp.status_code == 200:
                        self._last_ollama_issue = ""
                        msg = resp.json().get("message", {})
                        logger.info("LLM response via ollama/%s", candidate_model)
                        return {
                            "content": msg.get("content", ""),
                            "tool_calls": msg.get("tool_calls"),
                            "provider": "ollama",
                        }

                    body = (resp.text or "")[:200]
                    if resp.status_code == 404 and "not found" in body.lower():
                        self._last_ollama_issue = f"model_not_found:{candidate_model}"
                        logger.warning("Ollama model not found: %s", candidate_model)
                        should_try_next_model = True
                        break

                    self._last_ollama_issue = f"http_{resp.status_code}"
                    logger.warning("Ollama %s: %s", resp.status_code, body)
                    break
                except http_requests.exceptions.ConnectionError:
                    self._last_ollama_issue = "unreachable"
                    if attempt < _MAX_RETRIES:
                        delay = _RETRY_BASE_DELAY * (2 ** attempt)
                        logger.info(
                            "Ollama connection failed, retry %d/%d in %.1fs",
                            attempt + 1,
                            _MAX_RETRIES,
                            delay,
                        )
                        time.sleep(delay)
                        continue
                    logger.warning("Ollama not reachable at %s after %d retries", self.ollama_url, _MAX_RETRIES)
                    break
                except http_requests.exceptions.Timeout:
                    self._last_ollama_issue = "timeout"
                    logger.warning("Ollama timeout after %ds", self.timeout)
                    break
                except Exception:
                    self._last_ollama_issue = "error"
                    logger.exception("Ollama error")
                    break

            if should_try_next_model and i + 1 < len(candidate_models):
                logger.info(
                    "Falling back from requested model '%s' to configured Ollama model '%s'",
                    requested_model,
                    candidate_models[i + 1],
                )
                continue
            if not should_try_next_model:
                break
        return None

    @staticmethod
    def _is_cloud_model_name(model: str) -> bool:
        """Best-effort detection for cloud-style model identifiers."""
        value = str(model or "").strip().lower()
        if not value:
            return False
        return value.startswith(_CLOUD_MODEL_PREFIXES)

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
        issue = str(getattr(self, "_last_ollama_issue", "") or "")
        if issue.startswith("model_not_found:"):
            model = issue.split(":", 1)[1]
            ollama_state = f"Ollama erreichbar, aber Modell '{model}' nicht installiert"
        elif issue == "timeout":
            ollama_state = f"Ollama ({self.ollama_url}) antwortet nicht rechtzeitig"
        elif issue in ("unreachable", "error", "unknown"):
            ollama_state = f"Ollama ({self.ollama_url}) nicht erreichbar"
        elif issue.startswith("http_"):
            ollama_state = f"Ollama ({self.ollama_url}) liefert {issue.replace('_', ' ').upper()}"
        else:
            ollama_state = f"Ollama ({self.ollama_url}) nicht erreichbar"

        return (
            f"Kein LLM-Provider verfuegbar. {ollama_state}"
            + (", Cloud-API nicht konfiguriert." if not self.has_cloud_fallback
               else f", Cloud-API ebenfalls nicht erreichbar.")
            + " Bitte pruefe die Addon-Konfiguration."
        )
