import json
import os
import re
from janome.tokenizer import Tokenizer
import tkinter as tk
from tkinter import filedialog

# ==================== CONFIGURACIÓN DE RUTAS ====================
# Forzar la ventana de selección al frente para que no se oculte
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()

print("Por favor, selecciona la carpeta del volumen (ej. [豊田 巧] RAIL WARS! 第01巻)...")
ruta_volumen = filedialog.askdirectory(title="Selecciona la carpeta del volumen")

if not ruta_volumen:
    raise ValueError("No se seleccionó ninguna carpeta. El script ha sido cancelado.")

ruta_volumen = os.path.normpath(ruta_volumen)

RUTA_VOCABULARIO = "C:/Users/JUDAPITEC/Documents/David/Halo Novelas/ライトノベル/RAIL WARS! -日本國有鉄道公安隊/Correccion/vocabulario_serie.json"

DIR_TXT_ENTRADA = os.path.join(ruta_volumen, "TXT") + "/"
DIR_TXT_SALIDA = os.path.join(ruta_volumen, "Correccion", "Corregido") + "/"
RUTA_LOG_SALIDA = os.path.join(ruta_volumen, "Correccion", "log_correcciones_v3.1.txt")

# Asegurar que las carpetas de salida existan automáticamente
os.makedirs(DIR_TXT_SALIDA, exist_ok=True)
os.makedirs(os.path.dirname(RUTA_LOG_SALIDA), exist_ok=True)

print(f"[✓] Carpeta del volumen seleccionada: {ruta_volumen}")
print(f"[✓] Entrada TXT: {DIR_TXT_ENTRADA}")
print(f"[✓] Salida Corregidos: {DIR_TXT_SALIDA}")
print(f"[✓] Log de correcciones: {RUTA_LOG_SALIDA}")
# MAPA EXPLICITO DE ERRORES OCR CONOCIDOS (Solo reemplazos seguros y directos)
MAPA_OCR_DIRECTO = {
    "北京駅": "東京駅",
    "大京駅": "東京駅",
    "鉄道公安機": "鉄道公安隊",
    "鉄道会安隊": "鉄道公安隊",
    "鉄道久安隊": "鉄道公安隊",
    "國鉄中央学": "國鉄中央線",
    "薪幹線": "新幹線",
    "新警線": "新幹線",
    "新乾線": "新幹線",
}


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
    """
    Protege verbos, partículas y sustantivos comunes válidos en japonés
    para impedir que sean aplastados por Levenshtein.
    """
    pos_1 = token.part_of_speech.split(",")[0]
    pos_2 = token.part_of_speech.split(",")[1]

    # No tocar verbos, adjetivos, partículas ni adverbios
    if pos_1 in ["動詞", "助詞", "形容詞", "副詞", "接続詞", "記号"]:
        return True

    # No tocar sustantivos comunes ni de tiempo (ej: 人, 犯人, 日, 本, 高校, 東京)
    if pos_1 == "名詞" and pos_2 in [
        "一般",
        "副詞可能",
        "時相名詞",
        "数",
        "接尾",
    ]:
        return True

    return False


def corregir_texto_blindado():
    if not os.path.exists(RUTA_VOCABULARIO):
        print("Error: No se encontró el archivo de vocabulario JSON.")
        return

    with open(RUTA_VOCABULARIO, "r", encoding="utf-8") as f:
        vocabulario = json.load(f)

    tokenizer = Tokenizer()
    os.makedirs(DIR_TXT_SALIDA, exist_ok=True)

    archivos = sorted(
        [f for f in os.listdir(DIR_TXT_ENTRADA) if f.lower().endswith(".txt")]
    )
    print(
        f"Iniciando corrección BLINDADA (v3.1) sobre {len(archivos)} archivos..."
    )

    lineas_log = []
    total_correcciones = 0

    for nombre_archivo in archivos:
        ruta_in = os.path.join(DIR_TXT_ENTRADA, nombre_archivo)
        ruta_out = os.path.join(DIR_TXT_SALIDA, nombre_archivo)

        with open(ruta_in, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        lineas_corregidas = []
        cambios_archivo = []

        for linea in lineas:
            linea_procesada = linea

            # 1. Aplicar Reemplazos OCR Directos y Seguros Primero
            for error_ocr, correccion in MAPA_OCR_DIRECTO.items():
                if error_ocr in linea_procesada:
                    linea_procesada = linea_procesada.replace(
                        error_ocr, correccion
                    )
                    cambios_archivo.append(f"  {error_ocr} -> {correccion}")
                    total_correcciones += 1

            # 2. Análisis Token por Token
            tokens = list(tokenizer.tokenize(linea_procesada))

            for token in tokens:
                superficie = token.surface

                # SI ES UNA PALABRA VÁLIDA DEL JAPONÉS, SE IGNORA TOTALMENTE
                if es_palabra_protegida(token):
                    continue

                # REGLA DE ORO: No corregir con Levenshtein palabras de <= 3 caracteres
                # a menos que sean un error evidente detectado
                if len(superficie) <= 3:
                    continue

                # Evaluar únicamente palabras compuestas largas por Levenshtein
                for termino_correcto, config in vocabulario.items():
                    # Solo evaluamos términos de 4 o más caracteres por aproximación
                    if len(termino_correcto) <= 3:
                        continue

                    tolerancia = config.get("tolerancia_levenshtein", 0)
                    if tolerancia == 0:
                        continue

                    if abs(len(superficie) - len(termino_correcto)) <= tolerancia:
                        distancia = calcular_levenshtein(
                            superficie, termino_correcto
                        )

                        if 0 < distancia <= tolerancia:
                            linea_procesada = linea_procesada.replace(
                                superficie, termino_correcto
                            )
                            cambios_archivo.append(
                                f"  {superficie} -> {termino_correcto}"
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

    print("\n--- PROCESO BLINDADO COMPLETADO ---")
    print(f"Total de correcciones seguras: {total_correcciones}")
    print(f"Archivos guardados en: {DIR_TXT_SALIDA}")
    print(f"Log guardado en: {RUTA_LOG_SALIDA}")


if __name__ == "__main__":
    corregir_texto_blindado()