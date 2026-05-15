from machine import TouchPad, Pin
from time import ticks_ms, ticks_diff, sleep_ms


class TouchSD:
    """
    Librería para manejo de entrada táctil capacitiva
    usando TouchPad interno del ESP32.

    Diseñada para:
    - carcasa metálica SD
    - pads capacitivos
    - superficies metálicas

    Eventos soportados:
    - toque simple
    - doble toque
    - triple toque
    - toque largo

    El ESP32 detecta cambios capacitivos:
    - sin tocar  -> valor alto
    - tocando    -> valor más bajo
    """

    # -------------------------------------------------
    # Eventos disponibles
    # -------------------------------------------------

    EVENTO_NINGUNO = None

    EVENTO_SIMPLE = "simple"

    EVENTO_DOBLE = "doble"

    EVENTO_TRIPLE = "triple"

    EVENTO_LARGO = "largo"

    # -------------------------------------------------

    def __init__(
        self,
        pin_touch=15,
        umbral=None,
        tiempo_largo_ms=1000,
        ventana_multitoque_ms=450,
        tiempo_antirrebote_ms=80,
        muestras_calibracion=30
    ):
        """
        Inicializa sistema touch.

        Parámetros:
        - pin_touch               : GPIO touch ESP32
        - umbral                  : nivel de detección
        - tiempo_largo_ms         : tiempo toque largo
        - ventana_multitoque_ms   : ventana agrupación toques
        - tiempo_antirrebote_ms   : filtro rebotes
        - muestras_calibracion    : muestras calibración inicial
        """

        # -----------------------------------------
        # Inicializar TouchPad hardware
        # -----------------------------------------

        self.touch = TouchPad(
            Pin(pin_touch)
        )

        # -----------------------------------------
        # Configuración tiempos
        # -----------------------------------------

        self.tiempo_largo_ms = (
            tiempo_largo_ms
        )

        self.ventana_multitoque_ms = (
            ventana_multitoque_ms
        )

        self.tiempo_antirrebote_ms = (
            tiempo_antirrebote_ms
        )

        # -----------------------------------------
        # Calibración inicial
        # -----------------------------------------

        self.valor_base = self._calibrar(
            muestras_calibracion
        )

        # -----------------------------------------
        # Configuración umbral
        #
        # En ESP32:
        # tocar -> baja el valor
        # -----------------------------------------

        if umbral is None:

            self.umbral = int(
                self.valor_base * 0.70
            )

        else:

            self.umbral = umbral

        # -----------------------------------------
        # Variables internas de estado
        # -----------------------------------------

        # Estado actual touch
        self.estado_tocado = False

        # Tiempo inicio toque
        self.tiempo_inicio_toque = 0

        # Último cambio estado
        self.tiempo_ultimo_cambio = 0

        # Contador multi-toques
        self.contador_toques = 0

        # Tiempo último toque
        self.tiempo_ultimo_toque = 0

        # Evita repetir evento largo
        self.largo_reportado = False

    # -------------------------------------------------

    def _calibrar(self, muestras):
        """
        Realiza calibración inicial.

        Proceso:
        1. leer múltiples muestras
        2. calcular promedio

        Retorna:
        - valor base sin tocar
        """

        acumulado = 0

        for _ in range(muestras):

            acumulado += self.touch.read()

            sleep_ms(20)

        return acumulado // muestras

    # -------------------------------------------------

    def leer_valor(self):
        """
        Lee valor instantáneo touch.

        Retorna:
        - valor crudo capacitivo
        """

        return self.touch.read()

    # -------------------------------------------------

    def esta_tocado(self):
        """
        Determina si existe toque.

        Comparación:
        valor actual < umbral

        Retorna:
        - True  : tocado
        - False : libre
        """

        return (
            self.leer_valor()
            <
            self.umbral
        )

    # -------------------------------------------------

    def actualizar(self):
        """
        Actualiza máquina de estados touch.

        Esta función debe ejecutarse
        continuamente dentro del bucle principal.

        Detecta:
        - toque simple
        - doble toque
        - triple toque
        - toque largo

        Retorna:
        - EVENTO_*
        - EVENTO_NINGUNO
        """

        # Tiempo actual
        ahora = ticks_ms()

        # Estado instantáneo
        tocado = self.esta_tocado()

        # -----------------------------------------
        # Antirrebote
        # -----------------------------------------

        if (
            ticks_diff(
                ahora,
                self.tiempo_ultimo_cambio
            )
            <
            self.tiempo_antirrebote_ms
        ):

            return self.EVENTO_NINGUNO

        # -----------------------------------------
        # Inicio del toque
        # -----------------------------------------

        if tocado and not self.estado_tocado:

            self.estado_tocado = True

            self.tiempo_inicio_toque = ahora

            self.tiempo_ultimo_cambio = ahora

            self.largo_reportado = False

            return self.EVENTO_NINGUNO

        # -----------------------------------------
        # Evaluación toque largo
        # -----------------------------------------

        if tocado and self.estado_tocado:

            duracion = ticks_diff(
                ahora,
                self.tiempo_inicio_toque
            )

            # Detectar largo una sola vez
            if (
                duracion >= self.tiempo_largo_ms
                and
                not self.largo_reportado
            ):

                self.largo_reportado = True

                # Cancelar multi-toques
                self.contador_toques = 0

                return self.EVENTO_LARGO

            return self.EVENTO_NINGUNO

        # -----------------------------------------
        # Fin del toque
        # -----------------------------------------

        if not tocado and self.estado_tocado:

            self.estado_tocado = False

            self.tiempo_ultimo_cambio = ahora

            # No contar si ya fue largo
            if not self.largo_reportado:

                self.contador_toques += 1

                self.tiempo_ultimo_toque = ahora

            return self.EVENTO_NINGUNO

        # -----------------------------------------
        # Evaluación simple/doble/triple
        # -----------------------------------------

        if self.contador_toques > 0:

            if (
                ticks_diff(
                    ahora,
                    self.tiempo_ultimo_toque
                )
                >
                self.ventana_multitoque_ms
            ):

                cantidad = self.contador_toques

                # Reiniciar contador
                self.contador_toques = 0

                # ---------------------------------
                # Clasificación evento
                # ---------------------------------

                if cantidad == 1:

                    return self.EVENTO_SIMPLE

                elif cantidad == 2:

                    return self.EVENTO_DOBLE

                elif cantidad >= 3:

                    return self.EVENTO_TRIPLE

        return self.EVENTO_NINGUNO

    # -------------------------------------------------

    def imprimir_diagnostico(self):
        """
        Imprime información de diagnóstico.

        Útil para:
        - calibración
        - ajuste umbral
        - pruebas hardware
        """

        print(
            "Touch:",
            self.leer_valor(),

            "Base:",
            self.valor_base,

            "Umbral:",
            self.umbral,

            "Tocado:",
            self.esta_tocado()
        )