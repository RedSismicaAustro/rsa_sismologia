import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    else:
        return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from obspy import read, UTCDateTime
from PyQt5.QtWidgets import QMessageBox, QFileDialog
from PyQt5 import uic, QtWidgets
from PyQt5.QtCore import QDate

from metodos_gestion import obtener_directorios, obtencion_hora
from rsa_io import lectura_archivo, escritura_archivo
from rsa_procesamiento import ordenar_y_eliminar_duplicados
from rsa_utilidades import extraccion

# Cargar la interfaz desde el archivo .ui directamente en esta instancia
ruta_ui = os.path.join(ruta_proyecto, "src", "ui", "caudales.ui")
qtCreatorFile = os.path.abspath(ruta_ui)

Ui_MainWindow, QtBassClass = uic.loadUiType(qtCreatorFile)


class Caudales(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.setWindowTitle("CAUDALES — Monitoreo de Filtraciones e Instrumentación")
        
        # === Variables internas y memoria ===
        self.directorio_trabajo = "G:/Mi unidad/DIA/"
        self.stream = None
        self.archivo = ""
        self.archivo_mseed = ""
        self.directorios = {}
        self.traza_id = ""
        self.marcas_usuario = []
        self.tr_segmento = None
        self.caudales = []
        self.eventos = []
        self.tiempo_centro_zoom = None
        self.evento_caudal_seleccionado = None

        # Conexiones de cambio de fechas y parámetros
        self.selector_fecha_inicio.dateChanged.connect(self.al_cambiar_periodo)
        self.selector_fecha_fin.dateChanged.connect(self.al_cambiar_periodo)
        self.selector_fecha_grafico.dateChanged.connect(self.al_cambiar_fecha_sismograma)
        
        self.combo_diezmado.clear()
        self.combo_diezmado.addItems(["1", "2", "5", "8", "10", "20", "50", "100"])
        self.combo_diezmado.setCurrentText("10")
        self.combo_diezmado.currentIndexChanged.connect(lambda: self.desplegar_grafico(silencioso=True))
        
        self.combo_traza.setMinimumWidth(180)
        self.combo_traza.currentIndexChanged.connect(lambda: self.desplegar_grafico(silencioso=True))
        self.Lbl_directorio.setText("Directorio de trabajo: G:/Mi unidad/DIA/")

        # === Formulario de configuración y eventos ===
        self.boton_directorio.clicked.connect(self.seleccionar_directorio_trabajo)
        self.boton_siguiente_ciclo.clicked.connect(self.ir_a_siguiente_ciclo_esperado)
        self.boton_guardar_marcas.clicked.connect(self.guardar_marcas)
        if hasattr(self, "boton_borrar_marcas"):
            self.boton_borrar_marcas.clicked.connect(self.borrar_marcas)
        self.boton_ignorar_caudal.clicked.connect(self.ignorar_punto_caudal_seleccionado)
        if hasattr(self, "boton_exportar_grafico"):
            self.boton_exportar_grafico.clicked.connect(self.abrir_dialogo_exportar_grafico)
        self.boton_salir.clicked.connect(self.close)
        
        # === Incrustar los 3 Lienzos de Matplotlib ===
        self.inicializar_lienzos_graficos()
        
        # Cargar base de datos de caudales y posicionarse automáticamente en la última marca
        self.cargar_caudales_y_posicionar_inicio()
        
        # Iniciar ventana maximizada
        self.showMaximized()

    def ordenar_caudales(self):
        """Ordena self.caudales cronológicamente por la fecha y hora del evento .sis."""
        def clave_fecha(fila):
            if not fila or len(fila) == 0:
                return datetime.min
            nom = str(fila[0]).strip().replace(".sis", "")
            if len(nom) == 13:
                nom = '20' + nom
            try:
                return datetime.strptime(nom, "%Y%m%d_%H%M%S")
            except Exception:
                return datetime.min

        self.caudales.sort(key=clave_fecha)

    def obtener_ultima_marca_confirmada(self):
        """Retorna la última marca confirmada (bandera == '1') registrada en self.caudales."""
        eventos = []
        for fila in self.caudales:
            if len(fila) >= 3 and str(fila[2]).strip() == "1":
                nom = str(fila[0]).strip().replace(".sis", "")
                if len(nom) == 13:
                    nom = '20' + nom
                try:
                    dt = datetime.strptime(nom, "%Y%m%d_%H%M%S")
                    eventos.append((dt, fila))
                except Exception:
                    pass
        if not eventos:
            return None
        eventos.sort(key=lambda x: x[0])
        dt_ult, fila_ult = eventos[-1]
        return {
            'dt': dt_ult,
            'nombre': str(fila_ult[0]).strip(),
            'caudal': int(fila_ult[1]) if len(fila_ult) > 1 and str(fila_ult[1]).isdigit() else 0,
            'fila': fila_ult
        }

    def sanear_caudales_duplicados(self):
        """
        Detecta y remueve de self.caudales registros duplicados con bandera 0 que fueron generados
        por sobre-marcado accidental a menos de 60 segundos de un evento confirmado válido.
        """
        if not self.caudales:
            return False

        eventos_validos_dt = []
        for fila in self.caudales:
            if len(fila) >= 3 and str(fila[2]).strip() == "1":
                nom = str(fila[0]).strip().replace(".sis", "")
                if len(nom) == 13:
                    nom = '20' + nom
                try:
                    dt = datetime.strptime(nom, "%Y%m%d_%H%M%S")
                    eventos_validos_dt.append(dt)
                except Exception:
                    pass

        filas_limpias = []
        filas_eliminadas = 0
        for fila in self.caudales:
            if len(fila) >= 3 and str(fila[2]).strip() == "0":
                nom = str(fila[0]).strip().replace(".sis", "")
                if len(nom) == 13:
                    nom = '20' + nom
                try:
                    dt = datetime.strptime(nom, "%Y%m%d_%H%M%S")
                    es_duplicado_accidental = any(abs((dt - dt_val).total_seconds()) <= 60 for dt_val in eventos_validos_dt)
                    if es_duplicado_accidental:
                        filas_eliminadas += 1
                        continue
                except Exception:
                    pass
            filas_limpias.append(fila)

        if filas_eliminadas > 0:
            print(f"[INFO] Saneamiento: se removieron {filas_eliminadas} registros duplicados de caudales.csv.")
            self.caudales = filas_limpias
            self.ordenar_caudales()
            archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
            try:
                escritura_archivo(archivo_caudales, self.caudales)
            except Exception as e:
                print(f"[ERROR] Error al guardar saneamiento de caudales.csv: {e}")
            return True
        return False

    def cargar_caudales_y_posicionar_inicio(self):
        """Carga caudales.csv, asegura el orden cronológico y posiciona todos los gráficos en la última marca confirmada."""
        archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
        if os.path.isfile(archivo_caudales):
            try:
                self.caudales = lectura_archivo(archivo_caudales)
                self.ordenar_caudales()
                self.sanear_caudales_duplicados()
            except Exception as e:
                print(f"[ERROR] Error al cargar caudales iniciales: {e}")
                self.caudales = []
        else:
            self.caudales = []

        hoy = QDate.currentDate()
        ultima_marca = self.obtener_ultima_marca_confirmada()

        if ultima_marca:
            dt_ult = ultima_marca['dt']
            qdate_ult = QDate(dt_ult.year, dt_ult.month, dt_ult.day)
            
            self.selector_fecha_grafico.blockSignals(True)
            self.selector_fecha_inicio.blockSignals(True)
            self.selector_fecha_fin.blockSignals(True)
            
            # Posicionar el sismograma en la fecha de la última marca confirmada
            self.selector_fecha_grafico.setDate(qdate_ult)
            
            # El periodo abarca desde 15 días antes de la última marca hasta la fecha actual
            self.selector_fecha_inicio.setDate(qdate_ult.addDays(-15))
            self.selector_fecha_fin.setDate(hoy)
            
            self.selector_fecha_grafico.blockSignals(False)
            self.selector_fecha_inicio.blockSignals(False)
            self.selector_fecha_fin.blockSignals(False)
            
            # Centrar el zoom exactamente en el instante de la última marca
            self.tiempo_centro_zoom = mdates.date2num(dt_ult)
        else:
            self.selector_fecha_inicio.setDate(hoy.addDays(-7))
            self.selector_fecha_fin.setDate(hoy)
            self.selector_fecha_grafico.setDate(hoy)
            self.tiempo_centro_zoom = None

        # Desplegar sismograma diario, zoom y serie histórica de caudales
        self.cargar_componentes_fecha()
        self.desplegar_grafico(silencioso=True)
        self.cargar_eventos_control(silencioso=True)
        self.graficar_caudales(silencioso=True)
        self.cargar_guia_operacion()

    def obtener_eventos_grafico_dia(self, fecha_grafico):
        """
        Retorna la lista de eventos para el día seleccionado, unificando caudales.csv y los
        eventos CONTROL del catálogo diario (evitando duplicados y garantizando visibilidad en pantalla).
        Cada elemento es un dict: {'nombre': str, 'dt': datetime, 'caudal': int, 'bandera': str}
        """
        eventos_dia = {}

        # 1. Prioridad: registros maestros en self.caudales
        for fila in self.caudales:
            if not fila or len(fila) == 0:
                continue
            nom_original = str(fila[0]).strip()
            nom_limpio = nom_original.replace(".sis", "")
            nom_14 = '20' + nom_limpio if len(nom_limpio) == 13 else nom_limpio
            try:
                dt_ev = datetime.strptime(nom_14, "%Y%m%d_%H%M%S")
            except Exception:
                continue

            if dt_ev.date() == fecha_grafico:
                caudal = int(fila[1]) if len(fila) > 1 and str(fila[1]).isdigit() else 0
                bandera = str(fila[2]).strip() if len(fila) > 2 else '1'
                eventos_dia[nom_original] = {
                    'nombre': nom_original,
                    'dt': dt_ev,
                    'caudal': caudal,
                    'bandera': bandera
                }

        # 2. Complementar con eventos CONTROL del catálogo diario self.eventos si existen
        caudales_confirmados = {f[0] for f in self.caudales if len(f) > 2 and f[2] == "1"}
        for evento in self.eventos:
            if len(evento) > 2 and str(evento[2]).strip().upper() == "CONTROL":
                nom_ev = str(evento[1]).strip()
                if nom_ev not in eventos_dia:
                    nom_limpio = nom_ev.replace(".sis", "")
                    nom_14 = '20' + nom_limpio if len(nom_limpio) == 13 else nom_limpio
                    try:
                        dt_ev = datetime.strptime(nom_14, "%Y%m%d_%H%M%S")
                    except Exception:
                        continue
                    if dt_ev.date() == fecha_grafico:
                        bandera = '1' if nom_ev in caudales_confirmados else '0'
                        eventos_dia[nom_ev] = {
                            'nombre': nom_ev,
                            'dt': dt_ev,
                            'caudal': 0,
                            'bandera': bandera
                        }

        # Retornar lista ordenada por tiempo
        lista_ordenada = list(eventos_dia.values())
        lista_ordenada.sort(key=lambda x: x['dt'])
        return lista_ordenada

    def inicializar_lienzos_graficos(self):
        """Inicializa los 3 lienzos Matplotlib con margen para unidades en caudales y alineación vertical."""
        # 1. Contenedor Superior: Serie Temporal de Caudales
        self.fig_caudales = Figure(figsize=(10, 2.0))
        self.fig_caudales.subplots_adjust(left=0.065, right=0.99, top=0.94, bottom=0.18)
        self.canvas_caudales = FigureCanvas(self.fig_caudales)
        self.toolbar_caudales = NavigationToolbar(self.canvas_caudales, self)
        self.toolbar_caudales.setMaximumHeight(24)
        self.ax_caudales = self.fig_caudales.add_subplot(111)
        self.ax_caudales.grid(True, linestyle='--', alpha=0.3)
        self.ax_caudales.yaxis.set_visible(True)
        self.ax_caudales.set_ylabel('Caudal\n(cm³/s)', fontsize=8, fontweight='bold')
        self.ax_caudales.tick_params(axis='y', labelsize=8, pad=2)
        self.ax_caudales.tick_params(axis='x', labelsize=7.5, pad=1)
        self.layout_grafico_caudales.addWidget(self.toolbar_caudales)
        self.layout_grafico_caudales.addWidget(self.canvas_caudales)

        # 2. Contenedor Medio: Sismograma Diario 24h
        self.fig_sismograma = Figure(figsize=(10, 2.0))
        self.fig_sismograma.subplots_adjust(left=0.065, right=0.99, top=0.96, bottom=0.16)
        self.canvas_sismograma = FigureCanvas(self.fig_sismograma)
        self.toolbar_sismograma = NavigationToolbar(self.canvas_sismograma, self)
        self.toolbar_sismograma.setMaximumHeight(24)
        self.ax_sismograma = self.fig_sismograma.add_subplot(111)
        self.ax_sismograma.grid(True, linestyle='--', alpha=0.3)
        self.ax_sismograma.yaxis.set_visible(False)
        self.ax_sismograma.tick_params(axis='x', labelsize=7.5, pad=1)
        self.layout_grafico_sismograma.addWidget(self.toolbar_sismograma)
        self.layout_grafico_sismograma.addWidget(self.canvas_sismograma)

        # 3. Contenedor Inferior: Zoom de Forma de Onda para Marcado
        self.fig_zoom = Figure(figsize=(10, 2.5))
        self.fig_zoom.subplots_adjust(left=0.065, right=0.99, top=0.96, bottom=0.16)
        self.canvas_zoom = FigureCanvas(self.fig_zoom)
        self.toolbar_zoom = NavigationToolbar(self.canvas_zoom, self)
        self.toolbar_zoom.setMaximumHeight(24)
        self.ax_zoom = self.fig_zoom.add_subplot(111)
        self.ax_zoom.grid(True, linestyle='--', alpha=0.3)
        self.ax_zoom.yaxis.set_visible(False)
        self.ax_zoom.tick_params(axis='x', labelsize=7.5, pad=1)
        self.layout_grafico_zoom.addWidget(self.toolbar_zoom)
        self.layout_grafico_zoom.addWidget(self.canvas_zoom)

        # Conectar eventos de ratón en los 3 lienzos
        self.canvas_caudales.mpl_connect('button_press_event', self.al_hacer_clic_caudales)
        self.canvas_sismograma.mpl_connect('button_press_event', self.al_hacer_clic_sismograma)
        self.canvas_zoom.mpl_connect('button_press_event', self.al_hacer_clic_zoom)

        # Cargar cuadro de guía y diagnóstico
        self.cargar_guia_operacion()

    def verificar_senal_en_intervalo(self, dt_min, dt_max):
        """Comprueba si existen datos sísmicos registrados para CHA2 en el intervalo [dt_min, dt_max]."""
        try:
            fecha_str = dt_min.strftime("%Y%m%d")
            archivo_dia = os.path.join(self.directorio_trabajo, fecha_str + "000000")
            dirs = obtener_directorios(archivo_dia)
            ruta_mseed = os.path.join(dirs.get('Directorio_registros', ''), f"CHA2_{fecha_str}_000000.mseed")

            if not os.path.isfile(ruta_mseed):
                ruta_mseed = os.path.join(self.directorio_trabajo, "Datos Estaciones", "CHA2", f"CHA2_{fecha_str}_000000.mseed")
                if not os.path.isfile(ruta_mseed):
                    return False

            st = read(ruta_mseed, headonly=True)
            if not st:
                return False

            utc_min = UTCDateTime(dt_min)
            utc_max = UTCDateTime(dt_max)

            for tr in st:
                if tr.stats.starttime <= utc_max and tr.stats.endtime >= utc_min:
                    return True

            return False
        except Exception:
            return False

    def obtener_estado_bombeo_y_prediccion(self):
        """
        Calcula el estado de vigilancia del bombeo proyectando la próxima descarga
        a partir de la MODA de las últimas 10 mediciones confirmadas válidas (caudal > 0).
        """
        if not self.caudales:
            return None

        eventos_confirmados = []
        for fila in self.caudales:
            if len(fila) < 3 or str(fila[2]).strip() != "1":
                continue
            nom = str(fila[0]).strip()
            if len(nom) == 17:
                nom = '20' + nom
            try:
                dt = datetime.strptime(nom.replace(".sis", ""), "%Y%m%d_%H%M%S")
                caudal = int(fila[1]) if len(fila) > 1 and str(fila[1]).isdigit() else 0
                eventos_confirmados.append((dt, nom, caudal))
            except Exception:
                pass

        if not eventos_confirmados:
            return None

        eventos_confirmados.sort(key=lambda x: x[0])
        ultimo_dt, ultimo_nom, ultimo_caudal_fila = eventos_confirmados[-1]

        # Extraer los últimos hasta 10 caudales válidos confirmados (Caudal > 0)
        caudales_validos = [ev[2] for ev in eventos_confirmados if ev[2] > 0]
        ultimos_10 = caudales_validos[-10:] if caudales_validos else []

        if ultimos_10:
            from collections import Counter
            conteo = Counter(ultimos_10)
            max_frec = max(conteo.values())
            modas = [val for val, frec in conteo.items() if frec == max_frec]
            if len(modas) == 1:
                caudal_referencia = modas[0]
            else:
                caudal_referencia = int(np.median(ultimos_10))
        elif ultimo_caudal_fila > 0:
            caudal_referencia = ultimo_caudal_fila
        else:
            caudal_referencia = 450  # Valor nominal de referencia

        # Intervalo proyectado a partir de la moda de los últimos 10 registros
        delta_t_seg = int(1.214 * 3500000 / caudal_referencia)
        dt_esperado = ultimo_dt + timedelta(seconds=delta_t_seg)
        margen_seg = max(600, int(delta_t_seg * 0.10))  # Margen de tolerancia ±10% (mínimo 10 min)
        dt_min_esp = dt_esperado - timedelta(seconds=margen_seg)
        dt_max_esp = dt_esperado + timedelta(seconds=margen_seg)

        ahora = datetime.now()
        segundos_transcurridos = (ahora - ultimo_dt).total_seconds()
        horas_transcurridas = round(segundos_transcurridos / 3600.0, 1)
        ratio = segundos_transcurridos / delta_t_seg if delta_t_seg > 0 else 0

        # Paso 1: Evaluar si hay señal sísmica en el tiempo esperado
        hay_senal_en_esperado = self.verificar_senal_en_intervalo(dt_min_esp, dt_max_esp)

        if not hay_senal_en_esperado and dt_esperado < ahora:
            estado = "REINICIO_MEDICION"
        elif ratio > 1.5:
            estado = "ALERTA_CRITICA"
        elif ratio > 1.0:
            estado = "PENDIENTE"
        else:
            estado = "NORMAL"

        return {
            'ultimo_nombre': ultimo_nom,
            'ultimo_dt': ultimo_dt,
            'ultimo_caudal': caudal_referencia,
            'caudal_fila': ultimo_caudal_fila,
            'delta_t_seg': delta_t_seg,
            'delta_t_horas': round(delta_t_seg / 3600.0, 1),
            'dt_esperado': dt_esperado,
            'dt_min_esp': dt_min_esp,
            'dt_max_esp': dt_max_esp,
            'hay_senal_en_esperado': hay_senal_en_esperado,
            'horas_transcurridas': horas_transcurridas,
            'ratio': ratio,
            'estado': estado,
            'ciclos_pendientes': max(0, int(ratio))
        }

    def ir_a_siguiente_ciclo_esperado(self):
        """Salto guiado: calcula y enfoca automáticamente la fecha y hora estimada del próximo ciclo de bombeo."""
        pred = self.obtener_estado_bombeo_y_prediccion()
        if not pred:
            QMessageBox.warning(
                self,
                "Sin Registros Previos",
                "No hay suficientes eventos confirmados en caudales.csv para estimar el próximo ciclo."
            )
            return

        dt_esp = pred['dt_esperado']
        qdate = QDate(dt_esp.year, dt_esp.month, dt_esp.day)

        if self.selector_fecha_grafico.date() != qdate:
            self.selector_fecha_grafico.blockSignals(True)
            self.selector_fecha_grafico.setDate(qdate)
            self.selector_fecha_grafico.blockSignals(False)
            self.cargar_componentes_fecha()

        self.desplegar_grafico(silencioso=True)
        self.actualizar_grafico_zoom(centro_tiempo=mdates.date2num(dt_esp))
        self.cargar_guia_operacion()

    def cargar_guia_operacion(self):
        """Carga el panel integrado de diagnóstico de bombeo, alarma de inundación y guía de uso en HTML."""
        pred = self.obtener_estado_bombeo_y_prediccion()

        if pred:
            if pred['estado'] == "REINICIO_MEDICION":
                badge_bg = "#eff6ff"
                badge_color = "#1e40af"
                badge_border = "#93c5fd"
                titulo_estado = "🔄 REINICIO DE MEDICIÓN (Sin señal en ciclo esperado)"
                detalle_estado = f"No hubo señal a la hora prevista (~{pred['dt_esperado'].strftime('%H:%M')}). Coloca la <strong>Marca Base (Caudal=0)</strong> en la señal actual para reiniciar la serie."
            elif pred['estado'] == "ALERTA_CRITICA":
                badge_bg = "#fee2e2"
                badge_color = "#991b1b"
                badge_border = "#f87171"
                titulo_estado = "🚨 ALERTA CRÍTICA: RIESGO DE INUNDACIÓN"
                detalle_estado = f"Motor inactivo por <strong>{pred['horas_transcurridas']}h</strong> (~{pred['ciclos_pendientes']} ciclos sin bombeo)."
            elif pred['estado'] == "PENDIENTE":
                badge_bg = "#fef3c7"
                badge_color = "#92400e"
                badge_border = "#fcd34d"
                titulo_estado = "⚠️ AUDITORÍA PENDIENTE"
                detalle_estado = f"Próximo ciclo debió ocurrir hace {pred['horas_transcurridas']}h. Pulsa <em>'🎯 Ir a Siguiente Ciclo'</em>."
            else:
                badge_bg = "#dcfce7"
                badge_color = "#166534"
                badge_border = "#86efac"
                titulo_estado = "🟢 MONITOREO AL DÍA"
                detalle_estado = "Sistema de bombeo dentro del ciclo regular de operación."

            bloque_diagnostico = f"""
            <div style="background:{badge_bg}; border:1px solid {badge_border}; color:{badge_color}; padding:6px 8px; border-radius:5px; margin-bottom:8px; font-size:10.5px;">
                <p style="margin:0 0 3px 0; font-weight:bold; font-size:11px;">{titulo_estado}</p>
                <p style="margin:0 0 3px 0;">{detalle_estado}</p>
                <hr style="border:0; border-top:1px dashed {badge_border}; margin:4px 0;">
                <span style="font-size:10px;">
                    <strong>Último:</strong> {pred['ultimo_dt'].strftime('%Y-%m-%d %H:%M')} | <strong>Ref (Moda 10):</strong> {pred['ultimo_caudal']} L/s<br>
                    <strong>Intervalo:</strong> ~{pred['delta_t_horas']}h | <strong>Esperado:</strong> {pred['dt_esperado'].strftime('%Y-%m-%d %H:%M')}
                </span>
            </div>
            """
        else:
            bloque_diagnostico = """
            <div style="background:#f1f5f9; border:1px solid #cbd5e1; color:#475569; padding:5px 7px; border-radius:4px; margin-bottom:8px; font-size:10px;">
                ℹ️ Sin eventos confirmados para calcular predicción de ciclo.
            </div>
            """

        html = f"""
        <div style="font-family:'Segoe UI', Tahoma, sans-serif; font-size:11px; line-height:1.35; color:#1e293b;">
            {bloque_diagnostico}
            <p style="margin:0 0 4px 0; font-weight:bold; color:#0f766e; font-size:11px;">📋 Flujo de Operación Rápida:</p>
            <ol style="margin:0; padding-left:15px; font-size:10.5px;">
                <li style="margin-bottom:3px;"><strong>🎯 Salto Guiado</strong>: Pulsa <em>"Ir a Siguiente Ciclo"</em> para situar el zoom en el pulso previsto.</li>
                <li style="margin-bottom:3px;"><strong>Marcar Evento</strong>: En el zoom (franja sombreada), <u>clic derecho</u> para fijar 2 marcas rojas.</li>
                <li style="margin-bottom:3px;"><strong>Extraer</strong>: Pulsa <em>"Guardar marcas (.SIS)"</em> para registrar y saltar al siguiente.</li>
                <li style="margin-bottom:3px;"><strong>Descartar</strong>: <u>Clic derecho</u> en serie superior y pulsa <em>"🚫 Ignorar Punto"</em>.</li>
            </ol>
            <div style="margin-top:5px; padding:3px 5px; background:#f8fafc; border-radius:4px; font-size:9.5px; color:#64748b;">
                🟢 Confirmado (1) | 🔴 No confirmado (0) | 🟨 Zona Esperada
            </div>
            <div style="margin-top:6px; padding:5px 6px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:4px; font-size:9.8px; color:#1e40af; line-height:1.3;">
                <p style="margin:0 0 2px 0; font-weight:bold; color:#1e3a8a;">🛡️ Vigilante Residente (Segundo Plano):</p>
                • Ejecuta <strong>Vigilante_Caudales.bat</strong> para monitoreo continuo en bandeja.<br>
                • <em>Autoarranque Windows</em>: Presiona <strong>Win+R</strong>, escribe <strong>shell:startup</strong> y pega un acceso directo al .bat.
            </div>
        </div>
        """
        self.cuadro_guia.setHtml(html)

    def al_hacer_clic_caudales(self, event):
        """
        Maneja los clics en la serie superior de caudales:
        - Clic Izquierdo (1): Sincroniza fecha, carga sismograma 24h y enfoca zoom.
        - Clic Derecho (3): Resalta/selecciona el punto de caudal en rojo para su exclusión.
        """
        if not event.inaxes or event.xdata is None:
            return
        try:
            dt_click = mdates.num2date(event.xdata).replace(tzinfo=None)
            fecha_click = dt_click.date()
            tiempo_evento_cercano = event.xdata
            nombre_evento_cercano = None
            dt_min_diff = None

            # Buscar el punto de caudal confirmado más cercano al clic
            for fila in self.caudales:
                if len(fila) < 3 or str(fila[2]).strip() != "1":
                    continue
                try:
                    dt_ev = datetime.strptime(fila[0].replace(".sis", ""), "%Y%m%d_%H%M%S")
                    diff = abs((dt_ev - dt_click).total_seconds())
                    if dt_min_diff is None or diff < dt_min_diff:
                        dt_min_diff = diff
                        if diff <= 86400:
                            tiempo_evento_cercano = mdates.date2num(dt_ev)
                            nombre_evento_cercano = fila[0]
                            fecha_click = dt_ev.date()
                except Exception:
                    pass

            if event.button == 3:
                # Clic derecho: alternar selección para descartar
                if nombre_evento_cercano:
                    if self.evento_caudal_seleccionado == nombre_evento_cercano:
                        self.evento_caudal_seleccionado = None
                    else:
                        self.evento_caudal_seleccionado = nombre_evento_cercano
                    self.graficar_caudales(silencioso=True)
                return

            if event.button == 1:
                # Clic izquierdo: navegar a ese día y centrar zoom
                qdate = QDate(fecha_click.year, fecha_click.month, fecha_click.day)

                if self.selector_fecha_grafico.date() != qdate:
                    self.selector_fecha_grafico.blockSignals(True)
                    self.selector_fecha_grafico.setDate(qdate)
                    self.selector_fecha_grafico.blockSignals(False)
                    self.cargar_componentes_fecha()

                self.desplegar_grafico(silencioso=True)
                self.actualizar_grafico_zoom(centro_tiempo=tiempo_evento_cercano)
        except Exception as e:
            print(f"[ERROR] Error al procesar clic en caudales: {e}")

    def ignorar_punto_caudal_seleccionado(self):
        """Cambia la bandera a 0 del punto de caudal seleccionado en caudales.csv y actualiza cálculos."""
        if not self.evento_caudal_seleccionado:
            QMessageBox.information(
                self,
                "Sin Selección",
                "Haz clic derecho sobre un punto en el gráfico superior de caudales para resaltarlo en rojo antes de ignorar."
            )
            return

        evento_a_ignorar = self.evento_caudal_seleccionado
        encontrado = False

        for fila in self.caudales:
            if len(fila) > 0 and (fila[0] == evento_a_ignorar or fila[0] == evento_a_ignorar.replace('.sis', '')):
                if len(fila) > 2:
                    fila[2] = '0'
                else:
                    fila.append('0')
                encontrado = True
                break

        if encontrado:
            self.ordenar_caudales()
            archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
            escritura_archivo(archivo_caudales, self.caudales)
            
            self.evento_caudal_seleccionado = None
            self.graficar_caudales(silencioso=True)
            self.desplegar_grafico(silencioso=True, mantener_vista=True)
            self.cargar_guia_operacion()
            QMessageBox.information(
                self,
                "Punto Ignorado",
                f"La medición del evento {evento_a_ignorar} se ha puesto en bandera 0 y fue excluida de la gráfica."
            )
        else:
            QMessageBox.warning(self, "No encontrado", f"No se encontró el evento {evento_a_ignorar} en el catálogo.")

    def borrar_marcas(self):
        """
        Gestiona el borrado seguro con confirmación de decisión negativa (por defecto 'No, salir sin borrar'):
        - Si existen marcas de usuario en pantalla (rojas), permite eliminarlas del lienzo.
        - Si existe un evento seleccionado en la curva de caudales, permite eliminarlo de caudales.csv.
        """
        hay_marcas_pantalla = bool(self.marcas_usuario)
        hay_evento_seleccionado = bool(self.evento_caudal_seleccionado)

        if not hay_marcas_pantalla and not hay_evento_seleccionado:
            QMessageBox.information(
                self,
                "Sin Marcas para Borrar",
                "No hay marcas temporales activas en pantalla ni eventos seleccionados en la curva de caudales.\n\n"
                "• Para borrar marcas de pantalla: coloca marcas con clic derecho en el zoom.\n"
                "• Para borrar un registro guardado: haz clic derecho sobre su punto en la curva superior de caudales para seleccionarlo y luego presiona este botón."
            )
            return

        if hay_marcas_pantalla and hay_evento_seleccionado:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("Borrar Marcas / Registros")
            msg_box.setText(
                f"Tiene {len(self.marcas_usuario)} marca(s) temporal(es) en pantalla y el evento "
                f"'{self.evento_caudal_seleccionado}' seleccionado en la curva de caudales.\n\n"
                "¿Qué acción desea realizar?"
            )
            boton_cancelar = msg_box.addButton("No, salir sin borrar", QMessageBox.RejectRole)
            boton_pantalla = msg_box.addButton("Borrar marcas en pantalla", QMessageBox.ActionRole)
            boton_registro = msg_box.addButton("Eliminar registro de caudales.csv", QMessageBox.DestructiveRole)
            msg_box.setDefaultButton(boton_cancelar)
            msg_box.exec_()

            if msg_box.clickedButton() == boton_pantalla:
                self.limpiar_marcas_pantalla()
            elif msg_box.clickedButton() == boton_registro:
                self.eliminar_evento_caudal(self.evento_caudal_seleccionado)
            return

        if hay_marcas_pantalla:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Confirmar Borrado de Marcas")
            msg_box.setText(
                f"¿Desea borrar las {len(self.marcas_usuario)} marca(s) temporales activas en pantalla?\n\n"
                "Esta acción desmarcará la selección actual en el sismograma y zoom."
            )
            boton_cancelar = msg_box.addButton("No, salir sin borrar", QMessageBox.RejectRole)
            boton_borrar = msg_box.addButton("Sí, borrar marcas", QMessageBox.AcceptRole)
            msg_box.setDefaultButton(boton_cancelar)
            msg_box.exec_()

            if msg_box.clickedButton() == boton_borrar:
                self.limpiar_marcas_pantalla()
            return

        if hay_evento_seleccionado:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Confirmar Eliminación de Registro")
            msg_box.setText(
                f"¿Desea eliminar definitivamente el registro del evento '{self.evento_caudal_seleccionado}'?\n\n"
                "Esta acción removerá la medición de caudales.csv y de los catálogos del día."
            )
            boton_cancelar = msg_box.addButton("No, salir sin borrar", QMessageBox.RejectRole)
            boton_eliminar = msg_box.addButton("Sí, eliminar registro", QMessageBox.DestructiveRole)
            msg_box.setDefaultButton(boton_cancelar)
            msg_box.exec_()

            if msg_box.clickedButton() == boton_eliminar:
                self.eliminar_evento_caudal(self.evento_caudal_seleccionado)
            return

    def limpiar_marcas_pantalla(self):
        """Limpia las marcas temporales del usuario y refresca los lienzos gráficos."""
        self.marcas_usuario.clear()
        for line in list(self.ax_sismograma.lines):
            if line.get_color() == 'red' and line.get_linestyle() == '--':
                line.remove()
        self.canvas_sismograma.draw_idle()
        self.actualizar_grafico_zoom()

    def eliminar_evento_caudal(self, evento_nom):
        """Elimina permanentemente un evento de caudales.csv y de los catálogos diarios asociados."""
        if not evento_nom:
            return

        nom_base = str(evento_nom).strip().replace(".sis", "")
        # 1. Remover de self.caudales
        longitud_antes = len(self.caudales)
        self.caudales = [
            fila for fila in self.caudales
            if len(fila) == 0 or (str(fila[0]).strip().replace(".sis", "") != nom_base)
        ]
        eliminado_caudales = (len(self.caudales) < longitud_antes)

        # 2. Guardar caudales.csv ordenado
        self.ordenar_caudales()
        archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
        escritura_archivo(archivo_caudales, self.caudales)

        # 3. Remover del catálogo del día correspondiente
        nom_limpio = nom_base
        if len(nom_limpio) == 13:
            nom_limpio = '20' + nom_limpio
        try:
            ev_dt = datetime.strptime(nom_limpio, "%Y%m%d_%H%M%S")
            nombre_archivo_dia = ev_dt.strftime("%Y%m%d000000")
            dirs_dia = obtener_directorios(os.path.join(self.directorio_trabajo, nombre_archivo_dia))
            
            # Limpiar del archivo_csv del día
            archivo_csv_dia = dirs_dia.get('archivo_csv', '')
            if not os.path.isfile(archivo_csv_dia):
                archivo_csv_dia = os.path.join(self.directorio_trabajo, dirs_dia.get('archivo_csv', ''))
            if os.path.isfile(archivo_csv_dia):
                eventos_dia = lectura_archivo(archivo_csv_dia)
                eventos_dia_filtrados = [
                    ev for ev in eventos_dia
                    if len(ev) < 2 or str(ev[1]).strip().replace(".sis", "") != nom_base
                ]
                if len(eventos_dia_filtrados) < len(eventos_dia):
                    escritura_archivo(archivo_csv_dia, eventos_dia_filtrados)
                    if hasattr(self, 'archivo') and nombre_archivo_dia in self.archivo:
                        self.eventos = eventos_dia_filtrados

            # Limpiar del archivo_auxiliar del día
            archivo_aux_dia = dirs_dia.get('archivo_auxiliar', '')
            if not os.path.isfile(archivo_aux_dia):
                archivo_aux_dia = os.path.join(self.directorio_trabajo, dirs_dia.get('archivo_auxiliar', ''))
            if os.path.isfile(archivo_aux_dia):
                eventos_aux = lectura_archivo(archivo_aux_dia)
                eventos_aux_filtrados = [
                    ev for ev in eventos_aux
                    if len(ev) < 2 or str(ev[1]).strip().replace(".sis", "") != nom_base
                ]
                if len(eventos_aux_filtrados) < len(eventos_aux):
                    escritura_archivo(archivo_aux_dia, eventos_aux_filtrados)
        except Exception as e:
            print(f"[WARN] No se pudo depurar el evento de los catálogos diarios: {e}")

        self.evento_caudal_seleccionado = None
        self.graficar_caudales(silencioso=True)
        self.desplegar_grafico(silencioso=True, mantener_vista=True)
        self.cargar_guia_operacion()
        QMessageBox.information(
            self,
            "Registro Eliminado",
            f"El evento '{evento_nom}' ha sido eliminado exitosamente de caudales.csv y catálogos asociados."
        )

    def al_cambiar_periodo(self):
        """Sincroniza y actualiza automáticamente los caudales al modificar cualquier fecha del periodo."""
        self.cargar_eventos_control(silencioso=True)
        self.graficar_caudales(silencioso=True)

    def al_cambiar_fecha_sismograma(self):
        """Carga el registro del día y actualiza automáticamente el sismograma y zoom."""
        self.tiempo_centro_zoom = None
        self.cargar_componentes_fecha()
        self.desplegar_grafico(silencioso=True)

    def limpiar_graficos_sismograma(self, mensaje="Registro MiniSEED no disponible para esta fecha"):
        """Limpia los lienzos del sismograma y zoom mostrando un mensaje no invasivo de estado."""
        self.ax_sismograma.clear()
        self.ax_sismograma.yaxis.set_visible(False)
        self.ax_sismograma.text(0.5, 0.5, mensaje, horizontalalignment='center',
                                verticalalignment='center', transform=self.ax_sismograma.transAxes,
                                color='#64748b', fontsize=8.5)
        self.canvas_sismograma.draw_idle()

        self.ax_zoom.clear()
        self.ax_zoom.yaxis.set_visible(False)
        self.ax_zoom.text(0.5, 0.5, "Sin datos de forma de onda", horizontalalignment='center',
                          verticalalignment='center', transform=self.ax_zoom.transAxes,
                          color='#64748b', fontsize=8.5)
        self.canvas_zoom.draw_idle()

    def seleccionar_directorio_trabajo(self):
        """Permite al usuario seleccionar el directorio base de trabajo."""
        folderpath = QFileDialog.getExistingDirectory(self, 'Selecciona el directorio de trabajo')
        if folderpath:
            if not folderpath.endswith('/'):
                folderpath += '/'
            self.directorio_trabajo = folderpath
            self.Lbl_directorio.setText(f"Directorio: {self.directorio_trabajo}")
            self.al_cambiar_fecha_sismograma()
            self.al_cambiar_periodo()

    def cargar_componentes_fecha(self):
        """Carga el registro MiniSEED del día seleccionado con contención de errores si no existe."""
        fecha = self.selector_fecha_grafico.date()
        self.archivo_mseed = f"CHA2_{fecha.toString('yyyyMMdd')}_000000.mseed"
        self.archivo = os.path.join(self.directorio_trabajo, fecha.toString("yyyyMMdd") + "000000")
        self.directorios = obtener_directorios(self.archivo)
        ruta_archivo = os.path.join(self.directorios.get('Directorio_registros', ''), self.archivo_mseed)
        
        self.stream = None
        if os.path.isfile(ruta_archivo):
            try:
                self.stream = read(ruta_archivo)
                self.cargar_componentes(self.stream)
            except Exception as e:
                print(f"[ERROR] Error al leer MiniSEED {ruta_archivo}: {e}")
                self.stream = None
                self.combo_traza.blockSignals(True)
                self.combo_traza.clear()
                self.combo_traza.blockSignals(False)
                self.limpiar_graficos_sismograma(f"Error de lectura en {self.archivo_mseed}")
        else:
            print(f"[INFO] {ruta_archivo} no existe.")
            self.stream = None
            self.combo_traza.blockSignals(True)
            self.combo_traza.clear()
            self.combo_traza.blockSignals(False)
            self.limpiar_graficos_sismograma("Corte de comunicación con estación CHA2")
        
        archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
        if os.path.isfile(archivo_caudales):
            try:
                self.caudales = lectura_archivo(archivo_caudales)
                self.ordenar_caudales()
            except Exception as e:
                print(f"[ERROR] Error al leer caudales.csv: {e}")
        else:
            self.caudales = []

    def cargar_componentes(self, stream):
        """Puebla el combo de trazas priorizando canales verticales Z o ENV."""
        self.combo_traza.blockSignals(True)
        self.combo_traza.clear()
        traza_vertical_index = -1
        for i, traza in enumerate(stream):
            self.combo_traza.addItem(traza.id)
            if traza.id.endswith("Z") or traza.id.endswith("ENV"):
                traza_vertical_index = i
        self.combo_traza.setCurrentIndex(traza_vertical_index if traza_vertical_index != -1 else 0)
        self.combo_traza.blockSignals(False)

    def desplegar_grafico(self, silencioso=False, mantener_vista=False):
        """Despliega el sismograma diario de 24h en el contenedor medio y actualiza el zoom inicial."""
        if not self.stream or not self.combo_traza.currentText():
            self.limpiar_graficos_sismograma("Registro MiniSEED no disponible para esta fecha")
            if not silencioso:
                QMessageBox.warning(self, "Archivo no cargado", "Debes seleccionar una fecha válida con registros disponibles.")
            return

        xlim_previo = self.ax_sismograma.get_xlim() if (mantener_vista and self.ax_sismograma.has_data()) else None
        ylim_previo = self.ax_sismograma.get_ylim() if (mantener_vista and self.ax_sismograma.has_data()) else None

        self.marcas_usuario.clear()
        self.traza_id = self.combo_traza.currentText()
        trazas_sel = self.stream.select(id=self.traza_id)
        if not trazas_sel:
            self.limpiar_graficos_sismograma(f"Traza {self.traza_id} no disponible")
            if not silencioso:
                QMessageBox.warning(self, "Traza no encontrada", f"No se encontró la traza {self.traza_id} en el registro.")
            return
        tr = trazas_sel[0]

        fecha_grafico = self.selector_fecha_grafico.date().toPyDate()
        hora_inicio = datetime(fecha_grafico.year, fecha_grafico.month, fecha_grafico.day)

        self.tr_segmento = tr.copy()
        try:
            factor_diezmado = int(self.combo_diezmado.currentText())
        except Exception:
            factor_diezmado = 10

        if factor_diezmado > 1:
            self.tr_segmento.decimate(factor_diezmado, no_filter=True)

        tiempo = self.tr_segmento.times("matplotlib")
        datos = self.tr_segmento.data

        self.ax_sismograma.clear()
        self.ax_sismograma.plot(tiempo, datos, linewidth=0.7, color='navy')
        self.ax_sismograma.yaxis.set_visible(False)
        self.ax_sismograma.grid(True, linestyle='--', alpha=0.3)

        # === Eventos del día (unificando caudales.csv y catálogo diario) ===
        archivo_csv_dia = self.directorios.get('archivo_csv', '')
        if os.path.isfile(archivo_csv_dia):
            self.eventos = lectura_archivo(archivo_csv_dia)
        else:
            self.eventos = []

        eventos_dia = self.obtener_eventos_grafico_dia(fecha_grafico)
        max_valor = float(datos.max()) if len(datos) > 0 else 1.0

        primer_evento_dt = None
        for ev in eventos_dia:
            try:
                dt_evento = ev['dt']
                if primer_evento_dt is None:
                    primer_evento_dt = dt_evento
                tiempo_relativo = mdates.date2num(dt_evento)
                
                es_confirmado = (ev['bandera'] == '1')
                color_linea = '#16a34a' if es_confirmado else '#dc2626'
                estilo_linea = '-' if es_confirmado else ':'
                ancho_linea = 1.3 if es_confirmado else 1.0
                
                texto_etiqueta = f"{ev['nombre']} ({ev['caudal']} cm³/s)" if (es_confirmado and ev['caudal'] > 0) else ev['nombre']
                
                self.ax_sismograma.axvline(x=tiempo_relativo, color=color_linea, linestyle=estilo_linea, linewidth=ancho_linea, alpha=0.85)
                self.ax_sismograma.text(tiempo_relativo, max_valor * 0.92, texto_etiqueta, rotation=90,
                                        fontsize=6.5, verticalalignment='top', color=color_linea, fontweight='bold')
            except Exception as e:
                print(f"Error al graficar evento del día en sismograma: {ev} → {e}")

        # === Zona Predictiva de Bombeo (Ciclo Esperado) ===
        pred = self.obtener_estado_bombeo_y_prediccion()
        if pred:
            dt_esp = pred['dt_esperado']
            dt_min_esp = pred['dt_min_esp']
            dt_max_esp = pred['dt_max_esp']
            inicio_dia = datetime(fecha_grafico.year, fecha_grafico.month, fecha_grafico.day, 0, 0, 0)
            fin_dia = datetime(fecha_grafico.year, fecha_grafico.month, fecha_grafico.day, 23, 59, 59)
            if not (dt_max_esp < inicio_dia or dt_min_esp > fin_dia):
                t_min_esp_num = mdates.date2num(dt_min_esp)
                t_max_esp_num = mdates.date2num(dt_max_esp)
                t_esp_num = mdates.date2num(dt_esp)
                color_franja = '#fca5a5' if pred['estado'] == 'ALERTA_CRITICA' else '#fef08a'
                color_borde = '#dc2626' if pred['estado'] == 'ALERTA_CRITICA' else '#d97706'
                self.ax_sismograma.axvspan(t_min_esp_num, t_max_esp_num, color=color_franja, alpha=0.4, linestyle='--', edgecolor=color_borde)
                self.ax_sismograma.axvline(x=t_esp_num, color=color_borde, linestyle='--', linewidth=1.2, alpha=0.85)
                self.ax_sismograma.text(t_esp_num, max_valor * 0.75, f"⏳ Ciclo Esperado (~{pred['ultimo_caudal']} L/s)",
                                        rotation=90, fontsize=6.8, verticalalignment='bottom', color=color_borde, fontweight='bold')

        self.ax_sismograma.tick_params(axis='x', labelsize=7.5, pad=1)
        self.ax_sismograma.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        if xlim_previo is not None:
            self.ax_sismograma.set_xlim(xlim_previo)
        if ylim_previo is not None:
            self.ax_sismograma.set_ylim(ylim_previo)
        self.fig_sismograma.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.16)
        self.canvas_sismograma.draw_idle()

        # Actualizar la vista de Zoom preservando la posición actual del pico
        if mantener_vista and self.tiempo_centro_zoom is not None:
            centro_zoom = self.tiempo_centro_zoom
        elif self.tiempo_centro_zoom is not None:
            dt_centro = mdates.num2date(self.tiempo_centro_zoom).replace(tzinfo=None)
            if dt_centro.date() == fecha_grafico:
                centro_zoom = self.tiempo_centro_zoom
            else:
                centro_zoom = mdates.date2num(eventos_dia[-1]['dt']) if eventos_dia else (tiempo[0] + (tiempo[-1] - tiempo[0]) / 2.0)
        else:
            centro_zoom = mdates.date2num(eventos_dia[-1]['dt']) if eventos_dia else (tiempo[0] + (tiempo[-1] - tiempo[0]) / 2.0)
        self.actualizar_grafico_zoom(centro_tiempo=centro_zoom)

    def actualizar_grafico_zoom(self, centro_tiempo=None):
        """Actualiza el contenedor inferior con la forma de onda ampliada alrededor de centro_tiempo."""
        if not self.stream or not self.combo_traza.currentText():
            return

        trazas_sel = self.stream.select(id=self.combo_traza.currentText())
        if not trazas_sel:
            return
        tr_original = trazas_sel[0]

        if centro_tiempo is not None:
            self.tiempo_centro_zoom = centro_tiempo

        if self.tiempo_centro_zoom is None:
            fecha_grafico = self.selector_fecha_grafico.date().toPyDate()
            dt_base = datetime(fecha_grafico.year, fecha_grafico.month, fecha_grafico.day, 12, 0, 0)
            self.tiempo_centro_zoom = mdates.date2num(dt_base)

        # Ventana de zoom de 20 minutos (±10 min)
        ventana_dias = 20.0 / 1440.0
        t_min = self.tiempo_centro_zoom - (ventana_dias / 2.0)
        t_max = self.tiempo_centro_zoom + (ventana_dias / 2.0)

        dt_min = mdates.num2date(t_min).replace(tzinfo=None)
        dt_max = mdates.num2date(t_max).replace(tzinfo=None)

        utc_min = UTCDateTime(dt_min)
        utc_max = UTCDateTime(dt_max)
        tr_zoom = tr_original.slice(utc_min, utc_max)

        self.ax_zoom.clear()
        self.ax_zoom.yaxis.set_visible(False)
        self.ax_zoom.grid(True, linestyle='--', alpha=0.3)

        if len(tr_zoom.data) > 0:
            tiempo_zoom = tr_zoom.times("matplotlib")
            datos_zoom = tr_zoom.data
            self.ax_zoom.plot(tiempo_zoom, datos_zoom, color='teal', linewidth=1.0)
            self.ax_zoom.set_xlim(t_min, t_max)
            max_zoom = float(datos_zoom.max()) if len(datos_zoom) > 0 else 1.0
            min_zoom = float(datos_zoom.min()) if len(datos_zoom) > 0 else -1.0
            rango = max_zoom - min_zoom if max_zoom != min_zoom else 1.0
            self.ax_zoom.set_ylim(min_zoom - 0.05 * rango, max_zoom + 0.05 * rango)
        else:
            self.ax_zoom.text(0.5, 0.5, "Sin datos en intervalo de zoom",
                              horizontalalignment='center', verticalalignment='center', transform=self.ax_zoom.transAxes, fontsize=8)

        # === Zona Predictiva de Bombeo en el Zoom ===
        pred = self.obtener_estado_bombeo_y_prediccion()
        if pred:
            t_min_esp = mdates.date2num(pred['dt_min_esp'])
            t_max_esp = mdates.date2num(pred['dt_max_esp'])
            t_esp = mdates.date2num(pred['dt_esperado'])
            if max(t_min, t_min_esp) <= min(t_max, t_max_esp):
                color_franja = '#fca5a5' if pred['estado'] == 'ALERTA_CRITICA' else '#fef08a'
                color_borde = '#dc2626' if pred['estado'] == 'ALERTA_CRITICA' else '#d97706'
                self.ax_zoom.axvspan(max(t_min, t_min_esp), min(t_max, t_max_esp),
                                     color=color_franja, alpha=0.35, linestyle='--', edgecolor=color_borde)
                if t_min <= t_esp <= t_max:
                    self.ax_zoom.axvline(x=t_esp, color=color_borde, linestyle='--', linewidth=1.3, alpha=0.9)
                    self.ax_zoom.text(t_esp, self.ax_zoom.get_ylim()[1] * 0.75, "⏳ Pulso Esperado",
                                      rotation=90, fontsize=6.8, verticalalignment='bottom', color=color_borde, fontweight='bold')

        # Dibujar marcas de usuario activas en el zoom
        for marca in self.marcas_usuario:
            self.ax_zoom.axvline(marca, color='red', linestyle='--', linewidth=1.8)

        # Dibujar marcas de eventos en el zoom
        eventos_dia_zoom = self.obtener_eventos_grafico_dia(dt_min.date())
        for ev in eventos_dia_zoom:
            try:
                t_ev = mdates.date2num(ev['dt'])
                if t_min <= t_ev <= t_max:
                    es_confirmado = (ev['bandera'] == '1')
                    color_linea = '#16a34a' if es_confirmado else '#dc2626'
                    estilo_linea = '-' if es_confirmado else ':'
                    ancho_linea = 1.4 if es_confirmado else 1.0
                    
                    texto_etiqueta = f"{ev['nombre']} ({ev['caudal']} cm³/s)" if (es_confirmado and ev['caudal'] > 0) else ev['nombre']
                    
                    self.ax_zoom.axvline(x=t_ev, color=color_linea, linestyle=estilo_linea, linewidth=ancho_linea, alpha=0.9)
                    self.ax_zoom.text(t_ev, self.ax_zoom.get_ylim()[1] * 0.88, texto_etiqueta, rotation=90,
                                      fontsize=6.8, verticalalignment='top', color=color_linea, fontweight='bold')
            except Exception as e:
                print(f"Error al graficar evento en zoom: {ev} → {e}")

        self.ax_zoom.tick_params(axis='x', labelsize=7.5, pad=1)
        self.ax_zoom.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig_zoom.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.16)
        self.canvas_zoom.draw_idle()

    def al_hacer_clic_sismograma(self, event):
        """Maneja los clics en el sismograma de 24h: Izquierdo=Centrar Zoom, Derecho=Marcas."""
        if not event.inaxes or not self.stream:
            return
        if event.button == 1:
            self.actualizar_grafico_zoom(centro_tiempo=event.xdata)
        elif event.button == 3:
            self.gestionar_marca_tiempo(event.xdata)

    def al_hacer_clic_zoom(self, event):
        """Maneja los clics en el contenedor de zoom: Derecho=Colocar/Quitar marcas."""
        if not event.inaxes or not self.stream:
            return
        if event.button == 3:
            self.gestionar_marca_tiempo(event.xdata)

    def gestionar_marca_tiempo(self, tiempo_click):
        """Agrega o elimina una marca temporal roja (máximo 2) y sincroniza ambos gráficos."""
        tolerancia = 2.0 / 86400.0  # 2 segundos de tolerancia para desmarcar
        marca_a_eliminar = None
        for marca in self.marcas_usuario:
            if abs(marca - tiempo_click) < tolerancia:
                marca_a_eliminar = marca
                break

        if marca_a_eliminar is not None:
            self.marcas_usuario.remove(marca_a_eliminar)
        else:
            if len(self.marcas_usuario) < 2:
                self.marcas_usuario.append(tiempo_click)
            else:
                self.marcas_usuario[1] = tiempo_click

        # Redibujar marcas en el sismograma 24h
        for line in list(self.ax_sismograma.lines):
            if line.get_color() == 'red' and line.get_linestyle() == '--':
                line.remove()
        for marca in self.marcas_usuario:
            self.ax_sismograma.axvline(marca, color='red', linestyle='--', linewidth=1.5)
        self.canvas_sismograma.draw_idle()

        # Redibujar marcas en el Zoom
        self.actualizar_grafico_zoom()

    def guardar_marcas(self):
        """Extrae la ventana seleccionada, actualiza catálogos y preserva la vista actual de trabajo."""
        if not self.stream:
            QMessageBox.warning(
                self,
                "Registro No Consolidado",
                "No existe registro MiniSEED cargado para este día. Debe procesarse primero el día desde el módulo de consolidación."
            )
            return

        if len(self.marcas_usuario) != 2:
            QMessageBox.warning(self, "Marcas Incompletas", "Debes seleccionar exactamente 2 marcas con clic derecho en el gráfico de zoom.")
            return

        marcas_ordenadas = sorted(self.marcas_usuario)
        marca_dt_inicio = mdates.num2date(marcas_ordenadas[0]).replace(tzinfo=None)
        marca_dt_fin = mdates.num2date(marcas_ordenadas[1]).replace(tzinfo=None)
        
        tiempo_inicio = int((marca_dt_inicio - datetime(marca_dt_inicio.year, marca_dt_inicio.month, marca_dt_inicio.day)).total_seconds())
        tiempo_fin = int((marca_dt_fin - datetime(marca_dt_fin.year, marca_dt_fin.month, marca_dt_fin.day)).total_seconds())
        
        archivo_auxiliar = self.directorios.get('archivo_auxiliar', '')
        if not archivo_auxiliar:
            QMessageBox.warning(self, "Error", "No se determinó la ruta del archivo auxiliar del día.")
            return

        eventos_auxiliar = lectura_archivo(archivo_auxiliar) if os.path.isfile(archivo_auxiliar) else []
        tiempo = obtencion_hora(self.archivo)
        fecha_real = tiempo + tiempo_inicio
        nombre_sis = fecha_real.strftime('%Y%m%d_%H%M%S.sis')
        dt_nuevo = datetime.strptime(nombre_sis.replace(".sis", ""), "%Y%m%d_%H%M%S")

        # 1. Detección preventiva de pulsos ya marcados (mismo ciclo de descarga de la bomba)
        evento_existente_cercano = None
        distancia_minima_seg = 999999
        for fila in self.caudales:
            if not fila or len(fila) == 0:
                continue
            nom_fila = str(fila[0]).strip().replace(".sis", "")
            nom_norm = '20' + nom_fila if len(nom_fila) == 13 else nom_fila
            try:
                dt_fila = datetime.strptime(nom_norm, "%Y%m%d_%H%M%S")
                dist_seg = abs((dt_nuevo - dt_fila).total_seconds())
                if dist_seg < 1800:  # Menor a 30 minutos (mismo pulso de descarga de la bomba)
                    if dist_seg < distancia_minima_seg:
                        distancia_minima_seg = dist_seg
                        evento_existente_cercano = (dt_fila, fila)
            except Exception:
                pass

        nom_reemplazar = None
        if evento_existente_cercano:
            dt_exist, fila_exist = evento_existente_cercano
            nom_exist = str(fila_exist[0]).strip()
            caudal_exist = fila_exist[1] if len(fila_exist) > 1 else '0'
            dif_seg = int(distancia_minima_seg)
            minutos = round(dif_seg / 60.0, 1)

            msg = (
                f"Ya existe una marca registrada para este pulso de descarga:\n\n"
                f"• Evento existente: {nom_exist}\n"
                f"• Caudal actual: {caudal_exist} cm³/s\n"
                f"• Diferencia de tiempo: {dif_seg} s ({minutos} min)\n\n"
                f"¿Deseas REEMPLAZAR la marca existente con la nueva posición seleccionada?\n\n"
                f"(Al aceptar se actualizará la posición manteniendo el cálculo de caudal correcto respecto al ciclo anterior)."
            )
            resp = QMessageBox.question(self, "Pulso Ya Registrado", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
            nom_reemplazar = nom_exist

        # 2. Calcular caudal respecto al último evento confirmado previo
        eventos_confirmados_previos = []
        for fila in self.caudales:
            if len(fila) >= 3 and str(fila[2]).strip() == "1":
                nom = str(fila[0]).strip()
                if nom_reemplazar and (nom == nom_reemplazar or nom.replace('.sis', '') == nom_reemplazar.replace('.sis', '')):
                    continue  # No comparar contra sí mismo al reemplazar
                nom_norm = '20' + nom if len(nom) == 17 else nom
                try:
                    dt_prev = datetime.strptime(nom_norm.replace(".sis", ""), "%Y%m%d_%H%M%S")
                    if dt_prev < dt_nuevo:
                        eventos_confirmados_previos.append((dt_prev, fila))
                except Exception:
                    pass

        caudal_nuevo = 0
        if eventos_confirmados_previos:
            eventos_confirmados_previos.sort(key=lambda x: x[0])
            dt_ultimo = eventos_confirmados_previos[-1][0]
            segundos = int((dt_nuevo - dt_ultimo).total_seconds())
            if segundos > 0:
                if segundos < 600:
                    QMessageBox.warning(
                        self,
                        "Intervalo Anómalo",
                        f"El intervalo respecto al ciclo anterior es de solo {segundos} segundos (< 10 min).\n"
                        f"Esto generaría un caudal anómalo.\n\n"
                        f"Operación cancelada para preservar la integridad del registro."
                    )
                    return
                caudal_nuevo = int(1.214 * 3500000 / segundos)

        # 3. Actualizar catálogo auxiliar y matriz de eventos del día
        n_evento = 0
        tipo_evento = 'CONTROL'
        ahora = datetime.now()
        estaciones = "CHA231000000"
        
        if nom_reemplazar:
            eventos_auxiliar = [ev for ev in eventos_auxiliar if len(ev) < 2 or ev[1] != nom_reemplazar]
            
        evento_auxiliar = (n_evento, nombre_sis, tipo_evento, ahora, tiempo_inicio, tiempo_fin, 'RSA', estaciones, 'Caudales')
        eventos_auxiliar.append(evento_auxiliar)
        escritura_archivo(archivo_auxiliar, eventos_auxiliar)

        archivo_csv = self.directorios.get('archivo_csv', '')
        if os.path.isfile(archivo_csv):
            self.eventos = lectura_archivo(archivo_csv)
        else:
            self.eventos = []

        if nom_reemplazar:
            self.eventos = [ev for ev in self.eventos if len(ev) < 2 or ev[1] != nom_reemplazar]

        solo_eventos = [fila[1] for fila in self.eventos if len(fila) > 1]
        for i, ev_aux in enumerate(eventos_auxiliar):
            evento = extraccion(ev_aux, solo_eventos, self.archivo, False)
            if evento is not None:
                self.eventos.append(evento)
                
        self.eventos = ordenar_y_eliminar_duplicados(self.eventos, 1, False)
        escritura_archivo(archivo_csv, self.eventos)

        # 4. Registrar o actualizar en self.caudales (bandera = '1')
        if nom_reemplazar:
            for fila in self.caudales:
                if len(fila) > 0 and (fila[0] == nom_reemplazar or fila[0] == nom_reemplazar.replace('.sis', '')):
                    fila[0] = nombre_sis
                    fila[1] = str(caudal_nuevo)
                    if len(fila) > 2:
                        fila[2] = '1'
                    else:
                        fila.append('1')
                    break
        else:
            evento_en_caudales = False
            for fila in self.caudales:
                if len(fila) > 0 and (fila[0] == nombre_sis or fila[0] == nombre_sis.replace('.sis', '')):
                    fila[1] = str(caudal_nuevo)
                    if len(fila) > 2:
                        fila[2] = '1'
                    else:
                        fila.append('1')
                    evento_en_caudales = True
                    break
            if not evento_en_caudales:
                self.caudales.append([nombre_sis, str(caudal_nuevo), "1"])

        # Ordenar cronológicamente y guardar
        self.ordenar_caudales()
        archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
        escritura_archivo(archivo_caudales, self.caudales)
        
        # Limpiar marcas y redibujar preservando el encuadre actual del sismograma y zoom
        self.marcas_usuario.clear()
        self.tiempo_centro_zoom = mdates.date2num(dt_nuevo)
        self.desplegar_grafico(silencioso=True, mantener_vista=True)
        self.graficar_caudales(silencioso=True)
        self.cargar_guia_operacion()
        QMessageBox.information(self, "Extracción Exitosa", f"Evento {nombre_sis} extraído, confirmado (Q = {caudal_nuevo} cm³/s) y graficado.")

    def graficar_caudales(self, silencioso=False):
        """Grafica la evolución temporal de caudales confirmados (bandera=1) en el contenedor superior de caudales."""
        if not self.caudales:
            if not silencioso:
                QMessageBox.warning(self, "Sin datos", "No hay datos de caudales cargados en caudales.csv.")
            return

        fechas = []
        valores = []
        nombres = []

        fecha_inicio = self.selector_fecha_inicio.date().toPyDate()
        fecha_fin = self.selector_fecha_fin.date().toPyDate()

        for fila in self.caudales:
            try:
                if len(fila) < 3 or str(fila[2]).strip() != "1":
                    continue

                fecha_evento = datetime.strptime(fila[0].replace(".sis", ""), "%Y%m%d_%H%M%S")

                if not (fecha_inicio <= fecha_evento.date() <= fecha_fin):
                    continue

                valor = int(fila[1]) if len(fila) > 1 and str(fila[1]).isdigit() else 0
                if valor <= 0:
                    continue  # Marca base sin cálculo de caudal; omitir de la curva

                fechas.append(fecha_evento)
                valores.append(valor)
                nombres.append(fila[0])
            except Exception as e:
                print(f"Error procesando fila de caudal {fila}: {e}")

        self.ax_caudales.clear()
        self.ax_caudales.yaxis.set_visible(False)
        self.ax_caudales.grid(True, linestyle='--', alpha=0.3)

        if not fechas or not valores:
            if not silencioso:
                QMessageBox.warning(self, "Sin datos válidos", "No se encontraron datos confirmados (bandera=1) en el rango seleccionado.")
            self.canvas_caudales.draw_idle()
            return

        self.ax_caudales.plot(fechas, valores, marker='o', markersize=2.5, linestyle='-', color='royalblue')

        # Resaltar en rojo si hay un punto seleccionado con clic derecho para ignorar
        if self.evento_caudal_seleccionado:
            for f_dt, v, ev_nom in zip(fechas, valores, nombres):
                if ev_nom == self.evento_caudal_seleccionado or ev_nom.replace('.sis', '') == self.evento_caudal_seleccionado.replace('.sis', ''):
                    self.ax_caudales.plot([f_dt], [v], marker='o', markersize=7, color='crimson', markeredgecolor='black', markeredgewidth=1.2, zorder=5)
                    break

        self.ax_caudales.set_ylim(bottom=0)
        self.ax_caudales.yaxis.set_visible(True)
        self.ax_caudales.set_ylabel('Caudal\n(cm³/s)', fontsize=8, fontweight='bold')
        self.ax_caudales.tick_params(axis='y', labelsize=8, pad=2)
        self.ax_caudales.tick_params(axis='x', labelsize=7.5, pad=1)
        self.ax_caudales.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        self.fig_caudales.subplots_adjust(left=0.065, right=0.99, top=0.94, bottom=0.18)
        self.canvas_caudales.draw_idle()

        # Guardar periodo graficado en caudales_periodo.csv
        ruta_salida = os.path.join(self.directorio_trabajo, "caudales_periodo.csv")
        try:
            t0 = mdates.date2num(fechas[0])
            with open(ruta_salida, "w", encoding="utf-8") as f:
                for fecha, valor in zip(fechas, valores):
                    t_rel_dias = mdates.date2num(fecha) - t0
                    f.write(f"{t_rel_dias},{valor}\n")
            print(f"[INFO] caudales_periodo.csv exportado correctamente.")
        except Exception as e:
            print(f"[ERROR] Error al exportar caudales_periodo.csv: {e}")

    def cargar_eventos_control(self, silencioso=False):
        """Busca eventos CONTROL en los catálogos diarios del periodo y los incorpora a caudales.csv."""
        archivo_csv = os.path.join(self.directorio_trabajo, "caudales.csv")
        if os.path.isfile(archivo_csv):
            try:
                self.caudales = lectura_archivo(archivo_csv)
            except Exception as e:
                if not silencioso:
                    QMessageBox.warning(self, "Error", f"No se pudo cargar caudales.csv: {str(e)}")
                return
        else:
            self.caudales = []

        caudales_set = {fila[0] for fila in self.caudales if fila}

        fecha_ini = self.selector_fecha_inicio.date().toPyDate()
        fecha_fin = self.selector_fecha_fin.date().toPyDate()
        eventos_control = set()
        fecha_actual = fecha_ini

        while fecha_actual <= fecha_fin:
            nombre_archivo = fecha_actual.strftime("%Y%m%d") + "000000"
            try:
                directorios_dia = obtener_directorios(os.path.join(self.directorio_trabajo, nombre_archivo))
                archivo_csv_eventos = directorios_dia.get('archivo_csv', '')
                if not os.path.isfile(archivo_csv_eventos):
                    archivo_csv_eventos = os.path.join(self.directorio_trabajo, directorios_dia.get('archivo_csv', ''))
                if os.path.isfile(archivo_csv_eventos):
                    lista_eventos = lectura_archivo(archivo_csv_eventos)
                    for fila in lista_eventos:
                        if len(fila) > 2 and str(fila[2]).strip().upper() == "CONTROL":
                            eventos_control.add(str(fila[1]).strip())
            except Exception as e:
                print(f"No se pudo procesar el día {fecha_actual}: {e}")
            fecha_actual += timedelta(days=1)

        eventos_control_ordenados = sorted(eventos_control)
        eventos_control_nuevos = []

        for evento in eventos_control_ordenados:
            if evento in caudales_set:
                continue

            try:
                nom = '20' + str(evento) if len(str(evento)) == 17 else str(evento)
                dt_ev = datetime.strptime(nom.replace(".sis", ""), "%Y%m%d_%H%M%S")
            except Exception:
                dt_ev = None

            caudal_ev = 0
            if dt_ev and self.caudales:
                dt_anterior = None
                for fila in self.caudales:
                    if len(fila) >= 3 and str(fila[2]).strip() == "1":
                        n = '20' + str(fila[0]) if len(str(fila[0])) == 17 else str(fila[0])
                        try:
                            d = datetime.strptime(n.replace(".sis", ""), "%Y%m%d_%H%M%S")
                            if d < dt_ev and (dt_anterior is None or d > dt_anterior):
                                dt_anterior = d
                        except Exception:
                            pass
                if dt_anterior:
                    seg = int((dt_ev - dt_anterior).total_seconds())
                    if seg > 0:
                        caudal_ev = int(1.214 * 3500000 / seg)

            nueva_fila = [evento, str(caudal_ev), "1"]
            eventos_control_nuevos.append(nueva_fila)
            self.caudales.append(nueva_fila)
            caudales_set.add(evento)

        if eventos_control_nuevos:
            try:
                self.ordenar_caudales()
                escritura_archivo(archivo_csv, self.caudales)
                if not silencioso:
                    QMessageBox.information(
                        self,
                        "Carga Exitosa",
                        f"Se agregaron {len(eventos_control_nuevos)} nuevos eventos CONTROL a caudales.csv."
                    )
                self.graficar_caudales(silencioso=True)
            except Exception as e:
                if not silencioso:
                    QMessageBox.critical(self, "Error", f"No se pudo guardar caudales.csv: {str(e)}")
        else:
            if not silencioso:
                QMessageBox.information(self, "Sin cambios", "No se encontraron nuevos eventos CONTROL en el periodo.")

    def closeEvent(self, event):
        """Asegura el guardado final de caudales.csv al cerrar la aplicación."""
        try:
            ruta_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
            if self.caudales:
                escritura_archivo(ruta_caudales, self.caudales)
                print("[INFO] caudales.csv guardado correctamente al cerrar.")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar caudales.csv al cerrar: {e}")
        event.accept()

    def abrir_dialogo_exportar_grafico(self):
        """Abre la ventana emergente para configurar el marco de caudales y exportar el gráfico en DXF."""
        fecha_ini = self.selector_fecha_inicio.date().toPyDate()
        fecha_fin = self.selector_fecha_fin.date().toPyDate()
        dialogo = DialogoExportarGraficoCaudales(
            self,
            self.caudales,
            fecha_ini,
            fecha_fin,
            self.directorio_trabajo
        )
        dialogo.exec_()


def calcular_paso_optimo(rango, divisiones_deseadas=7):
    """Calcula un paso estético (1, 2, 4, 5 o 10 x 10^k) para graduar los ejes."""
    if rango <= 0:
        return 1.0
    paso_bruto = rango / divisiones_deseadas
    potencia = 10 ** math.floor(math.log10(paso_bruto))
    fraccion = paso_bruto / potencia
    if fraccion <= 1.5:
        multiplicador = 1.0
    elif fraccion <= 3.0:
        multiplicador = 2.0
    elif fraccion <= 4.5:
        multiplicador = 4.0
    elif fraccion <= 7.5:
        multiplicador = 5.0
    else:
        multiplicador = 10.0
    return potencia * multiplicador


def calcular_ticks_eje_y(y0, y1, divisiones_deseadas=7):
    """Calcula los ticks y cotas principales entre y0 e y1."""
    rango = y1 - y0
    if rango <= 0:
        return [y0, y0 + 10.0], 10.0
    paso = calcular_paso_optimo(rango, divisiones_deseadas)
    num_div = round(rango / paso)
    if abs(rango - num_div * paso) < 1e-4:
        ticks = [round(y0 + i * paso, 4) for i in range(num_div + 1)]
    else:
        primer_tick = math.ceil(y0 / paso) * paso
        ticks = []
        t = primer_tick
        while t <= y1 + 1e-5:
            ticks.append(round(t, 4))
            t += paso
        if not ticks or ticks[0] > y0:
            ticks.insert(0, round(y0, 4))
        if ticks[-1] < y1:
            ticks.append(round(y1, 4))
    return ticks, paso


def escribir_dxf_caudales(ruta_dxf, fecha_inicio, fecha_final, y_min, y_max, puntos):
    """
    Genera un archivo DXF con la maquetación exacta para Caudal Total (cm³/s):
    - Marco rectangular superior con cuadrícula horizontal en cotas principales.
    - Líneas continuas verticales y compartimentos para los meses correspondientes.
    - Franja inferior sombreada en gris con nombres de mes centrados en blanco.
    - Eje vertical rotado a 90° con la etiqueta 'CAUDAL TOTAL (cm³/s)'.
    - Curva continua de caudales como LWPOLYLINE en capa CAUDAL.
    """
    NOMBRES_MESES = [
        "", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
        "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
    ]

    duracion_segundos = max((fecha_final - fecha_inicio).total_seconds(), 3600.0)
    x0 = 0.0
    x1 = duracion_segundos / 86400.0
    y0 = float(y_min)
    y1 = float(y_max)

    rango_x = x1 - x0
    rango_y = max(y1 - y0, 0.1)

    alto_barra_meses = max(rango_y * 0.075, 0.6)
    y_barra_fondo = y0 - alto_barra_meses

    margen_x = max(rango_x * 0.05, 0.5)
    margen_y = max(rango_y * 0.08, 0.5)

    contenido = []

    def agregar(codigo, valor):
        contenido.append(str(codigo))
        contenido.append(str(valor))

    def agregar_linea(xa, ya, xb, yb, capa="MARCO", color=7):
        agregar(0, "LINE")
        agregar(8, capa)
        agregar(62, color)
        agregar(10, f"{xa:.4f}")
        agregar(20, f"{ya:.4f}")
        agregar(30, "0.0")
        agregar(11, f"{xb:.4f}")
        agregar(21, f"{yb:.4f}")
        agregar(31, "0.0")

    def agregar_texto(x, y, texto, alto=0.25, rotacion=0.0, alineacion_h=0, alineacion_v=0, capa="TEXTOS", color=7):
        agregar(0, "TEXT")
        agregar(8, capa)
        agregar(62, color)
        agregar(10, f"{x:.4f}")
        agregar(20, f"{y:.4f}")
        agregar(30, "0.0")
        agregar(40, f"{alto:.4f}")
        agregar(1, str(texto))
        if rotacion != 0.0:
            agregar(50, f"{rotacion:.1f}")
        agregar(7, "STANDARD")
        if alineacion_h != 0 or alineacion_v != 0:
            agregar(72, alineacion_h)
            agregar(11, f"{x:.4f}")
            agregar(21, f"{y:.4f}")
            agregar(31, "0.0")
            agregar(73, alineacion_v)

    # 1. Encabezado DXF (AutoCAD R12 / AC1009: estándar universal para ODA y Vectorworks)
    agregar(0, "SECTION")
    agregar(2, "HEADER")
    agregar(9, "$ACADVER")
    agregar(1, "AC1009")
    agregar(9, "$LTSCALE")
    agregar(40, "1.0")
    agregar(0, "ENDSEC")

    # 2. Tablas
    agregar(0, "SECTION")
    agregar(2, "TABLES")

    # Tabla de tipos de línea
    agregar(0, "TABLE")
    agregar(2, "LTYPE")
    agregar(70, 1)
    agregar(0, "LTYPE")
    agregar(2, "CONTINUOUS")
    agregar(70, 0)
    agregar(3, "Solid line")
    agregar(72, 65)
    agregar(73, 0)
    agregar(40, "0.0")
    agregar(0, "ENDTAB")

    # Tabla de capas
    capas = [
        ("0", 7),
        ("MARCO", 7),
        ("MALLA_HORIZONTAL", 8),
        ("MALLA_MESES", 7),
        ("FONDO_MESES", 8),
        ("CAUDAL", 7),
        ("TEXTOS", 7),
        ("TEXTOS_MESES", 7)
    ]
    agregar(0, "TABLE")
    agregar(2, "LAYER")
    agregar(70, len(capas))
    for nom, col in capas:
        agregar(0, "LAYER")
        agregar(2, nom)
        agregar(70, 0)
        agregar(62, col)
        agregar(6, "CONTINUOUS")
    agregar(0, "ENDTAB")

    # Tabla de estilos de texto
    agregar(0, "TABLE")
    agregar(2, "STYLE")
    agregar(70, 1)
    agregar(0, "STYLE")
    agregar(2, "STANDARD")
    agregar(70, 0)
    agregar(40, "0.0")
    agregar(41, "1.0")
    agregar(50, "0.0")
    agregar(71, 0)
    agregar(42, "0.2")
    agregar(3, "ARIAL")
    agregar(0, "ENDTAB")

    agregar(0, "ENDSEC")

    # 3. Bloques (requerido por parsers ODA de Vectorworks)
    agregar(0, "SECTION")
    agregar(2, "BLOCKS")
    agregar(0, "ENDSEC")

    # 4. Entidades gráficas
    agregar(0, "SECTION")
    agregar(2, "ENTITIES")

    # Marco rectangular del gráfico
    agregar_linea(x0, y0, x1, y0, "MARCO", 7)
    agregar_linea(x1, y0, x1, y1, "MARCO", 7)
    agregar_linea(x1, y1, x0, y1, "MARCO", 7)
    agregar_linea(x0, y1, x0, y0, "MARCO", 7)

    # Marco de la barra de meses inferior
    agregar_linea(x0, y_barra_fondo, x1, y_barra_fondo, "MARCO", 7)
    agregar_linea(x0, y_barra_fondo, x0, y0, "MARCO", 7)
    agregar_linea(x1, y_barra_fondo, x1, y0, "MARCO", 7)

    # Ticks horizontales y cotas (Eje Y)
    ticks_y, paso_y = calcular_ticks_eje_y(y0, y1, 7)
    alto_texto_y = max(rango_y * 0.025, 0.18)
    for t_y in ticks_y:
        agregar_linea(x0, t_y, x1, t_y, "MALLA_HORIZONTAL", 8)
        agregar_linea(x0 - margen_x * 0.015, t_y, x0, t_y, "MARCO", 7)
        etiqueta_y = f"{int(round(t_y))}" if paso_y >= 1 and abs(t_y - round(t_y)) < 1e-4 else f"{t_y:.1f}"
        agregar_texto(x0 - margen_x * 0.025, t_y, etiqueta_y, alto=alto_texto_y, alineacion_h=2, alineacion_v=2, capa="TEXTOS", color=7)

    # Rótulo vertical del eje Y
    alto_rotulo_y = max(rango_y * 0.032, 0.25)
    agregar_texto(
        x0 - margen_x * 0.08,
        (y0 + y1) / 2.0,
        "CAUDAL TOTAL (cm3/s)",
        alto=alto_rotulo_y,
        alineacion_h=1,
        alineacion_v=2,
        rotacion=90.0,
        capa="TEXTOS",
        color=7
    )

    # Líneas verticales continuas en los cambios de mes
    cur_dia = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
    while cur_dia <= fecha_final:
        pos_x = (cur_dia - fecha_inicio).total_seconds() / 86400.0
        if x0 < pos_x < x1 and cur_dia.day == 1:
            agregar_linea(pos_x, y_barra_fondo, pos_x, y1, "MALLA_MESES", 7)
        cur_dia += timedelta(days=1)

    # Compartimentos y nombres de mes en la barra inferior
    cursor_mes = datetime(fecha_inicio.year, fecha_inicio.month, 1)
    alto_texto_mes = alto_barra_meses * 0.40
    while cursor_mes <= fecha_final:
        ini_seg = max(fecha_inicio, cursor_mes)
        if cursor_mes.month == 12:
            siguiente_mes = datetime(cursor_mes.year + 1, 1, 1)
        else:
            siguiente_mes = datetime(cursor_mes.year, cursor_mes.month + 1, 1)
        fin_seg = min(fecha_final, siguiente_mes)

        if fin_seg > ini_seg:
            xa = (ini_seg - fecha_inicio).total_seconds() / 86400.0
            xb = (fin_seg - fecha_inicio).total_seconds() / 86400.0

            # Fondo gris de cada compartimento de mes
            agregar(0, "SOLID")
            agregar(8, "FONDO_MESES")
            agregar(62, 8)
            agregar(10, f"{xa:.4f}")
            agregar(20, f"{y_barra_fondo:.4f}")
            agregar(30, "0.0")
            agregar(11, f"{xb:.4f}")
            agregar(21, f"{y_barra_fondo:.4f}")
            agregar(31, "0.0")
            agregar(12, f"{xa:.4f}")
            agregar(22, f"{y0:.4f}")
            agregar(32, "0.0")
            agregar(13, f"{xb:.4f}")
            agregar(23, f"{y0:.4f}")
            agregar(33, "0.0")

            # Nombre del mes centrado en mayúsculas
            nom_mes = NOMBRES_MESES[cursor_mes.month]
            x_centro = (xa + xb) / 2.0
            y_centro = (y_barra_fondo + y0) / 2.0
            agregar_texto(x_centro, y_centro, nom_mes, alto=alto_texto_mes, alineacion_h=1, alineacion_v=2, capa="TEXTOS_MESES", color=7)

        cursor_mes = siguiente_mes

    # Polilínea universal R12 de caudales
    puntos_caudal = []
    for dt, val in puntos:
        t_dias = (dt - fecha_inicio).total_seconds() / 86400.0
        puntos_caudal.append((t_dias, float(val)))

    if puntos_caudal:
        agregar(0, "POLYLINE")
        agregar(8, "CAUDAL")
        agregar(62, 7)
        agregar(66, 1)  # Banderín obligatorio: vértices siguen
        agregar(10, "0.0")
        agregar(20, "0.0")
        agregar(30, "0.0")
        agregar(70, 0)
        for px, py in puntos_caudal:
            agregar(0, "VERTEX")
            agregar(8, "CAUDAL")
            agregar(10, f"{px:.4f}")
            agregar(20, f"{py:.4f}")
            agregar(30, "0.0")
        agregar(0, "SEQEND")
        agregar(8, "CAUDAL")

    agregar(0, "ENDSEC")
    agregar(0, "EOF")

    with open(ruta_dxf, "w", encoding="ascii", errors="replace") as archivo:
        archivo.write("\n".join(contenido) + "\n")


class DialogoExportarGraficoCaudales(QtWidgets.QDialog):
    """
    Ventana emergente interactiva para configurar límites de caudal y exportar a DXF.
    """
    def __init__(self, padre, datos_caudales, fecha_ini_def, fecha_fin_def, dir_trabajo):
        super().__init__(padre)
        self.padre = padre
        self.datos_caudales = datos_caudales
        self.dir_trabajo = dir_trabajo
        self.setWindowTitle("Exportar Gráfico de Caudales — DXF")
        self.resize(520, 240)
        self.inicializar_interfaz(fecha_ini_def, fecha_fin_def)

    def inicializar_interfaz(self, fecha_ini_def, fecha_fin_def):
        layout = QtWidgets.QVBoxLayout(self)

        grupo_params = QtWidgets.QGroupBox("Parámetros del Marco y Período")
        layout_grid = QtWidgets.QGridLayout(grupo_params)

        layout_grid.addWidget(QtWidgets.QLabel("<b>Fecha Inicio:</b>"), 0, 0)
        self.selector_fecha_ini = QtWidgets.QDateEdit(self)
        self.selector_fecha_ini.setCalendarPopup(True)
        self.selector_fecha_ini.setDate(fecha_ini_def)
        layout_grid.addWidget(self.selector_fecha_ini, 0, 1)

        layout_grid.addWidget(QtWidgets.QLabel("<b>Fecha Fin:</b>"), 0, 2)
        self.selector_fecha_fin = QtWidgets.QDateEdit(self)
        self.selector_fecha_fin.setCalendarPopup(True)
        self.selector_fecha_fin.setDate(fecha_fin_def)
        layout_grid.addWidget(self.selector_fecha_fin, 0, 3)

        min_sug, max_sug = self.calcular_sugerencia_caudal(fecha_ini_def, fecha_fin_def)

        layout_grid.addWidget(QtWidgets.QLabel("<b>Caudal Mínimo [cm³/s]:</b>"), 1, 0)
        self.spin_caudal_min = QtWidgets.QDoubleSpinBox(self)
        self.spin_caudal_min.setRange(-1000.0, 100000.0)
        self.spin_caudal_min.setDecimals(1)
        self.spin_caudal_min.setSingleStep(5.0)
        self.spin_caudal_min.setValue(min_sug)
        layout_grid.addWidget(self.spin_caudal_min, 1, 1)

        layout_grid.addWidget(QtWidgets.QLabel("<b>Caudal Máximo [cm³/s]:</b>"), 1, 2)
        self.spin_caudal_max = QtWidgets.QDoubleSpinBox(self)
        self.spin_caudal_max.setRange(-1000.0, 100000.0)
        self.spin_caudal_max.setDecimals(1)
        self.spin_caudal_max.setSingleStep(5.0)
        self.spin_caudal_max.setValue(max_sug)
        layout_grid.addWidget(self.spin_caudal_max, 1, 3)

        self.selector_fecha_ini.dateChanged.connect(self.al_cambiar_fechas_dialogo)
        self.selector_fecha_fin.dateChanged.connect(self.al_cambiar_fechas_dialogo)

        layout.addWidget(grupo_params)

        layout_botones = QtWidgets.QHBoxLayout()

        self.boton_previsualizar = QtWidgets.QPushButton("👁️ Previsualizar Gráfico")
        self.boton_previsualizar.clicked.connect(self.previsualizar_grafico)
        layout_botones.addWidget(self.boton_previsualizar)

        self.boton_generar_dxf = QtWidgets.QPushButton("📐 Generar Archivo DXF")
        self.boton_generar_dxf.clicked.connect(self.generar_archivo_dxf)
        layout_botones.addWidget(self.boton_generar_dxf)

        self.boton_cerrar = QtWidgets.QPushButton("Cerrar")
        self.boton_cerrar.clicked.connect(self.close)
        layout_botones.addWidget(self.boton_cerrar)

        layout.addLayout(layout_botones)

    def al_cambiar_fechas_dialogo(self):
        f_ini = self.selector_fecha_ini.date().toPyDate()
        f_fin = self.selector_fecha_fin.date().toPyDate()
        if f_ini < f_fin:
            min_sug, max_sug = self.calcular_sugerencia_caudal(f_ini, f_fin)
            self.spin_caudal_min.setValue(min_sug)
            self.spin_caudal_max.setValue(max_sug)

    def calcular_sugerencia_caudal(self, f_ini, f_fin):
        valores = []
        for fila in self.datos_caudales:
            try:
                if len(fila) < 3 or str(fila[2]).strip() != "1":
                    continue
                dt = datetime.strptime(fila[0].replace(".sis", ""), "%Y%m%d_%H%M%S")
                if f_ini <= dt.date() <= f_fin:
                    val = float(fila[1])
                    if val > 0:
                        valores.append(val)
            except Exception:
                continue
        if valores:
            v_min = min(valores)
            v_max = max(valores)
            sug_min = math.floor(v_min / 10.0) * 10.0
            sug_max = math.ceil(v_max / 10.0) * 10.0
            if sug_max <= sug_min:
                sug_max = sug_min + 10.0
            return sug_min, sug_max
        return 120.0, 190.0

    def obtener_datos_filtrados(self):
        f_ini_date = self.selector_fecha_ini.date().toPyDate()
        f_fin_date = self.selector_fecha_fin.date().toPyDate()
        if f_ini_date >= f_fin_date:
            QMessageBox.warning(self, "Rango de fechas inválido", "La fecha de inicio debe ser anterior a la fecha de fin.")
            return None, None, None, None, []

        c_min = self.spin_caudal_min.value()
        c_max = self.spin_caudal_max.value()
        if c_min >= c_max:
            QMessageBox.warning(self, "Rango de caudal inválido", "El caudal mínimo debe ser menor que el caudal máximo.")
            return None, None, None, None, []

        f_ini_dt = datetime.combine(f_ini_date, datetime.min.time())
        f_fin_dt = datetime.combine(f_fin_date, datetime.max.time())

        puntos = []
        for fila in self.datos_caudales:
            try:
                if len(fila) < 3 or str(fila[2]).strip() != "1":
                    continue
                dt = datetime.strptime(fila[0].replace(".sis", ""), "%Y%m%d_%H%M%S")
                if f_ini_dt <= dt <= f_fin_dt:
                    val = float(fila[1])
                    if val > 0:
                        puntos.append((dt, val))
            except Exception:
                continue

        if not puntos:
            QMessageBox.warning(self, "Sin datos", "No existen registros de caudal confirmados (bandera=1) en el período seleccionado.")
            return None, None, None, None, []

        puntos.sort(key=lambda x: x[0])
        return f_ini_dt, f_fin_dt, c_min, c_max, puntos

    def previsualizar_grafico(self):
        f_ini, f_fin, c_min, c_max, puntos = self.obtener_datos_filtrados()
        if not puntos:
            return

        fechas = [p[0] for p in puntos]
        valores = [p[1] for p in puntos]

        NOMBRES_MESES = [
            "", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
            "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
        ]

        ticks_y, paso_y = calcular_ticks_eje_y(c_min, c_max, 7)

        # Configuración tipográfica estilo técnico Arial AutoCAD
        plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
        plt.rcParams['font.family'] = 'sans-serif'

        fig, (ax_grafico, ax_meses) = plt.subplots(
            2, 1, figsize=(12, 4.8),
            gridspec_kw={'height_ratios': [8.5, 1.2], 'hspace': 0.0}
        )

        # Curva de caudales destacada (grosor equivalente a 0.50 mm de AutoCAD)
        ax_grafico.plot(fechas, valores, color='black', lw=1.8, zorder=4)
        ax_grafico.set_ylabel('CAUDAL TOTAL (cm³/s)', fontname='Arial', fontweight='bold', fontsize=11)
        ax_grafico.set_ylim(c_min, c_max)
        ax_grafico.set_yticks(ticks_y)
        ax_grafico.set_yticklabels(
            [f"{int(round(t))}" if paso_y >= 1 and abs(t - round(t)) < 1e-4 else f"{t:.1f}" for t in ticks_y],
            fontname='Arial', fontsize=10
        )
        # Malla horizontal fina (grosor equivalente a 0.15 mm de AutoCAD)
        ax_grafico.grid(True, which='major', axis='y', color='black', linestyle='-', linewidth=0.6, zorder=1)

        ax_grafico.set_xlim(f_ini, f_fin)
        ax_grafico.tick_params(axis='x', which='both', bottom=False, labelbottom=False)
        ax_grafico.tick_params(axis='y', which='both', direction='out', length=5, width=1.0)

        # Marco exterior con grosor medio (0.35 mm de AutoCAD)
        for spine in ax_grafico.spines.values():
            spine.set_linewidth(1.3)
            spine.set_color('black')

        # Líneas verticales continuas en los cambios de mes (0.30 mm de AutoCAD)
        cur_dia = datetime(f_ini.year, f_ini.month, f_ini.day)
        while cur_dia <= f_fin:
            if cur_dia > f_ini and cur_dia.day == 1:
                ax_grafico.axvline(cur_dia, color='black', linestyle='-', linewidth=1.2, zorder=2)
                ax_meses.axvline(cur_dia, color='black', linestyle='-', linewidth=1.2, zorder=3)
            cur_dia += timedelta(days=1)

        cursor_mes = datetime(f_ini.year, f_ini.month, 1)
        while cursor_mes <= f_fin:
            ini_seg = max(f_ini, cursor_mes)
            if cursor_mes.month == 12:
                siguiente_mes = datetime(cursor_mes.year + 1, 1, 1)
            else:
                siguiente_mes = datetime(cursor_mes.year, cursor_mes.month + 1, 1)
            fin_seg = min(f_fin, siguiente_mes)

            if fin_seg > ini_seg:
                nom_mes = NOMBRES_MESES[cursor_mes.month]
                dt_centro = ini_seg + (fin_seg - ini_seg) / 2
                ax_meses.axvspan(ini_seg, fin_seg, facecolor='#666666', edgecolor='black', linewidth=1.2)
                ax_meses.text(
                    dt_centro, 0.5, nom_mes, color='white', fontname='Arial',
                    fontweight='bold', fontsize=10.5, ha='center', va='center'
                )
            cursor_mes = siguiente_mes

        ax_meses.set_xlim(f_ini, f_fin)
        ax_meses.set_ylim(0, 1)
        ax_meses.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        for spine in ax_meses.spines.values():
            spine.set_linewidth(1.3)
            spine.set_color('black')

        fig.tight_layout()
        plt.show()

    def generar_archivo_dxf(self):
        f_ini, f_fin, c_min, c_max, puntos = self.obtener_datos_filtrados()
        if not puntos:
            return

        nombre_sug = f"caudal_{f_ini.strftime('%Y%m%d')}_a_{f_fin.strftime('%Y%m%d')}.dxf"
        ruta_sug = os.path.join(self.dir_trabajo or "", nombre_sug)

        ruta_dxf, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Gráfico de Caudales en DXF",
            ruta_sug,
            "Archivos DXF (*.dxf)"
        )
        if not ruta_dxf:
            return

        try:
            escribir_dxf_caudales(ruta_dxf, f_ini, f_fin, c_min, c_max, puntos)
            QMessageBox.information(
                self,
                "DXF Generado Exitosamente",
                f"El archivo DXF se guardó correctamente en:\n{ruta_dxf}\n\n"
                f"Total de registros exportados: {len(puntos)}\n"
                f"Marco de caudal: {c_min:.1f} a {c_max:.1f} cm³/s\n"
                f"Período: {f_ini.strftime('%d/%m/%Y')} a {f_fin.strftime('%d/%m/%Y')}"
            )
        except Exception as ex:
            QMessageBox.critical(self, "Error al generar DXF", f"No se pudo escribir el archivo DXF:\n{ex}")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Caudales()
    window.show()
    app.exec_()

