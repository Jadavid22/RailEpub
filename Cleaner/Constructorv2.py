import json
import os
import re
from collections import Counter
from janome.tokenizer import Tokenizer
import os
import tkinter as tk
from tkinter import filedialog

# ==================== CONFIGURACIÓN DE RUTAS ====================
# Forzar la ventana de selección al frente para que no se oculte
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()

print("Por favor, selecciona la carpeta de textos corregidos (ej. Corregidos)...")
ruta_seleccionada = filedialog.askdirectory(title="Selecciona la carpeta de textos corregidos")

if not ruta_seleccionada:
    raise ValueError("No se seleccionó ninguna carpeta. El script ha sido cancelado.")

# Asignar ruta de entrada dinámicamente
RUTA_TXT_ENTRADA = os.path.normpath(ruta_seleccionada) + "/"

# Ruta fija para el JSON global de toda la serie
RUTA_JSON_SALIDA = "C:/Users/JUDAPITEC/Documents/David/Halo Novelas/ライトノベル/RAIL WARS! -日本國有鉄道公安隊/Correccion/vocabulario_serie.json"

print(f"[✓] Carpeta de entrada asignada: {RUTA_TXT_ENTRADA}")
print(f"[✓] Ruta del JSON de salida: {RUTA_JSON_SALIDA}")

# ==================== FILTROS Y UMBRALES ====================
FRECUENCIA_MINIMA = {
    "rail_material": 2,
    "rail_infraestructura": 3,
    "nombre_propio": 3,
    "katakana": 5,
}

TOLERANCIA_LEVENSHTEIN = {
    "rail_material": 0,
    "rail_infraestructura": 1,
    "nombre_propio": 1,
    "katakana": 1,
}

PARTICULAS_SUFIJOS = re.compile(
    r"(は|が|に|を|の|と|も|へ|で|から|まで|より|さん|様|くん|ちゃん|たち)$"
)
REGEX_KATAKANA_PURO = re.compile(r"^[\u30a0-\u30ff\u30fc]+$")

STOPWORDS = {
    "それ",
    "これ",
    "あれ",
    "そこ",
    "ここ",
    "あそこ",
    "私",
    "僕",
    "俺",
    "あなた",
    "そう",
    "どう",
    "人",
    "方",
    "物",
    "事",
    "とき",
    "時",
    "毎日",
    "今日",
    "明日",
    "昨日",
    "自分",
    "コツ",
}

TERMINACIONES_VERBALES = re.compile(
    r"(った|いた|した|て|た|ない|よう|ます|です|ある|いる|なる|する|思う|言った|来る|行く)$"
)

# ==================== PATRONES REGEX ====================
PATRONES = {
    "rail_material": re.compile(
        r"(?:[A-Z]{1,3}[0-9]{2,4}|[0-9]{2,4}系|キハ[0-9]+|C[0-9]{2}|D[0-9]{2})"
    ),
    "rail_infraestructura": re.compile(
        r"[\u4e00-\u9faf]{2,8}(?:線|駅|本線|鉄道|公安隊)"
    ),
    "katakana": re.compile(r"[\u30a0-\u30ff\u30fc]{2,}"),
}


def limpiar_palabra(palabra):
    return PARTICULAS_SUFIJOS.sub("", palabra)


def corregir_categoria(palabra, categoria_actual):
    if (
        REGEX_KATAKANA_PURO.match(palabra)
        and categoria_actual == "nombre_propio"
    ):
        return "katakana"
    return categoria_actual


def esta_solapado(start, end, rangos_ocupados):
    """Verifica si un rango de caracteres ya fue reclamado por una categoría de mayor prioridad."""
    for r_start, r_end in rangos_ocupados:
        if not (end <= r_start or start >= r_end):
            return True
    return False


