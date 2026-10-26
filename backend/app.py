"""
IKA — servidor local (Flask + waitress).

Sirve el frontend estático, la API en /api y respalda la base de datos al
abrir, cada 15 minutos y al cerrar.
"""
import atexit
import signal
import sys

from flask import Flask, send_from_directory
from waitress import serve

import db
from api import bp
from config import DB_PATH, DOCS_DIR, FRONTEND_DIR, PUERTO

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.teardown_appcontext(db.close_db)
app.register_blueprint(bp)


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:ruta>")
def estaticos(ruta):
    return send_from_directory(FRONTEND_DIR, ruta, max_age=0)


def _apagar(*_):
    db.detener_backup_periodico()
    sys.exit(0)


def main():
    print("=" * 56)
    print("  IKA - cotizaciones y notas de entrega")
    print("=" * 56)
    print(f"  Base de datos : {DB_PATH}")
    print(f"  Documentos    : {DOCS_DIR}")

    db.init_db()
    db.hacer_backup("apertura")
    db.iniciar_backup_periodico()
    atexit.register(lambda: db.hacer_backup("cierre"))
    signal.signal(signal.SIGINT, _apagar)
    try:
        signal.signal(signal.SIGTERM, _apagar)
    except (ValueError, AttributeError):
        pass

    print(f"\n  Abre http://localhost:{PUERTO}")
    print("  No cierres esta ventana mientras uses IKA.\n")
    serve(app, host="127.0.0.1", port=PUERTO, threads=6)


if __name__ == "__main__":
    main()
