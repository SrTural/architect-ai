"""
Post-Processor - ArchitectAI
=============================

AI chixishini rule-based yoxlayir ve avtomatik duzeldir.

DUZELISLER (26 Rule):
    1.  '/.env' endpoint silinir
    2.  Tehlukesiz CORS konfiqurasiyasi duzeldilir
    3.  Deprecated @app.on_event ashkar edilir
    4.  Sync/async qarishiqligi ashkar edilir
    5.  Pydantic v1 -> v2 sintaksisi duzeldilir
    6.  Missing import-lar avtomatik elave edilir
    7.  Istifade olunmayan import-lar ashkar edilir
    8.  Missing function (YALNIZ user-defined) ashkar edilir + stub
    9.  Hardcoded DATABASE_URL -> os.getenv()
    10. Optional parametrler -> Query(...)
    11. Istifade olunmayan import-lar SILINIR
    12. 'SessionLocal' type hint -> 'Session'
    13. 'db.query().delete()' -> 'count() == 0'
    14. 'next(get_db())' -> 'Depends(get_db)'
    15. '@app.on_event(\"startup\")' -> 'lifespan'
    16. Xam SQL 'db.execute(SELECT...)' -> 'db.query()'
    17. 'db.first()' -> duzgun ORM
    18. GET + Body -> GET + Query
    19. 'raise SQLAlchemyError' -> 'raise HTTPException'
    20. 'return {...}, 404' -> 'raise HTTPException(404)'
    21. Recursive Depends(get_db) duzeldilir
    22. 'add_all' 'count() == 0' yoxlamasi olmadan -> elave edilir
    23. Duplicate init_db() cagirishlari silinir
    24. Sinif adlari missing function SAYILMIR
    25. Duplicate sinif adlari (User SQLAlchemy vs User Pydantic) -> rename
    26. 'from fastapi.cli import main' -> 'uvicorn.run' ile evez edilir
"""

import ast
import re
from typing import Final


# ============================================================
# Konfiqurasiya (ASCII-safe, encoding problemi olmasin)
# ============================================================
ENV_ENDPOINT_PATTERNS: Final[tuple[str, ...]] = ("/.env", "/env")

HTTP_DECORATORS: Final[tuple[str, ...]] = (
    "@app.get", "@app.post", "@app.put", "@app.delete",
    "@app.patch", "@app.route",
)

PROTECTED_FUNCS: Final[set[str]] = {"get_db"}

RULE8_IGNORED: Final[set[str]] = {
    # FastAPI
    "FastAPI", "Depends", "HTTPException", "Query", "Path", "Body",
    "File", "Form", "UploadFile", "Request", "Response",
    "JSONResponse", "FileResponse", "StreamingResponse",
    "CORSMiddleware", "APIRouter", "WebSocket",
    # SQLAlchemy
    "Session", "create_engine", "sessionmaker", "declarative_base",
    "Column", "Integer", "String", "ForeignKey", "relationship",
    "select", "text", "MetaData", "Table", "engine",
    # Pydantic
    "BaseModel", "Field", "validator", "ConfigDict",
    # Stdlib
    "load_dotenv", "dotenv_values", "Path", "os", "sys", "re",
    "asyncio", "json", "datetime", "uuid", "typing",
}

FASTAPI_IMPORTS: Final[dict[str, str]] = {
    "Depends": "from fastapi import Depends",
    "HTTPException": "from fastapi import HTTPException",
    "Query": "from fastapi import Query",
    "Path": "from fastapi import Path",
    "Body": "from fastapi import Body",
    "File": "from fastapi import File",
    "Form": "from fastapi import Form",
    "UploadFile": "from fastapi import UploadFile",
    "Request": "from fastapi import Request",
    "Response": "from fastapi import Response",
    "JSONResponse": "from fastapi.responses import JSONResponse",
    "FileResponse": "from fastapi.responses import FileResponse",
    "StreamingResponse": "from fastapi.responses import StreamingResponse",
    "CORSMiddleware": "from fastapi.middleware.cors import CORSMiddleware",
}

SQLALCHEMY_IMPORTS: Final[dict[str, str]] = {
    "Session": "from sqlalchemy.orm import Session",
    "create_engine": "from sqlalchemy import create_engine",
    "sessionmaker": "from sqlalchemy.orm import sessionmaker",
    "declarative_base": "from sqlalchemy.ext.declarative import declarative_base",
    "Column": "from sqlalchemy import Column",
    "Integer": "from sqlalchemy import Integer",
    "String": "from sqlalchemy import String",
    "ForeignKey": "from sqlalchemy import ForeignKey",
    "relationship": "from sqlalchemy.orm import relationship",
    "select": "from sqlalchemy import select",
    "text": "from sqlalchemy import text",
}

