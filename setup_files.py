"""
setup_files.py - Bütün layihə fayllarını tək əmrlə yenidən yazan skript.
VS Code save problemini bypass edir.
"""

from pathlib import Path

# ==== Fayl məzmunları ====

ARCHITECT_PROMPT = '''ARCHITECT_PROMPT = """
Sen bas tehlukesizlik arxitektorusan (Senior Security Architect).

Sene verilen kodu analiz et ve onu muasir, tehlukesiz arxitekturaya cevir.

QAYDALAR:
1. Zeifliyi tapmaqla kifayetlenme. Onun KOK SEBEBINI tap ve butun fayli ele yeniden yaz ki, o zeiflik bir daha yarana bilmesin.
2. Xam SQL varsa -> SQLAlchemy ORM-e kecir.
3. eval(), exec(), pickle.loads() varsa -> tehlukesiz alternativlerle evez et.
4. Hardcoded sifre/API acari varsa -> os.getenv() ile evez et.
5. Kodu FastAPI standartlarina uygunlashdir, type hint elave et.
6. Yalniz temiz kodu qaytar. Izah yazma.

CAVAB FORMATI:
python kod bloku seklinde qaytar.
"""
'''

PARSER = '''"""
Code Parser Module - ArchitectAI
Legacy kod faylini oxuyur ve AST strukturuna cevirir.
"""

import ast
from pathlib import Path
from typing import Optional


class ParserError(Exception):
    """Parser ile bagli xetalar ucun xususi exception."""
    pass


class Parser:
    """Legacy Python kodunu oxuyub analiz eden sinif."""

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.source = ""
        self.tree = None
        self._load()

    def _load(self):
        if not self.file_path.exists():
            raise ParserError(f"Fayl tapilmadi: {self.file_path}")

        try:
            self.source = self.file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise ParserError(f"Fayl oxuna bilmedi (encoding): {e}") from e

        try:
            self.tree = ast.parse(self.source)
        except SyntaxError as e:
            raise ParserError(
                f"Sintaksis xetasi ({self.file_path}): "
                f"setir {e.lineno}, sutun {e.offset} -- {e.msg}"
            ) from e

    def get_full_code(self):
        return self.source

    def get_functions(self):
        if self.tree is None:
            return []
        return [
            node.name
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
        ]

    def __repr__(self):
        return f"Parser(file={self.file_path.name}, functions={len(self.get_functions())})"
'''

REFACTOR_ENGINE = '''"""
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
            {"role": "user", "content": f"Bu kodu tehlukesiz arxitekturaya cevir:\\n\\n{old_code}"},
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
'''

MAIN = '''"""
ArchitectAI - Legacy Kod Refaktor Alehti
Entry point.
"""

import sys
from app.core.parser import Parser, ParserError
from app.core.refactor_engine import RefactorEngine


LEGACY_FILE = "legacy_code/old_app.py"
SEPARATOR = "=" * 60


def print_section(title):
    print(f"\\n{SEPARATOR}\\n{title}\\n{SEPARATOR}")


def main():
    try:
        print(f"Fayl oxunur: {LEGACY_FILE}")
        parser = Parser(LEGACY_FILE)
        old_code = parser.get_full_code()
        print(f"Yuklendi: {len(old_code)} simvol, {len(parser.get_functions())} funksiya")

        engine = RefactorEngine()
        result = engine.refactor(old_code)

        print_section("KOHNE KOD (legacy)")
        print(result["old_code"])

        print_section("YENI KOD (AI terefinden)")
        print(result["new_code"])

        print_section("NETICE")
        status = "UGURLU" if result["valid_syntax"] else "SINTAKSIS XETASI"
        print(f"Sintaksis      : {status}")
        print(f"Ceht sayi      : {result['attempts']}")

        return 0 if result["valid_syntax"] else 1

    except ParserError as e:
        print(f"Parser xetasi: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"Fayl tapilmadi: {e}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("\\nIstifadeci terefinden dayandirildi.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Gozlenilmez xeta: {type(e).__name__}: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
'''

OLD_APP = '''import os
import sqlite3

password = "admin123"


def login(user_input):
    result = eval(user_input)
    os.system("ls " + user_input)
    return result


def get_user(user_id):
    conn = sqlite3.connect("db.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()
'''

APP_INIT = '''"""ArchitectAI - Legacy Kod Refaktor Alehti."""

__version__ = "0.1.0"
__author__ = "Tural Dadasov"
__license__ = "MIT"
'''

CORE_INIT = '''"""Core modullar - parser ve refactor engine."""
'''

PROMPTS_INIT = '''"""Prompt sablonlari - LLM telimatlari."""
'''

GITIGNORE = '''# Python
__pycache__/
*.py[cod]
*.so
venv/
.venv/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
'''


# ==== Faylları yaz ====

FILES = {
    "app/prompts/architect_prompt.py": ARCHITECT_PROMPT,
    "app/core/parser.py": PARSER,
    "app/core/refactor_engine.py": REFACTOR_ENGINE,
    "app/main.py": MAIN,
    "app/__init__.py": APP_INIT,
    "app/core/__init__.py": CORE_INIT,
    "app/prompts/__init__.py": PROMPTS_INIT,
    "legacy_code/old_app.py": OLD_APP,
    ".gitignore": GITIGNORE,
}


if __name__ == "__main__":
    for path, content in FILES.items():
        Path(path).write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        print(f"[OK] {path:50s} ({lines} setir)")

    print("\nButun fayllar ugurla yazildi!")