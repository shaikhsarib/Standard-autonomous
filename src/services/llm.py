import os
import time
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from config.settings import settings

logger = logging.getLogger(__name__)

class BaseLLMClient(ABC):
    @abstractmethod
    def generate_chat(self, messages: List[Dict[str, str]], system_message: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def generate_response(self, prompt: str, system_message: Optional[str] = None) -> str:
        pass


class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or settings.llm_model or os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self.client = None
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize google-genai client: {e}")

    def _call_with_retry(self, fn, max_retries: int = 3, backoff: float = 2.0):
        for attempt in range(max_retries):
            try:
                return fn()
            except Exception as e:
                err_str = str(e).lower()
                if ("429" in err_str or "quota" in err_str or "503" in err_str) and attempt < max_retries - 1:
                    sleep_time = backoff * (2 ** attempt)
                    logger.warning(f"Gemini API rate limited/busy. Retrying in {sleep_time}s... Error: {e}")
                    time.sleep(sleep_time)
                else:
                    raise

    def generate_chat(self, messages: List[Dict[str, str]], system_message: Optional[str] = None) -> str:
        if not self.client:
            return self._fallback_chat(messages, system_message)

        prompt_parts = []
        if system_message:
            prompt_parts.append(f"System: {system_message}\n")
        for m in messages:
            role = "Model" if m.get("role") in ["model", "assistant"] else "User"
            prompt_parts.append(f"{role}: {m.get('content', '')}")
            
        full_prompt = "\n".join(prompt_parts)
        
        def _call():
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )
            return response.text or ""

        try:
            return self._call_with_retry(_call)
        except Exception as e:
            logger.error(f"Gemini generate_chat error: {e}")
            return self._fallback_chat(messages, system_message)

    def generate_response(self, prompt: str, system_message: Optional[str] = None) -> str:
        if not self.client:
            return self._fallback_response(prompt)

        full_prompt = f"System: {system_message}\n\n{prompt}" if system_message else prompt

        def _call():
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )
            return response.text or ""

        try:
            return self._call_with_retry(_call)
        except Exception as e:
            logger.error(f"Gemini generate_response error: {e}")
            return self._fallback_response(prompt)

    def _fallback_chat(self, messages: List[Dict[str, str]], system_message: Optional[str] = None) -> str:
        return "Thank you for sharing that. We specialize in custom software development and automated lead generation to accelerate your business growth. What is your primary objective this quarter?"

    def _fallback_response(self, prompt: str) -> str:
        return '{"pain_points": ["No online booking system", "High manual labor", "Low digital visibility"], "business_loss": "Losing 10-15 potential clients weekly", "whatsapp_message": "Hi, noticed your business is growing! Would you be open to seeing a demo of how automated booking can boost revenue?", "email_subject": "Quick idea for your business growth", "email_body": "Hi there,\\n\\nI noticed you have great reviews in the area. We help local businesses automate bookings and reach more customers directly on WhatsApp and Google.\\n\\nWould you be open to a quick 5-min chat this week?\\n\\nBest regards,\\nGrowth Team"}'


class OpenAILikeClient(BaseLLMClient):
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o-mini"):
        import openai
        self.model = model
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def generate_chat(self, messages: List[Dict[str, str]], system_message: Optional[str] = None) -> str:
        msgs = []
        if system_message:
            msgs.append({"role": "system", "content": system_message})
        for m in messages:
            role = "assistant" if m.get("role") in ["model", "assistant"] else "user"
            msgs.append({"role": role, "content": m.get("content", "")})

        res = self.client.chat.completions.create(model=self.model, messages=msgs)
        return res.choices[0].message.content or ""

    def generate_response(self, prompt: str, system_message: Optional[str] = None) -> str:
        msgs = []
        if system_message:
            msgs.append({"role": "system", "content": system_message})
        msgs.append({"role": "user", "content": prompt})
        res = self.client.chat.completions.create(model=self.model, messages=msgs)
        return res.choices[0].message.content or ""


class ProductionLLMClient:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or settings.llm_provider or "gemini").lower()
        self.model = model or settings.llm_model

        if self.provider == "gemini":
            self.client = GeminiClient(model=self.model)
        elif self.provider in ["groq"] and (settings.groq_api_key or os.getenv("GROQ_API_KEY")):
            self.client = OpenAILikeClient(
                api_key=settings.groq_api_key or os.getenv("GROQ_API_KEY", ""),
                base_url="https://api.groq.com/openai/v1",
                model=self.model or settings.groq_model or "llama-3.3-70b-versatile"
            )
        elif self.provider in ["nvidia", "nvidia_nim", "nim"] and (settings.nvidia_nim_api_key or os.getenv("NVIDIA_NIM_API_KEY")):
            self.client = OpenAILikeClient(
                api_key=settings.nvidia_nim_api_key or os.getenv("NVIDIA_NIM_API_KEY", ""),
                base_url="https://integrate.api.nvidia.com/v1",
                model=self.model or settings.nvidia_nim_model or "meta/llama-3.3-70b-instruct"
            )
        elif self.provider == "openai" and os.getenv("OPENAI_API_KEY"):
            self.client = OpenAILikeClient(
                api_key=os.getenv("OPENAI_API_KEY"),
                model=self.model or "gpt-4o-mini"
            )
        else:
            self.client = GeminiClient(model=self.model)

    def generate_chat(self, messages: List[Dict[str, str]], system_message: Optional[str] = None) -> str:
        return self.client.generate_chat(messages, system_message)

    def generate_response(self, prompt: str, system_message: Optional[str] = None) -> str:
        return self.client.generate_response(prompt, system_message)

    def generate(self, prompt: str, system_message: Optional[str] = None) -> str:
        return self.client.generate_response(prompt, system_message)


def get_fast_client() -> ProductionLLMClient:
    """Ultra-low latency engine (Groq Llama 3.3 70B @ 500 tok/s or Gemini Flash)."""
    if settings.groq_api_key or os.getenv("GROQ_API_KEY"):
        return ProductionLLMClient(provider="groq", model=settings.groq_model)
    return ProductionLLMClient(provider="gemini", model=settings.llm_model)


def get_reasoning_client() -> ProductionLLMClient:
    """Deep reasoning engine for HyperResearch (NVIDIA NIM Nemotron/Llama 3.3 or Gemini Pro)."""
    if settings.nvidia_nim_api_key or os.getenv("NVIDIA_NIM_API_KEY"):
        return ProductionLLMClient(provider="nvidia", model=settings.nvidia_nim_model)
    return ProductionLLMClient(provider="gemini", model=settings.llm_model)


llm_client = ProductionLLMClient()

