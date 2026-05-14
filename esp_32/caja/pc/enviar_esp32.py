import os
import subprocess

PUERTO = "COM4"

RUTA_PROYECTO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

ARCHIVOS = [
    # Programa principal
    os.path.join(RUTA_PROYECTO, "esp32", "main.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "boot.py"),

    # Drivers usados
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "i2c_bus.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "rgb_led.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "lcd_i2c.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "hx711.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "ds3231.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "touch_sd.py"),
    os.path.join(RUTA_PROYECTO, "esp32", "drivers", "control_reles.py"),
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
