"""
DUSTFRONT - Autoball (seit 0.34.17)
===================================

Rocket League von oben. Gemeldet: "man soll mit den Autos quasi Rocket
League in 2D spielen koennen ... auch wenn zwei Autos an den extrem grossen
Ball von zwei verschiedenen Seiten ranfahren, soll er nicht irgendwie
durch die durchgehen".

Jeder sitzt in seinem eigenen Buggy (fahrzeug.Buggy), zwei Mannschaften,
ein grosser Ball, zwei Tore. Gefahren wird wie sonst auch, dazu kommt der
Boost (linke Maustaste). Ein Tor zaehlt, wenn der Ball ganz im Tor liegt.

**Der Ball und die Stoesse (Spielfeld).** Das ist der Teil, der nicht
schiefgehen darf. Drei Dinge halten ihn dicht:

1. Der Ball wird in Teilschritten bewegt, keiner laenger als
   K.AUTOBALL["teilschritt"] (4 Pixel). Ein Wagen ist 30 Pixel breit, der
   Ball hat 44 Pixel Radius: damit sein Mittelpunkt auf die andere Seite
   eines Wagens kaeme, muesste er in einem Teilschritt ueber 59 Pixel tief
   eindringen. Er dringt hoechstens 4 ein, plus die 4 Pixel, die ein
   Wagen in einem Schritt hoechstens faehrt. Durchtunneln geht damit
   schon geometrisch nicht.
2. Je Teilschritt werden alle Beruehrungen mehrmals hintereinander
   geloest (Gauss-Seidel): Ball an Wand, Ball an jedem Wagen, Wagen an
   Wagen. Die Verschiebung teilt sich nach Masse auf, die Wand gibt nie
   nach. Wird der Ball zwischen zwei Wagen gequetscht, schieben die
   Durchgaenge darum die **Wagen** auseinander - der Ball bleibt, wo
   Platz ist.
3. Bleibt danach noch Ueberlappung (der Ball klemmt zwischen Wagen und
   Wand), weicht in einer letzten Stufe der Wagen ganz zurueck - und
   kann er das nicht, an die Stelle vom Anfang des Schrittes, an der er
   den Ball noch nicht beruehrte. Der Ball gibt hier nie nach: er hat
   nach den Waenden keinen Platz.

Stoesse sind echte Impulse mit Drehung: wer den Ball mit der Ecke trifft,
schiebt ihn schraeg und dreht sich dabei selbst ein wenig.

**Wer rechnet.** Wie alles der Gastgeber. Der Gast bekommt den Ball mit
der Weltmeldung und zeichnet ihn nur; das Rollen (das Muster dreht sich
mit) rechnet er aus der gemeldeten Bewegung selbst, es ist nur Bild.

**Im Gefecht** steht der Teil fuer die Spielart (AutoballTeil): Wagen
fuer jeden, Anstoss, Tore, Verlaengerung, Ballkamera, Anzeige.
"""

from __future__ import annotations

import math

import pygame

from . import config as K
from .entities import Wesen, wolke
from .font import SCHRIFT


# ══════════════════════════════════════════════════════════════════
# Der Ball
# ══════════════════════════════════════════════════════════════════

# Die Flecken eines Fussballs: die zwoelf Ecken eines Ikosaeders. Auf
# einer Kugel gleichmaessig verteilt, so sieht man das Rollen in jede
# Richtung gleich gut.
_PHI = (1.0 + math.sqrt(5.0)) / 2.0
_FLECKEN = []
for _a in (-1.0, 1.0):
    for _b in (-_PHI, _PHI):
        for _p in ((0.0, _a, _b), (_a, _b, 0.0), (_b, 0.0, _a)):
            _l = math.sqrt(sum(c * c for c in _p))
            _FLECKEN.append(tuple(c / _l for c in _p))


def _drehen(m, achse, winkel):
    """Die Lage m (3x3, zeilenweise) um `achse` (Einheitsvektor) drehen."""
    x, y, z = achse
    c, s = math.cos(winkel), math.sin(winkel)
    t = 1.0 - c
    r = ((t * x * x + c, t * x * y - s * z, t * x * z + s * y),
         (t * x * y + s * z, t * y * y + c, t * y * z - s * x),
         (t * x * z - s * y, t * y * z + s * x, t * z * z + c))
    return [[sum(r[i][k] * m[k][j] for k in range(3)) for j in range(3)]
            for i in range(3)]


