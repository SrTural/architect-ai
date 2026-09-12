"""
ArchitectAI - Entry Point
=========================

İki rejimdə işləyir:

1. CLI Rejimi (default):
    python -m app.main

2. API Rejimi:
    python -m app.main api
"""

import sys
from typing import Callable

from app.core.parser import Parser, ParserError
from app.core.refactor_engine import RefactorEngine


# ==== Konfiqurasiya ====
LEGACY_FILE = "legacy_code/old_app.py"
SEPARATOR = "=" * 60


# ==== CLI Rejimi ====
def print_section(title: str) -> None:
    """Bölmə başlığını çap edir."""
    print(f"\n{SEPARATOR}\n{title}\n{SEPARATOR}")


def run_cli() -> int:
    """
    CLI rejimi: legacy kodu oxuyur, refaktor edir və nəticəni göstərir.

    Returns:
        int: Exit kodu (0 = uğurlu, 1+ = xəta).
    """
    try:
        parser = Parser(LEGACY_FILE)
        old_code = parser.get_full_code()
        print(f"✅ Yükləndi: {len(old_code)} simvol, {len(parser.get_functions())} funksiya")

        engine = RefactorEngine()
        result = engine.refactor(old_code)

        print_section("KÖHNƏ KOD (legacy)")
        print(result["old_code"])

        print_section("YENİ KOD (AI tərəfindən)")
        print(result["new_code"])

        print_section("NƏTİCƏ")
        status = "✅ UĞURLU" if result["valid_syntax"] else "❌ SİNTAKSİS XƏTASI"
        print(f"Sintaksis : {status}")
        print(f"Cəhd sayı : {result['attempts']}")

        return 0 if result["valid_syntax"] else 1

    except ParserError as e:
        print(f"❌ Parser xətası: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"❌ Fayl tapılmadı: {e}", file=sys.stderr)
        return 3


# ==== API Rejimi ====
def run_api() -> None:
    """API rejimi: FastAPI serverini işə salır."""
    import uvicorn

    print("🚀 ArchitectAI API serveri başladılır...")
    print("📖 Sənədləşdirmə: http://localhost:8000/docs")
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


# ==== Entry Point ====
def main() -> int:
    """
    Əsas giriş nöqtəsi.

    İstifadəçi arqumentlərini yoxlayır və uyğun rejimi işə salır.
    """
    commands: dict[str, Callable[[], int | None]] = {
        "api": run_api,
        "cli": run_cli,
    }

    # Arqument yoxdur → CLI rejimi
    if len(sys.argv) < 2:
        return run_cli()

    command = sys.argv[1].lower()

    # Naməlum əmr
    if command not in commands:
        print(f"❌ Naməlum əmr: '{command}'", file=sys.stderr)
        print(f"📌 Mövcud əmrlər: {', '.join(commands.keys())}", file=sys.stderr)
        return 64  # EX_USAGE

    handler = commands[command]
    result = handler()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⚠️ İstifadəçi tərəfindən dayandırıldı.", file=sys.stderr)
        sys.exit(130)