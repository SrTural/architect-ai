"""
Validator - ArchitectAI
=======================

AI tərəfindən yazılmış kodu static analiz edir.

Yoxlamalar:
    - Sintaksis (ast.parse)
    - İstifadə olunan adlar import edilibmi?
    - Type hint düzgündürmü?
    - Duplicate insert riski varmı?
    - Deprecated API istifadə olunubmu?
"""

import ast
from typing import Final


class CodeValidator:
    """AI tərəfindən yazılmış kodu static analiz edir."""

    # ============================================================
    # Konfiqurasiya
    # ============================================================
    FASTAPI_SPECIALS: Final[set[str]] = {
        "Depends",
        "HTTPException",
        "Query",
        "Path",
        "Body",
        "File",
        "Form",
        "UploadFile",
        "Request",
        "Response",
        "JSONResponse",
        "FileResponse",
        "StreamingResponse",
    }

    SQLALCHEMY_SPECIALS: Final[set[str]] = {
        "Session",
        "create_engine",
        "sessionmaker",
        "declarative_base",
        "Column",
        "Integer",
        "String",
        "ForeignKey",
        "relationship",
        "Text",
        "Boolean",
        "DateTime",
        "Float",
        "select",
    }

    # ============================================================
    # Əsas Metod
    # ============================================================
    def validate(self, code: str) -> tuple[bool, list[str]]:
        """
        Kodu static analiz edir.

        Args:
            code: AI tərəfindən yazılmış Python kodu.

        Returns:
            tuple: (keçdi?, xəbərdarlıqlar siyahısı)
                   "keçdi" = kritik xəta yoxdur
        """
        warnings: list[str] = []

        # ==== 1. Sintaksis yoxla ====
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"❌ Sintaksis xətası: sətir {e.lineno}, sütun {e.offset} — {e.msg}"]

        # ==== 2. Adları topla ====
        used_names = self._collect_names(tree)
        imported_names = self._collect_imports(tree)

        # ==== 3. FastAPI xüsusi adları yoxla ====
        for name in self.FASTAPI_SPECIALS:
            if name in used_names and name not in imported_names:
                warnings.append(
                    f"❌ '{name}' istifadə olunub, amma import edilməyib."
                )

        # ==== 4. SQLAlchemy xüsusi adları yoxla ====
        for name in self.SQLALCHEMY_SPECIALS:
            if name in used_names and name not in imported_names:
                warnings.append(
                    f"❌ '{name}' istifadə olunub, amma import edilməyib."
                )

        # ==== 5. Type hint yoxla: SessionLocal (yanlış) ====
        if "db: SessionLocal" in code:
            warnings.append(
                "⚠️ 'SessionLocal' type hint yanlışdır. 'Session' istifadə edin."
            )

        # ==== 6. Duplicate insert yoxla ====
        if "add_all" in code and "count() == 0" not in code:
            warnings.append(
                "⚠️ 'add_all' 'count() == 0' yoxlaması olmadan istifadə olunub. "
                "Duplicate data riski."
            )

        # ==== 7. Deprecated API yoxla ====
        if '@app.on_event("startup")' in code:
            warnings.append(
                "⚠️ '@app.on_event' deprecated-dir. 'lifespan' istifadə edin."
            )

        # ==== 8. Pydantic v1 sintaksisi yoxla ====
        if "orm_mode = True" in code or "orm_mode=True" in code:
            warnings.append(
                "⚠️ 'orm_mode' Pydantic v1 sintaksisidir. "
                "Pydantic v2 üçün 'from_attributes = True' istifadə edin."
            )

        # ==== 9. İstifadə olunmayan import yoxla ====
        unused = imported_names - used_names - {"__future__"}
        for name in unused:
            # Bəzi importlar side-effect üçün lazım ola bilər, onları filtrlə
            if name in {"dotenv", "load_dotenv"}:
                continue
            warnings.append(
                f"⚠️ '{name}' import edilib, amma istifadə olunmur."
            )

        # ==== Kritik xəta varmı? ====
        # Yalnız ❌ ilə başlayan xəbərdarlıqlar "critical" sayılır
        has_critical = any(w.startswith("❌") for w in warnings)

        return not has_critical, warnings

    # ============================================================
    # Köməkçi Metodlar
    # ============================================================
    @staticmethod
    def _collect_names(tree: ast.AST) -> set[str]:
        """
        Kodda istifadə olunan bütün adları toplayır.

        Nümunə:
            - `Depends` (Name)
            - `app.get` → `app` və `get` (Attribute)
        """
        names: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)

        return names

    @staticmethod
    def _collect_imports(tree: ast.AST) -> set[str]:
        """
        Import olunmuş bütün adları toplayır.

        Nümunə:
            - `from fastapi import Depends` → `Depends`
            - `import os` → `os`
            - `from fastapi import Depends as D` → `D`
        """
        imports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    # `import os.path` → `os`
                    imports.add(alias.asname or alias.name.split(".")[0])

        return imports