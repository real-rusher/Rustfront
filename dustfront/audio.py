"""
DUSTFRONT - Ton
===============

Klangdateien liegen in `assets/sfx/<name>/`; WAV, OGG und MP3 werden geladen.
Der Dateiname in diesem Ordner ist frei. Fuer `schuss_repetierer` hat eine
Aufnahme in `assets/sfx/schuss_repetierer/` Vorrang vor der alten flachen
Datei `assets/sfx/schuss_repetierer.wav` und dem allgemeinen Rueckfall
`assets/sfx/schuss.wav`.

Damit ein Dauerfeuer nicht wie ein Maschinengewehr aus einer einzigen Kopie
klingt, gibt es von jedem Platzhalter drei Fassungen, aus denen zufaellig
gewaehlt wird. Bei echten Dateien passiert dasselbe, sobald
`schuss_repetierer_1.wav`, `_2` und so weiter daneben liegen.
"""

from __future__ import annotations

import array
import math
import random
from pathlib import Path

import pygame

from . import config as K

RATE = 44100
ENDUNGEN = K.ASSETS["ton_endungen"]

_PLATZHALTER = {}

# Die Quellen einiger Schussaufnahmen enthalten mehrere Schuesse in Folge.
# Im Spiel kommt der Klang je abgegebenem Geschoss; deshalb wird daraus je
# ein Schuss mit seinem kurzen Nachhall, statt dieselbe Salve zu ueberlagern.
_SCHUSS_SEGMENTE = {
    "u_f09vejvoga-gun-shot-350315.mp3": (
        (0.12, 0.76), (1.38, 2.02), (2.21, 2.85), (3.47, 4.11),
        (4.35, 4.99), (5.60, 6.24), (6.45, 7.09), (7.70, 8.34),
    ),
    "freesound_community-clean-machine-gun-burst-98224.mp3": tuple(
        (max(0.0, start - 0.012), start + 0.105)
        for start in (0.02, 0.11, 0.20, 0.29, 0.38, 0.47, 0.56, 0.65,
                      0.74, 0.83, 0.92, 1.01, 1.10, 1.19, 1.28, 1.36)
    ),
}

# Zeitfenster nach dem Abhoeren der Wellenform (Sekunden). Die laengeren
# Originaldateien haben davor oder danach Stille bzw. bei Rauch einen langen
# Hintergrundton, der nicht bei jedem Wurf wiederholt werden soll.
_ZUSCHNITTE = {
    "ribhavagrawal-woosh-230554.mp3": (0.38, 0.62),
    "tmp_7901-951678082.mp3": (0.32, 0.94),
    "grenade-explosion.mp3": (0.38, 1.82),
    "freesound_community-glass-shatter-3-100155.mp3": (0.02, 0.34),
    "gregorquendel-designed-fire-winds-swoosh-04-116788.mp3": (0.02, 1.45),
    "smoke-grenade-sound-effect.mp3": (0.48, 1.18),
    "freesound_community-069321_light-machine-gun-m249-39814.mp3": (0.04, 0.18),
    "freesound_community-sniper-rifle-firing-shot-1-39789.mp3": (0.03, 1.48),
    "yodguard-spear_thrust-6-382403.mp3": (0.0, 0.32),
    "universfield-combat-impact-352458.mp3": (0.0, 0.36),
    "universfield-hammer-steel-impact-454390.mp3": (0.0, 0.32),
    "fighting.mp3": (0.20, 2.42),
    "gta-v-wasted-death-sound.mp3": (0.0, 4.25),
}


def _ausschnitt(sound, start: float, ende: float):
    """Schneidet PCM-Material im bereits initialisierten Mischerformat."""
    try:
        roh = sound.get_raw()
        mixer = pygame.mixer.get_init()
    except (pygame.error, AttributeError):
        return sound
    if not roh or mixer is None:
        return sound
    rate, form, kanaele = mixer
    byte_pro_wert = abs(form) // 8
    rahmen = max(1, kanaele * byte_pro_wert)
    von = max(0, int(start * rate)) * rahmen
    bis = min(len(roh), int(ende * rate) * rahmen)
    von -= von % rahmen
    bis -= bis % rahmen
    if bis <= von:
        return sound
    try:
        return pygame.mixer.Sound(buffer=roh[von:bis])
    except pygame.error:
        return sound


def platzhalter_klang(name):
    """Registriert einen Erzeuger fuer einen Klang, den es noch nicht gibt."""
    def deko(fn):
        _PLATZHALTER[name] = fn
        return fn
    return deko


