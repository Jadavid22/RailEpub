import os
import re
import math
import shutil
import cv2
import numpy as np
import logging
from PIL import Image
import tkinter as tk
from tkinter import filedialog 
from tqdm import tqdm

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
logging.getLogger("transformers").setLevel(logging.ERROR)


root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()

print("Por favor, selecciona la carpeta del volumen...")
ruta_seleccionada = filedialog.askdirectory(title="Selecciona la carpeta del volumen")

if not ruta_seleccionada:
    raise ValueError("No se seleccionó ninguna carpeta. El script ha sido cancelado.")

ruta_base = os.path.normpath(ruta_seleccionada) + "/"

RUTA_IMAGENES_ORIGEN = ruta_base
RUTA_SALIDA_TXT = os.path.join(ruta_base, "TXT/")
RUTA_SALIDA_IMG = os.path.join(ruta_base, "Imagenes/")

os.makedirs(RUTA_SALIDA_TXT, exist_ok=True)
os.makedirs(RUTA_SALIDA_IMG, exist_ok=True)

RUTA_DEBUG = os.path.join(RUTA_IMAGENES_ORIGEN, "debug")
MODO_DEBUG = False

ANCHO_MINIMO_COLUMNA_RELATIVO = 0.4
HUECO_MINIMO_RELATIVO = 0.3          
ANCHO_FUSION_FURIGANA_RELATIVO = 0.2 

PADDING = 4
DETECTAR_ENCABEZADO = True
ZONA_ENCABEZADO_MAX = 0.15
HUECO_VERTICAL_MINIMO = 15

MAX_CARACTERES_POR_TRAMO = 16  
VENTANA_BUSQUEDA_CORTE = 18    
PADDING_VERTICAL = 4
FACTOR_ESCALA_OCR = 2.5

if MODO_DEBUG:
    os.makedirs(RUTA_DEBUG, exist_ok=True)


def orden_natural(nombre):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', nombre)]


def leer_imagen_cv(ruta):
    datos = np.fromfile(ruta, dtype=np.uint8)
    return cv2.imdecode(datos, cv2.IMREAD_COLOR)


def es_imagen_color_o_ilustracion(imagen_cv):
    """
    Analiza la imagen para determinar si es una ilustración a color o en blanco y negro sin texto estructurado.
    Retorna: (es_ilustracion, es_color)
    """
    if imagen_cv is None:
        return False, False

    b, g, r = cv2.split(imagen_cv)
    diff_rg = cv2.absdiff(r, g)
    diff_rb = cv2.absdiff(r, b)
    diff_gb = cv2.absdiff(g, b)
    desviacion_color = np.mean(diff_rg) + np.mean(diff_rb) + np.mean(diff_gb)

    es_color = desviacion_color > 12.0

    gris = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2GRAY)
    _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    densidad_tinta = np.sum(binaria > 0) / (imagen_cv.shape[0] * imagen_cv.shape[1])
    es_ilustracion = es_color or (densidad_tinta > 0.18)

    return es_ilustracion, es_color


def recortar_encabezado(imagen_cv):
    gris = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2GRAY)
    _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    proyeccion_filas = np.sum(binaria > 0, axis=1)
    hay_tinta = proyeccion_filas > 0

    alto = imagen_cv.shape[0]
    limite_busqueda = int(alto * ZONA_ENCABEZADO_MAX)

    encontro_tinta = False
    hueco = 0
    for y in range(limite_busqueda):
        if hay_tinta[y]:
            encontro_tinta = True
            hueco = 0
        elif encontro_tinta:
            hueco += 1
            if hueco >= HUECO_VERTICAL_MINIMO:
                y_inicio = y - hueco + 1
                return imagen_cv[y_inicio:, :], y_inicio

    return imagen_cv, 0


