from machine import Pin
from time import sleep_us, sleep_ms, ticks_ms, ticks_diff


class HX711:
    """
    Librería para manejo del ADC HX711.

    El HX711 trabaja con dos líneas:
    - DT  : salida de datos del HX711 hacia el ESP32.
    - SCK : reloj generado por el ESP32.

    Funcionamiento:
    - DT en alto  : conversión en proceso.
    - DT en bajo  : dato disponible.
    - El ESP32 genera 24 pulsos SCK para leer el dato.
    - Pulsos extra seleccionan canal y ganancia para la siguiente conversión.

    Ganancias:
    - 128 -> Canal A
    - 64  -> Canal A
    - 32  -> Canal B
    """

    GANANCIA_A_128 = 128
    GANANCIA_A_64 = 64
    GANANCIA_B_32 = 32

    def __init__(self, pin_datos, pin_clock, ganancia=GANANCIA_A_128):
        self.pin_datos = Pin(pin_datos, Pin.IN)
        self.pin_clock = Pin(pin_clock, Pin.OUT)

        self.ganancia = ganancia
        self.pulsos_ganancia = 1

        self.offset = 0
        self.escala = 1.0

        self.ultima_lectura_cruda = None
        self.ultima_lectura = None

        # SCK debe quedar en bajo.
        # Si SCK queda alto más de ~60 us, el HX711 entra en power-down.
        self.pin_clock.value(0)
        sleep_ms(500)

        self.configurar_ganancia(ganancia)

    def configurar_ganancia(self, ganancia):
        """
        Configura canal y ganancia para la siguiente conversión.

        Pulsos extra después de los 24 bits:
        - 1 pulso  -> Canal A, ganancia 128
        - 2 pulsos -> Canal B, ganancia 32
        - 3 pulsos -> Canal A, ganancia 64
        """

        if ganancia == self.GANANCIA_A_128:
            self.pulsos_ganancia = 1

        elif ganancia == self.GANANCIA_B_32:
            self.pulsos_ganancia = 2

        elif ganancia == self.GANANCIA_A_64:
            self.pulsos_ganancia = 3

        else:
            raise ValueError("Ganancia invalida. Use 128, 64 o 32.")

        self.ganancia = ganancia

        # Se realiza una lectura de descarte para aplicar la ganancia
        # a la siguiente conversión, si el HX711 responde.
        self.leer_crudo(timeout_ms=1500)

    def disponible(self):
        """
        Retorna True cuando DT está en bajo,
        indicando dato listo.
        """

        return self.pin_datos.value() == 0

    def esperar_disponible(self, timeout_ms=1500):
        """
        Espera a que el HX711 tenga dato listo.

        Se usa timeout para evitar que el programa se cuelgue
        si el HX711 no responde, no está alimentado, o SCK quedó mal.
        """

        inicio = ticks_ms()

        while not self.disponible():

            if ticks_diff(ticks_ms(), inicio) >= timeout_ms:
                return False

            sleep_ms(1)

        return True

    def leer_crudo(self, timeout_ms=1500):
        """
        Lee una muestra cruda signed de 24 bits.

        Retorna:
        - entero signed si la lectura fue correcta.
        - None si no hubo dato disponible dentro del timeout.
        """

        if not self.esperar_disponible(timeout_ms):
            return None

        valor = 0

        for _ in range(24):

            self.pin_clock.value(1)
            sleep_us(1)

            valor = (valor << 1) | self.pin_datos.value()

            self.pin_clock.value(0)
            sleep_us(1)

        # Pulsos extra para definir canal/ganancia siguiente.
        for _ in range(self.pulsos_ganancia):

            self.pin_clock.value(1)
            sleep_us(1)

            self.pin_clock.value(0)
            sleep_us(1)

        # Conversión complemento a dos de 24 bits.
        if valor & 0x800000:
            valor -= 0x1000000

        self.ultima_lectura_cruda = valor

        return valor

    def leer_promedio_crudo(self, muestras=10, timeout_ms=1500, espera_entre_muestras_ms=120):
        """
        Lee varias muestras crudas y retorna su promedio.

        Para módulos HX711 típicos a 10 SPS, una muestra nueva aparece
        aproximadamente cada 100 ms. Por eso se deja una espera
        entre lecturas.
        """

        acumulado = 0
        validas = 0

        for _ in range(muestras):

            valor = self.leer_crudo(timeout_ms=timeout_ms)

            if valor is not None:
                acumulado += valor
                validas += 1

            sleep_ms(espera_entre_muestras_ms)

        if validas == 0:
            return None

        return acumulado / validas

    def leer(self, muestras=5, timeout_ms=1500, espera_entre_muestras_ms=120):
        """
        Lee valor calibrado:
        (promedio_crudo - offset) / escala
        """

        promedio = self.leer_promedio_crudo(
            muestras=muestras,
            timeout_ms=timeout_ms,
            espera_entre_muestras_ms=espera_entre_muestras_ms
        )

        if promedio is None:
            return None

        valor = (promedio - self.offset) / self.escala

        self.ultima_lectura = valor

        return valor

    def tarar(self, muestras=20, timeout_ms=1500):
        """
        Calcula el offset del sistema.

        Debe ejecutarse sin carga o con la condición base definida.

        Retorna:
        - True si la tara fue válida.
        - False si no se pudieron obtener muestras.
        """

        promedio = self.leer_promedio_crudo(
            muestras=muestras,
            timeout_ms=timeout_ms,
            espera_entre_muestras_ms=120
        )

        if promedio is None:
            return False

        self.offset = promedio

        return True

    def establecer_escala(self, escala):
        """
        Define el factor de escala.

        La escala convierte cuentas ADC a unidades físicas:
        gramos, kg, deformación, fuerza, etc.
        """

        if escala == 0:
            raise ValueError("La escala no puede ser cero")

        self.escala = escala

    def calibrar_con_peso(self, peso_conocido, muestras=20, timeout_ms=1500):
        """
        Calcula la escala usando una carga conocida.

        Procedimiento típico:
        1. Tarar sin carga.
        2. Colocar peso conocido.
        3. Ejecutar este método.
        """

        promedio = self.leer_promedio_crudo(
            muestras=muestras,
            timeout_ms=timeout_ms,
            espera_entre_muestras_ms=120
        )

        if promedio is None:
            return False

        diferencia = promedio - self.offset

        if diferencia == 0:
            return False

        self.escala = diferencia / peso_conocido

        return True

    def apagar(self):
        """
        Pone el HX711 en modo bajo consumo.

        SCK en alto por más de 60 us apaga el chip.
        """

        self.pin_clock.value(0)
        sleep_us(1)
        self.pin_clock.value(1)
        sleep_us(70)

    def encender(self):
        """
        Despierta el HX711 dejando SCK en bajo.
        """

        self.pin_clock.value(0)
        sleep_ms(500)

    def obtener_estado(self):
        """
        Retorna estado interno útil para diagnóstico.
        """

        return {
            "ganancia": self.ganancia,
            "offset": self.offset,
            "escala": self.escala,
            "ultima_lectura_cruda": self.ultima_lectura_cruda,
            "ultima_lectura": self.ultima_lectura,
            "disponible": self.disponible(),
            "dt": self.pin_datos.value(),
            "sck": self.pin_clock.value(),
        }