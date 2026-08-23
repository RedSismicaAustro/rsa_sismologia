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

import numpy as np
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
        
        hoy = QDate.currentDate()
        semana_atras = hoy.addDays(-7)
        self.selector_fecha_inicio.setDate(semana_atras)
        self.selector_fecha_fin.setDate(hoy)
        self.selector_fecha_grafico.setDate(hoy)
        
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

        # === Formulario de configuración y eventos ===
        self.boton_directorio.clicked.connect(self.seleccionar_directorio_trabajo)
        self.boton_siguiente_ciclo.clicked.connect(self.ir_a_siguiente_ciclo_esperado)
        self.boton_guardar_marcas.clicked.connect(self.guardar_marcas)
        self.boton_ignorar_caudal.clicked.connect(self.ignorar_punto_caudal_seleccionado)
        self.boton_salir.clicked.connect(self.close)
        
        # === Incrustar los 3 Lienzos de Matplotlib ===
        self.inicializar_lienzos_graficos()
        
        # Cargar datos iniciales
        self.al_cambiar_fecha_sismograma()
        self.al_cambiar_periodo()
        
        # Iniciar ventana maximizada
        self.showMaximized()

    def inicializar_lienzos_graficos(self):
        """Inicializa los 3 lienzos Matplotlib con área gráfica al 100%, sin eje Y ni títulos redundantes."""
        # 1. Contenedor Superior: Serie Temporal de Caudales
        self.fig_caudales = Figure(figsize=(10, 2.0))
        self.fig_caudales.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.16)
        self.canvas_caudales = FigureCanvas(self.fig_caudales)
        self.toolbar_caudales = NavigationToolbar(self.canvas_caudales, self)
        self.toolbar_caudales.setMaximumHeight(24)
        self.ax_caudales = self.fig_caudales.add_subplot(111)
        self.ax_caudales.grid(True, linestyle='--', alpha=0.3)
        self.ax_caudales.yaxis.set_visible(False)
        self.ax_caudales.tick_params(axis='x', labelsize=7.5, pad=1)
        self.layout_grafico_caudales.addWidget(self.toolbar_caudales)
        self.layout_grafico_caudales.addWidget(self.canvas_caudales)

        # 2. Contenedor Medio: Sismograma Diario 24h
        self.fig_sismograma = Figure(figsize=(10, 2.0))
        self.fig_sismograma.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.16)
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
        self.fig_zoom.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.16)
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
            archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
            escritura_archivo(archivo_caudales, self.caudales)
            
            self.evento_caudal_seleccionado = None
            self.graficar_caudales(silencioso=True)
            self.desplegar_grafico(silencioso=True, mantener_vista=True)
            QMessageBox.information(
                self,
                "Punto Ignorado",
                f"La medición del evento {evento_a_ignorar} se ha puesto en bandera 0 y fue excluida de la gráfica."
            )
        else:
            QMessageBox.warning(self, "No encontrado", f"No se encontró el evento {evento_a_ignorar} en el catálogo.")

    def al_cambiar_periodo(self):
        """Sincroniza y actualiza automáticamente los caudales al modificar cualquier fecha del periodo."""
        self.cargar_eventos_control(silencioso=True)
        self.graficar_caudales(silencioso=True)

    def al_cambiar_fecha_sismograma(self):
        """Carga el registro del día y actualiza automáticamente el sismograma y zoom."""
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

        # === Eventos CONTROL del día ===
        archivo_csv_dia = self.directorios.get('archivo_csv', '')
        if os.path.isfile(archivo_csv_dia):
            self.eventos = lectura_archivo(archivo_csv_dia)
        else:
            self.eventos = []

        eventos_control_dia = [evento[1] for evento in self.eventos if len(evento) > 2 and str(evento[2]).strip().upper() == "CONTROL"]
        max_valor = float(datos.max()) if len(datos) > 0 else 1.0
        caudales_confirmados = {f[0] for f in self.caudales if len(f) > 2 and f[2] == "1"}

        primer_evento_dt = None
        for evento in eventos_control_dia:
            try:
                color_linea = 'green' if evento in caudales_confirmados else 'red'
                dt_evento = datetime.strptime(evento.replace(".sis", ""), "%Y%m%d_%H%M%S")
                if primer_evento_dt is None:
                    primer_evento_dt = dt_evento
                tiempo_relativo = mdates.date2num(dt_evento)
                self.ax_sismograma.axvline(x=tiempo_relativo, color=color_linea, linestyle=':', linewidth=1, alpha=0.7)
                self.ax_sismograma.text(tiempo_relativo, max_valor * 0.95, evento, rotation=90,
                                        fontsize=6.5, verticalalignment='bottom', color=color_linea)
            except Exception as e:
                print(f"Error al graficar evento CONTROL del día: {evento} → {e}")

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
        else:
            centro_zoom = mdates.date2num(primer_evento_dt) if primer_evento_dt else (tiempo[0] + (tiempo[-1] - tiempo[0]) / 2.0)
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

        # Dibujar marcas de eventos CONTROL en el zoom
        for evento in self.eventos:
            if len(evento) > 2 and str(evento[2]).strip().upper() == "CONTROL":
                try:
                    dt_ev = datetime.strptime(evento[1].replace(".sis", ""), "%Y%m%d_%H%M%S")
                    t_ev = mdates.date2num(dt_ev)
                    if t_min <= t_ev <= t_max:
                        self.ax_zoom.axvline(x=t_ev, color='green', linestyle=':', linewidth=1.2)
                        self.ax_zoom.text(t_ev, self.ax_zoom.get_ylim()[1] * 0.9, evento[1], rotation=90,
                                          fontsize=6.5, verticalalignment='top', color='green')
                except Exception:
                    pass

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
        n_evento = 0
        tipo_evento = 'CONTROL'
        fecha_real = tiempo + tiempo_inicio
        nombre_sis = fecha_real.strftime('%Y%m%d_%H%M%S.sis')
        ahora = datetime.now()
        estaciones = "CHA231000000"
        
        evento_auxiliar = (n_evento, nombre_sis, tipo_evento, ahora, tiempo_inicio, tiempo_fin, 'RSA', estaciones, 'Caudales')
        eventos_auxiliar.append(evento_auxiliar)
        escritura_archivo(archivo_auxiliar, eventos_auxiliar)

        archivo_csv = self.directorios.get('archivo_csv', '')
        if os.path.isfile(archivo_csv):
            self.eventos = lectura_archivo(archivo_csv)
        else:
            self.eventos = []

        solo_eventos = [fila[1] for fila in self.eventos if len(fila) > 1]
        for i, ev_aux in enumerate(eventos_auxiliar):
            evento = extraccion(ev_aux, solo_eventos, self.archivo, False)
            if evento is not None:
                self.eventos.append(evento)
                
        self.eventos = ordenar_y_eliminar_duplicados(self.eventos, 1, False)
        escritura_archivo(archivo_csv, self.eventos)
        
        # Calcular caudal para el nuevo evento respecto al último confirmado anterior
        dt_nuevo = datetime.strptime(nombre_sis.replace(".sis", ""), "%Y%m%d_%H%M%S")
        eventos_confirmados_previos = []
        for fila in self.caudales:
            if len(fila) >= 3 and str(fila[2]).strip() == "1":
                nom = str(fila[0]).strip()
                if len(nom) == 17:
                    nom = '20' + nom
                try:
                    dt_prev = datetime.strptime(nom.replace(".sis", ""), "%Y%m%d_%H%M%S")
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
                caudal_nuevo = int(1.214 * 3500000 / segundos)

        # Registrar o actualizar solo el nuevo evento en self.caudales (bandera = '1')
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

        archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
        escritura_archivo(archivo_caudales, self.caudales)
        
        # Limpiar marcas y redibujar preservando el encuadre actual del sismograma y zoom
        self.marcas_usuario.clear()
        self.desplegar_grafico(silencioso=True, mantener_vista=True)
        self.graficar_caudales(silencioso=True)
        self.cargar_guia_operacion()
        QMessageBox.information(self, "Extracción Exitosa", f"Evento {nombre_sis} extraído, confirmado y graficado en la serie de caudales.")

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
        self.ax_caudales.tick_params(axis='x', labelsize=7.5, pad=1)
        self.ax_caudales.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        self.fig_caudales.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.16)
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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Caudales()
    window.show()
    app.exec_()

