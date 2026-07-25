import os
import re
from ebooklib import epub
import tkinter as tk
from tkinter import filedialog

# ==============================================================================
# 1. CONFIGURACIÓN DINÁMICA DE RUTAS Y DATOS DEL LIBRO
# ==============================================================================
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()

print("Por favor, selecciona la carpeta del volumen (ej. [豊田 巧] RAIL WARS! 第02巻)...")
ruta_seleccionada = filedialog.askdirectory(title="Selecciona la carpeta del volumen")

if not ruta_seleccionada:
    raise ValueError("No se seleccionó ninguna carpeta. El script ha sido cancelado.")

ruta_volumen = os.path.normpath(ruta_seleccionada)

subcarpetas = [f for f in os.listdir(ruta_volumen) if os.path.isdir(os.path.join(ruta_volumen, f))]
if os.path.basename(ruta_volumen) in subcarpetas:
    ruta_volumen = os.path.join(ruta_volumen, os.path.basename(ruta_volumen))

nombre_carpeta = os.path.basename(ruta_volumen)
match_vol = re.search(r'第(\d+)巻', nombre_carpeta)
num_vol = match_vol.group(1) if match_vol else "02"

ruta_base_serie = "C:/Users/JUDAPITEC/Documents/David/Halo Novelas/ライトノベル/RAIL WARS! -日本國有鉄道公安隊/"
dir_dist = os.path.join(ruta_base_serie, "dist")

DIR_TXT = os.path.join(ruta_volumen, "Correccion", "Corregido") + "/"
DIR_IMG = os.path.join(ruta_volumen, "Imagenes") + "/"

RUTA_INDICE_TXT = os.path.join(DIR_TXT, "indice.txt")
if not os.path.exists(RUTA_INDICE_TXT):
    RUTA_INDICE_TXT = os.path.join(DIR_TXT, "Indice.txt")

RUTA_EPUB_SALIDA = os.path.join(dir_dist, f"RAIL_WARS_Vol_{num_vol}.epub")

os.makedirs(DIR_TXT, exist_ok=True)
os.makedirs(DIR_IMG, exist_ok=True)
os.makedirs(dir_dist, exist_ok=True)

print(f"\n[✓] Volumen detectado: {nombre_carpeta} (Vol. {num_vol})")
print(f"    • TXT Corregidos: {DIR_TXT}")
print(f"    • Imágenes: {DIR_IMG}")
print(f"    • Archivo índice: {RUTA_INDICE_TXT}")
print(f"    • EPUB de salida: {RUTA_EPUB_SALIDA}\n")


# ==============================================================================
# 2. FUNCIONES AUXILIARES Y PARSER DE ÍNDICE
# ==============================================================================
def fullwidth_to_int(texto_num):
    """Convierte números japoneses y letras de ancho completo (incluyendo O como cero) a enteros."""
    full_digits = '０１２３４５６７８９Ｏｏ'
    ascii_digits = '012345678900'
    trans = str.maketrans(full_digits, ascii_digits)
    return int(texto_num.translate(trans))


def cargar_portadas_capitulo_desde_txt(ruta_txt, offset_paginas=14):
    portadas_capitulo = {}
    if not os.path.exists(ruta_txt):
        print(f"[!] ADVERTENCIA: No se encontró el índice en: {ruta_txt}")
        return portadas_capitulo

    with open(ruta_txt, "r", encoding="utf-8", errors="ignore") as f:
        lineas = f.readlines()

    # Regex universal ultra-flexible: captura cualquier código inicial, título, puntos/espacios y la P (normal o ancha)
    patron = re.compile(r"^\s*([^\s]+[\s ]+.+?)[．\.・\s]+[pPｐＰ]([０-９Ｏｏ\d]+)", re.UNICODE)

    for linea in lineas:
        linea_clean = linea.strip()
        coincidencia = patron.search(linea_clean)
        if coincidencia:
            titulo = coincidencia.group(1).strip()
            pag_str = coincidencia.group(2)
            try:
                pag_indice = fullwidth_to_int(pag_str)
                pag_real = pag_indice + offset_paginas
                portadas_capitulo[pag_real] = titulo
            except Exception as e:
                print(f"[!] Error procesando página '{pag_str}': {e}")

    print(f"\n[✓] CAPÍTULOS DETECTADOS DESDE ÍNDICE ({len(portadas_capitulo)}):")
    for pag, tit in portadas_capitulo.items():
        print(f"    • Imagen Portada: {pag:03d} | Texto inicia en: {pag+1:03d}.txt -> {tit}")
    print("-" * 50)
    return portadas_capitulo


