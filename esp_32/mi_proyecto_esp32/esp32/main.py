from time import sleep
from i2c_bus import BusI2C
from aht20 import AHT20
from lis3dhtr import LIS3DHTR
from rgb_led import LedRGB

print("Iniciando sistema ESP32...")

i2c = BusI2C()
sensor_temp = AHT20(i2c)
acelerometro = LIS3DHTR(i2c)
led = LedRGB()

while True:
    sleep(1)

    x, y, z = acelerometro.leer()
    temp, hum = sensor_temp.leer()

    if x is None or temp is None:
        led.set_color_basico(LedRGB.COLOR_ROJO)   # error
    else:
        led.set_color_basico(LedRGB.COLOR_MAGENTA)   # OK

    print(f"Acel: {x:.2f},{y:.2f},{z:.2f}  Temp: {temp:.1f}C  Hum: {hum:.1f}%")
