import sys
import os
from pathlib import Path
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    else:
        return ''
ruta_librerias=os.path.dirname(__file__)
ruta_proyecto=extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src','librerias'))

# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QCalendarWidget, QMessageBox
)
from obspy import read
from metodos_rsa import (obtencion_hora,lectura_archivo)

from metodos_gestion import parametros_estaciones,obtener_directorios
import scipy.signal as signal
import struct
import matplotlib
import numpy as np
matplotlib.use('Qt5Agg')  # Asegúrate de que esto está antes de importar matplotlib.pyplot

def extraccion(archivo, tipo_evento, t_inicio, t_final,
                estaciones_eventos_total):
    """
    archivo:                     archivo con formato G:\DIA\AAMMDD000000
    tipo_evento:                 Tipo de evento, SISMO, CONTROL, FF, FC, Indefinido, etc.
    t_inicio:                    Tiempo de inicio en segundos
    t_final:                     Tiempo final en segundos
    estaciones_eventos_total:    las estaciones que tienen señal
    """
    directorios = obtener_directorios(archivo)
    parametros = parametros_estaciones()
    fecha_ = obtencion_hora(archivo)
    t_ini = fecha_ + t_inicio
    t_fin = fecha_ + t_final
    numero_de_muestras=int((t_fin-t_ini)*64)
    nombre_sis = os.path.join(directorios['Directorio_dia'] , t_ini.strftime('%y%m%d_%H%M%S.sis'))
    hora_formateada = t_ini.strftime(" %H: %M: %S")
    if t_inicio > t_final:
        QMessageBox.about(None, "Advertencia", "Hora incorrecta: Tiempo de inicio mayor a final")
        return
    if tipo_evento != "Ruido":
        print(nombre_sis[-17:],tipo_evento,numero_de_muestras)
        sismo_extraido=[]
        for numero_estacion in range(0,16):
            componente=int(parametros['COMPONENTE'][numero_estacion])-1
            if numero_estacion not in estaciones_eventos_total:
                stcanal=[]
                sis_extraido=np.array([])
            else:
                archivo_mseed_dia=os.path.join(directorios['Directorio_registros'],parametros['CODIGO'][numero_estacion]+directorios['sufijo_mseed'])
                stcanal = read(archivo_mseed_dia, format="MSEED", starttime=t_ini, endtime=t_fin, nearest_sample=False)
                # Aplica corrección de polaridad si es necesario
                if parametros['POLARIDAD'][numero_estacion] == 'N':
                    print('Canal con polaridad negativa: ', parametros['CODIGO'][numero_estacion])
                    stcanal[componente].data *= -1
                # Guardar archivo .mseed
                nombre_mseed = os.path.join(directorios['Directorio_eventos'] ,parametros['CODIGO'][numero_estacion] + t_ini.strftime('_%Y%m%d_%H%M%S.mseed'))
                stcanal[componente].data = stcanal[componente].data.astype('int32')
                stcanal.write(nombre_mseed, format='MSEED', encoding='STEIM1', reclen=512)
                sis_extraido = stcanal[componente].data
                muestras = stcanal[componente].stats.sampling_rate
                if muestras!=64:
                    sis_extraido = signal.resample(sis_extraido, numero_de_muestras)
                # Forzar tamaño correcto
                if sis_extraido.size != numero_de_muestras:
                    if sis_extraido.size > numero_de_muestras:
                        sis_extraido = sis_extraido[:numero_de_muestras]
                    else:
                        faltantes = numero_de_muestras - sis_extraido.size
                        sis_extraido = np.pad(sis_extraido, (0, faltantes), mode='constant')

            sismo_extraido.append(sis_extraido)
          
        # Crear archivo .sis si es evento sísmico
        if tipo_evento == "SISMO":
            archivo_cabecera = archivo[0:-12] + "cabecera_sismo"
            try:
                with open(archivo_cabecera, 'rb') as archivo_leer:
                    cabecera = b''
                    contador = 0
                    while contador < 2:
                        marcador = archivo_leer.read(2)
                        if marcador == b'\x08\x00':
                            cabecera_0 = archivo_leer.read(2)
                            num_caracteres = struct.unpack("<H", cabecera_0)[0]
                            archivo_leer.read(num_caracteres)
                            contador += 1
                    puntero = archivo_leer.tell()
                    archivo_leer.seek(0)
                    cabecera = archivo_leer.read(puntero) + b'\x08\x00\x0B\x00' + hora_formateada.encode('utf-8') + archivo_leer.read()
                with open(nombre_sis, 'wb') as archivo_escribir:
                    archivo_escribir.write(cabecera)
                    segundo_ = t_ini.hour * 3600 + t_ini.minute * 60 + t_ini.second
                    segundo_string = f'{segundo_:05}'
                    archivo_escribir.write(segundo_string.encode())
                    k = 0
                    for n in range( numero_de_muestras):
                        if k == 0:
                            archivo_escribir.write(
                                b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00'
                            )
                        k += 1
                        if k == 64:
                            k = 0
                        for m in range(16):
                            if parametros['HAB_CANAL'][m] == "1" and sismo_extraido[m].size>0:
                                valor = int(sismo_extraido[m][n])
                            else:
                                valor=0
                            if parametros['BITS'][m]=='20':
                                valor= int(valor*(32767 / 524287))
                            archivo_escribir.write(valor.to_bytes(2, byteorder='little', signed=True))
            except FileNotFoundError:
                print("Cabecera binaria no encontrada:", archivo_cabecera)

    print("Evento extraído y guardado correctamente.")
    return


class AplicacionEventos(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Selector de Evento Sísmico")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.calendario = QCalendarWidget(self)
        self.calendario.setGridVisible(True)
        layout.addWidget(self.calendario)

        self.boton_ejecutar = QPushButton("Procesar evento del día seleccionado", self)
        self.boton_ejecutar.clicked.connect(self.procesar_evento)
        layout.addWidget(self.boton_ejecutar)

        # Botón para salir
        self.boton_salir = QPushButton("Salir", self)
        self.boton_salir.clicked.connect(self.close)
        layout.addWidget(self.boton_salir)

        self.directorio_trabajo = 'G:\Mi unidad\DIA'
        #self.directorio_trabajo = 'C:\DIA'
        self.setLayout(layout)

    def procesar_evento(self):
        fecha_qt = self.calendario.selectedDate()
        archivo = os.path.join(self.directorio_trabajo, fecha_qt.toString("yyMMdd") + "000000")
        directorios = obtener_directorios(archivo)

        eventos_auxiliar = lectura_archivo(directorios['archivo_auxiliar'])
        eventos = lectura_archivo(directorios['archivo_csv'])
        solo_eventos = [fila[1] for fila in eventos]

        for linea_evento_auxiliar in eventos_auxiliar:
            evento, t_inicio, t_fin = linea_evento_auxiliar[1], float(linea_evento_auxiliar[4]), float(linea_evento_auxiliar[5])
            indice = solo_eventos.index(evento)
            evento_completo=eventos[indice]
            tipo_evento = evento_completo[2]
            evento_completo=evento_completo[3:]
            estaciones_eventos_total=[i for i, valor in enumerate(evento_completo) if valor != '-']
            extraccion(archivo, tipo_evento, t_inicio, t_fin, estaciones_eventos_total)




def main():
    app = QApplication(sys.argv)
    ventana = AplicacionEventos()
    ventana.resize(400, 300)
    ventana.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
