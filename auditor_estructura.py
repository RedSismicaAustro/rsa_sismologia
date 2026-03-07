import os
import ast
import networkx as nx
from datetime import datetime

RUTA_REPO = r"C:\proyectos\rsa_sismologia"
CARPETA_ANALISIS = os.path.join(RUTA_REPO, "src")

UMBRAL_LINEAS = 500  # archivo grande (ajustable)
UMBRAL_DEPENDIENTES = 5  # muchos módulos dependen de él


def obtener_archivos_py(directorio):
    archivos = []
    for root, _, files in os.walk(directorio):
        for f in files:
            if f.endswith(".py"):
                archivos.append(os.path.join(root, f))
    return archivos


def modulo_relativo(path):
    return os.path.relpath(path, CARPETA_ANALISIS).replace("\\", "/")


def analizar_archivo(path):
    with open(path, "r", encoding="utf-8") as f:
        contenido = f.read()

    try:
        tree = ast.parse(contenido)
    except Exception:
        return [], 0, contenido

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    lineas = contenido.count("\n")
    return imports, lineas, contenido


def construir_grafo(archivos):
    G = nx.DiGraph()
    mapa = {}

    for archivo in archivos:
        mod = modulo_relativo(archivo)
        mapa[mod] = archivo
        G.add_node(mod)

    for mod, archivo in mapa.items():
        imports, _, _ = analizar_archivo(archivo)

        for imp in imports:
            imp_path = imp.replace(".", "/") + ".py"
            for posible_mod in mapa:
                if posible_mod.endswith(imp_path):
                    G.add_edge(mod, posible_mod)

    return G, mapa


def auditoria():
    archivos = obtener_archivos_py(CARPETA_ANALISIS)
    G, mapa = construir_grafo(archivos)

    reporte = []
    reporte.append("# Reporte Auditoría Estructural v2\n")
    reporte.append(f"Fecha: {datetime.now()}\n")

    # 1️⃣ Ciclos
    ciclos = list(nx.simple_cycles(G))
    reporte.append("## Ciclos Detectados\n")
    if ciclos:
        for ciclo in ciclos:
            reporte.append(" - " + " → ".join(ciclo))
    else:
        reporte.append("No se detectaron ciclos.")

    # 2️⃣ Qt en librerias
    reporte.append("\n## Uso de Qt dentro de librerias\n")
    for mod, path in mapa.items():
        if mod.startswith("librerias/"):
            _, _, contenido = analizar_archivo(path)
            if "PyQt5" in contenido or "QObject" in contenido or "QRunnable" in contenido:
                reporte.append(f" - {mod} usa Qt (mezcla de capa)")

    # 3️⃣ Violación de capa (librerias importa subprogramas)
    reporte.append("\n## Violaciones de capa (librerias → subprogramas)\n")
    for mod in G.nodes:
        if mod.startswith("librerias/"):
            for destino in G.successors(mod):
                if destino.startswith("subprogramas/"):
                    reporte.append(f" - {mod} importa {destino}")

    # 4️⃣ Archivos grandes
    reporte.append("\n## Archivos grandes (posible mezcla de responsabilidades)\n")
    for mod, path in mapa.items():
        _, lineas, _ = analizar_archivo(path)
        if lineas > UMBRAL_LINEAS:
            reporte.append(f" - {mod} tiene {lineas} líneas")

    # 5️⃣ Módulos con muchos dependientes
    reporte.append("\n## Módulos con muchos dependientes\n")
    for mod in G.nodes:
        dependientes = list(G.predecessors(mod))
        if len(dependientes) > UMBRAL_DEPENDIENTES:
            reporte.append(f" - {mod} es usado por {len(dependientes)} módulos")

    ruta_reporte = os.path.join(RUTA_REPO, "reporte_arquitectura_v2.md")
    with open(ruta_reporte, "w", encoding="utf-8") as f:
        f.write("\n".join(reporte))

    print("Auditoría completada.")
    print("Reporte generado en:", ruta_reporte)


if __name__ == "__main__":
    auditoria()