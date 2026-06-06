import ast
import os

ARCHIVO = "metodos_rsa.py"

PALABRAS_GUI = [
    "QMessageBox",
    "QWidget",
    "QDialog",
    "matplotlib",
    "plt",
    "canvas",
    "add_subplot",
    "FigureCanvas"
]


def leer_codigo(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


def obtener_funciones(codigo):
    arbol = ast.parse(codigo)
    funciones = []

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef):
            inicio = nodo.lineno
            fin = nodo.end_lineno
            nombre = nodo.name

            funciones.append({
                "nombre": nombre,
                "inicio": inicio,
                "fin": fin
            })

    return funciones


def clasificar_funciones(codigo, funciones):

    lineas = codigo.splitlines()

    funciones_gui = []
    funciones_core = []

    for f in funciones:

        bloque = "\n".join(lineas[f["inicio"]-1:f["fin"]])

        es_gui = False

        for palabra in PALABRAS_GUI:
            if palabra in bloque:
                es_gui = True
                break

        if es_gui:
            funciones_gui.append(f["nombre"])
        else:
            funciones_core.append(f["nombre"])

    return funciones_gui, funciones_core


def main():

    if not os.path.exists(ARCHIVO):
        print("No se encontró el archivo:", ARCHIVO)
        return

    codigo = leer_codigo(ARCHIVO)

    funciones = obtener_funciones(codigo)

    gui, core = clasificar_funciones(codigo, funciones)

    print("\nFUNCIONES QUE DEBEN IR A GUI\n")
    for f in gui:
        print(" -", f)

    print("\nFUNCIONES QUE PUEDEN QUEDARSE EN LIBRERIAS\n")
    for f in core:
        print(" -", f)


if __name__ == "__main__":
    main()