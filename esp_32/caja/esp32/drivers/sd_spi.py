import os
from machine import Pin, SDCard


class TarjetaSD:
    def __init__(
        self,
        pin_cs=5,
        pin_mosi=23,
        pin_miso=19,
        pin_sclk=18,
        punto_montaje="/sd"
    ):
        self.pin_cs = pin_cs
        self.pin_mosi = pin_mosi
        self.pin_miso = pin_miso
        self.pin_sclk = pin_sclk
        self.punto_montaje = punto_montaje
        self.sd = None
        self.montada = False

    def montar(self):
        try:
            self.sd = SDCard(
                slot=2,
                sck=Pin(self.pin_sclk),
                mosi=Pin(self.pin_mosi),
                miso=Pin(self.pin_miso),
                cs=Pin(self.pin_cs)
            )

            os.mount(self.sd, self.punto_montaje)
            self.montada = True
            return True

        except Exception as error:
            print("Error montando SD:", error)
            self.montada = False
            return False

    def desmontar(self):
        try:
            if self.montada:
                os.umount(self.punto_montaje)
                self.montada = False
            return True

        except Exception as error:
            print("Error desmontando SD:", error)
            return False

    def listar(self, ruta=None):
        if ruta is None:
            ruta = self.punto_montaje

        if not self.montada:
            return []

        try:
            return os.listdir(ruta)

        except Exception as error:
            print("Error listando SD:", error)
            return []

    def escribir_texto(self, nombre_archivo, texto, modo="a"):
        if not self.montada:
            print("SD no montada")
            return False

        ruta = self.punto_montaje + "/" + nombre_archivo

        try:
            with open(ruta, modo) as archivo:
                archivo.write(texto)

            return True

        except Exception as error:
            print("Error escribiendo SD:", error)
            return False

    def leer_texto(self, nombre_archivo):
        if not self.montada:
            print("SD no montada")
            return None

        ruta = self.punto_montaje + "/" + nombre_archivo

        try:
            with open(ruta, "r") as archivo:
                return archivo.read()

        except Exception as error:
            print("Error leyendo SD:", error)
            return None

    def existe(self, nombre_archivo):
        if not self.montada:
            return False

        try:
            archivos = os.listdir(self.punto_montaje)
            return nombre_archivo in archivos

        except:
            return False