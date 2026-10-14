#!/usr/bin/env python3
"""Eine Attrappe von cloudflared fuer die Pruefungen (seit 0.34.13).

Benimmt sich nach aussen wie das echte Programm - dieselben Aufrufe,
dieselben Zeilen in der Ausgabe -, geht aber nicht ueber Cloudflare,
sondern bleibt auf dem Rechner:

    tunnel --url tcp://127.0.0.1:PORT
        gibt einen Code aus und meldet "Registered tunnel connection".
        Welcher Port zum Code gehoert, legt sie als Datei im Ordner
        $ATTRAPPE_ORDNER ab.
    access tcp --hostname CODE.trycloudflare.com --url 127.0.0.1:P
        lauscht auf P und reicht jede Verbindung an den Port zum Code
        weiter. Gibt es den Code nicht, schreibt sie die Fehlerzeile, die
        das echte Programm dann schreibt, und legt auf.

Damit laeuft in den Pruefungen der ganze Weg - Lobby, Code, Eingabe,
Beitritt -, nur Cloudflare selbst nicht.
"""

import os
import socket
import sys
import threading
import time

ORDNER = os.environ.get("ATTRAPPE_ORDNER", ".")
ENDUNG = ".trycloudflare.com"


def log(stufe, text):
    print("2026-01-01T00:00:00Z %s %s" % (stufe, text), flush=True)


def wert(name):
    args = sys.argv[1:]
    return args[args.index(name) + 1] if name in args else ""


def weiterreichen(a, b):
    try:
        while True:
            daten = a.recv(65536)
            if not daten:
                break
            b.sendall(daten)
    except OSError:
        pass
    for s in (a, b):
        try:
            s.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def tunnel():
    port = int(wert("--url").rsplit(":", 1)[1])
    # Englisch wie bei Cloudflare (dort z. B. "thermal-underlying-providers-toe").
    code = "sample-tunnel-for-%d" % port
    log("INF", "Requesting new quick Tunnel on trycloudflare.com...")
    time.sleep(0.2)
    log("INF", "|  https://%s%s   |" % (code, ENDUNG))
    with open(os.path.join(ORDNER, code), "w") as f:
        f.write(str(port))
    if os.environ.get("ATTRAPPE_KEIN_EDGE"):
        log("ERR", "edge discovery: error looking up Cloudflare edge IPs: "
                   "the DNS query failed")
    else:
        log("INF", "Registered tunnel connection connIndex=0 location=test protocol=http2")
    while True:
        time.sleep(1.0)


def zugang():
    code = wert("--hostname")[:-len(ENDUNG)]
    hier = wert("--url")
    port = int(hier.rsplit(":", 1)[1])
    lausch = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lausch.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lausch.bind(("127.0.0.1", port))
    lausch.listen(4)
    log("INF", "Start Websocket listener host=127.0.0.1:%d" % port)
    while True:
        verbindung, _ = lausch.accept()
        pfad = os.path.join(ORDNER, code)
        if not os.path.isfile(pfad):
            log("ERR", 'failed to connect to origin error="websocket: bad handshake" '
                       "originURL=https://%s%s" % (code, ENDUNG))
            verbindung.close()
            continue
        with open(pfad) as f:
            ziel = int(f.read().strip())
        weiter = socket.create_connection(("127.0.0.1", ziel))
        for a, b in ((verbindung, weiter), (weiter, verbindung)):
            threading.Thread(target=weiterreichen, args=(a, b), daemon=True).start()


if __name__ == "__main__":
    if sys.argv[1:2] == ["tunnel"]:
        tunnel()
    elif sys.argv[1:3] == ["access", "tcp"]:
        zugang()
    else:
        log("ERR", "unbekannter Aufruf %s" % sys.argv[1:])
        sys.exit(2)