# ══════════════════════════════════════════════════════════════════
# Kleine Klangwerkstatt
# ══════════════════════════════════════════════════════════════════

def _rauschen(dur, vol, lp0, lp1, decay=2.4, seed=0, hp=False):
    """Gefiltertes Rauschen. Der Knall eines Schusses ist im Kern genau das."""
    n = max(1, int(RATE * dur))
    r = random.Random(seed)
    out = [0.0] * n
    y = prev = 0.0
    for i in range(n):
        p = i / n
        k = 1 - math.exp(-2 * math.pi * (lp0 + (lp1 - lp0) * p) / RATE)
        y += k * (r.uniform(-1.0, 1.0) - y)
        s = (y - prev) if hp else y
        prev = y
        out[i] = s * (1 - p) ** decay * vol
    return out


def _schlag(f0, f1, dur, vol, decay=3.0):
    """Tiefer Stoss mit fallender Tonhoehe, gibt dem Schuss Koerper."""
    n = max(1, int(RATE * dur))
    out = [0.0] * n
    ph = 0.0
    tp = 2 * math.pi
    for i in range(n):
        p = i / n
        ph += tp * (f0 * (1 - p) + f1 * p) / RATE
        out[i] = math.sin(ph) * (1 - p) ** decay * vol
    return out


def _mischen(*teile):
    n = max(len(t) for t in teile)
    out = [0.0] * n
    for t in teile:
        for i, s in enumerate(t):
            out[i] += s
    return out


