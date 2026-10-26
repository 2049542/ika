"""
Rutas y constantes de IKA.

Tres modos:
  - instalado: el .exe instalado con IKA-Instalador. La base de datos y los
    backups viven en %LOCALAPPDATA%\\IKA y los PDF en Documentos\\IKA, así
    la carpeta del programa puede reemplazarse al actualizar sin tocar datos.
  - portable: el .exe con un archivo `portable.txt` al lado (USB). Todo se
    guarda junto al programa.
  - desarrollo: corriendo con Python; todo se guarda en la carpeta del repo.
La variable IKA_RAIZ fuerza una carpeta para todo (pruebas).
"""
import os
import sys
from pathlib import Path

CONGELADO = getattr(sys, "frozen", False)
EXE_DIR = Path(sys.executable).resolve().parent if CONGELADO else None


def _documentos() -> Path:
    """Carpeta Documentos real del usuario (respeta la redirección de OneDrive)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]

            # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            fid = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
            ruta = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(ruta)) == 0:
                valor = ruta.value
                ctypes.windll.ole32.CoTaskMemFree(ruta)
                return Path(valor)
        except Exception:
            pass
    return Path.home() / "Documents"


def _modo() -> str:
    if os.environ.get("IKA_RAIZ"):
        return "prueba"
    if not CONGELADO:
        return "desarrollo"
    if (EXE_DIR / "portable.txt").exists() or (EXE_DIR.parent / "portable.txt").exists():
        return "portable"
    return "instalado"


MODO = _modo()

if MODO == "prueba":
    RAIZ = Path(os.environ["IKA_RAIZ"]).resolve()
    DOCS_DIR = RAIZ / "documentos"
elif MODO == "desarrollo":
    RAIZ = Path(__file__).resolve().parent.parent
    DOCS_DIR = RAIZ / "documentos"
elif MODO == "portable":
    RAIZ = EXE_DIR.parent if (EXE_DIR.parent / "portable.txt").exists() else EXE_DIR
    DOCS_DIR = RAIZ / "documentos"
else:
    RAIZ = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "IKA"
    DOCS_DIR = _documentos() / "IKA"

# Recursos empaquetados (frontend, schema) — dentro del .exe o en el repo.
RECURSOS = Path(getattr(sys, "_MEIPASS", EXE_DIR)) if CONGELADO else Path(__file__).resolve().parent.parent

DATA_DIR = RAIZ / "data"
BACKUPS_DIR = RAIZ / "backups"
DB_PATH = DATA_DIR / "ika.db"
LOCK_PATH = DATA_DIR / "ika.lock"
LOG_PATH = DATA_DIR / "ika.log"
SCHEMA_PATH = RECURSOS / ("schema.sql" if CONGELADO else "backend/schema.sql")
FRONTEND_DIR = RECURSOS / "frontend"
LOGO_DEFAULT = FRONTEND_DIR / "img" / "logo-mr.png"

PUERTO = int(os.environ.get("IKA_PUERTO", 4580))
MAX_BACKUPS = 15
INTERVALO_BACKUP_MINUTOS = 15

for _d in (DATA_DIR, BACKUPS_DIR, DOCS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
