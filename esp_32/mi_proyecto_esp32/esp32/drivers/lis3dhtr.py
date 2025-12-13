# esp32/drivers/lis3dhtr.py
# Basado en datasheet ST LIS3DH / LIS3DHTR (I2C)

class LIS3DHTR:
    # Dirección I2C típica
    DIRECCION = 0x19

    # Registros
    REG_WHO_AM_I   = 0x0F
    REG_CTRL1     = 0x20
    REG_CTRL4     = 0x23
    REG_OUT_X_L   = 0x28

    WHO_AM_I_VALOR = 0x33

    # Rangos (FS bits en CTRL_REG4)
    RANGO_2G  = 0x00
    RANGO_4G  = 0x10
    RANGO_8G  = 0x20
    RANGO_16G = 0x30

    # ODR (CTRL_REG1)
    ODR_1HZ   = 0x10
    ODR_10HZ  = 0x20
    ODR_25HZ  = 0x30
    ODR_50HZ  = 0x40
    ODR_100HZ = 0x50
    ODR_200HZ = 0x60
    ODR_400HZ = 0x70

    def __init__(self, bus_i2c, odr=ODR_100HZ, rango=RANGO_2G):
        self.bus = bus_i2c
        self.disponible = False

        self.odr = odr
        self.rango = rango

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0

        self._sensibilidad = 16384  # por defecto ±2g
        self._inicializar()

    # -------------------------------------------------

    def _inicializar(self):
        if self.DIRECCION not in self.bus.scan():
            return

        who = self.bus.write_read(
            self.DIRECCION,
            bytes([self.REG_WHO_AM_I]),
            1
        )

        if who[0] != self.WHO_AM_I_VALOR:
            return

        # CTRL_REG1
        # ODR + habilitar X, Y, Z
        ctrl1 = self.odr | 0x07
        self.bus.write(self.DIRECCION, bytes([self.REG_CTRL1, ctrl1]))

        # CTRL_REG4
        # High resolution + rango
        ctrl4 = 0x08 | self.rango
        self.bus.write(self.DIRECCION, bytes([self.REG_CTRL4, ctrl4]))

        # CTRL_REG2: habilitar auto-incremento de direcciones
        # IF_ADD_INC = bit 2
        self.bus.write(self.DIRECCION, bytes([0x21, 0x04]))

        self._configurar_sensibilidad()
        self.disponible = True

    # -------------------------------------------------

    def _configurar_sensibilidad(self):
        # Valores del datasheet (mg/LSB → convertido a divisor)
        if self.rango == self.RANGO_2G:
            self._sensibilidad = 16384
        elif self.rango == self.RANGO_4G:
            self._sensibilidad = 8192
        elif self.rango == self.RANGO_8G:
            self._sensibilidad = 4096
        elif self.rango == self.RANGO_16G:
            self._sensibilidad = 1365

    # -------------------------------------------------

    def _leer_crudo(self):
        # Auto-incremento activado (bit 7)
        datos = self.bus.write_read(
            self.DIRECCION,
            bytes([self.REG_OUT_X_L | 0x80]),
            6
        )

        def conv(lo, hi):
            val = (hi << 8) | lo
            if val & 0x8000:
                val -= 65536
            return val

        x = conv(datos[0], datos[1])
        y = conv(datos[2], datos[3])
        z = conv(datos[4], datos[5])

        return x, y, z

    # -------------------------------------------------

    def leer(self):
        if not self.disponible:
            return None, None, None

        x_raw, y_raw, z_raw = self._leer_crudo()

        self.x = x_raw / self._sensibilidad
        self.y = y_raw / self._sensibilidad
        self.z = z_raw / self._sensibilidad

        return self.x, self.y, self.z
