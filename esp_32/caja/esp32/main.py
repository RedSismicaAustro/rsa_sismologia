from time import sleep, sleep_ms
from i2c_bus import BusI2C
from lcd_i2c import LCD_I2C
from hx711 import HX711
from touch_sd import TouchSD
from control_reles import ControlReles

print("===================================")
print("Inicializando sistema")
print("===================================")

sleep(2)

# --------------------------------
# Inicialización I2C y LCD
# --------------------------------

i2c = BusI2C()

print("Dispositivos I2C:", i2c.scan())

lcd = LCD_I2C(
    i2c,
    direccion=0x27,
    columnas=16,
    filas=2
)

lcd.limpiar()
lcd.escribir_linea(0, "Inicializando")
lcd.escribir_linea(1, "Sistema...")

# --------------------------------
# Inicialización de relés
# --------------------------------

reles = ControlReles()

# Estado inicial solicitado
reles.deshabilitar_medicion()
reles.desenergizar_puente()
reles.seleccionar_sensor_tipo_1()
reles.seleccionar_modo_deformacion()

tipo_sensor = 1
modo_medicion = "DEF"

puente_energizado = False
medicion_habilitada = False

print("Reles inicializados")
print("Modo inicial: deformacion")
print("Sensor inicial: tipo 1")
print("Puente desenergizado")
print("Medicion deshabilitada")

# --------------------------------
# Inicialización HX711
# --------------------------------

lcd.escribir_linea(0, "Tarando HX711")
lcd.escribir_linea(1, "Espere...")

hx711 = HX711(
    pin_datos=4,
    pin_clock=33
)

hx711.tarar(muestras=20)

print("HX711 inicializado")

# --------------------------------
# Inicialización Touch
# --------------------------------

touch = TouchSD(pin_touch=15)

print("Touch inicializado")
print("Valor base:", touch.valor_base)
print("Umbral:", touch.umbral)

# --------------------------------
# Funciones auxiliares
# --------------------------------

def actualizar_lcd():

    lcd.escribir_linea(
        0,
        "{} S{} P{} M{}".format(
            modo_medicion,
            tipo_sensor,
            "1" if puente_energizado else "0",
            "1" if medicion_habilitada else "0"
        )
    )


def imprimir_estado(evento):

    print("-----------------------------------")
    print("Evento:", evento)
    print("Modo:", modo_medicion)
    print("Sensor:", tipo_sensor)
    print("Puente:", puente_energizado)
    print("Medicion:", medicion_habilitada)
    print("-----------------------------------")


# --------------------------------
# Estado inicial LCD
# --------------------------------

actualizar_lcd()

lcd.escribir_linea(
    1,
    "Sistema listo"
)

print("Sistema listo")
print("Esperando eventos touch...")



def tomar_medicion_puente(muestras=20, espera_estabilizacion_ms=300):
    global puente_energizado

    if not medicion_habilitada:
        print("ERROR: medicion no habilitada")
        lcd.escribir_linea(1, "M no habilitada")
        return None

    print("Iniciando medicion real")
    lcd.escribir_linea(1, "Midiendo...")

    reles.energizar_puente()
    puente_energizado = True
    actualizar_lcd()

    sleep_ms(espera_estabilizacion_ms)

    acumulado = 0
    validas = 0

    for i in range(muestras):
        valor = hx711.leer(muestras=1)

        if valor is not None:
            acumulado += valor
            validas += 1

        lcd.escribir_linea(1, "Muestra {}/{}".format(i + 1, muestras))
        print("Muestra:", i + 1, "Valor:", valor)

        sleep_ms(80)

    reles.desenergizar_puente()
    puente_energizado = False
    actualizar_lcd()

    if validas == 0:
        print("ERROR: no hubo lecturas validas")
        lcd.escribir_linea(1, "HX711 ERROR")
        return None

    promedio = acumulado / validas

    print("Promedio HX711:", promedio)
    lcd.escribir_linea(1, "Prom:{:.1f}".format(promedio))

    return promedio

# --------------------------------
# Bucle principal
# --------------------------------

while True:

    evento = touch.actualizar()

    # ----------------------------
    # Toque simple
    # Cambia sensor
    # ----------------------------

    if evento == TouchSD.EVENTO_SIMPLE:

        if tipo_sensor == 1:

            tipo_sensor = 2
            reles.seleccionar_sensor_tipo_2()

        else:

            tipo_sensor = 1
            reles.seleccionar_sensor_tipo_1()

        actualizar_lcd()

        imprimir_estado(
            "Toque simple - cambio sensor"
        )

    # ----------------------------
    # Doble toque
    # Cambia modo medición
    # ----------------------------

    elif evento == TouchSD.EVENTO_DOBLE:

        if modo_medicion == "DEF":

            modo_medicion = "TEMP"
            reles.seleccionar_modo_temperatura()

        else:

            modo_medicion = "DEF"
            reles.seleccionar_modo_deformacion()

        actualizar_lcd()

        imprimir_estado(
            "Doble toque - cambio modo"
        )

    # ----------------------------
    # Triple toque
    # Energiza puente
    # ----------------------------

    elif evento == TouchSD.EVENTO_TRIPLE:
        if medicion_habilitada:
            promedio = tomar_medicion_puente(muestras=20)
        else:
            print("Medicion no habilitada")
            lcd.escribir_linea(1, "M no habilitada")

    # ----------------------------
    # Toque largo
    # Habilita medición
    # ----------------------------

    elif evento == TouchSD.EVENTO_LARGO:

        medicion_habilitada = not medicion_habilitada

        if medicion_habilitada:

            reles.habilitar_medicion()

        else:

            reles.deshabilitar_medicion()

        actualizar_lcd()

        imprimir_estado(
            "Toque largo - medicion"
        )

    

    sleep_ms(20)