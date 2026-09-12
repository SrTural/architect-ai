"""
Refactor Engine - ArchitectAI
Legacy kodu muasir, tehlukesiz arxitekturaya ceviren esas muherrik.
"""

import ast
import logging
from typing import Optional

import ollama

from app.prompts.architect_prompt import ARCHITECT_PROMPT


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class RefactorEngine:
    """LLM vasitesile legacy kodu refaktor eden sinif."""

    DEFAULT_MODEL = "qwen2.5:7b-16k"
    MAX_RETRIES = 2

    def __init__(self, model=None):
        self.model = model or self.DEFAULT_MODEL
        logger.info(f"RefactorEngine basladildi | Model: {self.model}")

    def refactor(self, old_code):
        if not old_code.strip():
            raise ValueError("Bos kod refaktor edile bilmez.")

        messages = [
            {"role": "system", "content": ARCHITECT_PROMPT},
            {"role": "user", "content": f"Bu kodu tehlukesiz arxitekturaya cevir:\n\n{old_code}"},
        ]

        new_code = ""
        valid = False
        attempt = 0

        while attempt < self.MAX_RETRIES:
            attempt += 1
            logger.info(f"Ceht #{attempt} - LLM-e sorgu gonderilir...")

            response = ollama.chat(model=self.model, messages=messages)
            raw = response["message"]["content"]
            new_code = self._clean(raw)
            valid = self._validate(new_code)

            if valid:
                logger.info(f"Ugurlu refaktor (ceht #{attempt})")
                break

            logger.warning(f"Sintaksis xetasi (ceht #{attempt}). Yeniden ceht edilir...")
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": "Yuxaridaki kodda sintaksis xetasi var. Yeniden yaz, yalniz temiz Python kodu qaytar.",
            })

        return {
            "old_code": old_code,
            "new_code": new_code,
            "valid_syntax": valid,
            "attempts": attempt,
        }

    @staticmethod
    def _clean(raw):
        raw = raw.strip()
        if "```python" in raw:
            parts = raw.split("```python")
            if len(parts) > 1:
                return parts[1].split("```")[0].strip()
        if "```" in raw:
            parts = raw.split("```")
            if len(parts) > 1:
                return parts[1].strip()
        return raw

    @staticmethod
    def _validate(code):
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
