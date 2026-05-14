from machine import Pin
import neopixel

class LedRGB:
    # Colores básicos (RGB)
    COLOR_APAGADO   = (0, 0, 0)
    COLOR_ROJO      = (255, 0, 0)
    COLOR_VERDE     = (0, 255, 0)
    COLOR_AZUL      = (0, 0, 255)
    COLOR_AMARILLO  = (255, 200, 0)
    COLOR_NARANJA   = (255, 120, 0)
    COLOR_CIAN      = (0, 255, 255)
    COLOR_MAGENTA   = (255, 0, 255)
    COLOR_BLANCO    = (255, 255, 255)
    COLOR_BLANCO_SUAVE = (20, 20, 20)

    def __init__(self, pin=2, brillo=0.2):
        self.np = neopixel.NeoPixel(Pin(pin), 1)
        self.brillo = brillo
        self.color_actual = self.COLOR_APAGADO
        self.apagar()

    def _escala(self, color):
        return tuple(int(c * self.brillo) for c in color)

    def set_color(self, r, g, b):
        self.color_actual = (r, g, b)
        self.np[0] = self._escala(self.color_actual)
        self.np.write()

    def set_color_basico(self, color):
        """
        color: una de las constantes COLOR_*
        """
        self.set_color(*color)

    def apagar(self):
        self.set_color(*self.COLOR_APAGADO)
