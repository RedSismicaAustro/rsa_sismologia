from machine import Pin
import neopixel


class LedRGB:
    """
    Librería básica para manejo de LED RGB direccionable
    tipo WS2812 / NeoPixel.

    El LED se controla mediante:
    - un único pin digital
    - protocolo serial temporizado

    Esta librería:
    - define colores básicos
    - permite control de brillo
    - mantiene el color actual
    """

    # -------------------------------------------------
    # Definición de colores básicos RGB
    # Formato:
    # (R, G, B)
    # Valores:
    # 0 a 255
    # -------------------------------------------------

    COLOR_APAGADO = (0, 0, 0)

    COLOR_ROJO = (255, 0, 0)
    COLOR_VERDE = (0, 255, 0)
    COLOR_AZUL = (0, 0, 255)

    COLOR_AMARILLO = (255, 200, 0)
    COLOR_NARANJA = (255, 120, 0)

    COLOR_CIAN = (0, 255, 255)
    COLOR_MAGENTA = (255, 0, 255)

    COLOR_BLANCO = (255, 255, 255)

    # Blanco tenue para iluminación suave
    COLOR_BLANCO_SUAVE = (20, 20, 20)

    # -------------------------------------------------

    def __init__(self, pin=2, brillo=0.2):
        """
        Inicializa el LED RGB.

        Parámetros:
        - pin    : GPIO conectado al NeoPixel
        - brillo : factor de brillo global
                   rango recomendado:
                   0.0 a 1.0

        Ejemplo:
        brillo = 0.2 -> 20% intensidad
        """

        # Inicializar objeto NeoPixel
        # 1 LED conectado
        self.np = neopixel.NeoPixel(Pin(pin), 1)

        # Brillo global
        self.brillo = brillo

        # Color actual almacenado
        self.color_actual = self.COLOR_APAGADO

        # Apagar LED al iniciar
        self.apagar()

    # -------------------------------------------------

    def _escala(self, color):
        """
        Aplica factor de brillo al color.

        Parámetros:
        - color : tupla (R, G, B)

        Retorna:
        - color escalado según brillo
        """

        return tuple(
            int(c * self.brillo)
            for c in color
        )

    # -------------------------------------------------

    def set_color(self, r, g, b):
        """
        Configura color RGB manualmente.

        Parámetros:
        - r : rojo   (0-255)
        - g : verde  (0-255)
        - b : azul   (0-255)

        Proceso:
        1. Guarda color actual.
        2. Aplica escala de brillo.
        3. Envía datos al NeoPixel.
        """

        # Guardar color actual
        self.color_actual = (r, g, b)

        # Aplicar brillo
        self.np[0] = self._escala(
            self.color_actual
        )

        # Actualizar LED físicamente
        self.np.write()

    # -------------------------------------------------

    def set_color_basico(self, color):
        """
        Configura uno de los colores
        predefinidos en la librería.

        Parámetro:
        - color : constante COLOR_*

        Ejemplos:
        led.set_color_basico(
            LedRGB.COLOR_ROJO
        )

        led.set_color_basico(
            LedRGB.COLOR_VERDE
        )
        """

        self.set_color(*color)

    # -------------------------------------------------

    def apagar(self):
        """
        Apaga completamente el LED.
        """

        self.set_color(
            *self.COLOR_APAGADO
        )
