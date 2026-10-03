"""
DUSTFRONT - Die Lobby und der Rundenplan
========================================

Wer eine Runde aufmacht, landet nicht mehr sofort im Gefecht, sondern in
der Lobby: ein Platz zum Herumstehen, ein Schiessstand mit Puppen, links
eine Arena fuer PVP und rechts ein Gehege mit Zombies. Waehrenddessen
stellt der Gastgeber die naechsten Runden ein - im Spiel, mit der Maus,
und nicht mehr im Terminal vor dem Start.

Zwei Teile:

* `LobbyTeil` haengt am Gefecht (als zweite Elternklasse). Was dort steht,
  ist alles, was das Gefecht in der Lobby anders macht, und der Ablauf des
  Rundenplans: starten, weiterschalten, zurueck in die Lobby.
* `Rundenplanung` ist die Tafel dazu, eine Szene ueber dem laufenden
  Gefecht wie das Ausruestungsmenue. Der Gastgeber stellt ein, ein Gast
  sieht zu.

Der Rundenplan ist bewusst versteckt: zu sehen ist zuerst nur die eine
naechste Runde und ein Knopf zum Starten. Wer mehr will - drei Runden
hintereinander, eine Schleife, Einstellungen von einer Runde in die
naechste kopieren -, klappt ihn auf.

Nichts aus der Lobby wird gebucht. Das Buchen haengt am Rundenende, und
eine Lobby endet nie; ihre Zaehler werden mit dem Start der naechsten
Runde geleert.
"""

from __future__ import annotations

import pygame

from . import config as K
from . import regeln as R
from . import ui
from .font import SCHRIFT
from .menues import Menue


def lobby_regeln() -> dict:
    """Die Regeln, die in der Lobby gelten.

    Jeder hat alles - man soll hier jede Waffe ausprobieren koennen, auch
    die, die man in der naechsten Runde nicht tragen wird. Kein
    Einstiegsschutz, der wuerde im Schiessstand nur stoeren; keine knappe
    Munition, keine herumliegenden Medkits, kein Raketenwerfer.
    """
    return R.saeubern({"modus": "lobby", "karte": K.LOBBY["karte"],
                       "loadouts": "alles", "knapp": False, "schutz": False,
                       "medkits": 3, "medkit_spawn": False, "rpg": False})


# Farben der Bereiche, am Boden und in der Anzeige.
FARBEN = {"pvp": (196, 72, 48), "stand": (220, 160, 64), "pve": (132, 176, 84)}
NAMEN = {"pvp": "PVP", "stand": "SCHIESSSTAND", "pve": "PVE"}
HINWEISE = {"pvp": "ARENA: HIER TRIFFT JEDER JEDEN",
            "stand": "SCHIESSSTAND: DIE PUPPEN ZÄHLEN MIT",
            "pve": "GEHEGE: DIE ZOMBIES SIND ECHT",
            "": "LOBBY: HIER TUT NIEMANDEM ETWAS WEH"}


