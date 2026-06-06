import time


class AHT20:
    """
    Librería básica para manejo del sensor AHT20.

    El AHT20 es un sensor digital I2C para:
    - temperatura
    - humedad relativa

    Comunicación:
    - Bus I2C
    - Dirección fija: 0x38

    El sensor entrega:
    - humedad relativa en %
    - temperatura en °C
    """

    # Dirección I2C del sensor
    DIRECCION = 0x38

    # -------------------------------------------------

    def __init__(self, bus_i2c):
        """
        Inicializa el sensor AHT20.

        Parámetros:
        - bus_i2c : instancia del bus I2C compartido

        Variables internas:
        - disponible  : indica si el sensor fue detectado
        - temperatura : última temperatura medida
        - humedad     : última humedad medida
        """

        # Referencia al bus I2C
        self.bus = bus_i2c

        # Estado inicial
        self.disponible = False

        # Variables de última lectura
        self.temperatura = None
        self.humedad = None

        # Inicializar sensor
        self._inicializar()

    # -------------------------------------------------

    def _inicializar(self):
        """
        Inicializa el AHT20.

        Proceso:
        1. Escanear bus I2C.
        2. Verificar presencia del sensor.
        3. Enviar comando de inicialización.
        4. Marcar sensor como disponible.
        """

        # Obtener dispositivos I2C detectados
        dispositivos = self.bus.scan()

        # Verificar presencia del sensor
        if self.DIRECCION not in dispositivos:

            self.disponible = False
            return

        # -----------------------------------------
        # Comando de inicialización recomendado
        #
        # 0xBE -> initialize
        # 0x08
        # 0x00
        # -----------------------------------------

        self.bus.write(
            self.DIRECCION,
            b'\xBE\x08\x00'
        )

        # Esperar estabilización
        time.sleep_ms(10)

        # Sensor disponible
        self.disponible = True

    # -------------------------------------------------

    def leer(self):
        """
        Realiza una medición de:
        - temperatura
        - humedad relativa

        Proceso:
        1. Verificar disponibilidad.
        2. Enviar comando de medición.
        3. Esperar conversión interna.
        4. Leer 6 bytes.
        5. Extraer datos crudos.
        6. Convertir a unidades físicas.

        Retorna:
        - temperatura (°C)
        - humedad (%RH)

        Si falla:
        - retorna (None, None)
        """

        # Verificar estado sensor
        if not self.disponible:
            return None, None

        # -----------------------------------------
        # Trigger measurement
        #
        # 0xAC -> iniciar medición
        # 0x33
        # 0x00
        # -----------------------------------------

        self.bus.write(
            self.DIRECCION,
            b'\xAC\x33\x00'
        )

        # Esperar conversión interna
        time.sleep_ms(80)

        # Leer 6 bytes del sensor
        datos = self.bus.read(
            self.DIRECCION,
            6
        )

        # -----------------------------------------
        # Extracción de humedad
        #
        # 20 bits:
        # datos[1], datos[2], parte de datos[3]
        # -----------------------------------------

        hum_raw = (
            (
                (datos[1] << 16)
                |
                (datos[2] << 8)
                |
                datos[3]
            )
            >> 4
        )

        # -----------------------------------------
        # Extracción de temperatura
        #
        # 20 bits:
        # parte de datos[3], datos[4], datos[5]
        # -----------------------------------------

        temp_raw = (
            (
                (datos[3] & 0x0F) << 16
            )
            |
            (datos[4] << 8)
            |
            datos[5]
        )

        # -----------------------------------------
        # Conversión a unidades físicas
        #
        # Fórmulas del datasheet
        # -----------------------------------------

        # Humedad relativa (%RH)
        self.humedad = (
            hum_raw * 100 / 1048576
        )

        # Temperatura en °C
        self.temperatura = (
            temp_raw * 200 / 1048576
        ) - 50

        # Retornar valores calculados
        return self.temperatura, self.humedad
