"""
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
