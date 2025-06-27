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
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))
# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)



#Programa para insertar los registro fuera de tiemp, incluye los disparos por eventos de los ETNA u cualquier otros tipo de digitalizador
#Estructura de la informacions  ..\AAAA\ESTA\Datos evt
# AAAA año
# ESTA estación
# Datos EVT daton con la información del registro en el nombre o en los metadatos del registro

from metodos_rsa import parametros_estaciones,obtener_directorios,obtenerTraza,escritura_archivo,recolectar_evt,lectura_archivo,clasificar_evento_sismico,ejecutar_en_vm
from PyQt5 import uic, QtWidgets#Importamos módulo uic y Qtwidgets

import re
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtWidgets import (QApplication,QMainWindow, QMessageBox)
from obspy import read
from obspy import Stream
from datetime import datetime
from datetime import timedelta
from obspy.io.mseed.util import get_record_information
dic_estaciones = {
    "CHB": "CHAB",
    "CHC": "CHAC",
    "MZB": "MABA",
    "MZC": "MACI",    
    "MZD": "MADE",
    "PABA": "DPBA",
    "PACI": "DPCI",
    "ACC1": "EEAS",#Esta denominación está en varios lugares, EEAlSur,EEALNor,Miraflo    
    "": "",
    "": "",
    "UCET": "UCET",#Esta está marcada como unversidad de Cuenca
    "UDEC": "UCET"#Falta esta estación en la lista de estaciones, es la Universidad de Cuenca
    
}


dic_estaciones_dir = {
    "Azogues": "CICA",
    "CICA": "CICA",
    "ChanludBase":"CHAB",
    "ChaBase": "CHAB",
    "Chanlbas": "CHAB",
    "Chanlbas": "CHAB",
    "Chanlcim": "CHAC",
    "ChaCima": "CHAC",
    "ChanludCima": "CHAC",
    "EEEBASE": "EEAS",
    "EEBase": "EEBA",
    "EEE-Base": "EEBA",
    "EEAlNor": "EEAN",
    "EEALNor": "EEAN",
    "EEE-AltNort": "EEAN",
    "EEAltSur": "EEAS",
    "EEAlSur": "EEAS",
    "EEE-AltSur": "EEAS",
    "Huajibam": "AHUA",
    "Huajibamba": "AHUA",    
    "HUAJIBAM": "AHUA",    
    "Huajibamba-SSA": "AHUA",    
    "MazarBas": "MABA",
    "MazarBase": "MABA",
    "MazarCim": "MACI",    
    "MazarCima": "MACI",    
    "MazarDer": "MADE",
    "Miraflo": "MIRA",
    "Miraflor": "MIRA",
    "Miraflores": "MIRA",
    "PauteBas": "DPBA", #Paute base
    "Pautebas": "DPBA", #Paute base
    "PauteBase": "DPBA", #Paute base
    "PauMed": "DPME", #Paute medio
    "PauteCim": "DPCI", #Paute Cima
    "PauteCim": "DPCI", #Paute Cima
    "PauteCima": "DPCI", #Paute Cima
    "Regcivil": "REGC",#
    "UAzuay": "UDAZ",#
    "UCCamp": "UCET",#
    "UCcamp": "UCET",#
    "UCoficin": "UCAO",#
    "UDEC": "UCET"#Falta esta estación en la lista de estaciones, es la Universidad de Cuenca
    
}


def obtener_estacion_dir(entrada):
    return dic_estaciones_dir.get(entrada, entrada)

def obtener_estacion(entrada):
    return dic_estaciones.get(entrada, entrada)

def ajustar_tiempos_stream_por_evento(eventos, stream, tolerancia_minutos):

    tr = stream[0]
    estacion = obtener_estacion(tr.stats.station)
    inicio = tr.stats.starttime

    tiempo_stream = inicio.datetime
    archivo_mseed = f"{estacion}_{inicio.strftime('%Y%m%d_%H%M%S')}.mseed"
    tolerancia_segundos = tolerancia_minutos * 60
    mejor_evento = None
    mejor_diferencia = float('inf')
    mejor_tipo = None
    for evento in eventos:
        tipo = evento[2]
        if tipo not in ("FF", "FC", "SISMO"):
            continue
        try:
            tiempo_evento = datetime.strptime(evento[1][:13], "%y%m%d_%H%M%S")
        except:
            continue
        diferencia = abs((tiempo_stream - tiempo_evento).total_seconds())
        if diferencia <= tolerancia_segundos and diferencia < mejor_diferencia:
            mejor_evento = tiempo_evento
            mejor_diferencia = diferencia
            mejor_tipo = tipo
    if mejor_evento:
        diferencia_tiempo = mejor_evento - tiempo_stream
        bandera = True
    else:
        diferencia_tiempo = timedelta(seconds=0)
        bandera = False
    for traza in stream:
        traza.stats.starttime += diferencia_tiempo
    return stream, bandera, mejor_tipo,archivo_mseed


