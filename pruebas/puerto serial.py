import serial
import time
import csv

PORT = "COM4"        # Ajusta según corresponda
BAUD = 9600
TIMEOUT = 1

def leer_datos():
    ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
    print("Leyendo... Presiona Ctrl+C para terminar.")
    datos = []

    try:
        while True:
            linea = ser.readline().decode(errors="ignore").strip()
            if linea:
                print(linea)
                datos.append(linea)
    except KeyboardInterrupt:
        pass

    ser.close()
    return datos


def guardar_txt(datos, nombre="ruide.txt"):
    with open(nombre, "w") as f:
        for l in datos:
            f.write(l + "\n")
    print("Guardado en", nombre)


def guardar_csv(datos, nombre="ruide.csv"):
    with open(nombre, "w", newline="") as f:
        w = csv.writer(f)
        for l in datos:
            w.writerow([l])
    print("Guardado en", nombre)


def guardar_xyz(datos, nombre="ruide.xyz"):
    with open(nombre, "w") as f:
        for l in datos:
            f.write(l + "\n")
    print("Guardado en", nombre)


# ===========================
# PROGRAMA PRINCIPAL
# ===========================

datos = leer_datos()

print("\nElige formato de salida:")
print("1 = TXT")
print("2 = CSV")
print("3 = XYZ")

op = input("Opción: ")

if op == "1":
    guardar_txt(datos)
elif op == "2":
    guardar_csv(datos)
elif op == "3":
    guardar_xyz(datos)
else:
    print("Opción no válida.")
