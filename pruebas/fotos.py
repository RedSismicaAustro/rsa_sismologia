import cv2
import numpy as np
from pathlib import Path


# =========================================================
# CONFIGURACIÓN
# =========================================================
CARPETA_ENTRADA = Path(r"C:/proyectos/carpeta fotos/entrada")
CARPETA_SALIDA = Path(r"C:/proyectos/carpeta fotos/salida")

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# Tamaño de salida rectificada
ANCHO_SALIDA = 1400
ALTO_SALIDA = 1800

# Tamaño máximo de visualización en pantalla
PANTALLA_ANCHO_MAX = 1400
PANTALLA_ALTO_MAX = 900


# =========================================================
# VARIABLES GLOBALES
# =========================================================
puntos = []
imagen_original = None
imagen_mostrar = None
imagen_rectificada_previa = None
factor_escala = 1.0
nombre_actual = ""


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================
def ajustar_para_pantalla(img, ancho_max=PANTALLA_ANCHO_MAX, alto_max=PANTALLA_ALTO_MAX):
    global factor_escala

    h, w = img.shape[:2]
    escala_w = ancho_max / w
    escala_h = alto_max / h
    escala = min(escala_w, escala_h, 1.0)

    factor_escala = escala

    if escala < 1.0:
        nuevo_w = int(w * escala)
        nuevo_h = int(h * escala)
        return cv2.resize(img, (nuevo_w, nuevo_h), interpolation=cv2.INTER_AREA)

    return img.copy()


def ordenar_puntos(pts):
    """
    Orden esperado de salida:
    [superior izquierda, superior derecha, inferior derecha, inferior izquierda]
    """
    pts = np.array(pts, dtype=np.float32).reshape(4, 2)

    suma = pts.sum(axis=1)
    diferencia = np.diff(pts, axis=1)

    superior_izquierda = pts[np.argmin(suma)]
    inferior_derecha = pts[np.argmax(suma)]
    superior_derecha = pts[np.argmin(diferencia)]
    inferior_izquierda = pts[np.argmax(diferencia)]

    return np.array(
        [
            superior_izquierda,
            superior_derecha,
            inferior_derecha,
            inferior_izquierda
        ],
        dtype=np.float32
    )


def rectificar_imagen(img, pts_origen, ancho_salida, alto_salida):
    pts_origen = np.array(pts_origen, dtype=np.float32).reshape(4, 2)
    pts_origen = ordenar_puntos(pts_origen)

    pts_destino = np.array(
        [
            [0, 0],
            [ancho_salida - 1, 0],
            [ancho_salida - 1, alto_salida - 1],
            [0, alto_salida - 1]
        ],
        dtype=np.float32
    )

    H = cv2.getPerspectiveTransform(pts_origen, pts_destino)
    rectificada = cv2.warpPerspective(img, H, (ancho_salida, alto_salida))

    return rectificada, H


