"""
ArchitectAI - Legacy Kod Refaktor Alehti
Entry point.
"""

import sys
from app.core.parser import Parser, ParserError
from app.core.refactor_engine import RefactorEngine


LEGACY_FILE = "legacy_code/old_app.py"
SEPARATOR = "=" * 60


def print_section(title):
    print(f"\n{SEPARATOR}\n{title}\n{SEPARATOR}")


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
        print("\nIstifadeci terefinden dayandirildi.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Gozlenilmez xeta: {type(e).__name__}: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
