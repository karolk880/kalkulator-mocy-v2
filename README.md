# Kalkulator mocy produkcyjnych

Notebook w Pythonie (pandas), który sprawdza, czy na stacjach linii montażowej
jest wystarczająco dużo pracowników do wykonania planu produkcji.
Wynik zapisywany jest do pliku Excel, z którego korzysta raport **Power BI**,
oraz do bazy **SQLite**.

## Skąd pomysł

Na linii montażowej każdy pojazd przechodzi kolejno przez stacje, a na każdej
stacji spędza jeden takt. Różne pojazdy wymagają różnej ilości pracy, więc
liczba potrzebnych osób na stacji zmienia się z taktu na takt. Notebook
porównuje to zapotrzebowanie z liczbą pracowników obecnych na zmianie.

## Jak to działa

1. **Plan produkcji (ZPP_PLAN)**: kolejność pojazdów na linii. Na tej podstawie
   powstaje matryca: który pojazd stoi na której stacji w kolejnych taktach.
2. **Plan SOP**: dla każdej pozycji kontraktu wybierany jest ostatni pojazd,
   bo jego marszruta jest najbardziej aktualna.
3. **Operacje (OPERACJE_ZP03)**: czasy montażu na stacjach. Czas podzielony
   przez czas taktu daje liczbę potrzebnych osób.
4. **Zasoby (ZPP_T_ZZASOBY)**: lista pracowników z obecnościami. Notebook
   ustala, która brygada pracuje teraz, i liczy obecnych na stanowiskach.
5. **Wynik**: `bilans_mocy = obecni − potrzebne_moce`. Wartość ujemna oznacza
   brak ludzi na stacji.

Wynik trafia w dwa miejsca, za każdym razem jako dwie tabele:
- `matrix_coois_zasoby`: bilans mocy dla każdej stacji i taktu,
- `zasoby_total`: absencja na stanowiskach.

| Miejsce | Do czego |
|---|---|
| plik Excel (`raport`) | źródło danych dla raportu Power BI |
| baza SQLite (`baza`) | analiza zapytaniami SQL; przy każdym uruchomieniu tabele są zastępowane najnowszym wynikiem |

Przykładowe zapytanie, które pokazuje stacje z największym brakiem ludzi:

```sql
SELECT Stacja_robocza, MIN(bilans_mocy) AS najwiekszy_brak
FROM matrix_coois_zasoby
GROUP BY Stacja_robocza
ORDER BY najwiekszy_brak;
```

## Pliki

| Plik | Opis |
|---|---|
| `kalkulator_mocy.ipynb` | główny notebook |
| `funkcje.py` | funkcje pomocnicze (ścieżki, zmiana, wypożyczenia, zapis do Excela i SQLite) |
| `tests/test_funkcje.py` | testy funkcji pomocniczych |
| `uruchom.sh` | uruchamia notebook bez Jupytera (dla crona) |
| `config.example.ini` | wzór pliku ze ścieżkami |

Dane wejściowe to eksporty z SAP (CSV) i ręcznie prowadzony słownik stacji
(`slownik.xlsx`). Dane nie są częścią repozytorium.

## Uruchomienie

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.ini .config.ini   # wpisz własne ścieżki do plików
```

Następnie otwórz `kalkulator_mocy.ipynb` w Jupyter lub VS Code i uruchom
wszystkie komórki. Z terminala, bez otwierania notebooka:

```bash
./uruchom.sh
```

Testy:

```bash
pytest
```

## Harmonogram (cron, Ubuntu 26.04 LTS)

Cron to systemowy harmonogram zadań w Linuksie. Uruchamia polecenia o
określonych porach, także wtedy, gdy nikt nie jest zalogowany. Dzięki niemu
raport w Power BI odświeża się sam.

### 1. Przygotowanie systemu

```bash
# Python ze środowiskami wirtualnymi (Ubuntu nie pozwala instalować
# pakietów pip w systemowym Pythonie, dlatego potrzebne jest .venv)
sudo apt install python3-venv

# cron - sprawdź, czy działa; jeśli usługi nie ma, zainstaluj ją
systemctl status cron
sudo apt install cron
sudo systemctl enable --now cron

# strefa czasowa - notebook ustala zmianę na podstawie godziny,
# więc serwer musi mieć czas polski
timedatectl
sudo timedatectl set-timezone Europe/Warsaw
```

### 2. Przygotowanie projektu

Wykonaj kroki z sekcji [Uruchomienie](#uruchomienie). Następnie:

```bash
chmod +x uruchom.sh   # pozwolenie na uruchamianie skryptu
mkdir -p logi         # folder na logi crona
./uruchom.sh          # próbne uruchomienie - musi zakończyć się bez błędów
```

Ścieżki w `.config.ini` muszą być ścieżkami Linuksa. Pliki z dysku sieciowego
Windows trzeba najpierw zamontować (np. pakietem `cifs-utils`) i wpisać ścieżkę
do punktu montowania, np. `/mnt/raporty/SEP100ZPP_PLAN.CSV`.

### 3. Dodanie zadania do crona

```bash
crontab -e
```

Dopisz na końcu pliku jedną linię (zamień `/home/uzytkownik/kalkulator_v2`
na swoją ścieżkę; jeśli ścieżka zawiera spacje, weź ją w cudzysłów):

```
*/30 6-21 * * 1-5 /home/uzytkownik/kalkulator_v2/uruchom.sh >> /home/uzytkownik/kalkulator_v2/logi/cron.log 2>&1
```

Ta linia oznacza: co 30 minut, od 6:00 do 21:30, od poniedziałku do piątku.
Kolejne pola to:

```
*/30   6-21    *            *         1-5
minuta godzina dzień_miesiąca miesiąc  dzień_tygodnia (1 = poniedziałek)
```

Część `>> .../logi/cron.log 2>&1` dopisuje wszystkie komunikaty, także błędy,
do pliku z logami.

### 4. Sprawdzenie, czy działa

```bash
crontab -l                          # lista zadań
tail -n 20 logi/cron.log            # ostatnie uruchomienia skryptu
journalctl -u cron --since today    # czy cron uruchomił zadanie
```

Kopia notebooka z wynikami ostatniego uruchomienia jest w
`logi/ostatnie_uruchomienie.ipynb`. Można ją otworzyć i zobaczyć, w której
komórce wystąpił błąd. Ostrzeżenie `Kernel is running over TCP without
encryption` w logu jest niegroźne: kernel działa lokalnie na tym samym
komputerze.

Do przeglądania bazy z terminala służy `sqlite3`
(`sudo apt install sqlite3`):

```bash
sqlite3 kalkulator_mocy.db "SELECT * FROM zasoby_total;"
```

## Technologie

Python · pandas · Jupyter · SQLite · pytest · cron · Power BI
