import os
import time
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseLLMClient:
    """Base class for all LLM clients."""

    def generate_chat(self, messages: List[Dict[str, str]], system_message: str = "") -> Optional[str]:
        raise NotImplementedError("Subclasses must implement generate_chat")

    def generate_response(self, prompt: str, system_message: str = "") -> Optional[str]:
        """Single-turn convenience wrapper around generate_chat."""
        return self.generate_chat([{"role": "user", "content": prompt}], system_message)


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

class GeminiClient(BaseLLMClient):
    """Client for Google Gemini (google-genai SDK)."""

    _RETRYABLE_CODES = ("429", "500", "502", "503", "504")

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from google import genai
        from google.genai import types as _types  # noqa: F401 – kept for type hints below

        self._genai = genai
        self._types = _types
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "gemini-2.5-flash-lite")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        self.client = genai.Client(api_key=self.api_key)

    def _is_retryable(self, exc: Exception) -> bool:
        msg = str(exc)
        return any(code in msg for code in self._RETRYABLE_CODES)

    def generate_chat(self, messages: List[Dict[str, str]], system_message: str = "") -> Optional[str]:
        types = self._types

        # Map "assistant" -> "model" as Gemini requires
        def _map_role(role: str) -> str:
            return "model" if role == "assistant" else role

        # History = everything except the last message
        gemini_history = [
            types.Content(role=_map_role(m["role"]), parts=[types.Part(text=m["content"])])
            for m in messages[:-1]
        ]

        config_kwargs: Dict[str, Any] = {}
        if system_message:
            config_kwargs["system_instruction"] = system_message

        try:
            chat = self.client.chats.create(
                model=self.model,
                history=gemini_history,
                config=types.GenerateContentConfig(**config_kwargs) if config_kwargs else None,
            )

            user_input = messages[-1]["content"]
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = chat.send_message(user_input)
                    return response.text
                except Exception as exc:
                    if self._is_retryable(exc) and attempt < max_retries - 1:
                        sleep_time = 2 ** (attempt + 1)
                        logging.warning(f"Retryable Gemini error (attempt {attempt+1}), sleeping {sleep_time}s: {exc}")
                        time.sleep(sleep_time)
                    else:
                        raise
        except Exception as exc:
            logging.error(f"Gemini API error: {exc}")
            return None


# ---------------------------------------------------------------------------
# Optional: Anthropic
# ---------------------------------------------------------------------------

class AnthropicClient(BaseLLMClient):
    """Client for Anthropic Claude (requires 'anthropic' package)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            import anthropic as _anthropic
        except ImportError:
            raise ImportError("Install the 'anthropic' package to use AnthropicClient.")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        self._client = _anthropic.Anthropic(api_key=self.api_key)

    def generate_chat(self, messages: List[Dict[str, str]], system_message: str = "") -> Optional[str]:
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_message or "You are a helpful assistant.",
                messages=messages,
            )
            return response.content[0].text
        except Exception as exc:
            logging.error(f"Anthropic API error: {exc}")
            return None


# ---------------------------------------------------------------------------
# Optional: Ollama
# ---------------------------------------------------------------------------

class OllamaClient(BaseLLMClient):
    """Client for local Ollama models."""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model or os.getenv("LLM_MODEL", "llama3")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def generate_chat(self, messages: List[Dict[str, str]], system_message: str = "") -> Optional[str]:
        import requests as _requests

        payload = {
            "model": self.model,
            "messages": (
                [{"role": "system", "content": system_message}] if system_message else []
            ) + messages,
            "stream": False,
        }
        try:
            resp = _requests.post(f"{self.base_url}/api/chat", json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except Exception as exc:
            logging.error(f"Ollama error: {exc}")
            return None


# ---------------------------------------------------------------------------
# Production router
# ---------------------------------------------------------------------------

class ProductionLLMClient(BaseLLMClient):
    """Routes to the correct backend based on LLM_PROVIDER env var."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if self.provider == "gemini":
            self._client = GeminiClient()
        elif self.provider == "anthropic":
            self._client = AnthropicClient()
        elif self.provider == "ollama":
            self._client = OllamaClient()
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {self.provider!r}. Choose gemini/anthropic/ollama.")

    def generate_chat(self, messages: List[Dict[str, str]], system_message: str = "") -> Optional[str]:
        return self._client.generate_chat(messages, system_message)

    def generate_response(self, prompt: str, system_message: str = "") -> Optional[str]:
        return self._client.generate_response(prompt, system_message)
