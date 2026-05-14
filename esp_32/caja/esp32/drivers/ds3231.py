class DS3231:
    DIRECCION = 0x68

    def __init__(self, bus_i2c):
        self.bus = bus_i2c

    def _bcd_a_decimal(self, valor):
        return ((valor >> 4) * 10) + (valor & 0x0F)

    def _decimal_a_bcd(self, valor):
        return ((valor // 10) << 4) | (valor % 10)

    def leer_fecha_hora(self):
        datos = self.bus.write_read(self.DIRECCION, bytes([0x00]), 7)

        segundo = self._bcd_a_decimal(datos[0] & 0x7F)
        minuto = self._bcd_a_decimal(datos[1])
        hora = self._bcd_a_decimal(datos[2] & 0x3F)
        dia_semana = self._bcd_a_decimal(datos[3])
        dia = self._bcd_a_decimal(datos[4])
        mes = self._bcd_a_decimal(datos[5] & 0x1F)
        anio = self._bcd_a_decimal(datos[6]) + 2000

        return anio, mes, dia, hora, minuto, segundo, dia_semana

    def escribir_fecha_hora(self, anio, mes, dia, hora, minuto, segundo, dia_semana=1):
        datos = bytes([
            0x00,
            self._decimal_a_bcd(segundo),
            self._decimal_a_bcd(minuto),
            self._decimal_a_bcd(hora),
            self._decimal_a_bcd(dia_semana),
            self._decimal_a_bcd(dia),
            self._decimal_a_bcd(mes),
            self._decimal_a_bcd(anio - 2000)
        ])

        self.bus.write(self.DIRECCION, datos)

    def texto_fecha_hora(self):
        anio, mes, dia, hora, minuto, segundo, _ = self.leer_fecha_hora()

        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            anio, mes, dia, hora, minuto, segundo
        )