import os
import sys
import subprocess

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
RAILEPUB_SCRIPT = os.path.join(BASE_DIR, "RailEpub.py")

def main():
    if not os.path.exists(VENV_PYTHON):
        print("===================================================")
        print("[!] ERROR: No se encontró el entorno virtual (.venv).")
        print("Por favor, ejecuta primero 'instalar_dependencias.bat'")
        print("===================================================")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    if not os.path.exists(RAILEPUB_SCRIPT):
        print(f"[!] ERROR: No se encontró 'RailEpub.py' en: {BASE_DIR}")
        input("\nPresiona Enter para salir...")
        sys.exit(1)

    try:
        subprocess.run([VENV_PYTHON, RAILEPUB_SCRIPT])
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n[!] Error ejecutando el programa: {e}")
        input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()