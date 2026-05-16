from machine import Pin


class ControlReles:
    """
    Librería para control de relés del sistema
    de adquisición basado en puentes.

    Funciones principales:
    - habilitar/deshabilitar medición
    - energizar/desenergizar puente
    - seleccionar tipo de sensor
    - seleccionar modo de medición

    La librería abstrae completamente
    el manejo de GPIOs y las combinaciones
    válidas de relés.
    """

    # -------------------------------------------------
    # Definición de modos de medición
    # -------------------------------------------------

    MODO_DEFORMACION = "deformacion"
    MODO_INCORRECTO_1 = "incorrecto 1"
    MODO_INCORRECTO_2 = "incorrecto 2"
    MODO_TEMPERATURA = "temperatura"

    # -------------------------------------------------
    # Definición de tipos de sensor
    # -------------------------------------------------

    SENSOR_TIPO_1 = 0
    SENSOR_TIPO_2 = 1

    # -------------------------------------------------

    def __init__(self):
        """
        Inicializa todos los GPIOs asociados
        a relés del sistema.

        Relés:
        - GPIO13 -> habilitación medición
        - GPIO14 -> alimentación puente
        - GPIO16 -> selección modo
        - GPIO17 -> selección modo
        - GPIO25 -> selección tipo sensor

        Al iniciar:
        - se configura un estado seguro
        """

        # -----------------------------------------
        # Relé habilitación medición
        #
        # 0 -> medición deshabilitada
        # 1 -> medición habilitada
        # -----------------------------------------

        self.rele_medicion = Pin(
            13,
            Pin.OUT
        )

        # -----------------------------------------
        # Relé alimentación puente
        #
        # 0 -> puente sin alimentación
        # 1 -> puente energizado
        # -----------------------------------------

        self.rele_alimentacion = Pin(
            14,
            Pin.OUT
        )

        # -----------------------------------------
        # Relés selección modo
        #
        # 00 -> deformación
        # 11 -> temperatura
        # -----------------------------------------

        self.rele_3 = Pin(
            16,
            Pin.OUT
        )

        self.rele_4 = Pin(
            17,
            Pin.OUT
        )

        # -----------------------------------------
        # Relé selección tipo sensor
        #
        # 0 -> tipo 1
        # 1 -> tipo 2
        # -----------------------------------------

        self.rele_tipo_sensor = Pin(
            25,
            Pin.OUT
        )

        # Variables internas de estado
        self.modo_actual = None
        self.tipo_sensor_actual = (
            self.SENSOR_TIPO_1
        )

        # Configurar estado inicial seguro
        self.estado_seguro()

    # -------------------------------------------------

    def estado_seguro(self):
        """
        Configura estado seguro inicial.

        Estado:
        - medición deshabilitada
        - puente sin alimentación
        - sensor tipo 1
        - modo deformación
        """

        self.deshabilitar_medicion()

        self.desenergizar_puente()

        self.seleccionar_sensor_tipo_1()

        self.seleccionar_modo_deformacion()

    # -------------------------------------------------

    def habilitar_medicion(self):
        """
        Habilita el sistema de medición.
        """

        self.rele_medicion.value(1)

    # -------------------------------------------------

    def deshabilitar_medicion(self):
        """
        Deshabilita el sistema de medición.
        """

        self.rele_medicion.value(0)

    # -------------------------------------------------

    def energizar_puente(self):
        """
        Energiza el puente de medición
        con 3.3 V.
        """

        self.rele_alimentacion.value(1)

    # -------------------------------------------------

    def desenergizar_puente(self):
        """
        Desconecta alimentación del puente.
        """

        self.rele_alimentacion.value(0)

    # -------------------------------------------------

    def seleccionar_sensor_tipo_1(self):
        """
        Selecciona sensor tipo 1.
        """

        self.rele_tipo_sensor.value(0)

        self.tipo_sensor_actual = (
            self.SENSOR_TIPO_1
        )

    # -------------------------------------------------

    def seleccionar_sensor_tipo_2(self):
        """
        Selecciona sensor tipo 2.
        """

        self.rele_tipo_sensor.value(1)

        self.tipo_sensor_actual = (
            self.SENSOR_TIPO_2
        )

    # -------------------------------------------------

    def seleccionar_tipo_sensor(self, tipo):
        """
        Selecciona tipo de sensor.

        Parámetro:
        - tipo:
            * SENSOR_TIPO_1
            * SENSOR_TIPO_2
        """

        if tipo == self.SENSOR_TIPO_1:

            self.seleccionar_sensor_tipo_1()

        elif tipo == self.SENSOR_TIPO_2:

            self.seleccionar_sensor_tipo_2()

        else:

            raise ValueError(
                "Tipo de sensor no válido"
            )

    # -------------------------------------------------

    def seleccionar_modo_deformacion(self):
        """
        Selecciona medición de deformación.

        Configuración:
        - rele_3 = 0
        - rele_4 = 0

        Combinación válida:
        00 -> deformación
        """

        self.rele_3.value(0)

        self.rele_4.value(0)

        self.modo_actual = (
            self.MODO_DEFORMACION
        )

    # -------------------------------------------------

    def seleccionar_modo_incorrecto_1(self):
        """
        Selecciona medición incorrecto 1, solo pruebas.

        Configuración:
        - rele_3 = 0
        - rele_4 = 1

        Combinación válida:
        01 -> incorrecto 1
        """

        self.rele_3.value(0)

        self.rele_4.value(1)

        self.modo_actual = (
            self.MODO_INCORRECTO_1
        )

    # -------------------------------------------------

    def seleccionar_modo_incorrecto_2(self):
        """
        Selecciona medición incorrecto 1, solo pruebas.

        Configuración:
        - rele_3 = 1
        - rele_4 = 0

        Combinación válida:
        10 -> incorrecto 2
        """

        self.rele_3.value(1)

        self.rele_4.value(0)

        self.modo_actual = (
            self.MODO_INCORRECTO_2
        )



    # -------------------------------------------------

    def seleccionar_modo_temperatura(self):
        """
        Selecciona medición de temperatura.

        Configuración:
        - rele_3 = 1
        - rele_4 = 1

        Combinación válida:
        11 -> temperatura
        """

        self.rele_3.value(1)

        self.rele_4.value(1)

        self.modo_actual = (
            self.MODO_TEMPERATURA
        )

    # -------------------------------------------------

    def seleccionar_modo(self, modo):
        """
        Selecciona modo de medición.

        Parámetro:
        - modo:
            * MODO_DEFORMACION
            * MODO_INCORRECTO_1
            * MODO_INCORRECTO_2
            * MODO_TEMPERATURA
        """

        if modo == self.MODO_DEFORMACION:
            self.seleccionar_modo_deformacion()

        elif modo == self.MODO_INCORRECTO_1:
            self.seleccionar_modo_incorrecto_1()

        elif modo == self.MODO_INCORRECTO_2:
            self.seleccionar_modo_incorrecto_2()

        elif modo == self.MODO_TEMPERATURA:
            self.seleccionar_modo_temperatura()

        else:
            raise ValueError("Modo de medición no válido")

    # -------------------------------------------------

    def iniciar_medicion_deformacion(
        self,
        tipo_sensor=SENSOR_TIPO_1
    ):
        """
        Ejecuta secuencia segura para
        iniciar medición de deformación.

        Secuencia:
        1. deshabilitar medición
        2. desenergizar puente
        3. seleccionar sensor
        4. seleccionar modo deformación
        5. energizar puente
        6. habilitar medición
        """

        self.deshabilitar_medicion()

        self.desenergizar_puente()

        self.seleccionar_tipo_sensor(
            tipo_sensor
        )

        self.seleccionar_modo_deformacion()

        self.energizar_puente()

        self.habilitar_medicion()

    # -------------------------------------------------

    def iniciar_medicion_temperatura(
        self,
        tipo_sensor=SENSOR_TIPO_1
    ):
        """
        Ejecuta secuencia segura para
        iniciar medición de temperatura.
        """

        self.deshabilitar_medicion()

        self.desenergizar_puente()

        self.seleccionar_tipo_sensor(
            tipo_sensor
        )

        self.seleccionar_modo_temperatura()

        self.energizar_puente()

        self.habilitar_medicion()

    # -------------------------------------------------

    def detener_medicion(self):
        """
        Detiene medición de forma segura.

        Acciones:
        - deshabilita medición
        - desenergiza puente

        No modifica:
        - modo actual
        - tipo de sensor
        """

        self.deshabilitar_medicion()

        self.desenergizar_puente()

    # -------------------------------------------------

    def obtener_estado(self):
        """
        Retorna estado completo del sistema.

        Retorna:
        - diccionario con:
            * relés
            * modo
            * tipo de sensor
        """

        return {
            "medicion":
                self.rele_medicion.value(),

            "alimentacion":
                self.rele_alimentacion.value(),

            "rele_3":
                self.rele_3.value(),

            "rele_4":
                self.rele_4.value(),

            "tipo_sensor":
                self.rele_tipo_sensor.value(),

            "modo_actual":
                self.modo_actual,

            "tipo_sensor_actual":
                self.tipo_sensor_actual,
        }