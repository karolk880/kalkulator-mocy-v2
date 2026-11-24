#!/usr/bin/env bash
# Uruchamia notebook kalkulator_mocy.ipynb bez otwierania Jupytera.
# Używany przez cron (patrz README.md, sekcja "Harmonogram").

# zatrzymaj skrypt przy pierwszym błędzie
set -euo pipefail

# przejście do folderu, w którym leży ten skrypt - cron startuje w katalogu domowym
cd "$(dirname "$(readlink -f "$0")")"

# środowisko wirtualne z pandas, openpyxl i jupyter
source .venv/bin/activate

mkdir -p logi
echo "=== $(date '+%Y-%m-%d %H:%M:%S') start ==="

# --execute               - wykonaj wszystkie komórki
# --output-dir / --output - kopia notebooka z wynikami trafia do logi/,
#                           oryginał zostaje bez zmian
# timeout=600             - przerwij, jeśli jedna komórka trwa dłużej niż 10 minut
jupyter nbconvert --to notebook --execute kalkulator_mocy.ipynb \
    --output-dir logi --output ostatnie_uruchomienie \
    --ExecutePreprocessor.timeout=600

echo "=== $(date '+%Y-%m-%d %H:%M:%S') koniec ==="
