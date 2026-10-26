"""
Rutas y constantes de IKA.

Todo se resuelve relativo a la raíz de la app (la carpeta que contiene
iniciar.bat), así funciona igual desde el disco o desde una USB.
La variable de entorno IKA_RAIZ permite apuntar a otra carpeta (pruebas).
"""
import os
import sys
from pathlib import Path


def _raiz() -> Path:
    if os.environ.get("IKA_RAIZ"):
        return Path(os.environ["IKA_RAIZ"]).resolve()
    if getattr(sys, "frozen", False):
        # <raiz>/app/IKA.exe
        return Path(sys.executable).resolve().parent.parent
    return Path(__file__).resolve().parent.parent


def _recursos() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


RAIZ = _raiz()
RECURSOS = _recursos()

DATA_DIR = RAIZ / "data"
BACKUPS_DIR = RAIZ / "backups"
DOCS_DIR = RAIZ / "documentos"

DB_PATH = DATA_DIR / "ika.db"
SCHEMA_PATH = RECURSOS / "backend" / "schema.sql" if not getattr(sys, "frozen", False) else RECURSOS / "schema.sql"
FRONTEND_DIR = RECURSOS / "frontend"
LOGO_DEFAULT = FRONTEND_DIR / "img" / "logo-mr.png"

PUERTO = int(os.environ.get("IKA_PUERTO", 4580))
MAX_BACKUPS = 15
INTERVALO_BACKUP_MINUTOS = 15

for _d in (DATA_DIR, BACKUPS_DIR, DOCS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
