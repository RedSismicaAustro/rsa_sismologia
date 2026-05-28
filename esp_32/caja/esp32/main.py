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

reles.deshabilitar_medicion()
reles.desenergizar_puente()
reles.seleccionar_sensor_tipo_1()
reles.seleccionar_modo_deformacion()

# --------------------------------
# Variables de estado
# --------------------------------

tipo_sensor = 1
puente_energizado = False
medicion_habilitada = False

indice_modo = 0

modos_medicion = [
    ("DEF", ControlReles.MODO_DEFORMACION),
    ("ERR1", ControlReles.MODO_INCORRECTO_1),
    ("ERR2", ControlReles.MODO_INCORRECTO_2),
    ("TEMP", ControlReles.MODO_TEMPERATURA),
]

modo_medicion = modos_medicion[indice_modo][0]

print("Reles inicializados")
print("Modo inicial:", modo_medicion)
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
    pin_clock=33,
    ganancia=HX711.GANANCIA_A_128
)

resultado_tara = hx711.tarar(
    muestras=20,
    timeout_ms=1500
)

if resultado_tara:
    print("HX711 inicializado")
    lcd.escribir_linea(1, "HX711 OK")
else:
    print("ERROR: HX711 no respondio")
    print("Estado HX711:", hx711.obtener_estado())
    lcd.escribir_linea(1, "HX711 ERROR")

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
    """
    Primera línea:
    modo, sensor, puente y medición.
    """

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
    """
    Imprime estado completo en el monitor serial.
    """

    print("-----------------------------------")
    print("Evento:", evento)
    print("Modo:", modo_medicion)
    print("Sensor:", tipo_sensor)
    print("Puente:", puente_energizado)
    print("Medicion:", medicion_habilitada)
    print("Estado HX711:", hx711.obtener_estado())
    print("-----------------------------------")


def convertir_cuentas_a_milivoltios(cuentas):
    """
    Convierte cuentas diferenciales del HX711 a milivoltios.

    Datos del sistema:
    - Alimentación del HX711: 3.3 V
    - Alimentación del puente: 3.3 V
    - Ganancia usada: 128
    - Escala signed ideal: +/- 8388607 cuentas

    Resultado:
    - milivoltios diferenciales aproximados en la entrada del HX711.
    """

    AVDD = 3.3
    GANANCIA = 128
    ESCALA_24_BITS = 8388607

    rango_voltios = AVDD / GANANCIA
    voltios = (cuentas / ESCALA_24_BITS) * rango_voltios

    return voltios * 1000


def tomar_medicion_puente(muestras=20, espera_estabilizacion_ms=500):
    """
    Medición real del puente.

    Secuencia:
    1. Verifica que la medición esté habilitada.
    2. Energiza el puente.
    3. Espera estabilización analógica.
    4. Descarta dos lecturas iniciales.
    5. Toma varias muestras crudas.
    6. Corrige por offset.
    7. Convierte a mV diferenciales.
    8. Desenergiza el puente.
    """

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

    print("Descartando lecturas iniciales")

    for _ in range(2):
        descarte = hx711.leer_crudo(
            timeout_ms=1500
        )

        print("Descarte crudo:", descarte)

        sleep_ms(120)

    acumulado = 0
    validas = 0

    for i in range(muestras):

        valor_crudo = hx711.leer_crudo(
            timeout_ms=1500
        )

        if valor_crudo is not None:
            valor_corregido = valor_crudo - hx711.offset
            acumulado += valor_corregido
            validas += 1
        else:
            valor_corregido = None

        lcd.escribir_linea(
            1,
            "Muestra {}/{}".format(
                i + 1,
                muestras
            )
        )

        print(
            "Muestra:",
            i + 1,
            "Crudo:",
            valor_crudo,
            "Corregido:",
            valor_corregido
        )

        sleep_ms(120)

    reles.desenergizar_puente()
    puente_energizado = False
    actualizar_lcd()

    if validas == 0:
        print("ERROR: no hubo lecturas validas")
        print("Estado HX711:", hx711.obtener_estado())
        lcd.escribir_linea(1, "HX711 ERROR")
        return None

    promedio_cuentas = acumulado / validas
    promedio_mv = convertir_cuentas_a_milivoltios(
        promedio_cuentas
    )

    print("Promedio cuentas:", promedio_cuentas)
    print("Promedio mV:", promedio_mv)

    lcd.escribir_linea(
        1,
        "{:.4f} mV".format(
            promedio_mv
        )
    )

    return promedio_mv


# --------------------------------
# Estado inicial LCD
# --------------------------------

actualizar_lcd()
lcd.escribir_linea(1, "Sistema listo")

print("Sistema listo")
print("Esperando eventos touch...")

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
    # Cambia modo:
    # DEF -> ERR1 -> ERR2 -> TEMP -> DEF
    # ----------------------------

    elif evento == TouchSD.EVENTO_DOBLE:

        indice_modo = (
            indice_modo + 1
        ) % len(modos_medicion)

        modo_medicion = modos_medicion[indice_modo][0]
        modo_rele = modos_medicion[indice_modo][1]

        reles.seleccionar_modo(modo_rele)

        actualizar_lcd()

        imprimir_estado(
            "Doble toque - cambio modo"
        )

    # ----------------------------
    # Triple toque
    # Ejecuta medición real
    # ----------------------------

    elif evento == TouchSD.EVENTO_TRIPLE:

        promedio_mv = tomar_medicion_puente(
            muestras=20,
            espera_estabilizacion_ms=500
        )

        if promedio_mv is None:
            print("Medicion no ejecutada o sin datos")
        else:
            print("Medicion final:", promedio_mv, "mV")

    # ----------------------------
    # Toque largo
    # Habilita/deshabilita medición
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