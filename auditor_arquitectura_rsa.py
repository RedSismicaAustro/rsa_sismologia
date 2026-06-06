# auditor_arquitectura_rsa.py

import os
import ast
from collections import defaultdict

RUTA_SRC = r"C:\proyectos\rsa_sismologia\src"
ARCHIVO_REPORTE = "reporte_arquitectura_rsa.md"

PAQUETES_INTERNOS = (
    "librerias",
    "subprogramas",
    "infraestructura",
    "ui"
)

def obtener_archivos_py(directorio):

    archivos = []

    for root, _, files in os.walk(directorio):
        for f in files:
            if f.endswith(".py"):
                archivos.append(os.path.join(root, f))

    return archivos


def modulo_relativo(path):

    return os.path.relpath(path, RUTA_SRC).replace("\\", "/")


def contar_lineas(path):

    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except:
        return 0


def contiene_qt(path):

    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()

        if "PyQt5" in txt or "QObject" in txt or "QRunnable" in txt or "pyqtSignal" in txt:
            return True

    except:
        pass

    return False


def extraer_imports(path):

    imports = []

    try:

        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

    except:
        pass

    return imports


def es_import_interno(modulo):

    return modulo.startswith(PAQUETES_INTERNOS)


def resolver_archivo(modulo):

    ruta_py = modulo.replace(".", "/") + ".py"
    ruta_init = modulo.replace(".", "/") + "/__init__.py"

    path1 = os.path.join(RUTA_SRC, ruta_py)
    path2 = os.path.join(RUTA_SRC, ruta_init)

    if os.path.isfile(path1):
        return ruta_py.replace("\\", "/")

    if os.path.isfile(path2):
        return ruta_init.replace("\\", "/")

    return None


def analizar():

    archivos = obtener_archivos_py(RUTA_SRC)

    mapa = {}
    lineas = {}
    usa_qt = []

    dependencias = defaultdict(set)
    dependientes = defaultdict(set)

    for a in archivos:

        rel = modulo_relativo(a)
        mapa[rel] = a

        lineas[rel] = contar_lineas(a)

        if contiene_qt(a):
            usa_qt.append(rel)

    for mod, path in mapa.items():

        imports = extraer_imports(path)

        for imp in imports:

            if not es_import_interno(imp):
                continue

            destino = resolver_archivo(imp)

            if destino and destino in mapa and destino != mod:

                dependencias[mod].add(destino)
                dependientes[destino].add(mod)

    return mapa, lineas, usa_qt, dependencias, dependientes


def generar_reporte():

    mapa, lineas, usa_qt, deps, dependientes = analizar()

    with open(ARCHIVO_REPORTE, "w", encoding="utf-8") as f:

        f.write("# Auditoría de Arquitectura RSA\n\n")

        f.write("## Archivos analizados\n\n")
        f.write(f"{len(mapa)} archivos Python\n\n")

        f.write("## Archivos grandes\n\n")

        grandes = sorted(lineas.items(), key=lambda x: x[1], reverse=True)

        for mod, l in grandes[:15]:
            if l > 400:
                f.write(f"- {mod} : {l} líneas\n")

        f.write("\n")

        f.write("## Uso de Qt dentro del proyecto\n\n")

        for mod in usa_qt:
            f.write(f"- {mod}\n")

        f.write("\n")

        f.write("## Módulos con más dependencias\n\n")

        ranking = sorted(deps.items(), key=lambda x: len(x[1]), reverse=True)

        for mod, d in ranking[:10]:
            f.write(f"- {mod} : {len(d)} dependencias\n")

        f.write("\n")

        f.write("## Módulos más utilizados\n\n")

        ranking = sorted(dependientes.items(), key=lambda x: len(x[1]), reverse=True)

        for mod, d in ranking[:10]:
            f.write(f"- {mod} : usado por {len(d)} módulos\n")

        f.write("\n")

        f.write("## Posibles puntos de refactorización\n\n")

        for mod, l in grandes:

            if l > 800:
                f.write(f"- {mod} : módulo muy grande ({l} líneas)\n")

        f.write("\n")

        f.write("## Dependencias internas\n\n")

        for mod, d in deps.items():

            if not d:
                continue

            f.write(f"### {mod}\n")

            for x in d:
                f.write(f"- {x}\n")

            f.write("\n")

    print("\nReporte generado:", ARCHIVO_REPORTE)


if __name__ == "__main__":
    generar_reporte()