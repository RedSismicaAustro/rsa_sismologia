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
    """
    Ajusta el starttime de cada traza del Stream para calzar con el evento más cercano
    dentro de una tolerancia dada. Devuelve el stream ajustado, una bandera de si hubo
    calce, el tipo de evento ('FF', 'FC', 'SISMO') y el nombre sugerido del .mseed.

    Notas:
    - Se espera que eventos sea una lista de filas donde evento[1] contiene
      'YYYYMMDD_HHMMSS.sis' o al menos 'YYYYMMDD_HHMMSS'.
    - Se robusteció el parseo para aceptar tanto 15 caracteres como con extensión.
    """
    tr = stream[0]
    estacion = obtener_estacion(str(tr.stats.station).strip().upper())
    inicio = tr.stats.starttime

    tiempo_stream = inicio.datetime
    archivo_mseed = f"{estacion}_{inicio.strftime('%Y%m%d_%H%M%S')}.mseed"
    tolerancia_segundos = int(tolerancia_minutos) * 60

    mejor_evento = None
    mejor_diferencia = float('inf')
    mejor_tipo = None

    for evento in eventos:
        # Validación mínima de longitud de fila
        if not evento or len(evento) < 3:
            continue

        tipo = str(evento[2]).strip().upper()
        if tipo not in ("FF", "FC", "SISMO"):
            continue

        # Aceptar varias formas en evento[1]: con o sin extensión
        crudo = str(evento[1]).strip()
        if "_" not in crudo:
            continue

        # Extrae exactamente 'YYYYMMDD_HHMMSS' (15 chars) desde el inicio
        ts_txt = crudo[:15]
        try:
            tiempo_evento = datetime.strptime(ts_txt, "%Y%m%d_%H%M%S")
        except Exception:
            # Intento alterno: dividir por '_' por si hay ruido
            try:
                fecha, hora = ts_txt.split("_")
                if len(fecha) == 8 and len(hora) == 6:
                    tiempo_evento = datetime.strptime(f"{fecha}_{hora}", "%Y%m%d_%H%M%S")
                else:
                    continue
            except Exception:
                continue

        diferencia = abs((tiempo_stream - tiempo_evento).total_seconds())
        if diferencia <= tolerancia_segundos and diferencia < mejor_diferencia:
            mejor_evento = tiempo_evento
            mejor_diferencia = diferencia
            mejor_tipo = tipo

    if mejor_evento is not None:
        diferencia_tiempo = mejor_evento - tiempo_stream
        bandera = True
    else:
        diferencia_tiempo = timedelta(seconds=0)
        bandera = False

    # Ajusta todo el stream con el mismo delta
    for traza in stream:
        traza.stats.starttime += diferencia_tiempo

    return stream, bandera, mejor_tipo, archivo_mseed



def insertar_evento(directorio_grabar: str, eventos: list, st: Stream, serial_equipo: str = None) -> list:
    """
    Inserta un evento en la lista de eventos, guardando el archivo MiniSEED
    y marcando en 'eventos' la columna correspondiente a la estación.
    Supone que 'eventos' tiene un encabezado en la fila 0 y que la segunda
    columna (índice 1) es el nombre base de evento 'YYYYMMDD_HHMMSS.sis'.
    """
    # Extrae desde el stream
    tr = st[0]
    estacion = obtener_estacion(str(tr.stats.station).strip().upper())
    inicio = tr.stats.starttime

    # Nombre de salida .mseed; si hay serial, anteponerlo y crear subcarpeta
    prefijo = str(serial_equipo) if serial_equipo else estacion
    nombre_archivo = f"{prefijo}_{inicio.strftime('%Y%m%d_%H%M%S')}.mseed"

    destino = directorio_grabar
    if serial_equipo:
        destino = os.path.join(directorio_grabar, str(serial_equipo))
    os.makedirs(destino, exist_ok=True)

    ruta_completa = os.path.join(destino, nombre_archivo)

    # Carga parámetros de estación
    parametros = parametros_estaciones()
    estaciones = [str(x).strip().upper() for x in parametros['CODIGO']]
    componentes = parametros['COMPONENTE']
    try:
        idx_est = estaciones.index(estacion)
    except ValueError:
        print(f"[ADVERTENCIA] Estación '{estacion}' no está en la configuración.")
        return eventos

    # Homologar: el CSV guarda 'YYYYMMDD_HHMMSS.sis'
    archivo_evento = f"{inicio.strftime('%Y%m%d_%H%M%S')}.sis"
    segundos_elementos = [str(f[1]).strip() for f in eventos]  # asumiendo fila 0 = encabezado
    # Busca desde fila 1 si la fila 0 es encabezado
    try:
        n_evento = segundos_elementos.index(archivo_evento)
    except ValueError:
        # Si la fila 0 es encabezado, intenta desde 1
        try:
            n_evento = segundos_elementos[1:].index(archivo_evento) + 1
        except ValueError:
            # No encontrado: salir limpio
            return eventos

    # Asegurar calib presente
    for tr in st:
        if not hasattr(tr.stats, "calib"):
            tr.stats.calib = 1.0

    # Escribir MSEED (parámetros por defecto)
    st.write(ruta_completa, format='MSEED')

    # Actualizar eventos de forma segura:
    # Si tu estructura es [ID, FECHA, ..., columnas por estación], mantener 'indice + 3'
    # pero validando rangos.
    col_destino = idx_est + 3
    if col_destino < len(eventos[n_evento]):
        eventos[n_evento][col_destino] = estacion + componentes[idx_est] + '1000000'
    else:
        # Expandir fila si hiciera falta
        faltan = col_destino - len(eventos[n_evento]) + 1
        eventos[n_evento].extend([''] * faltan)
        eventos[n_evento][col_destino] = estacion + componentes[idx_est] + '1000000'

    return eventos