def detectar_columnas_adaptativo(imagen_cv):
    gris = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2GRAY)
    _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    proyeccion = np.sum(binaria > 0, axis=0)
    hay_texto = proyeccion > 0

    columnas_candidatas = []
    inicio = None
    hueco = 0

    for x, val in enumerate(hay_texto):
        if val:
            if inicio is None:
                inicio = x
            hueco = 0
        elif inicio is not None:
            hueco += 1
            if hueco >= 3:
                fin = x - hueco
                if fin - inicio >= 5:
                    columnas_candidatas.append([inicio, fin])
                inicio = None

    if inicio is not None:
        fin = len(hay_texto)
        if fin - inicio >= 5:
            columnas_candidatas.append([inicio, fin])

    if not columnas_candidatas:
        return []

    anchos = [c[1] - c[0] for c in columnas_candidatas]
    ancho_medio = np.median(anchos)

    ancho_minimo = ancho_medio * ANCHO_MINIMO_COLUMNA_RELATIVO
    ancho_furigana = ancho_medio * ANCHO_FUSION_FURIGANA_RELATIVO

    columnas_filtradas = [c for c in columnas_candidatas if (c[1] - c[0]) >= ancho_minimo]
    columnas_finales = [c for c in columnas_filtradas if (c[1] - c[0]) >= ancho_furigana]

    ancho_img = imagen_cv.shape[1]
    columnas_finales = [(max(0, a - PADDING), min(ancho_img, b + PADDING)) for a, b in columnas_finales]
    columnas_finales.sort(key=lambda c: c[0], reverse=True)

    return columnas_finales


def encontrar_extremos_tinta(proyeccion):
    indices = np.nonzero(proyeccion > 0)[0]
    if len(indices) == 0:
        return None
    return int(indices[0]), int(indices[-1])


def dividir_columna_larga(imagen_cv, x_inicio, x_fin):
    ancho_real_texto = max(1, (x_fin - x_inicio) - (PADDING * 2))
    alto_imagen = imagen_cv.shape[0]

    gris = cv2.cvtColor(imagen_cv[:, x_inicio:x_fin], cv2.COLOR_BGR2GRAY)
    _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    proyeccion = np.sum(binaria > 0, axis=1)

    extremos = encontrar_extremos_tinta(proyeccion)
    if extremos is None:
        return [(0, alto_imagen)]

    y_min, y_max = extremos
    alto_texto = y_max - y_min
    caracteres_estimados = alto_texto / ancho_real_texto

    if caracteres_estimados <= MAX_CARACTERES_POR_TRAMO:
        y_min_pad = max(0, y_min - PADDING_VERTICAL)
        y_max_pad = min(alto_imagen, y_max + PADDING_VERTICAL)
        return [(y_min_pad, y_max_pad)]

    n_tramos = math.ceil(caracteres_estimados / MAX_CARACTERES_POR_TRAMO)
    puntos_corte = [max(0, y_min - PADDING_VERTICAL)]
    
    for i in range(1, n_tramos):
        y_ideal = y_min + int(alto_texto * i / n_tramos)
        ventana_inicio = max(y_min, y_ideal - VENTANA_BUSQUEDA_CORTE)
        ventana_fin = min(y_max, y_ideal + VENTANA_BUSQUEDA_CORTE)
        
        sub = proyeccion[ventana_inicio:ventana_fin]
        mejor_y = ventana_inicio + int(np.argmin(sub)) if len(sub) > 0 else y_ideal
        puntos_corte.append(mejor_y)

    puntos_corte.append(min(alto_imagen, y_max + PADDING_VERTICAL))
    return [(puntos_corte[i], puntos_corte[i + 1]) for i in range(len(puntos_corte) - 1)]


def generar_bloques(imagen_cv):
    columnas = detectar_columnas_adaptativo(imagen_cv)
    resultado = []
    for x_inicio, x_fin in columnas:
        tramos_y = dividir_columna_larga(imagen_cv, x_inicio, x_fin)
        resultado.append([(x_inicio, x_fin, y1, y2) for y1, y2 in tramos_y])
    return resultado