PORTADAS_CAPITULO_AUTO = cargar_portadas_capitulo_desde_txt(RUTA_INDICE_TXT, offset_paginas=14)

ESTRUCTURA_VOL = {
    "titulo": f"RAIL WARS !  {num_vol} 日本國有鉄道公安隊-",
    "autor": "豊田 巧",
    "idioma": "ja",
    "portada": 5,
    "ilustraciones_color": list(range(11, 15)),
    "rango_texto": (15, 309),
    "portadas_capitulo": PORTADAS_CAPITULO_AUTO,
    "paginas_solo_imagen": [14, 46, 78, 96, 120, 158, 164, 206, 250, 261, 262, 270],
    "ilustraciones_finales": list(range(295, 305)),
}


def buscar_archivo_txt(num_pagina, dir_txt):
    formatos = [f"{num_pagina:03d}.txt", f"{num_pagina:02d}.txt", f"{num_pagina}.txt"]
    for fmt in formatos:
        ruta = os.path.join(dir_txt, fmt)
        if os.path.exists(ruta):
            return ruta
    return None


def buscar_archivo_imagen(num_pagina, dir_imagenes):
    formatos = [f"{num_pagina:03d}", f"{num_pagina:02d}", f"{num_pagina}"]
    extensiones = [".jpg", ".jpeg", ".png", ".webp"]

    for fmt in formatos:
        for ext in extensiones:
            nombre = f"{fmt}{ext}"
            ruta = os.path.join(dir_imagenes, nombre)
            if os.path.exists(ruta):
                return ruta, nombre
    return None, None


def crear_css():
    style = """
    @page { margin: 5px; }
    body {
        margin: 0;
        padding: 10px;
        font-family: "Hiragino Mincho ProN", "YuMincho", "MS Mincho", serif;
        writing-mode: vertical-rl;
        -webkit-writing-mode: vertical-rl;
        line-height: 1.8;
    }
    p {
        text-indent: 1em;
        margin-top: 0;
        margin-bottom: 0;
        text-align: justify;
    }
    .img-contenedor {
        text-align: center;
        page-break-before: always;
        page-break-after: always;
        margin: 0 auto;
        height: 100vh;
        writing-mode: horizontal-tb;
    }
    .img-contenedor img {
        max-width: 100%;
        max-height: 98vh;
        object-fit: contain;
    }
    .img-inline {
        text-align: center;
        margin: 1em 0;
        writing-mode: horizontal-tb;
    }
    .img-inline img {
        max-width: 100%;
        height: auto;
    }
    """
    return epub.EpubItem(
        uid="style_nav",
        file_name="style/style.css",
        media_type="text/css",
        content=style,
    )


