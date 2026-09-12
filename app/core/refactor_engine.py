"""
Refactor Engine - ArchitectAI
=============================

Legacy kodu müasir, təhlükəsiz arxitekturaya çevirən əsas mühərrik.

Arxitektura (3 qat):
    ┌─────────────────────────────────────────────────────┐
    │  Qat 1: LLM (Ollama + Qwen 2.5)  → kod yazır (80%) │
    │  Qat 2: PostProcessor            → düzəlişlər (+10%)│
    │  Qat 3: Validator                → analiz (+5%)     │
    └─────────────────────────────────────────────────────┘
    CƏMİ: ~95% dəqiqlik

Self-Correction:
    - LLM sintaksis xətası yazsa, yenidən cəhd edir (max 2)
    - PostProcessor kodu pozsa, orijinal LLM çıxışına qayıdır
    - Hər mərhələdən sonra sintaksis yenidən yoxlanılır
"""

import ast
import logging
from typing import Optional

import ollama

from app.core.post_processor import PostProcessor
from app.core.validator import CodeValidator
from app.prompts.architect_prompt import ARCHITECT_PROMPT


# ============================================================
# Logging Konfiqurasiyası
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class RefactorEngine:
    """
    LLM vasitəsilə legacy Python kodunu təhlükəsiz arxitekturaya
    çevirən əsas sinif.

    Xüsusiyyətlər:
        - Yerli LLM (Ollama + Qwen 2.5)
        - Self-correction loop (sintaksis xətası olsa, yenidən cəhd)
        - Post-processing (rule-based düzəlişlər)
        - Static validation (import, type hint, deprecated API)
        - Fallback mexanizmi (PostProcessor kodu pozsa)
        - Quality score (0-100)
    """

    # ============================================================
    # Sinif Səviyyəsində Sabitlər
    # ============================================================
    DEFAULT_MODEL: str = "qwen2.5:7b-16k"
    MAX_RETRIES: int = 2

    # ============================================================
    # İnisializasiya
    # ============================================================
    def __init__(self, model: Optional[str] = None) -> None:
        """
        RefactorEngine-i işə salır.

        Args:
            model: İstifadə olunacaq LLM modeli.
                   Default: qwen2.5:7b-16k
        """
        self.model: str = model or self.DEFAULT_MODEL
        self.post_processor: PostProcessor = PostProcessor()
        self.validator: CodeValidator = CodeValidator()

        logger.info(f"RefactorEngine başladıldı | Model: {self.model}")

    # ============================================================
    # Əsas Metod
    # ============================================================
    def refactor(self, old_code: str) -> dict:
        """
        Verilən kodu LLM-ə göndərir və təmizlənmiş versiyasını qaytarır.

        Proses:
            1. LLM-ə sorğu göndər (self-correction loop ilə)
            2. Post-process (rule-based düzəlişlər)
            3. Post-Processor-dən sonra sintaksisi yoxla (fallback)
            4. Validate (static analiz)
            5. Quality score hesabla
            6. Nəticəni qaytar

        Args:
            old_code: Refaktor ediləcək legacy kod.

        Returns:
            dict: {
                "old_code": orijinal kod,
                "new_code": refaktor edilmiş kod,
                "valid_syntax": sintaksis düzgündürmü,
                "attempts": neçə cəhd edildi,
                "warnings": bütün xəbərdarlıqlar,
                "quality_score": 0-100 arası keyfiyyət balı,
            }
        """
        # ==== Boş kod yoxlaması ====
        if not old_code.strip():
            raise ValueError("Boş kod refaktor edilə bilməz.")

        # ============================================================
        # Qat 1: LLM + Self-Correction
        # ============================================================
        llm_code, llm_valid, attempt = self._run_llm_refactor(old_code)

        # ============================================================
        # Qat 2: Post-Processing (Rule-Based) + Fallback
        # ============================================================
        new_code, post_warnings = self._run_post_processing(llm_code)

        # ============================================================
        # Qat 3: Static Validation
        # ============================================================
        is_valid, val_warnings = self.validator.validate(new_code)

        if val_warnings:
            logger.info(f"Validator: {len(val_warnings)} xəbərdarlıq")
            for w in val_warnings:
                logger.warning(w)

        # ============================================================
        # Xəbərdarlıqları Birləşdir (Dublikatları Sil)
        # ============================================================
        all_warnings = self._merge_warnings(post_warnings, val_warnings)

        # ============================================================
        # Son sintaksis yoxlaması (PostProcessor-dən sonra)
        # ============================================================
        final_valid = self._validate_syntax(new_code)

        if not final_valid and llm_valid:
            # Bu, PostProcessor-in kodu pozduğunu göstərir
            logger.error(
                "❌ PostProcessor-dən sonra sintaksis pozuldu! "
                "Orijinal LLM çıxışı bərpa edilir."
            )
            new_code = llm_code
            final_valid = True
            all_warnings.append(
                "⚠️ PostProcessor sintaksisi pozdu, LLM-in orijinal çıxışı saxlanıldı."
            )

        # ============================================================
        # Quality Score Hesabla
        # ============================================================
        quality_score = self._calculate_quality_score(
            valid_syntax=final_valid,
            warnings=all_warnings,
            original_len=len(old_code),
            new_len=len(new_code),
        )

        # ============================================================
        # Nəticə
        # ============================================================
        return {
            "old_code": old_code,
            "new_code": new_code,
            "valid_syntax": final_valid,
            "attempts": attempt,
            "warnings": all_warnings,
            "quality_score": quality_score,
        }

    # ============================================================
    # Qat 1: LLM Refactor + Self-Correction
    # ============================================================
    def _run_llm_refactor(self, old_code: str) -> tuple[str, bool, int]:
        """
        LLM-ə sorğu göndərir və self-correction loop ilə işləyir.

        Args:
            old_code: Refaktor ediləcək kod.

        Returns:
            tuple: (yeni kod, sintaksis düzgündürmü, cəhd sayı)
        """
        messages = self._build_messages(old_code)
        new_code = ""
        valid = False
        attempt = 0

        while attempt < self.MAX_RETRIES:
            attempt += 1
            logger.info(f"Cəhd #{attempt} - LLM-ə sorğu göndərilir...")

            try:
                response = ollama.chat(model=self.model, messages=messages)
                raw = response["message"]["content"]
                new_code = self._clean(raw)
                valid = self._validate_syntax(new_code)

                if valid:
                    logger.info(f"✅ Uğurlu refaktor (cəhd #{attempt})")
                    return new_code, True, attempt

                logger.warning(
                    f"⚠️ Sintaksis xətası (cəhd #{attempt}). "
                    f"Yenidən cəhd edilir..."
                )
                # LLM-ə xəta barədə məlumat ver
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        "Yuxarıdaki kodda sintaksis xətası var. "
                        "Yenidən yaz, yalnız təmiz Python kodu qaytar. "
                        "Heç bir izah yazma."
                    ),
                })

            except Exception as e:
                logger.error(f"LLM xətası: {e}")
                raise

        return new_code, valid, attempt

    # ============================================================
    # Qat 2: Post-Processing + Fallback
    # ============================================================
    def _run_post_processing(self, llm_code: str) -> tuple[str, list[str]]:
        """
        PostProcessor-i işə salır və nəticəni yoxlayır.
        Əgər PostProcessor kodu pozsa, orijinal LLM çıxışına qayıdır.

        Args:
            llm_code: LLM-dən gələn orijinal kod.

        Returns:
            tuple: (düzəldilmiş kod, xəbərdarlıqlar)
        """
        processed_code, warnings = self.post_processor.process(llm_code)

        if warnings:
            logger.info(f"Post-processing: {len(warnings)} düzəliş")
            for w in warnings:
                logger.warning(w)

        # ==== PostProcessor kodu pozubsa, geri qaytar ====
        if not self._validate_syntax(processed_code):
            logger.warning(
                "⚠️ PostProcessor sintaksisi pozdu. "
                "LLM-in orijinal çıxışı saxlanılır."
            )
            warnings.append(
                "⚠️ PostProcessor sintaksisi poza bilər, orijinal kod saxlanıldı."
            )
            return llm_code, warnings

        return processed_code, warnings

    # ============================================================
    # Köməkçi Metodlar
    # ============================================================
    def _build_messages(self, old_code: str) -> list[dict]:
        """LLM üçün mesaj strukturunu qurur."""
        return [
            {"role": "system", "content": ARCHITECT_PROMPT},
            {
                "role": "user",
                "content": f"Bu kodu təhlükəsiz arxitekturaya çevir:\n\n{old_code}",
            },
        ]

    @staticmethod
    def _clean(raw: str) -> str:
        """LLM cavabından markdown kod bloklarını təmizləyir."""
        raw = raw.strip()

        # ```python ... ``` formatı
        if "```python" in raw:
            parts = raw.split("```python")
            if len(parts) > 1:
                return parts[1].split("```")[0].strip()

        # ``` ... ``` formatı
        if "```" in raw:
            parts = raw.split("```")
            if len(parts) > 1:
                return parts[1].strip()

        return raw

    @staticmethod
    def _validate_syntax(code: str) -> bool:
        """Kodun sintaksis baxımından düzgün olub-olmadığını yoxlayır."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    @staticmethod
    def _merge_warnings(
        post_warnings: list[str],
        val_warnings: list[str],
    ) -> list[str]:
        """
        İki xəbərdarlıq siyahısını birləşdirir və dublikatları silir.
        Sıra saxlanılır: əvvəlcə post, sonra validator.
        """
        seen: set[str] = set()
        merged: list[str] = []

        for w in post_warnings + val_warnings:
            if w not in seen:
                seen.add(w)
                merged.append(w)

        return merged

    @staticmethod
    def _calculate_quality_score(
        valid_syntax: bool,
        warnings: list[str],
        original_len: int,
        new_len: int,
    ) -> int:
        """
        Kodun ümumi keyfiyyət balını hesablayır (0-100).

        Hesablama:
            - Başlanğıc: 100 bal
            - Sintaksis xətası: -50 bal
            - Hər CRITICAL (❌) xəbərdarlıq: -10 bal
            - Hər WARNING (⚠️): -5 bal
            - Kod böyüməsi > 5x: -10 bal (şiştirmə)
        """
        score = 100

        # ==== Sintaksis xətası ====
        if not valid_syntax:
            score -= 50

        # ==== Xəbərdarlıqlar ====
        for w in warnings:
            if w.startswith("❌"):
                score -= 10  # Critical
            elif w.startswith("⚠️"):
                score -= 5   # Warning

        # ==== Şiştirmə yoxlaması ====
        if original_len > 0 and new_len > original_len * 5:
            score -= 10

        # ==== 0-100 aralığında saxla ====
        return max(0, min(100, score))