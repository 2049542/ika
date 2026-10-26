"""
IKA — servidor local + lanzador de la ventana.

Al abrir IKA:
  1. Si ya hay una IKA corriendo, solo abre otra ventana hacia ella.
  2. Si no, levanta el servidor en un puerto libre (4580 de preferencia),
     respalda la base de datos y abre la app en una ventana propia de Edge
     (modo app: sin pestañas ni barra de direcciones).
  3. Al cerrar esa ventana, el servidor hace el respaldo final y se apaga.
     Si no hay Edge, se usa el navegador predeterminado y el servidor se
     apaga cuando la página deja de dar señales de vida por unos minutos.

`--servidor` solo levanta el servidor, sin ventana (desarrollo y pruebas).
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from waitress.server import create_server

import db
from api import bp
from config import CONGELADO, DATA_DIR, DB_PATH, DOCS_DIR, FRONTEND_DIR, LOCK_PATH, LOG_PATH, MODO, PUERTO, RAIZ

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.teardown_appcontext(db.close_db)
app.register_blueprint(bp)

_ultimo_latido = [0.0]


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:ruta>")
def estaticos(ruta):
    return send_from_directory(FRONTEND_DIR, ruta, max_age=0)


@app.get("/api/ika")
def identidad():
    return jsonify({"app": "IKA", "modo": MODO, "datos": str(RAIZ), "documentos": str(DOCS_DIR)})


@app.post("/api/latido")
def latido():
    _ultimo_latido[0] = time.time()
    return "", 204


# ------------------------------------------------------------- utilidades

def _aviso(texto, error=False):
    """Mensaje visible aunque el .exe no tenga consola."""
    print(texto)
    if CONGELADO and sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, texto, "IKA", 0x10 if error else 0x40)


def _preparar_logs():
    # Sin consola (exe con --windowed) stdout/stderr son None: todo va al log.
    if sys.stdout is None or sys.stderr is None:
        log = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = log


def _responde(puerto) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/ika", timeout=1.5) as r:
            return json.load(r).get("app") == "IKA"
    except Exception:
        return False


def _instancia_activa():
    try:
        puerto = int(LOCK_PATH.read_text().strip())
    except (OSError, ValueError):
        return None
    return puerto if _responde(puerto) else None


def _puerto_libre(preferido):
    for puerto in [preferido] + list(range(preferido + 1, preferido + 20)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", puerto)) != 0:
                return puerto
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ruta_edge():
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if base:
            ruta = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if ruta.exists():
                return ruta
    return None


def abrir_ventana(url):
    """Abre IKA en ventana de app de Edge. Devuelve el proceso, o None si se usó el navegador."""
    edge = _ruta_edge()
    if edge and os.environ.get("IKA_VENTANA") != "navegador":
        perfil = DATA_DIR / "ventana"  # perfil propio: la ventana es un proceso independiente
        try:
            return subprocess.Popen([
                str(edge), f"--app={url}", f"--user-data-dir={perfil}", "--no-first-run",
                "--no-default-browser-check", "--start-maximized", "--disable-features=Translate",
            ])
        except OSError:
            pass
    webbrowser.open(url)
    return None


def _esperar_cierre(proceso):
    if proceso is not None:
        inicio = time.time()
        proceso.wait()
        if time.time() - inicio > 8:
            return
        # Edge regresó de inmediato (otra ventana con ese perfil, políticas...):
        # se sigue con el modo de latidos.
    # Navegador normal: se apaga tras 3 min sin latidos (la página manda uno
    # cada 20 s; los navegadores frenan pestañas ocultas hasta 1 por minuto).
    limite_inicial = time.time() + 120
    while True:
        time.sleep(5)
        ultimo = _ultimo_latido[0]
        if ultimo == 0 and time.time() > limite_inicial:
            return
        if ultimo and time.time() - ultimo > 180:
            return


# -------------------------------------------------------------------- main

def main():
    solo_servidor = "--servidor" in sys.argv
    _preparar_logs()
    print(f"IKA ({MODO}) · datos: {DB_PATH} · documentos: {DOCS_DIR}")

    existente = _instancia_activa()
    if existente:
        if not solo_servidor:
            abrir_ventana(f"http://127.0.0.1:{existente}/")
        return

    try:
        db.init_db()
    except Exception as e:
        _aviso(f"No se pudo abrir la base de datos en\n{DB_PATH}\n\n{e}", error=True)
        sys.exit(1)

    puerto = PUERTO if solo_servidor else _puerto_libre(PUERTO)
    try:
        servidor = create_server(app, host="127.0.0.1", port=puerto, threads=6)
    except OSError as e:
        _aviso(f"No se pudo iniciar IKA en el puerto {puerto}.\n\n{e}", error=True)
        sys.exit(1)

    LOCK_PATH.write_text(str(puerto))
    db.hacer_backup("apertura")
    db.iniciar_backup_periodico()
    url = f"http://127.0.0.1:{puerto}/"
    print(f"Servidor en {url}")

    try:
        if solo_servidor:
            servidor.run()
        else:
            threading.Thread(target=servidor.run, daemon=True).start()
            _esperar_cierre(abrir_ventana(url))
    except KeyboardInterrupt:
        pass
    finally:
        db.detener_backup_periodico()
        db.hacer_backup("cierre")
        try:
            if LOCK_PATH.read_text().strip() == str(puerto):
                LOCK_PATH.unlink()
        except OSError:
            pass
        servidor.close()
        print("IKA cerrada.")


if __name__ == "__main__":
    if "--desinstalar" in sys.argv:
        import desinstalar
        desinstalar.main()
    else:
        main()
