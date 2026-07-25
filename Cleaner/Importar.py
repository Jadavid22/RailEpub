import os
import re
import json

# ================== CONFIGURACIÓN ==================
RUTA_GLOSARIO_TXT = "C:/Users/JUDAPITEC/Documents/David/Halo Novelas/ライトノベル/RAIL WARS! -日本國有鉄道公安隊/Correccion/GlosarioRailWars.txt"

RUTA_VOCABULARIO = "C:/Users/JUDAPITEC/Documents/David/Halo Novelas/ライトノベル/RAIL WARS! -日本國有鉄道公安隊/Correccion/vocabulario_serie.json"

# admite "—" o "-" como separador y () o （） para la lectura
PATRON_ENTRADA = re.compile(
    r'^([^\s(（]+)\s*(?:[\(（]([^\)）]+)[\)）])?\s*[—\-]\s*(.+)$'
)

# ================== CATEGORÍAS ==================

MAPA_CATEGORIAS = {
    "🏢 Organizaciones": ("organizaciones", "organizacion"),
    "🚉 Líneas ferroviarias": ("lineas", "linea"),
    "🚄 Series de trenes": ("series", "serie"),
    "🚂 Locomotoras": ("locomotoras", "locomotora"),
    "👤 Personajes": ("personajes", "personaje"),
}

CATEGORIA_DEFECTO = ("general", "general")


# ================== FUNCIONES ==================

def cargar_vocabulario():
    if os.path.exists(RUTA_VOCABULARIO):
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

        # Preparados para futuras versiones
        "aliases": existente.get("aliases", []),
        "errores": existente.get("errores", []),
        "confianza": existente.get("confianza", 1.0),
    }


# ================== MAIN ==================

def main():

    if not os.path.exists(RUTA_GLOSARIO_TXT):
        print(f"No se encontró el glosario en '{RUTA_GLOSARIO_TXT}'")
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

            categoria, tipo = MAPA_CATEGORIAS.get(
                categoria_actual,
                CATEGORIA_DEFECTO
            )

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

    os.makedirs(os.path.dirname(RUTA_VOCABULARIO), exist_ok=True)

    with open(RUTA_VOCABULARIO, "w", encoding="utf-8") as f:
        json.dump(vocabulario, f, ensure_ascii=False, indent=2)

    print(f"Términos nuevos: {agregados}")
    print(f"Términos actualizados: {actualizados}")
    print(f"Total de términos: {len(vocabulario)}")
    print(f"Vocabulario guardado en:\n{RUTA_VOCABULARIO}")


if __name__ == "__main__":
    main()