# -*- coding: utf-8 -*-
"""
PROCESAMIENTO SISMICO – Unión TOTAL de MSEED por día
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime


# ==== Rutas base del proyecto =================================================
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + os.sep
    else:
        return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)

# ==== Librerías del proyecto / terceros ======================================
from rsa_io import lectura_archivo
from rsa_dominio import obtenerTraza
from metodos_gestion import parametros_estaciones, obtener_directorios

import numpy as np
import obspy
from obspy import Stream
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QDate, QCoreApplication
import matplotlib
matplotlib.use('Agg')


# =============================================================================
# Utilitarios para conversión de binario digital a MSEED
# =============================================================================

def nombre_mseed(nombre_prefijo: str, fecha_):
    anio_s, mes_s, dia_s, hora_s, minuto_s, segundo_s = fecha_[1]
    return f"{nombre_prefijo}{anio_s}{mes_s}{dia_s}_{hora_s}{minuto_s}{segundo_s}.mseed"

def conversion_mseed_digital(self, fileName: str, fecha_, data_np):
    anio, mes, dia, horas, minutos, segundos, _ = fecha_[0]
    nombre_estacion = self.datos_estacion[2]

    trazaCH1 = obtenerTraza(nombre_estacion, 1, data_np[0], (2000 + anio), mes, dia, horas, minutos, segundos, 0)
    trazaCH2 = obtenerTraza(nombre_estacion, 2, data_np[1], (2000 + anio), mes, dia, horas, minutos, segundos, 0)
    trazaCH3 = obtenerTraza(nombre_estacion, 3, data_np[2], (2000 + anio), mes, dia, horas, minutos, segundos, 0)

    stData = Stream(traces=[trazaCH1, trazaCH2, trazaCH3])
    stData.write(fileName, format='MSEED', encoding='STEIM1', reclen=512)

def verificacion_archivo(self, archivo_bin: str):
    with open(archivo_bin, "rb") as f:
        tramaDatos = np.fromfile(f, np.int8, 2506)

    hora = int(tramaDatos[2503]); minuto = int(tramaDatos[2504]); segundo = int(tramaDatos[2505])
    n_segundo = hora * 3600 + minuto * 60 + segundo
    anio = int(tramaDatos[2500]); mes = int(tramaDatos[2501]); dia = int(tramaDatos[2502])

    anio_s = f"{anio:02d}"; mes_s = f"{mes:02d}"; dia_s = f"{dia:02d}"
    hora_s = f"{hora:02d}"; minuto_s = f"{minuto:02d}"; segundo_s = f"{segundo:02d}"

    return ((anio, mes, dia, hora, minuto, segundo, n_segundo),
            (anio_s, mes_s, dia_s, hora_s, minuto_s, segundo_s))

def lectura_archivo_digital(self, archivo_bin: str):
    datos = [[], [], []]
    bandera = 1
    contador = 0
    avance = 0

    with open(archivo_bin, "rb") as f:
        while bandera:
            trama = np.fromfile(f, np.int8, 2506)
            contador += 1
            if len(trama) != 2506:
                bandera = 0
                break

            if contador == 864:
                contador = 0
                avance += 1
                self.agregar_mensaje(f'Avance {avance} %')
                if hasattr(self, 'progressBar'):
                    self.progressBar.setValue(avance)
                QCoreApplication.processEvents()

            for j in range(0, 3):
                for i in range(0, 250):
                    d1 = int(trama[i * 10 + j * 3 + 1]) & 0xFF
                    d2 = int(trama[i * 10 + j * 3 + 2]) & 0xFF
                    d3 = int(trama[i * 10 + j * 3 + 3]) & 0xFF
                    x = ((d1 << 12) & 0xFF000) | ((d2 << 4) & 0xFF0) | ((d3 >> 4) & 0xF)
                    if x >= 0x80000:
                        x = x & 0x7FFFF
                        x = -1 * (((~x) + 1) & 0x7FFFF)
                    datos[j].append(int(x))

    return np.asarray(datos)


# =============================================================================
# Interfaz PyQt – aplicación principal
# =============================================================================

ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, "src", "ui", "acelerografos.ui"))
Ui_MainWindow, QtBassClass = uic.loadUiType(ruta_ui)

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PROCESAMIENTO SISMICO")
        self.setupUi(self)

        # ==== CONEXIONES DE BOTONES ====
        self.Btn_Iniciar.clicked.connect(self.Iniciar)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.Btn_Salir.clicked.connect(self.salir)

        # ==== CONFIGURAR AREA DE TEXTO ====
        self.area_texto.clear()
        self.area_texto.setReadOnly(True)

        # ==== FECHA ====
        d = QDate.currentDate()
        self.dateEdit.setDate(d)
        self.dateEdit.dateChanged.connect(self.showDate)

        # ==== DIRECTORIOS POR DEFECTO ====
        self.directorio_trabajo = f"G:{os.sep}Mi unidad{os.sep}DIA{os.sep}"
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
        self.Lbl_directorio_2.setText(self.directorio_binario)

        # ==== INICIALIZAR ====
        self.showDate(d)
        self.definir_dia()

        # ==== PARÁMETROS DE ESTACIONES ====
        archivo_digitales = os.path.join(ruta_proyecto, 'datos', "digitales.csv")
        self.est_digitales_ = lectura_archivo(archivo_digitales)
        self.estaciones_ = parametros_estaciones()

        self.estacion_habilitada = self.estaciones_['HAB_CANAL']
        self.nombre_estacion = self.estaciones_['NOMBRE']
        self.codigo_estacion = self.estaciones_['CODIGO']
        self.ganancia = list(map(float, self.estaciones_['GANANCIA']))
        self.diezmado = list(map(int, self.estaciones_['DIEZMADO_PLT']))
        self.factor_mult = list(map(float, self.estaciones_['FACTOR_MUL']))
        self.canal_ = list(map(int, self.estaciones_['COMPONENTE']))

        self.agregar_mensaje("=== PROCESAMIENTO SISMICO INICIADO ===")
        self.agregar_mensaje(f"Fecha actual: {d.toString('dd/MM/yyyy')}")

    # ==================== MANEJO DE MENSAJES ====================
    
    def agregar_mensaje(self, texto):
        """Agrega un mensaje al área de texto (area_texto) y a consola"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        mensaje = f"[{timestamp}] {texto}"
        
        print(mensaje)
        self.area_texto.append(mensaje)
        
        cursor = self.area_texto.textCursor()
        cursor.movePosition(cursor.End)
        self.area_texto.setTextCursor(cursor)
        
        QCoreApplication.processEvents()
    
    def limpiar_mensajes(self):
        self.area_texto.clear()
    
    # ==================== BOTÓN SALIR (CIERRE FORZADO PARA WINDOWS) ====================
    
    def salir(self):
        """Cierra la aplicación forzosamente (solución para Windows)"""
        self.agregar_mensaje("Cerrando aplicación...")
        self.close()
        QCoreApplication.processEvents()
        os._exit(0)  # Terminación inmediata del proceso
    
    # ==================== UI HELPERS ====================

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Seleccionar carpeta base DIA')
        if not folderpath:
            return
        if not folderpath.endswith(os.sep):
            folderpath += os.sep

        self.directorio_trabajo = folderpath
        self.Lbl_directorio.setText(self.directorio_trabajo)

        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
        if not os.path.exists(self.directorio_binario):
            folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'SELECCIONAR DIRECTORIO "Datos Estaciones"')
            if not folderpath:
                return
            if not folderpath.endswith(os.sep):
                folderpath += os.sep
            self.directorio_binario = folderpath

        self.Lbl_directorio_2.setText(self.directorio_binario)
        self.agregar_mensaje(f"Directorio de trabajo: {self.directorio_trabajo}")
        self.agregar_mensaje(f"Directorio de estaciones: {self.directorio_binario}")

    def showDate(self, date: QDate):
        self.date = date
        self.archivo = os.path.join(self.directorio_trabajo, date.toString('yyyyMMdd') + '000000')
        self.agregar_mensaje(f"Fecha seleccionada: {date.toString('dd/MM/yyyy')}")

    # ==================== LÓGICA PRINCIPAL ====================

    def Iniciar(self):
        self.agregar_mensaje("")
        self.agregar_mensaje("=== INICIANDO PROCESAMIENTO ===")
        self.definir_dia()
        
        if hasattr(self, 'progressBar'):
            self.progressBar.setValue(0)

        try:
            os.listdir(self.directorio_binario)
        except FileNotFoundError:
            QMessageBox.information(self, "Advertencia", f"No existe el directorio: {self.directorio_binario}")
            self.agregar_mensaje(f"ERROR: No existe {self.directorio_binario}")
            return

        dia_yyyymmdd = self.date.toString('yyyyMMdd')
        archivo_evento = dia_yyyymmdd + "_000000"
        self.agregar_mensaje(f"Procesando día: {dia_yyyymmdd}")

        patron_mseed_dia = re.compile(r'^([A-Za-z0-9]{4})_(\d{8})_(\d{6}).*\.mseed$', re.IGNORECASE)

        estaciones_procesadas = 0
        total_estaciones = len([e for e in self.est_digitales_[1:] if self.estacion_habilitada[int(e[1])] == '1'])
        
        for idx, estacion_digital in enumerate(self.est_digitales_[1:]):
            num_estacion = int(estacion_digital[1])
            
            if hasattr(self, 'progressBar') and total_estaciones > 0:
                self.progressBar.setValue(int((idx / total_estaciones) * 100))
            
            if self.estacion_habilitada[num_estacion] != '1':
                self.agregar_mensaje(f"Estación {self.nombre_estacion[num_estacion]} no habilitada - omitida")
                continue
            
            nombre_carpeta = estacion_digital[0]
            codigo_estacion = self.codigo_estacion[num_estacion]
            
            ruta_carpeta = os.path.join(self.directorio_binario, nombre_carpeta)
            if not os.path.isdir(ruta_carpeta):
                self.agregar_mensaje(f"Carpeta no existe: {ruta_carpeta}")
                continue
            
            archivos_mseed = []
            try:
                for archivo in os.listdir(ruta_carpeta):
                    match = patron_mseed_dia.match(archivo)
                    if match and match.group(2) == dia_yyyymmdd:
                        archivos_mseed.append(os.path.join(ruta_carpeta, archivo))
            except Exception as e:
                self.agregar_mensaje(f"Error al listar {ruta_carpeta}: {e}")
                continue
            
            if not archivos_mseed:
                self.agregar_mensaje(f"{codigo_estacion}: No hay MSEED para este día")
                continue
            
            self.agregar_mensaje(f"{codigo_estacion}: {len(archivos_mseed)} archivos encontrados")
            
            archivos_con_tiempo = []
            archivos_sin_tiempo = []
            for ruta in archivos_mseed:
                try:
                    st = obspy.read(ruta, headonly=True)
                    t0 = min(tr.stats.starttime for tr in st)
                    archivos_con_tiempo.append((t0, ruta))
                except Exception:
                    archivos_sin_tiempo.append(ruta)
            
            archivos_con_tiempo.sort(key=lambda x: x[0])
            rutas_ordenadas = [r for _, r in archivos_con_tiempo] + archivos_sin_tiempo
            
            stream_unido = Stream()
            for ruta in rutas_ordenadas:
                try:
                    stream_unido += obspy.read(ruta)
                except Exception as e:
                    self.agregar_mensaje(f"  Error al leer {os.path.basename(ruta)}: {e}")
            
            if len(stream_unido) == 0:
                self.agregar_mensaje(f"  No se pudo leer ningún dato")
                continue
            
            stream_unido.merge(method=1, fill_value='latest')
            
            archivo_salida = os.path.join(self.directorio_registros, f"{codigo_estacion}_{archivo_evento}.mseed")
            try:
                stream_unido.write(archivo_salida, format='MSEED', encoding='STEIM1', reclen=512)
                self.agregar_mensaje(f"  ✓ Unido: {codigo_estacion}_{archivo_evento}.mseed")
            except Exception as e:
                self.agregar_mensaje(f"  Error al guardar: {e}")
                continue
            
            try:
                canal_idx = 0
                if num_estacion < len(self.canal_):
                    canal_idx = int(self.canal_[num_estacion]) - 1
                    if canal_idx < 0:
                        canal_idx = 0
                
                if len(stream_unido) > canal_idx:
                    png_salida = os.path.join(self.directorio, f"{codigo_estacion}_{archivo_evento}.png")
                    stream_unido[canal_idx].plot(
                        type='dayplot',
                        outfile=png_salida,
                        dpi=200,
                        size=(2400, 1800),
                        linewidth=0.2
                    )
                    self.agregar_mensaje(f"  ✓ PNG: {codigo_estacion}_{archivo_evento}.png")
                else:
                    self.agregar_mensaje(f"  ⚠ Canal {canal_idx+1} no existe en el stream")
            except Exception as e:
                self.agregar_mensaje(f"  ⚠ Error al generar PNG: {e}")
            
            estaciones_procesadas += 1
            QCoreApplication.processEvents()
        
        if hasattr(self, 'progressBar'):
            self.progressBar.setValue(100)
        
        self.agregar_mensaje(f"=== PROCESAMIENTO COMPLETADO: {estaciones_procesadas} estaciones ===")
        self.agregar_mensaje("")

    def definir_dia(self):
        self.directorios_ = obtener_directorios(self.archivo)
        self.directorio = self.directorios_['Directorio_base']
        self.directorio_dia = self.directorios_['Directorio_dia']
        self.directorio_registros = self.directorios_['Directorio_registros']

        for ruta in (self.directorio, self.directorio_dia, self.directorio_registros):
            try:
                Path(ruta).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.agregar_mensaje(f"No se pudo crear {ruta}: {e}")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())