def extraer_candidatos_linea(linea, tokenizer):
    candidatos_linea = {}
    rangos_ocupados = []

    # ---------------------------------------------------------
    # PASO 1 (Prioridad Alta): Infraestructura y Material Rodante
    # ---------------------------------------------------------
    for cat in ["rail_material", "rail_infraestructura"]:
        for match in PATRONES[cat].finditer(linea):
            palabra = limpiar_palabra(match.group())
            if len(palabra) >= 2 and palabra not in STOPWORDS:
                candidatos_linea[palabra] = cat
                # Reservar el rango en la línea para evitar que Janome extraiga fragmentos
                rangos_ocupados.append((match.start(), match.end()))

    # ---------------------------------------------------------
    # PASO 2 (Prioridad Media): Janome (Nombres Propios) con Filtro de Solapamiento
    # ---------------------------------------------------------
    tokens = list(tokenizer.tokenize(linea))
    cursor = 0

    for i, token in enumerate(tokens):
        tok_len = len(token.surface)
        tok_start = linea.find(token.surface, cursor)
        tok_end = tok_start + tok_len if tok_start != -1 else cursor + tok_len
        cursor = tok_end if tok_start != -1 else cursor

        # Si este token está dentro de un término ferroviario ya extraído, SE IGNORA
        if esta_solapado(tok_start, tok_end, rangos_ocupados):
            continue

        super_pos = token.part_of_speech.split(",")[0]
        sub_pos = token.part_of_speech.split(",")[1]

        if super_pos == "名詞" and (
            sub_pos in ["固有名詞", "人名", "地域", "組織"]
        ):
            palabra = token.surface

            # Concatenar nombres compuestos (ej: 桜井 + あおい)
            if i + 1 < len(tokens):
                sig_token = tokens[i + 1]
                sig_sub = sig_token.part_of_speech.split(",")[1]
                if sig_sub == "人名" or (
                    sig_token.part_of_speech.split(",")[0] == "名詞"
                    and re.match(r"^[\u3040-\u309f]+$", sig_token.surface)
                ):
                    palabra += sig_token.surface

            palabra = limpiar_palabra(palabra)
            if len(palabra) >= 2 and palabra not in STOPWORDS:
                cat = corregir_categoria(palabra, "nombre_propio")
                candidatos_linea[palabra] = cat

    # ---------------------------------------------------------
    # PASO 3: Katakana General
    # ---------------------------------------------------------
    for match in PATRONES["katakana"].finditer(linea):
        if not esta_solapado(match.start(), match.end(), rangos_ocupados):
            palabra = match.group()
            if palabra not in STOPWORDS and not TERMINACIONES_VERBALES.search(
                palabra
            ):
                if palabra not in candidatos_linea:
                    candidatos_linea[palabra] = "katakana"

    return candidatos_linea


def construir_vocabulario():
    print("Inicializando Janome con filtro de solapamiento v2.3...")
    tokenizer = Tokenizer()

    if not os.path.isdir(RUTA_TXT_ENTRADA):
        print(f"Error: La carpeta '{RUTA_TXT_ENTRADA}' no existe.")
        return

    archivos_txt = [
        f for f in os.listdir(RUTA_TXT_ENTRADA) if f.lower().endswith(".txt")
    ]
    if not archivos_txt:
        print(f"No se encontraron archivos .txt en '{RUTA_TXT_ENTRADA}'.")
        return

    conteo_global = Counter()
    categorias_palabras = {}

    print(f"Procesando {len(archivos_txt)} archivo(s)...")

    for nombre_archivo in archivos_txt:
        ruta_archivo = os.path.join(RUTA_TXT_ENTRADA, nombre_archivo)
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue

                candidatos_linea = extraer_candidatos_linea(linea, tokenizer)

                for palabra, categoria in candidatos_linea.items():
                    if (
                        TERMINACIONES_VERBALES.search(palabra)
                        and categoria != "rail_material"
                    ):
                        continue

                    conteo_global[palabra] += 1
                    if (
                        palabra not in categorias_palabras
                        or categorias_palabras[palabra] == "katakana"
                    ):
                        categorias_palabras[palabra] = categoria

    # ---------------------------------------------------------
    # Consolidación Final
    # ---------------------------------------------------------
    vocabulario_final = {}
    descartados = 0

    for palabra, frecuencia in conteo_global.items():
        cat = categorias_palabras[palabra]
        cat = corregir_categoria(palabra, cat)
        frec_minima = FRECUENCIA_MINIMA.get(cat, 3)

        if frecuencia >= frec_minima and palabra not in STOPWORDS:
            vocabulario_final[palabra] = {
                "frecuencia": frecuencia,
                "categoria": cat,
                "tolerancia_levenshtein": TOLERANCIA_LEVENSHTEIN.get(cat, 1),
            }
        else:
            descartados += 1

    vocabulario_ordenado = dict(
        sorted(
            vocabulario_final.items(),
            key=lambda x: x[1]["frecuencia"],
            reverse=True,
        )
    )

    os.makedirs(os.path.dirname(RUTA_JSON_SALIDA), exist_ok=True)
    with open(RUTA_JSON_SALIDA, "w", encoding="utf-8") as f:
        json.dump(vocabulario_ordenado, f, ensure_ascii=False, indent=2)

    print("\n--- RESUMEN DEL PROCESO v2.3 ---")
    print(f"Términos aprobados: {len(vocabulario_ordenado)}")
    print(f"Descartados por ruido/frecuencia: {descartados}")
    print(f"JSON guardado en: {RUTA_JSON_SALIDA}")


if __name__ == "__main__":
    construir_vocabulario()