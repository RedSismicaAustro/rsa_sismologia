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
if not ruta_proyecto:
    raise RuntimeError('No se encontro la raiz del proyecto rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)

# ==== Librerías del proyecto / terceros ======================================
from rsa_io import lectura_archivo
from metodos_gestion import parametros_estaciones, obtener_directorios

import obspy
from obspy import Stream
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QDate, QCoreApplication
import matplotlib
matplotlib.use('Agg')


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
        self.tipo_canal = self.estaciones_['CANAL']

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

    def validar_fila_digital(self, fila, numero_fila):
        if len(fila) < 2:
            self.agregar_mensaje(f"ADVERTENCIA: digitales.csv fila {numero_fila} incompleta - omitida")
            return None

        nombre_carpeta = fila[0].strip()
        numero_estacion = fila[1].strip()
        if not nombre_carpeta:
            self.agregar_mensaje(f"ADVERTENCIA: digitales.csv fila {numero_fila} sin carpeta - omitida")
            return None

        try:
            num_estacion = int(numero_estacion)
        except ValueError:
            self.agregar_mensaje(
                f"ADVERTENCIA: digitales.csv fila {numero_fila} con numero invalido '{numero_estacion}' - omitida"
            )
            return None

        limites = (
            len(self.estacion_habilitada),
            len(self.nombre_estacion),
            len(self.codigo_estacion),
            len(self.canal_),
            len(self.tipo_canal),
        )
        if num_estacion < 0 or any(num_estacion >= limite for limite in limites):
            self.agregar_mensaje(
                f"ADVERTENCIA: digitales.csv fila {numero_fila} referencia estacion {num_estacion} fuera de rango - omitida"
            )
            return None

        return nombre_carpeta, num_estacion

    def filas_digitales_validas(self):
        filas_validas = []
        for numero_fila, fila in enumerate(self.est_digitales_[1:], start=2):
            datos_fila = self.validar_fila_digital(fila, numero_fila)
            if datos_fila is not None:
                filas_validas.append((numero_fila, fila, datos_fila[0], datos_fila[1]))
        return filas_validas

    def actualizar_progreso(self, estaciones_evaluadas, total_estaciones):
        if hasattr(self, 'progressBar') and total_estaciones > 0:
            self.progressBar.setValue(int((estaciones_evaluadas / total_estaciones) * 100))

    def registrar_huecos(self, stream, codigo_estacion, momento):
        huecos = stream.get_gaps()
        if not huecos:
            self.agregar_mensaje(f"  {codigo_estacion}: sin huecos detectados {momento}")
            return

        self.agregar_mensaje(f"  ADVERTENCIA: {codigo_estacion}: {len(huecos)} huecos/solapes detectados {momento}")
        for hueco in huecos[:5]:
            red, estacion, ubicacion, canal, inicio, fin, delta, muestras = hueco
            id_traza = ".".join(parte for parte in (red, estacion, ubicacion, canal) if parte)
            self.agregar_mensaje(
                f"    {id_traza}: {inicio} a {fin}, delta={delta:.4f}s, muestras={muestras}"
            )
        if len(huecos) > 5:
            self.agregar_mensaje(f"    ... {len(huecos) - 5} huecos/solapes adicionales")

    def seleccionar_traza_png(self, stream, num_estacion, codigo_estacion):
        canal_idx = int(self.canal_[num_estacion]) - 1
        if canal_idx < 0:
            canal_idx = 0

        stream_ordenado = stream.copy()
        stream_ordenado.sort(keys=['network', 'station', 'location', 'channel', 'starttime'])

        orientaciones = str(self.tipo_canal[num_estacion]).strip().upper()
        if canal_idx < len(orientaciones):
            componente = orientaciones[canal_idx]
            for traza in stream_ordenado:
                canal = str(traza.stats.channel).upper()
                if canal.endswith(componente):
                    self.agregar_mensaje(
                        f"  {codigo_estacion}: PNG usando canal {traza.id} por componente {componente}"
                    )
                    return traza
            self.agregar_mensaje(
                f"  ADVERTENCIA: {codigo_estacion}: no se encontro componente {componente}; se usa fallback por indice"
            )

        if len(stream_ordenado) > canal_idx:
            traza = stream_ordenado[canal_idx]
            self.agregar_mensaje(f"  {codigo_estacion}: PNG usando canal {traza.id} por indice {canal_idx + 1}")
            return traza

        return None

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
        self.agregar_mensaje(f"Procesando dia: {dia_yyyymmdd}")

        patron_mseed_dia = re.compile(r'^([A-Za-z0-9]{4})_(\d{8})_(\d{6}).*\.mseed$', re.IGNORECASE)

        estaciones_procesadas = 0
        estaciones_evaluadas = 0
        filas_validas = self.filas_digitales_validas()
        total_estaciones = len([
            fila for fila in filas_validas
            if self.estacion_habilitada[fila[3]] == '1'
        ])

        for numero_fila, estacion_digital, nombre_carpeta, num_estacion in filas_validas:
            if self.estacion_habilitada[num_estacion] != '1':
                self.agregar_mensaje(f"Estacion {self.nombre_estacion[num_estacion]} no habilitada - omitida")
                continue

            codigo_estacion = self.codigo_estacion[num_estacion]
            try:
                ruta_carpeta = os.path.join(self.directorio_binario, nombre_carpeta)
                if not os.path.isdir(ruta_carpeta):
                    self.agregar_mensaje(f"{codigo_estacion}: carpeta no existe: {ruta_carpeta}")
                    continue

                archivos_mseed = []
                archivos_otro_codigo = 0
                try:
                    for archivo in os.listdir(ruta_carpeta):
                        match = patron_mseed_dia.match(archivo)
                        if not match or match.group(2) != dia_yyyymmdd:
                            continue
                        codigo_archivo = match.group(1).upper()
                        if codigo_archivo != codigo_estacion.upper():
                            archivos_otro_codigo += 1
                            continue
                        archivos_mseed.append(os.path.join(ruta_carpeta, archivo))
                except Exception as e:
                    self.agregar_mensaje(f"{codigo_estacion}: error al listar {ruta_carpeta}: {e}")
                    continue

                if archivos_otro_codigo:
                    self.agregar_mensaje(
                        f"  ADVERTENCIA: {codigo_estacion}: {archivos_otro_codigo} archivos del dia ignorados por otro codigo"
                    )

                if not archivos_mseed:
                    self.agregar_mensaje(f"{codigo_estacion}: No hay MSEED para este dia")
                    continue

                self.agregar_mensaje(f"{codigo_estacion}: {len(archivos_mseed)} archivos encontrados")

                archivos_con_tiempo = []
                archivos_sin_tiempo = []
                for ruta in archivos_mseed:
                    try:
                        st = obspy.read(ruta, headonly=True)
                        t0 = min(tr.stats.starttime for tr in st)
                        archivos_con_tiempo.append((t0, ruta))
                    except Exception as e:
                        archivos_sin_tiempo.append(ruta)
                        self.agregar_mensaje(
                            f"  ADVERTENCIA: sin cabecera legible {os.path.basename(ruta)}: {e}"
                        )

                archivos_con_tiempo.sort(key=lambda x: x[0])
                rutas_ordenadas = [r for _, r in archivos_con_tiempo] + archivos_sin_tiempo

                stream_unido = Stream()
                for ruta in rutas_ordenadas:
                    try:
                        stream_unido += obspy.read(ruta)
                    except Exception as e:
                        self.agregar_mensaje(f"  Error al leer {os.path.basename(ruta)}: {e}")

                if len(stream_unido) == 0:
                    self.agregar_mensaje("  No se pudo leer ningun dato")
                    continue

                self.registrar_huecos(stream_unido, codigo_estacion, "antes de unir")
                stream_unido.merge(method=1, fill_value=None)
                stream_unido = stream_unido.split()
                self.registrar_huecos(stream_unido, codigo_estacion, "despues de unir")

                archivo_salida = os.path.join(self.directorio_registros, f"{codigo_estacion}_{archivo_evento}.mseed")
                try:
                    stream_unido.write(archivo_salida, format='MSEED', encoding='STEIM1', reclen=512)
                    self.agregar_mensaje(f"  Unido: {codigo_estacion}_{archivo_evento}.mseed")
                except Exception as e:
                    self.agregar_mensaje(f"  Error al guardar: {e}")
                    continue

                try:
                    traza_png = self.seleccionar_traza_png(stream_unido, num_estacion, codigo_estacion)
                    if traza_png is not None:
                        png_salida = os.path.join(self.directorio, f"{codigo_estacion}_{archivo_evento}.png")
                        traza_png.plot(
                            type='dayplot',
                            outfile=png_salida,
                            dpi=200,
                            size=(2400, 1800),
                            linewidth=0.2
                        )
                        self.agregar_mensaje(f"  PNG: {codigo_estacion}_{archivo_evento}.png")
                    else:
                        self.agregar_mensaje("  ADVERTENCIA: no existe un canal valido para generar PNG")
                except Exception as e:
                    self.agregar_mensaje(f"  ADVERTENCIA: Error al generar PNG: {e}")

                estaciones_procesadas += 1
            finally:
                estaciones_evaluadas += 1
                self.actualizar_progreso(estaciones_evaluadas, total_estaciones)
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
