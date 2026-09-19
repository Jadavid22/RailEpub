import os
import re
from ebooklib import epub
import tkinter as tk
from tkinter import filedialog


# ==============================================================================
# 1. SELECCIÓN DE CARPETAS Y CONFIGURACIÓN INICIAL
# ==============================================================================
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()

print("Por favor, selecciona la carpeta raíz del volumen...")
ruta_seleccionada = filedialog.askdirectory(title="1. Selecciona la carpeta raíz del volumen")

if not ruta_seleccionada:
    raise ValueError("No se seleccionó la carpeta del volumen. El script ha sido cancelado.")

ruta_volumen = os.path.normpath(ruta_seleccionada)
nombre_carpeta = os.path.basename(ruta_volumen)

titulo_volumen = nombre_carpeta

match_vol = (
    re.search(r'第(\d+)巻', nombre_carpeta) or 
    re.search(r'Vol(?:ume|\.|\_|\s*)?(\d+)', nombre_carpeta, re.IGNORECASE) or 
    re.search(r'(\d+)', nombre_carpeta)
)

if match_vol:
    num_vol = match_vol.group(1).zfill(2)
else:
    num_vol = "01"

print(f"[✓] Título detectado: '{titulo_volumen}'")
print(f"[✓] Número de volumen detectado: Vol. {num_vol}")

print("\n" + "=" * 65)
print(" CONFIGURACIÓN DEL VOLUMEN")
print("=" * 65)

entrada_autor = input("-> Ingresa el nombre del autor [presiona Enter para '豊田 巧']: ").strip()
AUTOR_VOLUMEN = entrada_autor if entrada_autor else "豊田 巧"
print(f"[✓] Autor configurado: {AUTOR_VOLUMEN}")

print("\n Explicación Desfase: (Número de archivo TXT Cap 1) - (Pág Cap 1 en Indice.txt)")
print(" Ejemplo: Si el Cap 1 está en '017.txt' y el índice dice 'P.2', el desfase es 15.")

entrada_desfase = input("-> Ingresa el número de desfase [presiona Enter para usar 14]: ").strip()

if entrada_desfase == "":
    DESFASE_PAGINAS = 14
else:
    try:
        DESFASE_PAGINAS = int(entrada_desfase)
    except ValueError:
        print("[!] Entrada no válida. Se usará el desfase por defecto (14).")
        DESFASE_PAGINAS = 14

print(f"[✓] Desfase configurado en: +{DESFASE_PAGINAS}")
print("-" * 65 + "\n")

print("Por favor, selecciona la carpeta donde se encuentran los archivos TXT...")
sugerencia_txt = os.path.join(ruta_volumen, "TXT")
if not os.path.exists(sugerencia_txt):
    sugerencia_txt = os.path.join(ruta_volumen, "Correccion", "Corregido")
if not os.path.exists(sugerencia_txt):
    sugerencia_txt = ruta_volumen

ruta_txt_sel = filedialog.askdirectory(
    title="2. Selecciona la carpeta que contiene los archivos TXT",
    initialdir=sugerencia_txt
)

if not ruta_txt_sel:
    raise ValueError("No se seleccionó la carpeta de los archivos TXT. El script ha sido cancelado.")

DIR_TXT = os.path.normpath(ruta_txt_sel) + "/"

print("Por favor, selecciona la carpeta donde deseas guardar el EPUB...")
dir_dist_sel = filedialog.askdirectory(
    title="3. Selecciona la carpeta de destino para el EPUB",
    initialdir=ruta_volumen
)

if not dir_dist_sel:
    raise ValueError("No se seleccionó la carpeta de destino del EPUB. El script ha sido cancelado.")

DIR_IMG = os.path.join(ruta_volumen, "Imagenes") + "/"

RUTA_INDICE_TXT = os.path.join(DIR_TXT, "indice.txt")
if not os.path.exists(RUTA_INDICE_TXT):
    RUTA_INDICE_TXT = os.path.join(DIR_TXT, "Indice.txt")

# NOMBRE DE ARCHIVO AUTOMATIZADO DE SALIDA
RUTA_EPUB_SALIDA = os.path.join(dir_dist_sel, f"RAIL_WARS_Vol_{num_vol}.epub")

os.makedirs(DIR_TXT, exist_ok=True)
os.makedirs(DIR_IMG, exist_ok=True)


# ==============================================================================
# 2. FUNCIONES AUXILIARES DE PROCESAMIENTO
# ==============================================================================
def buscar_archivo_txt(num_pagina, dir_txt):
    if not os.path.exists(dir_txt):
        return None

    patron = re.compile(rf'^0*{num_pagina}\.txt$', re.IGNORECASE)

    for fn in os.listdir(dir_txt):
        if patron.match(fn):
            return os.path.join(dir_txt, fn)
    return None


