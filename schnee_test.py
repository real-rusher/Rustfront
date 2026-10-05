"""Eigenstaendige Schnee- und Plateau-Demo: python schnee_test.py."""

from __future__ import annotations

import random
import sys

import pygame


BREITE, HOEHE = 960, 640
WELT_W, WELT_H = 1920, 1440
SCHNEE = (202, 220, 225)
SCHNEE_HELL = (231, 242, 240)
FELS = (65, 83, 99)
FELS_DUNKEL = (36, 51, 67)
EIS = (101, 157, 177)


def baue_welt():
    """Erzeugt festes Gelaende mit lesbaren Schnee- und Felsformen."""
    welt = pygame.Surface((WELT_W, WELT_H))
    welt.fill((117, 151, 169))
    rng = random.Random(2026)
    for _ in range(700):
        x, y = rng.randrange(WELT_W), rng.randrange(WELT_H)
        farbe = rng.choice((SCHNEE, (183, 207, 216), (217, 231, 232)))
        pygame.draw.line(welt, farbe, (x, y), (x + rng.randrange(5, 32), y - 2))
    massife = [
        pygame.Rect(140, 170, 440, 330), pygame.Rect(700, 135, 510, 390),
        pygame.Rect(1340, 215, 420, 360), pygame.Rect(360, 830, 520, 370),
        pygame.Rect(1050, 850, 590, 420),
    ]
    for index, r in enumerate(massife):
        pts = [(r.x + r.width // 7, r.y), (r.right - r.width // 8, r.y + 8),
               (r.right, r.y + r.height // 3), (r.right - 14, r.bottom - r.height // 5),
               (r.x + r.width * 3 // 4, r.bottom), (r.x, r.bottom - r.height // 4),
               (r.x + 9, r.y + r.height // 3)]
        pygame.draw.polygon(welt, FELS_DUNKEL, [(x + 9, y + 18) for x, y in pts])
        pygame.draw.polygon(welt, FELS, pts)
        for i in range(5):
            yy = r.y + 66 + i * 43
            pygame.draw.line(welt, (77 + i * 3, 99 + i * 2, 115 + i),
                             (r.x + 25 + (i * 19) % 90, yy), (r.right - 28, yy - 9), 3)
        cap = [(r.x + 42, r.y + 49), (r.x + 100, r.y + 25),
               (r.x + 146, r.y + 39), (r.x + 202, r.y + 13),
               (r.x + 255, r.y + 36), (r.right - 45, r.y + 24),
               (r.right - 23, r.y + 82), (r.x + 32, r.y + 91)]
        pygame.draw.polygon(welt, (76, 112, 134), [(x, y + 11) for x, y in cap])
        pygame.draw.polygon(welt, SCHNEE_HELL, cap)
        pygame.draw.line(welt, (246, 250, 244), cap[1], cap[2], 5)
        pygame.draw.line(welt, EIS, cap[-2], cap[-1], 3)
        innen = r.inflate(-76, -105).move(0, 49)
        pygame.draw.ellipse(welt, (180, 207, 217), innen)
        pygame.draw.ellipse(welt, (218, 233, 235), innen.inflate(-10, -10))
        pygame.draw.line(welt, SCHNEE_HELL, (innen.x + 23, innen.y + 28),
                         (innen.right - 50, innen.y + 19), 4)
        # Eine schmale Rinne macht den hoeheren Plateau-Look spielbar.
        ramp = pygame.Rect(r.centerx - 32, r.bottom - 20, 64, 96)
        pygame.draw.polygon(welt, (156, 188, 201),
                            [(ramp.x, ramp.bottom), (ramp.x + 14, ramp.y),
                             (ramp.right - 13, ramp.y), (ramp.right, ramp.bottom)])
        pygame.draw.line(welt, SCHNEE_HELL, (ramp.x + 22, ramp.bottom),
                         (ramp.x + 28, ramp.y + 8), 3)
    for x, y, s in [(95, 660, 1), (620, 690, 1.2), (1270, 690, 1),
                    (1780, 760, 1.3), (275, 1320, 1.2), (900, 650, .8),
                    (1690, 120, .9), (820, 1330, 1)]:
        pygame.draw.ellipse(welt, (77, 105, 122), (x - 18*s, y + 19*s, 42*s, 14*s))
        for j, farbe in enumerate(((31, 62, 74), (42, 84, 94), (55, 105, 111))):
            pygame.draw.polygon(welt, farbe,
                [(x, y - 45*s + j*21*s), (x - (26-j*5)*s, y + j*15*s),
                 (x + (26-j*5)*s, y + j*15*s)])
        pygame.draw.line(welt, (187, 218, 218), (x - 13*s, y - 22*s),
                         (x - 3*s, y - 34*s), max(1, int(2*s)))
    return welt


def main():
    pygame.init()
    fenster = pygame.display.set_mode((BREITE, HOEHE), pygame.RESIZABLE)
    pygame.display.set_caption("DUSTFRONT | SCHNEE-GELAENDETEST")
    welt = baue_welt()
    schrift = pygame.font.Font(None, 22)
    klein = pygame.font.Font(None, 18)
    spieler = pygame.Vector2(960, 720)
    spuren = []
    schritt = 0.0
    kamera = pygame.Vector2(0, 0)
    uhr = pygame.time.Clock()
    offen = True
    while offen:
        dt = min(uhr.tick(60) / 1000.0, 0.04)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                offen = False
            elif ev.type == pygame.VIDEORESIZE:
                fenster = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
        tasten = pygame.key.get_pressed()
        richtung = pygame.Vector2(
            int(tasten[pygame.K_d] or tasten[pygame.K_RIGHT]) - int(tasten[pygame.K_a] or tasten[pygame.K_LEFT]),
            int(tasten[pygame.K_s] or tasten[pygame.K_DOWN]) - int(tasten[pygame.K_w] or tasten[pygame.K_UP]))
        if richtung.length_squared():
            richtung = richtung.normalize()
            spieler += richtung * 205 * dt
            schritt += dt * 7.0
            if schritt >= 0.15:
                schritt = 0.0
                seit = pygame.Vector2(-richtung.y, richtung.x) * 5
                for seite in (-1, 1):
                    p = spieler - richtung * 7 + seit * seite
                    spuren.append([p.x, p.y, 1.0])
        spieler.x = max(18, min(WELT_W - 18, spieler.x))
        spieler.y = max(18, min(WELT_H - 18, spieler.y))
        for spur in spuren:
            spur[2] -= dt * 0.045
        spuren = [s for s in spuren if s[2] > 0]
        breite, hoehe = fenster.get_size()
        kamera.x = max(0, min(WELT_W - breite, spieler.x - breite / 2))
        kamera.y = max(0, min(WELT_H - hoehe, spieler.y - hoehe / 2))
        fenster.blit(welt, (-int(kamera.x), -int(kamera.y)))
        for x, y, kraft in spuren:
            px, py = int(x-kamera.x), int(y-kamera.y)
            kraft = max(0.0, min(1.0, kraft))
            schatten = tuple(int(202 - (202 - c) * kraft) for c in (70, 111, 132))
            mitte = tuple(int(220 - (220 - c) * kraft) for c in (151, 183, 195))
            pygame.draw.ellipse(fenster, schatten, (px-4, py-3, 8, 6))
            pygame.draw.ellipse(fenster, mitte, (px-3, py-2, 6, 4))
            pygame.draw.line(fenster, schatten, (px-2, py), (px+2, py), 1)
        px, py = int(spieler.x-kamera.x), int(spieler.y-kamera.y)
        pygame.draw.ellipse(fenster, (49, 69, 83), (px-11, py+5, 22, 10))
        pygame.draw.circle(fenster, (31, 54, 68), (px, py), 9)
        pygame.draw.circle(fenster, (190, 213, 218), (px-2, py-3), 6)
        pygame.draw.rect(fenster, (126, 56, 43), (px-2, py-6, 7, 5))
        pygame.draw.rect(fenster, (18, 29, 39), (12, 12, 390, 78))
        pygame.draw.rect(fenster, (118, 154, 169), (12, 12, 390, 78), 1)
        fenster.blit(schrift.render("SCHNEE-FELDTEST / PLATEAU-STUDIE", False, (229, 240, 239)), (23, 20))
        fenster.blit(klein.render("WASD / PFEILE  LAUFEN     ESC  BEENDEN", False, (164, 194, 203)), (23, 46))
        fenster.blit(klein.render("Fussabdruecke verdichten Schnee und verblassen langsam", False, (164, 194, 203)), (23, 67))
        pygame.display.flip()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