def insertar_evento(directorio_grabar: str, eventos: list, st: Stream, serial_equipo: str = None) -> list:
    """
    Inserta un evento en la lista de eventos, guardando el archivo MiniSEED
    con los parámetros originales del Stream.
    Args:
        directorio_grabar (str): Ruta del directorio donde se guardará el nuevo archivo.
        eventos (list): Lista de eventos (estructura esperada: lista de listas).
        st (Stream): Stream con los datos ya leídos y posiblemente modificados.
    Returns:
        list: Lista de eventos actualizada.
    """
    # Extraer datos temporales desde el primer Trace
    tr = st[0]
    estacion = obtener_estacion(tr.stats.station)
    inicio = tr.stats.starttime

    # Construcción del nombre del archivo: serial_YYYYMMDD_HHMMSS.mseed o estación_...
    prefijo = serial_equipo if serial_equipo else estacion
    nombre_archivo = f"{prefijo}_{inicio.strftime('%Y%m%d_%H%M%S')}.mseed"

    # Si se usa serial, crear subdirectorio
    if serial_equipo:
        directorio_grabar = os.path.join(directorio_grabar, str(serial_equipo))
        os.makedirs(directorio_grabar, exist_ok=True)

    ruta_completa = os.path.join(directorio_grabar, nombre_archivo)
    # Cargar parámetros de estación
    parametros = parametros_estaciones()
    estaciones = parametros['CODIGO']
    try:
        indice = estaciones.index(estacion)
    except ValueError:
        print(f"Estación {estacion} no está en la configuración.")
        return eventos

    # Construir nombre del evento buscado (formato corto: AAMMDD_HHMMSS.sis)
    
    archivo_evento = f"{inicio.strftime('%y%m%d_%H%M%S')}.sis"
    segundos_elementos = [evento[1] for evento in eventos]

    if archivo_evento not in segundos_elementos:
        return eventos
    n_evento = segundos_elementos.index(archivo_evento)

    for tr in st:
        if not hasattr(tr.stats, "calib"):
            tr.stats.calib = 1.0  # Asumimos 1.0 si no se definió (caso común en algunos formatos)
  
    st.write(ruta_completa, format='MSEED')

    # Actualizar eventos
    eventos[n_evento][indice + 3] = estacion + parametros['COMPONENTE'][indice] + '1000000'

    return eventos

