"""
IKA-Instalador.exe — instala IKA para el usuario actual, sin administrador.

Lleva dentro `IKA.zip` (la carpeta app/IKA que genera build.bat). Lo
descomprime en %LOCALAPPDATA%\\Programs\\IKA, crea los accesos directos en
el Escritorio y en el menú Inicio, y ofrece abrir la app. Si ya había una
versión instalada la reemplaza; los datos no se tocan porque viven en
%LOCALAPPDATA%\\IKA y Documentos\\IKA.
"""
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent / "backend"))))
import accesos  # noqa: E402

PAQUETE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent / "build")) / "IKA.zip"


def main():
    destino = accesos.carpeta_programa()
    actualizar = (destino / "IKA.exe").exists()
    pregunta = ("Ya tienes IKA instalada. ¿Actualizarla a esta versión?\n\nTus datos se conservan."
                if actualizar else
                f"Se instalará IKA (cotizaciones y notas de entrega de MR INFRATEC) en:\n{destino}\n\n¿Continuar?")
    if not accesos.mensaje(pregunta, pregunta=True):
        return

    if not PAQUETE.exists():
        accesos.mensaje("El instalador está incompleto (falta IKA.zip). Vuelve a generarlo con build.bat.", error=True)
        sys.exit(1)

    # Se descomprime aparte y luego se cambia de lugar, para no dejar una
    # instalación a medias si algo falla.
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = Path(tempfile.mkdtemp(prefix="IKA-", dir=destino.parent))
    try:
        with zipfile.ZipFile(PAQUETE) as z:
            z.extractall(temporal)
        viejo = destino.with_name("IKA-anterior")
        shutil.rmtree(viejo, ignore_errors=True)
        if destino.exists():
            try:
                destino.rename(viejo)  # falla si IKA está abierta; así no queda a medio borrar
            except PermissionError:
                accesos.mensaje("IKA está abierta. Ciérrala y vuelve a ejecutar el instalador.", error=True)
                sys.exit(1)
        temporal.rename(destino)
        shutil.rmtree(viejo, ignore_errors=True)
    finally:
        shutil.rmtree(temporal, ignore_errors=True)

    exe = destino / "IKA.exe"
    try:
        accesos.crear_accesos(exe)
    except Exception as e:
        accesos.mensaje(f"IKA se instaló, pero no se pudieron crear los accesos directos:\n{e}\n\nPuedes abrirla desde:\n{exe}", error=True)
        return

    texto = "IKA se actualizó." if actualizar else "IKA quedó instalada. Tienes un acceso directo en el Escritorio y en el menú Inicio."
    if accesos.mensaje(texto + "\n\n¿Abrirla ahora?", pregunta=True) and not accesos.SIN_PREGUNTAS:
        subprocess.Popen([str(exe)], cwd=str(destino), close_fds=True)


if __name__ == "__main__":
    main()
