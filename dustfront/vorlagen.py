"""
DUSTFRONT - Vorlagen und Bestandsliste
======================================

Zwei kleine Werkzeuge rund um die Aussenhaut. Beide ruehren das Spiel nicht
an, sie schauen es nur an.

    python -m dustfront --vorlagen     schreibt jedes im Code gezeichnete Bild
                                       als PNG nach assets_vorlage/
    python -m dustfront --assets       sagt, welcher Name gerade aus einer
                                       Datei kommt und welcher aus dem Code

Wozu die Vorlagen? Wer eine Textur malen will, braucht zwei Angaben: wie
gross sie sein muss und wie das aussieht, was sie ersetzt. Beides steckt im
Platzhalter. `--vorlagen` legt ihn masshaltig auf die Platte, man malt
darueber, kopiert die Datei nach `assets/` und ist fertig. Umbenennen ist
nicht noetig, der Dateiname ist schon der richtige.

Die Uebersichtstafel `_uebersicht.png` zeigt alle Bilder nebeneinander mit
Namen und Mass, damit man beim Malen nicht dauernd im README nachschlaegt.
Durchsichtige Stellen liegen dort auf einem Schachbrett, sonst sieht man
nicht, wo ein Bild aufhoert.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import config as K


def _bildschirm_los() -> None:
    """pygame ohne Fenster hochfahren. Die Platzhalter zeichnen auf eine
    Flaeche, und dafuer muss ein Anzeigemodus gesetzt sein.

    Laeuft schon einer, etwa weil der Test das Werkzeug aufruft, bleibt er
    stehen: ein zweites set_mode wuerde ihm die Flaeche unter den Fuessen
    wegziehen.
    """
    import pygame
    if pygame.display.get_surface() is not None:
        return
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((K.TILE, K.TILE))


def _karo(pygame, groesse):
    """Schachbrett als Untergrund, damit man Durchsichtiges erkennt."""
    w, h = groesse
    f = K.VORLAGEN["karo_feld"]
    s = pygame.Surface(groesse)
    s.fill(K.VORLAGEN["karo"])
    for y in range(0, h, f):
        for x in range(0, w, f):
            if (x // f + y // f) % 2:
                s.fill(K.VORLAGEN["karo_2"], (x, y, f, f))
    return s


def namen() -> list[str]:
    """Alle Bildnamen, die das Spiel kennt, in der Reihenfolge der Tabelle."""
    from .core import _PLATZHALTER
    from . import art  # noqa: F401  registriert die Platzhalter
    aus_tabelle = list(K.BILD_MASS)
    # Was jemand registriert, aber in der Tabelle vergessen hat, faellt sonst
    # unter den Tisch. Lieber hinten anhaengen als verschweigen.
    dazu = [n for n in _PLATZHALTER if n not in K.BILD_MASS]
    return aus_tabelle + sorted(dazu)


def _tafel(pygame, bilder, liste):
    """Alle Bilder auf eine Tafel, mit Namen und Mass darunter."""
    from .font import SCHRIFT
    v = K.VORLAGEN
    zw, zh = v["zelle"]
    spalten = v["spalten"]
    zeilen = (len(liste) + spalten - 1) // spalten
    w = v["rand"] * 2 + spalten * zw
    h = v["rand"] * 2 + v["kopf"] + zeilen * zh
    tafel = pygame.Surface((w, h))
    tafel.fill(K.C_VOID)
    SCHRIFT.zeichnen(tafel, "DUSTFRONT %s - VORLAGEN" % K.VERSION,
                     w // 2, v["rand"], K.C_AMBER, 1, ausrichtung="mitte")
    SCHRIFT.zeichnen(tafel, "DATEI ASSETS/NAME.PNG ERSETZT DAS BILD",
                     w // 2, v["rand"] + 9, K.C_MUTED, 1, ausrichtung="mitte")
    platz = (zw - v["rand"], zh - v["luft"])
    for i, name in enumerate(liste):
        s = bilder.platzhalter(name)
        zelle = pygame.Rect(v["rand"] + (i % spalten) * zw,
                            v["rand"] + v["kopf"] + (i // spalten) * zh, zw, zh)
        mitte_y = zelle.y + (zh - v["luft"]) // 2
        # Was nicht in die Zelle passt - die Vignette ist bildschirmgross -
        # wird nur fuer die Anschauung verkleinert. Das Mass darunter nennt
        # weiter die echte Groesse.
        gezeigt, mass = s, s.get_size()
        if mass[0] > platz[0] or mass[1] > platz[1]:
            k = min(platz[0] / mass[0], platz[1] / mass[1])
            # Hier darf weichgezeichnet werden: die Tafel ist zum Anschauen,
            # nicht zum Spielen.
            gezeigt = pygame.transform.smoothscale(
                s, (max(1, int(mass[0] * k)), max(1, int(mass[1] * k))))
        grund = _karo(pygame, gezeigt.get_size())
        grund.blit(gezeigt, (0, 0))
        tafel.blit(grund, (zelle.centerx - gezeigt.get_width() // 2,
                           mitte_y - gezeigt.get_height() // 2))
        SCHRIFT.zeichnen(tafel, name.upper(), zelle.centerx, zelle.bottom - 15,
                         K.C_CREAM, 1, ausrichtung="mitte")
        SCHRIFT.zeichnen(tafel, "%d X %d" % mass, zelle.centerx,
                         zelle.bottom - 7, K.C_MUTED_DK, 1, ausrichtung="mitte")
    lupe = v["lupe"]
    return pygame.transform.scale(tafel, (w * lupe, h * lupe))


def schreiben(ziel: Path | None = None, melden: bool = True) -> int:
    """Schreibt alle Platzhalter als PNG und gibt die Anzahl zurueck."""
    _bildschirm_los()
    import pygame

    from .core import Bilder
    from .pfade import spielordner

    ziel = Path(ziel) if ziel is not None else spielordner() / K.ASSETS["vorlagen"]
    ziel.mkdir(parents=True, exist_ok=True)
    bilder = Bilder(None)          # None: immer der Code, nie eine Datei
    liste = namen()

    for name in liste:
        s = bilder.platzhalter(name)
        pygame.image.save(s, str(ziel / (name + ".png")))
    pygame.image.save(_tafel(pygame, bilder, liste), str(ziel / "_uebersicht.png"))
    if not melden:
        return len(liste)

    print("%d Vorlagen in %s" % (len(liste), ziel))
    for name in liste:
        soll = Bilder.mass(name)
        s = bilder.platzhalter(name)
        warnung = ""
        if soll is not None and soll != s.get_size():
            warnung = "   ACHTUNG: BILD_MASS sagt %d x %d" % soll
        print("  %-20s %3d x %-3d%s" % ((name,) + s.get_size() + (warnung,)))
    print("Uebersichtstafel: %s" % (ziel / "_uebersicht.png"))
    return len(liste)


def bestand() -> int:
    """Sagt zu jedem Namen, woher er gerade kommt: Datei oder Code."""
    _bildschirm_los()

    from .core import Bilder
    from .main import asset_ordner
    from .audio import Klaenge

    ordner = asset_ordner()
    print("Assets-Ordner: %s" % (ordner or "keiner, alles kommt aus dem Code"))
    print()
    print("BILDER")
    bilder = Bilder(ordner)
    aus_dateien = 0
    for name in namen():
        pfad = bilder.datei(name)
        s = bilder.bild(name)
        if pfad is not None:
            aus_dateien += 1
            herkunft = pfad.name
        else:
            herkunft = "Code"
        print("  %-20s %3d x %-3d  %s" % ((name,) + s.get_size() + (herkunft,)))

    print()
    print("KLAENGE")
    klaenge = Klaenge(ordner)
    for name in K.KLANG_NAMEN:
        klaenge.klang(name)
        print("  %-20s %s" % (name,
                              "Datei" if name in klaenge.aus_datei else "Code"))

    for grund in bilder.fehler + klaenge.fehler:
        print("  FEHLER: %s" % grund)
    print()
    print("%d von %d Bildern kommen aus Dateien." % (aus_dateien, len(namen())))
    return 0