def transformar_copiar_EVT(archivo_evt, directorio_trabajo, bandera_verificar, bandera_insertar, directorio_destino=None):
    datos_completos = []
    directorios_almacenamiento = re.split(r"[\\/]", archivo_evt)
    directorios = []
    directorio_estacion_almacenado = ""

    for i, directorio_arbol in enumerate(directorios_almacenamiento):
        if directorio_arbol in dic_estaciones_dir:
            directorio_estacion_almacenado += dic_estaciones_dir[directorio_arbol] + " "
        if directorio_arbol != '':
            directorios.append(directorio_arbol)
    if directorio_estacion_almacenado == '':
        directorio_estacion_almacenado = "Fuera de diccionario: " + ' / '.join(directorios)
    mensaje, mensaje_1, resultado_str = '', '', ''
    archivo_mseed, archivo, estacion = '', '', 'Ninguna'
    equipo_modelo, equipo_version, equipo_serial = 'Desconocido', 'Desconocida', 'Desconocido'
    bandera_formato = 0

    try:
        st = read(archivo_evt, format='KINEMETRICS_EVT')
        evt_info = st[0].stats.kinemetrics_evt
        #for stream in st:
            #stream.data = stream.data.astype(np.int32)
        bandera_formato = 1
    except:
        archivo_mseed = "No es compatible al formato"
        ejecutar_en_vm(archivo_evt,'O:\KINEMETRICS')
        mensaje = "Error: archivo no legible como EVT"
        mensaje_1 = "No insertado"
        datos_grabar = [archivo_evt, archivo_mseed, mensaje, "", mensaje_1,
                    "", directorio_estacion_almacenado, "Desconocido",
                    "Desconocido", "Desconocida", "Desconocido"]
        datos_completos.append(datos_grabar)

    if bandera_formato:
        t = st[0].stats.starttime
        archivo=os.path.join(directorio_trabajo, f"{t.year % 100:02d}{t.month:02d}{t.day:02d}{t.hour:02d}{t.minute:02d}{t.second:02d}") 
        directorios = obtener_directorios(archivo)
            
        # === EXTRAER INFO DEL EQUIPO ===
        try:
            equipo_modelo =evt_info['comment']
            equipo_version = evt_info['instrument']
            equipo_serial = evt_info['serialnumber']
        except Exception as e:
            print(f"Error obteniendo info de equipo: {e}")
        estacion =obtener_estacion(st[0].stats.station)

        equipo_serial = str(equipo_serial) if directorio_destino else None

        directorio_final = directorio_destino if directorio_destino else directorios['Directorio_eventos']

        if os.path.exists(directorios['archivo_csv']):
            eventos = lectura_archivo(directorios['archivo_csv'])
            st,bandera_localizacion,tipo,archivo_mseed =ajustar_tiempos_stream_por_evento(eventos, st, tolerancia_minutos=5)
            if equipo_serial:
                archivo_mseed=equipo_serial+archivo_mseed[4:]
                archivo_mseed=os.path.join(directorio_final,equipo_serial,archivo_mseed)
            
            else:
                archivo_mseed=os.path.join(directorio_final,archivo_mseed)
            t = st[0].stats.starttime
            
            st_copia = st.copy()
            resultado = clasificar_evento_sismico(st_copia)
            resultado_str = ' / '.join([f"{k}: {v}" for k, v in resultado.items()])
            if bandera_localizacion:
                mensaje = "Evento encontrado: "+tipo
            else:
                mensaje = "Evento no encontrado"

            if resultado['evento_sismico_probable']:
                if bandera_verificar:
                    plt.close('all')
                    fig, axs = plt.subplots(len(st), 1, figsize=(10, 6), sharex=True)
                    if len(st) == 1: axs = [axs]
                    for ax, tr in zip(axs, st):
                            tiempo = tr.times("matplotlib")
                            ax.plot(tiempo, tr.data, label=tr.id)
                            ax.legend()
                    axs[-1].set_xlabel("Tiempo")
                    nombre_evt = os.path.basename(archivo_evt)
                    titulo_grafico = f"Verificación del Evento\nEVT: {nombre_evt}  |  Evento: {archivo}  |  Resultado: {mensaje}"
                    plt.suptitle(titulo_grafico)
                    plt.tight_layout()
                    plt.show()
                    if bandera_localizacion:
                        respuesta = QMessageBox.question(None, "Insertar evento",
                                                             "¿Deseas insertar este evento en la estructura de datos?",
                                                             QMessageBox.Yes | QMessageBox.No)
                        if respuesta == QMessageBox.No:
                                mensaje_1 = 'No insertado'
                                bandera_localizacion=False
                    else:
                        QMessageBox.information(None, "AVISO", f"EVT: {nombre_evt}  {mensaje}")

            if bandera_insertar and bandera_localizacion:
                eventos = insertar_evento(directorio_final, eventos, st, equipo_serial)
                escritura_archivo(directorios['archivo_csv'], eventos)
                mensaje_1 = 'Insertado'
        else:
            archivo_mseed="No encontrado csv del dia:"+directorios['archivo_csv']
        datos_grabar = [archivo_evt, archivo_mseed, mensaje, archivo, mensaje_1,
                            resultado_str, directorio_estacion_almacenado, estacion,
                            equipo_modelo, equipo_version, equipo_serial]
        datos_completos.append(datos_grabar)
    return datos_completos



def transformar_copiar_lista_EVT(self, lista_rutas_evt):
    datos_completos = []
    datos=['archivo_evt', 'archivo_mseed', 'mensaje', 'archivo', 'insercion',
                        'resultado_str', 'directorio_estacion_almacenado', 'estacion',
                        'equipo_modelo', 'equipo_version', 'equipo_serial']
    datos_completos.append(datos)
    total_archivos = len(lista_rutas_evt)

    self.progressBar.setMaximum(total_archivos)
    self.progressBar.setValue(0)

    for contador, archivo_evt in enumerate(lista_rutas_evt, start=1):
        print(archivo_evt)
        datos = transformar_copiar_EVT(archivo_evt,
                                self.directorio_trabajo,
                                self.checkBox_verificacion.isChecked(),
                                self.checkBox_insercion.isChecked(),
                                self.directorio_destino)
        
        
        datos_completos.extend(datos)
        self.progressBar.setValue(contador)
        QtWidgets.QApplication.processEvents()

    self.progressBar.setValue(total_archivos)
    return datos_completos


