"""
Instalación por usuario (sin permisos de administrador): rutas, accesos
directos y mensajes. Lo comparten el instalador y el desinstalador.

Variables para pruebas: IKA_INSTALAR_EN (carpeta del programa),
IKA_ACCESOS_EN (carpeta donde van los accesos en lugar del Escritorio y el
menú Inicio) e IKA_SIN_PREGUNTAS=1 (no muestra cuadros de diálogo).
"""
import os
import subprocess
import sys
from pathlib import Path

SIN_VENTANA = 0x08000000  # CREATE_NO_WINDOW
SIN_PREGUNTAS = os.environ.get("IKA_SIN_PREGUNTAS") == "1"


def carpeta_programa() -> Path:
    if os.environ.get("IKA_INSTALAR_EN"):
        return Path(os.environ["IKA_INSTALAR_EN"])
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Programs" / "IKA"


def _powershell(script: str) -> str:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, creationflags=SIN_VENTANA,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "PowerShell falló")
    return r.stdout.strip()


def carpetas_accesos() -> tuple[Path, Path]:
    """(Escritorio, carpeta IKA del menú Inicio)."""
    if os.environ.get("IKA_ACCESOS_EN"):
        base = Path(os.environ["IKA_ACCESOS_EN"])
        return base / "Escritorio", base / "Inicio" / "IKA"
    escritorio = _powershell("[Environment]::GetFolderPath('Desktop')")
    programas = _powershell("[Environment]::GetFolderPath('Programs')")
    return Path(escritorio), Path(programas) / "IKA"


def _comillas(texto) -> str:
    return "'" + str(texto).replace("'", "''") + "'"


def crear_accesos(exe: Path):
    escritorio, inicio = carpetas_accesos()
    escritorio.mkdir(parents=True, exist_ok=True)
    inicio.mkdir(parents=True, exist_ok=True)
    accesos = [
        (escritorio / "IKA.lnk", "", "Cotizaciones y notas de entrega MR INFRATEC"),
        (inicio / "IKA.lnk", "", "Cotizaciones y notas de entrega MR INFRATEC"),
        (inicio / "Desinstalar IKA.lnk", "--desinstalar", "Quita IKA de este equipo (los datos se conservan)"),
    ]
    lineas = ["$sh = New-Object -ComObject WScript.Shell"]
    for ruta, args, desc in accesos:
        lineas += [
            f"$s = $sh.CreateShortcut({_comillas(ruta)})",
            f"$s.TargetPath = {_comillas(exe)}",
            f"$s.Arguments = {_comillas(args)}",
            f"$s.WorkingDirectory = {_comillas(exe.parent)}",
            f"$s.IconLocation = {_comillas(str(exe) + ',0')}",
            f"$s.Description = {_comillas(desc)}",
            "$s.Save()",
        ]
    _powershell("; ".join(lineas))
    return [a[0] for a in accesos]


def quitar_accesos():
    escritorio, inicio = carpetas_accesos()
    (escritorio / "IKA.lnk").unlink(missing_ok=True)
    for lnk in inicio.glob("*.lnk"):
        lnk.unlink(missing_ok=True)
    try:
        inicio.rmdir()
    except OSError:
        pass


def mensaje(texto, pregunta=False, error=False) -> bool:
    """Cuadro de diálogo de Windows. Con pregunta=True devuelve True si se eligió Sí."""
    print(texto)
    if SIN_PREGUNTAS or sys.platform != "win32":
        return True
    import ctypes
    estilo = 0x04 | 0x20 if pregunta else (0x10 if error else 0x40)  # Sí/No + ?, error o info
    respuesta = ctypes.windll.user32.MessageBoxW(None, texto, "IKA", estilo | 0x10000)  # al frente
    return respuesta == 6 if pregunta else True
