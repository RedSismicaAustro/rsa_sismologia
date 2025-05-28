from PyQt5.QtCore import QObject, QRunnable, pyqtSignal
from obspy import read
import numpy as np
import matplotlib.dates as mdates
import os

class SeñalesCarga(QObject):
    terminado = pyqtSignal(dict)       # Diccionario: {codigo_estacion: {'tiempos', 'datos', 'fs'}}
    error = pyqtSignal(str)            # Mensaje de error

class CargarDatosRunnable(QRunnable):
    def __init__(self, archivos_mseed, estaciones, componentes, tiempo_inicio, tiempo_final):
        super().__init__()
        self.archivos_mseed = archivos_mseed
        self.estaciones = estaciones
        self.componentes = componentes
        self.tiempo_inicio = tiempo_inicio
        self.tiempo_final = tiempo_final
        self.signals = SeñalesCarga()

    def run(self):
        datos_por_estacion = {}
        print("Lectura de datos")
        for archivo in self.archivos_mseed:
            nombre_archivo = os.path.basename(archivo)
            codigo_estacion = nombre_archivo[0:4]

            idx_estacion = self.estaciones.index(codigo_estacion)
            componente_idx = int(self.componentes[idx_estacion]) - 1

            st = read(archivo, starttime=self.tiempo_inicio, endtime=self.tiempo_final)
            #st.detrend('demean')
            #st.merge(method=1, fill_value='interpolate')
            traza = st[componente_idx]

            fs = traza.stats.sampling_rate
            print("calculo de tiempo")
            tiempos_mpl = mdates.date2num(traza.times("utcdatetime"))
            datos = traza.data.astype(np.float32)

            datos_por_estacion[codigo_estacion] = {
                'tiempos': tiempos_mpl,
                'datos': datos,
                'fs': fs
            }
            print("Saliendo")
        self.signals.terminado.emit(datos_por_estacion)
