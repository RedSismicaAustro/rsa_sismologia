# esp32/drivers/lis3dhtr.py
# Basado en datasheet ST LIS3DH / LIS3DHTR (I2C)


class LIS3DHTR:
    """
    Librería para acelerómetro LIS3DH / LIS3DHTR.

    Características:
    - acelerómetro triaxial MEMS
    - comunicación I2C
    - lectura X, Y, Z
    - selección de rango
    - selección de frecuencia de muestreo (ODR)

    El sensor entrega aceleración en:
    - X
    - Y
    - Z

    Unidad retornada:
    - g (gravedad)
    """

    # -------------------------------------------------
    # Dirección I2C típica
    # -------------------------------------------------

    DIRECCION = 0x19

    # -------------------------------------------------
    # Registros principales
    # -------------------------------------------------

    # Registro identificación dispositivo
    REG_WHO_AM_I = 0x0F

    # Registro control 1
    REG_CTRL1 = 0x20

    # Registro control 4
    REG_CTRL4 = 0x23

    # Registro salida eje X low byte
    REG_OUT_X_L = 0x28

    # -------------------------------------------------
    # Valor esperado WHO_AM_I
    # -------------------------------------------------

    WHO_AM_I_VALOR = 0x33

    # -------------------------------------------------
    # Rangos de aceleración
    #
    # Bits FS en CTRL_REG4
    # -------------------------------------------------

    RANGO_2G = 0x00
    RANGO_4G = 0x10
    RANGO_8G = 0x20
    RANGO_16G = 0x30

    # -------------------------------------------------
    # ODR = Output Data Rate
    #
    # Bits en CTRL_REG1
    # -------------------------------------------------

    ODR_1HZ = 0x10
    ODR_10HZ = 0x20
    ODR_25HZ = 0x30
    ODR_50HZ = 0x40
    ODR_100HZ = 0x50
    ODR_200HZ = 0x60
    ODR_400HZ = 0x70

    # -------------------------------------------------

    def __init__(
        self,
        bus_i2c,
        odr=ODR_100HZ,
        rango=RANGO_2G
    ):
        """
        Inicializa acelerómetro.

        Parámetros:
        - bus_i2c : instancia bus I2C
        - odr     : frecuencia de muestreo
        - rango   : rango aceleración

        Variables internas:
        - disponible
        - x, y, z
        - sensibilidad
        """

        # Referencia bus I2C
        self.bus = bus_i2c

        # Estado inicial
        self.disponible = False

        # Configuración seleccionada
        self.odr = odr
        self.rango = rango

        # Últimas lecturas
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0

        # Sensibilidad por defecto ±2g
        self._sensibilidad = 16384

        # Inicializar sensor
        self._inicializar()

    # -------------------------------------------------

    def _inicializar(self):
        """
        Inicializa el acelerómetro.

        Proceso:
        1. verificar presencia en I2C
        2. leer WHO_AM_I
        3. configurar CTRL_REG1
        4. configurar CTRL_REG4
        5. habilitar auto-incremento
        6. configurar sensibilidad
        """

        # Verificar dirección I2C
        if self.DIRECCION not in self.bus.scan():
            return

        # -----------------------------------------
        # Leer WHO_AM_I
        # -----------------------------------------

        who = self.bus.write_read(
            self.DIRECCION,
            bytes([self.REG_WHO_AM_I]),
            1
        )

        # Verificar identidad sensor
        if who[0] != self.WHO_AM_I_VALOR:
            return

        # -----------------------------------------
        # CTRL_REG1
        #
        # Configuración:
        # - ODR
        # - habilitar ejes X,Y,Z
        #
        # Bits:
        # XYZ enable = 0x07
        # -----------------------------------------

        ctrl1 = self.odr | 0x07

        self.bus.write(
            self.DIRECCION,
            bytes([
                self.REG_CTRL1,
                ctrl1
            ])
        )

        # -----------------------------------------
        # CTRL_REG4
        #
        # Configuración:
        # - high resolution
        # - rango
        #
        # bit 3 = HR
        # -----------------------------------------

        ctrl4 = 0x08 | self.rango

        self.bus.write(
            self.DIRECCION,
            bytes([
                self.REG_CTRL4,
                ctrl4
            ])
        )

        # -----------------------------------------
        # CTRL_REG2
        #
        # Habilitar auto incremento
        # de direcciones internas
        #
        # IF_ADD_INC = bit 2
        # -----------------------------------------

        self.bus.write(
            self.DIRECCION,
            bytes([0x21, 0x04])
        )

        # Configurar sensibilidad
        self._configurar_sensibilidad()

        # Sensor listo
        self.disponible = True

    # -------------------------------------------------

    def _configurar_sensibilidad(self):
        """
        Configura divisor de sensibilidad
        según rango seleccionado.

        Conversión:
        cuentas ADC -> g

        Valores aproximados derivados
        del datasheet.
        """

        # ±2g
        if self.rango == self.RANGO_2G:

            self._sensibilidad = 16384

        # ±4g
        elif self.rango == self.RANGO_4G:

            self._sensibilidad = 8192

        # ±8g
        elif self.rango == self.RANGO_8G:

            self._sensibilidad = 4096

        # ±16g
        elif self.rango == self.RANGO_16G:

            self._sensibilidad = 1365

    # -------------------------------------------------

    def _leer_crudo(self):
        """
        Lee datos crudos del acelerómetro.

        Proceso:
        1. leer 6 bytes consecutivos
        2. convertir signed 16 bits
        3. separar X,Y,Z

        Retorna:
        - x_raw
        - y_raw
        - z_raw
        """

        # -----------------------------------------
        # bit 7 = auto incremento
        #
        # Permite leer múltiples registros
        # consecutivos automáticamente.
        # -----------------------------------------

        datos = self.bus.write_read(
            self.DIRECCION,
            bytes([
                self.REG_OUT_X_L | 0x80
            ]),
            6
        )

        # -----------------------------------------
        # Conversión signed 16 bits
        # -----------------------------------------

        def conv(lo, hi):

            val = (hi << 8) | lo

            # Conversión complemento a dos
            if val & 0x8000:
                val -= 65536

            return val

        # Extraer ejes
        x = conv(datos[0], datos[1])

        y = conv(datos[2], datos[3])

        z = conv(datos[4], datos[5])

        return x, y, z

    # -------------------------------------------------

    def leer(self):
        """
        Lee aceleración calibrada.

        Proceso:
        1. verificar disponibilidad
        2. leer datos crudos
        3. aplicar sensibilidad

        Retorna:
        (
            x,
            y,
            z
        )

        Unidad:
        - g
        """

        # Verificar sensor inicializado
        if not self.disponible:

            return None, None, None

        # Leer datos crudos
        x_raw, y_raw, z_raw = (
            self._leer_crudo()
        )

        # Aplicar sensibilidad
        self.x = (
            x_raw / self._sensibilidad
        )

        self.y = (
            y_raw / self._sensibilidad
        )

        self.z = (
            z_raw / self._sensibilidad
        )

        return (
            self.x,
            self.y,
            self.z
        )