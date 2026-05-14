from time import sleep_ms


class LCD_I2C:
    # Comandos HD44780
    LCD_LIMPIAR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x06
    LCD_DISPLAY_ON = 0x0C
    LCD_FUNCTION_SET = 0x28  # 4 bits, 2 líneas, 5x8
    LCD_SET_DDRAM_ADDR = 0x80

    # Bits PCF8574
    BIT_RS = 0x01
    BIT_RW = 0x02
    BIT_EN = 0x04
    BIT_BACKLIGHT = 0x08

    def __init__(self, bus_i2c, direccion=0x27, columnas=16, filas=2):
        self.bus = bus_i2c
        self.direccion = direccion
        self.columnas = columnas
        self.filas = filas
        self.backlight = self.BIT_BACKLIGHT

        self._inicializar()

    def _escribir_byte(self, dato):
        self.bus.write(self.direccion, bytes([dato | self.backlight]))

    def _pulso_enable(self, dato):
        self._escribir_byte(dato | self.BIT_EN)
        sleep_ms(1)
        self._escribir_byte(dato & ~self.BIT_EN)
        sleep_ms(1)

    def _enviar_nibble(self, nibble, modo):
        dato = (nibble & 0xF0) | modo
        self._pulso_enable(dato)

    def _enviar_byte(self, valor, modo=0):
        self._enviar_nibble(valor & 0xF0, modo)
        self._enviar_nibble((valor << 4) & 0xF0, modo)

    def _comando(self, comando):
        self._enviar_byte(comando, 0)
        sleep_ms(2)

    def _dato(self, dato):
        self._enviar_byte(dato, self.BIT_RS)

    def _inicializar(self):
        sleep_ms(50)

        # Secuencia estándar de inicialización en modo 4 bits
        self._enviar_nibble(0x30, 0)
        sleep_ms(5)
        self._enviar_nibble(0x30, 0)
        sleep_ms(5)
        self._enviar_nibble(0x30, 0)
        sleep_ms(1)
        self._enviar_nibble(0x20, 0)

        self._comando(self.LCD_FUNCTION_SET)
        self._comando(self.LCD_DISPLAY_ON)
        self._comando(self.LCD_LIMPIAR)
        self._comando(self.LCD_ENTRY_MODE)

    def limpiar(self):
        self._comando(self.LCD_LIMPIAR)
        sleep_ms(2)

    def mover_cursor(self, fila, columna):
        offsets = [0x00, 0x40, 0x14, 0x54]
        if fila >= self.filas:
            fila = self.filas - 1
        direccion = self.LCD_SET_DDRAM_ADDR | (offsets[fila] + columna)
        self._comando(direccion)

    def escribir(self, texto):
        for caracter in texto:
            self._dato(ord(caracter))

    def escribir_linea(self, fila, texto):
        texto = str(texto)

        if len(texto) > self.columnas:
            texto = texto[:self.columnas]
        else:
            texto = texto + " " * (self.columnas - len(texto))

        self.mover_cursor(fila, 0)
        self.escribir(texto)

    def apagar_luz(self):
        self.backlight = 0x00
        self._escribir_byte(0)

    def encender_luz(self):
        self.backlight = self.BIT_BACKLIGHT
        self._escribir_byte(0)