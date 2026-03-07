import os
import ast

RUTA_SRC = r"C:\proyectos\rsa_sismologia\src"


def obtener_archivos_py(directorio):

    archivos = []

    for root, _, files in os.walk(directorio):

        for f in files:

            if f.endswith(".py"):
                archivos.append(os.path.join(root, f))

    print("Archivos encontrados:", len(archivos))

    return archivos


def modulo_relativo(path):

    return os.path.relpath(path, RUTA_SRC).replace("\\", "/")


def obtener_imports(path):

    with open(path, "r", encoding="utf-8") as f:
        contenido = f.read()

    try:
        tree = ast.parse(contenido)
    except Exception:
        return []

    imports = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                imports.append(node.module)

    return imports


def construir_grafo(mapa):

    grafo = {}

    for mod in mapa:
        grafo[mod] = []

    for mod, path in mapa.items():

        print("Analizando imports:", mod)

        imports = obtener_imports(path)

        for imp in imports:

            imp_path = imp.replace(".", "/") + ".py"

            for posible in mapa:

                if posible.endswith(imp_path) and posible != mod:
                    grafo[mod].append(posible)

    return grafo


def detectar_ciclo(grafo):

    visitado = set()
    pila = []

    def dfs(nodo):

        if nodo in pila:

            ciclo = pila[pila.index(nodo):] + [nodo]

            print("\nCICLO DETECTADO:\n")

            for c in ciclo:
                print(" ->", c)

            return True

        if nodo in visitado:
            return False

        visitado.add(nodo)
        pila.append(nodo)

        for vecino in grafo.get(nodo, []):

            if dfs(vecino):
                return True

        pila.pop()

        return False

    for nodo in grafo:

        if dfs(nodo):
            return

    print("\nNo se detectaron ciclos")


def main():

    archivos = obtener_archivos_py(RUTA_SRC)

    mapa = {}

    print("\nConstruyendo mapa de módulos...\n")

    for archivo in archivos:

        mod = modulo_relativo(archivo)

        print(mod)

        mapa[mod] = archivo

    grafo = construir_grafo(mapa)

    print("\nBuscando ciclos...\n")

    detectar_ciclo(grafo)


if __name__ == "__main__":

    main()