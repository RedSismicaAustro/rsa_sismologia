from machine import Pin


class ControlReles:
    """
    Control de relés para selección de medición, alimentación,
    tipo de sensor y modo de lectura.

    Relés:
    - rele_medicion: GPIO13
        0 = medición deshabilitada
        1 = medición habilitada

    - rele_alimentacion: GPIO14
        0 = puente sin alimentación
        1 = puente energizado con 3.3 V

    - rele_3: GPIO16
    - rele_4: GPIO17
        Combinación:
        00 = medición de deformación
        01 = combinación no válida
        10 = combinación no válida
        11 = medición de temperatura

    - rele_tipo_sensor: GPIO25
        0 = sensor tipo 1
        1 = sensor tipo 2
    """

    MODO_DEFORMACION = "deformacion"
    MODO_TEMPERATURA = "temperatura"

    SENSOR_TIPO_1 = 0
    SENSOR_TIPO_2 = 1

    def __init__(self):
        self.rele_medicion = Pin(13, Pin.OUT)
        self.rele_alimentacion = Pin(14, Pin.OUT)
        self.rele_3 = Pin(16, Pin.OUT)
        self.rele_4 = Pin(17, Pin.OUT)
        self.rele_tipo_sensor = Pin(25, Pin.OUT)

        self.modo_actual = None
        self.tipo_sensor_actual = self.SENSOR_TIPO_1

        self.estado_seguro()

    def estado_seguro(self):
        """
        Estado seguro inicial:
        - medición deshabilitada
        - puente sin alimentación
        - sensor tipo 1
        - modo deformación por defecto
        """
        self.deshabilitar_medicion()
        self.desenergizar_puente()
        self.seleccionar_sensor_tipo_1()
        self.seleccionar_modo_deformacion()

    def habilitar_medicion(self):
        self.rele_medicion.value(1)

    def deshabilitar_medicion(self):
        self.rele_medicion.value(0)

    def energizar_puente(self):
        self.rele_alimentacion.value(1)

    def desenergizar_puente(self):
        self.rele_alimentacion.value(0)

    def seleccionar_sensor_tipo_1(self):
        self.rele_tipo_sensor.value(0)
        self.tipo_sensor_actual = self.SENSOR_TIPO_1

    def seleccionar_sensor_tipo_2(self):
        self.rele_tipo_sensor.value(1)
        self.tipo_sensor_actual = self.SENSOR_TIPO_2

    def seleccionar_tipo_sensor(self, tipo):
        if tipo == self.SENSOR_TIPO_1:
            self.seleccionar_sensor_tipo_1()
        elif tipo == self.SENSOR_TIPO_2:
            self.seleccionar_sensor_tipo_2()
        else:
            raise ValueError("Tipo de sensor no válido")

    def seleccionar_modo_deformacion(self):
        """
        Relé 3 = 0
        Relé 4 = 0
        """
        self.rele_3.value(0)
        self.rele_4.value(0)
        self.modo_actual = self.MODO_DEFORMACION

    def seleccionar_modo_temperatura(self):
        """
        Relé 3 = 1
        Relé 4 = 1
        """
        self.rele_3.value(1)
        self.rele_4.value(1)
        self.modo_actual = self.MODO_TEMPERATURA

    def seleccionar_modo(self, modo):
        if modo == self.MODO_DEFORMACION:
            self.seleccionar_modo_deformacion()
        elif modo == self.MODO_TEMPERATURA:
            self.seleccionar_modo_temperatura()
        else:
            raise ValueError("Modo de medición no válido")

    def iniciar_medicion_deformacion(self, tipo_sensor=SENSOR_TIPO_1):
        """
        Secuencia recomendada:
        1. deshabilitar medición
        2. desenergizar puente
        3. seleccionar tipo de sensor
        4. seleccionar modo deformación
        5. energizar puente
        6. habilitar medición
        """
        self.deshabilitar_medicion()
        self.desenergizar_puente()

        self.seleccionar_tipo_sensor(tipo_sensor)
        self.seleccionar_modo_deformacion()

        self.energizar_puente()
        self.habilitar_medicion()

    def iniciar_medicion_temperatura(self, tipo_sensor=SENSOR_TIPO_1):
        """
        Secuencia recomendada para temperatura.
        """
        self.deshabilitar_medicion()
        self.desenergizar_puente()

        self.seleccionar_tipo_sensor(tipo_sensor)
        self.seleccionar_modo_temperatura()

        self.energizar_puente()
        self.habilitar_medicion()

    def detener_medicion(self):
        """
        Apaga la medición y desenergiza el puente.
        No cambia el modo seleccionado.
        """
        self.deshabilitar_medicion()
        self.desenergizar_puente()

    def obtener_estado(self):
        return {
            "medicion": self.rele_medicion.value(),
            "alimentacion": self.rele_alimentacion.value(),
            "rele_3": self.rele_3.value(),
            "rele_4": self.rele_4.value(),
            "tipo_sensor": self.rele_tipo_sensor.value(),
            "modo_actual": self.modo_actual,
            "tipo_sensor_actual": self.tipo_sensor_actual,
        }