def buscar_archivo_imagen(num_pagina, dir_imagenes):
    if not os.path.exists(dir_imagenes):
        return None, None

    patron = re.compile(rf'^0*{num_pagina}(?:_.*)?\.(jpg|jpeg|png|webp)$', re.IGNORECASE)

    for fn in os.listdir(dir_imagenes):
        if patron.match(fn):
            return os.path.join(dir_imagenes, fn), fn
    return None, None


def analizar_carpeta_imagenes(dir_img):
    imagenes_encontradas = {}
    if os.path.exists(dir_img):
        for fn in os.listdir(dir_img):
            match = re.match(r'^(\d+)', fn)
            if match:
                num = int(match.group(1))
                if num not in imagenes_encontradas or "_COLOR" in fn.upper():
                    imagenes_encontradas[num] = fn

    if not imagenes_encontradas:
        return 5, [11, 12, 13, 14]

    numeros_ordenados = sorted(imagenes_encontradas.keys())
    
    num_portada = numeros_ordenados[0]
    
    num_color = [
        n for n, fn in imagenes_encontradas.items() 
        if n != num_portada and ("COLOR" in fn.upper() or n < 15)
    ]
    num_color.sort()

    print(f"[✓] Portada detectada: {imagenes_encontradas[num_portada]} (Pág {num_portada})")
    print(f"[✓] Ilustraciones a color detectadas: {[imagenes_encontradas[n] for n in num_color]}")
    return num_portada, num_color


NUM_PORTADA, ILUSTRACIONES_COLOR = analizar_carpeta_imagenes(DIR_IMG)


def fullwidth_to_int(texto_num):
    full_digits = '０１２３４５６７８９Ｏｏ'
    ascii_digits = '012345678900'
    trans = str.maketrans(full_digits, ascii_digits)
    return int(texto_num.translate(trans))


def unir_lineas_parrafo(lineas):
    SIGNOS_CIERRE = set('。！？…」）』】〉》"\'')
    parrafos = []
    actual = ""

    for linea in lineas:
        linea_clean = linea.strip()
        if not linea_clean:
            if actual:
                parrafos.append(actual)
                actual = ""
            continue

        if actual:
            actual += linea_clean
        else:
            actual = linea_clean

        if linea_clean and linea_clean[-1] in SIGNOS_CIERRE:
            parrafos.append(actual)
            actual = ""

    if actual:
        parrafos.append(actual)

    return parrafos


def cargar_portadas_capitulo(ruta_indice_txt, offset=12):
    if not os.path.exists(ruta_indice_txt):
        print(f"[!] No se encontró el archivo de índice en: {ruta_indice_txt}")
        return {}

    with open(ruta_indice_txt, "r", encoding="utf-8", errors="ignore") as f:
        lineas = f.readlines()

    patron = re.compile(r"^\s*([^\s]+[\s ]+.+?)[．\.・\s]+[pPｐＰ]([０-９Ｏｏ\d]+)", re.UNICODE)
    portadas_capitulo = {}
    idx_cap = 1

    print(f"\n[✓] PROCESANDO ÍNDICE CON DESFASE (+{offset}):")

    for linea in lineas:
        coincidencia = patron.search(linea.strip())
        if coincidencia:
            titulo = coincidencia.group(1).strip()
            pag_impresa = fullwidth_to_int(coincidencia.group(2))
            pag_real = pag_impresa + offset

            print(f"    • Cap {idx_cap}: '{titulo}' -> Archivo {pag_real:03d} (Pág Impresa: {pag_impresa} + {offset})")

            portadas_capitulo[pag_real] = titulo
            idx_cap += 1

    print("-" * 60)
    return dict(sorted(portadas_capitulo.items()))


PORTADAS_CAPITULO = cargar_portadas_capitulo(RUTA_INDICE_TXT, offset=DESFASE_PAGINAS)

ESTRUCTURA_VOL = {
    "titulo": titulo_volumen,
    "autor": AUTOR_VOLUMEN,
    "idioma": "ja",
    "portada": NUM_PORTADA,
    "ilustraciones_color": ILUSTRACIONES_COLOR,
    "portadas_capitulo": PORTADAS_CAPITULO,
    "ilustraciones_finales": [],
}


def obtener_rango_paginas(dir_txt, portadas_capitulo):
    paginas = set(portadas_capitulo.keys())
    if os.path.exists(dir_txt):
        for archivo in os.listdir(dir_txt):
            match = re.search(r'^(\d+)\.txt$', archivo, re.IGNORECASE)
            if match:
                paginas.add(int(match.group(1)))
    if not paginas:
        return 1, 350
    return min(paginas), max(paginas)


