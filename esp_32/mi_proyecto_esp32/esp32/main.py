from time import sleep
from i2c_bus import BusI2C
from aht20 import AHT20
from lis3dhtr import LIS3DHTR
from rgb_led import LedRGB
from lcd_i2c import LCD_I2C

print("Iniciando sistema ESP32...")

i2c = BusI2C()
sensor_temp = AHT20(i2c)
acelerometro = LIS3DHTR(i2c)
led = LedRGB()
lcd = LCD_I2C(i2c, direccion=0x27, columnas=16, filas=2)
lcd.limpiar()
lcd.escribir_linea(0, "Sistema ESP32")
lcd.escribir_linea(1, "Iniciando...")

while True:
    sleep(1)

    x, y, z = acelerometro.leer()
    temp, hum = sensor_temp.leer()

    if x is None or temp is None:
        led.set_color_basico(LedRGB.COLOR_ROJO)   # error
    else:
        led.set_color_basico(LedRGB.COLOR_MAGENTA)   # OK

    lcd.escribir_linea(0, "T:{:.1f} H:{:.1f}".format(temp, hum))
    lcd.escribir_linea(1, "Z:{:.2f}".format(z))

    print(f"Acel: {x:.2f},{y:.2f},{z:.2f}  Temp: {temp:.1f}C  Hum: {hum:.1f}%")