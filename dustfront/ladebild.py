"""
DUSTFRONT - Ladebild fuer cloudflared (seit 0.34.150)
====================================================

Gewuenscht: "Cloudflared soll beim Online-Spiel das ganze laden, mit
Loading Screen mit Fortschrittsbalken." Bis 0.34.149 lag cloudflared fuer
drei Systeme im Spiel bei (58 MB); jetzt laedt online.Lader beim ersten
Spiel ueber das Internet genau das eine, das gebraucht wird.

Das Ladebild liegt ueber der Lobby (Gastgeber) oder der Lobbysuche (Gast)
und zeigt nur, wie weit es ist. Warten tun Tunnel und Zugang selbst
(online.py, Zustand "laedt") - das Bild kann also fehlen (Pruefungen, Start
ueber die Kommandozeile), und alles laeuft trotzdem. ESC bricht ab; dann
steht der Grund dort, wo sonst der Code steht.
"""

from __future__ import annotations

import pygame

from . import config as K
from . import online
from . import ui
from .core import Szene
from .font import SCHRIFT


def zeigen_wenn_noetig(app) -> "Ladebild | None":
    """Das Ladebild oben auflegen, wenn cloudflared gerade geladen wird
    und es nicht schon liegt."""
    l = online.lader()
    if l is None or not l.laeuft or isinstance(getattr(app, "oben", None), Ladebild):
        return None
    bild = Ladebild(app, l)
    app.schieben(bild)
    return bild


class Ladebild(Szene):
    """Balken, Megabytes und ESC zum Abbrechen."""

    deckt_zu = False             # die Lobby darunter bleibt zu sehen

    def __init__(self, app, lader: online.Lader) -> None:
        super().__init__(app)
        self.lader = lader
        self.zeit = 0.0

    def ereignis(self, ev) -> None:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.lader.abbrechen()

    def schritt(self, dt: float) -> None:
        self.zeit += dt
        if not self.lader.laeuft and self.app.oben is self:
            # Fertig oder gescheitert: weg. Den Grund zeigt, wer wartet.
            self.app.werfen()

    def zeichnen(self, ziel, alpha: float) -> None:
        ui.schleier(ziel, 150)
        w, h = ziel.get_size()
        r = pygame.Rect(0, 0, 300, 92)
        r.center = (w // 2, h // 2)
        ui.tafel(ziel, r, "ONLINE")
        l = self.lader
        SCHRIFT.zeichnen(ziel, "CLOUDFLARED WIRD GELADEN", r.centerx, r.y + 14,
                         K.C_AMBER, 1, ausrichtung="mitte")
        SCHRIFT.zeichnen(ziel, "NUR BEIM ERSTEN SPIEL ÜBER DAS INTERNET", r.centerx,
                         r.y + 26, K.C_MUTED, 1, ausrichtung="mitte")
        balken = pygame.Rect(r.x + 18, r.y + 42, r.width - 36, 12)
        ui.kasten(ziel, balken, K.C_MUTED_DK, (12, 9, 7), 2)
        innen = balken.inflate(-4, -4)
        if l.gesamt:
            voll = int(innen.width * l.anteil)
            if voll > 0:
                pygame.draw.rect(ziel, K.C_AMBER, (innen.x, innen.y, voll, innen.height))
            text = "%.1f VON %.1f MB" % (l.geladen / 1e6, l.gesamt / 1e6)
        else:
            # Die Groesse ist noch unbekannt: ein wandernder Block statt Stillstand.
            breite = max(8, innen.width // 6)
            x = innen.x + int((self.zeit * 90) % (innen.width + breite)) - breite
            teil = pygame.Rect(x, innen.y, breite, innen.height).clip(innen)
            pygame.draw.rect(ziel, K.C_AMBER, teil)
            text = "VERBINDET ..."
        SCHRIFT.zeichnen(ziel, text, r.centerx, r.y + 60, K.C_MUTED, 1, ausrichtung="mitte")
        SCHRIFT.zeichnen(ziel, "[ESC] ABBRECHEN", r.centerx, r.y + 74, K.C_MUTED_DK, 1,
                         ausrichtung="mitte")
