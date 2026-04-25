import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import List, Optional, Dict, Callable, Any

from google import genai
from google.genai import types

import config


class GeminiClient:
    """Gemini API wrapper with retries, native chat, vision, and L2 template support."""

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 2
    REQUEST_TIMEOUT_SECONDS = 30
    MODEL = "gemma-3-27b-it"

    def __init__(self):
        self._client = None
        self._initialized = False

    def _ensure_init(self):
        if self._initialized:
            return
        try:
            self._client = genai.Client(api_key=config.GEMINI_API_KEY)
            self._initialized = True
        except Exception as e:
            print(f"Gemini init failed: {e}")

    @staticmethod
    def _response_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        candidates = getattr(response, "candidates", None)
        if candidates:
            parts = []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                if not content:
                    continue
                for part in getattr(content, "parts", []) or []:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        parts.append(part_text)
            if parts:
                return "\n".join(parts)

        return str(response)

    def _call_with_retry(
        self,
        fn,
        *args,
        timeout_seconds: Optional[int] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> str:
        last_error = None
        timeout_seconds = timeout_seconds or self.REQUEST_TIMEOUT_SECONDS

        for attempt in range(self.MAX_RETRIES):
            try:
                if status_callback and attempt > 0:
                    status_callback(f"Retrying API request ({attempt + 1}/{self.MAX_RETRIES})...")

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(fn, *args, **kwargs)
                    try:
                        response = future.result(timeout=timeout_seconds)
                    except FuturesTimeoutError:
                        future.cancel()
                        return f"[Error: Timeout after {timeout_seconds}s]"

                return self._response_text(response)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if "429" in error_str or "resource" in error_str or "quota" in error_str or "500" in error_str or "503" in error_str:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    if status_callback:
                        status_callback(f"Waiting for API... retrying in {delay}s ({attempt + 1}/{self.MAX_RETRIES})")
                    print(f"Rate limit/transient error (attempt {attempt + 1}/{self.MAX_RETRIES}), retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                return f"[Error: {e}]"
        return f"[Error: API failed after {self.MAX_RETRIES} retries. Last error: {last_error}]"

    # ── L2 mode: simple prompt ──────────────────────────────────────

    def send_prompt(
        self,
        prompt_text: str,
        status_callback: Optional[Callable[[str], None]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        self._ensure_init()
        if not self._client:
            return "[Error: Gemini not initialized. Check API key.]"
        return self._call_with_retry(
            self._client.models.generate_content,
            model=self.MODEL,
            contents=prompt_text,
            timeout_seconds=timeout_seconds,
            status_callback=status_callback,
            config=types.GenerateContentConfig(temperature=0.4, max_output_tokens=4096),
        )

    def send_with_template(
        self,
        template_path: str,
        data: str,
        extra_data: Optional[Dict[str, str]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """L2 mode: load a prompt template, replace placeholders, send.

        Falls back to cached L2 responses when the API is unavailable.
        """
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
        except FileNotFoundError:
            return f"[Error: Template not found: {template_path}]"

        template = template.replace("{{DATA}}", data)
        if extra_data:
            for key, value in extra_data.items():
                template = template.replace(f"{{{{{key}}}}}", value)

        l2_guardrails = (
            "L2 MODE CONSTRAINTS:\n"
            "- Single-shot answer only (no multi-turn interaction).\n"
            "- Plain text narrative output only.\n"
            "- Do not output JSON, markdown tables, or code blocks.\n"
            "- Do not claim access to computational tools."
        )

        response = self.send_prompt(
            f"{l2_guardrails}\n\n{template}",
            status_callback=status_callback,
            timeout_seconds=timeout_seconds,
        )

        if response.startswith("[Error"):
            from engine.cache import L2ResponseCache
            import os
            template_name = os.path.splitext(os.path.basename(template_path))[0]
            cached = L2ResponseCache().get_cached(template_name, data)
            if cached:
                return cached

        return response

    # ── L3 mode: context-aware conversation ─────────────────────────

    def send_with_context(
        self,
        system_prompt: str,
        user_message: str,
        history: Optional[List[dict]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        self._ensure_init()
        if not self._client:
            return "[Error: Gemini not initialized. Check API key.]"

        try:
            gemini_history = []
            is_gemma = "gemma" in self.MODEL.lower()

            if history:
                for i, msg in enumerate(history):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    gemini_role = "model" if role in ("agent", "model", "assistant") else "user"

                    if is_gemma and i == 0 and gemini_role == "user":
                        content = f"System Instructions:\n{system_prompt}\n\nUser Input:\n{content}"

                    gemini_history.append(
                        types.Content(role=gemini_role, parts=[types.Part.from_text(text=content)])
                    )

            if is_gemma and not history:
                user_message = f"System Instructions:\n{system_prompt}\n\nUser Input:\n{user_message}"

            config_kwargs = {
                "temperature": 0.4,
                "max_output_tokens": 4096,
            }
            if not is_gemma:
                config_kwargs["system_instruction"] = system_prompt

            chat = self._client.chats.create(
                model=self.MODEL,
                config=types.GenerateContentConfig(**config_kwargs),
                history=gemini_history,
            )
            return self._call_with_retry(
                chat.send_message,
                user_message,
                timeout_seconds=timeout_seconds,
                status_callback=status_callback,
            )

        except Exception as e:
            return f"[Error: {e}]"

    # ── Vision mode ─────────────────────────────────────────────────

    def parse_image(
        self,
        image_path: str,
        prompt: str,
        status_callback: Optional[Callable[[str], None]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        self._ensure_init()
        if not self._client:
            return "[Error: Gemini Vision not initialized.]"
        try:
            from PIL import Image

            img = Image.open(image_path)
            return self._call_with_retry(
                self._client.models.generate_content,
                model=self.MODEL,
                contents=[prompt, img],
                timeout_seconds=timeout_seconds,
                status_callback=status_callback,
                config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=4096),
            )
        except FileNotFoundError:
            return f"[Error: Image not found: {image_path}]"
        except Exception as e:
            return f"[Error: {e}]"
