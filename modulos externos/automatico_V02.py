# -*- coding: utf-8 -*-
"""
PROCESAMIENTO SISMICO UNIFICADO
1. Convierte binarios desde R: a MSEED
2. Une todos los MSEEDs por día
3. Genera PNGs y reportes
"""

import os
import sys
import re
import csv
import shutil
from pathlib import Path
from datetime import datetime

# ==== Configuración de rutas =================================================
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + os.sep
    return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

# ==== Librerías ==============================================================
from rsa_io import lectura_archivo, conversion_mseed, escritura_archivo
from rsa_utilidades import loc_cabecera
from metodos_gestion import parametros_estaciones, obtencion_hora, obtener_directorios

import numpy as np
import obspy
from obspy import Stream
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5.QtCore import QDate, QCoreApplication, Qt
from PyQt5.QtGui import QTextCursor

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()


# =============================================================================
# UTILITARIOS COMUNES
# =============================================================================

def agregar_mensaje(widget_texto, texto, borrar=False):
    """Agrega mensaje a QTextEdit y consola"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    mensaje = f"[{timestamp}] {texto}"
    print(mensaje)
    
    try:
        if borrar:
            widget_texto.setPlainText(mensaje)
        else:
            cursor = widget_texto.textCursor()
            cursor.movePosition(QTextCursor.End)
            widget_texto.setTextCursor(cursor)
            if widget_texto.toPlainText():
                widget_texto.insertPlainText("\n")
            widget_texto.insertPlainText(mensaje)
    except Exception:
        pass
    
    QCoreApplication.processEvents()


# =============================================================================
# PASO 1: LECTOR DE BINARIOS (desde R:)
# =============================================================================

def leer_binario_completo(archivo_binario, archivo_estaciones, barra_progreso, widget_texto):
    """Lee archivo binario desde el principio usando loc_cabecera"""
    bytes_por_segundo = 2077
    n_canales = 16
    sps = 64
    marca_fija = b'\x08\x00\x05\x00'
    cabecera_1_esperada = b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00'
    bytes_cuerpo = 2048

    canal = [[] for _ in range(n_canales)]
    linea = [0] * n_canales
    
    with open(archivo_binario, 'rb') as f:
        numero_segundo, configuracion, puntero_cabecera = loc_cabecera(f)
        
        if not os.path.exists(archivo_estaciones) or os.path.getsize(archivo_estaciones) == 0:
            try:
                escritura_archivo(archivo_estaciones, configuracion)
                agregar_mensaje(widget_texto, f"Configuración guardada", False)
            except Exception as e:
                agregar_mensaje(widget_texto, f"Error guardando configuración: {e}", False)
    
    pos_inicio = max(0, int(puntero_cabecera) - 5)
    tamano_archivo = os.path.getsize(archivo_binario)
    bytes_restantes = tamano_archivo - pos_inicio
    segundos_estimados = bytes_restantes // bytes_por_segundo
    
    agregar_mensaje(widget_texto, f"Inicio: {pos_inicio}, Segundos: {segundos_estimados}", True)
    
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
            cab_0 = f.read(4)
            if len(cab_0) < 4:
                break
                
            if cab_0 != marca_fija:
                f.seek(pos_actual + 1)
                continue
            
            numero_segundo_b = f.read(5)
            if len(numero_segundo_b) < 5:
                break
            
            cab_1 = f.read(20)
            if cab_1 != cabecera_1_esperada:
                continue
            
            cuerpo = f.read(bytes_cuerpo)
            if len(cuerpo) < bytes_cuerpo:
                break
            
            datos = np.frombuffer(cuerpo, dtype='<i2')
            try:
                datos = datos.reshape((sps, n_canales))
            except ValueError:
                break
            
            if primera_vez:
                offset = datos.mean(axis=0).astype(np.int32)
                datos = (datos.astype(np.int32) - offset).astype(np.int16)
                linea[:] = offset.tolist()
                primera_vez = False
            else:
                datos = (datos.astype(np.int32) - np.array(linea, dtype=np.int32)).astype(np.int16)
            
            for m in range(n_canales):
                canal[m].extend(datos[:, m].tolist())
            
            contador_segundos += 1
            
            if barra_progreso and contador_segundos % 100 == 0:
                barra_progreso.setValue(min(contador_segundos, segundos_estimados))
                QCoreApplication.processEvents()
    
    agregar_mensaje(widget_texto, f"Lectura terminada: {contador_segundos} segundos", True)
    return np.asarray(canal), 0


# =============================================================================
# PASO 2: PROCESADOR DE MSEED (unión por día)
# =============================================================================

def unir_mseeds_por_dia(directorio_binario, dia_yyyymmdd, est_digitales, estaciones, widget_texto, progressBar=None):
    """
    Une archivos MSEED por estación para un día específico.
    Retorna lista de (codigo_estacion, stream_unido, canal_idx)
    """
    estacion_habilitada = estaciones['HAB_CANAL']
    codigo_estacion = estaciones['CODIGO']
    canal_ = list(map(int, estaciones['COMPONENTE']))
    
    patron_mseed_dia = re.compile(r'^([A-Za-z0-9]{4})_(\d{8})_(\d{6}).*\.mseed$', re.IGNORECASE)
    resultados = []
    
    total_estaciones = len([e for e in est_digitales[1:] if estacion_habilitada[int(e[1])] == '1'])
    
    for idx, estacion_digital in enumerate(est_digitales[1:]):
        num_estacion = int(estacion_digital[1])
        
        if progressBar and total_estaciones > 0:
            progressBar.setValue(int((idx / total_estaciones) * 100))
        
        if estacion_habilitada[num_estacion] != '1':
            continue
        
        nombre_carpeta = estacion_digital[0]
        codigo = codigo_estacion[num_estacion]
        
        ruta_carpeta = os.path.join(directorio_binario, nombre_carpeta)
        if not os.path.isdir(ruta_carpeta):
            agregar_mensaje(widget_texto, f"Carpeta no existe: {ruta_carpeta}", False)
            continue
        
        archivos_mseed = []
        try:
            for archivo in os.listdir(ruta_carpeta):
                match = patron_mseed_dia.match(archivo)
                if match and match.group(2) == dia_yyyymmdd:
                    archivos_mseed.append(os.path.join(ruta_carpeta, archivo))
        except Exception as e:
            agregar_mensaje(widget_texto, f"Error al listar {ruta_carpeta}: {e}", False)
            continue
        
        if not archivos_mseed:
            agregar_mensaje(widget_texto, f"{codigo}: No hay MSEED para este día", False)
            continue
        
        agregar_mensaje(widget_texto, f"{codigo}: {len(archivos_mseed)} archivos encontrados", False)
        
        # Ordenar por tiempo
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
                agregar_mensaje(widget_texto, f"  Error al leer {os.path.basename(ruta)}: {e}", False)
        
        if len(stream_unido) == 0:
            agregar_mensaje(widget_texto, f"  No se pudo leer ningún dato", False)
            continue
        
        stream_unido.merge(method=1, fill_value='latest')
        
        canal_idx = 0
        if num_estacion < len(canal_):
            canal_idx = int(canal_[num_estacion]) - 1
            if canal_idx < 0:
                canal_idx = 0
        
        resultados.append((codigo, stream_unido, canal_idx))
        QCoreApplication.processEvents()
    
    if progressBar:
        progressBar.setValue(100)
    
    return resultados


# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================

ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, "src", "ui", "acelerografos.ui"))
Ui_MainWindow, QtBassClass = uic.loadUiType(ruta_ui)

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PROCESAMIENTO SISMICO - UNIFICADO")
        self.setupUi(self)

        # ==== CONEXIONES ====
        self.Btn_Iniciar.clicked.connect(self.iniciar_procesamiento)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)
        self.Btn_Salir.clicked.connect(self.salir)

        # ==== CONFIGURAR AREA DE TEXTO ====
        self.area_texto.clear()
        self.area_texto.setReadOnly(True)

        # ==== DIRECTORIOS POR DEFECTO ====
        self.directorio_trabajo = f"G:{os.sep}Mi unidad{os.sep}DIA{os.sep}"
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
        self.Lbl_directorio_2.setText(self.directorio_binario)

        # ==== FECHA ====
        d = QDate.currentDate()
        self.dateEdit.setDate(d)
        self.dateEdit.dateChanged.connect(self.showDate)
        
        # Inicializar variables de fecha
        self.date = d
        self.archivo = os.path.join(self.directorio_trabajo, d.toString('yyyyMMdd') + '000000')

        # ==== INICIALIZAR OTRAS VARIABLES ====
        self.trCanal = None
        self.directorio = ""
        self.directorio_dia = ""
        self.directorio_registros = ""

        # ==== PARÁMETROS DE ESTACIONES ====
        try:
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
        except Exception as e:
            agregar_mensaje(self.area_texto, f"ERROR al cargar parámetros: {e}", False)
            # Valores por defecto para evitar crashes
            self.estacion_habilitada = ['0'] * 16
            self.codigo_estacion = [f"CH{i+1}" for i in range(16)]
            self.canal_ = [i+1 for i in range(16)]
            self.est_digitales_ = []

        agregar_mensaje(self.area_texto, "=== PROCESAMIENTO SISMICO UNIFICADO INICIADO ===")
        agregar_mensaje(self.area_texto, f"Fecha actual: {d.toString('dd/MM/yyyy')}")
        
        # Verificar R: al inicio
        self.verificar_unidad_r_inicial()

    def verificar_unidad_r_inicial(self):
        """Verifica si R: está disponible al iniciar (solo informativo)"""
        if not os.path.exists('R:/'):
            agregar_mensaje(self.area_texto, "⚠ ATENCIÓN: Unidad R: no disponible - Registro Continuo no conectado", False)
            agregar_mensaje(self.area_texto, "  El procesamiento de binarios se omitirá, solo se procesarán MSEEDs existentes", False)
        else:
            try:
                archivos = os.listdir('R:/')
                agregar_mensaje(self.area_texto, f"✓ Unidad R: disponible - {len(archivos)} archivos encontrados", False)
            except:
                agregar_mensaje(self.area_texto, "⚠ Unidad R: existe pero no se puede leer", False)

    def showDate(self, date: QDate):
        self.date = date
        self.archivo = os.path.join(self.directorio_trabajo, date.toString('yyyyMMdd') + '000000')
        agregar_mensaje(self.area_texto, f"Fecha seleccionada: {date.toString('dd/MM/yyyy')}", False)

    def seleccionar_drive(self):
        folderpath = QFileDialog.getExistingDirectory(self, 'Seleccionar carpeta base DIA')
        if not folderpath:
            return
        if not folderpath.endswith(os.sep):
            folderpath += os.sep

        self.directorio_trabajo = folderpath
        self.Lbl_directorio.setText(self.directorio_trabajo)

        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
        if not os.path.exists(self.directorio_binario):
            folderpath = QFileDialog.getExistingDirectory(self, 'SELECCIONAR DIRECTORIO "Datos Estaciones"')
            if folderpath:
                if not folderpath.endswith(os.sep):
                    folderpath += os.sep
                self.directorio_binario = folderpath

        self.Lbl_directorio_2.setText(self.directorio_binario)
        agregar_mensaje(self.area_texto, f"Directorio de trabajo: {self.directorio_trabajo}", False)
        agregar_mensaje(self.area_texto, f"Directorio de estaciones: {self.directorio_binario}", False)

    def salir(self):
        agregar_mensaje(self.area_texto, "Cerrando aplicación...", False)
        self.close()
        QCoreApplication.processEvents()
        os._exit(0)

    def definir_dia(self):
        directorios_ = obtener_directorios(self.archivo)
        self.directorio = directorios_['Directorio_base']
        self.directorio_dia = directorios_['Directorio_dia']
        self.directorio_registros = directorios_['Directorio_registros']

        for ruta in (self.directorio, self.directorio_dia, self.directorio_registros):
            try:
                Path(ruta).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                agregar_mensaje(self.area_texto, f"No se pudo crear {ruta}: {e}", False)

    def iniciar_procesamiento(self):
        """Procesa completo: primero binarios, luego une MSEEDs"""
        agregar_mensaje(self.area_texto, "", False)
        agregar_mensaje(self.area_texto, "=" * 60, False)
        agregar_mensaje(self.area_texto, "INICIANDO PROCESAMIENTO COMPLETO", False)
        agregar_mensaje(self.area_texto, "=" * 60, False)
        
        self.definir_dia()
        
        # ===== PASO 1: Convertir binarios de R: a MSEED =====
        self.procesar_binarios()
        
        # ===== PASO 2: Unir MSEEDs existentes y generar PNGs =====
        self.procesar_mseeds()
        
        agregar_mensaje(self.area_texto, "=" * 60, False)
        agregar_mensaje(self.area_texto, "PROCESAMIENTO COMPLETADO EXITOSAMENTE", False)
        agregar_mensaje(self.area_texto, "=" * 60, False)
        agregar_mensaje(self.area_texto, "", False)

    def procesar_binarios(self):
        """Paso 1: Lee binarios desde R:, convierte a MSEED y guarda"""
        agregar_mensaje(self.area_texto, "", False)
        agregar_mensaje(self.area_texto, ">>> PASO 1: CONVIRTIENDO BINARIOS DE R: A MSEED <<<", False)
        
        dia_aa = self.date.toString('yyMMdd')
        dia_yyyymmdd = self.date.toString('yyyyMMdd')
        
        # Verificar si R: existe
        if not os.path.exists('R:/'):
            agregar_mensaje(self.area_texto, "  ✗ UNIDAD R: NO DISPONIBLE - No se puede acceder a la unidad de red", False)
            agregar_mensaje(self.area_texto, "  ✗ Verifique que el registrador continuo esté conectado y la unidad R: esté mapeada", False)
            return
        
        # Verificar si R: tiene archivos
        try:
            archivos_r = os.listdir('R:/')
            if not archivos_r:
                agregar_mensaje(self.area_texto, "  ⚠ UNIDAD R: VACÍA - No hay archivos en la unidad", False)
                return
        except PermissionError:
            agregar_mensaje(self.area_texto, "  ✗ PERMISO DENEGADO - No se puede leer la unidad R:", False)
            return
        except Exception as e:
            agregar_mensaje(self.area_texto, f"  ✗ ERROR AL LEER R: - {str(e)}", False)
            return
        
        # Buscar archivos del día actual
        archivos_origen = []
        for archivo in archivos_r:
            if Path(archivo).suffix == '' and archivo.startswith(dia_aa):
                archivos_origen.append(archivo)
        
        if not archivos_origen:
            agregar_mensaje(self.area_texto, f"  ⚠ No hay archivos para el día {dia_yyyymmdd} en R:", False)
            agregar_mensaje(self.area_texto, f"  ⚠ Buscaba archivos que empiecen con: {dia_aa}", False)
            return
        
        archivos_origen.sort()
        agregar_mensaje(self.area_texto, f"  ✓ Archivos encontrados en R:: {archivos_origen}", False)
        
        # Copiar y renombrar
        archivos_procesar = []
        for archivo in archivos_origen:
            nombre_corregido = self.corregir_nombre_archivo(archivo)
            origen = f'R:/{archivo}'
            destino = os.path.join(self.directorio_trabajo, nombre_corregido)
            
            try:
                shutil.copy2(origen, destino)
                agregar_mensaje(self.area_texto, f"  Copiado: {archivo} -> {nombre_corregido}", False)
                archivos_procesar.append(destino)
            except Exception as e:
                agregar_mensaje(self.area_texto, f"  ✗ Error copiando {archivo}: {e}", False)
                continue
        
        if not archivos_procesar:
            agregar_mensaje(self.area_texto, "  ✗ No se pudo copiar ningún archivo", False)
            return
        
        # Limpiar registros anteriores
        registros_eliminados = 0
        if os.path.exists(self.directorio_registros):
            for arch in os.listdir(self.directorio_registros):
                if arch.endswith('.mseed'):
                    try:
                        os.remove(os.path.join(self.directorio_registros, arch))
                        registros_eliminados += 1
                    except:
                        pass
            if registros_eliminados > 0:
                agregar_mensaje(self.area_texto, f"  Limpiados {registros_eliminados} MSEEDs anteriores", False)
        
        # Procesar cada binario
        todos_los_canales = None
        estaciones_csv = os.path.join(self.directorio, "estaciones.csv")
        
        for idx, archivo_bin in enumerate(archivos_procesar):
            agregar_mensaje(self.area_texto, f"\n  Leyendo {Path(archivo_bin).name} ({idx+1}/{len(archivos_procesar)})...", False)
            
            canal, _ = leer_binario_completo(
                archivo_bin, estaciones_csv, 
                self.progressBar, self.area_texto
            )
            
            if todos_los_canales is None:
                todos_los_canales = canal
            else:
                for i in range(16):
                    todos_los_canales[i] = np.concatenate([todos_los_canales[i], canal[i]])
        
        # Convertir a MSEED
        if todos_los_canales is not None:
            fecha_ref = obtencion_hora(archivos_procesar[0])
            
            try:
                self.trCanal = conversion_mseed(
                    todos_los_canales,
                    self.estacion_habilitada,
                    self.codigo_estacion,
                    fecha_ref,
                    self.directorio_registros
                )
                agregar_mensaje(self.area_texto, f"\n  ✓ Conversión a MSEED completada", False)
                
                # Generar PNGs de los datos convertidos
                self.generar_pngs_desde_traces(fecha_ref)
                
            except Exception as e:
                agregar_mensaje(self.area_texto, f"  ✗ Error en conversión: {e}", False)
        else:
            agregar_mensaje(self.area_texto, "  ✗ No se leyeron datos", False)

    def procesar_mseeds(self):
        """Paso 2: Une MSEEDs existentes y genera PNGs"""
        agregar_mensaje(self.area_texto, "", False)
        agregar_mensaje(self.area_texto, ">>> PASO 2: UNIENDO MSEEDS POR DÍA <<<", False)
        
        dia_yyyymmdd = self.date.toString('yyyyMMdd')
        
        # Verificar si existe el directorio de estaciones
        if not os.path.exists(self.directorio_binario):
            agregar_mensaje(self.area_texto, f"  ✗ Directorio no existe: {self.directorio_binario}", False)
            agregar_mensaje(self.area_texto, f"  ✗ Verifique que la ruta sea correcta", False)
            return
        
        # Verificar si hay subdirectorios de estaciones
        try:
            subdirs = [d for d in os.listdir(self.directorio_binario) 
                       if os.path.isdir(os.path.join(self.directorio_binario, d))]
            if not subdirs:
                agregar_mensaje(self.area_texto, f"  ⚠ No hay carpetas de estaciones en {self.directorio_binario}", False)
                return
        except Exception as e:
            agregar_mensaje(self.area_texto, f"  ✗ Error al leer directorio: {e}", False)
            return
        
        # Unir MSEEDs
        agregar_mensaje(self.area_texto, f"  Buscando MSEEDs para el día {dia_yyyymmdd}...", False)
        
        resultados = unir_mseeds_por_dia(
            self.directorio_binario,
            dia_yyyymmdd,
            self.est_digitales_,
            self.estaciones_,
            self.area_texto,
            self.progressBar if hasattr(self, 'progressBar') else None
        )
        
        if not resultados:
            agregar_mensaje(self.area_texto, "  ⚠ No se encontraron MSEEDs para unir", False)
            agregar_mensaje(self.area_texto, "  ⚠ Verifique que los archivos MSEED existan en las carpetas de estaciones", False)
            return
        
        agregar_mensaje(self.area_texto, f"  ✓ Se encontraron {len(resultados)} estaciones con datos", False)
        
        # Guardar streams unidos y generar PNGs
        archivo_evento = dia_yyyymmdd + "_000000"
        
        for codigo, stream_unido, canal_idx in resultados:
            # Guardar MSEED unido
            archivo_salida = os.path.join(self.directorio_registros, f"{codigo}_{archivo_evento}.mseed")
            try:
                stream_unido.write(archivo_salida, format='MSEED', encoding='STEIM1', reclen=512)
                agregar_mensaje(self.area_texto, f"  ✓ Unido: {codigo}_{archivo_evento}.mseed", False)
            except Exception as e:
                agregar_mensaje(self.area_texto, f"  ✗ Error al guardar {codigo}: {e}", False)
                continue
            
            # Generar PNG con el MISMO nombre que el MSEED
            if len(stream_unido) > canal_idx:
                png_salida = os.path.join(self.directorio, f"{codigo}_{archivo_evento}.png")
                try:
                    stream_unido[canal_idx].plot(
                        type='dayplot',
                        outfile=png_salida,
                        dpi=200,
                        size=(2400, 1800),
                        linewidth=0.2
                    )
                    agregar_mensaje(self.area_texto, f"  ✓ PNG: {codigo}_{archivo_evento}.png", False)
                except Exception as e:
                    agregar_mensaje(self.area_texto, f"  ✗ Error en PNG {codigo}: {e}", False)

    def generar_pngs_desde_traces(self, fecha_ref):
        """Genera PNGs desde traces existentes con el mismo nombre que los MSEEDs"""
        # El formato que usa conversion_mseed: f"{self.codigo_estacion[i]}_{fecha_ref}.mseed"
        # donde fecha_ref es un datetime object
        
        for i in range(16):
            if str(self.estacion_habilitada[i]) == '1' and i < len(self.trCanal):
                if self.trCanal[i] and len(self.trCanal[i]) > 0:
                    # Formato exacto que usa conversion_mseed
                    # conversion_mseed usa: f"{codigo_estacion}_{fecha_ref}.mseed"
                    nombre_base = f"{self.codigo_estacion[i]}_{fecha_ref}"
                    
                    # Verificar si existe el archivo MSEED
                    mseed_path = os.path.join(self.directorio_registros, f"{nombre_base}.mseed")
                    png_path = os.path.join(self.directorio, f"{nombre_base}.png")
                    
                    if os.path.exists(mseed_path):
                        try:
                            self.trCanal[i].plot(
                                type='dayplot', 
                                outfile=png_path,
                                dpi=200, 
                                size=(2400, 1800),
                                linewidth=0.2, 
                                show=False
                            )
                            agregar_mensaje(self.area_texto, f"  ✓ PNG: {nombre_base}.png", False)
                        except Exception as e:
                            agregar_mensaje(self.area_texto, f"  ✗ Error en PNG {self.codigo_estacion[i]}: {e}", False)
                    else:
                        agregar_mensaje(self.area_texto, f"  ⚠ No se encontró MSEED para {self.codigo_estacion[i]}, no se genera PNG", False)
        
        plt.close('all')

    def corregir_nombre_archivo(self, nombre_original):
        """Corrige nombre de archivo (235959 → 000000)"""
        solo_nombre = Path(nombre_original).name
        if solo_nombre.endswith('235959'):
            return solo_nombre[:-6] + '000000'
        if re.match(r'^\d{14}$', solo_nombre):
            return solo_nombre[2:]
        return solo_nombre


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())