def dibujar_interfaz():
    global imagen_original, imagen_mostrar, puntos, nombre_actual

    if imagen_original is None:
        return

    copia = imagen_original.copy()

    for i, p in enumerate(puntos):
        cv2.circle(copia, tuple(map(int, p)), 8, (0, 0, 255), -1)
        cv2.putText(
            copia,
            f"{i+1}",
            (int(p[0]) + 10, int(p[1]) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 0, 0),
            2,
            cv2.LINE_AA
        )

    if len(puntos) > 1:
        for i in range(len(puntos) - 1):
            cv2.line(
                copia,
                tuple(map(int, puntos[i])),
                tuple(map(int, puntos[i + 1])),
                (0, 255, 0),
                2
            )

    if len(puntos) == 4:
        cv2.line(
            copia,
            tuple(map(int, puntos[3])),
            tuple(map(int, puntos[0])),
            (0, 255, 0),
            2
        )

    imagen_mostrar = ajustar_para_pantalla(copia)

    y0 = 30
    dy = 28

    textos = [
        f"Imagen: {nombre_actual}",
        "Marque 4 puntos sobre la fachada:",
        "1=Sup Izq, 2=Sup Der, 3=Inf Der, 4=Inf Izq",
        "Teclas: s=previsualizar  g=guardar  r=reiniciar  u=deshacer  n=saltar  q=salir"
    ]

    for i, texto in enumerate(textos):
        cv2.putText(
            imagen_mostrar,
            texto,
            (20, y0 + i * dy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
            cv2.LINE_AA
        )

    cv2.imshow("Rectificacion", imagen_mostrar)


def evento_mouse(event, x, y, flags, param):
    global puntos, factor_escala

    if event == cv2.EVENT_LBUTTONDOWN:
        if len(puntos) >= 4:
            return

        x_real = int(x / factor_escala)
        y_real = int(y / factor_escala)

        puntos.append((x_real, y_real))
        dibujar_interfaz()


def mostrar_previa_rectificada(rectificada):
    previa = ajustar_para_pantalla(rectificada, ancho_max=1000, alto_max=800)
    cv2.imshow("Vista previa rectificada", previa)


def cerrar_previa_si_existe():
    try:
        cv2.destroyWindow("Vista previa rectificada")
    except:
        pass


# =========================================================
# PROCESAMIENTO DE CADA IMAGEN
# =========================================================
def procesar_imagen(ruta_entrada, ruta_salida):
    global puntos, imagen_original, imagen_rectificada_previa, nombre_actual

    puntos = []
    imagen_rectificada_previa = None
    nombre_actual = ruta_entrada.name

    img = cv2.imread(str(ruta_entrada))
    if img is None:
        print(f"No se pudo abrir: {ruta_entrada}")
        return "error"

    imagen_original = img
    dibujar_interfaz()
    cerrar_previa_si_existe()

    while True:
        tecla = cv2.waitKey(20) & 0xFF

        if tecla == ord("r"):
            puntos = []
            imagen_rectificada_previa = None
            cerrar_previa_si_existe()
            dibujar_interfaz()

        elif tecla == ord("u"):
            if puntos:
                puntos.pop()
                imagen_rectificada_previa = None
                cerrar_previa_si_existe()
                dibujar_interfaz()

        elif tecla == ord("n"):
            print(f"Omitida: {ruta_entrada.name}")
            cerrar_previa_si_existe()
            return "omitida"

        elif tecla == ord("q"):
            cerrar_previa_si_existe()
            return "salir"

        elif tecla == ord("s"):
            if len(puntos) != 4:
                print("Debes marcar exactamente 4 puntos.")
                continue

            try:
                pts_validos = np.array(puntos, dtype=np.float32).reshape(4, 2)
                imagen_rectificada_previa, _ = rectificar_imagen(
                    imagen_original,
                    pts_validos,
                    ANCHO_SALIDA,
                    ALTO_SALIDA
                )
                mostrar_previa_rectificada(imagen_rectificada_previa)
                print("Vista previa generada. Si está bien, presiona 'g' para guardar.")
            except Exception as e:
                print("Error al rectificar la imagen:")
                print(e)
                print("Puntos usados:", puntos)
                imagen_rectificada_previa = None

        elif tecla == ord("g"):
            if imagen_rectificada_previa is None:
                print("Primero debes generar la vista previa con la tecla 's'.")
                continue

            cv2.imwrite(str(ruta_salida), imagen_rectificada_previa)
            print(f"Guardada: {ruta_salida}")
            cerrar_previa_si_existe()
            return "guardada"


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================
def main():
    carpeta_entrada = Path(CARPETA_ENTRADA)
    carpeta_salida = Path(CARPETA_SALIDA)

    carpeta_salida.mkdir(parents=True, exist_ok=True)

    if not carpeta_entrada.exists():
        print(f"No existe la carpeta de entrada: {carpeta_entrada.resolve()}")
        return

    archivos = sorted(
        [
            p for p in carpeta_entrada.iterdir()
            if p.is_file() and p.suffix.lower() in EXTENSIONES_VALIDAS
        ]
    )

    if not archivos:
        print(f"No hay imágenes válidas en: {carpeta_entrada.resolve()}")
        return

    cv2.namedWindow("Rectificacion", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("Rectificacion", evento_mouse)

    print("========================================")
    print("INSTRUCCIONES")
    print("========================================")
    print("1. Marca 4 puntos sobre la fachada en este orden:")
    print("   1 = superior izquierda")
    print("   2 = superior derecha")
    print("   3 = inferior derecha")
    print("   4 = inferior izquierda")
    print("")
    print("2. Presiona 's' para generar vista previa.")
    print("3. Presiona 'g' para guardar.")
    print("4. Presiona 'r' para reiniciar puntos.")
    print("5. Presiona 'u' para deshacer el último punto.")
    print("6. Presiona 'n' para saltar la imagen.")
    print("7. Presiona 'q' para salir.")
    print("========================================")

    for archivo in archivos:
        salida = carpeta_salida / f"{archivo.stem}_rectificada{archivo.suffix}"
        estado = procesar_imagen(archivo, salida)

        if estado == "salir":
            break

    cerrar_previa_si_existe()
    cv2.destroyAllWindows()
    print("Proceso terminado.")


if __name__ == "__main__":
    main()