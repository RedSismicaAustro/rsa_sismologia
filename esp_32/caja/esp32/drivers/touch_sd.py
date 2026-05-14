from machine import TouchPad, Pin
from time import ticks_ms, ticks_diff, sleep_ms


class TouchSD:
    EVENTO_NINGUNO = None
    EVENTO_SIMPLE = "simple"
    EVENTO_DOBLE = "doble"
    EVENTO_TRIPLE = "triple"
    EVENTO_LARGO = "largo"

    def __init__(
        self,
        pin_touch=15,
        umbral=None,
        tiempo_largo_ms=1000,
        ventana_multitoque_ms=450,
        tiempo_antirrebote_ms=80,
        muestras_calibracion=30
    ):
        self.touch = TouchPad(Pin(pin_touch))

        self.tiempo_largo_ms = tiempo_largo_ms
        self.ventana_multitoque_ms = ventana_multitoque_ms
        self.tiempo_antirrebote_ms = tiempo_antirrebote_ms

        self.valor_base = self._calibrar(muestras_calibracion)

        if umbral is None:
            # En ESP32, al tocar normalmente BAJA el valor.
            self.umbral = int(self.valor_base * 0.70)
        else:
            self.umbral = umbral

        self.estado_tocado = False
        self.tiempo_inicio_toque = 0
        self.tiempo_ultimo_cambio = 0

        self.contador_toques = 0
        self.tiempo_ultimo_toque = 0
        self.largo_reportado = False

    def _calibrar(self, muestras):
        acumulado = 0

        for _ in range(muestras):
            acumulado += self.touch.read()
            sleep_ms(20)

        return acumulado // muestras

    def leer_valor(self):
        return self.touch.read()

    def esta_tocado(self):
        return self.leer_valor() < self.umbral

    def actualizar(self):
        ahora = ticks_ms()
        tocado = self.esta_tocado()

        # Antirrebote básico
        if ticks_diff(ahora, self.tiempo_ultimo_cambio) < self.tiempo_antirrebote_ms:
            return self.EVENTO_NINGUNO

        # Inicio del toque
        if tocado and not self.estado_tocado:
            self.estado_tocado = True
            self.tiempo_inicio_toque = ahora
            self.tiempo_ultimo_cambio = ahora
            self.largo_reportado = False
            return self.EVENTO_NINGUNO

        # Toque largo
        if tocado and self.estado_tocado:
            duracion = ticks_diff(ahora, self.tiempo_inicio_toque)

            if duracion >= self.tiempo_largo_ms and not self.largo_reportado:
                self.largo_reportado = True
                self.contador_toques = 0
                return self.EVENTO_LARGO

            return self.EVENTO_NINGUNO

        # Fin del toque
        if not tocado and self.estado_tocado:
            self.estado_tocado = False
            self.tiempo_ultimo_cambio = ahora

            if not self.largo_reportado:
                self.contador_toques += 1
                self.tiempo_ultimo_toque = ahora

            return self.EVENTO_NINGUNO

        # Evaluar simple/doble/triple cuando terminó la ventana
        if self.contador_toques > 0:
            if ticks_diff(ahora, self.tiempo_ultimo_toque) > self.ventana_multitoque_ms:
                cantidad = self.contador_toques
                self.contador_toques = 0

                if cantidad == 1:
                    return self.EVENTO_SIMPLE
                elif cantidad == 2:
                    return self.EVENTO_DOBLE
                elif cantidad >= 3:
                    return self.EVENTO_TRIPLE

        return self.EVENTO_NINGUNO

    def imprimir_diagnostico(self):
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