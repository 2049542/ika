"""
`IKA.exe --desinstalar` (acceso "Desinstalar IKA" del menú Inicio).

Quita el programa y sus accesos directos. La base de datos, los backups y los
PDF NO se borran: se avisa dónde quedan por si se reinstala o se respaldan.
"""
import subprocess
import sys

import accesos
from config import CONGELADO, DOCS_DIR, EXE_DIR, RAIZ


def main():
    if not accesos.mensaje("¿Quitar IKA de este equipo?\n\nTus cotizaciones, clientes y PDF se conservan.", pregunta=True):
        return
    accesos.quitar_accesos()
    if CONGELADO and EXE_DIR:
        # El .exe no puede borrarse a sí mismo mientras corre: lo hace cmd al salir.
        subprocess.Popen(
            f'cmd /c ping -n 3 127.0.0.1 >nul & rmdir /s /q "{EXE_DIR}"',
            creationflags=accesos.SIN_VENTANA, close_fds=True,
        )
    accesos.mensaje(
        "IKA se quitó de este equipo.\n\n"
        f"Tus datos siguen en:\n{RAIZ}\n\nTus PDF siguen en:\n{DOCS_DIR}\n\n"
        "Si vuelves a instalar IKA, aparecerán tal como estaban."
    )
    sys.exit(0)
