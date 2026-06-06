import cv2
import numpy as np

print("====================================")
print("PRUEBA DE TRANSFORMACIÓN")
print("====================================")
print("Ruta de numpy:", np.__file__)
print("Ruta de cv2:", cv2.__file__)
print()

# Imagen de prueba en blanco
img = np.ones((800, 600, 3), dtype=np.uint8) * 255

# Dibujar un cuadrilátero simulando una fachada con perspectiva
pts_dibujo = np.array([
    [150, 120],   # superior izquierda
    [450, 140],   # superior derecha
    [500, 650],   # inferior derecha
    [100, 680]    # inferior izquierda
], dtype=np.int32)

cv2.polylines(img, [pts_dibujo], isClosed=True, color=(0, 0, 255), thickness=3)

# Dibujar puntos
for i, p in enumerate(pts_dibujo):
    cv2.circle(img, tuple(p), 8, (255, 0, 0), -1)
    cv2.putText(
        img,
        str(i + 1),
        (p[0] + 10, p[1] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 0),
        2,
        cv2.LINE_AA
    )

# Puntos origen en float32
pts_origen = np.array([
    [150, 120],
    [450, 140],
    [500, 650],
    [100, 680]
], dtype=np.float32)

# Puntos destino: rectángulo frontal
ancho_salida = 400
alto_salida = 700

pts_destino = np.array([
    [0, 0],
    [ancho_salida - 1, 0],
    [ancho_salida - 1, alto_salida - 1],
    [0, alto_salida - 1]
], dtype=np.float32)

print("pts_origen:")
print(pts_origen)
print("Tipo:", type(pts_origen))
print("Shape:", pts_origen.shape)
print("Dtype:", pts_origen.dtype)
print()

print("pts_destino:")
print(pts_destino)
print("Tipo:", type(pts_destino))
print("Shape:", pts_destino.shape)
print("Dtype:", pts_destino.dtype)
print()

try:
    H = cv2.getPerspectiveTransform(pts_origen, pts_destino)
    print("Matriz H:")
    print(H)
    print()

    rectificada = cv2.warpPerspective(img, H, (ancho_salida, alto_salida))

    cv2.imshow("Imagen original de prueba", img)
    cv2.imshow("Imagen rectificada", rectificada)
    print("La transformación funcionó correctamente.")
    print("Presiona cualquier tecla dentro de una ventana para cerrar.")

    cv2.waitKey(0)
    cv2.destroyAllWindows()

except Exception as e:
    print("ERROR en la transformación:")
    print(e)