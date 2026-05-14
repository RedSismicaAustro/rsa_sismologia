import time

class AHT20:
    DIRECCION = 0x38

    def __init__(self, bus_i2c):
        self.bus = bus_i2c
        self.disponible = False
        self.temperatura = None
        self.humedad = None
        self._inicializar()

    def _inicializar(self):
        dispositivos = self.bus.scan()
        if self.DIRECCION not in dispositivos:
            self.disponible = False
            return

        # Comando de inicialización recomendado
        self.bus.write(self.DIRECCION, b'\xBE\x08\x00')
        time.sleep_ms(10)
        self.disponible = True

    def leer(self):
        if not self.disponible:
            return None, None

        # Trigger measurement
        self.bus.write(self.DIRECCION, b'\xAC\x33\x00')
        time.sleep_ms(80)

        datos = self.bus.read(self.DIRECCION, 6)

        hum_raw = ((datos[1] << 16) | (datos[2] << 8) | datos[3]) >> 4
        temp_raw = ((datos[3] & 0x0F) << 16) | (datos[4] << 8) | datos[5]

        self.humedad = hum_raw * 100 / 1048576
        self.temperatura = temp_raw * 200 / 1048576 - 50

        return self.temperatura, self.humedad
