import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HERRAMIENTAS = {
    "1": ("OCR (EscanerFinal)", os.path.join("OCR", "EscanerFinal.py")),
    "2": ("Cleaner - Importar", os.path.join("Cleaner", "Importar.py")),
    "3": ("Cleaner - Corrección", os.path.join("Cleaner", "Correccion.py")),
    "4": ("Cleaner - Constructor v2", os.path.join("Cleaner", "Constructorv2.py")),
    "5": ("Generador EPUB (EpubCreator)", os.path.join("EPUB", "EpubCreator.py")),
}


def ejecutar_script(ruta_relativa):
    ruta_absoluta = os.path.join(BASE_DIR, ruta_relativa)

    if not os.path.exists(ruta_absoluta):
        print(f"\n[!] Error: No se encontró el archivo en: {ruta_absoluta}\n")
        return

    print(f"\nLanzando {os.path.basename(ruta_relativa)}...\n" + "-" * 50)
    try:
        subprocess.run([sys.executable, ruta_absoluta], check=True)
        print("-" * 50 + "\n[✓] Proceso finalizado correctamente.\n")
    except subprocess.CalledProcessError as e:
        print(f"\n[!] El script finalizó con error (Código: {e.returncode}).\n")
    except KeyboardInterrupt:
        print("\n[!] Ejecución cancelada por el usuario.\n")
    except Exception as e:
        print(f"\n[!] Ocurrió un error insospechado: {e}\n")


def menu_principal():
    while True:
        print("==============================================")
        print("          RAIL EPUB - PANEL PRINCIPAL         ")
        print("==============================================")
        for opcion, (nombre, _) in HERRAMIENTAS.items():
            print(f"  [{opcion}] {nombre}")
        print("  [0] Salir")
        print("==============================================")

        eleccion = input("Selecciona una herramienta (0-5): ").strip()

        if eleccion == "0":
            print("\n¡Hasta luego!")
            break
        elif eleccion in HERRAMIENTAS:
            _, ruta_script = HERRAMIENTAS[eleccion]
            ejecutar_script(ruta_script)
        else:
            print("\n[!] Opción no válida. Por favor, intenta de nuevo.\n")


if __name__ == "__main__":
    menu_principal()