import json
import os
import re
import tkinter as tk
from tkinter import filedialog

# ================== CONFIGURACIÓN DINÁMICA ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Usa 'ruta_volumen' si existe en el contexto global/local; si no, usa BASE_DIR
CARPETA_BASE = globals().get('ruta_volumen') or locals().get('ruta_volumen') or BASE_DIR

# 1. Búsqueda automática del Glosario TXT
RUTA_GLOSARIO_TXT = os.path.join(CARPETA_BASE, "Correccion", "GlosarioRailWars.txt")
if not os.path.exists(RUTA_GLOSARIO_TXT):
    RUTA_GLOSARIO_TXT = os.path.join(CARPETA_BASE, "GlosarioRailWars.txt")

# 2. Búsqueda automática del Vocabulario JSON
RUTA_VOCABULARIO = os.path.join(CARPETA_BASE, "Correccion", "vocabulario_serie.json")
if not os.path.exists(RUTA_VOCABULARIO):
    RUTA_VOCABULARIO = os.path.join(CARPETA_BASE, "vocabulario_serie.json")

# --- VERIFICACIÓN / SELECCIÓN MANUAL SI NO EXISTEN ---
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)

if not os.path.exists(RUTA_GLOSARIO_TXT):
    print("[!] No se encontró 'GlosarioRailWars.txt' automáticamente. Selecciónalo manualmente:")
    RUTA_GLOSARIO_TXT = filedialog.askopenfilename(
        title="Selecciona el archivo de Glosario (.txt)",
        initialdir=CARPETA_BASE,
        filetypes=[("Archivos TXT", "*.txt"), ("Todos los archivos", "*.*")]
    )

if not os.path.exists(RUTA_VOCABULARIO):
    print("[!] No se encontró 'vocabulario_serie.json' automáticamente. Selecciónalo manualmente:")
    RUTA_VOCABULARIO = filedialog.askopenfilename(
        title="Selecciona el archivo de Vocabulario (.json)",
        initialdir=CARPETA_BASE,
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
    )

print(f"[✓] Glosario cargado desde: {RUTA_GLOSARIO_TXT}")
print(f"[✓] Vocabulario cargado desde: {RUTA_VOCABULARIO}")

# Admite "—" o "-" como separador y () o （） para la lectura
PATRON_ENTRADA = re.compile(
    r'^([^\s(（]+)\s*(?:[\(（]([^\)）]+)[\)）])?\s*[—\-]\s*(.+)$'
)


# ================== FUNCIONES AUXILIARES ==================

def obtener_categoria_y_tipo(header_linea):
    """
    Limpia emojis/símbolos del encabezado y deduce automáticamente
    la categoría (clave) y su tipo en singular.
    """
    texto_limpio = re.sub(r'[^\w\s]', '', header_linea).strip()
    if not texto_limpio:
        return "general", "general"

    categoria = texto_limpio.lower().replace(" ", "_")

    # Deducción básica del tipo en singular para español
    tipo = categoria
    if tipo.endswith("ciones"):
        tipo = tipo[:-2]  # organizaciones -> organizacion
    elif tipo.endswith("es") and len(tipo) > 3:
        tipo = tipo[:-2]  # personajes -> personaje
    elif tipo.endswith("s") and len(tipo) > 3:
        tipo = tipo[:-1]  # lineas -> linea, locomotoras -> locomotora

    return categoria, tipo


def cargar_vocabulario():
    if RUTA_VOCABULARIO and os.path.exists(RUTA_VOCABULARIO):
        with open(RUTA_VOCABULARIO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def crear_entrada_manual(
    termino,
    lectura,
    descripcion,
    categoria,
    tipo,
    existente=None
):
    if existente is None:
        existente = {}

    return {
        "origen": "manual",
        "categoria": categoria,
        "tipo": tipo,
        "lectura": lectura if lectura else existente.get("lectura"),
        "descripcion": descripcion.strip(),
        "frecuencia": existente.get("frecuencia", 0),
        "aliases": existente.get("aliases", []),
        "errores": existente.get("errores", []),
        "confianza": existente.get("confianza", 1.0),
    }


# ================== MAIN ==================

def main():

    if not RUTA_GLOSARIO_TXT or not os.path.exists(RUTA_GLOSARIO_TXT):
        print("[!] Operación cancelada o no se encontró el glosario.")
        return

    with open(RUTA_GLOSARIO_TXT, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    vocabulario = cargar_vocabulario()

    categoria_actual = "general"

    agregados = 0
    actualizados = 0

    for linea in lineas:

        linea = linea.strip()

        if not linea:
            continue

        m = PATRON_ENTRADA.match(linea)

        if m:

            termino, lectura, descripcion = m.groups()

            categoria, tipo = obtener_categoria_y_tipo(categoria_actual)

            existente = vocabulario.get(termino)

            vocabulario[termino] = crear_entrada_manual(
                termino=termino,
                lectura=lectura,
                descripcion=descripcion,
                categoria=categoria,
                tipo=tipo,
                existente=existente
            )

            if existente:
                actualizados += 1
            else:
                agregados += 1

        else:
        
            categoria_actual = linea

    if RUTA_VOCABULARIO:
        dir_vocabulario = os.path.dirname(RUTA_VOCABULARIO)
        if dir_vocabulario:
            os.makedirs(dir_vocabulario, exist_ok=True)

        with open(RUTA_VOCABULARIO, "w", encoding="utf-8") as f:
            json.dump(vocabulario, f, ensure_ascii=False, indent=2)

        print(f"\n[✓] Términos nuevos: {agregados}")
        print(f"[✓] Términos actualizados: {actualizados}")
        print(f"[✓] Total de términos: {len(vocabulario)}")
        print(f"[✓] Vocabulario guardado en:\n{RUTA_VOCABULARIO}")


if __name__ == "__main__":
    main()