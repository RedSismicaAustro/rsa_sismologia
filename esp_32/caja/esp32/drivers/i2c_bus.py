from machine import I2C, Pin


class BusI2C:
    """
    Librería base para manejar el bus I2C del ESP32.

    Esta clase no conoce sensores específicos.
    Solo se encarga de:
    - inicializar el bus I2C
    - escanear dispositivos
    - leer datos
    - escribir datos
    - escribir y luego leer datos

    Por defecto usa:
    - SCL = GPIO22
    - SDA = GPIO21
    - Frecuencia = 100 kHz
    """

    def __init__(self, scl=22, sda=21, freq=100_000):
        """
        Inicializa el bus I2C.

        Parámetros:
        - scl  : GPIO usado como reloj I2C
        - sda  : GPIO usado como datos I2C
        - freq : frecuencia del bus en Hz
        """

        self.i2c = I2C(
            0,
            scl=Pin(scl),
            sda=Pin(sda),
            freq=freq
        )

    def scan(self):
        """
        Escanea el bus I2C.

        Retorna:
        - lista de direcciones detectadas en decimal
        """

        return self.i2c.scan()

    def read(self, addr, nbytes):
        """
        Lee bytes desde un dispositivo I2C.

        Parámetros:
        - addr   : dirección I2C del dispositivo
        - nbytes : cantidad de bytes a leer
        """

        return self.i2c.readfrom(addr, nbytes)

    def write(self, addr, data):
        """
        Escribe datos hacia un dispositivo I2C.

        Parámetros:
        - addr : dirección I2C del dispositivo
        - data : bytes a enviar
        """

        self.i2c.writeto(addr, data)

    def write_read(self, addr, wdata, nbytes):
        """
        Escribe datos y luego lee respuesta.

        Muy usado para leer registros:
        1. escribir dirección de registro
        2. leer cantidad de bytes requerida

        Parámetros:
        - addr   : dirección I2C del dispositivo
        - wdata  : datos a escribir antes de leer
        - nbytes : cantidad de bytes a leer
        """

        self.i2c.writeto(addr, wdata)
        return self.i2c.readfrom(addr, nbytes)