# ==============================================================================
# 3. PROCESAMIENTO Y ARMADO DEL EPUB
# ==============================================================================
def construir_epub():
    print("Iniciando construcción del EPUB...\n")
    book = epub.EpubBook()

    book.set_title(ESTRUCTURA_VOL["titulo"])
    book.set_language(ESTRUCTURA_VOL["idioma"])
    book.add_author(ESTRUCTURA_VOL["autor"])

    css = crear_css()
    book.add_item(css)

    spine = []
    toc = []
    items_imagenes_cargadas = {}

    def registrar_imagen(num_pagi):
        if num_pagi in items_imagenes_cargadas:
            return items_imagenes_cargadas[num_pagi]

        ruta_img, nombre_img = buscar_archivo_imagen(num_pagi, DIR_IMG)
        if ruta_img and os.path.exists(ruta_img):
            with open(ruta_img, "rb") as f:
                contenido = f.read()

            ext = os.path.splitext(nombre_img)[1].lower()
            media_type = "image/png" if ext == ".png" else "image/jpeg"

            img_item = epub.EpubItem(
                uid=f"img_{num_pagi}",
                file_name=f"images/{nombre_img}",
                media_type=media_type,
                content=contenido,
            )
            book.add_item(img_item)
            items_imagenes_cargadas[num_pagi] = nombre_img
            return nombre_img
        return None

    # --- A. Portada Principal ---
    ruta_cover, nombre_cover = buscar_archivo_imagen(ESTRUCTURA_VOL["portada"], DIR_IMG)
    if ruta_cover and os.path.exists(ruta_cover):
        with open(ruta_cover, "rb") as f:
            cover_bytes = f.read()
        book.set_cover(f"images/{nombre_cover}", cover_bytes)
        items_imagenes_cargadas[ESTRUCTURA_VOL["portada"]] = nombre_cover

        cover_page = epub.EpubHtml(
            title="Portada",
            file_name="text/cover.xhtml",
            content=f"""<html><head><link rel="stylesheet" href="../style/style.css" type="text/css"/></head>
            <body>
                <div class="img-contenedor">
                    <img src="../images/{nombre_cover}" alt="Portada"/>
                </div>
            </body></html>"""
        )
        cover_page.add_item(css)
        book.add_item(cover_page)
        spine.append(cover_page)

    # --- B. Ilustraciones a Color ---
    for paf in ESTRUCTURA_VOL["ilustraciones_color"]:
        nombre_img = registrar_imagen(paf)
        if nombre_img:
            html_content = f"""<html><head><link rel="stylesheet" href="../style/style.css" type="text/css"/></head>
            <body>
                <div class="img-contenedor">
                    <img src="../images/{nombre_img}" alt="Color {paf}"/>
                </div>
            </body></html>"""
            item = epub.EpubHtml(
                title=f"Color {paf}",
                file_name=f"text/color_{paf:03d}.xhtml",
                content=html_content,
            )
            item.add_item(css)
            book.add_item(item)
            spine.append(item)

    spine.append("nav")

    # --- C. Texto Principal y Portadas de Capítulo ---
    capitulo_actual = None
    contenido_capitulo_html = ""
    num_capitulo = 0

    inicio_txt, fin_txt = ESTRUCTURA_VOL["rango_texto"]

    for pag in range(inicio_txt, fin_txt + 1):
        if pag in ESTRUCTURA_VOL["portadas_capitulo"]:
            if capitulo_actual:
                capitulo_actual.content = f"<html><head><link rel='stylesheet' href='../style/style.css' type='text/css'/></head><body>{contenido_capitulo_html}</body></html>"
                book.add_item(capitulo_actual)
                spine.append(capitulo_actual)
                toc.append(capitulo_actual)

            num_capitulo += 1
            titulo_capitulo_actual = ESTRUCTURA_VOL["portadas_capitulo"][pag]
            capitulo_actual = epub.EpubHtml(
                title=titulo_capitulo_actual,
                file_name=f"text/capitulo_{num_capitulo:02d}.xhtml",
            )
            capitulo_actual.add_item(css)
            contenido_capitulo_html = ""

            print(f"[+] Capitulo {num_capitulo}: '{titulo_capitulo_actual}' (Portada en Pág {pag})")

            nombre_img_cap = registrar_imagen(pag)
            if nombre_img_cap:
                contenido_capitulo_html += f"""
                <div class="img-contenedor">
                    <img src="../images/{nombre_img_cap}" alt="{titulo_capitulo_actual}"/>
                </div>
                """

        elif pag in ESTRUCTURA_VOL["paginas_solo_imagen"]:
            nombre_img_int = registrar_imagen(pag)
            if nombre_img_int:
                contenido_capitulo_html += f"""
                <div class="img-inline">
                    <img src="../images/{nombre_img_int}" alt="Ilustración {pag}"/>
                </div>
                """

        if pag not in ESTRUCTURA_VOL["paginas_solo_imagen"]:
            ruta_txt = buscar_archivo_txt(pag, DIR_TXT)
            if ruta_txt:
                with open(ruta_txt, "r", encoding="utf-8", errors="ignore") as f:
                    lineas = f.readlines()

                for linea in lineas:
                    linea_clean = linea.strip()
                    if linea_clean:
                        contenido_capitulo_html += f"<p>{linea_clean}</p>\n"

    if capitulo_actual:
        capitulo_actual.content = f"<html><head><link rel='stylesheet' href='../style/style.css' type='text/css'/></head><body>{contenido_capitulo_html}</body></html>"
        book.add_item(capitulo_actual)
        spine.append(capitulo_actual)
        toc.append(capitulo_actual)

    # --- D. Ilustraciones Finales ---
    for paf in ESTRUCTURA_VOL["ilustraciones_finales"]:
        nombre_img = registrar_imagen(paf)
        if nombre_img:
            html_content = f"""<html><head><link rel="stylesheet" href="../style/style.css" type="text/css"/></head>
            <body>
                <div class="img-contenedor">
                    <img src="../images/{nombre_img}" alt="Final {paf}"/>
                </div>
            </body></html>"""
            item = epub.EpubHtml(
                title=f"Final {paf}",
                file_name=f"text/final_{paf:03d}.xhtml",
                content=html_content,
            )
            item.add_item(css)
            book.add_item(item)
            spine.append(item)

    # --- E. Exportar ---
    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    os.makedirs(os.path.dirname(RUTA_EPUB_SALIDA), exist_ok=True)
    epub.write_epub(RUTA_EPUB_SALIDA, book, {})
    print(f"\n¡EPUB generado con éxito en!: {RUTA_EPUB_SALIDA}")


if __name__ == "__main__":
    construir_epub()