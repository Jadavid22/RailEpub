import os
import re
import math
import cv2
import numpy as np
from PIL import Image
from manga_ocr import MangaOcr
import tkinter as tk
from tkinter import filedialog  
import os
import tkinter as tk
from tkinter import filedialog

# ==============================================================================
# SELECCIÓN DINÁMICA DE CARPETAS
# ==============================================================================
# Ocultar la ventana principal de Tkinter para que solo aparezca el explorador
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()
print("Por favor, selecciona la carpeta del volumen (ej. [豊田 巧] RAIL WARS! 第02巻)...")
ruta_seleccionada = filedialog.askdirectory(title="Selecciona la carpeta del volumen")

# Validar si el usuario canceló la selección
if not ruta_seleccionada:
    raise ValueError("No se seleccionó ninguna carpeta. El script ha sido cancelado.")

# Normalizar la ruta seleccionada con barras inclinadas hacia adelante
ruta_base = os.path.normpath(ruta_seleccionada) + "/"

# Asignar rutas automáticamente
RUTA_IMAGENES = ruta_base
RUTA_SALIDA_TXT = os.path.join(ruta_base, "TXT/")

# Asegurar que la carpeta TXT exista (si no existe, la crea)
os.makedirs(RUTA_SALIDA_TXT, exist_ok=True)

print(f"[✓] Carpeta de imágenes asignada: {RUTA_IMAGENES}")
print(f"[✓] Carpeta de salida TXT asignada: {RUTA_SALIDA_TXT}")
RUTA_DEBUG = os.path.join(RUTA_IMAGENES, "debug")

MODO_DEBUG = False
ARCHIVO_MAESTRO = os.path.join(RUTA_SALIDA_TXT, "novela_completa.txt")

# Parámetros adaptativos (se calculan automáticamente)
ANCHO_MINIMO_COLUMNA_RELATIVO = 0.4  # 40% del ancho de columna promedio
HUECO_MINIMO_RELATIVO = 0.3          # 30% del ancho de columna promedio
ANCHO_FUSION_FURIGANA_RELATIVO = 0.2 # 20% del ancho de columna promedio

PADDING = 4

DETECTAR_ENCABEZADO = True
ZONA_ENCABEZADO_MAX = 0.15
HUECO_VERTICAL_MINIMO = 15

# --- PARÁMETROS DE SEGMENTACIÓN AJUSTADOS ---
MAX_CARACTERES_POR_TRAMO = 16  # Reducido para forzar tramos más cortos e ideales para MangaOCR
VENTANA_BUSQUEDA_CORTE = 18    # Ventana en píxeles para buscar el espacio inter-carácter
PADDING_VERTICAL = 4
FACTOR_ESCALA_OCR = 2.5

GENERAR_TXT_MAESTRO = False

os.makedirs(RUTA_SALIDA_TXT, exist_ok=True)
os.makedirs(RUTA_DEBUG, exist_ok=True)


def orden_natural(nombre):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', nombre)]


def leer_imagen_cv(ruta):
    datos = np.fromfile(ruta, dtype=np.uint8)
    return cv2.imdecode(datos, cv2.IMREAD_COLOR)


def guardar_imagen_cv(ruta, imagen):
    extension = os.path.splitext(ruta)[1]
    ok, buffer = cv2.imencode(extension, imagen)
    if ok:
        buffer.tofile(ruta)
    return ok


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
    """
    Detecta columnas usando parámetros adaptativos basados en el espaciado real
    """
    gris = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2GRAY)
    _, binaria = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    proyeccion = np.sum(binaria > 0, axis=0)
    hay_texto = proyeccion > 0

    # Paso 1: Detectar columnas candidatas con umbral muy bajo
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
            if hueco >= 3:  # Umbral mínimo muy bajo
                fin = x - hueco
                if fin - inicio >= 5:  # Ancho mínimo muy bajo
                    columnas_candidatas.append([inicio, fin])
                inicio = None

    if inicio is not None:
        fin = len(hay_texto)
        if fin - inicio >= 5:
            columnas_candidatas.append([inicio, fin])

    if not columnas_candidatas:
        return []

    # Paso 2: Calcular estadísticas de las columnas candidatas
    anchos = [c[1] - c[0] for c in columnas_candidatas]
    ancho_medio = np.median(anchos)
    
    print(f"    Columnas candidatas: {len(columnas_candidatas)}, ancho medio: {ancho_medio:.1f}px")

    # Paso 3: Calcular umbrales adaptativos
    ancho_minimo = ancho_medio * ANCHO_MINIMO_COLUMNA_RELATIVO
    hueco_minimo = ancho_medio * HUECO_MINIMO_RELATIVO
    ancho_furigana = ancho_medio * ANCHO_FUSION_FURIGANA_RELATIVO

    print(f"    Umbrales adaptativos:")
    print(f"      Ancho mínimo: {ancho_minimo:.1f}px")
    print(f"      Hueco mínimo: {hueco_minimo:.1f}px")
    print(f"      Ancho furigana: {ancho_furigana:.1f}px")

    # Paso 4: Filtrar columnas válidas
    columnas_filtradas = []
    for c in columnas_candidatas:
        ancho = c[1] - c[0]
        if ancho >= ancho_minimo:
            columnas_filtradas.append(c)

    # Paso 5: Filtrar furigana
    columnas_finales = [c for c in columnas_filtradas if (c[1] - c[0]) >= ancho_furigana]

    # Paso 6: Agregar padding
    ancho_img = imagen_cv.shape[1]
    columnas_finales = [(max(0, a - PADDING), min(ancho_img, b + PADDING)) for a, b in columnas_finales]

    # Orden de lectura japonés: derecha -> izquierda
    columnas_finales.sort(key=lambda c: c[0], reverse=True)

    return columnas_finales


