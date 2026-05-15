from time import sleep_ms


class LCD_I2C:
    """
    Librería para manejo de pantallas LCD HD44780
    usando interfaz I2C mediante expansor PCF8574.

    Características:
    - modo 4 bits
    - compatible 16x2, 20x4, etc.
    - control de backlight
    - escritura por líneas
    - movimiento de cursor

    Comunicación:
    ESP32 <-> I2C <-> PCF8574 <-> LCD HD44780
    """

    # -------------------------------------------------
    # Comandos principales del controlador HD44780
    # -------------------------------------------------

    # Limpia completamente pantalla
    LCD_LIMPIAR = 0x01

    # Cursor a posición inicial
    LCD_HOME = 0x02

    # Configuración de entrada
    LCD_ENTRY_MODE = 0x06

    # Display encendido
    LCD_DISPLAY_ON = 0x0C

    # Configuración:
    # - modo 4 bits
    # - 2 líneas
    # - matriz 5x8
    LCD_FUNCTION_SET = 0x28

    # Base para direccionamiento DDRAM
    LCD_SET_DDRAM_ADDR = 0x80

    # -------------------------------------------------
    # Bits del expansor PCF8574
    # -------------------------------------------------

    # Register Select
    BIT_RS = 0x01

    # Read/Write
    BIT_RW = 0x02

    # Enable
    BIT_EN = 0x04

    # Backlight
    BIT_BACKLIGHT = 0x08

    # -------------------------------------------------

    def __init__(
        self,
        bus_i2c,
        direccion=0x27,
        columnas=16,
        filas=2
    ):
        """
        Inicializa pantalla LCD.

        Parámetros:
        - bus_i2c  : instancia del bus I2C
        - direccion: dirección I2C PCF8574
        - columnas : número de columnas LCD
        - filas    : número de filas LCD
        """

        # Referencia bus I2C
        self.bus = bus_i2c

        # Dirección I2C del PCF8574
        self.direccion = direccion

        # Configuración física LCD
        self.columnas = columnas
        self.filas = filas

        # Backlight activado por defecto
        self.backlight = self.BIT_BACKLIGHT

        # Inicializar LCD
        self._inicializar()

    # -------------------------------------------------

    def _escribir_byte(self, dato):
        """
        Envía un byte al PCF8574.

        Parámetros:
        - dato : byte a enviar

        Siempre se mantiene el estado
        actual del backlight.
        """

        self.bus.write(
            self.direccion,
            bytes([dato | self.backlight])
        )

    # -------------------------------------------------

    def _pulso_enable(self, dato):
        """
        Genera pulso ENABLE requerido
        por el controlador HD44780.

        El LCD captura datos en el flanco
        del pin EN.
        """

        # EN = 1
        self._escribir_byte(
            dato | self.BIT_EN
        )

        sleep_ms(1)

        # EN = 0
        self._escribir_byte(
            dato & ~self.BIT_EN
        )

        sleep_ms(1)

    # -------------------------------------------------

    def _enviar_nibble(self, nibble, modo):
        """
        Envía 4 bits al LCD.

        Parámetros:
        - nibble : nibble alto
        - modo:
            0 -> comando
            BIT_RS -> dato
        """

        dato = (
            (nibble & 0xF0)
            | modo
        )

        self._pulso_enable(dato)

    # -------------------------------------------------

    def _enviar_byte(self, valor, modo=0):
        """
        Envía un byte completo en modo 4 bits.

        Proceso:
        1. enviar nibble alto
        2. enviar nibble bajo

        Parámetros:
        - valor : byte completo
        - modo:
            0 -> comando
            BIT_RS -> dato
        """

        # Nibble alto
        self._enviar_nibble(
            valor & 0xF0,
            modo
        )

        # Nibble bajo
        self._enviar_nibble(
            (valor << 4) & 0xF0,
            modo
        )

    # -------------------------------------------------

    def _comando(self, comando):
        """
        Envía comando al LCD.

        Parámetro:
        - comando : instrucción HD44780
        """

        self._enviar_byte(
            comando,
            0
        )

        sleep_ms(2)

    # -------------------------------------------------

    def _dato(self, dato):
        """
        Envía carácter ASCII al LCD.

        Parámetro:
        - dato : byte ASCII
        """

        self._enviar_byte(
            dato,
            self.BIT_RS
        )

    # -------------------------------------------------

    def _inicializar(self):
        """
        Secuencia estándar de inicialización
        HD44780 en modo 4 bits.

        Proceso:
        1. estabilización alimentación
        2. secuencia especial 4 bits
        3. configuración funcional
        4. limpieza pantalla
        """

        # Espera inicial de estabilización
        sleep_ms(50)

        # -----------------------------------------
        # Secuencia especial modo 4 bits
        # -----------------------------------------

        self._enviar_nibble(0x30, 0)
        sleep_ms(5)

        self._enviar_nibble(0x30, 0)
        sleep_ms(5)

        self._enviar_nibble(0x30, 0)
        sleep_ms(1)

        self._enviar_nibble(0x20, 0)

        # -----------------------------------------
        # Configuración LCD
        # -----------------------------------------

        self._comando(
            self.LCD_FUNCTION_SET
        )

        self._comando(
            self.LCD_DISPLAY_ON
        )

        self._comando(
            self.LCD_LIMPIAR
        )

        self._comando(
            self.LCD_ENTRY_MODE
        )

    # -------------------------------------------------

    def limpiar(self):
        """
        Limpia completamente pantalla LCD.
        """

        self._comando(
            self.LCD_LIMPIAR
        )

        sleep_ms(2)

    # -------------------------------------------------

    def mover_cursor(self, fila, columna):
        """
        Mueve cursor a posición específica.

        Parámetros:
        - fila
        - columna

        Compatible con LCDs:
        - 16x2
        - 20x4
        """

        # Offsets DDRAM típicos HD44780
        offsets = [
            0x00,
            0x40,
            0x14,
            0x54
        ]

        # Limitar fila válida
        if fila >= self.filas:
            fila = self.filas - 1

        # Calcular dirección DDRAM
        direccion = (
            self.LCD_SET_DDRAM_ADDR
            |
            (offsets[fila] + columna)
        )

        self._comando(direccion)

    # -------------------------------------------------

    def escribir(self, texto):
        """
        Escribe texto desde posición actual
        del cursor.

        Parámetro:
        - texto : string a mostrar
        """

        for caracter in texto:

            self._dato(
                ord(caracter)
            )

    # -------------------------------------------------

    def escribir_linea(self, fila, texto):
        """
        Escribe texto completo en una línea.

        Parámetros:
        - fila
        - texto

        La función:
        - recorta si excede columnas
        - rellena espacios si sobra
        """

        texto = str(texto)

        # Recortar si excede ancho
        if len(texto) > self.columnas:

            texto = texto[:self.columnas]

        else:

            # Rellenar espacios
            texto = texto + (
                " "
                *
                (self.columnas - len(texto))
            )

        # Mover cursor al inicio línea
        self.mover_cursor(fila, 0)

        # Escribir contenido
        self.escribir(texto)

    # -------------------------------------------------

    def apagar_luz(self):
        """
        Apaga backlight del LCD.
        """

        self.backlight = 0x00

        self._escribir_byte(0)

    # -------------------------------------------------

    def encender_luz(self):
        """
        Enciende backlight del LCD.
        """

        self.backlight = (
            self.BIT_BACKLIGHT
        )

        self._escribir_byte(0)