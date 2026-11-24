"""Testy funkcji pomocniczych. Uruchomienie w folderze kalkulator_v2: pytest"""
import datetime
import sqlite3
import sys
from pathlib import Path

import pandas as pd

# dzięki temu test widzi plik funkcje.py z folderu wyżej
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from funkcje import (tekst_na_liczbe, ustal_obecna_zmiane,  # noqa: E402
                     uwzglednij_wypozyczenia, zapisz_do_bazy)


# ---------- ustal_obecna_zmiane ----------

def test_rano_i_popoludniu_pracuja_rozne_brygady():
    rano = datetime.datetime(2026, 11, 23, 8, 0)
    popoludnie = datetime.datetime(2026, 11, 23, 15, 0)
    assert ustal_obecna_zmiane(rano) != ustal_obecna_zmiane(popoludnie)


def test_brygady_zmieniaja_sie_co_tydzien():
    ten_tydzien = datetime.datetime(2026, 11, 23, 8, 0)
    nastepny_tydzien = datetime.datetime(2026, 11, 30, 8, 0)
    assert ustal_obecna_zmiane(ten_tydzien) != ustal_obecna_zmiane(nastepny_tydzien)


def test_rotacja_dziala_na_przelomie_roku_z_53_tygodniami():
    # rok 2026 ma 53 tygodnie - tydzień 53 i tydzień 1 roku 2027 są oba nieparzyste
    tydzien_53 = datetime.datetime(2026, 12, 28, 8, 0)
    tydzien_1 = datetime.datetime(2027, 1, 4, 8, 0)
    assert ustal_obecna_zmiane(tydzien_53) != ustal_obecna_zmiane(tydzien_1)


# ---------- tekst_na_liczbe ----------

def test_tekst_z_sap_zamieniany_na_liczbe():
    kolumna = pd.Series([' 12,500', '12,5', '7'])
    assert tekst_na_liczbe(kolumna).tolist() == [12.5, 12.5, 7.0]


# ---------- uwzglednij_wypozyczenia ----------

def pracownik(numer, typ, stanowisko, godziny, pole_tekstowe=''):
    """Jeden wiersz listy pracowników (tylko kolumny potrzebne w teście)."""
    return {'Numer osobowy': numer, 'Typ pracownika': typ, 'Stanowisko robocze': stanowisko,
            'stanowisko_robocze': stanowisko, 'Ilość godzin': godziny, 'Pole tekstowe.1': pole_tekstowe}


def test_wypozyczony_na_caly_dzien_liczony_tam_gdzie_pracuje():
    df = pd.DataFrame([
        pracownik(1, 'N', 'MC01.165', 8),
        pracownik(1, 'W', 'MC02.170', 8),
    ])
    wynik = uwzglednij_wypozyczenia(df)
    assert wynik['stanowisko_robocze'].tolist() == ['MC02.170']


def test_wypozyczony_na_kilka_godzin_zostaje_na_swoim_stanowisku():
    df = pd.DataFrame([
        pracownik(1, 'N', 'MC01.165', 8),
        pracownik(1, 'W', 'MC02.170', 4),
    ])
    wynik = uwzglednij_wypozyczenia(df)
    assert wynik['stanowisko_robocze'].tolist() == ['MC01.165']


def test_szkolenia():
    df = pd.DataFrame([
        pracownik(1, 'N', 'SZKOL_WE', 8, 'szkolenie MC03.180'),  # przeniesiony na MC03.180
        pracownik(2, 'N', 'SZKOL_WE', 0),                        # pominięty
        pracownik(3, 'N', 'SZKOL_WE', 4),                        # zostaje na szkoleniu
    ])
    wynik = uwzglednij_wypozyczenia(df)
    assert wynik['stanowisko_robocze'].tolist() == ['MC03.180', 'SZKOL_WE']


# ---------- zapisz_do_bazy ----------

def test_zapis_do_bazy_zastepuje_poprzedni_wynik(tmp_path):
    # tmp_path - tymczasowy folder tworzony przez pytest na czas testu
    baza = tmp_path / "test.db"
    df = pd.DataFrame({"Stacja_robocza": ["MC01.165", "MC02.170"], "bilans_mocy": [1.5, -0.5]})

    # dwa uruchomienia - w bazie ma zostać tylko wynik ostatniego
    zapisz_do_bazy(df, baza, "matrix_coois_zasoby")
    zapisz_do_bazy(df, baza, "matrix_coois_zasoby")

    polaczenie = sqlite3.connect(baza)
    wynik = pd.read_sql("SELECT * FROM matrix_coois_zasoby", polaczenie)
    polaczenie.close()

    pd.testing.assert_frame_equal(wynik, df)