def _zu_sound(proben, gain=1.0):
    init = pygame.mixer.get_init()
    if not init:
        return None
    kanaele = init[2]
    n = len(proben)
    aus = min(n // 3, int(0.008 * RATE))          # kurzer Ausklang, sonst knackt es
    for i in range(aus):
        proben[n - 1 - i] *= i / aus
    spitze = max(1e-6, max(abs(s) for s in proben))
    norm = min(1.0, 0.94 / spitze) if spitze > 0.94 else 1.0
    buf = array.array("h")
    for s in proben:
        v = int(max(-1.0, min(1.0, s * norm * gain)) * 31000)
        buf.append(v)
        if kanaele > 1:
            buf.append(v)
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except pygame.error:
        return None


# ══════════════════════════════════════════════════════════════════
# Platzhalter
# ══════════════════════════════════════════════════════════════════

@platzhalter_klang("schuss_repetierer")
def _schuss_repetierer(seed=0):
    """Trockener, harter Knall mit kurzem Metallnachhall."""
    return _mischen(
        _rauschen(0.16, 0.95, 7000, 900, 3.2, seed + 1),
        _rauschen(0.05, 0.55, 12000, 6000, 2.0, seed + 2, hp=True),
        _schlag(180, 62, 0.13, 0.65, 3.4),
        [0.0] * int(RATE * 0.012) + _rauschen(0.22, 0.16, 2600, 700, 2.6, seed + 3),
    )


@platzhalter_klang("schuss_schrot")
def _schuss_schrot(seed=0):
    """Tiefer, breiter Schlag, laenger im Ausklang."""
    return _mischen(
        _rauschen(0.34, 1.0, 4200, 320, 2.1, seed + 11),
        _rauschen(0.06, 0.45, 9000, 3000, 1.8, seed + 12, hp=True),
        _schlag(120, 44, 0.30, 0.85, 2.6),
        [0.0] * int(RATE * 0.02) + _rauschen(0.40, 0.22, 1400, 380, 2.2, seed + 13),
    )


@platzhalter_klang("schuss_sturm")
def _schuss_sturm(seed=0):
    """Kuerzer und haerter als der Repetierer, fuer Dauerfeuer gedacht."""
    return _mischen(
        _rauschen(0.11, 0.9, 8000, 1400, 3.6, seed + 21),
        _rauschen(0.04, 0.5, 13000, 7000, 2.2, seed + 22, hp=True),
        _schlag(210, 84, 0.09, 0.55, 3.8),
    )


@platzhalter_klang("schuss_scharf")
def _schuss_scharf(seed=0):
    """Ein einzelner, sehr lauter Knall mit langem Nachhall."""
    return _mischen(
        _rauschen(0.55, 1.0, 6500, 240, 1.8, seed + 31),
        _rauschen(0.07, 0.6, 11000, 4000, 1.6, seed + 32, hp=True),
        _schlag(150, 46, 0.34, 0.9, 2.2),
        [0.0] * int(RATE * 0.03) + _rauschen(0.7, 0.3, 1800, 300, 1.9, seed + 33),
    )


@platzhalter_klang("granate")
def _granate(seed=0):
    """Tiefer Schlag, Druckwelle, langes Grollen."""
    return _mischen(
        _schlag(90, 28, 0.9, 1.0, 1.8),
        _rauschen(0.8, 0.9, 5000, 160, 1.5, seed + 41),
        [0.0] * int(RATE * 0.04) + _rauschen(1.2, 0.45, 900, 120, 1.4, seed + 42),
    )


@platzhalter_klang("nahkampf")
def _nahkampf(seed=0):
    """Metall auf Metall, kurz und scharf."""
    return _mischen(
        _rauschen(0.10, 0.7, 9000, 2200, 3.4, seed + 51, hp=True),
        _schlag(620, 280, 0.12, 0.4, 3.0),
        _schlag(1400, 900, 0.09, 0.25, 4.0),
    )


@platzhalter_klang("sturz")
def _sturz(seed=0):
    """Aufsetzen nach einem Fall: dumpfer Schlag und aufwirbelnder Staub.

    Tiefer als der Nahkampf und ohne Metall - man soll ihn nicht mit einem
    Treffer verwechseln, sondern mit Stiefeln auf Blech.
    """
    return _mischen(
        _schlag(150, 58, 0.26, 0.85, 2.2),
        _rauschen(0.30, 0.5, 2600, 420, 2.0, seed + 81),
        [0.0] * int(RATE * 0.02) + _rauschen(0.22, 0.28, 800, 200, 1.8, seed + 82),
    )


@platzhalter_klang("wurf")
def _wurf(seed=0):
    return _rauschen(0.22, 0.4, 1800, 5200, 1.6, seed + 61, hp=True)


@platzhalter_klang("medkit")
def _medkit(seed=0):
    return _mischen(_schlag(520, 760, 0.18, 0.35, 2.0),
                    _rauschen(0.12, 0.2, 3000, 900, 2.4, seed + 71))


@platzhalter_klang("aufheben")
def _aufheben(seed=0):
    return _mischen(_schlag(880, 1180, 0.12, 0.3, 2.4),
                    _schlag(1320, 1760, 0.09, 0.18, 3.0))


@platzhalter_klang("menue")
def _menue(seed=0):
    return _schlag(660, 720, 0.05, 0.22, 3.0)


@platzhalter_klang("menue_ok")
def _menue_ok(seed=0):
    return _mischen(_schlag(430, 640, 0.10, 0.28, 2.6),
                    _schlag(880, 1180, 0.08, 0.14, 3.2))


@platzhalter_klang("schuss")
def _schuss(seed=0):
    return _schuss_repetierer(seed)


@platzhalter_klang("molotov")
def _molotov(seed=0):
    """Glas zerbricht, dann faengt etwas Feuer.

    Kein Knall: eine Flasche explodiert nicht. Was man hoert, ist ein
    kurzes helles Splittern und danach ein Auflodern - breites Rauschen,
    das ansteigt statt abzufallen. Genau daran erkennt man im Gefecht,
    dass da kein Sprengsatz kam, sondern ein Ort weggenommen wurde.
    """
    glas = _rauschen(0.09, 0.75, 9000, 5200, 2.2, seed + 1, hp=True)
    lodern = _rauschen(0.55, 0.50, 1400, 3000, 0.6, seed + 2)
    # Das Auflodern faengt leise an und wird lauter - umgekehrt zu allem
    # anderen hier.
    n = len(lodern)
    for i in range(n):
        lodern[i] *= min(1.0, (i / n) * 3.0) * (1.0 - i / n) ** 0.8
    return _mischen(glas, [0.0] * int(RATE * 0.03) + lodern)


@platzhalter_klang("schuss_lmg")
def _schuss_lmg(seed=0):
    """Ein MG: tiefer und breiter als das Sturmgewehr, mit Nachhall.

    Der Unterschied zum Sturmgewehr ist nicht die Lautstaerke, sondern
    das Gewicht darunter. Ein tiefer Schlag traegt den Knall, und ein
    langer dunkler Nachhall haengt daran - so klingt etwas, das auf einem
    Zweibein steht und nicht in der Hand liegt.
    """
    return _mischen(
        _rauschen(0.14, 0.95, 5200, 700, 3.0, seed + 1),
        _rauschen(0.06, 0.45, 11000, 5000, 2.2, seed + 2, hp=True),
        _schlag(120, 46, 0.16, 0.85, 3.0),
        [0.0] * int(RATE * 0.02) + _rauschen(0.30, 0.22, 1800, 420, 2.4, seed + 3),
    )


@platzhalter_klang("rakete")
def _rakete(seed=0):
    """Der Abschuss: ein Zischen, das anschwillt, kein Knall.

    Eine Rakete wird nicht abgefeuert, sie faehrt los. Darum breites
    Rauschen mit einem Anstieg statt eines Abfalls, ein tiefer Schub
    darunter und ein Nachzischen. Wer das hoert, hat noch eine Sekunde.
    """
    zischen = _rauschen(0.45, 0.85, 900, 4200, 0.5, seed + 1)
    n = len(zischen)
    for i in range(n):
        p = i / n
        zischen[i] *= min(1.0, p * 8.0) * (1.0 - p) ** 0.7
    return _mischen(zischen, _schlag(140, 70, 0.22, 0.70, 2.2))


@platzhalter_klang("erfasst")
def _erfasst(seed=0):
    """Zwei kurze hohe Toene: die Erfassung steht.

    Kurz und unverwechselbar. Er sagt dem Schuetzen, dass er loslassen
    kann - und er ist so gebaut, dass man ihn auch im Gefecht hoert,
    ohne dass er wie ein Treffer klingt.
    """
    return _mischen(_schlag(1560, 1560, 0.05, 0.35, 2.0),
                    [0.0] * int(RATE * 0.07)
                    + _schlag(2080, 2080, 0.06, 0.32, 2.0))


@platzhalter_klang("blend")
def _blend(seed=0):
    """Der Knall einer Blendgranate: hart, hell, ohne Tiefe.

    Anders als eine Sprenggranate hat sie **keinen** Koerper. Eine
    Sprengladung drueckt, eine Blendladung knallt - also hohes Rauschen
    mit einem sehr kurzen Anstieg und einem Metallnachhall, und kein
    einziger tiefer Schlag darunter. Genau daran hoert man im Gefecht,
    was gerade geflogen kam, bevor man es sieht.
    """
    return _mischen(
        _rauschen(0.12, 1.0, 14000, 9000, 2.0, seed + 1, hp=True),
        _rauschen(0.30, 0.45, 8000, 4000, 2.6, seed + 2, hp=True),
        _schlag(2400, 1800, 0.08, 0.35, 2.2),
    )


@platzhalter_klang("blend_pfeifen")
def _blend_pfeifen(seed=0):
    """Das Pfeifen danach im Ohr. Lang, schmal, langsam verklingend.

    Ein reiner hoher Ton, der zwei Sekunden braucht. Er ist der Grund,
    warum eine Blendgranate wehtut: das Bild ist nach einer Sekunde
    wieder da, das Pfeifen nicht, und solange es laeuft, hoert man keine
    Schritte.
    """
    n = int(RATE * K.BLENDEN["ton_dauer"])
    out = [0.0] * n
    ph = ph2 = 0.0
    tp = 2 * math.pi
    for i in range(n):
        p = i / n
        # Zwei dicht benachbarte Toene: das schwebt leicht und klingt
        # nach Ohr und nicht nach Signalgeber.
        ph += tp * 3150 / RATE
        ph2 += tp * 3184 / RATE
        huelle = min(1.0, p * 40.0) * (1.0 - p) ** 1.6
        out[i] = (math.sin(ph) * 0.6 + math.sin(ph2) * 0.4) * huelle * 0.5
    return out


@platzhalter_klang("speien")
def _speien(seed=0):
    """Der Spuck des Speiers: ein nasses Ausstossen, kurz und tief.

    Gefiltertes Rauschen mit einem Tiefpass, der aufgeht statt zuzu-
    gehen - das klingt nach etwas, das herauskommt, und nicht nach
    etwas, das anschlaegt. Deutlich dumpfer als jeder Schuss, damit man
    im Getuemmel hoert, dass es kein Mitspieler war.
    """
    return _mischen(
        _rauschen(0.16, 0.42, 380, 1500, 2.6, seed),
        _schlag(180, 90, 0.10, 0.28, 4.0),
    )


@platzhalter_klang("boss_ansage")
def _boss_ansage(seed=0):
    """Ein Boss kuendigt an, was er gleich tut.

    Zwei tiefe Toene, der zweite hoeher - ein Hornsignal, kein Knall.
    Es muss sich von allem unterscheiden, was sonst im Bild passiert,
    denn es ist die einzige Warnung, die es gibt; wer es fuer einen
    Schuss haelt, weicht nicht aus.
    """
    n = int(RATE * 0.55)
    out = [0.0] * n
    ph = ph2 = 0.0
    tp = 2 * math.pi
    for i in range(n):
        p = i / n
        # Der Ton steigt in der zweiten Haelfte - das liest sich als
        # "es kommt", waehrend ein fallender Ton nach "vorbei" klingt.
        f = 110.0 + 46.0 * max(0.0, (p - 0.45) / 0.55)
        ph += tp * f / RATE
        ph2 += tp * (f * 1.5) / RATE
        huelle = min(1.0, p * 26.0) * (1.0 - p) ** 1.1
        out[i] = (math.sin(ph) * 0.62 + math.sin(ph2) * 0.22) * huelle * 0.8
    return out


@platzhalter_klang("dash")
def _dash(seed=0):
    """Der Dash: ein kurzes Luftreissen, hell und trocken.

    Rauschen mit einem Tiefpass, der schnell aufgeht - das klingt nach
    Bewegung und nicht nach Aufprall. Kurz, weil man ihn oft hoert, und
    leiser als jeder Schuss, weil er keine Gefahr ankuendigt.
    """
    return _mischen(
        _rauschen(0.14, 0.34, 900, 4200, 3.4, seed, hp=True),
        _rauschen(0.10, 0.18, 300, 900, 4.0, seed + 1),
    )


@platzhalter_klang("ruf")
def _ruf(seed=0):
    """Ein Gefallener ruft. Zwei kurze Toene, der zweite tiefer.

    Es muss sich von allem anderen unterscheiden, was im Gefecht
    klingt - Schuesse, Explosionen, Gegner. Ein Hornsignal nach unten
    liest sich als "hier!", und es ist leise genug, dass es nicht nervt,
    wenn jemand alle anderthalb Sekunden ruft.
    """
    n = int(RATE * 0.42)
    out = [0.0] * n
    ph = 0.0
    tp = 2 * math.pi
    for i in range(n):
        p = i / n
        f = 740.0 if p < 0.45 else 560.0
        ph += tp * f / RATE
        teil = p / 0.45 if p < 0.45 else (p - 0.5) / 0.5
        huelle = 0.0 if 0.45 <= p < 0.5 else min(1.0, teil * 18.0) * (1.0 - teil) ** 1.4
        out[i] = (math.sin(ph) * 0.7 + math.sin(ph * 2.0) * 0.18) * huelle * 0.55
    return out


@platzhalter_klang("herzschlag")
def _herzschlag(seed=0):
    """Zwei Schlaege, der zweite leiser und dichter dahinter.

    Ein Herz macht "lub-dub", nicht "bum". Der Unterschied klingt nach
    einem Koerper statt nach einer Trommel, und genau darum geht es: es
    soll der eigene Brustkorb sein, den man hoert, nicht ein Effekt.

    Sehr tief angesetzt (58 Hz auf 34 Hz), weil ein Herzschlag mehr
    gefuehlt als gehoert wird. Auf kleinen Lautsprechern bleibt davon
    ein dumpfes Klopfen uebrig - auch richtig.
    """
    erster = _schlag(58, 34, 0.14, 0.95, 2.6)
    luecke = [0.0] * int(RATE * 0.17)
    zweiter = _schlag(52, 30, 0.12, 0.62, 3.0)
    # Ein Hauch Rauschen darunter, damit es Koerper hat und nicht wie
    # ein reiner Sinuston klingt.
    koerper = _rauschen(0.30, 0.10, 220, 90, 3.4, seed + 5)
    return _mischen(erster + luecke + zweiter, koerper)


@platzhalter_klang("reload")
def _nachladen(seed=0):
    """Zwei kurze Mechanik-Klicks mit einem kleinen metallischen Nachklang."""
    klick = _rauschen(0.045, 0.6, 7200, 1800, 7.0, seed + 1, hp=True)
    return _mischen(klick, [0.0] * int(RATE * 0.14) + klick,
                    [0.0] * int(RATE * 0.20)
                    + _schlag(720, 380, 0.12, 0.18, 8.0))


@platzhalter_klang("downed_not_dead")
def _gefallen(seed=0):
    """Ein dumpfer Treffer und kurzer Atemstoss fuer den Fall zu Boden."""
    return _mischen(_schlag(105, 48, 0.18, 0.72, 4.0),
                    _rauschen(0.26, 0.22, 1200, 250, 3.0, seed + 2))


@platzhalter_klang("smoke_grenade")
def _rauchgranate(seed=0):
    """Eine kleine Huelse, die aufsetzt und leise zu zischen beginnt."""
    zischen = _rauschen(0.50, 0.30, 420, 1500, 1.8, seed + 1)
    return _mischen(_schlag(440, 190, 0.12, 0.48, 4.8),
                    [0.0] * int(RATE * 0.10) + zischen)


@platzhalter_klang("rundenstart")
def _rundenstart(seed=0):
    """Ein knapper Doppelschlag, der den neuen Gefechtsbeginn markiert."""
    return _mischen(_schlag(220, 110, 0.10, 0.48, 3.0),
                    [0.0] * int(RATE * 0.12)
                    + _schlag(330, 165, 0.12, 0.40, 3.0))


@platzhalter_klang("won_match")
def _sieg(seed=0):
    """Ein kurzer aufsteigender Dreiklang fuer einen gewonnenen Durchgang."""
    return _mischen(_schlag(523, 523, 0.12, 0.32, 2.0),
                    [0.0] * int(RATE * 0.10)
                    + _schlag(659, 659, 0.14, 0.30, 2.0),
                    [0.0] * int(RATE * 0.20)
                    + _schlag(784, 784, 0.20, 0.34, 2.0))


@platzhalter_klang("lost_match")
def _niederlage(seed=0):
    """Ein kurzer fallender Zweiklang fuer eine verlorene Runde."""
    return _mischen(_schlag(330, 330, 0.18, 0.35, 2.5),
                    [0.0] * int(RATE * 0.16)
                    + _schlag(220, 220, 0.24, 0.32, 2.5))


# ══════════════════════════════════════════════════════════════════
# Dumpf machen
# ══════════════════════════════════════════════════════════════════

def dumpf_machen(sound, grenze: float = 620.0, gain: float = 0.72):
    """Eine dumpfe Fassung eines Klangs. Echt gefiltert, nicht leiser.

    "Dumpf" ist keine Lautstaerke, sondern ein Frequenzgang: die Hoehen
    fehlen, der Rest bleibt. Nur leiser zu drehen klingt nach leiser, und
    das ist etwas anderes als "die Welt ist weit weg" - genau dieser
    Unterschied ist der ganze Effekt bei wenig Leben.

    Gerechnet wird mit einem Tiefpass erster Ordnung ueber die rohen
    Proben, so wie `_rauschen` es beim Bauen schon tut. Das kostet einen
    Python-Durchlauf je Klang; darum wird jede Fassung genau einmal
    gebaut und dann behalten. Ein Klang von einer Zehntelsekunde sind
    keine zehntausend Proben - das faellt einmal an und nie wieder.

    Ohne numpy, wie alles hier. `array` reicht.
    """
    try:
        roh = sound.get_raw()
    except (pygame.error, AttributeError):
        return sound
    proben = array.array("h")
    try:
        proben.frombytes(roh)
    except ValueError:
        return sound
    init = pygame.mixer.get_init()
    kanaele = init[2] if init else 1
    rate = init[0] if init else RATE
    k = 1.0 - math.exp(-2.0 * math.pi * grenze / rate)
    # Je Kanal ein eigener Durchlauf, mit Schrittweite statt Modulo: die
    # beiden Kanaele duerfen sich nicht mischen, und ein `i % kanaele` in
    # der innersten Schleife kostet bei vierzigtausend Proben spuerbar.
    n = len(proben)
    for c in range(kanaele):
        y = 0.0
        for i in range(c, n, kanaele):
            y += k * (proben[i] - y)
            v = int(y * gain)
            proben[i] = -32768 if v < -32768 else (32767 if v > 32767 else v)
    try:
        return pygame.mixer.Sound(buffer=proben.tobytes())
    except pygame.error:
        return sound


# ══════════════════════════════════════════════════════════════════
# Registratur
# ══════════════════════════════════════════════════════════════════

class Klaenge:
    FASSUNGEN = K.ASSETS["platzhalter_fassungen"]

    def __init__(self, ordner: Path | None = None) -> None:
        self.ordner = (ordner / K.ASSETS["sfx"]) if ordner is not None else None
        self.ok = False
        self.aus_datei: set[str] = set()
        self.fehler: list[str] = []
        self._cache: dict[str, list] = {}
        self._dumpf_cache: dict[str, list] = {}
        self._dumpf_offen: list[str] = []
        self.rnd = random.Random()
        self.gesamt = K.AUDIO["gesamt"]
        self.effekte = 1.0
        # Wie dumpf die Welt gerade klingt, 0 bis 1. Gesetzt von der
        # Spielszene aus `Befinden.dumpf`; hier wird nur danach gehandelt.
        self.daempfung = 0.0
        try:
            pygame.mixer.init(frequency=RATE, size=-16, channels=2, buffer=512)
            self.ok = pygame.mixer.get_init() is not None
        except pygame.error:
            self.ok = False
        if self.ok:
            try:
                pygame.mixer.set_num_channels(24)
            except pygame.error:
                pass

    # ---- Suchen und Bauen -------------------------------------------
    def _dateien(self, name: str) -> list[pygame.mixer.Sound]:
        """Alle passenden Dateien: name.wav, name_1.wav, name_2.ogg, ..."""
        if self.ordner is None or not self.ordner.is_dir():
            return []
        gefunden = []
        # Aufnahmen liegen kuenftig je Klang in einem eigenen Ordner. Der
        # Dateiname ist dabei frei; sortiert bleibt die Auswahl reproduzierbar.
        ordnernamen = [K.KLANG_ORDNER.get(name, name)]
        if name not in ordnernamen:
            ordnernamen.append(name)
        wurzel = name.split("_")[0]
        if wurzel not in ordnernamen:
            ordnernamen.append(wurzel)
        klang_ordner = [self.ordner / n for n in ordnernamen]
        for quelle_ordner in klang_ordner:
            if not quelle_ordner.is_dir():
                continue
            for pfad in sorted(quelle_ordner.iterdir()):
                if pfad.is_file() and pfad.suffix.lower() in ENDUNGEN:
                    try:
                        quelle = pygame.mixer.Sound(str(pfad))
                        segmente = _SCHUSS_SEGMENTE.get(pfad.name)
                        if segmente:
                            gefunden.extend(_ausschnitt(quelle, start, ende)
                                            for start, ende in segmente)
                        elif pfad.name in _ZUSCHNITTE:
                            gefunden.append(_ausschnitt(
                                quelle, *_ZUSCHNITTE[pfad.name]))
                        else:
                            gefunden.append(quelle)
                        self.aus_datei.add(name)
                    except pygame.error as grund:
                        self.fehler.append("%s: %s" % (pfad.name, grund))
            if gefunden:
                return gefunden
        nummern = range(1, K.ASSETS["fassungen"] + 1)
        for kandidat in [name] + ["%s_%d" % (name, i) for i in nummern]:
            for endung in ENDUNGEN:
                pfad = self.ordner / (kandidat + endung)
                if pfad.is_file():
                    try:
                        gefunden.append(pygame.mixer.Sound(str(pfad)))
                        self.aus_datei.add(name)
                    except pygame.error as grund:
                        self.fehler.append("%s: %s" % (pfad.name, grund))
        return gefunden

    def _bauen(self, name: str) -> list:
        # 1. Dateien unter genau diesem Namen
        fassungen = self._dateien(name)
        if fassungen:
            return fassungen
        # 2. Dateien unter dem allgemeinen Namen vor dem Unterstrich
        wurzel = name.split("_")[0]
        if wurzel != name:
            fassungen = self._dateien(wurzel)
            if fassungen:
                return fassungen
        # 3. Platzhalter aus dem Code
        erzeuger = _PLATZHALTER.get(name) or _PLATZHALTER.get(wurzel)
        if erzeuger is None:
            return []
        fassungen = []
        for i in range(self.FASSUNGEN):
            s = _zu_sound(erzeuger(i * 37))
            if s is not None:
                fassungen.append(s)
        return fassungen

    def klang(self, name: str) -> list:
        if not self.ok:
            return []
        hit = self._cache.get(name)
        if hit is None:
            hit = self._bauen(name)
            self._cache[name] = hit
        return hit

    def dumpf(self, name: str) -> list | None:
        """Dieselben Fassungen, nur gefiltert - **wenn sie schon da sind**.

        Gebaut wird nicht hier. Ein Filterlauf kostet gemessen etwa 23
        Millisekunden je Klang, und die mitten im Gefecht zu nehmen waeren
        drei ausgelassene Bilder an genau der Stelle, an der es eng wird.
        Statt dessen wird vorgemerkt und `dumpf_nachziehen` baut je Aufruf
        einen Namen - bis dahin klingt der Klang eben nur leiser.
        """
        hit = self._dumpf_cache.get(name)
        if hit is None and name not in self._dumpf_offen:
            self._dumpf_offen.append(name)
        return hit

    def dumpf_nachziehen(self) -> bool:
        """Einen vorgemerkten Klang filtern. True, wenn etwas getan wurde."""
        while self._dumpf_offen:
            name = self._dumpf_offen.pop(0)
            if name in self._dumpf_cache:
                continue
            # Nur **eine** dumpfe Fassung je Name, auch wenn es drei
            # klare gibt. Abwechslung hoert man an einem Klang, dem die
            # Hoehen fehlen, ohnehin kaum - und das Filtern kostet je
            # Fassung gemessen gut zwanzig Millisekunden. Drei davon in
            # einem Bild waeren ein sichtbarer Haenger.
            fassungen = self.klang(name)
            self._dumpf_cache[name] = ([dumpf_machen(fassungen[0])]
                                       if fassungen else [])
            return True
        return False

    def dumpf_vorbereiten(self) -> None:
        """Alles vormerken, was in dieser Runde schon zu hoeren war.

        Bewusst nur das und nicht die ganze Namensliste: einen Klang
        anzulegen, den es noch gar nicht gibt, kostet ein Vielfaches des
        Filterns - gemessen 521 Millisekunden fuer alle gegen 55 fuer das
        Filtern aller. Was noch nie gespielt wurde, wird auch gleich
        nicht gebraucht; und wenn doch, holt `dumpf` es sich nach.

        Aufgerufen, sobald es einem zum ersten Mal schlecht geht. Gebaut
        wird trotzdem einer nach dem anderen.
        """
        for name in self._cache:
            if name not in K.NIE_DUMPF and name not in self._dumpf_cache:
                if name not in self._dumpf_offen:
                    self._dumpf_offen.append(name)

    # ---- Abspielen ---------------------------------------------------
    def lautstaerke_setzen(self, gesamt: float, effekte: float) -> None:
        self.gesamt = max(0.0, min(1.0, gesamt))
        self.effekte = max(0.0, min(1.0, effekte))

    def daempfung_setzen(self, wert: float) -> None:
        vorher = self.daempfung
        self.daempfung = max(0.0, min(1.0, wert))
        if self.daempfung > 0.0 and vorher <= 0.0:
            self.dumpf_vorbereiten()

    def spielen(self, name: str, lautstaerke: float = 1.0) -> None:
        """Einen Klang abspielen - klar, dumpf, oder zwischen beidem.

        Der Uebergang ist ein echtes Ueberblenden und kein Umschalten:
        bei halber Daempfung laufen beide Fassungen zugleich, jede mit
        ihrem Anteil. Ein hartes Umschalten mitten im Gefecht hoert man
        als Knacks, und ein Knacks an der Stelle, an der es einem
        schlecht geht, ist genau das Gegenteil von dem, was der Effekt
        soll.
        """
        fassungen = self.klang(name)
        if not fassungen:
            return
        laut = max(0.0, min(1.0, lautstaerke * self.gesamt * self.effekte))
        if laut <= 0.0:
            return
        i = self.rnd.randrange(len(fassungen))
        d = 0.0 if name in K.NIE_DUMPF else self.daempfung
        try:
            if d < 0.995:
                s = fassungen[i]
                s.set_volume(laut * (1.0 - d))
                s.play()
            if d > 0.005:
                gefiltert = self.dumpf(name)
                if gefiltert is None:
                    # Noch nicht gefiltert: dann eben nur leiser. Das ist
                    # schlechter, aber es ist da, und es ist nie ein Loch.
                    if d >= 0.995:
                        s = fassungen[i]
                        s.set_volume(laut * 0.45)
                        s.play()
                elif gefiltert:
                    g = gefiltert[i % len(gefiltert)]
                    g.set_volume(laut * d)
                    g.play()
        except pygame.error:
            pass

    def ton_spielen(self, ton, lautstaerke: float = 1.0) -> None:
        """Einen fertigen Ton abspielen, der nicht aus der Tabelle kommt.

        Fuer die Spielerkosmetik: der Ton eines Mitspielers hat keinen
        Namen hier und keine dumpfe Fassung. Er bekommt dieselbe
        Lautstaerke wie alles andere, und wenn die Welt gerade dumpf
        klingt, ist er eben leiser.
        """
        if not self.ok or ton is None:
            return
        laut = max(0.0, min(1.0, lautstaerke * self.gesamt * self.effekte))
        laut *= 1.0 - 0.55 * self.daempfung
        if laut <= 0.0:
            return
        try:
            ton.set_volume(laut)
            ton.play()
        except pygame.error:
            pass

    def stille(self) -> None:
        if self.ok:
            try:
                pygame.mixer.stop()
            except pygame.error:
                pass
