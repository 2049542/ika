"""
Conexión SQLite (una por request, commit explícito) + backups automáticos.
"""
import shutil
import sqlite3
import threading
from datetime import datetime

from flask import g

from config import DB_PATH, SCHEMA_PATH, BACKUPS_DIR, MAX_BACKUPS, INTERVALO_BACKUP_MINUTOS

# Inventario inicial: solo la primera vez que se crea la base. Precios de
# referencia — se ajustan desde la pantalla de Inventario.
INVENTARIO_INICIAL = [
    # sku, nombre, tipo, categoria, unidad, costo, precio, stock, minimo
    ("PER-TEC", "Técnico instalador", "servicio", "personal", "jornada", 900, 1600, 0, 0),
    ("PER-AYU", "Ayudante general", "servicio", "personal", "jornada", 550, 950, 0, 0),
    ("PER-ING", "Ingeniero de proyecto", "servicio", "personal", "hora", 350, 650, 0, 0),
    ("PER-SUP", "Supervisión de obra", "servicio", "personal", "día", 1200, 2000, 0, 0),
    ("SRV-VIA", "Viáticos y traslado", "servicio", "otro", "servicio", 0, 850, 0, 0),
    ("SRV-PRO", "Configuración y puesta en marcha", "servicio", "otro", "servicio", 0, 1500, 0, 0),
    ("CCTV-IP4", "Cámara IP 4 MP tipo bala", "producto", "cctv", "pza", 950, 1450, 0, 4),
    ("CCTV-NVR8", "NVR 8 canales PoE", "producto", "cctv", "pza", 2600, 3900, 0, 1),
    ("RED-UTP6", "Cable UTP Cat 6 (bobina 305 m)", "producto", "red", "bobina", 2300, 3200, 0, 1),
    ("RED-SW8", "Switch PoE 8 puertos", "producto", "red", "pza", 1300, 1950, 0, 2),
    ("ENE-UPS1", "UPS 1 kVA en línea", "producto", "energia", "pza", 4200, 6100, 0, 1),
    ("ENE-BAT", "Batería 12 V 9 Ah", "producto", "energia", "pza", 380, 590, 0, 6),
]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
        g.db.execute("PRAGMA synchronous = FULL")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    nueva = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if nueva:
            conn.executemany(
                """INSERT INTO inventario (sku, nombre, tipo, categoria, unidad, costo, precio, stock, stock_minimo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                INVENTARIO_INICIAL,
            )
        conn.commit()
    finally:
        conn.close()


def config(db, clave, default=""):
    row = db.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,)).fetchone()
    return row["valor"] if row and row["valor"] is not None else default


def config_todo(db) -> dict:
    return {r["clave"]: r["valor"] for r in db.execute("SELECT clave, valor FROM configuracion")}


# ---------------------------------------------------------------- backups

_lock = threading.Lock()
_stop = threading.Event()


def hacer_backup(motivo="auto"):
    if not DB_PATH.exists():
        return None
    with _lock:
        try:
            destino = BACKUPS_DIR / f"ika_{datetime.now():%Y%m%d_%H%M%S}.db"
            src = sqlite3.connect(DB_PATH)
            dst = sqlite3.connect(destino)
            with dst:
                src.backup(dst)  # copia consistente aunque haya WAL pendiente
            src.close()
            dst.close()
            viejos = sorted(BACKUPS_DIR.glob("ika_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
            for v in viejos[MAX_BACKUPS:]:
                v.unlink(missing_ok=True)
            return destino
        except (OSError, sqlite3.Error) as e:
            print(f"[backup] no se pudo respaldar ({motivo}): {e}")
            return None


def iniciar_backup_periodico():
    def loop():
        while not _stop.wait(INTERVALO_BACKUP_MINUTOS * 60):
            hacer_backup("periodico")

    threading.Thread(target=loop, daemon=True).start()


def detener_backup_periodico():
    _stop.set()