def encontrar_extremos_tinta(proyeccion):
    indices = np.nonzero(proyeccion > 0)[0]
    if len(indices) == 0:
        return None
    return int(indices[0]), int(indices[-1])


def dividir_columna_larga(imagen_cv, x_inicio, x_fin):
    # Descontamos el PADDING para obtener el ancho real del cuerpo de texto
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

    # En japonés vertical, 1 carácter ≈ 1 cuadrado de lado "ancho_real_texto"
    caracteres_estimados = alto_texto / ancho_real_texto

    # Si la frase estimada tiene menos o igual caracteres que el límite, no se corta
    if caracteres_estimados <= MAX_CARACTERES_POR_TRAMO:
        y_min_pad = max(0, y_min - PADDING_VERTICAL)
        y_max_pad = min(alto_imagen, y_max + PADDING_VERTICAL)
        return [(y_min_pad, y_max_pad)]

    # Si excede el límite, calculamos cuántos tramos se requieren
    n_tramos = math.ceil(caracteres_estimados / MAX_CARACTERES_POR_TRAMO)
    
    puntos_corte = [max(0, y_min - PADDING_VERTICAL)]
    for i in range(1, n_tramos):
        y_ideal = y_min + int(alto_texto * i / n_tramos)
        ventana_inicio = max(y_min, y_ideal - VENTANA_BUSQUEDA_CORTE)
        ventana_fin = min(y_max, y_ideal + VENTANA_BUSQUEDA_CORTE)
        
        sub = proyeccion[ventana_inicio:ventana_fin]
        # Se busca la fila dentro de la ventana con menor densidad de tinta (espacio blanco entre caracteres)
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


def guardar_debug(imagen_cv, columnas_con_tramos, ruta_salida):
    debug_img = imagen_cv.copy()
    for i, tramos in enumerate(columnas_con_tramos):
        for j, (a, b, y1, y2) in enumerate(tramos):
            etiqueta = str(i) if len(tramos) == 1 else f"{i}.{j + 1}"
            cv2.rectangle(debug_img, (a, y1), (b, max(y1 + 1, y2 - 1)), (0, 0, 255), 2)
            cv2.putText(debug_img, etiqueta, (a + 2, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    guardar_imagen_cv(ruta_salida, debug_img)


def procesar_pagina(mocr, ruta_imagen):
    imagen_cv = leer_imagen_cv(ruta_imagen)
    if imagen_cv is None:
        raise ValueError(f"No se pudo leer la imagen: {ruta_imagen}")

    offset_y = 0
    if DETECTAR_ENCABEZADO:
        imagen_cv, offset_y = recortar_encabezado(imagen_cv)

    columnas_con_tramos = generar_bloques(imagen_cv)

    if MODO_DEBUG:
        nombre = os.path.splitext(os.path.basename(ruta_imagen))[0]
        guardar_debug(imagen_cv, columnas_con_tramos, os.path.join(RUTA_DEBUG, f"{nombre}_debug.png"))
        return None

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
    imagenes = [f for f in os.listdir(RUTA_IMAGENES)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
    imagenes.sort(key=orden_natural)

    if not imagenes:
        print(f"No se encontraron imágenes en '{RUTA_IMAGENES}'")
        return

    print(f"Se encontraron {len(imagenes)} imágenes.")

    mocr = None
    if not MODO_DEBUG:
        print("Inicializando Manga OCR...")
        mocr = MangaOcr()
        print("¡OCR listo!")
    else:
        print("MODO_DEBUG activo: solo se generarán imágenes con las columnas marcadas.")

    textos_paginas = []

    for nombre in imagenes:
        ruta_imagen = os.path.join(RUTA_IMAGENES, nombre)
        nombre_base = os.path.splitext(nombre)[0]
        print(f"Procesando: {nombre}")

        try:
            texto = procesar_pagina(mocr, ruta_imagen)
        except Exception as e:
            print(f"  Error con {nombre}: {e}")
            continue

        if MODO_DEBUG:
            continue

        ruta_txt = os.path.join(RUTA_SALIDA_TXT, f"{nombre_base}.txt")
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write(texto)
        textos_paginas.append(texto)
        print(f"  Guardado: {ruta_txt}")

    if MODO_DEBUG:
        print(f"\nRevisa las imágenes en: {RUTA_DEBUG}")
        print("\nParámetros adaptativos:")
        print(f"  ANCHO_MINIMO_COLUMNA_RELATIVO = {ANCHO_MINIMO_COLUMNA_RELATIVO}")
        print(f"  HUECO_MINIMO_RELATIVO = {HUECO_MINIMO_RELATIVO}")
        print(f"  ANCHO_FUSION_FURIGANA_RELATIVO = {ANCHO_FUSION_FURIGANA_RELATIVO}")
    else:
        if GENERAR_TXT_MAESTRO:
            with open(ARCHIVO_MAESTRO, "w", encoding="utf-8") as f:
                f.write("\n\n".join(textos_paginas))
            print(f"\n¡Procesamiento completado!")
            print(f"Txt por página en: {RUTA_SALIDA_TXT}")
            print(f"Txt maestro en: {ARCHIVO_MAESTRO}")
        else:
            print(f"\n¡Procesamiento completado! Txt por página en: {RUTA_SALIDA_TXT}")


if __name__ == "__main__":
    main()