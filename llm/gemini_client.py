import time
from typing import List, Optional

import config


class GeminiClient:
    def __init__(self):
        self._model = None
        self._vision_model = None
        self._initialized = False

    def _ensure_init(self):
        if self._initialized:
            return
        try:
            import google.generativeai as genai

            genai.configure(api_key=config.GEMINI_API_KEY)
            self._model = genai.GenerativeModel("gemini-1.5-flash")
            self._vision_model = genai.GenerativeModel("gemini-1.5-flash")
            self._initialized = True
        except Exception as e:
            print(f"Gemini init failed: {e}")

    def send_prompt(self, prompt_text: str) -> str:
        self._ensure_init()
        if not self._model:
            return "[Error: Gemini not initialized. Check API key.]"
        try:
            response = self._model.generate_content(prompt_text)
            return response.text
        except Exception as e:
            return f"[Error: {e}]"

    def send_with_context(
        self,
        system_prompt: str,
        user_message: str,
        history: Optional[List[dict]] = None,
    ) -> str:
        self._ensure_init()
        if not self._model:
            return "[Error: Gemini not initialized. Check API key.]"
        try:
            full_prompt = f"{system_prompt}\n\n"
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    full_prompt += f"{role}: {content}\n"
            full_prompt += f"user: {user_message}\nagent:"
            response = self._model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"[Error: {e}]"

    def parse_image(self, image_path: str, prompt: str) -> str:
        self._ensure_init()
        if not self._vision_model:
            return "[Error: Gemini Vision not initialized.]"
        try:
            from PIL import Image

            img = Image.open(image_path)
            response = self._vision_model.generate_content([prompt, img])
            return response.text
        except Exception as e:
            return f"[Error: {e}]"
