import cv2
import numpy as np
import ezdxf
from reportlab.pdfgen import canvas
from pathlib import Path

# =========================================================
# CONFIGURACIÓN
# =========================================================
CARPETA_ENTRADA = Path(r"C:\proyectos\carpeta fotos\entrada")
CARPETA_SALIDA = Path(r"C:\proyectos\carpeta fotos\salida")

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

PANTALLA_ANCHO_MAX = 1400
PANTALLA_ALTO_MAX = 900

ANCHO_SALIDA = 1400
ALTO_SALIDA = 2200

# Parámetros de detección de líneas
UMBRAL_CANNY_1 = 30
UMBRAL_CANNY_2 = 100
HOUGH_THRESHOLD = 35
MIN_LINE_LENGTH = 35
MAX_LINE_GAP = 20

TOLERANCIA_VERTICAL_GRADOS = 18
TOLERANCIA_HORIZONTAL_GRADOS = 18

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
# UTILIDADES
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
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)

    suma = pts.sum(axis=1)
    diferencia = np.diff(pts, axis=1).reshape(4)

    superior_izquierda = pts[np.argmin(suma)]
    inferior_derecha = pts[np.argmax(suma)]
    superior_derecha = pts[np.argmin(diferencia)]
    inferior_izquierda = pts[np.argmax(diferencia)]

    return np.ascontiguousarray(np.array([
        superior_izquierda,
        superior_derecha,
        inferior_derecha,
        inferior_izquierda
    ], dtype=np.float32))


def rectificar_imagen(img, pts_origen, ancho_salida, alto_salida):
    pts_origen = np.asarray(pts_origen, dtype=np.float32).reshape(4, 2)
    pts_origen = ordenar_puntos(pts_origen)

    pts_destino = np.array([
        [0, 0],
        [ancho_salida - 1, 0],
        [ancho_salida - 1, alto_salida - 1],
        [0, alto_salida - 1]
    ], dtype=np.float32)

    pts_destino = np.ascontiguousarray(pts_destino, dtype=np.float32)

    H = cv2.getPerspectiveTransform(pts_origen, pts_destino)
    rectificada = cv2.warpPerspective(img, H, (ancho_salida, alto_salida))

    return rectificada, H


def angulo_linea(x1, y1, x2, y2):
    ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
    if ang < 0:
        ang += 180
    return ang


def es_vertical(ang):
    return abs(ang - 90) <= TOLERANCIA_VERTICAL_GRADOS


def es_horizontal(ang):
    return ang <= TOLERANCIA_HORIZONTAL_GRADOS or abs(ang - 180) <= TOLERANCIA_HORIZONTAL_GRADOS


def detectar_lineas_principales(img_bgr):
    gris = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, (5, 5), 0)

    bordes = cv2.Canny(gris, UMBRAL_CANNY_1, UMBRAL_CANNY_2, apertureSize=3)

    lineas = cv2.HoughLinesP(
        bordes,
        rho=1,
        theta=np.pi / 180,
        threshold=HOUGH_THRESHOLD,
        minLineLength=MIN_LINE_LENGTH,
        maxLineGap=MAX_LINE_GAP
    )

    verticales = []
    horizontales = []
    otras = []

    if lineas is not None:
        for linea in lineas:
            x1, y1, x2, y2 = linea[0]
            ang = angulo_linea(x1, y1, x2, y2)

            if es_vertical(ang):
                verticales.append((x1, y1, x2, y2))
            elif es_horizontal(ang):
                horizontales.append((x1, y1, x2, y2))
            else:
                otras.append((x1, y1, x2, y2))

    return bordes, verticales, horizontales, otras


def dibujar_lineas(img, verticales, horizontales, otras=None):
    salida = np.ones_like(img) * 255

    for x1, y1, x2, y2 in verticales:
        cv2.line(salida, (x1, y1), (x2, y2), (0, 0, 0), 1)

    for x1, y1, x2, y2 in horizontales:
        cv2.line(salida, (x1, y1), (x2, y2), (0, 0, 0), 1)

    if otras:
        for x1, y1, x2, y2 in otras:
            cv2.line(salida, (x1, y1), (x2, y2), (0, 0, 0), 1)

    return salida


# =========================================================
# EXPORTACIÓN VECTORIAL
# =========================================================
def guardar_dxf(ruta_dxf, ancho, alto, verticales, horizontales, incluir_otras=True, otras=None):
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()

    def ycad(y):
        return alto - y

    for x1, y1, x2, y2 in verticales:
        msp.add_line((x1, ycad(y1)), (x2, ycad(y2)))

    for x1, y1, x2, y2 in horizontales:
        msp.add_line((x1, ycad(y1)), (x2, ycad(y2)))

    if incluir_otras and otras:
        for x1, y1, x2, y2 in otras:
            msp.add_line((x1, ycad(y1)), (x2, ycad(y2)))

    doc.saveas(str(ruta_dxf))


