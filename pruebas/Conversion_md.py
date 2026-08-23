#!/usr/bin/env python3
"""
Conversor Sismológico - CSV a Markdown con Generación de Cuadros
Versión GUI para ejecutar en Spyder/IDE
Autor: Asistente IA

Características:
- Convierte CSV a MD (individual)
- Genera informe con 4 cuadros + contexto histórico
- Interfaz gráfica completa con PyQt5
- Barra de progreso en tiempo real
- Guarda configuración entre sesiones
"""

import sys
import os
import re
import logging
from pathlib import Path
from datetime import datetime

# ==================== VERIFICAR DEPENDENCIAS ====================
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
        QProgressBar, QGroupBox, QCheckBox, QMessageBox, QStatusBar,
        QListWidget, QListWidgetItem
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
    from PyQt5.QtGui import QFont, QTextCursor, QColor, QPalette
except ImportError:
    print("❌ PyQt5 no está instalado. Ejecuta:")
    print("conda install -c conda-forge pyqt")
    sys.exit(1)

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("❌ pandas no está instalado. Ejecuta:")
    print("conda install pandas")
    sys.exit(1)

try:
    import tabulate
except ImportError:
    print("❌ tabulate no está instalado. Ejecuta:")
    print("pip install tabulate")
    sys.exit(1)

