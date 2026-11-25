"""
DUSTFRONT - Uebersicht der Klaenge als PDF (seit 0.34.154)
==========================================================

Gewuenscht: "eine Uebersicht fuer die noetigen Platzhalter, also fuer die
noetigen Sounddateien ... als Datei, vielleicht PDF". Dieses Werkzeug liest
die Namen aus K.KLANG_NAMEN, fragt das Spiel, welcher Name gerade aus einer
Datei kommt (wie `python -m dustfront --assets`), und schreibt
docs/KLAENGE_UEBERSICHT.pdf: je Name, wann er spielt, wohin die Datei gehoert,
was sie koennen sollte und wie dringend sie ist.

    pip install reportlab
    python tools/klang_uebersicht.py

Die Beschreibungen stehen unten in BESCHREIBUNG. Kommt ein neuer Name in
K.KLANG_NAMEN, ohne dass er hier steht, erscheint er trotzdem - mit dem
Vermerk, dass die Beschreibung fehlt.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from dustfront import config as K  # noqa: E402

# Prioritaet: A = staendig zu hoeren (jede Runde, oft), B = regelmaessig,
# C = selten oder nur Zierde. Gruppe ordnet die Tabelle.
# name: (Gruppe, Prioritaet, wann er spielt, was die Aufnahme koennen sollte)
BESCHREIBUNG = {
    # ---- Schusswaffen ----
    "schuss": ("Schusswaffen", "A", "Rückfall für jede Schusswaffe ohne eigene Datei",
               "Neutraler Gewehrschuss, kurz (0,3–0,6 s), 3+ Fassungen"),
    "schuss_repetierer": ("Schusswaffen", "A", "Repetierer", "Kräftiger Einzelschuss mit Hall"),
    "schuss_sturm": ("Schusswaffen", "A", "Sturmgewehr, je Kugel", "Sehr kurz (< 0,15 s), trocken, 4+ Fassungen für Dauerfeuer"),
    "schuss_schrot": ("Schusswaffen", "A", "Schrotflinte", "Breiter Knall, tiefer Anteil"),
    "schuss_scharf": ("Schusswaffen", "A", "Scharfschützengewehr", "Lauter Knall mit langem Nachhall"),
    "lmg_salve": ("Schusswaffen", "A", "MG, Salve", "Kurze Salve, schneidbar"),
    "lmg_dauer": ("Schusswaffen", "A", "MG im Dauerfeuer (je Kugel)", "Sehr kurz, 4+ Fassungen"),
    "schuss_revolver": ("Schusswaffen", "B", "Revolver", "Satter Einzelknall"),
    "schuss_mp": ("Schusswaffen", "A", "Maschinenpistole, je Kugel", "Heller, kurzer Knall, 4+ Fassungen"),
    "schuss_minigun": ("Schusswaffen", "B", "Minigun (gerufene Waffe), je Kugel", "Sehr kurz, sägend; ideal: Anlauf-Surren getrennt"),
    "schuss_panzerbuechse": ("Schusswaffen", "B", "Panzerbüchse (gerufene Waffe)", "Schwerer Knall, metallisch, lang"),
    "schuss_doppelflinte": ("Schusswaffen", "B", "Doppelflinte", "Wie Schrot, etwas trockener"),
    "schuss_granatwerfer": ("Schusswaffen", "B", "Granatwerfer, Abschuss", "Dumpfes ‚Plopp‘"),
    "schuss_bolzer": ("Schusswaffen", "C", "Bolzenschussgerät", "Pneumatischer Schlag"),
    "schuss_nagler": ("Schusswaffen", "C", "Nagler, je Nagel", "Kurzes ‚Tack‘, 3+ Fassungen"),
    "reload": ("Schusswaffen", "A", "Nachladen beginnt", "Magazin raus/rein, 0,5–1 s"),
    # ---- Chor-Waffen (Energie) ----
    "schuss_spule": ("Chor-Waffen", "B", "Spulengewehr, Schuss", "Elektrischer Knall mit Zischen"),
    "spule_laden": ("Chor-Waffen", "B", "Spulengewehr lädt auf", "Ansteigendes Summen, 0,5–1 s"),
    "schuss_kettenblitz": ("Chor-Waffen", "B", "Kettenblitz", "Knisternder Überschlag"),
    "schuss_spiegellaser": ("Chor-Waffen", "B", "Spiegellaser", "Heller, sirrender Strahl"),
    "schuss_kugelblitz": ("Chor-Waffen", "C", "Kugelblitz, Abschuss", "Brummende Kugel"),
    "plasma": ("Chor-Waffen", "C", "Kugelblitz platzt", "Elektrischer Puff"),
    "ueberhitzt": ("Chor-Waffen", "B", "Chor-Waffe und Fahrzeug-MG überhitzen", "Zischen + Klicken, Abkühlen"),
    # ---- Nahkampf ----
    "nahkampf": ("Nahkampf", "B", "Nahkampf allgemein", "Kurzer Schlag"),
    "nahkampf_schwung": ("Nahkampf", "B", "Brecheisen verfehlt (Ordner nahkampf/into_air)", "Luftzug"),
    "nahkampf_treffer_organisch": ("Nahkampf", "B", "Brecheisen trifft Figur (nahkampf/hit_organic)", "Dumpfer Treffer"),
    "nahkampf_treffer_metall": ("Nahkampf", "C", "Brecheisen trifft Boss (nahkampf/hit_metal)", "Metallischer Schlag"),
    "kettensaege": ("Nahkampf", "C", "Kettensäge", "Motor + Schneiden, schleifbar"),
    "hammer_boden": ("Nahkampf", "C", "Vorschlaghammer, Bodenschlag", "Schwerer Aufschlag mit Bodenbeben"),
    "schock": ("Nahkampf", "C", "Schockstab", "Elektrischer Schlag"),
    "schlag_faust": ("Nahkampf", "C", "Schlagring", "Faustschlag"),
    # ---- Würfe und Explosionen ----
    "wurf": ("Würfe & Explosionen", "A", "Granate verlässt die Hand", "Kurzer Wurf-Luftzug"),
    "wurf_leise": ("Würfe & Explosionen", "C", "Wurfmesser, Speer", "Leises Sirren"),
    "granate": ("Würfe & Explosionen", "A", "Granate explodiert", "Explosion mittel, 1–1,5 s"),
    "c4_explosion": ("Würfe & Explosionen", "B", "C4", "Große Explosion"),
    "molotov": ("Würfe & Explosionen", "B", "Molotow zerbricht und zündet", "Glas + Aufflammen"),
    "molotov_glass": ("Würfe & Explosionen", "B", "Molotow: Glas (Ordner molotov/glass_shatter)", "Glasbruch"),
    "molotov_whoosh": ("Würfe & Explosionen", "B", "Molotow: Feuer (molotov/fire_whoosh)", "Aufflammen, lodern"),
    "smoke_grenade": ("Würfe & Explosionen", "B", "Rauchgranate zündet", "Zischender Gasstrom"),
    "blend": ("Würfe & Explosionen", "B", "Blendgranate knallt", "Sehr heller Knall"),
    "blend_pfeifen": ("Würfe & Explosionen", "B", "Pfeifen im Ohr danach", "Tinnitus-Ton, 2–3 s, ausblendend"),
    "knaller": ("Würfe & Explosionen", "C", "Böller", "Kleiner Knall"),
    "emp": ("Würfe & Explosionen", "C", "EMP-Granate entlädt", "Elektrischer Puls, tief"),
    "piepen": ("Würfe & Explosionen", "C", "Haftladung piept", "Kurzes Piepen"),
    "klebt": ("Würfe & Explosionen", "C", "Haftladung klebt fest", "Saugendes ‚Klack‘"),
    "gas": ("Würfe & Explosionen", "C", "Gasgranate", "Ausströmendes Gas"),
    "schneeball": ("Würfe & Explosionen", "C", "Schneeball trifft", "Weicher Platsch"),
    "nagel_wand": ("Würfe & Explosionen", "C", "Nagel schlägt in Wand", "Holz-/Metall-Tack"),
    "rakete": ("Würfe & Explosionen", "B", "Raketenwerfer, Abschuss", "Zischen + Knall"),
    "erfasst": ("Würfe & Explosionen", "C", "Gelenkte Rakete hat Ziel erfasst", "Kurzer Ton/Piepton"),
    "einschlag": ("Würfe & Explosionen", "B", "Rakete oder Bombe schlägt ein", "Schwere Explosion"),
    # ---- Fahrzeuge ----
    "buggy_motor": ("Fahrzeuge", "A", "Motor Buggy, in einem Takt solange er fährt", "Kurzes Motorstück 0,3–0,5 s, schleifbar, 3 Fassungen"),
    "krad_motor": ("Fahrzeuge", "A", "Motor Krad", "Heller, knatternder Zweitakter-Takt"),
    "lkw_motor": ("Fahrzeuge", "A", "Laster: Tross-, Spulen-, Funkwagen, Werfer", "Tiefer Diesel-Takt"),
    "panzer_motor": ("Fahrzeuge", "A", "Panzer: Motor und Ketten", "Tiefes Brummen + Kettenrasseln"),
    "panzerwagen_motor": ("Fahrzeuge", "A", "Panzerwagen, Jagdpanzer, Flakwagen", "Schwerer Diesel"),
    "rotor": ("Fahrzeuge", "B", "Tragschrauber", "Rotorschlag, schleifbar"),
    "buggy_tuer": ("Fahrzeuge", "A", "Einsteigen/Aussteigen, Abwurf setzt auf", "Autotür"),
    "buggy_aufprall": ("Fahrzeuge", "B", "Wagen rumst; Jagdkanone prallt ab (seit 0.34.154)", "Blech-Rums; eigener Abprall-Klang wäre schön"),
    "rammen": ("Fahrzeuge", "B", "Fahrzeug rammt jemanden; Werfer-Stützen setzen auf", "Dumpfer Stoß"),
    "schuss_kanone": ("Fahrzeuge", "A", "Panzer- und Jagdpanzerkanone", "Sehr schwerer Knall, Druckwelle"),
    "schuss_bug_mg": ("Fahrzeuge", "A", "Bug-MG des Panzers, je Kugel", "Kurz, tief, 4+ Fassungen"),
    "schuss_ring_mg": ("Fahrzeuge", "A", "Ring-MG des Panzerwagens, je Kugel", "Kurz, 4+ Fassungen"),
    "schuss_flak_kanone": ("Fahrzeuge", "B", "Flak-Vierling", "Schnelles, hartes Bellen"),
    "flak_burst": ("Fahrzeuge", "B", "Flakwolke platzt", "Dumpfer Luftknall"),
    "panzer_einschlag": ("Fahrzeuge", "A", "Granate der Kanone schlägt ein", "Explosion + Metall"),
    "werfer_start": ("Fahrzeuge", "B", "Rakete des Werfers startet", "Fauchen"),
    "werfer_anflug": ("Fahrzeuge", "B", "Werferrakete heult herab", "Heulen, ~1 s"),
    "werfer_explosion": ("Fahrzeuge", "C", "Werfer geht hoch", "Große Explosion mit Nachknallen"),
    "absturz": ("Fahrzeuge", "C", "Fahrzeug schlägt nach Sturz auf", "Schwerer Aufschlag, Blech"),
    "reifen_platt": ("Fahrzeuge", "C", "Reifen platzt (Krähenfüße/Nägel)", "Knall + Zischen"),
    "emp_aus": ("Fahrzeuge", "C", "Fahrzeug fällt durch EMP aus", "Motor stirbt ab"),
    # ---- Luft und Nachschub ----
    "anflug": ("Luft & Nachschub", "B", "Flugzeug: Abwurf, Aufklärungsdrohne", "Vorbeiflug, 2–3 s"),
    "jet": ("Luft & Nachschub", "B", "Napalm-Bomber zieht über die Karte", "Jet-Vorbeiflug, 3–4 s"),
    "bomber": ("Luft & Nachschub", "B", "Triebwerk des Napalm-Bombers", "Dröhnendes Triebwerk, schleifbar"),
    "napalm_fall": ("Luft & Nachschub", "B", "Napalmbombe pfeift im Fall", "Fallendes Pfeifen ~1 s"),
    "napalm": ("Luft & Nachschub", "B", "Napalmbombe schlägt auf und brennt", "Wummern + Feuer"),
    "fallschirm_riss": ("Luft & Nachschub", "C", "Schirm eines Abwurfs reißt", "Stoffriss"),
    "bombe_ab": ("Luft & Nachschub", "C", "Lunte der Schrottbombe gezündet", "Zünden, Zischen"),
    "bombe_fall": ("Luft & Nachschub", "C", "Zischende Lunte der fallenden Bombe", "Zischen, schleifbar"),
    "drohne": ("Luft & Nachschub", "C", "Spähdrohne, Tragschrauber hebt ab", "Surren"),
    "funk_durch": ("Luft & Nachschub", "C", "Funkspruch durch", "Funk-Knacken"),
    # ---- Figur ----
    "sturz": ("Figur", "B", "Aufsetzen nach einem Fall", "Dumpfer Aufprall"),
    "platsch": ("Figur", "C", "Ins tiefe Wasser", "Platschen"),
    "dash": ("Figur", "A", "Dash", "Kurzer Luftstoß"),
    "medkit": ("Figur", "B", "Medkit angelegt", "Verband/Reißverschluss"),
    "aufheben": ("Figur", "A", "Etwas aufgehoben (Beute, Waffe, Kiste)", "Kurzes Klicken"),
    "downed_not_dead": ("Figur", "B", "Spieler fällt zu Boden", "Stöhnen/Treffer"),
    "tod": ("Figur", "B", "Jemand stirbt", "Kurz, nicht drastisch"),
    "ruf": ("Figur", "B", "Am Boden: Ruf nach Hilfe", "Kurzer Ruf"),
    "herzschlag": ("Figur", "B", "Eigener Herzschlag bei wenig Leben", "Ein Schlag, ~0,4 s"),
    "trefferzeichen": ("Figur", "A", "Eigener Treffer", "Sehr kurzes ‚Tick‘"),
    "trefferzeichen_toedlich": ("Figur", "A", "Eigener Treffer, der erledigt", "Tick mit mehr Gewicht"),
    "schild": ("Figur", "C", "Kugel trifft Schild", "Metall-Ping"),
    "schild_durch": ("Figur", "C", "Schild durchschlagen", "Brechen"),
    # ---- Gegner und Ausrüstung ----
    "speien": ("Gegner & Ausrüstung", "C", "Speier spuckt", "Schleimiges Spucken"),
    "boss_ansage": ("Gegner & Ausrüstung", "C", "Boss kündigt Angriff an", "Brüllen/Grollen"),
    "falle_klick": ("Gegner & Ausrüstung", "C", "Sprengfalle ausgelöst", "Klick"),
    "horchposten": ("Gegner & Ausrüstung", "C", "Horchposten meldet", "Piep/Funkton"),
    "flammenwerfer": ("Gegner & Ausrüstung", "B", "Flammenwerfer (gerufene Waffe)", "Fauchen, schleifbar"),
    # ---- Runde und Menü ----
    "rundenstart": ("Runde & Menü", "B", "Runde beginnt", "Signal, 1–2 s"),
    "won_match": ("Runde & Menü", "B", "Match gewonnen", "Jingle"),
    "lost_match": ("Runde & Menü", "B", "Match verloren", "Jingle"),
    "menue": ("Runde & Menü", "B", "Auswahl im Menü wandert", "Sehr kurzes Klicken"),
    "menue_ok": ("Runde & Menü", "B", "Auswahl bestätigt", "Kurzer Bestätigungston"),
}

GRUPPEN = ("Schusswaffen", "Chor-Waffen", "Nahkampf", "Würfe & Explosionen", "Fahrzeuge",
           "Luft & Nachschub", "Figur", "Gegner & Ausrüstung", "Runde & Menü", "Ohne Beschreibung")

# Klaenge, die (noch) einen anderen Namen mitbenutzen - eigene Dateien
# waeren hier am deutlichsten zu hoeren. (Wunschname, benutzt jetzt, wann)
MITBENUTZT = (
    ("jagd_abprall", "buggy_aufprall", "Granate der Jagdkanone prallt von einer Wand ab (seit 0.34.154)"),
    ("stuetze_auf", "rammen", "Werfer setzt beim Aufbauen seine Stützen auf (seit 0.34.154)"),
    ("mg_heiss", "ueberhitzt", "Fahrzeug-MG überhitzt (seit 0.34.154)"),
    ("kapsel_fall", "werfer_anflug", "Die Abwurfkapsel heult herab (seit 0.34.155)"),
    ("kapsel_einschlag", "einschlag + buggy_aufprall", "Die Kapsel schlaegt ein (seit 0.34.155)"),
    ("kapsel_auf", "knaller + aufheben", "Die Kapsel sprengt ihre Klappen ab (seit 0.34.155)"),
    ("jagd_durch", "buggy_aufprall", "Die Jagdkanone schlaegt durch Blech (seit 0.34.155)"),
)


def herkunft() -> set:
    """Welche Namen gerade aus einer Datei kommen (wie --assets)."""
    from dustfront.audio import Klaenge
    from dustfront.main import asset_ordner
    klaenge = Klaenge(asset_ordner())
    for name in K.KLANG_NAMEN:
        klaenge.klang(name)
    return set(klaenge.aus_datei)


def schreiben(ziel: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                    TableStyle, PageBreak)

    aus_datei = herkunft()
    stile = getSampleStyleSheet()
    klein = ParagraphStyle("klein", parent=stile["BodyText"], fontSize=7.6, leading=9.2)
    fett = ParagraphStyle("fett", parent=klein, fontName="Helvetica-Bold")
    titel = ParagraphStyle("titel", parent=stile["Title"], fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=stile["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4,
                        keepWithNext=1)
    text = ParagraphStyle("text", parent=stile["BodyText"], fontSize=9, leading=12)

    version = ""
    try:
        import rustfront_menu  # noqa: F401
        version = getattr(sys.modules["rustfront_menu"], "VERSION", "")
    except Exception:  # noqa: BLE001  ohne Menue: ohne Version
        version = ""

    namen = list(K.KLANG_NAMEN)
    datei_n = sum(1 for n in namen if n in aus_datei)
    teile = [
        Paragraph("DUSTFRONT – Übersicht der Klänge", titel),
        Paragraph("Stand: Version %s · %d Namen · %d aus Dateien · %d noch Platzhalter (im Code erzeugt)"
                  % (version or "?", len(namen), datei_n, len(namen) - datei_n), text),
        Spacer(1, 4 * mm),
        Paragraph("<b>Wohin die Dateien gehören:</b> je Name ein Ordner <font face='Courier'>assets/sfx/&lt;name&gt;/</font>, "
                  "Dateiname frei, WAV/OGG/MP3. Mehrere Dateien im Ordner werden zufällig abgewechselt "
                  "(für Dauerfeuer und Motoren 3–4 Fassungen). Ein Name mit Ordner in Klammern liegt in einem "
                  "Unterordner (K.KLANG_ORDNER). Prüfen: <font face='Courier'>python -m dustfront --assets</font>, "
                  "Anhören: <font face='Courier'>python tools/soundboard.py</font>.", text),
        Paragraph("<b>Priorität:</b> A = in jeder Runde ständig zu hören (zuerst ersetzen), "
                  "B = regelmäßig, C = selten oder Zierde. <b>Status:</b> DATEI = es gibt schon eine "
                  "Aufnahme (vorläufig, Rechte vor dem Release prüfen), PLATZHALTER = im Code erzeugt.", text),
        Spacer(1, 3 * mm),
    ]
    # Kurzliste: was am dringendsten fehlt
    dringend = [n for n in namen if n not in aus_datei and BESCHREIBUNG.get(n, ("", "C"))[1] == "A"]
    teile.append(Paragraph("Zuerst gebraucht (Priorität A, noch Platzhalter): %d" % len(dringend), h2))
    teile.append(Paragraph(", ".join("<font face='Courier'>%s</font>" % n for n in dringend), text))

    nach_gruppe = {}
    for n in namen:
        gruppe = BESCHREIBUNG.get(n, ("Ohne Beschreibung",))[0]
        nach_gruppe.setdefault(gruppe, []).append(n)
    breiten = [44 * mm, 14 * mm, 24 * mm, 84 * mm, 101 * mm]
    for gruppe in GRUPPEN:
        liste = nach_gruppe.get(gruppe)
        if not liste:
            continue
        teile.append(Paragraph(gruppe, h2))
        zeilen = [[Paragraph(x, fett) for x in ("Name / Ordner", "Prio", "Status", "Wann er spielt",
                                                "Was die Aufnahme können sollte")]]
        stil = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9a8a70")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8dcc4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP")]
        liste.sort(key=lambda n: (BESCHREIBUNG.get(n, ("", "C"))[1], n))
        for i, n in enumerate(liste, start=1):
            _g, prio, wann, wunsch = BESCHREIBUNG.get(n, ("", "?", "Beschreibung fehlt", ""))
            ordner = K.KLANG_ORDNER.get(n, n)
            datei = n in aus_datei
            zeilen.append([Paragraph("<font face='Courier'>%s</font>%s" % (
                n, "" if ordner == n else "<br/>(%s/)" % ordner), klein),
                Paragraph(prio, klein),
                Paragraph("DATEI" if datei else "PLATZHALTER", klein),
                Paragraph(wann, klein), Paragraph(wunsch, klein)])
            if datei:
                stil.append(("BACKGROUND", (2, i), (2, i), colors.HexColor("#cfe8c8")))
            elif prio == "A":
                stil.append(("BACKGROUND", (2, i), (2, i), colors.HexColor("#f4c9b8")))
        t = Table(zeilen, colWidths=breiten, repeatRows=1)
        t.setStyle(TableStyle(stil))
        teile.append(t)

    teile.append(PageBreak())
    teile.append(Paragraph("Mitbenutzte Klänge – eigene Dateien wären hier deutlich zu hören", h2))
    teile.append(Paragraph("Diese Ereignisse spielen zur Zeit einen anderen Namen ab. Für eine eigene "
                           "Aufnahme muss der Name im Code (effekte.py, ARTEN) und in K.KLANG_NAMEN "
                           "eingetragen werden – Bescheid geben, dann wird er angelegt.", text))
    zeilen = [[Paragraph(x, fett) for x in ("Wunschname", "benutzt jetzt", "Wann")]]
    for wunsch, jetzt, wann in MITBENUTZT:
        zeilen.append([Paragraph("<font face='Courier'>%s</font>" % wunsch, klein),
                       Paragraph("<font face='Courier'>%s</font>" % jetzt, klein), Paragraph(wann, klein)])
    t = Table(zeilen, colWidths=[50 * mm, 50 * mm, 167 * mm], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9a8a70")),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8dcc4")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    teile.append(t)
    teile.append(Spacer(1, 4 * mm))
    teile.append(Paragraph("Tipps für die Aufnahmen", h2))
    for satz in (
            "Pegel: Spitzen um −1 dBFS, keine Stille am Anfang (das Spiel spielt sofort ab; sonst kommt der Knall zu spät).",
            "Schüsse im Dauerfeuer (Sturmgewehr, MP, MGs, Minigun) je Kugel: sehr kurz, damit sie sich nicht stapeln; 3–4 Fassungen.",
            "Motoren: kurze Stücke von 0,3–0,5 s, die im Takt wiederholt werden (K.FAHRZEUG motor_takt) – keine langen Schleifen.",
            "Explosionen dürfen länger sein (1–2 s); das Spiel dämpft automatisch, wenn es einem schlecht geht (außer Herzschlag und Menü).",
            "Rechte: Die vorhandenen MP3s sind vorläufige Playtest-Aufnahmen – vor dem Release Quelle und Lizenz prüfen."):
        teile.append(Paragraph("• " + satz, text))

    doc = SimpleDocTemplate(str(ziel), pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm,
                            title="DUSTFRONT – Übersicht der Klänge", author="DUSTFRONT")
    doc.build(teile)


def main() -> int:
    ziel = WURZEL / "docs" / "KLAENGE_UEBERSICHT.pdf"
    try:
        schreiben(ziel)
    except ImportError:
        print("Dafuer braucht es reportlab:  pip install reportlab")
        return 1
    print("Geschrieben: %s" % ziel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
