"""Funkcje pomocnicze używane w notebooku kalkulator_mocy.ipynb.

Są w osobnym pliku, żeby można je było sprawdzić testami (folder tests/).
"""
import configparser
import datetime
import sqlite3
from pathlib import Path

import pandas as pd


def wczytaj_sciezki(plik_konfiguracji=".config.ini"):
    """Wczytuje ścieżki do plików z prywatnego pliku konfiguracji.

    Plik .config.ini nie trafia do repozytorium (jest w .gitignore).
    Wzór jego zawartości jest w config.example.ini.
    """
    if not Path(plik_konfiguracji).exists():
        raise FileNotFoundError(
            f"Brak pliku {plik_konfiguracji}. Skopiuj config.example.ini "
            "do .config.ini i wpisz własne ścieżki."
        )
    # interpolation=None - dzięki temu znak '%' w ścieżce nie powoduje błędu
    config = configparser.ConfigParser(interpolation=None)
    config.read(plik_konfiguracji, encoding="utf-8")
    return {**config["wejscie"], **config["wyjscie"]}


def ustal_obecna_zmiane(teraz):
    """Zwraca brygadę ('A' lub 'B'), która pracuje w podanym momencie.

    Brygady co tydzień zamieniają się zmianami (ranna / popołudniowa).
    Liczymy tygodnie od stałej daty, a nie z numeru tygodnia w roku,
    bo niektóre lata mają 53 tygodnie (np. 2026) - wtedy tydzień 53
    i tydzień 1 są oba nieparzyste i rotacja by się przesunęła.
    """
    # poniedziałek tygodnia, w którym brygada A była na rannej zmianie
    data_odniesienia = datetime.date(2024, 1, 1)
    tygodnie = (teraz.date() - data_odniesienia).days // 7

    poranna_zmiana = "A" if tygodnie % 2 == 0 else "B"
    popoludniowa_zmiana = "B" if poranna_zmiana == "A" else "A"

    # zmiana popołudniowa przejmuje linię o 14:00
    if teraz.hour < 14:
        return poranna_zmiana
    return popoludniowa_zmiana


def tekst_na_liczbe(kolumna):
    """Zamienia tekst z eksportu SAP (np. ' 12,500') na liczbę 12.5."""
    tekst = kolumna.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(tekst, errors="coerce")


def uwzglednij_wypozyczenia(df_zasoby):
    """Poprawia listę pracowników o wypożyczenia i szkolenia.

    Pracownik wypożyczony na inne stanowisko ma w SAP dwa wpisy:
    macierzysty (typ N/B/Z) i wypożyczenie (typ W). Zostawiamy jeden:
    - wypożyczenie > 7 h  -> liczymy go tam, gdzie go wypożyczono,
    - wypożyczenie <= 7 h -> liczymy go na stanowisku macierzystym.
    Szkolenie (SZKOL_WE):
    - > 7 h        -> przenosimy na stanowisko zapisane w polu tekstowym,
    - 0 lub 0,5 h  -> pomijamy.
    """
    df = df_zasoby[df_zasoby["Typ pracownika"].isin(["N", "B", "Z", "W"])]

    # numery osobowe wypożyczonych, podzielone wg liczby godzin
    wypozyczeni = df[df["Typ pracownika"] == "W"]
    wiecej_7h = wypozyczeni[wypozyczeni["Ilość godzin"] > 7]["Numer osobowy"]
    mniej_7h = wypozyczeni[wypozyczeni["Ilość godzin"] <= 7]["Numer osobowy"]

    # wiersze do usunięcia (drugi, zbędny wpis tej samej osoby)
    do_usuniecia = (
        (df["Numer osobowy"].isin(wiecej_7h) & df["Typ pracownika"].isin(["N", "B", "Z"]))
        | (df["Numer osobowy"].isin(mniej_7h) & (df["Typ pracownika"] == "W"))
    )
    df = df[~do_usuniecia].reset_index(drop=True)

    # szkolenia - zmieniamy kolumnę `stanowisko_robocze`, bo po niej
    # później grupujemy pracowników
    for index, row in df.iterrows():
        if row["Stanowisko robocze"] != "SZKOL_WE":
            continue
        if row["Ilość godzin"] > 7:
            # ostatnie 8 znaków pola tekstowego to stanowisko, np. 'MC01.165'
            df.loc[index, "stanowisko_robocze"] = str(row["Pole tekstowe.1"])[-8:]
        elif row["Ilość godzin"] in (0, 0.5):
            df.loc[index, "stanowisko_robocze"] = "DO_USUNIECIA"

    return df[df["stanowisko_robocze"] != "DO_USUNIECIA"].reset_index(drop=True)


def zapisz_arkusz(df, sciezka, nazwa_arkusza):
    """Zapisuje DataFrame do arkusza pliku Excel czytanego przez Power BI.

    Jeśli plik już istnieje, podmieniany jest tylko ten jeden arkusz.
    Jeśli pliku nie ma, zostaje utworzony.
    """
    if Path(sciezka).exists():
        with pd.ExcelWriter(sciezka, mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=nazwa_arkusza)
    else:
        with pd.ExcelWriter(sciezka) as writer:
            df.to_excel(writer, sheet_name=nazwa_arkusza)


def zapisz_do_bazy(df, sciezka_bazy, nazwa_tabeli):
    """Zapisuje DataFrame jako tabelę w bazie SQLite.

    SQLite to baza danych w jednym pliku - nie wymaga serwera.
    Jeśli pliku bazy nie ma, zostanie utworzony. Tabela jest za każdym
    razem zastępowana nową (if_exists='replace'), więc w bazie jest zawsze
    wynik ostatniego uruchomienia.
    """
    polaczenie = sqlite3.connect(sciezka_bazy)
    try:
        df.to_sql(nazwa_tabeli, polaczenie, if_exists="replace", index=False)
    finally:
        # połączenie zamykamy zawsze, nawet gdy zapis się nie uda
        polaczenie.close()
