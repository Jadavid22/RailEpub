# RailEpub

**RailEpub** es una herramienta integral diseñada para automatizar la creación de libros en formato **EPUB** a partir de imágenes escaneadas de novelas ligeras en japonés.

---

## Módulos Principales

### 1. OCR (Escáner de Texto)
Es el componente central del procesamiento de imágenes, construido sobre [MangaOCR](https://github.com/kha-white/manga-ocr). 

* **Segmentación de imágenes:** Dado que MangaOCR suele presentar fallos al procesar imágenes verticales muy largas, el módulo realiza primero una segmentación dividiendo la página en secciones de tamaño mediano para maximizar la precisión del reconocimiento.
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

* **Estructura por capítulos:** Requiere que exista un archivo `Indice.txt` en la carpeta `TXT/`. Este archivo es crucial ya que define la división de capítulos de la novela (debido a que el OCR suele fallar en el índice, se debe verificar y corregir manualmente antes de empaquetar), un ejemplo es el siguiente:
  
 <img width="780" height="1200" alt="017" src="https://github.com/user-attachments/assets/259a0f30-a074-4ab1-bd37-b65f9705a009" />

  ```text
  目 次
  
  ＲＯＯＯ１ 国鉄リニア 出発進行 ............................................P005
  
  ＲＯＯＯ２ 一人だけの戦い 場内警戒 ........................................P089
  
  ＲＯＯＯ３ 迫る東京駅 非常警戒 ............................................P159
  
  ＲＯＯＯ４ 事件が終わり...... 停止位置よし！................................P279
  
  ```

* **Nombres y Metadatos:** Detecta automáticamente el nombre de la novela y el volumen desde el directorio raíz. Durante la ejecución, el programa solicitará el nombre del autor y el **desfase** (la diferencia numérica entre la página indicada en el índice y la numeración real del archivo `.txt`).
```text
Página del índice: 005
Archivo OCR:      009.txt
Desfase:          +4
```
* Al finalizar el proceso, exporta el libro listo para leer en la ubicación indicada.

<p center="align">
  <img width="950" alt="Generador EPUB" src="https://github.com/user-attachments/assets/926c11a6-c855-4cc6-bd0b-3e7b6f69d130" />
</p>

---
## Instalación y Uso

1. Descarga el archivo `.zip`  del repositorio: [GitHub - Jadavid22/RailEpub] con todos los archivos necesarios y extráelo en tu equipo.
2. Si no tienes instaladas las librerías necesarias, ejecuta el archivo `.bat` incluido y se instalarán automáticamente.
3. Luego, ejecuta el archivo **`RailEpub.exe`** y verás el siguiente menú en la terminal:

<p align="center">
  <img width="674" height="313" alt="Menú Consola RailEpub" src="https://github.com/user-attachments/assets/60758945-3b1b-4403-b3e6-51b7c7cdedfa" />
</p>

4. Selecciona la opción del menú que necesites según la etapa que vayas a procesar.

> **Nota:** No es necesario utilizar el módulo corrector para hacer el EPUB; siempre que tengas los archivos `.txt` en la carpeta correspondiente, podrás generar el libro sin problemas.

## Arquitectura de Carpetas Requerida

Para que el programa pueda procesar un volumen correctamente, la carpeta raíz debe mantener la siguiente estructura:

```text
📁 [Autor] Nombre de la Novela Vol. Num/
 ├── 📁 TXT/                        <-- Textos generados por el OCR
 │    └── 📄 Indice.txt             <-- Requerido: Lista de capítulos y páginas
 ├── 📁 Imagenes/                   <-- Ilustraciones y portadas extraídas
 └── 📁 Correccion/                 <-- Creado al ejecutar el módulo Cleaner
      ├── 📄 vocabulario_serie.json  <-- Vocabulario base para la novela
      ├── 📄 log_correcciones.txt   <-- Registro de cambios aplicados
      └── 📁 Corregido/             <-- Textos limpios para la generación del EPUB
```
## Limitaciones

RailEpub está orientado principalmente a novelas ligeras japonesas
con texto vertical.

El OCR puede presentar errores en:

- caracteres kanji visualmente similares;
- nombres propios poco frecuentes;
- texto extremadamente pequeño;
- páginas con diseños poco convencionales.

El módulo Cleaner reduce muchos de estos errores mediante un vocabulario específico de la obra y comparación aproximada de términos, además de reglas para evitar correcciones incorrectas.

## Resultado

El resultado final será un archivo EPUB que contiene:

- portada;
- capítulos organizados;
- texto OCR corregido;
- ilustraciones;
- metadatos del volumen;
- índice de navegación.

## Licencia
MIT License

## Autor
Jadavid22
