import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(
        description="Usuwa pliki .mov z małej litery z podanej lokalizacji."
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Ścieżka do katalogu z plikami (domyślnie: bieżący katalog)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Fizycznie usuwa pliki. Bez tej flagi skrypt działa w trybie podglądu (dry-run)."
    )
    return parser.parse_args()

def remove_small_mov_files(directory: Path, dry_run: bool = True):
    if not directory.exists() or not directory.is_dir():
        print(f"Błąd: Katalog '{directory.resolve()}' nie istnieje lub nie jest folderem.")
        return

    counter = 0
    for file_path in directory.iterdir():
        # Sprawdza czy to plik oraz czy nazwa kończy się dokładnie na '.mov'
        if file_path.is_file() and file_path.name.endswith(".mov"):
            if dry_run:
                print(f"[PODGLĄD] Do usunięcia: {file_path.name}")
            else:
                file_path.unlink()
                print(f"[USUNIĘTO] {file_path.name}")
            counter += 1

    if dry_run:
        print(f"\nZnaleziono {counter} plików z rozszerzeniem .mov.")
        print("Uruchom skrypt z flagą --apply, aby fizycznie skasować pliki.")
    else:
        print(f"\nPomyślnie usunięto {counter} plików.")

if __name__ == "__main__":
    args = parse_args()
    target_dir = Path(args.path)
    remove_small_mov_files(target_dir, dry_run=not args.apply)