class LobbyTeil:
    """Was das Gefecht in der Lobby anders macht, und der Rundenplan."""

    # ---- Zustand --------------------------------------------------------
    def _lobby_anlegen(self, erste: dict | None) -> None:
        """Die Felder fuer Lobby und Plan, bei Gastgeber und Gast.

        `erste` sind die Regeln der ersten geplanten Runde - beim
        Gastgeber das, was die Kommandozeile mitgegeben hat. Ein Gast
        bekommt den Plan geschickt.
        """
        self.plan: list[dict] = [R.saeubern(erste or {}, self._umfeld())]
        self.plan_schleife = False
        self.plan_pos = 0             # welche geplante Runde laeuft / kommt
        self.plan_laeuft = False      # laeuft gerade eine geplante Runde?
        self.plan_weiter = -1.0       # Sekunden bis zur naechsten, -1: keine
        self.plan_ablage: dict | None = None
        self.plan_offen = False       # ist der Rundenplan aufgeklappt?
        self.plan_kosmetik = False    # mit Spielerkosmetik gestartet?
        self.plan_stand = 0           # zaehlt jede Aenderung mit
        self.bereiche: dict[str, pygame.Rect] = {}
        self.puppen: list = []
        self.gehege: list = []
        self._gehege_rest = 0.0
        self._bereich_vorher = None

    @property
    def in_lobby(self) -> bool:
        return bool(self.regeln.get("lobby"))

    def im_bereich(self, wesen, name: str) -> bool:
        """Steht es in diesem Bereich der Lobby? Nur Ebene 0 hat welche."""
        r = self.bereiche.get(name)
        if r is None or wesen is None or getattr(wesen, "ebene", 0) != 0:
            return False
        return r.collidepoint(wesen.pos.x, wesen.pos.y)

    def bereich_von(self, wesen) -> str:
        for name in ("pvp", "stand", "pve"):
            if self.im_bereich(wesen, name):
                return name
        return ""

    # ---- Karte ----------------------------------------------------------
    def _karte_geladen(self) -> None:
        """Nach jedem Laden einer Karte: Bereiche lesen und aufmalen.

        Auf jedem Rechner, beim Gast wie beim Gastgeber - gemalt wird in
        die Flecken der Ebene, und die sind Sache des Bildes, nicht des
        Spiels. Karten ohne Bereiche lassen das alles aus.
        """
        self.bereiche = {}
        kopf = getattr(self, "karte_kopf", None) or {}
        for name in ("pvp", "stand", "pve"):
            roh = str(kopf.get("bereich_" + name, "")).split()
            try:
                x0, y0, x1, y1 = (int(v) for v in roh)
            except ValueError:
                continue
            self.bereiche[name] = pygame.Rect(
                x0 * K.TILE, y0 * K.TILE,
                (x1 - x0 + 1) * K.TILE, (y1 - y0 + 1) * K.TILE)
        if self.bereiche:
            self._bereiche_malen()

    def _bereiche_malen(self) -> None:
        """Rahmen, Beschriftung und Absperrband auf den Boden.

        Man soll sehen, wo man ist, bevor man es merkt: eine gestrichelte
        Linie am Rand jedes Bereichs, sein Name gross auf dem Boden, und
        in jedem Tor ein Streifen Band in der Farbe des Bereichs. Alles
        blass - es ist Farbe auf Beton, kein Schild.
        """
        e = self.welt.ebene(0)
        for name, r in self.bereiche.items():
            farbe = FARBEN[name]
            flaeche = pygame.Surface(r.size, pygame.SRCALPHA)
            strich = (*farbe, 70)
            for x in range(4, r.width - 4, 12):
                pygame.draw.rect(flaeche, strich, (x, 3, 6, 2))
                pygame.draw.rect(flaeche, strich, (x, r.height - 5, 6, 2))
            for y in range(4, r.height - 4, 12):
                pygame.draw.rect(flaeche, strich, (3, y, 2, 6))
                pygame.draw.rect(flaeche, strich, (r.width - 5, y, 2, 6))
            schrift = SCHRIFT.flaeche(NAMEN[name], farbe, 3)
            schrift.set_alpha(58)
            y = (r.height - K.TILE * 2 - schrift.get_height()
                 if name == "stand" else K.TILE * 2)
            flaeche.blit(schrift, ((r.width - schrift.get_width()) // 2, y))
            e.dekal(flaeche, r.centerx, r.centery)
            if name != "stand":
                # Der Stand ist nach unten offen - er hat keine Tore.
                self._tore_malen(e, r, farbe)
        # Der Platz selbst bekommt seinen Namen, mitten in der Freiflaeche.
        platz = self._platz_mitte()
        if platz is not None:
            schrift = SCHRIFT.flaeche("LOBBY", K.C_MUTED, 3)
            schrift.set_alpha(40)
            e.dekal(schrift, platz.x, platz.y)

    def _platz_mitte(self):
        """Die Mitte zwischen Arena und Gehege, knapp unter dem Stand."""
        pvp, pve, stand = (self.bereiche.get(n) for n in ("pvp", "pve", "stand"))
        if pvp is None or pve is None:
            return None
        y = (stand.bottom + K.TILE * 3) if stand is not None else pvp.centery
        return pygame.Vector2((pvp.right + pve.left) / 2, y)

    def _tore_malen(self, e, r, farbe) -> None:
        """Absperrband in jedem Tor eines Bereichs.

        Ein Tor ist eine begehbare Kachel direkt ausserhalb des Rechtecks,
        in der Mauer, die es umgibt. Beim Gehege ist es zugleich die
        Grenze, an der die Zombies stehen bleiben - man sieht also, warum
        sie nicht herauskommen.
        """
        tx0, ty0 = r.x // K.TILE, r.y // K.TILE
        tx1, ty1 = (r.right - 1) // K.TILE, (r.bottom - 1) // K.TILE
        seiten = ([(tx0 - 1, y) for y in range(ty0, ty1 + 1)],
                  [(tx1 + 1, y) for y in range(ty0, ty1 + 1)],
                  [(x, ty0 - 1) for x in range(tx0, tx1 + 1)],
                  [(x, ty1 + 1) for x in range(tx0, tx1 + 1)])
        band = pygame.Surface((K.TILE, K.TILE), pygame.SRCALPHA)
        for i in range(-K.TILE, K.TILE, 8):
            pygame.draw.line(band, (*farbe, 120), (i, K.TILE), (i + K.TILE, 0), 3)
        for seite in seiten:
            offen = [(x, y) for (x, y) in seite if e.begehbar(x, y)]
            # Nur eine Seite, die im Wesentlichen Mauer ist, hat Tore.
            # Eine offene Seite ist keine Grenze mit Luecken, sondern gar
            # keine - dort gehoert kein Band hin.
            if len(offen) * 2 > len(seite):
                continue
            for (x, y) in offen:
                e.dekal(band, x * K.TILE + K.TILE / 2, y * K.TILE + K.TILE / 2)

    # ---- Was in der Lobby anders ist -------------------------------------
    def _darf_treffen(self, opfer, von) -> bool:
        """Darf `von` dem Kaempfer `opfer` hier Schaden machen?

        Ausserhalb der Lobby immer. In der Lobby nur dort, wo es
        verabredet ist: in der Arena unter Spielern (auch die eigene
        Granate - wer in der Arena steht, spielt), im Gehege durch
        Zombies. Auf dem Platz tut niemandem etwas weh, auch nicht, wenn
        die Kugel aus der Arena herausfliegt.
        """
        if not self.in_lobby:
            return True
        quelle = getattr(von, "von", von)
        from .mehrspieler import KampfGegner
        if isinstance(quelle, KampfGegner):
            return self.im_bereich(opfer, "pve")
        if not self.im_bereich(opfer, "pvp"):
            return False
        return (quelle is None or quelle is opfer
                or self.im_bereich(quelle, "pvp"))

    def _lobby_einstieg(self, ausser=None):
        """Ein Einstiegsplatz auf dem Platz: die Marke mit den wenigsten
        Leuten drumherum. None, wenn die Karte keine hat."""
        stellen = self.welt.ebene(0).marken.get("S") or []
        if not stellen:
            return None
        andere = [k.pos for k in self.kaempfer.values()
                  if k.lebt and k is not ausser]
        return pygame.Vector2(max(
            stellen, key=lambda p: min((p.distance_to(q) for q in andere),
                                       default=9999.0)))

    def _lobby_bestuecken(self) -> None:
        """Die Puppen im Schiessstand aufstellen. Nur beim Gastgeber."""
        from .mehrspieler import KampfGegner
        self.puppen = []
        self.gehege = []
        self._gehege_rest = 0.0
        for punkt in self.welt.ebene(0).marken.get("D", ()):
            p = KampfGegner(pygame.Vector2(punkt), "puppe", 0, self)
            p.winkel = 90.0
            self.welt.dazu(p)
            self.puppen.append(p)

    def _lobby_munition(self) -> None:
        """In der Lobby geht die Munition nie aus.

        Jedes Magazin wird in jedem Schritt wieder voll, auch das der
        Wurfwaffen, und ein angefangenes Nachladen faellt weg - es gibt
        nichts nachzuladen. Die Lobby ist zum Ausprobieren da, und wer
        eine Waffe kennenlernen will, soll schiessen und nicht warten.
        Nur beim Gastgeber: die Magazine gehen mit der Weltmeldung hinaus.

        Aufgerufen **nach** dem Schritt der Welt, nicht davor. Davor
        stand es zuerst, und dann nahm der Schuss im selben Schritt gleich
        wieder eine Patrone: die Zahl sprang bei jedem Schuss von 100 auf
        99 und zurueck - beim MG im Dauerfeuer ein Flackern (gemeldet).
        """
        for k in self.kaempfer.values():
            for w in list(k.magazin):
                if w == "rakete":
                    continue        # einmal auf der Karte, einmal geschossen
                voll = K.WAFFEN.get(w, {}).get("magazin")
                if voll is not None and k.magazin[w] < voll:
                    k.magazin[w] = voll
            if getattr(k, "nachlade_rest", 0.0) > 0:
                k.nachlade_rest = 0.0

    def _lobby_schritt(self, dt: float) -> None:
        """Das Gehege fuellen, solange jemand drin ist.

        Wenige Zombies, und nur, wenn einer drin steht - mit jedem
        weiteren ein paar mehr. Wer hinausgeht, laesst sie stehen: sie
        bleiben am Gatter und warten. Bosse gibt es hier nicht; das hier
        ist Aufwaermen.
        """
        from .mehrspieler import KampfGegner
        L = K.LOBBY
        self.gehege = [g for g in self.gehege if g.lebt]
        drin = [k for k in self.kaempfer.values()
                if k.lebt and self.im_bereich(k, "pve")]
        soll = 0
        if drin:
            soll = min(L["gehege_hoechstens"],
                       L["gehege_grund"] + L["gehege_je_spieler"] * (len(drin) - 1))
        if len(self.gehege) >= soll:
            self._gehege_rest = min(self._gehege_rest, L["gehege_takt"] * 0.5)
            return
        self._gehege_rest -= dt
        if self._gehege_rest > 0:
            return
        self._gehege_rest = L["gehege_takt"]
        stellen = [p for p in self.welt.ebene(0).marken.get("Z", ())
                   if self.bereiche.get("pve") is not None
                   and self.bereiche["pve"].collidepoint(p)]
        if not stellen:
            return
        art = self.rnd.choice(L["gehege_arten"])
        g = KampfGegner(pygame.Vector2(self.rnd.choice(stellen)), art, 0, self)
        self.welt.dazu(g)
        self.gehege.append(g)

    def _im_gehege_halten(self, g) -> None:
        """Ein Zombie der Lobby bleibt im Gehege - am Tor ist Schluss."""
        r = self.bereiche.get("pve")
        if r is None:
            return
        rand = g.radius + 1
        g.pos.x = max(r.left + rand, min(r.right - rand, g.pos.x))
        g.pos.y = max(r.top + rand, min(r.bottom - rand, g.pos.y))

    def _bereich_melden(self) -> None:
        """Beim Betreten eines Bereichs einmal sagen, was hier gilt."""
        if not self.in_lobby or self.ich is None or not self.bereiche:
            self._bereich_vorher = None
            return
        jetzt = self.bereich_von(self.ich)
        if jetzt != self._bereich_vorher:
            if self._bereich_vorher is not None:
                self.hinweis = HINWEISE[jetzt]
            self._bereich_vorher = jetzt

    # ---- Der Rundenplan ------------------------------------------------
    def _plan_geaendert(self) -> None:
        """Nach jeder Aenderung: mitzaehlen und an alle schicken."""
        self.plan_stand += 1
        if self.ist_gastgeber:
            self.gastgeber.an_alle(self._plan_meldung())

    def _plan_meldung(self) -> dict:
        return {"t": "plan", "runden": [dict(d) for d in self.plan],
                "schleife": self.plan_schleife, "pos": self.plan_pos,
                "laeuft": self.plan_laeuft, "weiter": round(self.plan_weiter, 1)}

    def _plan_lesen(self, nachricht: dict) -> None:
        """Beim Gast: der Plan, wie ihn der Gastgeber gerade hat."""
        runden = nachricht.get("runden")
        if isinstance(runden, list) and runden:
            self.plan = [R.saeubern(d) for d in runden[:K.LOBBY["plan_hoechstens"]]]
        self.plan_schleife = bool(nachricht.get("schleife", False))
        self.plan_laeuft = bool(nachricht.get("laeuft", False))
        try:
            self.plan_pos = max(0, min(len(self.plan) - 1,
                                       int(nachricht.get("pos", 0))))
            self.plan_weiter = float(nachricht.get("weiter", -1.0))
        except (TypeError, ValueError):
            pass
        self.plan_stand += 1

    def plan_verstellen(self, nr: int, schluessel: str, wert) -> None:
        """Eine Regel einer geplanten Runde setzen. Nur der Gastgeber."""
        if not self.ist_gastgeber or not 0 <= nr < len(self.plan):
            return
        d = dict(self.plan[nr])
        d[schluessel] = wert
        if schluessel in ("modus", "ende_art"):
            # Wie im Menue: die neue Endart bringt ihre eigene Vorgabe.
            d.pop("ende_wert", None)
        self.plan[nr] = R.saeubern(d, self._umfeld())
        self._plan_geaendert()

    def plan_standard(self, nr: int) -> None:
        """Eine geplante Runde auf die Standardrunde setzen (0.32)."""
        if not self.ist_gastgeber or not 0 <= nr < len(self.plan):
            return
        self.plan[nr] = R.standardrunde(self._umfeld())
        self._plan_geaendert()

    def plan_dazu(self, nach: int) -> int:
        """Eine Runde hinter `nach` einfuegen, als Kopie davon."""
        if not self.ist_gastgeber or len(self.plan) >= K.LOBBY["plan_hoechstens"]:
            return nach
        nach = max(0, min(len(self.plan) - 1, nach))
        self.plan.insert(nach + 1, dict(self.plan[nach]))
        self._plan_geaendert()
        return nach + 1

    def plan_weg(self, nr: int) -> int:
        """Eine Runde aus dem Plan nehmen. Eine bleibt immer."""
        if not self.ist_gastgeber or len(self.plan) <= 1 or not 0 <= nr < len(self.plan):
            return nr
        self.plan.pop(nr)
        self.plan_pos = min(self.plan_pos, len(self.plan) - 1)
        self._plan_geaendert()
        return min(nr, len(self.plan) - 1)

    def plan_kopieren(self, nr: int) -> None:
        if 0 <= nr < len(self.plan):
            self.plan_ablage = dict(self.plan[nr])

    def plan_einfuegen(self, nr: int) -> None:
        """Die kopierten Einstellungen auf diese Runde legen."""
        if (not self.ist_gastgeber or self.plan_ablage is None
                or not 0 <= nr < len(self.plan)):
            return
        self.plan[nr] = R.saeubern(self.plan_ablage, self._umfeld())
        self._plan_geaendert()

    def plan_schleife_setzen(self, an: bool) -> None:
        if not self.ist_gastgeber:
            return
        self.plan_schleife = bool(an)
        self._plan_geaendert()

    def plan_starten(self, nr: int = 0, kosmetik: bool | None = None) -> bool:
        """Die geplante Runde `nr` anfangen. Aus der Lobby oder danach.

        `kosmetik` entscheidet der Gastgeber beim Start aus der Lobby, und
        es gilt dann fuer den ganzen Plan. Mit Kosmetik geht es nur, wenn
        alle alles geladen haben - sonst hoerte der eine den Ton des
        Werfers und der andere den gewoehnlichen Knall, und keiner wuesste,
        was der andere erlebt. Gibt zurueck, ob es losging.
        """
        if not self.ist_gastgeber or not self.plan:
            return False
        if kosmetik is not None:
            if kosmetik and not self.kosmetik_bereit:
                da, noetig = self.kosmetik_stand()
                self._meldung = "KOSMETIK LÄDT NOCH - %d VON %d" % (da, noetig)
                self._meldung_rest = 3.0
                self.hinweis = self._meldung
                return False
            self.plan_kosmetik = bool(kosmetik)
        nr = max(0, min(len(self.plan) - 1, nr))
        self.plan_pos = nr
        self.plan_laeuft = True
        self.plan_weiter = -1.0
        self.wunsch = dict(self.plan[nr], kosmetik=self.plan_kosmetik)
        self._runde_neu()
        if len(self.plan) > 1:
            self.hinweis = "RUNDE %d VON %d: %s" % (
                nr + 1, len(self.plan), K.MODI[self.modus]["name"])
        self._plan_geaendert()
        return True

    def lobby_betreten(self) -> None:
        """Zurueck in die Lobby, von wo auch immer."""
        if not self.ist_gastgeber:
            return
        self.plan_laeuft = False
        self.plan_weiter = -1.0
        self.wunsch = lobby_regeln()
        self._runde_neu()
        self._plan_geaendert()

    def _plan_fuehren(self, dt: float) -> None:
        """Nach einer geplanten Runde: Siegtafel, dann die naechste.

        Zwoelf Sekunden Tafel, damit jeder sieht, wie es ausgegangen ist.
        Dann die naechste Runde im Plan, am Ende wieder die erste, wenn
        die Schleife an ist - sonst zurueck in die Lobby.
        """
        if not self.plan_laeuft or not self.vorbei:
            return
        if self.plan_weiter < 0:
            self.plan_weiter = K.LOBBY["weiter_nach"]
            self._plan_geaendert()
            return
        self.plan_weiter -= dt
        if self.plan_weiter > 0:
            return
        naechste = self.plan_pos + 1
        if naechste < len(self.plan):
            self.plan_starten(naechste)
        elif self.plan_schleife:
            self.plan_starten(0)
        else:
            self.lobby_betreten()

    def plan_ausblick(self) -> str:
        """Was nach der laufenden Runde kommt, als eine Zeile."""
        naechste = self.plan_pos + 1
        if naechste < len(self.plan):
            return "RUNDE %d: %s" % (naechste + 1,
                                     R.kurz(self.plan[naechste], self._umfeld()))
        if self.plan_schleife and self.plan:
            return "VON VORN: %s" % R.kurz(self.plan[0], self._umfeld())
        return "ZURÜCK IN DIE LOBBY"

    def _lobby_kopf(self, ziel) -> None:
        """Oben in der Mitte: wo man ist, was als Naechstes kommt, und
        wie man es aendert."""
        mitte = K.GAME_W // 2
        SCHRIFT.zeichnen(ziel, "LOBBY", mitte, 8, K.C_CREAM, 2,
                         ausrichtung="mitte")
        if self.plan:
            vorn = "ALS NÄCHSTES: " if len(self.plan) == 1 else \
                "RUNDE 1 VON %d: " % len(self.plan)
            SCHRIFT.zeichnen(ziel, vorn + R.kurz(self.plan[0], self._umfeld()),
                             mitte, 26, K.C_AMBER, 1, ausrichtung="mitte")
        taste = self._tastenname("planen")
        text = ("[%s] RUNDEN EINSTELLEN UND STARTEN" % taste
                if self.ist_gastgeber
                else "DER GASTGEBER STELLT EIN  [%s] ANSEHEN" % taste)
        SCHRIFT.zeichnen(ziel, text, mitte, 36, K.C_MUTED, 1,
                         ausrichtung="mitte")
        wo = self.bereich_von(self.ich) if self.ich is not None else ""
        if wo:
            SCHRIFT.zeichnen(ziel, NAMEN[wo], mitte, 46, FARBEN[wo], 1,
                             ausrichtung="mitte")
        # Spielerkosmetik: wie weit sie verteilt ist. Nur, wenn es welche
        # gibt - sonst ist es eine Zeile ueber nichts.
        if self.kos_index:
            da, noetig = self.kosmetik_stand()
            if da >= noetig:
                text, farbe = "KOSMETIK: ALLES GELADEN", K.C_TEAL
            else:
                text, farbe = ("KOSMETIK LÄDT  %d VON %d" % (da, noetig),
                               K.C_AMBER)
            SCHRIFT.zeichnen(ziel, text, mitte, 56, farbe, 1,
                             ausrichtung="mitte")

    def planung_oeffnen(self) -> None:
        """Die Tafel aufmachen, beim Gastgeber zum Einstellen."""
        self.app.schieben(Rundenplanung(self.app, self))


# ══════════════════════════════════════════════════════════════════
# Die Tafel
# ══════════════════════════════════════════════════════════════════

class RegelWahl(ui.Wahl):
    """Eine Wahl, die am Rand stehen bleibt, wenn die Regel es will.

    ui.Wahl faengt am Ende immer vorn wieder an. Bei Spielarten ist das
    richtig, bei Zahlen nicht: von 15 Runden auf 1 zu springen, weil man
    einmal zu oft geklickt hat, ueberrascht jeden.
    """

    def __init__(self, *args, rund: bool = True, **kw) -> None:
        super().__init__(*args, **kw)
        self.rund = rund

    def blaettern(self, d: int) -> None:
        if self.rund:
            super().blaettern(d)
        else:
            self.index = max(0, min(len(self.optionen) - 1, self.index + d))


class Rundenplanung(Menue):
    """Die Tafel fuer die naechsten Runden. Liegt ueber dem Gefecht.

    Das Gefecht laeuft darunter weiter (Szene.weiterlaufen), sonst fiele
    die Leitung tot. Der Gastgeber stellt ein, ein Gast sieht dieselbe
    Tafel ohne Knoepfe - er weiss dann wenigstens, was kommt.
    """

    titel = "RUNDEN"
    tafel = pygame.Rect(16, 10, 608, 340)
    ZEILE = 17
    SPALTE = 150

    def __init__(self, app, gefecht) -> None:
        self.gefecht = gefecht
        self.nr = 0
        self._stand = -1
        super().__init__(app)
        self.unterzeile = ("DU STELLST DIE NÄCHSTEN RUNDEN EIN"
                           if gefecht.ist_gastgeber
                           else "DER GASTGEBER STELLT EIN - DU SIEHST ZU")

    # ---- Aufbau --------------------------------------------------------
    @property
    def darf(self) -> bool:
        return self.gefecht.ist_gastgeber

    def aufbauen(self) -> None:
        g = self.gefecht
        self._stand = g.plan_stand
        self.nr = max(0, min(len(g.plan) - 1, self.nr))
        gewaehlt = self.gewaehlt()
        alter_name = gewaehlt.name if gewaehlt is not None else ""
        self.elemente = []
        r = self.tafel
        oben = r.y + 58
        if g.plan_offen:
            self._plan_spalte(r.x + 16, oben, 168)
            links, breite = r.x + 196, r.width - 212
        else:
            links, breite = r.x + 100, r.width - 200
        self._regeln_spalte(links, oben, breite)
        self._fuss(r)
        # Die Auswahl dort lassen, wo sie war - ein Klick auf einen Wert
        # baut die Tafel neu, und die Markierung soll nicht wegspringen.
        for i, el in enumerate(self.elemente):
            if el.name == alter_name and not el.gesperrt:
                self.wahl = i
                break
        else:
            w = self.waehlbar
            self.wahl = self.elemente.index(w[0]) if w else 0

    def _plan_spalte(self, x: int, y: int, breite: int) -> None:
        g = self.gefecht
        for i, d in enumerate(g.plan):
            text = "%d  %s  %s" % (i + 1, R.anzeige(d, "modus"),
                                   R.anzeige(d, "karte"))
            k = ui.Knopf((x, y + i * 16, breite, 14), text, "runde:%d" % i)
            self.elemente.append(k)
        y += max(1, len(g.plan)) * 16 + 6
        halb = (breite - 4) // 2
        voll = len(g.plan) >= K.LOBBY["plan_hoechstens"]
        self.elemente += [
            ui.Knopf((x, y, halb, 14), "+ RUNDE", "dazu",
                     gesperrt=not self.darf or voll),
            ui.Knopf((x + halb + 4, y, halb, 14), "WEG", "weg",
                     gesperrt=not self.darf or len(g.plan) <= 1),
            ui.Knopf((x, y + 18, halb, 14), "KOPIEREN", "kopieren",
                     gesperrt=not self.darf),
            ui.Knopf((x + halb + 4, y + 18, halb, 14), "EINFÜGEN", "einfuegen",
                     gesperrt=not self.darf or g.plan_ablage is None),
        ]
        schleife = ui.Schalter((x, y + 40, breite, 14), "SCHLEIFE", "schleife",
                               g.plan_schleife, spalte=90)
        schleife.gesperrt = not self.darf
        self.elemente.append(schleife)

    @property
    def erweitert(self) -> bool:
        return bool(self.app.opt["runden_erweitert"])

    def _regeln_spalte(self, x: int, y: int, breite: int) -> None:
        g = self.gefecht
        d = g.plan[self.nr]
        umfeld = g._umfeld()
        for i, f in enumerate(R.sichtbar(d, self.erweitert)):
            rect = (x, y + i * self.ZEILE, breite, 14)
            name = ("  " if f.einzug(d) else "") + f.name(d)
            if f.schalter:
                el = ui.Schalter(rect, name, "r:" + f.schluessel,
                                 bool(d[f.schluessel]), spalte=self.SPALTE)
            else:
                werte = f.werte(d, umfeld)
                jetzt = d[f.schluessel]
                if jetzt not in werte:
                    werte = sorted(set(werte) | {jetzt}) if f.zahl else [jetzt] + werte
                el = RegelWahl(rect, name, "r:" + f.schluessel, werte,
                               werte.index(jetzt),
                               {w: f.text(w, d, umfeld) for w in werte},
                               spalte=self.SPALTE, rund=f.rund)
            el.gesperrt = not self.darf
            self.elemente.append(el)

    def _fuss(self, r) -> None:
        g = self.gefecht
        # Oben rechts: einfach oder erweitert, und zurueck zum Standard.
        oben = r.y + 40
        self.elemente.append(ui.Knopf(
            (r.right - 16 - 96, oben, 96, 14),
            "EINFACH <" if self.erweitert else "ERWEITERT >", "ansicht"))
        self.elemente.append(ui.Knopf(
            (r.right - 16 - 96 - 104, oben, 100, 14), "STANDARDRUNDE",
            "standard", gesperrt=not self.darf))
        y = r.bottom - 58
        self.elemente.append(ui.Knopf(
            (r.x + 16, y, 150, 16),
            "RUNDENPLAN <" if g.plan_offen else "RUNDENPLAN >", "planen"))
        if self.darf and g.in_lobby:
            if g.kos_index:
                # Es gibt Spielerkosmetik: der Gastgeber entscheidet beim
                # Start. Mit Kosmetik erst, wenn alle alles haben.
                da, noetig = g.kosmetik_stand()
                bereit = da >= noetig
                # Zwei schmale statt eines breiten Knopfs, rechtsbuendig
                # mit Luft zu ZURUECK in der Mitte.
                self.elemente.append(ui.Knopf(
                    (r.right - 16 - 214, y, 104, 16),
                    "MIT KOSMETIK" if bereit else "LÄDT %d/%d" % (da, noetig),
                    "start_mit", gesperrt=not bereit))
                self.elemente.append(ui.Knopf(
                    (r.right - 16 - 104, y, 104, 16), "OHNE KOSMETIK",
                    "start_ohne"))
            else:
                self.elemente.append(ui.Knopf((r.right - 16 - 150, y, 150, 16),
                                              "START", "start"))
        self.elemente.append(ui.Knopf((r.centerx - 55, y, 110, 16),
                                      "ZURÜCK", "zurueck"))

    # ---- Reaktion ------------------------------------------------------
    def ausloesen(self, el) -> None:
        g = self.gefecht
        name = el.name
        if name == "zurueck":
            self.zurueck()
            return
        if name == "planen":
            g.plan_offen = not g.plan_offen
        elif name == "ansicht":
            self.app.opt["runden_erweitert"] = not self.erweitert
            self.app.opt.speichern()
        elif name == "standard":
            g.plan_standard(self.nr)
            self.sagen("RUNDE %d IST JETZT DIE STANDARDRUNDE" % (self.nr + 1))
        elif name.startswith("runde:"):
            self.nr = int(name.split(":")[1])
        elif name == "dazu":
            self.nr = g.plan_dazu(self.nr)
        elif name == "weg":
            self.nr = g.plan_weg(self.nr)
        elif name == "kopieren":
            g.plan_kopieren(self.nr)
            self.sagen("RUNDE %d KOPIERT" % (self.nr + 1))
        elif name == "einfuegen":
            g.plan_einfuegen(self.nr)
            self.sagen("IN RUNDE %d EINGEFÜGT" % (self.nr + 1))
        elif name in ("start", "start_ohne", "start_mit"):
            if g.plan_starten(0, kosmetik=(name == "start_mit")):
                self.app.werfen()
            else:
                self.sagen("KOSMETIK LÄDT NOCH")
            return
        self.aufbauen()

    def geaendert(self, el) -> None:
        g = self.gefecht
        if el.name == "schleife":
            g.plan_schleife_setzen(el.an)
        elif el.name.startswith("r:"):
            schluessel = el.name[2:]
            wert = el.an if isinstance(el, ui.Schalter) else el.wert
            g.plan_verstellen(self.nr, schluessel, wert)
        self.aufbauen()

    def schritt(self, dt: float) -> None:
        super().schritt(dt)
        # Der Plan kann sich von aussen aendern: beim Gast kommt ein neuer
        # vom Gastgeber, beim Gastgeber startet vielleicht gerade eine Runde.
        # Ebenso der Ladestand der Kosmetik, an dem der Startknopf haengt.
        kos = (bool(self.gefecht.kos_index), self.gefecht.kosmetik_stand())
        if self._stand != self.gefecht.plan_stand or kos != getattr(
                self, "_kos_alt", kos):
            self.aufbauen()
        self._kos_alt = kos

    def taste(self, ev) -> None:
        if ev.key in self.app.opt.codes("planen"):
            self.zurueck()
            return
        super().taste(ev)

    # ---- Bild --------------------------------------------------------
    def zeichnen(self, ziel, alpha: float) -> None:
        if not self.oben_auf:
            return
        # Leichter als die anderen Menues: man soll die Lobby darunter
        # noch erkennen - sie laeuft ja weiter.
        ui.schleier(ziel, 150)
        self.rahmen_zeichnen(ziel)
        for i, el in enumerate(self.elemente):
            el.ueber = (i == self.wahl) and not el.gesperrt
            el.zeichnen(ziel)
        self.inhalt_zeichnen(ziel)
        self.fuss_zeichnen(ziel)

    def inhalt_zeichnen(self, ziel) -> None:
        g = self.gefecht
        r = self.tafel
        # Welche Runde gerade eingestellt wird, als Ueberschrift der Regeln.
        if g.plan_offen:
            x = r.x + 196
            SCHRIFT.zeichnen(ziel, "RUNDENPLAN", r.x + 16, r.y + 46,
                             K.C_MUTED_DK, 1)
            # Die gewaehlte Runde in der Liste markieren.
            for el in self.elemente:
                if el.name == "runde:%d" % self.nr:
                    pygame.draw.rect(ziel, K.C_AMBER, el.rect, 1)
        else:
            x = r.x + 100
        titel = ("RUNDE %d VON %d" % (self.nr + 1, len(g.plan))
                 if len(g.plan) > 1 else "NÄCHSTE RUNDE")
        SCHRIFT.zeichnen(ziel, titel, x, r.y + 46, K.C_AMBER, 1)
        # Was die gewaehlte Zeile bedeutet.
        el = self.gewaehlt()
        hilfe = ""
        if el is not None and el.name.startswith("r:"):
            f = R.NACH_NAME.get(el.name[2:])
            hilfe = f.hilfe if f is not None else ""
        elif el is not None and el.name == "start":
            hilfe = ("STARTET RUNDE 1 - DANACH DIE NÄCHSTE IM PLAN"
                     if len(g.plan) > 1 else "STARTET DIE RUNDE FÜR ALLE")
        elif el is not None and el.name == "planen":
            hilfe = "MEHRERE RUNDEN HINTEREINANDER, SCHLEIFE, KOPIEREN"
        elif el is not None and el.name == "ansicht":
            hilfe = ("NUR DAS WICHTIGSTE ZEIGEN" if self.erweitert
                     else "ALLE REGELN: MUNITION, MEDKITS, SCHUTZ, RAKETEN ...")
        elif el is not None and el.name == "standard":
            hilfe = "%s - FÜR DEN ANFANG DAS RICHTIGE" % R.kurz(
                R.standardrunde(g._umfeld()), g._umfeld())
        elif el is not None and el.name == "start_mit":
            hilfe = "BLENDGRANATEN KLINGEN UND AUSSEHEN WIE VOM WERFER GEMACHT"
        elif el is not None and el.name == "start_ohne":
            hilfe = "ALLE BLENDGRANATEN WIE IMMER"
        if not self.darf:
            hilfe = hilfe or "NUR DER GASTGEBER KANN HIER ETWAS ÄNDERN"
        if hilfe:
            SCHRIFT.zeichnen(ziel, ui.kuerzen(hilfe, r.width - 32), r.centerx,
                             r.bottom - 34, K.C_MUTED, 1, ausrichtung="mitte")
        if not self.erweitert:
            # Was unter ERWEITERT verstellt ist, soll man auch in der
            # einfachen Ansicht erfahren.
            anders = R.verborgen_geaendert(g.plan[self.nr], g._umfeld())
            if anders:
                text = "UNTER ERWEITERT VERSTELLT: " + ", ".join(
                    f.name(g.plan[self.nr]).strip() for f in anders[:3])
                if len(anders) > 3:
                    text += " +%d" % (len(anders) - 3)
                SCHRIFT.zeichnen(ziel, ui.kuerzen(text, r.width - 40),
                                 r.centerx, r.bottom - 76, K.C_AMBER, 1,
                                 ausrichtung="mitte")

    def fusstext(self) -> str:
        return "[MAUS] ODER [PFEILE] EINSTELLEN   [P] / [ESC] ZURÜCK"