class MyApp(QMainWindow):
    def __init__(self, parent=None):
        super(MyApp, self).__init__(parent)


        # Cargar la interfaz desde el archivo .ui directamente en esta instancia
        ruta_ui =  os.path.join(ruta_proyecto,"src", "ui", "Insertar_evt.ui")
        ruta_ui = os.path.abspath(ruta_ui)
        uic.loadUi(ruta_ui, self)

        self.setWindowTitle("LECTURA EVT")
        self.parametros = parametros_estaciones()
        self.directorio_trabajo = 'G:/Mi unidad/DIA/'
        self.progressBar.setValue(0)

        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.Btn_directorio_datos.clicked.connect(self.Cargar_directorio)
        self.Btn_iniciar.clicked.connect(self.Iniciar)
        self.Btn_salir.clicked.connect(self.salir)

    def Cargar_directorio(self, event):
        if self.radioDirectorio1.isChecked():
            self.directorio_estacion = QtWidgets.QFileDialog.getExistingDirectory(None, 'Seleccione Directorio EVT')
            aux_ = os.listdir(self.directorio_estacion)
            self.directorio_principal = sorted(aux_)
            self.cmbx_eventos.addItems(self.directorio_principal)
            # Limpiar y llenar el combobox de subdirectorios
            self.cmbx_subdirectorios.clear()
            self.cmbx_subdirectorios.addItem("Todos")  # Opción por defecto
            # Verifica que haya algo seleccionado
            if self.directorio_principal:
                primer_subdir = os.path.join(self.directorio_estacion, self.directorio_principal[0])
                if os.path.isdir(primer_subdir):
                        subdirectorios = [d for d in os.listdir(primer_subdir)
                                      if os.path.isdir(os.path.join(primer_subdir, d))]
                        self.cmbx_subdirectorios.addItems(sorted(subdirectorios))
        if self.radioLista.isChecked():
            self.ruta_csv, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Seleccionar archivo CSV", "", "CSV Files (*.csv)")
        if self.radioDirectorio2.isChecked():
            self.directorio_evt_completo = QtWidgets.QFileDialog.getExistingDirectory(None, 'Seleccione Directorio EVT (completo)')
            if self.directorio_evt_completo:
                # Recolectar todos los archivos .evt dentro de cualquier subdirectorio
                self.lista_evt_directorio_completo = []
                for raiz, _, archivos in os.walk(self.directorio_evt_completo):
                    for archivo in archivos:
                        if archivo.lower().endswith(".evt"):
                            self.lista_evt_directorio_completo.append(os.path.join(raiz, archivo))
                QMessageBox.information(self, "Archivos encontrados", f"Se encontraron {len(self.lista_evt_directorio_completo)} archivos EVT.")

            

    def Iniciar(self):
        if self.radio_estacion_serial.isChecked():
            self.directorio_destino = QtWidgets.QFileDialog.getExistingDirectory(self, 'Seleccionar directorio destino por serial')
            if not self.directorio_destino:
                QMessageBox.warning(self, "Advertencia", "No se seleccionó un directorio de destino para el serial. Se cancelará el proceso.")
                return
        else:
            self.directorio_destino = None  # Por si se usa en el procesamiento, pero no se necesita
        if self.radioDirectorio1.isChecked():
            directorio_anio = self.cmbx_eventos.currentText()
            subdirectorio_filtro = self.cmbx_subdirectorios.currentText()
            ruta_base = os.path.join(self.directorio_estacion, directorio_anio)
            self.estacion = Path(self.directorio_estacion).resolve()
            lista_evt = recolectar_evt(ruta_base)
            if subdirectorio_filtro != "Todos":
                lista_evt = [ruta for ruta in lista_evt if subdirectorio_filtro in Path(ruta).parts]
            total_archivos = len(lista_evt)
            self.progressBar.setMaximum(total_archivos)
            self.progressBar.setValue(0)
            datos =transformar_copiar_lista_EVT(self, lista_evt)
        if self.radioLista.isChecked():
            rutas_evt=lectura_archivo(self.ruta_csv)
            datos = transformar_copiar_lista_EVT(self, rutas_evt)
        if self.radioDirectorio2.isChecked():
            if hasattr(self, "lista_evt_directorio_completo"):
                lista_evt = self.lista_evt_directorio_completo
                datos = transformar_copiar_lista_EVT(self, lista_evt)
            else:
                QMessageBox.warning(self, "Error", "No se ha seleccionado ningún directorio.")
                return
        salida=os.path.join(self.directorio_trabajo, 'procesados_desde_csv.csv')
        escritura_archivo(salida, datos)
        QMessageBox.information(self, "Proceso finalizado", f"Archivo generado:\n{salida}")


    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Seleccionar carpeta de trabajo')
        if not folderpath.endswith('/'):
            folderpath += '/'
        self.directorio_trabajo = folderpath
        self.lbl_directorio_trabajo.setText("Directorio de trabajo:   "+self.directorio_trabajo)


    def salir(self):
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
