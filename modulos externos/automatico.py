import sys
import os
import re
import csv
import shutil
import numpy as np
from pathlib import Path
from datetime import datetime
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QDate, QCoreApplication, Qt
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor

import obspy
from obspy import UTCDateTime, Trace, Stream
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()

# ==========================
# Configuración de rutas
# ==========================
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

# Importar todo lo necesario (incluyendo lectura_archivo y escritura_archivo)
from rsa_io import conversion_mseed, lectura_archivo, escritura_archivo
from rsa_utilidades import loc_cabecera
from metodos_gestion import parametros_estaciones, obtencion_hora, obtener_directorios

# ==========================
# Utilitarios UI
# ==========================
def mensaje_lbl(Lbl_Mensajes, mensaje, borrar=False):
    """Escribe en QTextEdit"""
    try:
        Lbl_Mensajes.setAlignment(Qt.AlignLeft)
        Lbl_Mensajes.setLineWrapMode(QTextEdit.WidgetWidth)
        texto_nuevo = "" if mensaje is None else str(mensaje)
        if borrar:
            Lbl_Mensajes.setPlainText(texto_nuevo)
        else:
            cursor = Lbl_Mensajes.textCursor()
            cursor.movePosition(QTextCursor.End)
            Lbl_Mensajes.setTextCursor(cursor)
            if Lbl_Mensajes.toPlainText():
                Lbl_Mensajes.insertPlainText("\n")
            Lbl_Mensajes.insertPlainText(texto_nuevo)
    except Exception:
        pass

def mostrar_advertencia(parent):
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle('Advertencia')
    texto = '<div style="text-align: center; font-size: 30px;">¡Registro Continuo no conectado!   ¡Verificar que esté en red!</div>'
    msg_box.setText(texto)
    msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
    msg_box.exec_()

# ==========================
# Lector binario (usa loc_cabecera, mantiene compatibilidad)
# ==========================
def leer_binario_completo(archivo_binario, archivo_estaciones, barra_progreso, Lbl_Mensajes):
    """
    Lee TODO el archivo binario desde el principio.
    USA loc_cabecera para obtener configuración y posición correcta.
    """
    # Constantes
    bytes_por_segundo = 2077
    n_canales = 16
    sps = 64
    marca_fija = b'\x08\x00\x05\x00'
    cabecera_1_esperada = b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00'
    bytes_cuerpo = 2048

    # Inicializar canales
    canal = [[] for _ in range(n_canales)]
    linea = [0] * n_canales
    
    # ===== USAR loc_cabecera (usa escritura_archivo internamente) =====
    with open(archivo_binario, 'rb') as f:
        numero_segundo, configuracion, puntero_cabecera = loc_cabecera(f)
        
        # Guardar configuración usando escritura_archivo si está disponible
        # o CSV directamente como fallback
        if not os.path.exists(archivo_estaciones) or os.path.getsize(archivo_estaciones) == 0:
            try:
                # Intentar usar escritura_archivo (formato que espera el sistema)
                escritura_archivo(archivo_estaciones, configuracion)
                mensaje_lbl(Lbl_Mensajes, f"Configuración guardada con escritura_archivo", False)
            except Exception as e:
                # Fallback: escribir CSV manualmente
                mensaje_lbl(Lbl_Mensajes, f"Fallback a CSV manual: {e}", False)
                with open(archivo_estaciones, 'w', newline='') as est_file:
                    writer = csv.writer(est_file, delimiter=';')
                    for fila in configuracion:
                        writer.writerow(fila)
    
    # Posición donde empiezan los datos (según loc_cabecera)
    pos_inicio = max(0, int(puntero_cabecera) - 5)
    
    tamano_archivo = os.path.getsize(archivo_binario)
    bytes_restantes = tamano_archivo - pos_inicio
    segundos_estimados = bytes_restantes // bytes_por_segundo
    
    mensaje_lbl(Lbl_Mensajes, f"Posición inicio: {pos_inicio}, Segundos estimados: {segundos_estimados}", True)
    
    if barra_progreso:
        barra_progreso.setRange(0, max(1, segundos_estimados))
        barra_progreso.setValue(0)
        QCoreApplication.processEvents()
    
    contador_segundos = 0
    primera_vez = True
    
    with open(archivo_binario, 'rb') as f:
        f.seek(pos_inicio)
        
        while True:
            pos_actual = f.tell()
            
            # Leer marca
            cab_0 = f.read(4)
            if len(cab_0) < 4:
                break
                
            if cab_0 != marca_fija:
                # Buscar siguiente marca
                f.seek(pos_actual + 1)
                continue
            
            # Leer número de segundo
            numero_segundo_b = f.read(5)
            if len(numero_segundo_b) < 5:
                break
            try:
                numero_segundo_b.decode('ascii')
            except:
                continue
            
            # Leer cabecera
            cab_1 = f.read(20)
            if cab_1 != cabecera_1_esperada:
                continue
            
            # Leer cuerpo de datos
            cuerpo = f.read(bytes_cuerpo)
            if len(cuerpo) < bytes_cuerpo:
                break
            
            # Procesar datos
            datos = np.frombuffer(cuerpo, dtype='<i2')
            try:
                datos = datos.reshape((sps, n_canales))
            except ValueError:
                break
            
            if primera_vez:
                # Primera lectura: calcular offset por canal
                offset = datos.mean(axis=0).astype(np.int32)
                datos = (datos.astype(np.int32) - offset).astype(np.int16)
                linea[:] = offset.tolist()
                primera_vez = False
            else:
                datos = (datos.astype(np.int32) - np.array(linea, dtype=np.int32)).astype(np.int16)
            
            # Agregar a canales
            for m in range(n_canales):
                canal[m].extend(datos[:, m].tolist())
            
            contador_segundos += 1
            
            if barra_progreso and contador_segundos % 100 == 0:
                barra_progreso.setValue(min(contador_segundos, segundos_estimados))
                QCoreApplication.processEvents()
    
    mensaje_lbl(Lbl_Mensajes, f"Lectura terminada. Segundos leídos: {contador_segundos}", True)
    
    return canal, 0