def crear_css():
    style = """
    @page { 
        margin: 0; 
    }
    html, body {
        margin: 0;
        padding: 0;
        height: 100%;
    }

    body.pagina-texto {
        padding: 15px 10px;
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

    body.pagina-imagen {
        margin: 0;
        padding: 0;
        writing-mode: horizontal-tb;
        -webkit-writing-mode: horizontal-tb;
        text-align: center;
        background-color: #ffffff;
    }

    .img-contenedor {
        width: 100%;
        height: 100vh;
        margin: 0 auto;
        padding: 0;
        display: block;
        text-align: center;
        page-break-inside: avoid;
        page-break-before: always;
        page-break-after: always;
    }

    .img-contenedor img {
        max-width: 100%;
        max-height: 95vh;
        width: auto;
        height: auto;
        margin: auto;
        vertical-align: middle;
        object-fit: contain;
    }

    .img-inline {
        text-align: center;
        margin: 1em auto;
        page-break-inside: avoid;
        page-break-before: always;
        page-break-after: always;
        writing-mode: horizontal-tb;
        -webkit-writing-mode: horizontal-tb;
    }

    .img-inline img {
        max-width: 100%;
        max-height: 85vh;
        width: auto;
        height: auto;
        object-fit: contain;
    }
    """
    return epub.EpubItem(
        uid="style_nav",
        file_name="style/style.css",
        media_type="text/css",
        content=style,
    )


# ==============================================================================
# 3. CONSTRUCCIÓN Y EXPORTACIÓN DEL EPUB
# ==============================================================================
def construir_epub():
    print("Iniciando construcción del EPUB...\n")
    book = epub.EpubBook()

    book.set_title(ESTRUCTURA_VOL["titulo"])
    book.set_language(ESTRUCTURA_VOL["idioma"])
    
    # Se agrega el autor únicamente si fue especificado/definido
    if ESTRUCTURA_VOL["autor"]:
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
            <body class="pagina-imagen">
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
            <body class="pagina-imagen">
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

    capitulo_actual = None
    contenido_capitulo_html = ""
    num_capitulo = 0

    min_pag, max_pag = obtener_rango_paginas(DIR_TXT, ESTRUCTURA_VOL["portadas_capitulo"])
    paginas_omitir = {ESTRUCTURA_VOL["portada"]} | set(ESTRUCTURA_VOL["ilustraciones_color"]) | set(ESTRUCTURA_VOL["ilustraciones_finales"])

    for pag in range(min_pag, max_pag + 1):
        if pag in paginas_omitir:
            continue

        if pag in ESTRUCTURA_VOL["portadas_capitulo"]:
            if capitulo_actual and contenido_capitulo_html.strip():
                capitulo_actual.content = f"<html><head><link rel='stylesheet' href='../style/style.css' type='text/css'/></head><body class='pagina-texto'>{contenido_capitulo_html}</body></html>"
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

            print(f"[+] Capitulo {num_capitulo}: '{titulo_capitulo_actual}' -> Archivo TXT {pag:03d}")

        elif capitulo_actual is None:
            ruta_txt_check = buscar_archivo_txt(pag, DIR_TXT)
            if ruta_txt_check:
                num_capitulo += 1
                capitulo_actual = epub.EpubHtml(
                    title="Inicio",
                    file_name=f"text/capitulo_{num_capitulo:02d}.xhtml",
                )
                capitulo_actual.add_item(css)
                contenido_capitulo_html = ""

        # Si esta página tiene ilustración en la carpeta 'Imagenes', se inserta aquí
        nombre_img = registrar_imagen(pag)
        if nombre_img:
            contenido_capitulo_html += f"""
            <div class="img-inline">
                <img src="../images/{nombre_img}" alt="Ilustración {pag}"/>
            </div>
            """

        ruta_txt = buscar_archivo_txt(pag, DIR_TXT)
        if ruta_txt:
            with open(ruta_txt, "r", encoding="utf-8", errors="ignore") as f:
                lineas = f.readlines()

            parrafos = unir_lineas_parrafo(lineas)
            for parrafo in parrafos:
                contenido_capitulo_html += f"<p>{parrafo}</p>\n"

    # Guardar el último capítulo
    if capitulo_actual and contenido_capitulo_html.strip():
        capitulo_actual.content = f"<html><head><link rel='stylesheet' href='../style/style.css' type='text/css'/></head><body class='pagina-texto'>{contenido_capitulo_html}</body></html>"
        book.add_item(capitulo_actual)
        spine.append(capitulo_actual)
        toc.append(capitulo_actual)

    # --- D. Exportar EPUB ---
    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    os.makedirs(os.path.dirname(RUTA_EPUB_SALIDA), exist_ok=True)
    epub.write_epub(RUTA_EPUB_SALIDA, book, {})
    print(f"\n[✓] ¡EPUB generado con éxito!: {RUTA_EPUB_SALIDA}")


if __name__ == "__main__":
    construir_epub()