def guardar_pdf(ruta_pdf, ancho, alto, verticales, horizontales, incluir_otras=True, otras=None):
    c = canvas.Canvas(str(ruta_pdf), pagesize=(ancho, alto))

    def ypdf(y):
        return alto - y

    c.setLineWidth(1)

    for x1, y1, x2, y2 in verticales:
        c.line(x1, ypdf(y1), x2, ypdf(y2))

    for x1, y1, x2, y2 in horizontales:
        c.line(x1, ypdf(y1), x2, ypdf(y2))

    if incluir_otras and otras:
        for x1, y1, x2, y2 in otras:
            c.line(x1, ypdf(y1), x2, ypdf(y2))

    c.showPage()
    c.save()


# =========================================================
# INTERFAZ
# =========================================================
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

    textos = [
        f"Imagen: {nombre_actual}",
        "Marque 4 puntos de la fachada principal",
        "1=Sup Izq, 2=Sup Der, 3=Inf Der, 4=Inf Izq",
        "s=previsualizar  g=guardar foto+dxf+pdf  r=reiniciar  u=deshacer  n=saltar  q=salir"
    ]

    for i, texto in enumerate(textos):
        cv2.putText(
            imagen_mostrar,
            texto,
            (20, 30 + i * 28),
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


def mostrar_previa_lineas(img_lineas):
    previa = ajustar_para_pantalla(img_lineas, ancho_max=1000, alto_max=800)
    cv2.imshow("Vista previa lineas", previa)


def cerrar_previas():
    for nombre in ["Vista previa rectificada", "Vista previa lineas"]:
        try:
            cv2.destroyWindow(nombre)
        except:
            pass


# =========================================================
# PROCESAMIENTO
# =========================================================
def procesar_y_guardar(ruta_salida_img, ruta_salida_dxf, ruta_salida_pdf):
    global imagen_rectificada_previa

    if imagen_rectificada_previa is None:
        print("Primero debes generar la vista previa con la tecla 's'.")
        return False

    rectificada = imagen_rectificada_previa.copy()
    _, verticales, horizontales, otras = detectar_lineas_principales(rectificada)

    cv2.imwrite(str(ruta_salida_img), rectificada)

    guardar_dxf(
        ruta_salida_dxf,
        rectificada.shape[1],
        rectificada.shape[0],
        verticales,
        horizontales,
        incluir_otras=True,
        otras=otras
    )

    guardar_pdf(
        ruta_salida_pdf,
        rectificada.shape[1],
        rectificada.shape[0],
        verticales,
        horizontales,
        incluir_otras=True,
        otras=otras
    )

    img_lineas = dibujar_lineas(rectificada, verticales, horizontales, otras=otras)
    mostrar_previa_lineas(img_lineas)

    print(f"Foto guardada: {ruta_salida_img}")
    print(f"DXF guardado:  {ruta_salida_dxf}")
    print(f"PDF guardado:  {ruta_salida_pdf}")
    print(f"Verticales: {len(verticales)} | Horizontales: {len(horizontales)} | Otras: {len(otras)}")

    return True


def procesar_imagen(ruta_entrada, ruta_salida_img, ruta_salida_dxf, ruta_salida_pdf):
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
    cerrar_previas()

    while True:
        tecla = cv2.waitKey(20) & 0xFF

        if tecla == ord("r"):
            puntos = []
            imagen_rectificada_previa = None
            cerrar_previas()
            dibujar_interfaz()

        elif tecla == ord("u"):
            if puntos:
                puntos.pop()
                imagen_rectificada_previa = None
                cerrar_previas()
                dibujar_interfaz()

        elif tecla == ord("n"):
            print(f"Omitida: {ruta_entrada.name}")
            cerrar_previas()
            return "omitida"

        elif tecla == ord("q"):
            cerrar_previas()
            return "salir"

        elif tecla == ord("s"):
            if len(puntos) != 4:
                print("Debes marcar exactamente 4 puntos.")
                continue

            try:
                pts_validos = np.asarray(puntos, dtype=np.float32).reshape(4, 2)

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
            guardado_ok = procesar_y_guardar(ruta_salida_img, ruta_salida_dxf, ruta_salida_pdf)
            if guardado_ok:
                return "guardada"


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================
def main():
    carpeta_entrada = CARPETA_ENTRADA
    carpeta_salida = CARPETA_SALIDA

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
    print("1. Marca 4 puntos sobre la fachada principal")
    print("2. Presiona 's' para generar vista previa")
    print("3. Presiona 'g' para guardar foto rectificada + DXF + PDF")
    print("4. Presiona 'r' para reiniciar puntos")
    print("5. Presiona 'u' para deshacer el último punto")
    print("6. Presiona 'n' para saltar la imagen")
    print("7. Presiona 'q' para salir")
    print("========================================")

    for archivo in archivos:
        salida_img = carpeta_salida / f"{archivo.stem}_rectificada{archivo.suffix}"
        salida_dxf = carpeta_salida / f"{archivo.stem}_rectificada.dxf"
        salida_pdf = carpeta_salida / f"{archivo.stem}_rectificada.pdf"

        estado = procesar_imagen(archivo, salida_img, salida_dxf, salida_pdf)

        if estado == "salir":
            break

    cerrar_previas()
    cv2.destroyAllWindows()
    print("Proceso terminado.")


if __name__ == "__main__":
    main()