# ==========================
# Guardar MSEED explícitamente (usa obspy directamente)
# ==========================
def guardar_mseed_con_obspy(todos_los_canales, hab_canal, nombre_canal, fecha_ref, directorio_registros, Lbl_Mensajes):
    """
    Guarda archivos MSEED usando Obspy directamente.
    Alternativa a conversion_mseed por si falla.
    """
    trCanal = []
    
    for i in range(16):
        if str(hab_canal[i]) != "0" and len(todos_los_canales[i]) > 0:
            mensaje_lbl(Lbl_Mensajes, f"Guardando canal {nombre_canal[i]}...", False)
            
            # Crear trace de Obspy
            trace = Trace()
            trace.data = np.array(todos_los_canales[i], dtype=np.float32)
            trace.stats.sampling_rate = 64.0
            trace.stats.network = "XX"
            trace.stats.station = nombre_canal[i][:3] if len(nombre_canal[i]) >= 3 else nombre_canal[i]
            trace.stats.location = ""
            trace.stats.channel = nombre_canal[i]
            trace.stats.starttime = UTCDateTime(fecha_ref)
            
            # Nombre del archivo
            hora_str = fecha_ref.strftime('%y%m%d_%H%M%S')
            nombre_mseed = f"{nombre_canal[i]}_{hora_str}.mseed"
            ruta_mseed = os.path.join(directorio_registros, nombre_mseed)
            
            # Escritura atómica
            ruta_tmp = ruta_mseed + ".tmp"
            trace.write(ruta_tmp, format="MSEED", encoding="STEIM1", reclen=512)
            os.replace(ruta_tmp, ruta_mseed)
            
            mensaje_lbl(Lbl_Mensajes, f"  → {nombre_mseed} ({len(trace.data)} muestras)", False)
            trCanal.append(trace)
        else:
            trCanal.append([])
    
    return trCanal