PYDANTIC_V1_TO_V2: Final[dict[str, str]] = {
    "orm_mode = True": "from_attributes = True",
    "orm_mode=True": "from_attributes=True",
}

ALL_IMPORTS: Final[dict[str, str]] = {**FASTAPI_IMPORTS, **SQLALCHEMY_IMPORTS}

BUILTINS: Final[set[str]] = {
    "print", "len", "range", "str", "int", "float", "list", "dict", "set",
    "tuple", "bool", "type", "isinstance", "issubclass", "getattr", "setattr",
    "hasattr", "delattr", "open", "input", "sum", "min", "max", "abs", "round",
    "sorted", "reversed", "enumerate", "zip", "map", "filter", "any", "all",
    "next", "iter", "super", "vars", "dir", "id", "hash", "repr", "format",
    "callable", "eval", "exec", "globals", "locals", "compile",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "AttributeError", "RuntimeError", "StopIteration", "ImportError",
    "OSError", "IOError", "ZeroDivisionError", "NameError", "SyntaxError",
    "AssertionError", "NotImplementedError", "OverflowError",
    "ArithmeticError", "LookupError", "UnicodeError", "Warning",
    "asyncio", "os", "sys", "re", "json",
}


class PostProcessor:
    """AI terefinden yazilmish kodu yoxlayir ve rule-based duzelishler edir."""

    def __init__(self) -> None:
        self._imports_added_this_run: set[str] = set()

    # ============================================================
    # Esas Metod (Idempotent - max 3 iterasiya)
    # ============================================================
    def process(self, code: str) -> tuple[str, list[str]]:
        """Kodu yoxlayir. Idempotent - max 3 iterasiya."""
        all_warnings: list[str] = []
        current_code = code

        for iteration in range(3):
            self._imports_added_this_run = set()
            new_code, warnings = self._process_once(current_code)
            all_warnings.extend(warnings)

            if new_code == current_code:
                break

            current_code = new_code

        seen: set[str] = set()
        unique_warnings: list[str] = []
        for w in all_warnings:
            if w not in seen:
                seen.add(w)
                unique_warnings.append(w)

        return current_code, unique_warnings

    # ============================================================
    # Tek Iterasiya
    # ============================================================
    def _process_once(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed_code = code

        # Rule 21
        fixed_code, w = self._fix_recursive_depends(fixed_code); warnings.extend(w)

        # Rule 1
        if self._has_env_endpoint(fixed_code):
            warnings.append("[WARN] '.env' endpoint ashkar edildi ve silindi.")
            fixed_code = self._remove_env_endpoint(fixed_code)

        # Rule 2
        if self._has_dangerous_cors(fixed_code):
            warnings.append("[WARN] Tehlukesiz CORS konfiqurasiyasi duzeldildi.")
            fixed_code = self._fix_cors(fixed_code)

        # Rule 3
        if '@app.on_event("startup")' in fixed_code:
            warnings.append("[WARN] '@app.on_event' deprecated-dir. 'lifespan' istifade edin.")

        # Rule 4
        if "create_engine" in fixed_code and "await " in fixed_code:
            warnings.append("[WARN] Sync 'create_engine' + 'await' qarishiqligi ashkar edildi.")

        # Rule 5
        fixed_code, w = self._fix_pydantic_v1(fixed_code); warnings.extend(w)

        # Rule 13
        fixed_code, w = self._fix_delete_pattern(fixed_code); warnings.extend(w)

        # Rule 16
        fixed_code, w = self._fix_raw_sql_execute(fixed_code); warnings.extend(w)

        # Rule 22
        fixed_code, w = self._fix_add_all_count(fixed_code); warnings.extend(w)

        # Rule 17
        fixed_code, w = self._fix_db_first(fixed_code); warnings.extend(w)

        # Rule 18
        fixed_code, w = self._fix_get_with_body(fixed_code); warnings.extend(w)

        # Rule 19
        fixed_code, w = self._fix_wrong_exception(fixed_code); warnings.extend(w)

        # Rule 20
        fixed_code, w = self._fix_tuple_return(fixed_code); warnings.extend(w)

        # Rule 15
        fixed_code, w = self._fix_on_event_lifespan(fixed_code); warnings.extend(w)

        # Rule 14
        fixed_code, w = self._fix_next_get_db(fixed_code); warnings.extend(w)

        # Rule 23
        fixed_code, w = self._fix_duplicate_init_db(fixed_code); warnings.extend(w)

        # Rule 25 (YENI) - Duplicate class names
        fixed_code, w = self._fix_duplicate_class_names(fixed_code); warnings.extend(w)

        # Rule 26 (YENI) - fastapi.cli -> uvicorn.run
        fixed_code, w = self._fix_fastapi_cli_main(fixed_code); warnings.extend(w)

        # Rule 8
        fixed_code, w = self._fix_missing_functions(fixed_code); warnings.extend(w)

        # Rule 9
        fixed_code, w = self._fix_hardcoded_url(fixed_code); warnings.extend(w)

        # Rule 10
        fixed_code, w = self._fix_optional_param(fixed_code); warnings.extend(w)

        # Rule 6
        fixed_code, w = self._fix_missing_imports(fixed_code); warnings.extend(w)

        # Rule 7
        fixed_code, w = self._detect_unused_imports(fixed_code); warnings.extend(w)

        # Rule 11
        fixed_code, w = self._remove_unused_imports_actual(fixed_code); warnings.extend(w)

        # Rule 12
        fixed_code, w = self._fix_session_type_hint(fixed_code); warnings.extend(w)

        return fixed_code, warnings

    # ============================================================
    # Rule 25 (YENI) - Duplicate Class Names
    # ============================================================
    def _fix_duplicate_class_names(self, code: str) -> tuple[str, list[str]]:
        """
        `class User(Base)` ve `class User(BaseModel)` kimi eyni adli
        sinifleri tapir. Pydantic olanini `UserResponse` olaraq rename edir.
        """
        warnings: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, warnings

        # Butun sinifleri topla: ad -> [(line, base_name)]
        classes: dict[str, list[tuple[int, str]]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases: list[str] = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(base.attr)

                classes.setdefault(node.name, []).append((node.lineno, bases[0] if bases else ""))

        # Duplicate sinifleri tap
        for class_name, occurrences in classes.items():
            if len(occurrences) < 2:
                continue

            # Pydantic modeli tap (BaseModel ile)
            pydantic_line: int | None = None
            sqlalchemy_line: int | None = None

            for line_no, base in occurrences:
                if base == "BaseModel":
                    pydantic_line = line_no
                elif base == "Base":
                    sqlalchemy_line = line_no

            if pydantic_line is not None and sqlalchemy_line is not None:
                # Pydantic modeli rename et: User -> UserResponse
                new_name = f"{class_name}Response"

                # Butun kodu yenile
                lines = code.split("\n")
                # Pydantic sinifinin bashlangic setirini tap
                for i, line in enumerate(lines):
                    if i + 1 == pydantic_line:
                        # `class User(BaseModel):` -> `class UserResponse(BaseModel):`
                        lines[i] = re.sub(
                            rf"\bclass\s+{class_name}\b",
                            f"class {new_name}",
                            line,
                        )
                        break
                code = "\n".join(lines)

                # Isdifade olunan yerleri de rename et
                # `response_model=list[User]` -> `list[UserResponse]`
                # `-> User` ve ya `: User` tipler
                code = re.sub(
                    rf"(response_model\s*=\s*(?:list\[)?){class_name}(\]?)",
                    rf"\1{new_name}\2",
                    code,
                )

                warnings.append(
                    f"[WARN] Duplicate sinif adi '{class_name}' -> Pydantic modeli "
                    f"'{new_name}' olaraq rename edildi."
                )

        return code, warnings

    # ============================================================
    # Rule 26 (YENI) - fastapi.cli -> uvicorn.run
    # ============================================================
    def _fix_fastapi_cli_main(self, code: str) -> tuple[str, list[str]]:
        """
        `from fastapi.cli import main` + `main(["run", "--reload"])`
        sehv patternini `uvicorn.run(app, ...)` ile evez edir.
        """
        warnings: list[str] = []

        has_cli_import = bool(
            re.search(r"from\s+fastapi\.cli\s+import\s+main", code)
        )
        has_cli_call = bool(
            re.search(r'main\(\s*\[\s*["\']run["\']', code)
        )

        if not (has_cli_import and has_cli_call):
            return code, warnings

        # fastapi.cli importunu sil
        code = re.sub(
            r"^\s*from\s+fastapi\.cli\s+import\s+main\s*\n",
            "",
            code,
            flags=re.MULTILINE,
        )

        # main([...]) cagirishini uvicorn ile evez et
        code = re.sub(
            r"main\(\s*\[\s*[\"']run[\"'][^\]]*\]\s*\)",
            'import uvicorn\n    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)',
            code,
        )

        warnings.append(
            "[WARN] 'fastapi.cli.main' -> 'uvicorn.run(app, ...)' ile evez edildi."
        )

        return code, warnings

    # ============================================================
    # Rule 21
    # ============================================================
    def _fix_recursive_depends(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        for func_name in PROTECTED_FUNCS:
            pattern = re.compile(
                rf"(def\s+{func_name}\s*\([^)]*?)(,?\s*db\s*:\s*Session\s*=\s*Depends\(get_db\))([^)]*\))",
                re.DOTALL,
            )

            def replace_recursive(match: re.Match) -> str:
                before = match.group(1).rstrip().rstrip(",")
                after = match.group(3).lstrip().lstrip(",")
                if before.endswith("(") and after.strip() == ")":
                    return f"{before})"
                if before.endswith("("):
                    return f"{before}{after}"
                return f"{before}{after}"

            if pattern.search(fixed):
                fixed = pattern.sub(replace_recursive, fixed)
                warnings.append(f"[WARN] '{func_name}' daxilinde recursive 'Depends(get_db)' silindi.")

        return fixed, warnings

    # ============================================================
    # Rule 1
    # ============================================================
    def _has_env_endpoint(self, code: str) -> bool:
        for line in code.split("\n"):
            stripped = line.strip()
            if not any(d in stripped for d in HTTP_DECORATORS):
                continue
            for pattern in ENV_ENDPOINT_PATTERNS:
                if f'"{pattern}"' in line or f"'{pattern}'" in line:
                    return True
        return False

    def _remove_env_endpoint(self, code: str) -> str:
        lines = code.split("\n")
        result: list[str] = []
        in_env_function = False
        in_triple_quote: str | None = None

        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            if in_triple_quote is not None:
                if in_triple_quote in line:
                    in_triple_quote = None
                continue

            is_decorator = any(d in line for d in HTTP_DECORATORS)
            is_env = any(
                f'"{p}"' in line or f"'{p}'" in line
                for p in ENV_ENDPOINT_PATTERNS
            )

            if is_decorator and is_env:
                in_env_function = True
                continue

            if in_env_function:
                if stripped == "":
                    continue
                if '"""' in stripped or "'''" in stripped:
                    quote = '"""' if '"""' in stripped else "'''"
                    count = stripped.count(quote)
                    if count == 1:
                        in_triple_quote = quote
                    continue
                if indent > 0:
                    continue
                if stripped.startswith(("def ", "async def ")):
                    continue
                in_env_function = False

            result.append(line)

        cleaned = "\n".join(result)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    # ============================================================
    # Rule 2
    # ============================================================
    def _has_dangerous_cors(self, code: str) -> bool:
        return 'allow_origins=["*"]' in code and "allow_credentials=True" in code

    def _fix_cors(self, code: str) -> str:
        return code.replace(
            "allow_credentials=True",
            "allow_credentials=False  # Tehlukesizlik: '*' origin ile credentials qadagandir",
        )

    # ============================================================
    # Rule 5
    # ============================================================
    def _fix_pydantic_v1(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code
        for old, new in PYDANTIC_V1_TO_V2.items():
            if old in fixed:
                fixed = fixed.replace(old, new)
                warnings.append(f"[WARN] Pydantic v1 -> v2: '{old}' -> '{new}'")
        return fixed, warnings

    # ============================================================
    # Rule 13
    # ============================================================
    def _fix_delete_pattern(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        pattern1 = re.compile(
            r"(\s*)db\.query\((\w+)\)\.delete\(\)\s*\n"
            r"(\s*)db\.add_all\(\[([^\]]*)\]\)",
            re.DOTALL,
        )

        def replace1(match: re.Match) -> str:
            indent2 = match.group(3)
            model = match.group(2)
            items = match.group(4)
            return (
                f"{indent2}if db.query({model}).count() == 0:\n"
                f"{indent2}    db.add_all([{items}])"
            )

        if pattern1.search(code):
            code = pattern1.sub(replace1, code)
            warnings.append("[WARN] 'db.query().delete()' -> 'count() == 0' yoxlamasi ile evez edildi.")
            return code, warnings

        pattern2 = re.compile(r"^\s*db\.query\((\w+)\)\.delete\(\)\s*$", re.MULTILINE)
        if pattern2.search(code):
            code = pattern2.sub("", code)
            warnings.append("[WARN] 'db.query().delete()' silindi.")

        return code, warnings

    # ============================================================
    # Rule 22
    # ============================================================
    def _fix_add_all_count(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        if "count() == 0" in fixed:
            return fixed, warnings

        pattern = re.compile(
            r"(\s*)db\.add_all\(\s*\[([^\]]+)\]\s*\)",
            re.DOTALL,
        )

        def replace_add_all(match: re.Match) -> str:
            indent = match.group(1)
            items = match.group(2)
            model_match = re.search(r"(\w+)\s*\(", items)
            if not model_match:
                return match.group(0)
            model = model_match.group(1)
            return (
                f"{indent}if db.query({model}).count() == 0:\n"
                f"{indent}    db.add_all([{items}])"
            )

        if pattern.search(fixed):
            new_fixed = pattern.sub(replace_add_all, fixed)
            if new_fixed != fixed:
                fixed = new_fixed
                warnings.append("[WARN] 'db.add_all()' -> 'count() == 0' yoxlamasi ile ehalte edildi.")

        return fixed, warnings

    # ============================================================
    # Rule 16
    # ============================================================
    def _fix_raw_sql_execute(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        pattern_ddl = re.compile(
            r"^\s*(?:db|cursor|conn)\.execute\(\s*[\"']{1,3}\s*(?:CREATE|DROP|ALTER|INSERT|DELETE|UPDATE)\b.*?[\"']{1,3}\s*\)\s*$",
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        if pattern_ddl.search(fixed):
            fixed = pattern_ddl.sub("", fixed)
            warnings.append("[WARN] Xam SQL DDL/DML setirleri silindi.")

        pattern = re.compile(
            r"(?:db|cursor|conn)\.execute\(\s*[\"']{1,3}\s*SELECT\s+.*?\s+FROM\s+(\w+)\s+WHERE\s+(\w+)\s*=\s*['\"]([^'\"]+)['\"]\s*;?\s*[\"']{1,3}\s*\)",
            re.DOTALL | re.IGNORECASE,
        )

        def replace_execute(match: re.Match) -> str:
            table = match.group(1).lower()
            column = match.group(2)
            value = match.group(3)
            model = table.capitalize()
            return f'db.query({model}).filter({model}.{column} == "{value}").first()'

        if pattern.search(fixed):
            fixed = pattern.sub(replace_execute, fixed)
            warnings.append("[WARN] Xam SQL 'execute(SELECT...)' -> ORM 'db.query().filter()'.")

        return fixed, warnings

    # ============================================================
    # Rule 17
    # ============================================================
    def _fix_db_first(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        if re.search(r"\bdb\.first\(\)", fixed):
            fixed = re.sub(r"\bdb\.first\(\)", "db.query(User).first()", fixed)
            warnings.append("[WARN] 'db.first()' -> 'db.query(User).first()'.")

        fixed = re.sub(
            r"db\.execute\([^)]+\)\.first\(\)",
            "db.query(User).first()",
            fixed,
        )

        return fixed, warnings

    # ============================================================
    # Rule 18
    # ============================================================
    def _fix_get_with_body(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        pattern = re.compile(
            r'(@app\.get\([^)]+\)\s*\n'
            r"def\s+(\w+)\s*\()\s*request:\s*Request\s*,\s*user_request:\s*(\w+)\s*\)"
        )

        def replace_get(match: re.Match) -> str:
            func_start = match.group(1)
            return f'{func_start}name: str = Query(...))'

        if pattern.search(fixed):
            fixed = pattern.sub(replace_get, fixed)
            warnings.append("[WARN] GET + Body -> GET + Query parameter.")
            fixed = re.sub(r"\buser_request\.name\b", "name", fixed)

            if not self._is_imported(fixed, "Query"):
                lines = fixed.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("from fastapi import"):
                        if "Query" not in line:
                            lines[i] = line.rstrip() + ", Query"
                            break
                fixed = "\n".join(lines)

        return fixed, warnings

    # ============================================================
    # Rule 19
    # ============================================================
    def _fix_wrong_exception(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        pattern = re.compile(r'raise\s+SQLAlchemyError\(\s*["\']([^"\']+)["\']\s*\)')

        def replace_raise(match: re.Match) -> str:
            msg = match.group(1)
            return f'raise HTTPException(status_code=404, detail="{msg}")'

        if pattern.search(fixed):
            fixed = pattern.sub(replace_raise, fixed)
            warnings.append("[WARN] 'raise SQLAlchemyError' -> 'raise HTTPException(404)'.")

            if not self._is_imported(fixed, "HTTPException"):
                lines = fixed.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("from fastapi import"):
                        if "HTTPException" not in line:
                            lines[i] = line.rstrip() + ", HTTPException"
                            break
                fixed = "\n".join(lines)

        return fixed, warnings

    # ============================================================
    # Rule 20
    # ============================================================
    def _fix_tuple_return(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        pattern = re.compile(
            r'return\s+\{\s*["\']error["\']\s*:\s*["\']([^"\']+)["\']\s*\}\s*,\s*(\d{3})'
        )

        def replace_return(match: re.Match) -> str:
            msg = match.group(1)
            status = match.group(2)
            return f'raise HTTPException(status_code={status}, detail="{msg}")'

        if pattern.search(fixed):
            fixed = pattern.sub(replace_return, fixed)
            warnings.append("[WARN] 'return {\"error\": ...}, XXX' -> 'raise HTTPException(XXX)'.")

            if not self._is_imported(fixed, "HTTPException"):
                lines = fixed.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("from fastapi import"):
                        if "HTTPException" not in line:
                            lines[i] = line.rstrip() + ", HTTPException"
                            break
                fixed = "\n".join(lines)

        return fixed, warnings

    # ============================================================
    # Rule 15
    # ============================================================
    def _fix_on_event_lifespan(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        if '@app.on_event("startup")' not in code:
            return code, warnings

        lines = code.split("\n")
        new_lines: list[str] = []
        startup_func_name: str | None = None
        startup_is_async: bool = False
        i = 0

        while i < len(lines):
            line = lines[i]
            if '@app.on_event("startup")' in line:
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    match = re.match(r"(\s*)(async\s+)?def\s+(\w+)\s*\(", next_line)
                    if match:
                        startup_is_async = bool(match.group(2))
                        startup_func_name = match.group(3)
                        i += 1
                        continue
            new_lines.append(line)
            i += 1

        code = "\n".join(new_lines)

        if startup_func_name:
            if "from contextlib import asynccontextmanager" not in code:
                lines = code.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith(("from ", "import ")):
                        lines.insert(i, "from contextlib import asynccontextmanager")
                        break
                code = "\n".join(lines)

            if startup_is_async:
                call_line = f"await {startup_func_name}()"
            else:
                call_line = f"await asyncio.to_thread({startup_func_name})"
                if "import asyncio" not in code:
                    lines = code.split("\n")
                    for i, line in enumerate(lines):
                        if line.strip().startswith(("from ", "import ")):
                            lines.insert(i, "import asyncio")
                            break
                    code = "\n".join(lines)

            lifespan_code = f'''

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown events (modern lifespan pattern)."""
    # ==== STARTUP ====
    {call_line}
    yield
    # ==== SHUTDOWN ====
'''

            if "app = FastAPI()" in code:
                code = code.replace(
                    "app = FastAPI()",
                    lifespan_code + "\n\napp = FastAPI(lifespan=lifespan)",
                    1,
                )
                warnings.append("[WARN] '@app.on_event(\"startup\")' -> 'lifespan' ile evez edildi.")

        return code, warnings

    # ============================================================
    # Rule 14
    # ============================================================
    def _fix_next_get_db(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        if "next(get_db())" not in code:
            return code, warnings

        lines = code.split("\n")
        new_lines = [l for l in lines if not re.match(r"\s*db\s*=\s*next\(get_db\(\)\)\s*$", l)]
        code = "\n".join(new_lines)

        def add_depends(match: re.Match) -> str:
            func_def = match.group(0)
            func_name_match = re.match(r"def\s+(\w+)\s*\(", func_def)
            if func_name_match and func_name_match.group(1) in PROTECTED_FUNCS:
                return func_def
            if "Depends(get_db)" in func_def or "db:" in func_def:
                return func_def
            if "(" in func_def and ")" in func_def:
                inner = func_def[func_def.index("(") + 1 : func_def.rindex(")")]
                if inner.strip():
                    new_inner = inner.rstrip().rstrip(",") + ", db: Session = Depends(get_db)"
                    return func_def[: func_def.index("(") + 1] + new_inner + ")"
                else:
                    return func_def[: func_def.index("(") + 1] + "db: Session = Depends(get_db))"
            return func_def

        code = re.sub(r"def \w+\([^)]*\)", add_depends, code)

        if not self._is_imported(code, "Depends"):
            lines = code.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("from fastapi import"):
                    if "Depends" not in line:
                        lines[i] = line.rstrip() + ", Depends"
                        break
            code = "\n".join(lines)

        if not self._is_imported(code, "Session"):
            lines = code.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("from sqlalchemy.orm import"):
                    if "Session" not in line:
                        lines[i] = line.rstrip() + ", Session"
                        break
            code = "\n".join(lines)

        warnings.append("[WARN] 'db = next(get_db())' -> 'Depends(get_db)' ile evez edildi.")
        return code, warnings

    # ============================================================
    # Rule 23
    # ============================================================
    def _fix_duplicate_init_db(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []

        lifespan_pattern = re.compile(
            r"async def lifespan\([^)]*\):(.*?)yield",
            re.DOTALL,
        )
        lifespan_match = lifespan_pattern.search(code)
        has_lifespan_call = bool(
            lifespan_match and re.search(r"init_db\s*\(\)", lifespan_match.group(1))
        )

        main_pattern = re.compile(
            r"if __name__.*?(init_db\s*\(\s*\))",
            re.DOTALL,
        )
        has_main_call = bool(main_pattern.search(code))

        if has_lifespan_call and has_main_call:
            code = re.sub(
                r"(\n\s+init_db\s*\(\s*\)\s*\n)",
                "\n",
                code,
                count=1,
            )
            warnings.append("[WARN] Duplicate 'init_db()' silindi (lifespan artiq cagirir).")

        return code, warnings

    # ============================================================
    # Rule 8
    # ============================================================
    def _fix_missing_functions(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, warnings

        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.asname or alias.name.split(".")[0])

        classes: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)

        defined: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(node.name)

        called: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called.add(node.func.id)

        missing = called - defined - imported - classes - BUILTINS - RULE8_IGNORED

        if not missing:
            return code, warnings

        if "init_db" in missing:
            warnings.append("[WARN] 'init_db()' teyin olunmayib, startup ucun elave edildi.")
            init_db_code = '''

# ==== Avtomatik elave olundu (Rule 8) ====
def init_db():
    """Database initialization (auto-generated)."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all([
                User(name="Alice", age=30),
                User(name="Bob", age=25),
                User(name="Charlie", age=35),
            ])
            db.commit()
    finally:
        db.close()
'''
            if 'if __name__' in code:
                code = code.replace('if __name__', init_db_code + '\n\nif __name__')
            else:
                code += init_db_code
            missing.discard("init_db")

        for func_name in sorted(missing):
            if func_name[0].isupper():
                continue

            warnings.append(f"[WARN] '{func_name}()' teyin olunmayib, stub elave edildi.")
            stub = f'''

# ==== Avtomatik stub (Rule 8) ====
def {func_name}(*args, **kwargs):
    """Auto-generated stub - implement edin."""
    raise NotImplementedError("'{func_name}' hele implement edilmeyib.")
'''
            if 'if __name__' in code:
                code = code.replace('if __name__', stub + '\n\nif __name__')
            else:
                code += stub

        return code, warnings

    # ============================================================
    # Rule 9
    # ============================================================
    def _fix_hardcoded_url(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        pattern = r'DATABASE_URL\s*=\s*["\']([^"\']+)["\']'

        def replace_url(match: re.Match) -> str:
            url = match.group(1)
            return f'DATABASE_URL = os.getenv("DATABASE_URL", "{url}")'

        if re.search(pattern, fixed):
            fixed = re.sub(pattern, replace_url, fixed)
            warnings.append("[WARN] Hardcoded DATABASE_URL -> os.getenv() ile evez edildi.")

            if not re.search(r"^\s*import\s+os\b", fixed, re.MULTILINE):
                lines = fixed.split("\n")
                inserted = False
                for i, line in enumerate(lines):
                    if line.strip().startswith(("from ", "import ")):
                        lines.insert(i, "import os")
                        inserted = True
                        break
                if not inserted:
                    lines.insert(0, "import os")
                fixed = "\n".join(lines)
                warnings.append("[WARN] 'import os' avtomatik elave edildi.")

        return fixed, warnings

    # ============================================================
    # Rule 10
    # ============================================================
    def _fix_optional_param(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        if (
            re.search(r"name\s*:\s*str\s*=\s*None", fixed)
            and "User.name == name" in fixed
        ):
            fixed = re.sub(
                r"name\s*:\s*str\s*=\s*None",
                'name: str = Query(..., description="Name to search")',
                fixed,
            )
            warnings.append("[WARN] 'name: str = None' -> 'Query(...)' (mecburi parametr).")

            if not self._is_imported(fixed, "Query"):
                lines = fixed.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("from fastapi import"):
                        if "Query" not in line:
                            lines[i] = line.rstrip() + ", Query"
                            warnings.append("[WARN] 'Query' fastapi import-a elave edildi.")
                        break
                fixed = "\n".join(lines)

        return fixed, warnings

    # ============================================================
    # Rule 6
    # ============================================================
    def _fix_missing_imports(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        used_names: set[str] = set()
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for name in ALL_IMPORTS:
                if not stripped.startswith(("from ", "import ")):
                    if re.search(rf"\b{name}\b", stripped):
                        used_names.add(name)

        missing_imports: list[str] = []
        for name in used_names:
            if not self._is_imported(code, name):
                missing_imports.append(ALL_IMPORTS[name])
                self._imports_added_this_run.add(name)

        if not missing_imports:
            return code, warnings

        lines = code.split("\n")
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith(("from ", "import ")):
                last_import_idx = i
            elif last_import_idx >= 0 and line.strip():
                break

        if last_import_idx == -1:
            new_lines = missing_imports + [""] + lines
        else:
            new_lines = (
                lines[: last_import_idx + 1]
                + missing_imports
                + lines[last_import_idx + 1 :]
            )

        for imp in missing_imports:
            warnings.append(f"[WARN] Avtomatik elave edildi: {imp}")

        return "\n".join(new_lines), warnings

    def _is_imported(self, code: str, name: str) -> bool:
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if (alias.asname or alias.name) == name:
                            return True
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if (alias.asname or alias.name.split(".")[0]) == name:
                            return True
            return False
        except SyntaxError:
            patterns = [
                rf"from\s+\S+\s+import\s+.*\b{name}\b",
                rf"import\s+{name}\b",
                rf"import\s+\S+\s+as\s+{name}\b",
            ]
            return any(re.search(p, code) for p in patterns)

    # ============================================================
    # Rule 7
    # ============================================================
    def _detect_unused_imports(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, warnings

        used_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                used_names.add(node.attr)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name in {"dotenv", "load_dotenv"}:
                        continue
                    if name not in used_names and name != "*":
                        warnings.append(f"[WARN] '{name}' import edilib, amma istifade olunmur.")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if name not in used_names:
                        warnings.append(f"[WARN] '{name}' import edilib, amma istifade olunmur.")

        return code, warnings

    # ============================================================
    # Rule 11
    # ============================================================
    def _remove_unused_imports_actual(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code, warnings

        used_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                used_names.add(node.attr)

        lines_to_remove: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                all_unused = True
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name in {"dotenv", "load_dotenv"}:
                        all_unused = False
                        break
                    if name in used_names:
                        all_unused = False
                        break
                    if name in self._imports_added_this_run:
                        all_unused = False
                        break
                if all_unused and node.names:
                    lines_to_remove.add(node.lineno - 1)
            elif isinstance(node, ast.Import):
                all_unused = True
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if name in used_names:
                        all_unused = False
                        break
                    if name in self._imports_added_this_run:
                        all_unused = False
                        break
                if all_unused:
                    lines_to_remove.add(node.lineno - 1)

        if not lines_to_remove:
            return code, warnings

        lines = code.split("\n")
        new_lines: list[str] = []
        for i, line in enumerate(lines):
            if i in lines_to_remove:
                warnings.append(f"[WARN] Silindi (unused): {line.strip()}")
                continue
            new_lines.append(line)

        return "\n".join(new_lines), warnings

    # ============================================================
    # Rule 12
    # ============================================================
    def _fix_session_type_hint(self, code: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        fixed = code

        if re.search(r":\s*SessionLocal\s*=\s*Depends", fixed):
            fixed = re.sub(
                r":\s*SessionLocal(\s*=\s*Depends)",
                r": Session\1",
                fixed,
            )
            warnings.append("[WARN] 'SessionLocal' type hint -> 'Session' ile evez edildi.")

            if not self._is_imported(fixed, "Session"):
                lines = fixed.split("\n")
                for i, line in enumerate(lines):
                    if line.strip().startswith("from sqlalchemy.orm import"):
                        if "Session" not in line:
                            lines[i] = line.rstrip() + ", Session"
                            break
                    elif line.strip().startswith("from sqlalchemy"):
                        lines.insert(i + 1, "from sqlalchemy.orm import Session")
                        break
                fixed = "\n".join(lines)
                warnings.append("[WARN] 'Session' import-a elave edildi.")

        return fixed, warnings