# ==================== CONFIGURACIÓN ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== HILO DE CONVERSIÓN ====================
class ConversionThread(QThread):
    """Hilo separado para la conversión sin bloquear la GUI"""
    
    progreso = pyqtSignal(int)
    estado = pyqtSignal(str)
    log = pyqtSignal(str)
    archivo_convertido = pyqtSignal(str, str)
    terminado = pyqtSignal(dict)
    archivos_encontrados = pyqtSignal(list)
    
    def __init__(self, directorio_origen, directorio_salida, recursive=True, generar_informe=True):
        super().__init__()
        self.directorio_origen = Path(directorio_origen)
        self.directorio_salida = Path(directorio_salida)
        self.recursive = recursive
        self.generar_informe = generar_informe
        self.detener = False
        
        # Patrones específicos para tus archivos
        self.patrones = [
            r'_aceleraciones\.csv$',
            r'__rsa_pro\.csv$',
            r'__rsa_sup\.csv$',
            r'__rsa_med\.csv$',
            r'_res\.csv$',
            r'_cat\.csv$',
            r'_rep\.csv$',
            r'_rep_total\.csv$'
        ]
        
        self.estadisticas = {
            'exitosos': 0,
            'fallidos': 0,
            'omitidos': 0,
            'archivos': []
        }
        
        # Almacenar DataFrames para el informe
        self.df_cat = None
        self.df_res = None
        self.df_acel = None
        self.df_rsa_pro = None
        self.df_rsa_med = None
        self.df_rsa_sup = None
        self.resumen_historico = None
        self.periodo = "01/03/2026 al 31/05/2026"
    
    def detener_conversion(self):
        """Detiene la conversión"""
        self.detener = True
    
    def filtrar_archivos(self):
        """Filtra archivos CSV según patrones definidos"""
        archivos_encontrados = []
        
        if self.recursive:
            archivos = list(self.directorio_origen.rglob('*.csv'))
        else:
            archivos = list(self.directorio_origen.glob('*.csv'))
        
        for archivo in archivos:
            for patron in self.patrones:
                if re.search(patron, archivo.name, re.IGNORECASE):
                    archivos_encontrados.append(archivo)
                    break
        
        return archivos_encontrados
    
    def leer_csv_inteligente(self, archivo):
        """Lee CSV detectando automáticamente codificación y separador"""
        codificaciones = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        separadores = [',', ';', '\t', '|']
        
        for encoding in codificaciones:
            try:
                df = pd.read_csv(archivo, encoding=encoding, nrows=5)
                if len(df.columns) > 1:
                    return pd.read_csv(archivo, encoding=encoding)
                
                for sep in separadores:
                    if sep != ',':
                        try:
                            df = pd.read_csv(archivo, encoding=encoding, sep=sep, nrows=5)
                            if len(df.columns) > 1:
                                return pd.read_csv(archivo, encoding=encoding, sep=sep)
                        except:
                            continue
                            
            except Exception:
                continue
        
        try:
            return pd.read_csv(archivo, encoding='utf-8', engine='python')
        except:
            return None
    
    def identificar_tipo(self, nombre_archivo):
        """Identifica el tipo de archivo según su nombre"""
        tipos = {
            '_aceleraciones.csv': 'Aceleraciones',
            '__rsa_pro.csv': 'RSA - Profundidad',
            '__rsa_sup.csv': 'RSA - Superficial',
            '__rsa_med.csv': 'RSA - Media',
            '_res.csv': 'Resultados',
            '_cat.csv': 'Catálogo',
            '_rep.csv': 'Reporte',
            '_rep_total.csv': 'Reporte Total'
        }
        
        for patron, tipo in tipos.items():
            if patron in nombre_archivo:
                return tipo
        
        return 'Datos Sismológicos'
    
    def convertir_csv_a_md(self, archivo):
        """Convierte CSV a Markdown - SOLO DATOS"""
        try:
            df = self.leer_csv_inteligente(archivo)
            
            if df is None or df.empty:
                self.log.emit(f"⚠️ Archivo vacío o no válido: {archivo.name}")
                return None
            
            tipo = self.identificar_tipo(archivo.name)
            
            contenido = f"# {tipo}\n\n"
            contenido += f"**Archivo original:** `{archivo.name}`\n\n"
            contenido += f"**Fecha de conversión:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            contenido += f"**Total de registros:** {len(df):,}\n\n"
            contenido += "---\n\n"
            contenido += df.to_markdown(index=False, tablefmt='github')
            
            # Guardar DataFrame para informe
            self.guardar_dataframe(archivo, df)
            
            return contenido
            
        except Exception as e:
            self.log.emit(f"❌ Error en {archivo.name}: {str(e)}")
            return None
    
    def guardar_dataframe(self, archivo, df):
        """Guarda el DataFrame para usar en el informe"""
        nombre = archivo.name.lower()
        if '_cat.csv' in nombre:
            self.df_cat = df
        elif '_res.csv' in nombre:
            self.df_res = df
        elif '_aceleraciones.csv' in nombre and 'cat' not in nombre:
            self.df_acel = df
        elif '__rsa_pro.csv' in nombre:
            self.df_rsa_pro = df
        elif '__rsa_med.csv' in nombre:
            self.df_rsa_med = df
        elif '__rsa_sup.csv' in nombre:
            self.df_rsa_sup = df
    




    def cargar_resumen_historico(self, parent=None):
        """
        Busca el archivo Resumen histórico.md.
        Si no existe, pide al usuario que lo seleccione.
        """
        archivo_hist = self.directorio_origen / "Resumen histórico.md"
        
        # Primero buscar en el directorio origen
        if archivo_hist.exists():
            with open(archivo_hist, 'r', encoding='utf-8') as f:
                self.resumen_historico = f.read()
            self.log.emit("✅ Resumen histórico encontrado en el directorio de origen")
            return True
        
        # Si no existe, buscar en el directorio de salida
        archivo_hist_salida = self.directorio_salida / "Resumen histórico.md"
        if archivo_hist_salida.exists():
            with open(archivo_hist_salida, 'r', encoding='utf-8') as f:
                self.resumen_historico = f.read()
            self.log.emit("✅ Resumen histórico encontrado en el directorio de salida")
            return True
        
        # Si no existe, mostrar ventana emergente pidiendo el archivo
        self.log.emit("⚠️ No se encontró 'Resumen histórico.md'")
        self.log.emit("📢 Solicitando archivo al usuario...")
        
        # Usar QFileDialog para pedir el archivo
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        
        # Emitir señal para abrir el diálogo desde el hilo principal
        archivo_seleccionado = self.pedir_archivo_historico(parent)
        
        if archivo_seleccionado and Path(archivo_seleccionado).exists():
            # Copiar el archivo al directorio de origen para futuras ejecuciones
            try:
                import shutil
                shutil.copy(archivo_seleccionado, self.directorio_origen / "Resumen histórico.md")
                self.log.emit(f"✅ Archivo histórico copiado a: {self.directorio_origen / 'Resumen histórico.md'}")
            except Exception as e:
                self.log.emit(f"⚠️ No se pudo copiar el archivo: {e}")
            
            with open(archivo_seleccionado, 'r', encoding='utf-8') as f:
                self.resumen_historico = f.read()
            self.log.emit(f"✅ Resumen histórico cargado desde: {archivo_seleccionado}")
            return True
        else:
            self.log.emit("⚠️ No se seleccionó ningún archivo histórico. El informe se generará sin contexto histórico.")
            self.resumen_historico = None
            return False
    
    def pedir_archivo_historico(self, parent=None):
        """
        Abre un diálogo para que el usuario seleccione el archivo histórico.
        Este método se ejecuta en el hilo principal usando una señal.
        """
        # Esta función se ejecuta desde el hilo de conversión,
        # pero debemos usar una señal para mostrar el diálogo en el hilo principal
        import time
        
        # Usar una variable para almacenar el resultado
        resultado = [None]
        
        # Función que se ejecutará en el hilo principal
        def mostrar_dialogo():
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            
            # Mostrar mensaje informativo
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Archivo Histórico Requerido")
            msg.setText("No se encontró el archivo 'Resumen histórico.md'")
            msg.setInformativeText(
                "Para generar el informe completo con contexto histórico, "
                "necesitamos el archivo que contiene el resumen histórico de trimestres anteriores.\n\n"
                "¿Deseas seleccionarlo ahora?\n\n"
                "Si cancelas, el informe se generará sin el contexto histórico."
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)
            respuesta = msg.exec_()
            
            if respuesta == QMessageBox.Yes:
                archivo, _ = QFileDialog.getOpenFileName(
                    parent,
                    "Seleccionar Resumen Histórico",
                    str(self.directorio_origen),
                    "Archivos Markdown (*.md);;Todos los archivos (*.*)"
                )
                if archivo:
                    resultado[0] = archivo
                    self.log.emit(f"📄 Archivo seleccionado: {archivo}")
                else:
                    self.log.emit("⚠️ Selección cancelada por el usuario")
            else:
                self.log.emit("⚠️ Usuario canceló la selección del archivo histórico")
        
        # Ejecutar en el hilo principal usando un temporizador
        from PyQt5.QtCore import QTimer, QEventLoop
        
        loop = QEventLoop()
        
        # Crear un temporizador para ejecutar el diálogo en el hilo principal
        def ejecutar_dialogo():
            mostrar_dialogo()
            loop.quit()
        
        # Si estamos en el hilo principal, ejecutar directamente
        import threading
        if threading.current_thread() is threading.main_thread():
            mostrar_dialogo()
        else:
            # Si estamos en el hilo secundario, usar el temporizador
            QTimer.singleShot(0, ejecutar_dialogo)
            loop.exec_()
        
        return resultado[0]


   
    def crear_resumen_historico_base(self):
        """Crea un resumen histórico base"""
        return """## Resumen ejecutivo
- **Síntesis del período analizado:** Los documentos cubren el monitoreo sísmico y estructural realizado bajo el convenio entre la Universidad de Cuenca (Red Sísmica del Austro - RSA) y ELECAUSTRO S.A. desde el **primer trimestre (marzo 2023)** hasta el **duodécimo trimestre (febrero 2026)**. El análisis técnico se enfoca en cinco zonas de interés: Chanlud, Labrado, Huascachaca, Ocaña y Soldados.
- **Principales hitos y dificultades:** Se destaca el reinicio de la monitorización en marzo de 2023 tras una pausa en el convenio. Entre los hitos sísmicos resaltan el sismo de Balao (marzo 2023) y el evento del 21 de junio de 2025, que generó una secuencia significativa de réplicas. Las principales dificultades han sido de carácter operativo: fallas constantes en el sistema de puesta a tierra, daños por descargas eléctricas atmosféricas, inundaciones en galerías e interferencias en los enlaces de comunicación debido a factores climáticos como el estiaje.

## Línea de tiempo simplificada
| Año/Mes | Evento Relevante |
| :--- | :--- |
| **2023 / Marzo** | Retoma de la monitorización de activos de ELECAUSTRO S.A.. |
| **2023 / 18 Marzo** | Registro del terremoto de Balao (6.8 MLv). |
| **2024 / Junio-Agosto** | Optimización del procesamiento de datos y mejora de la transmisión en tiempo real. |
| **2025 / 21 Junio** | Sismo de magnitud 4.7 Md en Naranjal con múltiples réplicas. |
| **2025 / Diciembre** | Registro de enjambre sísmico en Naranjal asociado a la falla de Naranjal. |

## Problemas recurrentes documentados
- **Fallas en el sistema de puesta a tierra:** Sensores estáticos de Chanlud inoperativos.
- **Ruido ambiental y operativo:** Presencia constante de ruido por viento en la estación Chanlud.
- **Inestabilidad de enlaces analógicos:** Pérdidas de conexión intermitentes.

## Estado actual de la información
- **Completo:** Catálogo sísmico y acelerográfico regional.
- **En proceso:** Implementación de nuevos diseños de puesta a tierra.
- **Afectado:** Capacidad de triangulación sísmica reducida por daños en estaciones clave.

## Buenas prácticas identificadas
- **Automatización y Alertas:** Implementación de sistemas de alertas para fallos.
- **Gestión de Datos:** Mejora en la conversión de datos al formato miniSEED.
- **Análisis de Correlación:** Uso de mediciones de caudales para alertas tempranas.

## Recomendaciones clave
- **Protección Eléctrica:** Instalar equipos de protección para la red eléctrica.
- **Rehabilitación de Sensores:** Implementar sistemas de puesta a tierra en Chanlud y Labrado.
- **Modernización de Red:** Priorizar la digitalización de los enlaces de comunicación.
"""
    
    def generar_cuadro1(self):
        """Cuadro 1: Actividad sísmica en diferentes períodos"""
        if self.df_res is None:
            return "⚠️ **No hay datos de resultados disponibles**\n"
        
        df = self.df_res.copy()
        df = df[df['DIA'] != 'Total:'].copy()
        df['DIA'] = pd.to_numeric(df['DIA'], errors='coerce')
        df = df.dropna(subset=['DIA'])
        df['DIA'] = df['DIA'].astype(int)
        
        periodos = [
            ("1-10 días", 1, 10),
            ("11-20 días", 11, 20),
            ("21-30 días", 21, 30),
            ("31-40 días", 31, 40),
            ("41-50 días", 41, 50),
            ("51-60 días", 51, 60),
            ("61-70 días", 61, 70),
            ("71-80 días", 71, 80),
            ("81-92 días", 81, 92)
        ]
        
        contenido = "## Cuadro 1. Actividad sísmica en diferentes períodos\n\n"
        contenido += f"**Período analizado:** {self.periodo}\n\n"
        contenido += "| Período | SISMO | FF | FC | TELESISMO | Evento Local | INDEFINIDO | Ruido |\n"
        contenido += "|---------|-------|----|----|-----------|--------------|------------|-------|\n"
        
        for nombre, inicio, fin in periodos:
            mask = (df['DIA'] >= inicio) & (df['DIA'] <= fin)
            subset = df[mask]
            if len(subset) > 0:
                contenido += f"| {nombre} | {subset['SISMO'].sum()} | {subset['FF'].sum()} | {subset['FC'].sum()} | {subset['TELESISMO'].sum()} | {subset['Evento Local'].sum()} | {subset['INDEFINIDO'].sum()} | {subset['Ruido'].sum()} |\n"
        
        contenido += f"| **TOTAL** | **{df['SISMO'].sum()}** | **{df['FF'].sum()}** | **{df['FC'].sum()}** | **{df['TELESISMO'].sum()}** | **{df['Evento Local'].sum()}** | **{df['INDEFINIDO'].sum()}** | **{df['Ruido'].sum()}** |\n"
        return contenido
    
    def generar_cuadro2(self):
        """Cuadro 2: Aceleraciones máximas registradas"""
        if self.df_acel is None:
            return "⚠️ **No hay datos de aceleraciones disponibles**\n"
        
        df = self.df_acel.copy()
        
        contenido = "## Cuadro 2. Aceleraciones máximas registradas (Valores en cm/seg²)\n\n"
        contenido += f"**Período analizado:** {self.periodo}\n\n"
        contenido += "| Evento | Estación | Canal | Aceleración Máxima (cm/s²) |\n"
        contenido += "|--------|----------|-------|---------------------------|\n"
        
        for idx, row in df.iterrows():
            if idx < 2:
                continue
            
            evento = row.iloc[0]
            if pd.isna(evento) or str(evento).lower() == 'nan':
                continue
            
            estacion = row.iloc[1] if pd.notna(row.iloc[1]) else "Desconocida"
            
            for canal, col_idx in [(0, 2), (1, 5), (2, 8)]:
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if pd.notna(val) and str(val).lower() != 'nan':
                        try:
                            val_float = float(val)
                            contenido += f"| {evento} | {estacion} | Canal {canal} | {val_float:.4f} |\n"
                        except:
                            pass
        
        return contenido
    
    def generar_cuadro3(self):
        """Cuadro 3: Eventos relevantes que generaron acelerogramas"""
        if self.df_acel is None:
            return "⚠️ **No hay datos de aceleraciones disponibles**\n"
        
        df = self.df_acel.copy()
        
        contenido = "## Cuadro 3. Eventos relevantes que generaron acelerogramas\n\n"
        contenido += f"**Período analizado:** {self.periodo}\n\n"
        contenido += "| N° | Fecha | Hora | Evento | Estación | Canales | Magnitud |\n"
        contenido += "|----|-------|------|--------|----------|---------|----------|\n"
        
        eventos_acel = {}
        for idx, row in df.iterrows():
            if idx < 2:
                continue
            
            evento = row.iloc[0]
            if pd.isna(evento) or str(evento).lower() == 'nan':
                continue
            
            if evento not in eventos_acel:
                eventos_acel[evento] = {'estaciones': set(), 'canales': []}
            
            estacion = row.iloc[1] if pd.notna(row.iloc[1]) else "Desconocida"
            eventos_acel[evento]['estaciones'].add(str(estacion))
            
            for canal, col_idx in [(0, 2), (1, 5), (2, 8)]:
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if pd.notna(val) and str(val).lower() != 'nan':
                        try:
                            if float(val) > 0:
                                eventos_acel[evento]['canales'].append(f"Canal {canal}")
                        except:
                            pass
            
            eventos_acel[evento]['canales'] = list(set(eventos_acel[evento]['canales']))
        
        eventos_ordenados = sorted(eventos_acel.keys())
        
        for i, evento in enumerate(eventos_ordenados, 1):
            if len(evento) >= 15:
                fecha_str = evento[:8]
                hora_str = evento[9:15]
                fecha_form = f"{fecha_str[6:8]}/{fecha_str[4:6]}/{fecha_str[0:4]}"
                hora_form = f"{hora_str[:2]}:{hora_str[2:4]}:{hora_str[4:6]}"
            else:
                fecha_form = evento[:8] if len(evento) >= 8 else evento
                hora_form = ""
            
            estaciones = ", ".join(eventos_acel[evento]['estaciones'])
            canales = ", ".join(eventos_acel[evento]['canales']) if eventos_acel[evento]['canales'] else "Todos"
            
            magnitud = ""
            if self.df_cat is not None:
                match = self.df_cat[self.df_cat['ruta'].str.contains(evento.replace('.sis', ''), na=False)]
                if len(match) > 0:
                    mag = match.iloc[0]['Mag']
                    if pd.notna(mag):
                        magnitud = f"{mag:.1f}"
            
            contenido += f"| {i} | {fecha_form} | {hora_form} | `{evento}` | {estaciones} | {canales} | {magnitud} |\n"
        
        return contenido
    
    def generar_cuadro4(self):
        """Cuadro 4: Aceleraciones en Chanlud - evento preponderante"""
        if self.df_acel is None:
            return "⚠️ **No hay datos de aceleraciones disponibles**\n"
        
        df = self.df_acel.copy()
        
        evento_preponderante = None
        max_acel = 0
        
        for idx, row in df.iterrows():
            if idx < 2:
                continue
            
            evento = row.iloc[0]
            if pd.isna(evento) or str(evento).lower() == 'nan':
                continue
            
            estacion = row.iloc[1] if pd.notna(row.iloc[1]) else ""
            if 'CHA' not in str(estacion).upper():
                continue
            
            for col_idx in [2, 5, 8]:
                if col_idx < len(row):
                    val = row.iloc[col_idx]
                    if pd.notna(val) and str(val).lower() != 'nan':
                        try:
                            val_float = float(val)
                            if val_float > max_acel:
                                max_acel = val_float
                                evento_preponderante = evento
                        except:
                            pass
        
        contenido = "## Cuadro 4. Aceleraciones máximas en las estaciones acelerográficas de la presa de Chanlud correspondientes al evento preponderante\n\n"
        contenido += f"**Período analizado:** {self.periodo}\n\n"
        
        if evento_preponderante is None:
            contenido += "⚠️ **No se encontraron eventos registrados en estaciones CHA (Chanlud).**\n"
            return contenido
        
        contenido += f"**Evento preponderante:** `{evento_preponderante}`\n\n"
        contenido += "| Estación | Canal | Aceleración Máxima (cm/s²) | Velocidad Máxima (cm/s) | Desplazamiento Máximo (cm) |\n"
        contenido += "|----------|-------|---------------------------|-------------------------|---------------------------|\n"
        
        for idx, row in df.iterrows():
            if idx < 2:
                continue
            
            evento = row.iloc[0]
            if pd.isna(evento) or str(evento).lower() == 'nan':
                continue
            
            if evento != evento_preponderante:
                continue
            
            estacion = row.iloc[1] if pd.notna(row.iloc[1]) else "Desconocida"
            if 'CHA' not in str(estacion).upper():
                continue
            
            for canal, col_acel, col_vel, col_desp in [(0, 2, 3, 4), (1, 5, 6, 7), (2, 8, 9, 10)]:
                if col_acel >= len(row):
                    continue
                
                acel = row.iloc[col_acel] if pd.notna(row.iloc[col_acel]) else None
                vel = row.iloc[col_vel] if col_vel < len(row) and pd.notna(row.iloc[col_vel]) else None
                desp = row.iloc[col_desp] if col_desp < len(row) and pd.notna(row.iloc[col_desp]) else None
                
                if acel is not None and str(acel).lower() != 'nan':
                    try:
                        acel_f = float(acel)
                        vel_f = float(vel) if vel is not None and str(vel).lower() != 'nan' else 0
                        desp_f = float(desp) if desp is not None and str(desp).lower() != 'nan' else 0
                        contenido += f"| {estacion} | Canal {canal} | {acel_f:.4f} | {vel_f:.4f} | {desp_f:.4f} |\n"
                    except:
                        pass
        
        return contenido
    
    def generar_cuadro_comparativo(self):
        """Cuadro Comparativo - Estadísticas del período"""
        contenido = "## Cuadro Comparativo - Estadísticas del Período\n\n"
        contenido += f"**Período analizado:** {self.periodo}\n\n"
        
        if self.df_cat is not None:
            df_cat = self.df_cat.copy()
            
            contenido += "### Distribución de eventos por magnitud\n\n"
            contenido += "| Rango de Magnitud | Cantidad | Porcentaje |\n"
            contenido += "|-------------------|----------|------------|\n"
            
            rangos = [("< 3.0", 0, 2.9), ("3.0 - 3.4", 3.0, 3.4), ("3.5 - 3.9", 3.5, 3.9), ("≥ 4.0", 4.0, 10)]
            total = len(df_cat)
            for nombre, min_mag, max_mag in rangos:
                mask = (df_cat['Mag'] >= min_mag) & (df_cat['Mag'] <= max_mag)
                count = mask.sum()
                pct = (count / total * 100) if total > 0 else 0
                contenido += f"| {nombre} | {count} | {pct:.1f}% |\n"
            
            contenido += f"\n**Total de eventos:** {total}\n"
            
            contenido += "\n### Distribución por profundidad\n\n"
            contenido += "| Rango de Profundidad | Cantidad |\n"
            contenido += "|----------------------|----------|\n"
            
            prof_rangos = [("< 30 km", 0, 30), ("30 - 60 km", 30, 60), ("60 - 100 km", 60, 100), ("> 100 km", 100, 500)]
            for nombre, min_p, max_p in prof_rangos:
                mask = (df_cat['prof'] >= min_p) & (df_cat['prof'] <= max_p)
                contenido += f"| {nombre} | {mask.sum()} |\n"
        
        if self.df_res is not None:
            df_res = self.df_res.copy()
            df_res = df_res[df_res['DIA'] != 'Total:'].copy()
            df_res['DIA'] = pd.to_numeric(df_res['DIA'], errors='coerce')
            df_res = df_res.dropna(subset=['DIA'])
            
            contenido += "\n### Estadísticas de actividad sísmica\n\n"
            contenido += "| Métrica | Valor |\n"
            contenido += "|---------|-------|\n"
            contenido += f"| Total de eventos SISMO | {df_res['SISMO'].sum()} |\n"
            contenido += f"| Total de eventos FF | {df_res['FF'].sum()} |\n"
            contenido += f"| Total de eventos FC | {df_res['FC'].sum()} |\n"
            contenido += f"| Total de eventos INDEFINIDO | {df_res['INDEFINIDO'].sum()} |\n"
            contenido += f"| Promedio diario de SISMO | {df_res['SISMO'].mean():.2f} |\n"
            contenido += f"| Día con mayor actividad (SISMO) | {df_res.loc[df_res['SISMO'].idxmax(), 'DIA']} |\n"
        
        return contenido
    
    def generar_amplificaciones(self):
        """Análisis de amplificaciones a partir de RSA"""
        contenido = "## Análisis de Amplificaciones\n\n"
        contenido += f"**Período analizado:** {self.periodo}\n\n"
        
        if self.df_rsa_pro is not None and self.df_rsa_med is not None and self.df_rsa_sup is not None:
            contenido += "### Distribución de eventos según profundidad\n\n"
            contenido += "| Tipo | Cantidad | Profundidad promedio (km) |\n"
            contenido += "|------|----------|---------------------------|\n"
            
            for nombre, df in [("Profundo", self.df_rsa_pro), ("Medio", self.df_rsa_med), ("Superficial", self.df_rsa_sup)]:
                if df is not None:
                    prof_avg = df['Prof.'].mean() if 'Prof.' in df.columns else 0
                    contenido += f"| {nombre} | {len(df)} | {abs(prof_avg):.1f} |\n"
            
            contenido += "\n### Distribución de magnitudes\n\n"
            contenido += "| Tipo | Magnitud promedio | Mínimo | Máximo |\n"
            contenido += "|------|-------------------|--------|--------|\n"
            
            for nombre, df in [("Profundo", self.df_rsa_pro), ("Medio", self.df_rsa_med), ("Superficial", self.df_rsa_sup)]:
                if df is not None and 'Mag.' in df.columns:
                    mag_avg = df['Mag.'].mean()
                    mag_min = df['Mag.'].min()
                    mag_max = df['Mag.'].max()
                    contenido += f"| {nombre} | {mag_avg:.2f} | {mag_min:.1f} | {mag_max:.1f} |\n"
        else:
            contenido += "⚠️ **No hay datos RSA disponibles para el análisis de amplificaciones.**\n"
        
        return contenido
    
    def generar_informe(self):
        """Genera el informe completo con todos los cuadros"""
        self.log.emit("\n📋 Generando informe consolidado...")
        
        contenido = "# INFORME SISMOLÓGICO - TRIMESTRE ACTUAL\n\n"
        contenido += f"**Período analizado:** {self.periodo}\n"
        contenido += f"**Fecha de generación:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        contenido += "---\n\n"
        
        # Contexto histórico
        self.cargar_resumen_historico()
        contenido += "## 📋 Contexto Histórico\n\n"
        contenido += self.resumen_historico
        contenido += "\n\n---\n\n"
        
        # Cuadros
        contenido += self.generar_cuadro1()
        contenido += "\n\n"
        contenido += self.generar_cuadro2()
        contenido += "\n\n"
        contenido += self.generar_cuadro3()
        contenido += "\n\n"
        contenido += self.generar_cuadro4()
        contenido += "\n\n"
        contenido += self.generar_cuadro_comparativo()
        contenido += "\n\n"
        contenido += self.generar_amplificaciones()
        contenido += "\n\n"
        
        contenido += "---\n"
        contenido += f"*Informe generado automáticamente a partir de los datos del trimestre {self.periodo}*\n"
        
        # Guardar informe
        archivo_informe = self.directorio_salida / f"Informe_Sismologico_{self.periodo.replace('/', '_').replace(' ', '_')}.md"
        with open(archivo_informe, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        self.log.emit(f"✅ Informe guardado: {archivo_informe.name}")
        return archivo_informe
    



    def run(self):
        """Ejecuta la conversión en el hilo"""
        self.log.emit("🚀 Iniciando conversión...")
        
        # Crear directorio de salida
        self.directorio_salida.mkdir(parents=True, exist_ok=True)
        
        # Buscar archivos
        archivos = self.filtrar_archivos()
        
        if not archivos:
            self.log.emit("⚠️ No se encontraron archivos con los patrones especificados")
            self.terminado.emit(self.estadisticas)
            return
        
        self.archivos_encontrados.emit([str(a) for a in archivos])
        self.log.emit(f"📄 Archivos encontrados: {len(archivos)}")
        for archivo in archivos:
            self.log.emit(f"   • {archivo.name}")
        
        total = len(archivos)
        
        for idx, archivo in enumerate(archivos, 1):
            if self.detener:
                self.log.emit("⏹️ Conversión detenida por el usuario")
                break
            
            self.log.emit(f"\n[{idx}/{total}] 🔄 Procesando: {archivo.name}")
            
            contenido = self.convertir_csv_a_md(archivo)
            
            if contenido is None:
                self.estadisticas['fallidos'] += 1
                continue
            
            output_file = self.directorio_salida / f"{archivo.stem}.md"
            counter = 1
            while output_file.exists():
                output_file = self.directorio_salida / f"{archivo.stem}_{counter}.md"
                counter += 1
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            self.estadisticas['exitosos'] += 1
            tipo = self.identificar_tipo(archivo.name)
            self.estadisticas['archivos'].append({
                'original': archivo.name,
                'salida': output_file.name,
                'tipo': tipo
            })
            
            self.archivo_convertido.emit(archivo.name, output_file.name)
            self.log.emit(f"✅ Convertido: {output_file.name} ({tipo})")
            
            progreso = int((idx / total) * 100)
            self.progreso.emit(progreso)
        
        # Generar informe - PASAR EL PARENT PARA EL DIALOGO
        if self.generar_informe:
            # Necesitamos obtener el parent (la ventana principal)
            # Para esto, emitimos una señal o usamos un método
            self.generar_informe_con_dialogo()
        
        self.progreso.emit(100)
        self.log.emit("\n✅ Conversión completada")
        self.terminado.emit(self.estadisticas)
    
    def generar_informe_con_dialogo(self):
        """Genera el informe con diálogo para pedir el archivo histórico"""
        self.log.emit("\n📋 Generando informe consolidado...")
        
        # Cargar resumen histórico con diálogo
        # El parent se pasa como None porque estamos en el hilo secundario,
        # pero el método cargar_resumen_historico manejará el diálogo correctamente
        self.cargar_resumen_historico(parent=None)
        
        contenido = "# INFORME SISMOLÓGICO - TRIMESTRE ACTUAL\n\n"
        contenido += f"**Período analizado:** {self.periodo}\n"
        contenido += f"**Fecha de generación:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        contenido += "---\n\n"
        
        # Contexto histórico
        if self.resumen_historico:
            contenido += "## 📋 Contexto Histórico\n\n"
            contenido += self.resumen_historico
            contenido += "\n\n---\n\n"
        else:
            contenido += "## 📋 Contexto Histórico\n\n"
            contenido += "⚠️ **No se dispone del archivo 'Resumen histórico.md' para este trimestre.**\n\n"
            contenido += "El informe se genera sin el contexto histórico de trimestres anteriores.\n\n"
            contenido += "---\n\n"
        
        # Cuadros
        contenido += self.generar_cuadro1()
        contenido += "\n\n"
        contenido += self.generar_cuadro2()
        contenido += "\n\n"
        contenido += self.generar_cuadro3()
        contenido += "\n\n"
        contenido += self.generar_cuadro4()
        contenido += "\n\n"
        contenido += self.generar_cuadro_comparativo()
        contenido += "\n\n"
        contenido += self.generar_amplificaciones()
        contenido += "\n\n"
        
        contenido += "---\n"
        contenido += f"*Informe generado automáticamente a partir de los datos del trimestre {self.periodo}*\n"
        
        # Guardar informe
        archivo_informe = self.directorio_salida / f"Informe_Sismologico_{self.periodo.replace('/', '_').replace(' ', '_')}.md"
        with open(archivo_informe, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        self.log.emit(f"✅ Informe guardado: {archivo_informe}")
        
        # Mostrar mensaje emergente con la ubicación
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Informe Generado")
        msg.setText("✅ Informe generado correctamente")
        msg.setInformativeText(f"Ubicación:\n{archivo_informe}")
        msg.setStandardButtons(QMessageBox.Ok)
        # Para mostrar desde el hilo secundario, usamos un temporizador
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, msg.exec_)














# ==================== VENTANA PRINCIPAL ====================
class VentanaPrincipal(QMainWindow):
    """Ventana principal de la aplicación"""
    
    def __init__(self):
        super().__init__()
        self.hilo_conversion = None
        self.settings = QSettings("Sismologia", "ConversorMD")
        self.init_ui()
        self.cargar_configuracion()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("Conversor Sismológico - CSV a Markdown + Informe")
        self.setGeometry(100, 100, 1100, 750)
        
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QVBoxLayout(widget_central)
        layout_principal.setSpacing(10)
        
        # ===== SECCIÓN DE DIRECTORIOS =====
        grupo_directorios = QGroupBox("📁 Directorios de Trabajo")
        grupo_directorios.setStyleSheet("QGroupBox { font-weight: bold; font-size: 12pt; }")
        layout_directorios = QVBoxLayout()
        
        layout_origen = QHBoxLayout()
        label_origen = QLabel("📂 Origen:")
        label_origen.setFixedWidth(70)
        self.edit_origen = QLineEdit()
        self.edit_origen.setPlaceholderText("Selecciona el directorio con los archivos CSV...")
        self.edit_origen.setReadOnly(True)
        self.btn_origen = QPushButton("🔍 Examinar")
        self.btn_origen.setFixedWidth(120)
        self.btn_origen.clicked.connect(self.seleccionar_directorio_origen)
        layout_origen.addWidget(label_origen)
        layout_origen.addWidget(self.edit_origen)
        layout_origen.addWidget(self.btn_origen)
        
        layout_salida = QHBoxLayout()
        label_salida = QLabel("📁 Salida:")
        label_salida.setFixedWidth(70)
        self.edit_salida = QLineEdit()
        self.edit_salida.setPlaceholderText("Directorio donde se guardarán los archivos...")
        self.edit_salida.setReadOnly(True)
        self.btn_salida = QPushButton("🔍 Examinar")
        self.btn_salida.setFixedWidth(120)
        self.btn_salida.clicked.connect(self.seleccionar_directorio_salida)
        layout_salida.addWidget(label_salida)
        layout_salida.addWidget(self.edit_salida)
        layout_salida.addWidget(self.btn_salida)
        
        layout_directorios.addLayout(layout_origen)
        layout_directorios.addLayout(layout_salida)
        grupo_directorios.setLayout(layout_directorios)
        
        # ===== SECCIÓN DE OPCIONES =====
        grupo_opciones = QGroupBox("⚙️ Opciones de Conversión")
        layout_opciones = QHBoxLayout()
        
        self.check_recursivo = QCheckBox("📂 Incluir subdirectorios")
        self.check_recursivo.setChecked(True)
        self.check_recursivo.setStyleSheet("font-size: 11pt;")
        
        self.check_informe = QCheckBox("📊 Generar Informe Consolidado (Cuadros)")
        self.check_informe.setChecked(True)
        self.check_informe.setStyleSheet("font-size: 11pt;")
        
        label_patrones = QLabel("🔍 Busca: _aceleraciones, __rsa_*, _res, _cat, _rep*")
        label_patrones.setStyleSheet("font-size: 10pt; color: #555;")
        
        layout_opciones.addWidget(self.check_recursivo)
        layout_opciones.addWidget(self.check_informe)
        layout_opciones.addStretch()
        layout_opciones.addWidget(label_patrones)
        
        grupo_opciones.setLayout(layout_opciones)
        
        # ===== SECCIÓN DE ARCHIVOS ENCONTRADOS =====
        grupo_archivos = QGroupBox("📄 Archivos Encontrados")
        layout_archivos = QVBoxLayout()
        
        self.list_archivos = QListWidget()
        self.list_archivos.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: #fafafa;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)
        self.list_archivos.setMaximumHeight(100)
        
        layout_archivos.addWidget(self.list_archivos)
        grupo_archivos.setLayout(layout_archivos)
        
        # ===== BARRA DE PROGRESO =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 30px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        self.progress_bar.setValue(0)
        
        # ===== ÁREA DE LOG =====
        label_log = QLabel("📝 Registro de Actividad:")
        label_log.setStyleSheet("font-weight: bold; font-size: 11pt;")
        
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setFont(QFont("Consolas", 9))
        self.text_log.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', monospace;
            }
        """)
        self.text_log.setMinimumHeight(250)
        
        # ===== BOTONES DE ACCIÓN =====
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(10)
        
        self.btn_iniciar = QPushButton("▶️ Iniciar Conversión")
        self.btn_iniciar.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 12pt;
                padding: 12px 30px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.btn_iniciar.clicked.connect(self.iniciar_conversion)
        
        self.btn_detener = QPushButton("⏹️ Detener")
        self.btn_detener.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 12pt;
                padding: 12px 30px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.btn_detener.clicked.connect(self.detener_conversion)
        self.btn_detener.setEnabled(False)
        
        self.btn_limpiar = QPushButton("🧹 Limpiar Log")
        self.btn_limpiar.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_limpiar.clicked.connect(self.limpiar_log)
        
        self.btn_salir = QPushButton("🚪 Salir")
        self.btn_salir.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        self.btn_salir.clicked.connect(self.cerrar_aplicacion)
        
        layout_botones.addWidget(self.btn_iniciar)
        layout_botones.addWidget(self.btn_detener)
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_limpiar)
        layout_botones.addWidget(self.btn_salir)
        
        # ===== ENSAMBLAR TODO =====
        layout_principal.addWidget(grupo_directorios)
        layout_principal.addWidget(grupo_opciones)
        layout_principal.addWidget(grupo_archivos)
        layout_principal.addWidget(self.progress_bar)
        layout_principal.addWidget(label_log)
        layout_principal.addWidget(self.text_log)
        layout_principal.addLayout(layout_botones)
        
        # ===== BARRA DE ESTADO =====
        self.statusBar().showMessage("✅ Listo")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                color: #333;
                font-weight: bold;
                padding: 5px;
            }
        """)
        
        self.setMinimumSize(900, 680)
    
    def cargar_configuracion(self):
        """Carga la configuración guardada"""
        self.edit_origen.setText(self.settings.value("origen", ""))
        self.edit_salida.setText(self.settings.value("salida", ""))
        self.check_recursivo.setChecked(self.settings.value("recursivo", True, type=bool))
        self.check_informe.setChecked(self.settings.value("informe", True, type=bool))
    
    def guardar_configuracion(self):
        """Guarda la configuración actual"""
        self.settings.setValue("origen", self.edit_origen.text())
        self.settings.setValue("salida", self.edit_salida.text())
        self.settings.setValue("recursivo", self.check_recursivo.isChecked())
        self.settings.setValue("informe", self.check_informe.isChecked())
    
    def seleccionar_directorio_origen(self):
        directorio = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio con Archivos CSV",
            "",
            QFileDialog.ShowDirsOnly
        )
        if directorio:
            self.edit_origen.setText(directorio)
            self.list_archivos.clear()
            self.guardar_configuracion()
    
    def seleccionar_directorio_salida(self):
        directorio = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio de Salida",
            "",
            QFileDialog.ShowDirsOnly
        )
        if directorio:
            self.edit_salida.setText(directorio)
            self.guardar_configuracion()
    
    def iniciar_conversion(self):
        """Inicia el proceso de conversión"""
        if not self.edit_origen.text():
            QMessageBox.warning(self, "Error", "Selecciona un directorio de origen.")
            return
        
        if not os.path.exists(self.edit_origen.text()):
            QMessageBox.warning(self, "Error", f"El directorio '{self.edit_origen.text()}' no existe.")
            return
        
        if not self.edit_salida.text():
            self.edit_salida.setText(self.edit_origen.text())
        
        self.guardar_configuracion()
        
        self.hilo_conversion = ConversionThread(
            directorio_origen=self.edit_origen.text(),
            directorio_salida=self.edit_salida.text(),
            recursive=self.check_recursivo.isChecked(),
            generar_informe=self.check_informe.isChecked()
        )
        
        self.hilo_conversion.progreso.connect(self.progress_bar.setValue)
        self.hilo_conversion.log.connect(self.agregar_log)
        self.hilo_conversion.archivo_convertido.connect(self.actualizar_estado)
        self.hilo_conversion.terminado.connect(self.conversion_terminada)
        self.hilo_conversion.archivos_encontrados.connect(self.mostrar_archivos)
        
        self.btn_iniciar.setEnabled(False)
        self.btn_detener.setEnabled(True)
        self.btn_origen.setEnabled(False)
        self.btn_salida.setEnabled(False)
        self.check_recursivo.setEnabled(False)
        self.check_informe.setEnabled(False)
        self.list_archivos.clear()
        
        self.statusBar().showMessage("🔄 Convirtiendo...")
        self.agregar_log("=" * 70)
        self.agregar_log("🚀 INICIANDO CONVERSIÓN")
        self.agregar_log("=" * 70)
        
        self.hilo_conversion.start()
    
    def detener_conversion(self):
        if self.hilo_conversion and self.hilo_conversion.isRunning():
            self.hilo_conversion.detener_conversion()
            self.agregar_log("⏹️ Deteniendo conversión...")
            self.btn_detener.setEnabled(False)
            self.statusBar().showMessage("⏹️ Deteniendo...")
    
    def conversion_terminada(self, estadisticas):
        self.btn_iniciar.setEnabled(True)
        self.btn_detener.setEnabled(False)
        self.btn_origen.setEnabled(True)
        self.btn_salida.setEnabled(True)
        self.check_recursivo.setEnabled(True)
        self.check_informe.setEnabled(True)
        
        mensaje = f"✅ Conversión completada\n\n📊 Resumen:\n• Exitosos: {estadisticas['exitosos']}\n• Fallidos: {estadisticas['fallidos']}\n• Total: {len(estadisticas['archivos'])}\n\n📁 Archivos guardados en:\n{self.edit_salida.text()}"
        
        if estadisticas['exitosos'] > 0:
            QMessageBox.information(self, "Conversión Completada", mensaje)
        else:
            QMessageBox.warning(self, "Conversión Completada", "⚠️ No se pudo convertir ningún archivo.")
        
        self.statusBar().showMessage(f"✅ Completado - {estadisticas['exitosos']} archivos")
        self.agregar_log("\n" + "=" * 70)
        self.agregar_log(f"✅ CONVERSIÓN FINALIZADA - {estadisticas['exitosos']} archivos")
        self.agregar_log("=" * 70)
    
    def mostrar_archivos(self, archivos):
        self.list_archivos.clear()
        for archivo in archivos:
            item = QListWidgetItem(Path(archivo).name)
            item.setToolTip(archivo)
            self.list_archivos.addItem(item)
    
    def agregar_log(self, mensaje):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if "❌" in mensaje or "Error" in mensaje:
            color = "#ff6b6b"
        elif "✅" in mensaje or "completada" in mensaje.lower():
            color = "#69db7c"
        elif "⚠️" in mensaje:
            color = "#ffd43b"
        elif "🔄" in mensaje or "Procesando" in mensaje:
            color = "#74c0fc"
        elif "🚀" in mensaje or "INICIANDO" in mensaje:
            color = "#da77f2"
        else:
            color = "#d4d4d4"
        
        html = f'<span style="color: #888;">[{timestamp}]</span> '
        html += f'<span style="color: {color};">{mensaje}</span>'
        
        self.text_log.append(html)
        self.text_log.moveCursor(QTextCursor.End)
    
    def actualizar_estado(self, original, salida):
        self.statusBar().showMessage(f"📄 {original} → {salida}")
    
    def limpiar_log(self):
        self.text_log.clear()
        self.progress_bar.setValue(0)
        self.list_archivos.clear()
        self.statusBar().showMessage("🧹 Log limpiado")
    
    def cerrar_aplicacion(self):
        if self.hilo_conversion and self.hilo_conversion.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirmar Salida",
                "Hay una conversión en curso. ¿Seguro que quieres salir?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.hilo_conversion.detener_conversion()
                self.hilo_conversion.wait()
                QApplication.quit()
        else:
            QApplication.quit()
    
    def closeEvent(self, event):
        self.cerrar_aplicacion()
        event.accept()

# ==================== PUNTO DE ENTRADA ====================
if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    app.setStyle('Fusion')
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(50, 50, 50))
    app.setPalette(palette)
    
    ventana = VentanaPrincipal()
    ventana.show()
    
    try:
        sys.exit(app.exec_())
    except AttributeError:
        sys.exit(app.exec())