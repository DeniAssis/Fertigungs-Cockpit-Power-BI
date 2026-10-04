"""
Synthetische Fertigungsdaten für ein Power-BI-Dashboard.

Erzeugt CSV-Dateien im Ordner ./daten:
  dim_datum.csv, dim_produkt.csv, dim_station.csv, dim_fehlerart.csv,
  dim_standort.csv
  fakt_auftraege.csv, fakt_arbeitsschritte.csv, fakt_qualitaet.csv

Alle Daten sind frei erfunden (keine echten Firmen- oder Kundendaten).
Aufruf:  python fertigungsdaten_generieren.py
Benötigt: pandas, numpy
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_AUFTRAEGE = 3000
START = pd.Timestamp("2025-01-01")
ENDE = pd.Timestamp("2026-09-30")
AUSGABE = Path("daten")

rng = np.random.default_rng(SEED)

# --------------------------------------------------------------------------
# Stammdaten
# --------------------------------------------------------------------------
produkte = pd.DataFrame(
    {
        "ProduktID": ["P01", "P02", "P03", "P04", "P05"],
        "Produkt": [
            "Steuerungsmodul",
            "Sensorgehäuse",
            "Kabelbaum",
            "Antriebseinheit",
            "Schaltschrank",
        ],
        # Faktor für die Solldauer und die Fehlerneigung
        "Aufwandsfaktor": [1.0, 0.8, 1.2, 1.6, 2.0],
        "Fehlerfaktor": [1.0, 0.7, 1.6, 1.2, 1.1],
    }
)

stationen = pd.DataFrame(
    {
        "StationID": ["S1", "S2", "S3", "S4", "S5"],
        "Station": ["Zuschnitt", "Vormontage", "Montage", "Verkabelung", "Prüfung"],
        "Reihenfolge": [1, 2, 3, 4, 5],
        "Basis_Solldauer_h": [2.0, 3.0, 5.0, 4.0, 1.5],
        # Verkabelung ist der Engpass: längere Überschreitung und Wartezeit
        "Streuung": [0.10, 0.15, 0.20, 0.35, 0.10],
        "Wartezeit_h": [1.0, 2.0, 3.0, 8.0, 2.0],
        "Pruefung": [False, False, True, True, True],
        "Fehlerrate": [0.0, 0.0, 0.04, 0.07, 0.03],
    }
)

fehlerarten = pd.DataFrame(
    {
        "FehlerartID": ["F01", "F02", "F03", "F04", "F05", "F06"],
        "Fehlerart": [
            "Maßabweichung",
            "Lötfehler",
            "Falsche Verkabelung",
            "Oberflächenschaden",
            "Fehlendes Bauteil",
            "Sonstiges",
        ],
        "Gewicht": [0.28, 0.22, 0.20, 0.14, 0.10, 0.06],  # Pareto-Verteilung
        "Ausschuss_Anteil": [0.30, 0.20, 0.10, 0.35, 0.15, 0.25],
    }
)


standorte = pd.DataFrame(
    {
        "StandortID": ["W1", "W2", "W3", "W4", "W5"],
        "Standort": ["Werk Nord", "Werk Hanse", "Werk Ost", "Werk Süd", "Werk Südwest"],
        "Stadt": ["Hamburg", "Bremen", "Rostock", "Nürnberg", "Stuttgart"],
        "Bundesland": [
            "Hamburg",
            "Bremen",
            "Mecklenburg-Vorpommern",
            "Bayern",
            "Baden-Württemberg",
        ],
        "Breitengrad": [53.55, 53.08, 54.09, 49.45, 48.78],
        "Laengengrad": [9.99, 8.81, 12.14, 11.08, 9.18],
        "Gewicht": [0.28, 0.22, 0.14, 0.20, 0.16],
    }
)

# Kundenregionen (Bundesländer) mit grober Gewichtung
kundenregionen = pd.DataFrame(
    {
        "Bundesland": [
            "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen",
            "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen",
            "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen",
            "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen",
        ],
        "Gewicht": [11, 13, 4, 3, 1, 3, 7, 2, 9, 21, 5, 1, 5, 3, 4, 3],
    }
)


def datums_tabelle(von: pd.Timestamp, bis: pd.Timestamp) -> pd.DataFrame:
    tage = pd.date_range(von, bis, freq="D")
    return pd.DataFrame(
        {
            "Datum": tage,
            "Jahr": tage.year,
            "Quartal": "Q" + tage.quarter.astype(str),
            "Monat": tage.month,
            "Monatsname": tage.strftime("%b"),
            "Kalenderwoche": tage.isocalendar().week.values,
            "Wochentag": tage.dayofweek + 1,
        }
    )


# --------------------------------------------------------------------------
# Aufträge und Arbeitsschritte
# --------------------------------------------------------------------------
def erzeuge_auftraege():
    anzahl_tage = (ENDE - START).days - 30  # Platz für Durchlaufzeit am Ende
    auftragsdaten = START + pd.to_timedelta(
        rng.integers(0, anzahl_tage, N_AUFTRAEGE), unit="D"
    )
    auftragsdaten = np.sort(auftragsdaten.values)

    auftraege, schritte = [], []

    for i, auftragsdatum in enumerate(auftragsdaten, start=1):
        auftrag_id = f"A{i:05d}"
        produkt = produkte.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
        menge = int(rng.integers(5, 60))
        aktuelle_zeit = pd.Timestamp(auftragsdatum) + pd.Timedelta(hours=7)
        soll_gesamt_h = 0.0

        for _, st in stationen.iterrows():
            soll = st["Basis_Solldauer_h"] * produkt["Aufwandsfaktor"] * (1 + menge / 100)
            # Istdauer: meist etwas länger als Soll, an der Verkabelung stärker
            ist = soll * rng.lognormal(mean=0.05, sigma=st["Streuung"])
            wartezeit = rng.exponential(st["Wartezeit_h"])

            beginn = aktuelle_zeit + pd.Timedelta(hours=wartezeit)
            ende = beginn + pd.Timedelta(hours=ist)

            schritte.append(
                {
                    "AuftragID": auftrag_id,
                    "StationID": st["StationID"],
                    "Beginn": beginn.round("min"),
                    "Ende": ende.round("min"),
                    "Solldauer_h": round(soll, 2),
                    "Istdauer_h": round(ist, 2),
                    "Wartezeit_h": round(wartezeit, 2),
                }
            )
            aktuelle_zeit = ende
            soll_gesamt_h += soll

        # Liefertermin: geplante Arbeitszeit plus geplante Wartezeit plus kleiner Puffer.
        # Der Puffer ist knapp (teils negativ), damit ein Teil der Aufträge zu spät fertig wird.
        geplante_wartezeit_h = stationen["Wartezeit_h"].sum()
        puffer_tage = int(rng.choice([-1, 0, 0, 0, 1]))
        liefertermin = pd.Timestamp(auftragsdatum).normalize() + pd.Timedelta(
            days=int(np.ceil((soll_gesamt_h + geplante_wartezeit_h) / 24)) + puffer_tage
        )
        auftraege.append(
            {
                "AuftragID": auftrag_id,
                "ProduktID": produkt["ProduktID"],
                "Menge": menge,
                "Auftragsdatum": pd.Timestamp(auftragsdatum).normalize(),
                "Liefertermin": liefertermin,
                "Fertigstellung": aktuelle_zeit.normalize(),
            }
        )

    return pd.DataFrame(auftraege), pd.DataFrame(schritte)


# --------------------------------------------------------------------------
# Qualitätsprüfungen
# --------------------------------------------------------------------------
def erzeuge_qualitaet(auftraege: pd.DataFrame, schritte: pd.DataFrame) -> pd.DataFrame:
    produkt_faktor = produkte.set_index("ProduktID")["Fehlerfaktor"]
    pruefstationen = stationen[stationen["Pruefung"]].set_index("StationID")
    fehler_ids = fehlerarten["FehlerartID"].to_numpy()
    fehler_gewichte = fehlerarten["Gewicht"].to_numpy()
    ausschuss_anteil = fehlerarten.set_index("FehlerartID")["Ausschuss_Anteil"]

    schritte_idx = schritte.set_index(["AuftragID", "StationID"])
    zeilen = []
    pruef_nr = 1

    for _, a in auftraege.iterrows():
        for station_id, st in pruefstationen.iterrows():
            ende = schritte_idx.loc[(a["AuftragID"], station_id), "Ende"]
            wahrscheinlichkeit = st["Fehlerrate"] * produkt_faktor[a["ProduktID"]]
            anzahl_fehler = rng.binomial(a["Menge"], min(wahrscheinlichkeit, 0.5))

            for _ in range(anzahl_fehler):
                f_id = rng.choice(fehler_ids, p=fehler_gewichte)
                ist_ausschuss = rng.random() < ausschuss_anteil[f_id]
                zeilen.append(
                    {
                        "PruefID": f"Q{pruef_nr:06d}",
                        "AuftragID": a["AuftragID"],
                        "StationID": station_id,
                        "Pruefdatum": ende.normalize(),
                        "FehlerartID": f_id,
                        "Ausschuss": int(ist_ausschuss),
                        "Nacharbeit": int(not ist_ausschuss),
                    }
                )
                pruef_nr += 1

    return pd.DataFrame(zeilen)


# --------------------------------------------------------------------------
def ordne_orte_zu(auftraege: pd.DataFrame) -> pd.DataFrame:
    """Weist Aufträgen Werk und Kundenregion zu (eigener Zufallsgenerator,
    damit die übrigen Daten unverändert bleiben).
    Das Werk Hanse (Bremen) bekommt etwas mehr verspätete Aufträge,
    damit die Karte einen erkennbaren Unterschied zeigt."""
    rng_ort = np.random.default_rng(SEED + 1)
    puenktlich = (auftraege["Fertigstellung"] <= auftraege["Liefertermin"]).to_numpy()

    gewicht = standorte["Gewicht"].to_numpy()
    gewicht_spaet = gewicht.copy()
    gewicht_spaet[1] *= 2.2  # Werk Hanse
    gewicht = gewicht / gewicht.sum()
    gewicht_spaet = gewicht_spaet / gewicht_spaet.sum()

    ids = standorte["StandortID"].to_numpy()
    auftraege["StandortID"] = [
        rng_ort.choice(ids, p=gewicht if ok else gewicht_spaet) for ok in puenktlich
    ]

    g = kundenregionen["Gewicht"].to_numpy(dtype=float)
    auftraege["KundeBundesland"] = rng_ort.choice(
        kundenregionen["Bundesland"].to_numpy(), size=len(auftraege), p=g / g.sum()
    )
    return auftraege


def main():
    AUSGABE.mkdir(exist_ok=True)

    auftraege, schritte = erzeuge_auftraege()
    auftraege = ordne_orte_zu(auftraege)
    qualitaet = erzeuge_qualitaet(auftraege, schritte)

    tabellen = {
        "dim_datum": datums_tabelle(START, ENDE + pd.Timedelta(days=60)),
        "dim_produkt": produkte[["ProduktID", "Produkt"]],
        "dim_station": stationen[["StationID", "Station", "Reihenfolge"]],
        "dim_fehlerart": fehlerarten[["FehlerartID", "Fehlerart"]],
        "dim_standort": standorte.drop(columns="Gewicht"),
        "fakt_auftraege": auftraege,
        "fakt_arbeitsschritte": schritte,
        "fakt_qualitaet": qualitaet,
    }
    for name, df in tabellen.items():
        df.to_csv(AUSGABE / f"{name}.csv", index=False, encoding="utf-8-sig")
        print(f"{name}.csv: {len(df):,} Zeilen")

    termintreue = (auftraege["Fertigstellung"] <= auftraege["Liefertermin"]).mean()
    print(f"\nTermintreue gesamt: {termintreue:.1%}")
    auftraege["puenktlich"] = auftraege["Fertigstellung"] <= auftraege["Liefertermin"]
    print("\nTermintreue je Werk:")
    print(auftraege.groupby("StandortID")["puenktlich"].agg(["size", "mean"]).round(3))


if __name__ == "__main__":
    main()
