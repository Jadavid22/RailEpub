# RailEpub

**RailEpub** es una herramienta integral diseñada para automatizar la creación de libros en formato **EPUB** a partir de imágenes escaneadas de novelas ligeras en japonés.

---

## ⚙️ Módulos Principales

### 1. OCR (Escáner de Texto)
Es el componente central del procesamiento de imágenes, construido sobre [MangaOCR](https://github.com/kha-white/manga-ocr). 

* **Segmentación de imágenes:** Dado que MangaOCR suele presentar fallos al procesar imágenes verticales muy largas, el módulo realiza primero una disección dividiendo la página en secciones de tamaño mediano para maximizar la precisión del reconocimiento.
* **Filtrado automático:** Identifica páginas con ilustraciones (a color o blanco y negro) y las mueve a una carpeta dedicada de imágenes (`Imagenes/`), omitiendo la creación de archivos de texto vacíos para ellas.

<p center="align">
  <img width="784" alt="Proceso de disección OCR" src="https://github.com/user-attachments/assets/8157885f-6c9f-4709-84dd-3b58ddc1b3d3" />
</p>

---

### 2. Cleaner (Corrector de Texto)
Encargado de solucionar las confusiones comunes de kanjis similares producidas por el OCR. Se compone de tres scripts secuenciales:

1. **Importar (`Importar.py`):** Permite cargar un archivo `.txt` base con un diccionario manual de términos clave de la obra (nombres de personajes, locaciones, vehículos, etc.) categorizados, exportándolo como un `vocabulario_serie.json` estructurado.
2. **ConstructorV2 (`ConstructorV2.py`):** Analiza los archivos `.txt` generados por el OCR para extraer las palabras más frecuentes y nutrir el vocabulario JSON. Se recomienda revisar los primeros capítulos para alimentar este diccionario.
3. **Corrector (`Corrector.py`):** Procesa los archivos `.txt` del OCR aplicando reemplazos directos y aproximación Levenshtein contra el vocabulario. Para evitar falsos positivos:
   * Se inmunizan las palabras compuestas exclusivamente por **Katakana** u **Hiragana**.
   * Se protegen verbos, partículas y sustantivos comunes mediante análisis gramatical (**Janome**).
   * Genera una carpeta con los textos corregidos (`Correccion/Corregido/`) y un archivo `log_correcciones.txt` para auditoría.

---

### 3. EPUB (Generador de Libro)
Construye el archivo `.epub` final unificando el texto procesado y las imágenes extraídas.

* **Estructura por capítulos:** Requiere que exista un archivo `Indice.txt` en la carpeta `TXT/`. Este archivo es crucial ya que define la división de capítulos de la novela (debido a que el OCR suele fallar en el índice, se debe verificar y corregir manualmente antes de empaquetar).
* **Nombres y Metadatos:** Detecta automáticamente el nombre de la novela y el volumen desde el directorio raíz. Durante la ejecución, el programa solicitará el nombre del autor y el **desfase** (la diferencia numérica entre la página indicada en el índice y la numeración real del archivo `.txt`).
* Al finalizar el proceso, exporta el libro listo para leer en la ubicación indicada.

<p center="align">
  <img width="950" alt="Generador EPUB" src="https://github.com/user-attachments/assets/926c11a6-c855-4cc6-bd0b-3e7b6f69d130" />
</p>

---

## 📁 Arquitectura de Carpetas Requerida

Para que el programa pueda procesar un volumen correctamente, la carpeta raíz debe mantener la siguiente estructura:

```text
📁 [Autor] Nombre de la Novela Vol. 01/
 ├── 📁 TXT/                        <-- Textos generados por el OCR
 │    └── 📄 Indice.txt             <-- Requerido: Lista de capítulos y páginas
 ├── 📁 Imagenes/                   <-- Ilustraciones y portadas extraídas
 └── 📁 Correccion/                 <-- Creado al ejecutar el módulo Cleaner
      ├── 📄 vocabulario_serie.json  <-- Vocabulario base para la novela
      ├── 📄 log_correcciones.txt   <-- Registro de cambios aplicados
      └── 📁 Corregido/             <-- Textos limpios para la generación del EPUB