def procesar_pagina(mocr, ruta_imagen):
    imagen_cv = leer_imagen_cv(ruta_imagen)
    if imagen_cv is None:
        raise ValueError(f"No se pudo leer la imagen: {ruta_imagen}")

    offset_y = 0
    if DETECTAR_ENCABEZADO:
        imagen_cv, offset_y = recortar_encabezado(imagen_cv)

    columnas_con_tramos = generar_bloques(imagen_cv)

    img_pil = Image.open(ruta_imagen).convert("RGB")
    if offset_y > 0:
        img_pil = img_pil.crop((0, offset_y, img_pil.width, img_pil.height))

    textos = []
    for tramos in columnas_con_tramos:
        texto_columna = ""
        for a, b, y1, y2 in tramos:
            recorte = img_pil.crop((a, y1, b, y2))
            if FACTOR_ESCALA_OCR != 1.0:
                nuevo_ancho = max(1, int(recorte.width * FACTOR_ESCALA_OCR))
                nuevo_alto = max(1, int(recorte.height * FACTOR_ESCALA_OCR))
                recorte = recorte.resize((nuevo_ancho, nuevo_alto), Image.LANCZOS)
            texto = mocr(recorte)
            if texto.strip():
                texto_columna += texto.strip()
        if texto_columna:
            textos.append(texto_columna)

    return "\n".join(textos)


def main():
    imagenes = [f for f in os.listdir(RUTA_IMAGENES_ORIGEN)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
    imagenes.sort(key=orden_natural)

    if not imagenes:
        print(f"[!] No se encontraron imágenes en '{RUTA_IMAGENES_ORIGEN}'")
        return

    print(f"\n[✓] {len(imagenes)} imágenes encontradas. Iniciando escaneo...\n")

    mocr = None
    
    # Barra de progreso principal con tqdm
    bar_format = "{l_bar}{bar:30} | {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {postfix}"
    pbar = tqdm(imagenes, desc="Escaneando páginas", bar_format=bar_format)

    for nombre in pbar:
        ruta_imagen_orig = os.path.join(RUTA_IMAGENES_ORIGEN, nombre)
        nombre_base, ext = os.path.splitext(nombre)
        
        imagen_cv = leer_imagen_cv(ruta_imagen_orig)
        es_ilustracion, es_color = es_imagen_color_o_ilustracion(imagen_cv)

        # CASO 1: Ilustración (A color o B/N)
        if es_ilustracion:
            nuevo_nombre = f"{nombre_base}_COLOR{ext}" if es_color else nombre
            ruta_destino_img = os.path.join(RUTA_SALIDA_IMG, nuevo_nombre)
            shutil.copy2(ruta_imagen_orig, ruta_destino_img)
            
            etiqueta = "Color" if es_color else "Ilustración B/N"
            pbar.set_postfix_str(f"Guardada {nombre} -> Imagenes/ ({etiqueta})")
            continue

        if mocr is None and not MODO_DEBUG:
            pbar.set_postfix_str("Cargando modelo MangaOCR...")
            from manga_ocr import MangaOcr
            mocr = MangaOcr()

        pbar.set_postfix_str(f"Procesando OCR: {nombre}")
        try:
            texto = procesar_pagina(mocr, ruta_imagen_orig) if not MODO_DEBUG else "TEXTO DEBUG"
        except Exception as e:
            pbar.set_postfix_str(f"Error en {nombre}: {e}")
            continue

        if texto.strip():
            ruta_txt = os.path.join(RUTA_SALIDA_TXT, f"{nombre_base}.txt")
            with open(ruta_txt, "w", encoding="utf-8") as f:
                f.write(texto)
            pbar.set_postfix_str(f"Guardado TXT: {nombre_base}.txt")

    pbar.close()
    print("\n" + "="*50)
    print("¡Procesamiento completado con éxito!")
    print(f"• Ilustraciones organizadas en: {RUTA_SALIDA_IMG}")
    print(f"• Textos generados en: {RUTA_SALIDA_TXT}")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()