def transformar_copiar_EVT(archivo_evt, directorio_trabajo, bandera_verificar, bandera_insertar, directorio_destino=None, ventana_parent=None):
    """
    Lee un archivo EVT (Kinemetrics), trata de calzarlo en el catálogo del día para ajustar tiempos,
    clasifica el evento y, si corresponde, inserta el .mseed y actualiza el CSV.

    Parámetros:
        archivo_evt (str): Ruta del archivo .EVT a procesar.
        directorio_trabajo (str): Carpeta base C:/DIA/ (o similar) donde se arma 'archivo' AAAAMMDDhhmmss.
        bandera_verificar (bool): Si True, genera gráfico; se guarda PNG y se abre en visor del sistema.
        bandera_insertar (bool): Si True y el evento calza, inserta el .mseed y actualiza el CSV del día.
        directorio_destino (str|None): Si se quiere forzar un destino por serial (crea subcarpetas por serial).
        ventana_parent (QMainWindow|None): Si se pasa, se mantiene la ventana Matplotlib no modal viva
                                           guardando la referencia en ventana_parent._figs_abiertas.

    Retorna:
        list[list]: Una lista con una sola fila de resumen del procesamiento del EVT.
    """
    import os, re, gc
    from datetime import datetime
    import matplotlib.pyplot as plt
    from pathlib import Path

    # Imports locales para abrir PNG sin bloquear la app
    from PyQt5.QtCore import QUrl
    from PyQt5.QtGui import QDesktopServices
    from PyQt5.QtWidgets import QMessageBox

    datos_completos = []

    # Reconstrucción descriptiva de la ruta por si no cae en diccionario
    # (no cambiamos tu lógica, solo la hacemos más clara/robusta)
    directorios_almacenamiento = re.split(r"[\\/]", archivo_evt)
    from collections import deque
    partes_ruta_mapeadas = deque()
    for d in directorios_almacenamiento:
        if not d:
            continue
        partes_ruta_mapeadas.append(dic_estaciones_dir.get(d, d))
    directorio_estacion_almacenado = " / ".join(partes_ruta_mapeadas) if partes_ruta_mapeadas else "Sin ruta"

    # Variables de salida
    mensaje = ''
    mensaje_1 = ''
    resultado_str = ''
    archivo_mseed = ''
    archivo = ''
    estacion = 'Ninguna'
    equipo_modelo, equipo_version, equipo_serial = 'Desconocido', 'Desconocida', 'Desconocido'

    # Intento de lectura EVT
    st = None
    try:
        st = read(archivo_evt, format='KINEMETRICS_EVT')
        evt_info = st[0].stats.kinemetrics_evt
    except Exception:
        archivo_mseed = "No es compatible al formato"
        # Usar ruta cruda en Windows para evitar escapes inválidos
        try:
            ejecutar_en_vm(archivo_evt, r'O:\KINEMETRICS')
        except Exception as e:
            print(f"[AVISO] ejecutar_en_vm falló: {e}")
        mensaje = "Error: archivo no legible como EVT"
        mensaje_1 = "No insertado"
        datos_grabar = [archivo_evt, archivo_mseed, mensaje, "", mensaje_1,
                        "", directorio_estacion_almacenado, "Desconocido",
                        "Desconocido", "Desconocida", "Desconocido"]
        datos_completos.append(datos_grabar)
        return datos_completos

    try:
        # === Construcción de 'archivo' AAAAMMDDhhmmss con el directorio de trabajo ===
        t = st[0].stats.starttime
        archivo = os.path.join(
            directorio_trabajo,
            f"{t.year:04d}{t.month:02d}{t.day:02d}{t.hour:02d}{t.minute:02d}{t.second:02d}"
        )
        directorios = obtener_directorios(archivo)

        # === Extraer info del equipo de forma robusta ===
        try:
            equipo_modelo  = str(evt_info.get('comment', 'Desconocido'))
            equipo_version = str(evt_info.get('instrument', 'Desconocida'))
            equipo_serial  = str(evt_info.get('serialnumber', 'Desconocido'))
        except Exception:
            pass

        # Normaliza código de estación
        estacion = obtener_estacion(str(st[0].stats.station).strip().upper())

        # Si se pide destino por serial, renombra y dirige a esa carpeta
        serial_para_nombre = str(equipo_serial) if directorio_destino else None
        directorio_final = directorio_destino if directorio_destino else directorios.get('Directorio_eventos', directorios.get('directorio_eventos', directorio_trabajo))

        # Localiza CSV del día con tolerancia de may/min
        ruta_csv = directorios.get('Archivo_csv') or directorios.get('archivo_csv')
        if ruta_csv and os.path.exists(ruta_csv):
            eventos = lectura_archivo(ruta_csv)

            # === Ajuste de tiempos contra el catálogo (tolerancia 5 min) ===
            st, bandera_localizacion, tipo, archivo_mseed_nominal = ajustar_tiempos_stream_por_evento(
                eventos, st, tolerancia_minutos=5
            )

            # Arma ruta prevista del .mseed
            if serial_para_nombre:
                archivo_mseed = os.path.join(directorio_final, serial_para_nombre, serial_para_nombre + archivo_mseed_nominal[4:])
            else:
                archivo_mseed = os.path.join(directorio_final, archivo_mseed_nominal)

            # === Clasificación (sobre copia para no tocar st principal) ===
            st_copia = st.copy()
            resultado = clasificar_evento_sismico(st_copia)
            resultado_str = ' / '.join([f"{k}: {v}" for k, v in resultado.items()])

            mensaje = "Evento encontrado: " + (tipo if bandera_localizacion else "No encontrado")

            # === Verificación: guardar PNG y abrir visor del sistema (no bloquea) ===
            if bandera_verificar:
                try:
                    plt.close('all')
                    fig, axs = plt.subplots(len(st), 1, figsize=(10, 6), sharex=True)
                    if len(st) == 1:
                        axs = [axs]
                    for ax, tr in zip(axs, st):
                        tiempo = tr.times("matplotlib")
                        ax.plot(tiempo, tr.data, label=tr.id)
                        ax.legend(loc='upper right')
                    axs[-1].set_xlabel("Tiempo")
                    nombre_evt = os.path.basename(archivo_evt)
                    titulo_grafico = (
                        f"Verificación del Evento\n"
                        f"EVT: {nombre_evt}  |  Evento: {os.path.basename(archivo)}  |  Resultado: {mensaje}"
                    )
                    plt.suptitle(titulo_grafico)

                    # Mostrar la ventana Matplotlib en modo no modal y mantener referencia viva
                    try:
                        fig.show()
                        plt.pause(0.001)  # cede control al loop de eventos

                        if ventana_parent is not None:
                            if not hasattr(ventana_parent, "_figs_abiertas"):
                                ventana_parent._figs_abiertas = []
                            ventana_parent._figs_abiertas.append(fig)
                            # Limita cuántas figuras mantener (opcional)
                            if len(ventana_parent._figs_abiertas) > 5:
                                fig_vieja = ventana_parent._figs_abiertas.pop(0)
                                try:
                                    plt.close(fig_vieja)
                                except Exception:
                                    pass
                        # Si no quieres mantener la ventana Matplotlib, descomenta:
                        # plt.close(fig)
                    except Exception as e:
                        print(f"[AVISO] Mostrar figura no modal falló: {e}")

                    # Pregunta por inserción si hay localización
                    if bandera_localizacion:
                        respuesta = QMessageBox.question(
                            None, "Insertar evento",
                            "Se guardó una imagen de verificación.\n¿Deseas insertar este evento en la estructura de datos?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        if respuesta == QMessageBox.No:
                            mensaje_1 = 'No insertado'
                            bandera_localizacion = False
                    else:
                        QMessageBox.information(None, "AVISO", f"EVT: {nombre_evt}  {mensaje}")
                except Exception as e:
                    print(f"[AVISO] Verificación falló: {e}")

            # === Inserción en catálogo / escritura CSV ===
            if bandera_insertar and bandera_localizacion:
                try:
                    eventos = insertar_evento(directorio_final, eventos, st, serial_para_nombre)
                    escritura_archivo(ruta_csv, eventos)
                    mensaje_1 = 'Insertado'
                except Exception as e:
                    mensaje_1 = f"No insertado: {e}"
        else:
            archivo_mseed = f"No encontrado csv del dia: {ruta_csv}"
            mensaje = "Sin CSV, no se puede localizar/insertar"
    finally:
        # Limpieza de memoria del Stream
        try:
            if st is not None:
                st.clear()
                del st
        except Exception:
            pass
        gc.collect()

    # Fila de salida
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
                                       self.directorio_destino,
                                       self  # <-- importante para que no “desaparezcan” las figuras
                                       )

        
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
