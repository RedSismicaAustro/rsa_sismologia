class DS3231:
    """
    Librería básica para manejo del RTC DS3231.

    El DS3231 es un reloj de tiempo real (RTC)
    de alta precisión con comunicación I2C.

    Funciones principales:
    - lectura de fecha y hora
    - escritura de fecha y hora
    - conversión BCD <-> decimal

    Dirección I2C:
    - 0x68
    """

    # Dirección I2C fija del DS3231
    DIRECCION = 0x68

    # -------------------------------------------------

    def __init__(self, bus_i2c):
        """
        Inicializa el RTC.

        Parámetros:
        - bus_i2c : instancia del bus I2C
        """

        # Guardar referencia al bus I2C
        self.bus = bus_i2c

    # -------------------------------------------------

    def _bcd_a_decimal(self, valor):
        """
        Convierte un valor BCD a decimal.

        El DS3231 almacena números en formato:
        BCD (Binary Coded Decimal)

        Ejemplo:
        0x25 -> 25 decimal

        Parámetros:
        - valor : byte BCD

        Retorna:
        - entero decimal
        """

        return (
            ((valor >> 4) * 10)
            +
            (valor & 0x0F)
        )

    # -------------------------------------------------

    def _decimal_a_bcd(self, valor):
        """
        Convierte decimal a formato BCD.

        Ejemplo:
        25 decimal -> 0x25

        Parámetros:
        - valor : entero decimal

        Retorna:
        - byte en formato BCD
        """

        return (
            ((valor // 10) << 4)
            |
            (valor % 10)
        )

    # -------------------------------------------------

    def leer_fecha_hora(self):
        """
        Lee fecha y hora desde el RTC.

        Registros DS3231:
        0x00 -> segundos
        0x01 -> minutos
        0x02 -> horas
        0x03 -> día semana
        0x04 -> día mes
        0x05 -> mes
        0x06 -> año

        Proceso:
        1. Solicitar lectura desde registro 0x00
        2. Leer 7 bytes consecutivos
        3. Convertir BCD a decimal
        4. Retornar fecha/hora

        Retorna:
        (
            anio,
            mes,
            dia,
            hora,
            minuto,
            segundo,
            dia_semana
        )
        """

        # -----------------------------------------
        # Leer 7 bytes desde registro 0x00
        # -----------------------------------------

        datos = self.bus.write_read(
            self.DIRECCION,
            bytes([0x00]),
            7
        )

        # -----------------------------------------
        # Conversión de registros
        # -----------------------------------------

        segundo = self._bcd_a_decimal(
            datos[0] & 0x7F
        )

        minuto = self._bcd_a_decimal(
            datos[1]
        )

        hora = self._bcd_a_decimal(
            datos[2] & 0x3F
        )

        dia_semana = self._bcd_a_decimal(
            datos[3]
        )

        dia = self._bcd_a_decimal(
            datos[4]
        )

        mes = self._bcd_a_decimal(
            datos[5] & 0x1F
        )

        # DS3231 almacena año desde 2000
        anio = (
            self._bcd_a_decimal(datos[6])
            + 2000
        )

        return (
            anio,
            mes,
            dia,
            hora,
            minuto,
            segundo,
            dia_semana
        )

    # -------------------------------------------------

    def escribir_fecha_hora(
        self,
        anio,
        mes,
        dia,
        hora,
        minuto,
        segundo,
        dia_semana=1
    ):
        """
        Escribe fecha y hora en el RTC.

        Parámetros:
        - anio
        - mes
        - dia
        - hora
        - minuto
        - segundo
        - dia_semana

        Proceso:
        1. Convertir decimal a BCD
        2. Construir paquete I2C
        3. Escribir registros desde 0x00
        """

        # -----------------------------------------
        # Construcción de paquete de escritura
        #
        # Primer byte:
        # registro inicial = 0x00
        # -----------------------------------------

        datos = bytes([

            0x00,

            self._decimal_a_bcd(
                segundo
            ),

            self._decimal_a_bcd(
                minuto
            ),

            self._decimal_a_bcd(
                hora
            ),

            self._decimal_a_bcd(
                dia_semana
            ),

            self._decimal_a_bcd(
                dia
            ),

            self._decimal_a_bcd(
                mes
            ),

            # DS3231 almacena año desde 2000
            self._decimal_a_bcd(
                anio - 2000
            )
        ])

        # Escribir datos al RTC
        self.bus.write(
            self.DIRECCION,
            datos
        )

    # -------------------------------------------------

    def texto_fecha_hora(self):
        """
        Retorna fecha y hora como texto.

        Formato:
        YYYY-MM-DD HH:MM:SS

        Ejemplo:
        2026-05-15 14:35:22
        """

        (
            anio,
            mes,
            dia,
            hora,
            minuto,
            segundo,
            _
        ) = self.leer_fecha_hora()

        return (
            "{:04d}-{:02d}-{:02d} "
            "{:02d}:{:02d}:{:02d}"
        ).format(
            anio,
            mes,
            dia,
            hora,
            minuto,
            segundo
        )