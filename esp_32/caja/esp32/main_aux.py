from time import sleep
from machine import Pin
from i2c_bus import BusI2C
from lcd_i2c import LCD_I2C
from hx711 import HX711
from ds3231 import DS3231

print("=== PRUEBA LCD + HX711 + RELES + RTC ===")

sleep(2)

# -------------------------------
# Configuración de relés
# -------------------------------

rele_1 = Pin(13, Pin.OUT)
rele_2 = Pin(14, Pin.OUT)
rele_3 = Pin(16, Pin.OUT)
rele_4 = Pin(17, Pin.OUT)
rele_5 = Pin(25, Pin.OUT)

# Cambiar a 0/1 si tu módulo de relés es activo en bajo
RELE_ACTIVO = 1
RELE_INACTIVO = 0

def apagar_reles():
    rele_1.value(RELE_INACTIVO)
    rele_2.value(RELE_INACTIVO)
    rele_3.value(RELE_INACTIVO)
    rele_4.value(RELE_INACTIVO)
    rele_5.value(RELE_INACTIVO)

def activar_rele(numero):
    apagar_reles()

    if numero == 1:
        rele_1.value(RELE_ACTIVO)
    elif numero == 2:
        rele_2.value(RELE_ACTIVO)
    elif numero == 3:
        rele_3.value(RELE_ACTIVO)
    elif numero == 4:
        rele_4.value(RELE_ACTIVO)
    elif numero == 5:
        rele_5.value(RELE_ACTIVO)

apagar_reles()

# -------------------------------
# I2C, LCD y RTC
# -------------------------------

i2c = BusI2C()
dispositivos = i2c.scan()
print("Dispositivos I2C:", dispositivos)

lcd = LCD_I2C(i2c, direccion=0x27, columnas=16, filas=2)
lcd.limpiar()
lcd.escribir_linea(0, "Inicializando")
lcd.escribir_linea(1, "RTC + HX711")

rtc = DS3231(i2c)

# Para ajustar la hora UNA SOLA VEZ, descomenta, sube, ejecuta,
# y luego vuelve a comentar esta línea:
# rtc.escribir_fecha_hora(2026, 5, 13, 15, 30, 0, 3)

print("RTC:", rtc.texto_fecha_hora())

# -------------------------------
# HX711
# -------------------------------

hx711 = HX711(
    pin_datos=4,
    pin_clock=33
)

lcd.escribir_linea(0, "Tarando HX711")
lcd.escribir_linea(1, "Espere...")
hx711.tarar(muestras=20)

lcd.limpiar()
lcd.escribir_linea(0, "Sistema listo")
lcd.escribir_linea(1, "Leyendo...")
print("HX711 tarado correctamente")

contador = 0

while True:
    sleep(1)

    contador += 1

    fecha_hora = rtc.texto_fecha_hora()
    hora = fecha_hora[11:19]

    valor = hx711.leer(muestras=5)

    rele_actual = ((contador - 1) % 5) + 1
    activar_rele(rele_actual)

    print("Hora:", hora, "Cuenta:", contador, "HX711:", valor, "Rele:", rele_actual)

    lcd.escribir_linea(0, hora)

    if valor is None:
        lcd.escribir_linea(1, "R:{} HX ERROR".format(rele_actual))
    else:
        lcd.escribir_linea(1, "R:{} HX:{:.1f}".format(rele_actual, valor))