# ==========================
# UI principal
# ==========================
ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'ui', "automatico.ui"))
Ui_MainWindow, QtBassClass = uic.loadUiType(ruta_ui)

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
    
    def __init__(self, parent=None):
        super(MyApp, self).__init__(parent)
        uic.loadUi(ruta_ui, self)
        self.setWindowTitle("PROCESAMIENTO SISMICO - SIMPLIFICADO")
        
        # Conectar botones
        self.btn_abrir.clicked.connect(self.procesar_dia)
        self.Btn_Salir.clicked.connect(self.Salir_)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.dateEdit.dateChanged.connect(self.showDate)
        
        # Cargar parámetros de estaciones
        self.parametros = parametros_estaciones()
        self.nombre_canal = self.parametros['CODIGO']
        self.hab_canal = self.parametros['HAB_CANAL']
        
        # Configurar fecha por defecto
        now = datetime.now()
        self.directorio_trabajo = 'G:/Mi unidad/DIA/'
        self.dateEdit.setDate(QDate(now.year, now.month, now.day))
        self.showDate(self.dateEdit.date())
        
        mensaje_lbl(self.Lbl_Mensajes, "AUTOMATICO SIMPLIFICADO - INICIADO", False)
        
        # Verificar unidad R:
        if not os.path.exists('R:'):
            mostrar_advertencia(self)
    
    def showDate(self, date):
        """Actualiza fecha seleccionada"""
        self.date = date
        self.dia = self.date.toString('yyyyMMdd')
        self.dia_aa = self.date.toString('yyMMdd')
    
    def seleccionar_drive(self):
        """Selecciona directorio de trabajo"""
        folderpath = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath:
            if folderpath[-1] != '/':
                folderpath = folderpath + '/'
            self.directorio_trabajo = folderpath
            mensaje_lbl(self.Lbl_Mensajes, f"Directorio: {self.directorio_trabajo}", True)
    
    def corregir_nombre_archivo(self, nombre_original):
        """Corrige 235959 → 000000 y formato"""
        solo_nombre = Path(nombre_original).name
        
        if solo_nombre.endswith('235959'):
            nombre_corregido = solo_nombre[:-6] + '000000'
            mensaje_lbl(self.Lbl_Mensajes, f"Renombrando: {solo_nombre} -> {nombre_corregido}", False)
            return nombre_corregido
        
        if re.match(r'^\d{12}$', solo_nombre):
            return solo_nombre
        
        if re.match(r'^\d{14}$', solo_nombre):
            return solo_nombre[2:]
        
        return solo_nombre
    
    def procesar_dia(self):
        """Procesa TODO el día desde cero"""
        
        mensaje_lbl(self.Lbl_Mensajes, f"\n=== INICIANDO PROCESAMIENTO DEL DÍA {self.dia} ===", False)
        
        # ===== 1. OBTENER ARCHIVOS DE UNIDAD R: =====
        archivos_origen = []
        try:
            for archivo in os.listdir('R:/'):
                if Path(archivo).suffix == '' and len(archivo) >= 6:
                    if archivo[:6] == self.dia_aa:
                        archivos_origen.append(archivo)
        except FileNotFoundError:
            mensaje_lbl(self.Lbl_Mensajes, "ERROR: No se puede acceder a R:/", True)
            return
        
        if not archivos_origen:
            mensaje_lbl(self.Lbl_Mensajes, f"No hay archivos para el día {self.dia}", True)
            return
        
        archivos_origen.sort()
        mensaje_lbl(self.Lbl_Mensajes, f"Archivos encontrados: {archivos_origen}", False)
        
        # ===== 2. COPIAR Y RENOMBRAR ARCHIVOS =====
        archivos_procesar = []
        for archivo in archivos_origen:
            nombre_corregido = self.corregir_nombre_archivo(archivo)
            origen = f'R:/{archivo}'
            destino = os.path.join(self.directorio_trabajo, nombre_corregido)
            
            mensaje_lbl(self.Lbl_Mensajes, f"Copiando: {origen} -> {destino}", False)
            shutil.copy2(origen, destino)
            archivos_procesar.append(destino)
        
        # ===== 3. PREPARAR DIRECTORIOS =====
        archivo_ref = archivos_procesar[0]
        self.definir_directorios(archivo_ref)
        
        # Limpiar directorio de registros
        if os.path.exists(self.directorio_registros):
            mensaje_lbl(self.Lbl_Mensajes, "Limpiando registros anteriores...", False)
            for arch in os.listdir(self.directorio_registros):
                if arch.endswith('.mseed'):
                    try:
                        os.remove(os.path.join(self.directorio_registros, arch))
                    except:
                        pass
        else:
            os.makedirs(self.directorio_registros, exist_ok=True)
        
        # Eliminar estaciones.csv antiguo para forzar regeneración
        if os.path.exists(self.estaciones):
            try:
                os.remove(self.estaciones)
            except:
                pass
        
        # ===== 4. PROCESAR CADA ARCHIVO BINARIO =====
        todos_los_canales = None
        
        for idx, archivo_bin in enumerate(archivos_procesar):
            mensaje_lbl(self.Lbl_Mensajes, f"\n--- Procesando archivo {idx+1}/{len(archivos_procesar)}: {Path(archivo_bin).name} ---", False)
            
            fecha = obtencion_hora(archivo_bin)
            self.fecha_ = fecha
            
            # Leer binario completo
            canal, _ = leer_binario_completo(
                archivo_bin,
                self.estaciones,
                self.progressBar,
                self.Lbl_Mensajes
            )
            
            # Convertir a numpy
            canal_np = np.asarray(canal)
            
            # Acumular canales
            if todos_los_canales is None:
                todos_los_canales = canal_np
            else:
                for i in range(16):
                    todos_los_canales[i] = np.concatenate([todos_los_canales[i], canal_np[i]])
            
            if len(todos_los_canales[0]) > 0:
                segundos_totales = len(todos_los_canales[0]) // 64
                mensaje_lbl(self.Lbl_Mensajes, f"Total acumulado: {segundos_totales} segundos", False)
        
        # ===== 5. CONVERTIR A MSEED =====
        if todos_los_canales is not None:
            mensaje_lbl(self.Lbl_Mensajes, "\n=== CONVIRTIENDO A MSEED ===", False)
            
            fecha_ref = obtencion_hora(archivos_procesar[0])
            
            # Intentar usar conversion_mseed primero
            try:
                self.trCanal = conversion_mseed(
                    todos_los_canales,
                    self.hab_canal,
                    self.nombre_canal,
                    fecha_ref,
                    self.directorio_registros
                )
                mensaje_lbl(self.Lbl_Mensajes, "Conversión con conversion_mseed exitosa", False)
            except Exception as e:
                mensaje_lbl(self.Lbl_Mensajes, f"conversion_mseed falló: {e}. Usando método directo...", False)
                # Fallback: método directo con Obspy
                self.trCanal = guardar_mseed_con_obspy(
                    todos_los_canales,
                    self.hab_canal,
                    self.nombre_canal,
                    fecha_ref,
                    self.directorio_registros,
                    self.Lbl_Mensajes
                )
        
        # ===== 6. GENERAR PNGs =====
        self.generar_pngs()
        
        mensaje_lbl(self.Lbl_Mensajes, "\n=== PROCESAMIENTO COMPLETADO ===", True)
    
    def definir_directorios(self, archivo):
        """Define rutas necesarias"""
        directorios = obtener_directorios(archivo)
        self.directorio = directorios['Directorio_base']
        self.directorio_dia = directorios['Directorio_dia']
        self.directorio_eventos = directorios['Directorio_eventos']
        self.directorio_registros = directorios['Directorio_registros']
        self.directorio_reportes = directorios['Directorio_reportes']
        self.directorio_acel = directorios['Directorio_acelerogramas']
        self.estaciones = directorios['archivo_estaciones']
        
        # Crear directorios necesarios
        for ruta in [self.directorio, self.directorio_dia, self.directorio_registros,
                     self.directorio_reportes, self.directorio_acel]:
            try:
                Path(ruta).mkdir(parents=True, exist_ok=True)
            except:
                pass
    
    def generar_pngs(self):
        """Genera dayplots en PNG"""
        if not hasattr(self, 'trCanal') or not self.trCanal:
            mensaje_lbl(self.Lbl_Mensajes, "No hay datos para generar PNGs", False)
            return
        
        hora_string = self.fecha_.strftime('%Y%m%d_%H%M%S')
        mensaje_lbl(self.Lbl_Mensajes, "Generando PNGs...", True)
        
        for i in range(16):
            if str(self.hab_canal[i]) == '1' and i < len(self.trCanal):
                if self.trCanal[i] and len(self.trCanal[i]) > 0:
                    nombrepng = f"{self.nombre_canal[i]}_{hora_string}.png"
                    nombrepng = os.path.join(self.directorio, nombrepng)
                    try:
                        self.trCanal[i].plot(type='dayplot', outfile=nombrepng, 
                                           dpi=200, size=(2400,1800), 
                                           linewidth=0.2, show=False)
                        mensaje_lbl(self.Lbl_Mensajes, f"PNG generado: {Path(nombrepng).name}", False)
                    except Exception as e:
                        mensaje_lbl(self.Lbl_Mensajes, f"Error en PNG {self.nombre_canal[i]}: {e}", False)
        
        plt.close('all')
        mensaje_lbl(self.Lbl_Mensajes, "PNGs completados", False)
    
    def Salir_(self):
        self.close()

# ==========================
# Main
# ==========================
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    app.exec_()