class Ball(Wesen):
    """Der Ball. Rechnet sich nicht selbst - das tut das Spielfeld, das
    ihn zusammen mit den Wagen loesen muss."""
    fraktion = "neutral"
    trefferbar = False          # Kugeln gehen hindurch, nichts zielt auf ihn
    schiebt = False
    faellt = False
    schatten = True
    # Er ist hoeher als jeder Wagen: zuletzt gezeichnet, also obenauf.
    obenauf = True

    def __init__(self, pos, ebene: int = 0, nur_bild: bool = False) -> None:
        super().__init__(pos, ebene)
        self.radius = K.AUTOBALL["ball_radius"]
        self.geschw = pygame.Vector2(0, 0)
        self.nur_bild = nur_bild
        # Wer zuletzt dran war: (Spielernummer, Team). Fuer das Tor.
        self.zuletzt = (-1, -1)
        self.vorletzt = (-1, -1)
        self._lage = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        self._roll_von = pygame.Vector2(pos)
        self._bild = None
        self._glanz = None

    def schritt(self, dt: float) -> None:
        # Nur `vorher` nachziehen (Wesen.schritt): bewegt wird er im
        # Spielfeld, nach den Wagen.
        super().schritt(dt)

    def beruehrt_von(self, nummer: int, team: int) -> None:
        if nummer != self.zuletzt[0]:
            self.vorletzt = self.zuletzt
        self.zuletzt = (nummer, team)

    def setzen(self, pos) -> None:
        """An eine Stelle, ruhend (Anstoss)."""
        self.pos.update(pos)
        self.vorher.update(pos)
        self._roll_von.update(pos)
        self.geschw.update(0, 0)
        self.tempo.update(0, 0)
        self.zuletzt = self.vorletzt = (-1, -1)

    # ---- Bild ---------------------------------------------------------
    def rollen(self) -> None:
        """Die Lage des Musters der zurueckgelegten Strecke nachfuehren.
        Rollt er nach rechts, dreht er sich um die Achse, die von oben
        gesehen nach unten zeigt - und das Muster wandert mit."""
        weg = self.pos - self._roll_von
        self._roll_von.update(self.pos)
        d = weg.length()
        if d < 0.01 or d > 200.0:
            return
        # Achse (in Bildkoordinaten, z zum Betrachter): senkrecht zur
        # Bewegung, in der Bodenebene.
        achse = (-weg.y / d, weg.x / d, 0.0)
        self._lage = _drehen(self._lage, achse, d / self.radius)

    def selbst_zeichnen(self, ziel, p) -> None:
        """Vom Renderer statt eines Bildes gerufen (render.wesen_zeichnen)."""
        r = int(self.radius)
        m = r + 2
        a = K.AUTOBALL
        if self._bild is None:
            self._bild = pygame.Surface((2 * m, 2 * m), pygame.SRCALPHA)
            # Licht von oben links, Schatten unten rechts - eine Kugel,
            # keine Scheibe. Einmal gebaut und darueber gelegt (geblendet,
            # nicht hineingemalt: sonst stanzte das Halbdurchsichtige ein
            # Loch in den Ball).
            self._glanz = pygame.Surface((2 * m, 2 * m), pygame.SRCALPHA)
            for i in range(6, 0, -1):
                pygame.draw.circle(self._glanz, (255, 255, 255, 14),
                                   (m - r // 3, m - r // 3), int(r * 0.12 * i))
            pygame.draw.circle(self._glanz, (255, 255, 255, 90),
                               (m - r // 3, m - r // 3), max(2, r // 9))
            for i in range(5):
                pygame.draw.arc(self._glanz, (0, 0, 0, 26),
                                pygame.Rect(2 + i, 2 + i, 2 * (r - i), 2 * (r - i)),
                                -2.4, 0.8, 3)
        s = self._bild
        s.fill((0, 0, 0, 0))
        pygame.draw.circle(s, a["ball_farbe"], (m, m), r - 1)
        lage = self._lage
        gross = r * 0.21
        for f in _FLECKEN:
            x = sum(lage[0][k] * f[k] for k in range(3))
            y = sum(lage[1][k] * f[k] for k in range(3))
            z = sum(lage[2][k] * f[k] for k in range(3))
            if z <= 0.0:
                continue
            # Am Rand flach gedrueckt (Verkuerzung), in der Mitte rund.
            breit = max(1.5, gross * z)
            mitte = (m + x * (r - 1), m + y * (r - 1))
            if z > 0.97:
                pygame.draw.circle(s, a["ball_flecken"], mitte, gross)
                continue
            winkel = math.atan2(y, x)
            vorn = pygame.Vector2(math.cos(winkel), math.sin(winkel))
            quer = pygame.Vector2(-vorn.y, vorn.x)
            ecken = [pygame.Vector2(mitte) + vorn * (breit * math.cos(t)) + quer * (gross * math.sin(t))
                     for t in [i * math.pi / 5 for i in range(10)]]
            pygame.draw.polygon(s, a["ball_flecken"], ecken)
        # Was ueber den Rand ragt, wegschneiden: nur der Kreis bleibt.
        maske = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(maske, (255, 255, 255, 255), (m, m), r - 1)
        s.blit(maske, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.circle(s, a["ball_kante"], (m, m), r, 2)
        s.blit(self._glanz, (0, 0))
        ziel.blit(s, (p.x - m, p.y - m))


# ══════════════════════════════════════════════════════════════════
# Beruehrungen
# ══════════════════════════════════════════════════════════════════

def _kreuz(a, b) -> float:
    return a.x * b.y - a.y * b.x


def _senkrecht(v):
    """Geschwindigkeit eines Punkts im Abstand v bei Drehung 1 rad/s."""
    return pygame.Vector2(-v.y, v.x)


def wand_beruehrung(welt, pos, radius: float, ebene: int):
    """Die tiefste Beruehrung eines Kreises mit festen Kacheln (und
    Loechern - der Ball faellt nirgends hinunter): (Normale, Tiefe) oder
    None. Die Normale zeigt von der Wand weg."""
    e = welt.ebene(ebene)
    t = K.TILE
    tiefste = None
    for ty in range(int((pos.y - radius) // t), int((pos.y + radius) // t) + 1):
        for tx in range(int((pos.x - radius) // t), int((pos.x + radius) // t) + 1):
            if not (e.fest(tx, ty) or e.loch(tx, ty)):
                continue
            nx = max(tx * t, min(pos.x, tx * t + t))
            ny = max(ty * t, min(pos.y, ty * t + t))
            d = pygame.Vector2(pos.x - nx, pos.y - ny)
            abstand = d.length()
            if abstand >= radius:
                continue
            if abstand < 1e-6:
                # Mittelpunkt in der Kachel: kann bei Teilschritten nicht
                # vorkommen, aber wenn, dann zur naechsten Kante hinaus.
                mitte = pygame.Vector2(tx * t + t / 2, ty * t + t / 2)
                d = pos - mitte
                if d.length_squared() < 1e-9:
                    d = pygame.Vector2(0, -1)
                n = (pygame.Vector2(1 if d.x > 0 else -1, 0) if abs(d.x) > abs(d.y)
                     else pygame.Vector2(0, 1 if d.y > 0 else -1))
                tiefe = radius + t / 2
            else:
                n = d / abstand
                tiefe = radius - abstand
            if tiefste is None or tiefe > tiefste[1]:
                tiefste = (n, tiefe)
    return tiefste


def wagen_kasten(b):
    """Mitte, Laengs- und Querachse eines Wagens."""
    vorn = b.vorn
    return b.pos, vorn, pygame.Vector2(-vorn.y, vorn.x)


def ball_an_wagen(ball_pos, radius: float, b):
    """Beruehrung Ball - Wagen (Rechteck): (Normale vom Wagen zum Ball,
    Tiefe, Beruehrpunkt) oder None."""
    hl, hb = K.AUTOBALL["wagen_halb"]
    mitte, vorn, quer = wagen_kasten(b)
    rel = ball_pos - mitte
    lx, ly = rel.dot(vorn), rel.dot(quer)
    cx, cy = max(-hl, min(hl, lx)), max(-hb, min(hb, ly))
    if cx == lx and cy == ly:
        # Mittelpunkt im Wagen - nach der kuerzesten Seite hinaus.
        if hl - abs(lx) < hb - abs(ly):
            cx = math.copysign(hl, lx or 1.0)
            n = vorn * math.copysign(1.0, lx or 1.0)
        else:
            cy = math.copysign(hb, ly or 1.0)
            n = quer * math.copysign(1.0, ly or 1.0)
        punkt = mitte + vorn * cx + quer * cy
        return n, radius + (punkt - ball_pos).length(), punkt
    punkt = mitte + vorn * cx + quer * cy
    d = ball_pos - punkt
    abstand = d.length()
    if abstand >= radius:
        return None
    if abstand < 1e-6:
        n = rel.normalize() if rel.length_squared() > 1e-9 else vorn
    else:
        n = d / abstand
    return n, radius - abstand, punkt


def wagen_kreise(b) -> list:
    vorn = b.vorn
    return [b.pos + vorn * x for x in K.AUTOBALL["wagen_kreise"]]


def wagen_an_wagen(a, b):
    """Tiefste Beruehrung zweier Wagen (je drei Kreise): (Normale von a
    nach b, Tiefe, Beruehrpunkt) oder None."""
    r = K.AUTOBALL["wagen_kreis"]
    if a.pos.distance_squared_to(b.pos) > (2 * (r + 12.0)) ** 2:
        return None
    tiefste = None
    for ca in wagen_kreise(a):
        for cb in wagen_kreise(b):
            d = cb - ca
            abstand = d.length()
            tiefe = 2 * r - abstand
            if tiefe <= 0:
                continue
            if tiefste is None or tiefe > tiefste[1]:
                if abstand < 1e-6:
                    n = b.pos - a.pos
                    n = n.normalize() if n.length_squared() > 1e-9 else pygame.Vector2(1, 0)
                else:
                    n = d / abstand
                tiefste = (n, tiefe, ca + n * (r - tiefe / 2))
    return tiefste


# ══════════════════════════════════════════════════════════════════
# Das Spielfeld: alles, was sich beruehrt, in einem Schritt
# ══════════════════════════════════════════════════════════════════

class Spielfeld:
    """Loest Ball, Wagen und Waende zusammen. Wird vom Gastgeber nach dem
    Weltschritt gerufen, wenn die Wagen schon gefahren sind.

    `stoesse` zaehlt die Ballkontakte dieses Schritts (fuer Ton und
    "wer war zuletzt dran")."""

    def __init__(self, welt) -> None:
        self.welt = welt
        self.stoesse: list = []      # (Wagen, Staerke) je Schritt

    # ---- Wagen verschieben, nur wohin er passt -------------------------
    @staticmethod
    def _schieben(b, weg) -> bool:
        if weg.length_squared() < 1e-12:
            return True
        neu = b.pos + weg
        if b.passt(neu):
            b.pos.update(neu)
            return True
        # Wenigstens an der Wand entlang.
        for teil in (pygame.Vector2(weg.x, 0), pygame.Vector2(0, weg.y)):
            if teil.length_squared() > 1e-12 and b.passt(b.pos + teil):
                b.pos += teil
                return False
        return False

    # ---- Ein ganzer Schritt -------------------------------------------
    def schritt(self, ball, wagen: list, dt: float) -> None:
        a = K.AUTOBALL
        self.stoesse = []
        wagen = [b for b in wagen if b.lebt and b.ebene == ball.ebene]
        self._wagen_paare(wagen)

        # Rollen bremst gleichmaessig, die Luft anteilig.
        tempo = ball.geschw.length()
        if tempo > 0.0:
            neu = (max(0.0, tempo - a["ball_rollen"] * dt)
                   * max(0.0, 1.0 - a["ball_luft"] * dt))
            if neu > 0.01:
                ball.geschw.scale_to_length(min(neu, a["ball_hoechst"]))
            else:
                ball.geschw.update(0, 0)

        weg = ball.geschw.length() * dt
        teile = max(1, int(math.ceil(weg / a["teilschritt"])))
        h = dt / teile
        for _ in range(teile):
            ball.pos += ball.geschw * h
            for _ in range(a["durchgaenge"]):
                ruhig = self._ball_waende(ball)
                for b in wagen:
                    ruhig = self._ball_wagen(ball, b) and ruhig
                if ruhig:
                    break
            self._hart_loesen(ball, wagen)
        if ball.geschw.length() > a["ball_hoechst"]:
            ball.geschw.scale_to_length(a["ball_hoechst"])
        ball.tempo.update(ball.geschw)

    # ---- Ball an Wand ---------------------------------------------------
    def _ball_waende(self, ball) -> bool:
        """Alle Waende, an die der Ball stoesst. True: es gab keine."""
        a = K.AUTOBALL
        ruhig = True
        for _ in range(4):
            b = wand_beruehrung(self.welt, ball.pos, ball.radius, ball.ebene)
            if b is None:
                break
            ruhig = False
            n, tiefe = b
            ball.pos += n * tiefe
            vn = ball.geschw.dot(n)
            if vn < 0.0:
                ball.geschw -= n * (vn * (1.0 + a["abprall_wand"]))
                # An der Wand reibt er ein wenig - sonst glitte er ewig.
                tang = ball.geschw - n * ball.geschw.dot(n)
                ball.geschw -= tang * 0.04
        return ruhig

    # ---- Ball an Wagen --------------------------------------------------
    def _ball_wagen(self, ball, b) -> bool:
        """Eine Beruehrung loesen: Lage nach Masse aufteilen, dann der
        Impuls. True: sie beruehrten sich nicht."""
        a = K.AUTOBALL
        k = ball_an_wagen(ball.pos, ball.radius, b)
        if k is None:
            return True
        n, tiefe, punkt = k
        im_ball = 1.0 / a["ball_masse"]
        im_wagen = 1.0 / a["wagen_masse"]
        # Die Lage. Der Wagen nimmt seinen Anteil nur, wenn er dorthin
        # passt; sonst muss der Ball alles nehmen - und kann er das wegen
        # einer Wand nicht, loest es der naechste Durchgang (_hart_loesen).
        anteil_wagen = im_wagen / (im_ball + im_wagen)
        if not self._schieben(b, -n * (tiefe * anteil_wagen)):
            anteil_wagen = 0.0
        ball.pos += n * (tiefe * (1.0 - anteil_wagen))
        # Der Impuls, mit der Drehung des Wagens am Beruehrpunkt.
        r = punkt - b.pos
        v_wagen = b.geschw + _senkrecht(r) * b.gier
        rel = ball.geschw - v_wagen
        vn = rel.dot(n)
        if vn < 0.0:
            traeg = K.FAHRZEUG["traegheit"]
            rn = _kreuz(r, n)
            nenner = im_ball + im_wagen + rn * rn * im_wagen / traeg
            j = -(1.0 + a["abprall_wagen"]) * vn / nenner
            impuls = n * j
            # Reibung: der Wagen nimmt den Ball seitlich etwas mit.
            tang = rel - n * vn
            if tang.length_squared() > 1e-6:
                t = tang.normalize()
                rt = _kreuz(r, t)
                jt = -tang.length() / (im_ball + im_wagen + rt * rt * im_wagen / traeg)
                jt = max(-a["reibung_wagen"] * j, min(a["reibung_wagen"] * j, jt))
                impuls += t * jt
            ball.geschw += impuls * im_ball
            b.geschw -= impuls * im_wagen
            b.gier -= _kreuz(r, impuls) * im_wagen / traeg
            self.stoesse.append((b, -vn))
            fahrer = getattr(b, "fahrer", None)
            ball.beruehrt_von(getattr(fahrer, "nummer", -1),
                              getattr(fahrer, "team", -1))
        return False

    # ---- Wagen an Wagen -------------------------------------------------
    def _wagen_paare(self, wagen: list) -> None:
        a = K.AUTOBALL
        traeg = K.FAHRZEUG["traegheit"]
        im = 1.0 / a["wagen_masse"]
        for _ in range(3):
            ruhig = True
            for i, x in enumerate(wagen):
                for y in wagen[i + 1:]:
                    k = wagen_an_wagen(x, y)
                    if k is None:
                        continue
                    ruhig = False
                    n, tiefe, punkt = k
                    # Jeder die Haelfte; kann einer nicht, der andere alles.
                    if not self._schieben(x, -n * (tiefe / 2)):
                        self._schieben(y, n * tiefe)
                    elif not self._schieben(y, n * (tiefe / 2)):
                        self._schieben(x, -n * (tiefe / 2))
                    rx, ry = punkt - x.pos, punkt - y.pos
                    vx = x.geschw + _senkrecht(rx) * x.gier
                    vy = y.geschw + _senkrecht(ry) * y.gier
                    vn = (vy - vx).dot(n)
                    if vn >= 0.0:
                        continue
                    nx, ny = _kreuz(rx, n), _kreuz(ry, n)
                    nenner = 2 * im + (nx * nx + ny * ny) * im / traeg
                    j = -(1.0 + a["abprall_wagen_wagen"]) * vn / nenner
                    x.geschw -= n * (j * im)
                    y.geschw += n * (j * im)
                    x.gier -= nx * j * im / traeg
                    y.gier += ny * j * im / traeg
                    if -vn > K.FAHRZEUG["aufprall_hart"] and x.welt is not None:
                        x.welt.klang("buggy_aufprall", min(1.0, -vn / 300.0),
                                     punkt, x.ebene)
            if ruhig:
                break

    # ---- Die letzte Stufe ------------------------------------------------
    def _hart_loesen(self, ball, wagen: list) -> None:
        """Was nach allen Durchgaengen noch ueberlappt, klemmt: der Ball
        zwischen Wagen und Wand oder zwischen zwei Wagen. Dann gibt der
        Wagen ganz nach. Kann er auch das nicht (er steht selbst an einer
        Wand), geht er dorthin zurueck, wo er zu Beginn des Schritts stand.
        Zuletzt noch einmal die Waende - die gelten immer."""
        grenze = K.AUTOBALL["rest_ueberlapp"]
        for b in wagen:
            k = ball_an_wagen(ball.pos, ball.radius, b)
            if k is None or k[1] <= grenze:
                continue
            n, tiefe, _ = k
            if self._schieben(b, -n * (tiefe + 0.05)):
                pass
            elif ball_an_wagen(ball.pos, ball.radius, b) is not None:
                vorher = pygame.Vector2(b.vorher)
                if (b.passt(vorher)
                        and ball_an_wagen(ball.pos, ball.radius - grenze,
                                          _Stelle(b, vorher)) is None):
                    b.pos.update(vorher)
            # Was ihn weiter hineintreiben wuerde, ist weg.
            v = b.geschw.dot(n)
            if v > 0.0:
                b.geschw -= n * v
        self._ball_waende(ball)


class _Stelle:
    """Ein Wagen an einer anderen Stelle - nur fuer die Frage, ob er dort
    den Ball beruehren wuerde."""

    def __init__(self, b, pos) -> None:
        self.pos = pos
        self.vorn = b.vorn


# ══════════════════════════════════════════════════════════════════
# Die Spielart im Gefecht
# ══════════════════════════════════════════════════════════════════

def _rechteck(text):
    """'x0 y0 x1 y1' in Kacheln (einschliesslich) -> pygame.Rect in Pixeln."""
    try:
        x0, y0, x1, y1 = (int(v) for v in str(text).split()[:4])
    except (TypeError, ValueError):
        return None
    t = K.TILE
    return pygame.Rect(x0 * t, y0 * t, (x1 - x0 + 1) * t, (y1 - y0 + 1) * t)


class AutoballTeil:
    """Der Anteil des Gefechts fuer Autoball. Wie LobbyTeil: Methoden, die
    das Gefecht mitbekommt, damit mehrspieler.py nicht noch laenger wird."""

    # ---- Anlegen ------------------------------------------------------
    def _ab_anlegen(self) -> None:
        self.ball = None
        self.spielfeld = None
        self.ab_anstoss = 0.0         # Countdown bis zum Anstoss
        self.ab_jubel = 0.0           # Pause nach einem Tor
        self.ab_tor_team = -1         # wer zuletzt getroffen hat
        self.ab_schuetze = ""         # und wer genau ("" = Eigentor/keiner)
        self.ab_verlaengerung = False
        self.ab_ende_nach_jubel = False
        self.tore_von: dict = {}      # Spielernummer -> Tore
        self._ab_tore_vorher = [0, 0]
        self._ab_stoss_rest = 0.0     # Sperre fuer den Stosston
        self._ab_linien = None        # Flaeche fuer die Linien, wiederverwendet

    @property
    def mit_ball(self) -> bool:
        return bool(self.regeln.get("ball"))

    @property
    def tore_ziel(self) -> int:
        return int(self.regelwerk.get("tore", K.AUTOBALL["tore"]))

    def _ab_tore(self) -> list:
        """Die beiden Torraeume aus dem Kartenkopf: [Rect Team 0, Rect Team 1].
        Team 0 verteidigt das erste."""
        raus = []
        for i in range(2):
            r = _rechteck(self.karte_kopf.get("tor_%d" % i, ""))
            raus.append(r)
        return raus

    def _ab_marken(self, schluessel: str) -> list:
        buchstaben = str(self.karte_kopf.get(schluessel, "")).split()
        punkte = []
        for z in buchstaben:
            for p in self.welt.ebene(0).marken.get(z, ()):
                punkte.append(pygame.Vector2(p))
        return punkte

    def _ab_mitte(self) -> pygame.Vector2:
        m = self._ab_marken("ball")
        if m:
            return m[0]
        e = self.welt.ebene(0)
        return pygame.Vector2(e.pixel_breite / 2, e.pixel_hoehe / 2)

    # ---- Runde ----------------------------------------------------------
    def _ab_runde_neu(self) -> None:
        """Zu jeder neuen Runde (und beim Start ohne Lobby): Ball, Wagen,
        Anstoss. Ohne Autoball raeumt es nur weg, was davon noch steht."""
        if self.ball is not None:
            self.ball.lebt = False
            self.ball = None
        self.ab_jubel = 0.0
        self.ab_tor_team = -1
        self.ab_schuetze = ""
        self.ab_verlaengerung = False
        self.ab_ende_nach_jubel = False
        self.tore_von = {}
        self._ab_tore_vorher = [0, 0]
        if not self.mit_ball:
            self.spielfeld = None
            for b in list(self.fahrzeuge):
                if getattr(b, "besitzer", None) is not None:
                    if b.fahrer is not None:
                        self._fahrzeug_loesen(b.fahrer)
                    b.lebt = False
                    self.fahrzeuge.remove(b)
            return
        self.spielfeld = Spielfeld(self.welt)
        if not self.ist_gastgeber:
            return
        self.ball = Ball(self._ab_mitte(), 0)
        self.welt.dazu(self.ball)
        for k in self.kaempfer.values():
            self._ab_wagen_fuer(k)
        self._ab_anstoss()

    def _ab_wagen_fuer(self, k):
        """Jeder hat seinen eigenen Wagen. Gibt es ihn schon, steigt er
        wieder ein; sonst wird einer gebaut."""
        from .fahrzeug import Buggy
        b = next((w for w in self.fahrzeuge
                  if getattr(w, "besitzer", None) == k.nummer and w.lebt), None)
        if b is None:
            platz, winkel = self._ab_platz(k)
            b = Buggy(platz, 0, winkel)
            b.besitzer = k.nummer
            b.mit_boost = True
            b.wagen_stoesse = True
            b.boost_vorrat = K.AUTOBALL["boost_voll"] * 0.33
            self.welt.dazu(b)
            self.fahrzeuge.append(b)
        if k.fahrzeug is not b:
            self._fahrzeug_loesen(k)
            self._einsteigen(k, b, ton=False)
        return b

    def _ab_platz(self, k):
        """Wo dieser Spieler zum Anstoss steht und wohin er schaut.

        Je Mannschaft eine Reihe Marken (Kopf: "anstoss_0", "anstoss_1"),
        der Reihe nach vergeben - nach Spielernummer, damit es bei jedem
        Anstoss dieselben Plaetze sind. Mehr Spieler als Marken: hinter die
        letzte, versetzt."""
        team = k.team if k.team in (0, 1) else 0
        mitte = self._ab_mitte()
        # Die naechsten zuerst, bei gleichem Abstand die obere: so stehen
        # beide Mannschaften spiegelgleich, auch eins gegen eins.
        marken = sorted(self._ab_marken("anstoss_%d" % team),
                        key=lambda p: (round(p.distance_to(mitte)), p.y))
        if not marken:
            e = self.welt.ebene(0)
            seite = -1 if team == 0 else 1
            marken = [pygame.Vector2(mitte.x + seite * e.pixel_breite * 0.25, mitte.y)]
        mannschaft = sorted(x.nummer for x in self.kaempfer.values() if x.team == k.team)
        i = mannschaft.index(k.nummer) if k.nummer in mannschaft else 0
        if i < len(marken):
            platz = pygame.Vector2(marken[i])
        else:
            seite = -1 if team == 0 else 1
            zeile = i - len(marken)
            platz = pygame.Vector2(marken[-1].x + seite * 70 * (1 + zeile // 3),
                                   marken[-1].y + (zeile % 3 - 1) * 60)
        richtung = mitte - platz
        winkel = math.degrees(math.atan2(richtung.y, richtung.x))
        return platz, winkel

    def _ab_anstoss(self) -> None:
        """Ball in die Mitte, jeder auf seinen Platz, Countdown."""
        if self.ball is None:
            return
        self.ball.setzen(self._ab_mitte())
        for b in self.fahrzeuge:
            k = b.fahrer
            if k is None:
                continue
            platz, winkel = self._ab_platz(k)
            b.start = (pygame.Vector2(platz), 0, winkel)
            b.zuruecksetzen()
            b.boost_vorrat = K.AUTOBALL["boost_voll"] * 0.33
            k.pos.update(b.pos)
        self.ab_anstoss = K.AUTOBALL["anstoss"]
        self.ab_jubel = 0.0
        self.welt.klang("autoball_pfiff", 0.6)

    # ---- Jeder Schritt (Gastgeber) ------------------------------------
    def _autoball(self, dt: float) -> None:
        """Vor dem Weltschritt: Wagen fuer alle, Uhr, Anstoss, Jubel."""
        if not self.mit_ball or self.ball is None:
            return
        # Wer neu dazukommt, bekommt einen Wagen; wer geht, nimmt seinen mit.
        for k in self.kaempfer.values():
            if k.lebt and k.fahrzeug is None:
                b = self._ab_wagen_fuer(k)
                if self.ab_anstoss <= 0 and self.ab_jubel <= 0:
                    # Mitten im Spiel: an seinen Platz, wenn er frei ist.
                    platz, winkel = self._ab_platz(k)
                    if b.passt(platz, winkel):
                        b.start = (pygame.Vector2(platz), 0, winkel)
                        b.zuruecksetzen()
                        k.pos.update(b.pos)
        for b in list(self.fahrzeuge):
            besitzer = getattr(b, "besitzer", None)
            if besitzer is not None and besitzer not in self.kaempfer:
                b.lebt = False
                self.fahrzeuge.remove(b)
        if self.ab_jubel > 0.0:
            self.ab_jubel -= dt
            if self.ab_jubel <= 0.0:
                if self.ab_ende_nach_jubel:
                    self.sieger_team = self.ab_tor_team
                    self._runde_beenden(gewonnen=True)
                else:
                    self._ab_anstoss()
            return
        if self.ab_anstoss > 0.0:
            self.ab_anstoss = max(0.0, self.ab_anstoss - dt)
            return
        if self.ab_verlaengerung:
            return
        # Die Uhr laeuft nur, solange gespielt wird: nach einem Tor und
        # beim Anstoss steht sie, wie im Vorbild.
        self.rest = max(0.0, self.rest - dt)
        if self.rest > 0.0:
            return
        sieger = self._bestes_team()
        if sieger >= 0:
            self.sieger_team = sieger
            self._runde_beenden(gewonnen=True)
            return
        # Gleichstand: Verlaengerung, das naechste Tor entscheidet.
        self.ab_verlaengerung = True
        self.melden("VERLÄNGERUNG - DAS NÄCHSTE TOR ENTSCHEIDET", 4.0)
        self._ab_anstoss()

    def _ab_physik(self, dt: float) -> None:
        """Nach dem Weltschritt: Ball und Stoesse, dann das Tor."""
        if not self.mit_ball or self.ball is None or self.spielfeld is None:
            return
        ball = self.ball
        wagen = [b for b in self.fahrzeuge if b.lebt]
        if self.ab_anstoss > 0.0:
            # Countdown: alles steht an seinem Platz.
            ball.setzen(self._ab_mitte())
            for b in wagen:
                pos, ebene, winkel = b.start
                b.pos.update(pos)
                b.winkel = winkel
                b.geschw.update(0, 0)
                b.gier = b.lenkwinkel = 0.0
            return
        self.spielfeld.schritt(ball, wagen, dt)
        ball.rollen()
        staerkste = max((s for _, s in self.spielfeld.stoesse), default=0.0)
        self._ab_stoss_rest = max(0.0, self._ab_stoss_rest - dt)
        # GRUND fuer die Sperre: ein Wagen, der den Ball vor sich her
        # schiebt, stoesst ihn in vielen Schritten hintereinander an - ohne
        # sie ratterte der Ton wie ein Maschinengewehr.
        if staerkste > 40.0 and self._ab_stoss_rest <= 0.0:
            self._ab_stoss_rest = 0.12
            self.welt.klang("autoball_stoss", min(1.0, 0.3 + staerkste / 500.0),
                            ball.pos, ball.ebene)
        if self.ab_jubel <= 0.0 and not self.vorbei:
            self._ab_tor_pruefen()

    def _ab_tor_pruefen(self) -> None:
        """Ein Tor zaehlt, wenn der Ball ganz im Torraum liegt - also ganz
        ueber der Linie, wie im Vorbild."""
        ball = self.ball
        r = ball.radius
        for verteidiger, raum in enumerate(self._ab_tore()):
            if raum is None:
                continue
            if not (raum.left <= ball.pos.x - r and ball.pos.x + r <= raum.right
                    and raum.top <= ball.pos.y - r and ball.pos.y + r <= raum.bottom):
                continue
            team = 1 - verteidiger
            self.teampunkte[team] += 1
            nummer, von_team = ball.zuletzt
            if von_team != team:
                # Eigentor: der letzte, der vom treffenden Team dran war.
                nummer, von_team = ball.vorletzt
            k = self.kaempfer.get(nummer) if von_team == team else None
            self.ab_tor_team = team
            self.ab_schuetze = k.name if k is not None else ""
            if k is not None:
                self.tore_von[k.nummer] = self.tore_von.get(k.nummer, 0) + 1
            self.ab_jubel = K.AUTOBALL["tor_pause"]
            ziel = self.tore_ziel
            self.ab_ende_nach_jubel = (self.ab_verlaengerung
                                       or (ziel > 0 and self.teampunkte[team] >= ziel))
            self.welt.klang("autoball_tor", 0.9)
            self._ab_jubel_funken(team)
            return

    def _ab_jubel_funken(self, team: int) -> None:
        """Funken in der Farbe der Mannschaft, dort wo der Ball liegt.
        Beim Gast genauso, sobald sein Stand steigt."""
        if self.ball is None:
            return
        farbe = K.TEAMS["kombi"][team]["hud"] if team in (0, 1) else K.C_CREAM
        a = K.AUTOBALL
        wolke(self.welt, self.ball.pos, a["jubel_funken"], 420, 1.1, farbe,
              self.ball.ebene, 2, "funke")
        wolke(self.welt, self.ball.pos, a["jubel_funken"] // 2, 260, 1.4,
              K.C_CREAM, self.ball.ebene, 2, "funke")

    # ---- Netz --------------------------------------------------------
    def _ab_meldung(self) -> dict:
        """Was der Gast vom Autoball braucht. Leer ohne Autoball."""
        if not self.mit_ball or self.ball is None:
            return {}
        b = self.ball
        return {"ball": [round(b.pos.x, 1), round(b.pos.y, 1), b.ebene,
                         round(b.geschw.x, 1), round(b.geschw.y, 1)],
                "ab": [round(self.ab_anstoss, 2), round(self.ab_jubel, 2),
                       1 if self.ab_verlaengerung else 0, self.ab_tor_team,
                       self.ab_schuetze[:16],
                       {str(n): t for n, t in self.tore_von.items()}]}

    def _ab_uebernehmen(self, meldung: dict) -> None:
        """Beim Gast: Ball und Stand aus der Weltmeldung."""
        roh = meldung.get("ball")
        if not self.mit_ball or not isinstance(roh, list) or len(roh) < 5:
            if self.ball is not None:
                self.ball = None
            return
        try:
            x, y, ebene = float(roh[0]), float(roh[1]), int(roh[2])
            vx, vy = float(roh[3]), float(roh[4])
        except (TypeError, ValueError):
            return
        if self.ball is None:
            self.ball = Ball(pygame.Vector2(x, y), ebene, nur_bild=True)
            self.ball.welt = self.welt
        else:
            self.ball.vorher.update(self.ball.pos)
            self.ball.pos.update(x, y)
        self.ball.ebene = ebene
        self.ball.geschw.update(vx, vy)
        self.ball.rollen()
        ab = meldung.get("ab")
        if isinstance(ab, list) and len(ab) >= 6:
            try:
                self.ab_anstoss = float(ab[0])
                self.ab_jubel = float(ab[1])
                self.ab_verlaengerung = bool(ab[2])
                self.ab_tor_team = int(ab[3])
                self.ab_schuetze = str(ab[4])[:16]
                if isinstance(ab[5], dict):
                    self.tore_von = {int(n): int(t) for n, t in ab[5].items()}
            except (TypeError, ValueError):
                pass
        # Ein neues Tor: dieselben Funken wie beim Gastgeber.
        for i in range(min(2, len(self.teampunkte))):
            if self.teampunkte[i] > self._ab_tore_vorher[i]:
                self._ab_jubel_funken(i)
        self._ab_tore_vorher = list(self.teampunkte[:2])

    # ---- Kamera ------------------------------------------------------
    def _ab_kamera_ziel(self, pos):
        """Die Ballkamera: ein Stueck vom eigenen Wagen zum Ball hin."""
        if not self.mit_ball or self.ball is None:
            return pos
        a = K.AUTOBALL
        zug = (self.ball.pos - pos) * a["kamera_zug"]
        if zug.length() > a["kamera_max"]:
            zug.scale_to_length(a["kamera_max"])
        return pos + zug

    # ---- Bild --------------------------------------------------------
    def _ab_feld_zeichnen(self, flaeche, ebene: int, ecke) -> None:
        """Die Linien auf dem Boden: Mittellinie, Anstosskreis, die beiden
        Torraeume in der Farbe der Mannschaft, die sie verteidigt."""
        if not self.mit_ball or ebene != 0:
            return
        a = K.AUTOBALL
        mitte = self._ab_mitte() - ecke
        e = self.welt.ebene(0)
        t = K.TILE
        tore = self._ab_tore()
        # Das Feld reicht von Torlinie zu Torlinie.
        oben, unten = t, e.pixel_hoehe - t
        if self._ab_linien is None or self._ab_linien.get_size() != flaeche.get_size():
            self._ab_linien = pygame.Surface(flaeche.get_size(), pygame.SRCALPHA)
        flaeche_alpha = self._ab_linien
        flaeche_alpha.fill((0, 0, 0, 0))
        pygame.draw.line(flaeche_alpha, a["linie"], (mitte.x, oben - ecke.y),
                         (mitte.x, unten - ecke.y), a["linie_dicke"])
        pygame.draw.circle(flaeche_alpha, a["linie"], (int(mitte.x), int(mitte.y)),
                           int(a["ball_radius"] * 3), a["linie_dicke"])
        pygame.draw.circle(flaeche_alpha, a["linie"], (int(mitte.x), int(mitte.y)), 6)
        for team, raum in enumerate(tore):
            if raum is None:
                continue
            farbe = K.TEAMS["kombi"][team]["hud"]
            r = raum.move(-ecke.x, -ecke.y)
            pygame.draw.rect(flaeche_alpha, farbe + (a["tor_flaeche"],), r)
            # Der Strafraum davor, als Rahmen in Teamfarbe.
            breit = int(a["ball_radius"] * 3)
            vorn = (pygame.Rect(r.right, r.top - t, breit, r.height + 2 * t)
                    if team == 0 else
                    pygame.Rect(r.left - breit, r.top - t, breit, r.height + 2 * t))
            pygame.draw.rect(flaeche_alpha, farbe + (110,), vorn, a["linie_dicke"])
            # Die Torlinie selbst kraeftig.
            x = r.right if team == 0 else r.left
            pygame.draw.line(flaeche_alpha, farbe + (220,), (x, r.top), (x, r.bottom - 1),
                             a["linie_dicke"] + 1)
        flaeche.blit(flaeche_alpha, (0, 0))

    def ab_boost_taste(self) -> str:
        """Der Boost liegt auf "feuer" - meist die linke Maustaste, und die
        hat keinen Tastennamen."""
        name = self._tastenname("feuer")
        return "MAUS L" if name == "FEUER" else name

    def _ab_hinweis_text(self) -> str:
        return ("[%s/%s] GAS  [%s/%s] LENKEN  [%s] HANDBREMSE  [%s] BOOST" % (
            self._tastenname("vor"), self._tastenname("zurueck"),
            self._tastenname("links"), self._tastenname("rechts"),
            self._tastenname("dash"), self.ab_boost_taste()))

    def _ab_mitte_zeichnen(self, ziel) -> None:
        """Gross in der Bildmitte: der Countdown, und nach einem Tor wer."""
        if not self.mit_ball or self.vorbei:
            return
        w, h = K.GAME_W, K.GAME_H
        if self.ab_jubel > 0.0 and self.ab_tor_team in (0, 1):
            kombi = K.TEAMS["kombi"][self.ab_tor_team]
            SCHRIFT.zeichnen(ziel, "TOR FÜR %s!" % kombi["name"], w // 2, h // 2 - 46,
                             kombi["hud"], 3, ausrichtung="mitte", schatten=(8, 6, 4))
            unter = self.ab_schuetze or "EIGENTOR"
            SCHRIFT.zeichnen(ziel, unter, w // 2, h // 2 - 18, K.C_CREAM, 1,
                             ausrichtung="mitte", schatten=(8, 6, 4))
            return
        if self.ab_anstoss > 0.0:
            zahl = int(math.ceil(self.ab_anstoss))
            SCHRIFT.zeichnen(ziel, "%d" % zahl, w // 2, h // 2 - 50, K.C_AMBER, 4,
                             ausrichtung="mitte", schatten=(8, 6, 4))
            if self.ab_verlaengerung:
                SCHRIFT.zeichnen(ziel, "VERLÄNGERUNG", w // 2, h // 2 - 16, K.C_RED, 1,
                                 ausrichtung="mitte", schatten=(8, 6, 4))

    def _ab_ballpfeil(self, ziel) -> None:
        """Ist der Ball nicht im Bild, zeigt ein Pfeil am Rand auf ihn."""
        if not self.mit_ball or self.ball is None or self.vorbei:
            return
        p = self.kamera.zu_bild(self.ball.pos)
        rand = 24
        if rand <= p.x <= K.GAME_W - rand and rand <= p.y <= K.GAME_H - rand:
            return
        mitte = pygame.Vector2(K.GAME_W / 2, K.GAME_H / 2)
        richtung = p - mitte
        if richtung.length_squared() < 1:
            return
        stelle = self._randstelle(richtung, K.ZONE["randpfeil_abstand"])
        n = richtung.normalize()
        q = pygame.Vector2(-n.y, n.x)
        lang = K.ZONE["randpfeil"]
        spitze = stelle + n * lang
        punkte = [spitze, stelle - n * lang * 0.6 + q * lang * 0.8,
                  stelle - n * lang * 0.2, stelle - n * lang * 0.6 - q * lang * 0.8]
        pygame.draw.polygon(ziel, (8, 6, 4), [x + pygame.Vector2(1, 1) for x in punkte])
        pygame.draw.polygon(ziel, K.AUTOBALL["ball_farbe"], punkte)
        pygame.draw.circle(ziel, K.AUTOBALL["ball_flecken"],
                           (int(stelle.x - n.x * 4), int(stelle.y - n.y * 4)), 3)
