import os
import ast
from collections import defaultdict

RUTA_SRC = r"C:\proyectos\rsa_sismologia\src"

CATEGORIAS = {
    "qt": ["PyQt5", "QtCore", "QtWidgets"],
    "numerico": ["numpy"],
    "sismologia": ["obspy"],
    "graficos": ["matplotlib"],
    "io": ["os", "pathlib", "glob", "json", "pickle"],
    "rsa": ["rsa_"]
}

def obtener_archivos_py(directorio):

    archivos = []

    for root, _, files in os.walk(directorio):
        for f in files:
            if f.endswith(".py"):
                archivos.append(os.path.join(root, f))

    return archivos


def modulo_relativo(path):

    return os.path.relpath(path, RUTA_SRC).replace("\\", "/")


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


def clasificar_imports(imports):

    categorias = set()

    for imp in imports:

        for categoria, patrones in CATEGORIAS.items():

            for p in patrones:

                if imp.startswith(p):
                    categorias.add(categoria)

    return categorias


def analizar():

    archivos = obtener_archivos_py(RUTA_SRC)

    resultado = {}

    for archivo in archivos:

        rel = modulo_relativo(archivo)

        imports = extraer_imports(archivo)

        categorias = clasificar_imports(imports)

        resultado[rel] = {
            "imports": imports,
            "categorias": categorias
        }

    return resultado


def generar_reporte():

    datos = analizar()

    with open("reporte_librerias_rsa.md", "w", encoding="utf-8") as f:

        f.write("# Auditoría de uso de librerías\n\n")

        for mod, info in sorted(datos.items()):

            f.write(f"## {mod}\n\n")

            f.write("Categorías detectadas:\n\n")

            for c in sorted(info["categorias"]):
                f.write(f"- {c}\n")

            f.write("\nImports:\n\n")

            for i in sorted(info["imports"]):
                f.write(f"- {i}\n")

            f.write("\n\n")

    print("Reporte generado: reporte_librerias_rsa.md")


if __name__ == "__main__":
    generar_reporte()
