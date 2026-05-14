from machine import Pin
from time import sleep_us


class HX711:
    def __init__(self, pin_datos, pin_clock, ganancia=128):
        self.pin_datos = Pin(pin_datos, Pin.IN)
        self.pin_clock = Pin(pin_clock, Pin.OUT)

        self.ganancia = ganancia
        self.offset = 0
        self.escala = 1.0

        self.pin_clock.value(0)

        self._configurar_ganancia()

    # -------------------------------------------------

    def _configurar_ganancia(self):
        if self.ganancia == 128:
            self.pulsos_ganancia = 1
        elif self.ganancia == 64:
            self.pulsos_ganancia = 3
        elif self.ganancia == 32:
            self.pulsos_ganancia = 2
        else:
            raise ValueError("Ganancia inválida")

    # -------------------------------------------------

    def disponible(self):
        return self.pin_datos.value() == 0

    # -------------------------------------------------

    def leer_crudo(self):
        while not self.disponible():
            pass

        valor = 0

        for _ in range(24):
            self.pin_clock.value(1)
            sleep_us(1)

            valor = (valor << 1) | self.pin_datos.value()

            self.pin_clock.value(0)
            sleep_us(1)

        # Pulsos extra para ganancia
        for _ in range(self.pulsos_ganancia):
            self.pin_clock.value(1)
            sleep_us(1)
            self.pin_clock.value(0)
            sleep_us(1)

        # Conversión signed 24 bits
        if valor & 0x800000:
            valor -= 0x1000000

        return valor

    # -------------------------------------------------

    def leer(self, muestras=5):
        acumulado = 0

        for _ in range(muestras):
            acumulado += self.leer_crudo()

        promedio = acumulado / muestras

        return (promedio - self.offset) / self.escala

    # -------------------------------------------------

    def tarar(self, muestras=20):
        acumulado = 0

        for _ in range(muestras):
            acumulado += self.leer_crudo()

        self.offset = acumulado / muestras

    # -------------------------------------------------

    def establecer_escala(self, escala):
        self.escala = escala