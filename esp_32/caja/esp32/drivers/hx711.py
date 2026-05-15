from machine import Pin
from time import sleep_us


class HX711:
    """
    Librería básica para manejo del ADC HX711.

    El HX711 es un convertidor analógico-digital de 24 bits
    diseñado para celdas de carga y puentes de Wheatstone.

    Comunicación:
    - DT  : línea de datos
    - SCK : reloj serial

    El HX711 trabaja enviando:
    - 24 bits de datos
    - pulsos adicionales para seleccionar:
        * canal
        * ganancia

    Ganancias soportadas:
    - 128 : Canal A
    - 64  : Canal A
    - 32  : Canal B
    """

    def __init__(self, pin_datos, pin_clock, ganancia=128):
        """
        Inicializa el HX711.

        Parámetros:
        - pin_datos : GPIO conectado al pin DT
        - pin_clock : GPIO conectado al pin SCK
        - ganancia  : ganancia inicial (128, 64 o 32)
        """

        # Configuración de pines
        self.pin_datos = Pin(pin_datos, Pin.IN)
        self.pin_clock = Pin(pin_clock, Pin.OUT)

        # Configuración interna
        self.ganancia = ganancia

        # Offset utilizado para tara
        self.offset = 0

        # Factor de escala para calibración
        self.escala = 1.0

        # Inicializar reloj en bajo
        self.pin_clock.value(0)

        # Configurar cantidad de pulsos
        # según ganancia seleccionada
        self._configurar_ganancia()

    # -------------------------------------------------

    def _configurar_ganancia(self):
        """
        Configura la cantidad de pulsos extra requeridos
        por el HX711 para seleccionar canal y ganancia.

        Tabla HX711:
        - 1 pulso  -> Canal A ganancia 128
        - 3 pulsos -> Canal A ganancia 64
        - 2 pulsos -> Canal B ganancia 32
        """

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
        """
        Verifica si el HX711 tiene datos listos.

        El pin DT:
        - LOW  -> dato disponible
        - HIGH -> conversión en proceso

        Retorna:
        - True  : dato listo
        - False : aún ocupado
        """

        return self.pin_datos.value() == 0

    # -------------------------------------------------

    def leer_crudo(self):
        """
        Lee una muestra cruda de 24 bits desde el HX711.

        Proceso:
        1. Esperar dato disponible.
        2. Generar 24 pulsos de reloj.
        3. Leer bits MSB primero.
        4. Generar pulsos extra de ganancia.
        5. Convertir a entero signed.

        Retorna:
        - Valor entero signed de 24 bits.
        """

        # Esperar hasta que HX711 tenga datos
        while not self.disponible():
            pass

        valor = 0

        # Lectura de 24 bits
        for _ in range(24):

            # Flanco ascendente
            self.pin_clock.value(1)
            sleep_us(1)

            # Desplazar y agregar bit
            valor = (valor << 1) | self.pin_datos.value()

            # Flanco descendente
            self.pin_clock.value(0)
            sleep_us(1)

        # Pulsos extra para seleccionar
        # canal y ganancia siguiente
        for _ in range(self.pulsos_ganancia):

            self.pin_clock.value(1)
            sleep_us(1)

            self.pin_clock.value(0)
            sleep_us(1)

        # Conversión signed 24 bits
        # HX711 entrega complemento a dos
        if valor & 0x800000:
            valor -= 0x1000000

        return valor

    # -------------------------------------------------

    def leer(self, muestras=5):
        """
        Lee múltiples muestras y retorna promedio calibrado.

        Parámetros:
        - muestras : cantidad de muestras a promediar

        Proceso:
        1. Leer múltiples muestras crudas.
        2. Calcular promedio.
        3. Aplicar offset (tara).
        4. Aplicar escala.

        Retorna:
        - Valor calibrado.
        """

        acumulado = 0

        # Acumular muestras
        for _ in range(muestras):
            acumulado += self.leer_crudo()

        # Promedio
        promedio = acumulado / muestras

        # Aplicar calibración
        return (promedio - self.offset) / self.escala

    # -------------------------------------------------

    def tarar(self, muestras=20):
        """
        Realiza tara del sistema.

        La tara calcula el offset promedio
        cuando no existe carga aplicada.

        Parámetros:
        - muestras : cantidad de muestras para promedio
        """

        acumulado = 0

        for _ in range(muestras):
            acumulado += self.leer_crudo()

        # Guardar offset promedio
        self.offset = acumulado / muestras

    # -------------------------------------------------

    def establecer_escala(self, escala):
        """
        Configura factor de escala.

        Este factor permite convertir:
        - cuentas ADC
        en:
        - gramos
        - kg
        - deformación
        - fuerza
        - etc.

        Parámetros:
        - escala : factor multiplicativo
        """

        self.escala = escala