import json
import os
import re
import tkinter as tk
from tkinter import filedialog
from janome.tokenizer import Tokenizer

# ==================== CONFIGURACIÓN DE RUTAS DINÁMICAS ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()

ruta_volumen = globals().get('ruta_volumen') or locals().get('ruta_volumen')
if not ruta_volumen:
    print("Por favor, selecciona la carpeta del volumen...")
    ruta_volumen = filedialog.askdirectory(title="Selecciona la carpeta del volumen")

if not ruta_volumen:
    raise ValueError("No se seleccionó ninguna carpeta. El script ha sido cancelado.")

ruta_volumen = os.path.normpath(ruta_volumen)

RUTA_VOCABULARIO = os.path.join(ruta_volumen, "Correccion", "vocabulario_serie.json")
if not os.path.exists(RUTA_VOCABULARIO):
    RUTA_VOCABULARIO = os.path.join(ruta_volumen, "vocabulario_serie.json")

if not os.path.exists(RUTA_VOCABULARIO):
    RUTA_VOCABULARIO = filedialog.askopenfilename(
        title="Selecciona el archivo vocabulario_serie.json",
        initialdir=ruta_volumen,
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
    )

RUTA_MAPA_OCR_EXTRA = os.path.join(ruta_volumen, "Correccion", "mapa_ocr.json")

DIR_TXT_ENTRADA = os.path.join(ruta_volumen, "TXT")
DIR_TXT_SALIDA = os.path.join(ruta_volumen, "Correccion", "Corregido")
RUTA_LOG_SALIDA = os.path.join(ruta_volumen, "Correccion", "log_correcciones_v3.2.txt")

os.makedirs(DIR_TXT_SALIDA, exist_ok=True)
os.makedirs(os.path.dirname(RUTA_LOG_SALIDA), exist_ok=True)


# ==================== FUNCIONES AUXILIARES ====================

def es_katakana_puro(texto):
    """
    Retorna True si la palabra está compuesta exclusivamente por Katakana
    (incluyendo el guion largo de vocal prolongada 'ー').
    """
    return bool(re.fullmatch(r'[\u30A0-\u30FF\u30FC]+', texto))


def construir_mapa_ocr_dinamico(vocabulario, ruta_mapa_extra=None):
    mapa_ocr = {}

    if ruta_mapa_extra and os.path.exists(ruta_mapa_extra):
        try:
            with open(ruta_mapa_extra, "r", encoding="utf-8") as f:
                mapa_ocr.update(json.load(f))
        except Exception as e:
            print(f"[!] No se pudo cargar el mapa OCR extra: {e}")

    for termino_correcto, config in vocabulario.items():
        errores = config.get("errores", [])
        if isinstance(errores, list):
            for err in errores:
                err = err.strip()
                if err and err != termino_correcto:
                    mapa_ocr[err] = termino_correcto

    print(f"[✓] Reglas directas OCR cargadas: {len(mapa_ocr)}")
    return mapa_ocr


def calcular_levenshtein(s1, s2):
    if len(s1) < len(s2):
        return calcular_levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def es_palabra_protegida(token):
    superficie = token.surface

    # 1. PROTECCIÓN BLINDADA PARA KATAKANA: No aplicar Levenshtein a palabras 100% Katakana
    if es_katakana_puro(superficie):
        return True

    pos_parts = token.part_of_speech.split(",")
    pos_1 = pos_parts[0]
    pos_2 = pos_parts[1] if len(pos_parts) > 1 else ""

    if pos_1 in ["動詞", "助詞", "形容詞", "副詞", "接続詞", "記号"]:
        return True

    if pos_1 == "名詞" and pos_2 in ["一般", "副詞可能", "時相名詞", "数", "接尾"]:
        return True

    return False


# ==================== PROCESO PRINCIPAL ====================

def corregir_texto_blindado():
    if not RUTA_VOCABULARIO or not os.path.exists(RUTA_VOCABULARIO):
        print("[!] Error: No se encontró el archivo de vocabulario JSON.")
        return

    with open(RUTA_VOCABULARIO, "r", encoding="utf-8") as f:
        vocabulario = json.load(f)

    mapa_ocr_directo = construir_mapa_ocr_dinamico(vocabulario, RUTA_MAPA_OCR_EXTRA)
    tokenizer = Tokenizer()

    if not os.path.exists(DIR_TXT_ENTRADA):
        print(f"[!] Error: La carpeta de entrada TXT no existe: {DIR_TXT_ENTRADA}")
        return

    archivos = sorted(
        [f for f in os.listdir(DIR_TXT_ENTRADA) if f.lower().endswith(".txt")]
    )
    print(f"\nIniciando corrección BLINDADA (v3.2 - Katakana protegido) sobre {len(archivos)} archivos...")

    lineas_log = []
    total_correcciones = 0

    for nombre_archivo in archivos:
        ruta_in = os.path.join(DIR_TXT_ENTRADA, nombre_archivo)
        ruta_out = os.path.join(DIR_TXT_SALIDA, nombre_archivo)

        with open(ruta_in, "r", encoding="utf-8", errors="ignore") as f:
            lineas = f.readlines()

        lineas_corregidas = []
        cambios_archivo = []

        for linea in lineas:
            linea_procesada = linea

            # 1. Reemplazos Directos OCR (Acepta Katakana si está explícitamente definido en 'errores')
            for error_ocr, correccion in mapa_ocr_directo.items():
                if error_ocr in linea_procesada:
                    linea_procesada = linea_procesada.replace(error_ocr, correccion)
                    cambios_archivo.append(f"  [OCR Directo] {error_ocr} -> {correccion}")
                    total_correcciones += 1

            tokens = list(tokenizer.tokenize(linea_procesada))

            for token in tokens:
                superficie = token.surface

                if es_palabra_protegida(token):
                    continue

                if len(superficie) <= 3:
                    continue

                for termino_correcto, config in vocabulario.items():
                    if len(termino_correcto) <= 3:
                        continue

                    if es_katakana_puro(termino_correcto):
                        continue

                    tolerancia = config.get("tolerancia_levenshtein", 0)
                    if tolerancia == 0:
                        continue

                    if abs(len(superficie) - len(termino_correcto)) <= tolerancia:
                        distancia = calcular_levenshtein(superficie, termino_correcto)

                        if 0 < distancia <= tolerancia:
                            linea_procesada = linea_procesada.replace(
                                superficie, termino_correcto
                            )
                            cambios_archivo.append(
                                f"  [Levenshtein Kanji] {superficie} -> {termino_correcto}"
                            )
                            total_correcciones += 1
                            break

            lineas_corregidas.append(linea_procesada)

        with open(ruta_out, "w", encoding="utf-8") as f:
            f.writelines(lineas_corregidas)

        if cambios_archivo:
            lineas_log.append(f"--- {nombre_archivo} ---")
            lineas_log.extend(cambios_archivo)

    with open(RUTA_LOG_SALIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas_log))

    print("\n--- PROCESO COMPLETADO ---")
    print(f"Total de correcciones realizadas: {total_correcciones}")
    print(f"Archivos guardados en: {DIR_TXT_SALIDA}")
    print(f"Log guardado en: {RUTA_LOG_SALIDA}")


if __name__ == "__main__":
    corregir_texto_blindado()