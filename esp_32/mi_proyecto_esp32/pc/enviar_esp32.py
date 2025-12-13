import os
import subprocess

PUERTO = "COM7"

RUTA_PROYECTO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

ARCHIVOS = [
    # lógica común
    os.path.join(RUTA_PROYECTO, "comun", "logica.py"),

    # programa principal
    os.path.join(RUTA_PROYECTO, "esp32", "main.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "boot.py"),

    # TODOS los drivers en el mismo directorio
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "i2c_bus.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "aht20.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "lis3dhtr.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "rgb_led.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "sensor_adc.py"),
]
print("Subida de archivos al SP32")
def subir_archivos():
    for archivo in ARCHIVOS:
        print("DEBUG ruta:", archivo)

        if not os.path.exists(archivo):
            print(f"ERROR: no existe {archivo}")
            continue

        print(f"Subiendo {archivo} → ESP32...")
        subprocess.run(
            ["mpremote", "connect", PUERTO, "cp", archivo, ":"],
            check=False
        )

if __name__ == "__main__":
    subir_archivos()
