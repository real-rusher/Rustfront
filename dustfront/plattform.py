"""
DUSTFRONT - Worauf das Spiel gerade laeuft
==========================================

Seit 0.34.20, fuer den Port auf iOS (Branch `ios-port`, siehe
`ios/LIESMICH.md`). Was dort anders ist, steht hier an einer Stelle,
damit der Spielcode nicht an zwanzig Orten `sys.platform` fragt:

* **Kein zweites Programm.** Eine App auf iOS darf keinen Prozess
  starten. cloudflared faellt damit weg - der Gast nimmt den Weg in
  Python (wszugang.py), Gastgeber mit Online-Code geht nicht.
* **Finger statt Maus und Tastatur.** Die Touch-Steuerung (touch.py) ist
  an. Auf dem Rechner laesst sie sich mit DUSTFRONT_TOUCH=1 ausprobieren.
* **Eine Tastatur, die man herbeiholen muss.** Auf iOS kommen Zeichen nur,
  solange die Bildschirmtastatur offen ist - und die ist zu, bis jemand in
  ein Textfeld tippt (`tastatur_wuenschen`, `tastatur_abgleichen`).
* **Vollbild.** Es gibt kein Fenster, das man verschieben koennte.
"""

from __future__ import annotations

import os
import sys

import pygame

# Python meldet auf iPhone und iPad seit 3.13 "ios" (PEP 730). Vorher
# gab es dort kein offizielles Python, also auch keinen anderen Namen.
IOS = sys.platform == "ios"


def touch_an() -> bool:
    """Ob die Touch-Steuerung gilt. Auf iOS immer, sonst auf Wunsch."""
    return IOS or os.environ.get("DUSTFRONT_TOUCH", "") not in ("", "0")


def prozesse_erlaubt() -> bool:
    """Darf das Spiel ein anderes Programm starten (cloudflared)?"""
    return not IOS


def nur_vollbild() -> bool:
    return IOS


# ══════════════════════════════════════════════════════════════════
# Bildschirmtastatur
# ══════════════════════════════════════════════════════════════════
#
# Jedes Textfeld, das gerade dran ist, meldet sich einmal je Bild mit
# `tastatur_wuenschen()`. Am Ende des Bildes vergleicht
# `tastatur_abgleichen()` das mit dem Stand und oeffnet oder schliesst die
# Tastatur. GRUND fuer den Umweg: Felder gibt es in drei Modulen, und
# jedes kennt nur sich. Ob irgendeines dran ist, weiss erst das Bild als
# Ganzes - und ein Feld, das verschwindet, ohne sich abzumelden, soll die
# Tastatur nicht offen stehen lassen.

_gewuenscht = False
_offen = False
_feld = None            # wo das Feld steht, in Koordinaten der Spielflaeche
_feld_gesetzt = None
# Rechnet ein Rechteck der Spielflaeche in eines des Fensters um. Setzt,
# wer die Flaeche ins Fenster bringt (core.App, das Hauptmenue).
zu_fenster = None


def tastatur_wuenschen(rect=None) -> None:
    """`rect`: wo das Feld auf der Spielflaeche steht. iOS schiebt das Bild
    dann so weit hoch, dass die Tastatur es nicht verdeckt - sonst tippt
    man beim Anmelden blind in ein Feld unter der Tastatur."""
    global _gewuenscht, _feld
    _gewuenscht = True
    if rect is not None:
        _feld = pygame.Rect(rect)


def tastatur_offen() -> bool:
    return _offen


def tastatur_abgleichen() -> None:
    """Einmal je Bild, nach dem Zeichnen. Tut nur auf Touch-Geraeten etwas:
    auf dem Rechner kommen Zeichen ohnehin, und ein Aufruf von
    start_text_input dort schaltete nur die Eingabehilfen fuer Japanisch
    und Chinesisch um."""
    global _gewuenscht, _offen, _feld, _feld_gesetzt
    soll, _gewuenscht = _gewuenscht, False
    feld, _feld = _feld, None
    if not touch_an():
        return
    try:
        if soll and feld is not None and zu_fenster is not None \
                and feld != _feld_gesetzt:
            pygame.key.set_text_input_rect(zu_fenster(feld))
            _feld_gesetzt = feld
        if soll == _offen:
            return
        if soll:
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()
            _feld_gesetzt = None
        _offen = soll
    except (pygame.error, AttributeError, TypeError):
        pass


def text_umsetzen(ereignisse) -> list:
    """Getippte Zeichen als Tastendruecke, solange die Tastatur offen ist.

    Die Felder lesen Zeichen aus `KEYDOWN.unicode` - so war es immer, und
    auf dem Rechner bleibt es dabei. Die Bildschirmtastatur von iOS
    schickt die Zeichen dagegen als TEXTINPUT, und Einfuegen schickt ein
    ganzes Wort auf einmal ohne einen einzigen Tastendruck. Darum wird
    hier, solange die Tastatur offen ist, jedes Zeichen eines TEXTINPUT
    zu einem eigenen KEYDOWN (mit `key` 0, damit keine Belegung darauf
    reagiert), und ein KEYDOWN mit druckbarem Zeichen faellt weg - sonst
    kaeme jeder Buchstabe doppelt. Ruecktaste und Enter bleiben, wie sie
    sind.
    """
    if not (touch_an() and _offen):
        return list(ereignisse)
    raus = []
    for ev in ereignisse:
        if ev.type == pygame.KEYDOWN and getattr(ev, "unicode", "") \
                and ev.unicode.isprintable() and ev.key not in (
                    pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_BACKSPACE):
            continue
        if ev.type == pygame.TEXTINPUT:
            for zeichen in ev.text:
                raus.append(pygame.event.Event(
                    pygame.KEYDOWN, key=0, mod=0, scancode=0, unicode=zeichen))
            continue
        raus.append(ev)
    return raus
