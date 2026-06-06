import os
from machine import Pin, SDCard


class TarjetaSD:
    """
    Librería para manejo de tarjetas SD
    mediante interfaz SPI del ESP32.

    Funciones principales:
    - montar tarjeta
    - desmontar tarjeta
    - listar archivos
    - escribir texto
    - leer texto
    - verificar existencia de archivos

    Hardware utilizado:
    - interfaz SPI integrada del ESP32
    - clase SDCard de MicroPython

    Sistema de archivos esperado:
    - FAT32
    """

    # -------------------------------------------------

    def __init__(
        self,
        pin_cs=5,
        pin_mosi=23,
        pin_miso=19,
        pin_sclk=18,
        punto_montaje="/sd"
    ):
        """
        Inicializa configuración de tarjeta SD.

        Parámetros:
        - pin_cs          : chip select
        - pin_mosi        : línea MOSI
        - pin_miso        : línea MISO
        - pin_sclk        : reloj SPI
        - punto_montaje   : directorio de montaje

        No monta automáticamente la tarjeta.
        """

        # Configuración SPI
        self.pin_cs = pin_cs
        self.pin_mosi = pin_mosi
        self.pin_miso = pin_miso
        self.pin_sclk = pin_sclk

        # Punto de montaje virtual
        self.punto_montaje = punto_montaje

        # Objeto SDCard
        self.sd = None

        # Estado interno
        self.montada = False

    # -------------------------------------------------

    def montar(self):
        """
        Monta tarjeta SD en el sistema.

        Proceso:
        1. inicializar periférico SDCard
        2. montar sistema de archivos
        3. actualizar estado interno

        Retorna:
        - True  : montaje correcto
        - False : error
        """

        try:

            # -----------------------------------------
            # Inicializar interfaz SD SPI
            # -----------------------------------------

            self.sd = SDCard(
                slot=2,

                sck=Pin(self.pin_sclk),

                mosi=Pin(self.pin_mosi),

                miso=Pin(self.pin_miso),

                cs=Pin(self.pin_cs)
            )

            # -----------------------------------------
            # Montar sistema de archivos
            # -----------------------------------------

            os.mount(
                self.sd,
                self.punto_montaje
            )

            # Actualizar estado
            self.montada = True

            return True

        except Exception as error:

            print(
                "Error montando SD:",
                error
            )

            self.montada = False

            return False

    # -------------------------------------------------

    def desmontar(self):
        """
        Desmonta tarjeta SD del sistema.

        Importante:
        Debe ejecutarse antes de:
        - retirar tarjeta
        - apagar sistema
        - reiniciar

        Retorna:
        - True  : correcto
        - False : error
        """

        try:

            # Verificar estado
            if self.montada:

                os.umount(
                    self.punto_montaje
                )

                self.montada = False

            return True

        except Exception as error:

            print(
                "Error desmontando SD:",
                error
            )

            return False

    # -------------------------------------------------

    def listar(self, ruta=None):
        """
        Lista contenido de directorio.

        Parámetros:
        - ruta : directorio a listar

        Si ruta es None:
        usa punto de montaje principal.

        Retorna:
        - lista de archivos/directorios
        """

        # Ruta por defecto
        if ruta is None:

            ruta = self.punto_montaje

        # Verificar tarjeta montada
        if not self.montada:

            return []

        try:

            return os.listdir(ruta)

        except Exception as error:

            print(
                "Error listando SD:",
                error
            )

            return []

    # -------------------------------------------------

    def escribir_texto(
        self,
        nombre_archivo,
        texto,
        modo="a"
    ):
        """
        Escribe texto en archivo.

        Parámetros:
        - nombre_archivo
        - texto
        - modo:
            "a" -> append
            "w" -> sobrescribir

        Retorna:
        - True  : escritura correcta
        - False : error
        """

        # Verificar tarjeta montada
        if not self.montada:

            print("SD no montada")

            return False

        # Construir ruta completa
        ruta = (
            self.punto_montaje
            +
            "/"
            +
            nombre_archivo
        )

        try:

            # Abrir archivo
            with open(ruta, modo) as archivo:

                archivo.write(texto)

            return True

        except Exception as error:

            print(
                "Error escribiendo SD:",
                error
            )

            return False

    # -------------------------------------------------

    def leer_texto(self, nombre_archivo):
        """
        Lee contenido completo de archivo.

        Parámetros:
        - nombre_archivo

        Retorna:
        - string contenido archivo
        - None si falla
        """

        # Verificar tarjeta montada
        if not self.montada:

            print("SD no montada")

            return None

        # Construir ruta completa
        ruta = (
            self.punto_montaje
            +
            "/"
            +
            nombre_archivo
        )

        try:

            with open(ruta, "r") as archivo:

                return archivo.read()

        except Exception as error:

            print(
                "Error leyendo SD:",
                error
            )

            return None

    # -------------------------------------------------

    def existe(self, nombre_archivo):
        """
        Verifica existencia de archivo.

        Parámetros:
        - nombre_archivo

        Retorna:
        - True  : existe
        - False : no existe
        """

        # Verificar tarjeta montada
        if not self.montada:

            return False

        try:

            # Obtener lista archivos
            archivos = os.listdir(
                self.punto_montaje
            )

            return (
                nombre_archivo
                in
                archivos
            )

        except:

            return False