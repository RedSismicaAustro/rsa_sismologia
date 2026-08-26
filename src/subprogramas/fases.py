import os
import sys
import json
import struct
import re
from pathlib import Path
import obspy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QFileDialog, QMessageBox, QGroupBox, QLabel, QComboBox,
    QGridLayout, QFrame
)
from PyQt5.QtCore import QDate, pyqtSignal, Qt
from PyQt5 import uic


def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    return ''


ruta_modulo = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_modulo, 'rsa_sismologia')
if not ruta_proyecto:
    ruta_proyecto = os.path.abspath(os.path.join(ruta_modulo, '..', '..'))

ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

from metodos_rsa import lectura_archivo
from metodos_sismicos import detectar_y_marcar_fases
from metodos_gestion import obtener_directorios, cargar_parametros, parametros_estaciones
from gestor_fases import GestorFases


class VentanaPrincipal(QMainWindow):
    cerrado = pyqtSignal()

    def __init__(self, archivo=None, directorio_trabajo=None, responsable=None, periodo=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Marcador de Fases Sísmicas - RSA")
        self.showMaximized()

        # Compatibilidad de parámetros: si el primer argumento es un QWidget parent
        if isinstance(archivo, QWidget):
            parent = archivo
            archivo = None

        self.archivo = str(archivo) if archivo else ""
        self.responsable = responsable or "RSA"
        self.periodo = periodo or "00:00 - 12:00"

        # Configuración y resolución del directorio de trabajo base
        if directorio_trabajo and os.path.exists(directorio_trabajo):
            self.directorio_trabajo = str(directorio_trabajo)
        elif self.archivo and os.path.exists(self.archivo):
            if os.path.isdir(self.archivo):
                self.directorio_trabajo = self.archivo
            else:
                self.directorio_trabajo = str(Path(self.archivo).parent)
        elif self.archivo:
            dir_padre = str(Path(self.archivo).parent)
            if os.path.exists(dir_padre):
                self.directorio_trabajo = dir_padre
            else:
                self.directorio_trabajo = "G:\\Mi unidad\\DIA"
        else:
            self.directorio_trabajo = "G:\\Mi unidad\\DIA"

        self.estaciones_por_pagina = 4
        self.pagina_actual = 0
        self.archivos_mseed_todos = []
        self.archivos_mseed = []
        self.fases_detectadas = {}
        self.axes = {}
        self.gestor_fases = None
        self.directorios = {}
        self.matriz_eventos = []
        self.archivo_sis = ""
        self.archivo_json = ""
        self.archivo_estacion_activa = ""

        # Cargar parámetros reales de estaciones y orden canónico de estaciones.csv
        try:
            self.mapa_estaciones = cargar_parametros()
            parametros = parametros_estaciones()
            self.orden_estaciones = {
                cod.strip().upper(): idx for idx, cod in enumerate(parametros.get('CODIGO', []))
            }
        except Exception as e:
            print(f"Advertencia al cargar mapa de estaciones: {e}")
            self.mapa_estaciones = {}
            self.orden_estaciones = {}

        self.init_ui()

    def init_ui(self):
        layout_principal = QHBoxLayout()

        # Panel izquierdo (Formulario y controles)
        panel_izquierdo = QVBoxLayout()
        ruta_ui = os.path.join(ruta_proyecto, "src", "ui", "marcar_fases.ui")
        if not os.path.exists(ruta_ui):
            ruta_ui = os.path.join(ruta_proyecto, "ui", "marcar_fases.ui")
        ruta_ui = os.path.abspath(ruta_ui)

        uic.loadUi(ruta_ui, self)

        panel_izquierdo.addWidget(self.centralWidget())

        # Inicializar opciones en los ComboBoxes cargados desde marcar_fases.ui
        self.combo_tipo_p.clear()
        self.combo_tipo_p.addItem("I (Impulsivo)", "I")
        self.combo_tipo_p.addItem("E (Emergente)", "E")
        self.combo_tipo_p.addItem("Ninguno", " ")

        self.combo_pol_p.clear()
        self.combo_pol_p.addItem("+ (Up/Compresión)", "+")
        self.combo_pol_p.addItem("- (Down/Dilatación)", "-")
        self.combo_pol_p.addItem("None", " ")

        self.combo_peso_p.clear()
        for p in range(5):
            self.combo_peso_p.addItem(str(p), p)

        self.combo_pol_s.clear()
        self.combo_pol_s.addItem("None", " ")
        self.combo_pol_s.addItem("+ (Up)", "+")
        self.combo_pol_s.addItem("- (Down)", "-")

        self.combo_peso_s.clear()
        for p in range(5):
            self.combo_peso_s.addItem(str(p), p)
        self.combo_peso_s.setCurrentIndex(2)

        layout_principal.addLayout(panel_izquierdo, 1)

        # Panel derecho (Gráfico general paginado)
        panel_derecho = QVBoxLayout()
        self.figura = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figura)
        panel_derecho.addWidget(self.canvas)

        self.toolbar = NavigationToolbar(self.canvas, self)
        panel_derecho.addWidget(self.toolbar)

        layout_principal.addLayout(panel_derecho, 3)

        # Widget central contenedor
        widget_central = QWidget()
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

        # Conectar señales de la interfaz
        self.boton_directorio.clicked.connect(self.cambiar_directorio)
        self.combo_sis.currentIndexChanged.connect(self.cargar_evento)
        self.checkbox_filtro.stateChanged.connect(self.graficar_evento)
        if hasattr(self, 'checkbox_estaciones_aportantes'):
            self.checkbox_estaciones_aportantes.stateChanged.connect(self.aplicar_filtro_aportantes)
        self.boton_salir.clicked.connect(self.cerrar_ventana)
        self.lista_mseed.itemDoubleClicked.connect(self.seleccionar_grafico_mseed)
        self.lista_mseed.currentItemChanged.connect(self.al_cambiar_estacion_seleccionada)
        self.lista_mseed.itemClicked.connect(self.al_cambiar_estacion_seleccionada)
        self.boton_anterior.clicked.connect(self.anterior_pagina)
        self.boton_siguiente.clicked.connect(self.siguiente_pagina)

        # Conectar eventos de interacción con el canvas (doble clic para abrir subventana de detalle)
        self.canvas.mpl_connect('button_press_event', self.al_hacer_click_en_canvas)

        # Conectar cambios de configuración CSV interactiva
        self.chk_csv_aporta.stateChanged.connect(self.al_modificar_config_csv_estacion)
        self.spbox_csv_canal.valueChanged.connect(self.al_modificar_config_csv_estacion)
        self.spbox_csv_orden.valueChanged.connect(self.al_modificar_config_csv_estacion)
        self.spbox_csv_finf.valueChanged.connect(self.al_modificar_config_csv_estacion)
        self.spbox_csv_fsup.valueChanged.connect(self.al_modificar_config_csv_estacion)

        # Conectar cambios de parámetros incrustados
        self.combo_tipo_p.currentIndexChanged.connect(self.al_modificar_parametros_estacion)
        self.combo_pol_p.currentIndexChanged.connect(self.al_modificar_parametros_estacion)
        self.combo_peso_p.currentIndexChanged.connect(self.al_modificar_parametros_estacion)
        self.combo_pol_s.currentIndexChanged.connect(self.al_modificar_parametros_estacion)
        self.combo_peso_s.currentIndexChanged.connect(self.al_modificar_parametros_estacion)

        self.cargar_dia()

    def cerrar_ventana(self):
        self.cerrado.emit()
        self.close()

    def closeEvent(self, event):
        self.cerrado.emit()
        super().closeEvent(event)

    def cambiar_directorio(self):
        nuevo_dir = QFileDialog.getExistingDirectory(
            self, "Seleccionar Directorio de Trabajo", self.directorio_trabajo
        )
        if nuevo_dir:
            self.directorio_trabajo = nuevo_dir
            self.cargar_dia()

    def cargar_dia(self):
        import datetime
        self.fases_detectadas = {}

        # 1. Resolver directorios estándar del día inicializado
        try:
            self.directorios = obtener_directorios(self.archivo)
        except Exception as e:
            print(f"Error al obtener directorios para {self.archivo}: {e}")
            self.directorios = {}

        # Determinar fecha seleccionada
        try:
            nombre_base = Path(self.archivo).stem.replace('_', '')
            if len(nombre_base) >= 8 and nombre_base[:8].isdigit():
                y = int(nombre_base[:4])
                m = int(nombre_base[4:6])
                d = int(nombre_base[6:8])
                self.fecha_seleccionada = datetime.date(y, m, d)
            else:
                self.fecha_seleccionada = datetime.date.today()
        except Exception:
            self.fecha_seleccionada = datetime.date.today()

        # 2. Leer matriz CSV (fuente de verdad de la clasificación)
        archivo_csv = self.directorios.get('archivo_csv', '')
        if archivo_csv and os.path.exists(archivo_csv):
            self.matriz_eventos = lectura_archivo(archivo_csv) or []
        else:
            self.matriz_eventos = []

        # 3. Extraer única y exclusivamente eventos clasificados como SISMO en el CSV
        archivos_sis = []
        if self.matriz_eventos:
            for fila in self.matriz_eventos:
                if len(fila) > 2 and str(fila[1]).strip():
                    tipo_ev = str(fila[2]).strip().upper()
                    if tipo_ev == 'SISMO':
                        nombre_ev = str(fila[1]).strip()
                        if not nombre_ev.lower().endswith('.sis'):
                            nombre_ev += '.sis'
                        if nombre_ev not in archivos_sis:
                            archivos_sis.append(nombre_ev)

        # 4. Actualizar selector de eventos
        self.combo_sis.blockSignals(True)
        self.combo_sis.clear()
        self.combo_sis.addItems(archivos_sis)
        self.combo_sis.blockSignals(False)

        if archivos_sis:
            self.combo_sis.setCurrentIndex(0)
            self.cargar_evento()
        else:
            fecha_txt = self.fecha_seleccionada.strftime('%Y-%m-%d') if hasattr(self, 'fecha_seleccionada') else ""
            msg = f"No existen eventos clasificados como SISMO en la jornada ({fecha_txt})."
            self.limpiar_vista(msg)

    cambio_de_fecha = cargar_dia

    def limpiar_vista(self, mensaje="No existen eventos clasificados como SISMO en esta jornada."):
        self.lista_mseed.clear()
        self.archivos_mseed_todos = []
        self.archivos_mseed = []
        self.fases_detectadas = {}
        if hasattr(self, 'lbl_estacion_activa'):
            self.lbl_estacion_activa.setText("Estación: [Sin sismos]")
        if hasattr(self, 'lbl_tiempos_estacion'):
            self.lbl_tiempos_estacion.setText("P: -- | S: -- | Coda: -- | Ts-Tp: --")
        self.figura.clear()
        ax = self.figura.add_subplot(111)
        ax.axis('off')
        ax.text(
            0.5, 0.5,
            mensaje,
            fontsize=12,
            color='#546e7a',
            ha='center',
            va='center',
            fontweight='bold'
        )
        self.canvas.draw()

    def cargar_evento(self):
        self.archivo_sis = self.combo_sis.currentText()
        if not self.archivo_sis:
            self.limpiar_vista()
            return

        stem_sis = Path(self.archivo_sis).stem
        directorio_dia = self.directorios.get('Directorio_dia', '')
        self.archivo_json = os.path.join(directorio_dia, f"{stem_sis}.json")

        # Extraer hora y fecha del evento
        partes = stem_sis.split('_')
        if len(partes) > 1:
            hora_sis = partes[-1]
            fecha_str_ev = partes[0]
        else:
            hora_sis = stem_sis[-6:] if len(stem_sis) >= 6 and stem_sis[-6:].isdigit() else stem_sis
            fecha_str_ev = ""

        dir_eventos = self.directorios.get('Directorio_eventos', '')
        if dir_eventos and os.path.exists(dir_eventos):
            archivos_encontrados = [
                f for f in os.listdir(dir_eventos)
                if f.lower().endswith(('.mseed', '.miniseed')) and (stem_sis in f or (hora_sis and f"_{hora_sis}." in f))
            ]

            # Ordenar según el orden oficial de estaciones.csv
            def clave_orden_estacion(nombre_archivo):
                cod = nombre_archivo.split('_')[0].strip().upper()
                return self.orden_estaciones.get(cod, 9999)

            self.archivos_mseed_todos = sorted(archivos_encontrados, key=clave_orden_estacion)
        else:
            self.archivos_mseed_todos = []

        # Buscar archivo .fas binario para traducción directa a .json
        archivo_fas = os.path.join(directorio_dia, f"{stem_sis}.fas")
        if not os.path.exists(archivo_fas) and os.path.exists(directorio_dia):
            for f in os.listdir(directorio_dia):
                if f.lower().endswith('.fas') and (hora_sis in f or self._evento_coincide(f, self.archivo_sis)):
                    archivo_fas = os.path.join(directorio_dia, f)
                    break

        # Si existe archivo .fas, traducir directamente al archivo JSON equivalente (fuente canónica)
        if os.path.exists(archivo_fas):
            self.fases_detectadas = self.cargar_fases_desde_fas(archivo_fas, self.archivos_mseed_todos)
            if self.fases_detectadas:
                self.guardar_evento()
                print(f"Fases del archivo {archivo_fas} traducidas y guardadas exitosamente en {self.archivo_json}")
        elif os.path.exists(self.archivo_json):
            try:
                with open(self.archivo_json, 'r', encoding='utf-8') as f:
                    self.fases_detectadas = json.load(f)
            except Exception as e:
                print(f"Error al cargar JSON de fases existente: {e}")
                self.fases_detectadas = {}
        else:
            self.fases_detectadas = {}

        self.aplicar_filtro_aportantes()

    def decodificar_archivo_fas(self, ruta_fas):
        """
        Lee y decodifica un archivo binario .fas retornando un diccionario con los registros de cada estación.
        """
        if not os.path.exists(ruta_fas):
            return {}
        try:
            with open(ruta_fas, 'rb') as f:
                data = f.read()
        except Exception as e:
            print(f"Error al leer {ruta_fas}: {e}")
            return {}

        strings = []
        pos = 0
        while pos < len(data):
            if pos + 4 <= len(data) and data[pos] == 8 and data[pos+1] == 0:
                l = data[pos+2] + (data[pos+3] << 8)
                if 0 < l < 100 and pos + 4 + l <= len(data):
                    s = data[pos+4:pos+4+l].decode('latin-1', errors='replace')
                    strings.append(s)
                    pos += 4 + l
                    continue
            pos += 1

        fases_estaciones = {}
        for i in range(0, len(strings) - 2, 3):
            s_p = strings[i]
            s_s = strings[i+1]
            s_coda = strings[i+2]

            cod = s_p[:4].strip().upper() if len(s_p) >= 4 else ""
            if not cod:
                continue

            info = {
                'cod': cod,
                'p_str': s_p.strip(),
                's_str': s_s.strip(),
                'coda_str': s_coda.strip(),
                'p_hora_str': '',
                'tipo_p': s_p[4] if len(s_p) > 4 and s_p[4] in ('I', 'E', ' ') else 'I',
                'polaridad_p': s_p[6] if len(s_p) > 6 and s_p[6] in ('+', '-', 'U', 'D', ' ') else ' ',
                'peso_p': int(s_p[7]) if len(s_p) > 7 and s_p[7].isdigit() else 0,
                'polaridad_s': s_s[7] if len(s_s) > 7 and s_s[7] in ('+', '-', 'U', 'D', ' ') else ' ',
                'peso_s': int(s_s[8]) if len(s_s) > 8 and s_s[8].isdigit() else 2,
                's_seg': 0.0,
                'coda_dur': 0.0
            }

            partes_p = s_p.strip().split()
            if len(partes_p) >= 2:
                time_p_str = partes_p[-1]
                if len(time_p_str) >= 12:
                    info['p_hora_str'] = time_p_str

            partes_s = s_s.strip().split()
            if len(partes_s) >= 1:
                try:
                    info['s_seg'] = float(partes_s[0])
                except ValueError:
                    pass

            if s_coda.strip():
                try:
                    info['coda_dur'] = float(s_coda.strip())
                except ValueError:
                    pass

            fases_estaciones[cod] = info

        return fases_estaciones

    def cargar_fases_desde_fas(self, ruta_fas, archivos_mseed):
        """
        Traduce las marcas del archivo .fas a tiempos relativos de los archivos .mseed para graficar.
        """
        fases_fas = self.decodificar_archivo_fas(ruta_fas)
        if not fases_fas:
            return {}

        dir_eventos = self.directorios.get('Directorio_eventos', '')
        fases_traducidas = {}

        for archivo in archivos_mseed:
            cod_est = archivo.split('_')[0].strip().upper()
            archivo_mseed = os.path.join(dir_eventos, archivo)
            if not os.path.exists(archivo_mseed):
                continue

            if cod_est not in fases_fas:
                fases_traducidas[archivo] = {
                    'P': [0.0], 'S': [0.0], 'Coda': [0.0],
                    'tipo_p': 'I', 'polaridad_p': ' ', 'peso_p': 0,
                    'polaridad_s': ' ', 'peso_s': 2
                }
                continue

            info = fases_fas[cod_est]

            try:
                st = obspy.read(archivo_mseed)
                tr = st[0]
                t_inicio = tr.stats.starttime

                t_p = 0.0
                t_s = 0.0
                t_coda = 0.0

                anio = t_inicio.year
                mes = t_inicio.month
                dia = t_inicio.day
                hora = t_inicio.hour
                minuto = t_inicio.minute

                # 1. Calcular tiempo relativo de Onda P
                if info['p_hora_str']:
                    p_str = info['p_hora_str']
                    if len(p_str.split('.')[0]) == 12:
                        p_str = "20" + p_str
                    try:
                        anio = int(p_str[0:4])
                        mes = int(p_str[4:6])
                        dia = int(p_str[6:8])
                        hora = int(p_str[8:10])
                        minuto = int(p_str[10:12])
                        segundo = float(p_str[12:])
                        utc_p = obspy.UTCDateTime(anio, mes, dia, hora, minuto) + segundo
                        t_p = max(0.0, float(utc_p - t_inicio))
                    except Exception as e:
                        print(f"Error parseando fecha P de {cod_est}: {e}")

                # 2. Calcular tiempo relativo de Onda S
                if info['s_seg'] > 0:
                    try:
                        utc_minuto = obspy.UTCDateTime(anio, mes, dia, hora, minuto)
                        utc_s = utc_minuto + info['s_seg']
                        t_s = max(0.0, float(utc_s - t_inicio))
                    except Exception as e:
                        print(f"Error parseando tiempo S de {cod_est}: {e}")

                # 3. Calcular tiempo relativo de Coda
                if info['coda_dur'] > 0 and t_p > 0:
                    t_coda = t_p + info['coda_dur']

                fases_traducidas[archivo] = {
                    'P': [round(t_p, 3)],
                    'S': [round(t_s, 3)],
                    'Coda': [round(t_coda, 3)],
                    'tipo_p': info.get('tipo_p', 'I'),
                    'polaridad_p': info.get('polaridad_p', ' '),
                    'peso_p': info.get('peso_p', 0),
                    'polaridad_s': info.get('polaridad_s', ' '),
                    'peso_s': info.get('peso_s', 2)
                }
            except Exception as e:
                print(f"Error al traducir fases desde .fas para {archivo}: {e}")
                fases_traducidas[archivo] = {
                    'P': [0.0], 'S': [0.0], 'Coda': [0.0],
                    'tipo_p': 'I', 'polaridad_p': ' ', 'peso_p': 0,
                    'polaridad_s': ' ', 'peso_s': 2
                }

        return fases_traducidas

    def aplicar_filtro_aportantes(self):
        solo_aportantes = (
            hasattr(self, 'checkbox_estaciones_aportantes') and
            self.checkbox_estaciones_aportantes.isChecked()
        )
        if solo_aportantes:
            candidatos = [
                arch for arch in self.archivos_mseed_todos
                if self.obtener_info_estacion(arch.split('_')[0])[0]
            ]
            if not candidatos and self.archivos_mseed_todos:
                self.archivos_mseed = list(self.archivos_mseed_todos)
            else:
                self.archivos_mseed = candidatos
        else:
            self.archivos_mseed = list(self.archivos_mseed_todos)

        # Actualizar lista de estaciones en la interfaz
        self.lista_mseed.clear()
        for archivo in self.archivos_mseed:
            nombre_corto = archivo.split('_')[0]
            if nombre_corto in self.mapa_estaciones:
                nombre_completo, _ = self.mapa_estaciones[nombre_corto]
                self.lista_mseed.addItem(f"{nombre_completo} ({archivo})")
            else:
                self.lista_mseed.addItem(archivo)

        self.pagina_actual = 0
        if self.lista_mseed.count() > 0:
            self.lista_mseed.setCurrentRow(0)
        self.graficar_evento()

    def _evento_coincide(self, sis_fila, sis_actual):
        if not sis_fila or not sis_actual:
            return False
        s1 = Path(str(sis_fila).strip()).stem
        s2 = Path(str(sis_actual).strip()).stem
        if s1 == s2:
            return True
        p1 = s1.split('_')
        p2 = s2.split('_')
        if len(p1) > 1 and len(p2) > 1:
            return p1[-1] == p2[-1]
        return (s1 in s2) or (s2 in s1)

    def obtener_info_estacion(self, nombre_corto):
        """
        Retorna (aporta, componente, orden_filtro, frec_inf, frec_sup)
        decodificando el token EEEECBFFIISS de la matriz AAAAMMDD000000.csv.
        """
        nombre_corto_norm = nombre_corto.strip().upper()
        for fila in self.matriz_eventos:
            if len(fila) > 1 and self._evento_coincide(fila[1], self.archivo_sis):
                for info in fila[3:]:
                    if not info or info.strip() == '-':
                        continue
                    info_limpio = info.strip()
                    if len(info_limpio) >= 6:
                        codigo_est = info_limpio[0:4].strip().upper()
                        if codigo_est == nombre_corto_norm or info_limpio.upper().startswith(nombre_corto_norm):
                            try:
                                comp = info_limpio[4]
                                aporta = (info_limpio[5] == '1')
                                orden = int(info_limpio[6:8]) if len(info_limpio) >= 8 else 0
                                f_inf = float(info_limpio[8:10]) if len(info_limpio) >= 10 else 0.0
                                f_sup = float(info_limpio[10:12]) if len(info_limpio) >= 12 else 0.0
                                return aporta, comp, orden, f_inf, f_sup
                            except (ValueError, IndexError):
                                pass
        return False, '1', 0, 0.0, 0.0

    def graficar_evento(self):
        self.figura.clear()
        self.axes = {}

        inicio = self.pagina_actual * self.estaciones_por_pagina
        fin = inicio + self.estaciones_por_pagina
        archivos_a_mostrar = self.archivos_mseed[inicio:fin]

        colores_fases = {'P': 'red', 'S': 'darkorange', 'Coda': 'green'}
        total_slots = self.estaciones_por_pagina  # Siempre 4 slots para mantener proporciones

        ultimo_idx_valido = len(archivos_a_mostrar) - 1

        for k in range(total_slots):
            if k < len(archivos_a_mostrar):
                archivo = archivos_a_mostrar[k]
                dir_eventos = self.directorios.get('Directorio_eventos', '')
                archivo_mseed = os.path.join(dir_eventos, archivo)
                if not os.path.exists(archivo_mseed):
                    ax_vacio = self.figura.add_subplot(total_slots, 1, k + 1)
                    ax_vacio.axis('off')
                    continue

                try:
                    st = obspy.read(archivo_mseed)
                except Exception as e:
                    print(f"Error al leer {archivo_mseed}: {e}")
                    ax_vacio = self.figura.add_subplot(total_slots, 1, k + 1)
                    ax_vacio.axis('off')
                    continue

                nombre_corto = archivo.split('_')[0]
                aporta, comp_token, orden, f_inf, f_sup = self.obtener_info_estacion(nombre_corto)
                color_linea = "blue" if aporta else "gray"

                indice_stream = 0
                if nombre_corto in self.mapa_estaciones:
                    _, componente = self.mapa_estaciones[nombre_corto]
                    try:
                        indice_stream = int(componente) - 1
                    except (ValueError, TypeError):
                        indice_stream = 0

                if 0 <= indice_stream < len(st):
                    tr = st[indice_stream]
                elif len(st) > 0:
                    tr = st[0]
                else:
                    ax_vacio = self.figura.add_subplot(total_slots, 1, k + 1)
                    ax_vacio.axis('off')
                    continue

                # Aplicar filtro si el checkbox está activo y el token define orden > 0
                tr_mostrar = tr.copy()
                if hasattr(self, 'checkbox_filtro') and self.checkbox_filtro.isChecked() and orden > 0:
                    try:
                        if f_inf > 0 and f_sup > f_inf:
                            tr_mostrar.filter('bandpass', freqmin=f_inf, freqmax=f_sup, corners=orden, zerophase=True)
                        elif f_sup > 0:
                            tr_mostrar.filter('lowpass', freq=f_sup, corners=orden, zerophase=True)
                        elif f_inf > 0:
                            tr_mostrar.filter('highpass', freq=f_inf, corners=orden, zerophase=True)
                    except Exception as e:
                        print(f"Advertencia al filtrar traza de {nombre_corto}: {e}")

                # Detección automática preliminar si no existen fases registradas
                if archivo not in self.fases_detectadas:
                    try:
                        fases = detectar_y_marcar_fases(tr_mostrar)
                        self.fases_detectadas[archivo] = fases
                    except Exception as e:
                        print(f"Error al detectar fases para {archivo}: {e}")
                        self.fases_detectadas[archivo] = {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}

                # Construir información descriptiva del filtro
                if orden > 0:
                    if f_inf > 0 and f_sup > f_inf:
                        texto_filtro = f"Filtro: {f_inf:g}-{f_sup:g} Hz (Ord {orden})"
                    elif f_sup > 0:
                        texto_filtro = f"Filtro: < {f_sup:g} Hz (Ord {orden})"
                    elif f_inf > 0:
                        texto_filtro = f"Filtro: > {f_inf:g} Hz (Ord {orden})"
                    else:
                        texto_filtro = f"Filtro: Ord {orden}"
                else:
                    texto_filtro = "Sin filtro (Ord 0)"

                if hasattr(self, 'checkbox_filtro') and not self.checkbox_filtro.isChecked() and orden > 0:
                    texto_filtro += " [Inactivo]"

                # Crear subplot vertical proporcional
                ax = self.figura.add_subplot(total_slots, 1, k + 1)
                tiempos_senal = tr_mostrar.times()
                ax.plot(tiempos_senal, tr_mostrar.data, label=tr_mostrar.id, color=color_linea, linewidth=0.8)

                # Dibujar líneas verticales de fases sobre el visor general
                fases_est = self.fases_detectadas.get(archivo, {})
                for tipo_fase in ['P', 'S', 'Coda']:
                    lista_tiempos = fases_est.get(tipo_fase, [])
                    if isinstance(lista_tiempos, list) and len(lista_tiempos) > 0 and lista_tiempos[0] > 0:
                        t_fase = lista_tiempos[0]
                        ax.axvline(
                            t_fase,
                            color=colores_fases.get(tipo_fase, 'black'),
                            linestyle='--',
                            linewidth=1.0,
                            alpha=0.9
                        )

                nombre_etiqueta = nombre_corto
                if nombre_corto in self.mapa_estaciones:
                    nombre_etiqueta = f"{self.mapa_estaciones[nombre_corto][0]} ({nombre_corto})"

                # Construir información detallada de fases en rojo (tiempos, ponderación, tipo e impulso)
                t_p = fases_est.get('P', [0.0])[0] if fases_est.get('P') else 0.0
                t_s = fases_est.get('S', [0.0])[0] if fases_est.get('S') else 0.0
                t_coda = fases_est.get('Coda', [0.0])[0] if fases_est.get('Coda') else 0.0
                tipo_p = fases_est.get('tipo_p', 'I')
                pol_p = fases_est.get('polaridad_p', ' ')
                peso_p = fases_est.get('peso_p', 0)
                pol_s = fases_est.get('polaridad_s', ' ')
                peso_s = fases_est.get('peso_s', 2)

                partes_fases = []
                if t_p > 0:
                    desc_p = f"{tipo_p}P{pol_p}{peso_p}".replace(' ', '')
                    partes_fases.append(f"P: {t_p:.2f}s [{desc_p}]")
                if t_s > 0:
                    desc_s = f"S{pol_s}{peso_s}".replace(' ', '')
                    partes_fases.append(f"S: {t_s:.2f}s [{desc_s}]")
                if t_coda > 0:
                    partes_fases.append(f"Coda: {t_coda:.2f}s")
                if t_s > t_p and t_p > 0:
                    partes_fases.append(f"Ts-Tp: {(t_s - t_p):.2f}s")

                texto_fases_rojo = " | ".join(partes_fases) if partes_fases else "Sin marcas"

                ax.set_title(f"{nombre_etiqueta} - {archivo} | [{texto_filtro}]", fontsize=8, pad=2, loc='left')
                ax.set_title(texto_fases_rojo, fontsize=7.5, color='darkred', fontweight='bold', pad=2, loc='right')
                ax.set_yticks([])
                ax.tick_params(axis='y', which='both', left=False, labelleft=False)
                if k == ultimo_idx_valido:
                    ax.set_xlabel("Tiempo (s)", fontsize=8)
                ax.tick_params(axis='x', which='major', labelsize=7)
                ax.grid(True, linestyle=':', alpha=0.5)

                self.axes[archivo] = ax
            else:
                # Slot vacío para preservar proporción fija de 4 estaciones
                ax_vacio = self.figura.add_subplot(total_slots, 1, k + 1)
                ax_vacio.axis('off')

        self.figura.tight_layout()
        self.canvas.draw()

    def al_cambiar_estacion_seleccionada(self, current, previous=None):
        if not current:
            return
        texto = current.text() if hasattr(current, 'text') else str(current)
        if '(' in texto and ')' in texto:
            archivo = texto.split('(')[-1].split(')')[0].strip()
        else:
            archivo = texto.strip()

        self.archivo_estacion_activa = archivo
        cod_est = archivo.split('_')[0].strip().upper()
        self.lbl_estacion_activa.setText(f"Estación: {cod_est} ({archivo})")

        # Cargar y sincronizar configuración CSV interactiva de la estación
        aporta, comp, orden, f_inf, f_sup = self.obtener_info_estacion(cod_est)

        self.chk_csv_aporta.blockSignals(True)
        self.spbox_csv_canal.blockSignals(True)
        self.spbox_csv_orden.blockSignals(True)
        self.spbox_csv_finf.blockSignals(True)
        self.spbox_csv_fsup.blockSignals(True)

        self.chk_csv_aporta.setChecked(bool(aporta))
        try:
            self.spbox_csv_canal.setValue(int(comp))
        except (ValueError, TypeError):
            self.spbox_csv_canal.setValue(1)
        self.spbox_csv_orden.setValue(int(orden))
        self.spbox_csv_finf.setValue(float(f_inf))
        self.spbox_csv_fsup.setValue(float(f_sup))

        self.chk_csv_aporta.blockSignals(False)
        self.spbox_csv_canal.blockSignals(False)
        self.spbox_csv_orden.blockSignals(False)
        self.spbox_csv_finf.blockSignals(False)
        self.spbox_csv_fsup.blockSignals(False)

        fases_est = self.fases_detectadas.get(archivo, {})

        # Bloquear señales temporalmente para evitar guardar durante la carga
        self.combo_tipo_p.blockSignals(True)
        self.combo_pol_p.blockSignals(True)
        self.combo_peso_p.blockSignals(True)
        self.combo_pol_s.blockSignals(True)
        self.combo_peso_s.blockSignals(True)

        tipo_p = fases_est.get('tipo_p', 'I')
        idx = self.combo_tipo_p.findData(tipo_p)
        if idx >= 0:
            self.combo_tipo_p.setCurrentIndex(idx)

        pol_p = fases_est.get('polaridad_p', ' ')
        if pol_p == 'U':
            pol_p = '+'
        elif pol_p == 'D':
            pol_p = '-'
        idx = self.combo_pol_p.findData(pol_p)
        if idx >= 0:
            self.combo_pol_p.setCurrentIndex(idx)

        peso_p = fases_est.get('peso_p', 0)
        idx = self.combo_peso_p.findData(peso_p)
        if idx >= 0:
            self.combo_peso_p.setCurrentIndex(idx)

        pol_s = fases_est.get('polaridad_s', ' ')
        if pol_s == 'U':
            pol_s = '+'
        elif pol_s == 'D':
            pol_s = '-'
        idx = self.combo_pol_s.findData(pol_s)
        if idx >= 0:
            self.combo_pol_s.setCurrentIndex(idx)

        peso_s = fases_est.get('peso_s', 2)
        idx = self.combo_peso_s.findData(peso_s)
        if idx >= 0:
            self.combo_peso_s.setCurrentIndex(idx)

        self.combo_tipo_p.blockSignals(False)
        self.combo_pol_p.blockSignals(False)
        self.combo_peso_p.blockSignals(False)
        self.combo_pol_s.blockSignals(False)
        self.combo_peso_s.blockSignals(False)

        self.actualizar_etiqueta_tiempos_estacion(archivo)

    def al_modificar_parametros_estacion(self):
        if not hasattr(self, 'archivo_estacion_activa') or not self.archivo_estacion_activa:
            return
        archivo = self.archivo_estacion_activa
        if archivo not in self.fases_detectadas:
            self.fases_detectadas[archivo] = {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}

        self.fases_detectadas[archivo]['tipo_p'] = self.combo_tipo_p.currentData()
        self.fases_detectadas[archivo]['polaridad_p'] = self.combo_pol_p.currentData()
        self.fases_detectadas[archivo]['peso_p'] = self.combo_peso_p.currentData()
        self.fases_detectadas[archivo]['polaridad_s'] = self.combo_pol_s.currentData()
        self.fases_detectadas[archivo]['peso_s'] = self.combo_peso_s.currentData()

        # Guardar inmediatamente en .json y en .fas
        self.guardar_evento()

    def actualizar_controles_estacion_activa(self, archivo):
        self.al_cambiar_estacion_seleccionada(archivo)

    def al_modificar_config_csv_estacion(self):
        if not hasattr(self, 'archivo_estacion_activa') or not self.archivo_estacion_activa:
            return
        cod_est = self.archivo_estacion_activa.split('_')[0].strip().upper()
        aporta = self.chk_csv_aporta.isChecked()
        comp = str(self.spbox_csv_canal.value())
        orden = self.spbox_csv_orden.value()
        f_inf = self.spbox_csv_finf.value()
        f_sup = self.spbox_csv_fsup.value()

        self.guardar_config_csv_estacion(cod_est, aporta, comp, orden, f_inf, f_sup)
        self.graficar_evento()

    def guardar_config_csv_estacion(self, nombre_corto, aporta, comp, orden, f_inf, f_sup):
        """
        Actualiza o inserta el token EEEECBFFIISS de la estación en la matriz de eventos
        y guarda inmediatamente en el archivo CSV AAAAMMDD000000.csv.
        """
        if not self.archivo_sis:
            return
        nombre_corto_norm = nombre_corto.strip().upper()
        token_b = '1' if aporta else '0'
        token_c = str(comp)[0] if comp else '1'
        token_ff = f"{int(orden):02d}"
        token_ii = f"{int(f_inf):02d}"
        token_ss = f"{int(f_sup):02d}"
        token_nuevo = f"{nombre_corto_norm:<4}{token_c}{token_b}{token_ff}{token_ii}{token_ss}"

        fila_encontrada = None
        for fila in self.matriz_eventos:
            if len(fila) > 1 and self._evento_coincide(fila[1], self.archivo_sis):
                fila_encontrada = fila
                break

        if fila_encontrada is not None:
            actualizado = False
            for idx in range(3, len(fila_encontrada)):
                token_existente = str(fila_encontrada[idx]).strip()
                if len(token_existente) >= 4 and token_existente[0:4].strip().upper() == nombre_corto_norm:
                    fila_encontrada[idx] = token_nuevo
                    actualizado = True
                    break
            if not actualizado:
                fila_encontrada.append(token_nuevo)
        else:
            fecha_str = self.fecha_seleccionada.strftime('%Y%m%d_%H%M%S') if hasattr(self, 'fecha_seleccionada') else "000000_000000"
            nueva_fila = ["EVENTO", self.archivo_sis, fecha_str, token_nuevo]
            self.matriz_eventos.append(nueva_fila)

        archivo_csv = self.directorios.get('archivo_csv')
        if not archivo_csv:
            directorio_dia = self.directorios.get('Directorio_dia', self.directorio_trabajo)
            marca_dia = self.fecha_seleccionada.strftime('%Y%m%d000000') if hasattr(self, 'fecha_seleccionada') else "000000000000"
            archivo_csv = os.path.join(directorio_dia, f"{marca_dia}.csv")
            self.directorios['archivo_csv'] = archivo_csv

        try:
            escritura_archivo(archivo_csv, self.matriz_eventos)
            print(f"Configuración CSV de {nombre_corto_norm} guardada exitosamente en {archivo_csv}: {token_nuevo}")
        except Exception as e:
            print(f"Error al guardar CSV de eventos: {e}")

    def actualizar_etiqueta_tiempos_estacion(self, archivo=None):
        if not archivo:
            archivo = getattr(self, 'archivo_estacion_activa', None)
        if not archivo or archivo not in self.fases_detectadas:
            self.lbl_tiempos_estacion.setText("P: -- | S: -- | Coda: -- | Ts-Tp: --")
            return

        fases_est = self.fases_detectadas[archivo]
        t_p = fases_est.get('P', [0.0])[0] if fases_est.get('P') else 0.0
        t_s = fases_est.get('S', [0.0])[0] if fases_est.get('S') else 0.0
        t_coda = fases_est.get('Coda', [0.0])[0] if fases_est.get('Coda') else 0.0
        ts_tp = (t_s - t_p) if (t_s > t_p and t_p > 0) else 0.0

        str_p = f"{t_p:.2f}s" if t_p > 0 else "--"
        str_s = f"{t_s:.2f}s" if t_s > 0 else "--"
        str_c = f"{t_coda:.2f}s" if t_coda > 0 else "--"
        str_dt = f"{ts_tp:.2f}s" if ts_tp > 0 else "--"

        self.lbl_tiempos_estacion.setText(f"P: {str_p} | S: {str_s} | Coda: {str_c} | Ts-Tp: {str_dt}")

    def al_hacer_click_en_canvas(self, event):
        """Maneja clics sobre el lienzo general: selección en un clic y apertura de subventana en doble clic"""
        if event.inaxes is None or not hasattr(self, 'axes'):
            return

        # Identificar qué estación corresponde al eje presionado
        archivo_click = None
        for archivo, ax in self.axes.items():
            if event.inaxes == ax:
                archivo_click = archivo
                break

        if not archivo_click:
            return

        # Sincronizar selección en la lista de estaciones de la ventana principal
        for row in range(self.lista_mseed.count()):
            item = self.lista_mseed.item(row)
            texto = item.text()
            if archivo_click in texto:
                self.lista_mseed.setCurrentRow(row)
                break

        # Si fue doble clic, lanzar la subventana de marcado de fases
        if event.dblclick:
            self.abrir_ventana_detalle(archivo_click)

    def seleccionar_grafico_mseed(self, item):
        """Abre la subventana de detalle al hacer doble clic en un ítem de la lista"""
        texto_item = item.text() if hasattr(item, 'text') else str(item)
        if '(' in texto_item and ')' in texto_item:
            archivo_seleccionado = texto_item.split('(')[-1].split(')')[0].strip()
        else:
            archivo_seleccionado = texto_item.strip()
        self.abrir_ventana_detalle(archivo_seleccionado)

    def abrir_ventana_detalle(self, archivo_seleccionado):
        """Construye y despliega la subventana de marcado fino de fases"""
        if not archivo_seleccionado:
            return

        if archivo_seleccionado not in self.fases_detectadas:
            self.fases_detectadas[archivo_seleccionado] = {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}

        fases_estacion = self.fases_detectadas[archivo_seleccionado]
        self.gestor_fases = GestorFases(fases_estacion)

        dir_eventos = self.directorios.get('Directorio_eventos', '')
        self.ventana_detalle = VentanaGrafico(
            dir_eventos,
            archivo_seleccionado,
            self.fecha_seleccionada,
            self.fases_detectadas,
            self.gestor_fases,
            self
        )
        self.ventana_detalle.show()

    def anterior_pagina(self):
        if not self.archivos_mseed:
            return
        max_pagina = max(0, (len(self.archivos_mseed) - 1) // self.estaciones_por_pagina)
        if self.pagina_actual > 0:
            self.pagina_actual -= 1
        else:
            self.pagina_actual = max_pagina  # Cíclico: va a la última página
        self.graficar_evento()

    def siguiente_pagina(self):
        if not self.archivos_mseed:
            return
        max_pagina = max(0, (len(self.archivos_mseed) - 1) // self.estaciones_por_pagina)
        if self.pagina_actual < max_pagina:
            self.pagina_actual += 1
        else:
            self.pagina_actual = 0  # Cíclico: vuelve al inicio
        self.graficar_evento()

    def guardar_evento(self):
        try:
            if not self.fases_detectadas:
                return

            directorio_dia = self.directorios.get('Directorio_dia', '')
            if directorio_dia:
                os.makedirs(directorio_dia, exist_ok=True)
            nombre_base = os.path.splitext(self.archivo_sis)[0]
            if not self.archivo_json:
                self.archivo_json = os.path.join(directorio_dia, f"{nombre_base}.json")

            with open(self.archivo_json, 'w', encoding='utf-8') as archivo:
                json.dump(self.fases_detectadas, archivo, indent=4)

            print(f"Fases guardadas exitosamente en {self.archivo_json}")

            # Generar o actualizar el archivo binario .fas respetando el formato canónico
            if directorio_dia and nombre_base:
                ruta_fas = os.path.join(directorio_dia, f"{nombre_base}.fas")
                self.construir_archivo_fas(ruta_fas)

        except Exception as e:
            print(f"Error al guardar las fases: {e}")

    def construir_archivo_fas(self, ruta_fas):
        """
        Construye y guarda el archivo binario .fas respetando estrictamente
        el formato binario estructurado de 16 ranuras de la RSA.
        """
        dir_eventos = self.directorios.get('Directorio_eventos', '')
        buf_total = bytearray()
        slots_escritos = 0

        # Iterar sobre las estaciones disponibles en el evento
        for archivo in self.archivos_mseed_todos:
            if slots_escritos >= 16:
                break

            cod_est = archivo.split('_')[0].strip().upper()
            fases_est = self.fases_detectadas.get(archivo, {})
            p_val = fases_est.get('P', [0.0])
            t_p = p_val[0] if (p_val and len(p_val) > 0) else 0.0

            s_val = fases_est.get('S', [0.0])
            t_s = s_val[0] if (s_val and len(s_val) > 0) else 0.0

            coda_val = fases_est.get('Coda', [0.0])
            t_coda = coda_val[0] if (coda_val and len(coda_val) > 0) else 0.0

            if t_p > 0:
                archivo_mseed = os.path.join(dir_eventos, archivo)
                try:
                    st = obspy.read(archivo_mseed)
                    tr = st[0]
                    t_inicio = tr.stats.starttime
                except Exception:
                    t_inicio = obspy.UTCDateTime(self.fecha_seleccionada)

                utc_p = t_inicio + t_p
                float_p_seg = utc_p.hour * 3600 + utc_p.minute * 60 + utc_p.second + utc_p.microsecond / 1e6
                yy = utc_p.year % 100

                # Formatear parámetros HYPO71 de fase P
                tipo_p = fases_est.get('tipo_p', 'I')
                if tipo_p not in ('I', 'E', ' '):
                    tipo_p = 'I'
                pol_p = fases_est.get('polaridad_p', ' ')
                if pol_p not in ('+', '-', 'U', 'D', ' '):
                    pol_p = ' '
                try:
                    peso_p = int(fases_est.get('peso_p', 0))
                    if not (0 <= peso_p <= 4):
                        peso_p = 0
                except (ValueError, TypeError):
                    peso_p = 0

                p_str_24 = f"{cod_est:<4}{tipo_p}P{pol_p}{peso_p} {yy:02d}{utc_p.month:02d}{utc_p.day:02d}{utc_p.hour:02d}{utc_p.minute:02d}{utc_p.second:02d}.{utc_p.microsecond // 10000:02d}"

                # Formatear parámetros HYPO71 de fase S
                pol_s = fases_est.get('polaridad_s', ' ')
                if pol_s not in ('+', '-', 'U', 'D', ' '):
                    pol_s = ' '
                try:
                    peso_s = int(fases_est.get('peso_s', 2))
                    if not (0 <= peso_s <= 4):
                        peso_s = 2
                except (ValueError, TypeError):
                    peso_s = 2

                if t_s > 0:
                    utc_s = t_inicio + t_s
                    double_s_seg = utc_s.second + utc_s.microsecond / 1e6
                    if utc_s.minute > utc_p.minute:
                        double_s_seg += 60 * (utc_s.minute - utc_p.minute)
                    s_str_9 = f"{double_s_seg:5.2f} S{pol_s}{peso_s}"
                else:
                    double_s_seg = 0.0
                    s_str_9 = "         "

                coda_dur = (t_coda - t_p) if (t_coda > t_p) else 0.0
                coda_str_4 = f"{coda_dur:4.1f}" if coda_dur > 0 else "    "

                # P block
                buf_total += b'\x02\x00\x01\x00\x04\x00'
                buf_total += struct.pack('<f', float(float_p_seg))
                buf_total += b'\x08\x00\x18\x00' + p_str_24.ljust(24)[:24].encode('latin-1')

                # S block
                buf_total += b'\x02\x00\x01\x00\x05\x00'
                buf_total += struct.pack('<d', float(double_s_seg))
                buf_total += b'\x08\x00\x09\x00' + s_str_9.ljust(9)[:9].encode('latin-1')

                # Coda block
                if coda_dur > 0:
                    buf_total += b'\x02\x00\x01\x00'
                    buf_total += b'\x08\x00\x04\x00' + coda_str_4.ljust(4)[:4].encode('latin-1')
                else:
                    buf_total += b'\x00\x00'
                    buf_total += b'\x08\x00\x04\x00' + b'    '

                slots_escritos += 1
            else:
                # Ranura vacía
                buf_total += b'\x02\x00\x00\x00\x00\x00'
                buf_total += b'\x08\x00\x18\x00' + b' ' * 24
                buf_total += b'\x00\x00\x00\x00'
                buf_total += b'\x08\x00\x09\x00' + b' ' * 9
                buf_total += b'\x00\x00'
                buf_total += b'\x08\x00\x04\x00' + b' ' * 4
                slots_escritos += 1

        # Rellenar ranuras restantes hasta completar 16
        while slots_escritos < 16:
            buf_total += b'\x02\x00\x00\x00\x00\x00'
            buf_total += b'\x08\x00\x18\x00' + b' ' * 24
            buf_total += b'\x00\x00\x00\x00'
            buf_total += b'\x08\x00\x09\x00' + b' ' * 9
            buf_total += b'\x00\x00'
            buf_total += b'\x08\x00\x04\x00' + b' ' * 4
            slots_escritos += 1

        try:
            with open(ruta_fas, 'wb') as f:
                f.write(buf_total)
            print(f"Archivo binario .fas generado exitosamente en {ruta_fas} ({len(buf_total)} bytes)")
        except Exception as e:
            print(f"Error al escribir archivo .fas en {ruta_fas}: {e}")


class VentanaGrafico(QMainWindow):
    def __init__(self, directorio_eventos, archivo_seleccionado, fecha, fases_detectadas, gestor_fases, parent=None):
        super().__init__(parent)
        self.directorio_eventos = directorio_eventos
        self.archivo_seleccionado = archivo_seleccionado
        self.fecha = fecha
        self.fases_detectadas = fases_detectadas
        self.gestor_fases = gestor_fases
        self.parent = parent

        nombre_corto = self.archivo_seleccionado.split('_')[0]
        if self.parent and hasattr(self.parent, 'mapa_estaciones') and nombre_corto in self.parent.mapa_estaciones:
            self.nombre_estacion, _ = self.parent.mapa_estaciones[nombre_corto]
        else:
            self.nombre_estacion = nombre_corto

        self.setWindowTitle(f"Señal a Detalle - {self.nombre_estacion} ({nombre_corto}) - {archivo_seleccionado}")
        self.setGeometry(150, 150, 920, 620)
        self.init_ui()

    def init_ui(self):
        widget_central = QWidget()
        layout_principal = QVBoxLayout(widget_central)
        layout_principal.setContentsMargins(8, 8, 8, 8)
        layout_principal.setSpacing(6)

        # -------------------------------------------------------------
        # BARRA SUPERIOR COMPACTA: Parámetros HYPO71 y Tiempos en vivo
        # -------------------------------------------------------------
        barra_superior = QHBoxLayout()
        nombre_corto = self.archivo_seleccionado.split('_')[0]

        lbl_nombre = QLabel(f"<b>{self.nombre_estacion} ({nombre_corto})</b>")
        lbl_nombre.setStyleSheet("font-size: 11px; color: #1a252f;")
        barra_superior.addWidget(lbl_nombre)

        barra_superior.addSpacing(10)

        # Parámetros HYPO71 compactos
        barra_superior.addWidget(QLabel("Tipo P:"))
        self.combo_tipo_p = QComboBox()
        self.combo_tipo_p.addItems(["I", "E"])
        barra_superior.addWidget(self.combo_tipo_p)

        barra_superior.addWidget(QLabel("Pol P:"))
        self.combo_pol_p = QComboBox()
        self.combo_pol_p.addItems([" ", "C", "D", "+", "-"])
        barra_superior.addWidget(self.combo_pol_p)

        barra_superior.addWidget(QLabel("Peso P:"))
        self.combo_peso_p = QComboBox()
        self.combo_peso_p.addItems(["0", "1", "2", "3", "4"])
        barra_superior.addWidget(self.combo_peso_p)

        barra_superior.addSpacing(6)

        barra_superior.addWidget(QLabel("Pol S:"))
        self.combo_pol_s = QComboBox()
        self.combo_pol_s.addItems([" ", "C", "D", "+", "-"])
        barra_superior.addWidget(self.combo_pol_s)

        barra_superior.addWidget(QLabel("Peso S:"))
        self.combo_peso_s = QComboBox()
        self.combo_peso_s.addItems(["0", "1", "2", "3", "4"])
        barra_superior.addWidget(self.combo_peso_s)

        barra_superior.addSpacing(10)

        # Etiqueta en vivo de tiempos delta y distancia
        self.lbl_delta = QLabel("Ts-Tp: -- | Dist: --")
        self.lbl_delta.setStyleSheet("font-weight: bold; color: #c0392b; font-size: 11px;")
        barra_superior.addWidget(self.lbl_delta)

        barra_superior.addStretch()
        layout_principal.addLayout(barra_superior)

        # -------------------------------------------------------------
        # ÁREA DE GRÁFICO MATPLOTLIB (Sin leyenda superior)
        # -------------------------------------------------------------
        self.figura = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figura)
        layout_principal.addWidget(self.canvas, 1)

        # Barra de navegación inferior
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout_principal.addWidget(self.toolbar)

        self.setCentralWidget(widget_central)

        # Cargar valores iniciales en los combos
        fases_est = self.gestor_fases.obtener_fases() if self.gestor_fases else {}
        self.combo_tipo_p.setCurrentText(fases_est.get('tipo_p', 'I'))
        self.combo_pol_p.setCurrentText(fases_est.get('polaridad_p', ' '))
        self.combo_peso_p.setCurrentText(str(fases_est.get('peso_p', 0)))
        self.combo_pol_s.setCurrentText(fases_est.get('polaridad_s', ' '))
        self.combo_peso_s.setCurrentText(str(fases_est.get('peso_s', 2)))

        # Conectar cambios de combos a actualización interna
        self.combo_tipo_p.currentIndexChanged.connect(self.al_modificar_combos)
        self.combo_pol_p.currentIndexChanged.connect(self.al_modificar_combos)
        self.combo_peso_p.currentIndexChanged.connect(self.al_modificar_combos)
        self.combo_pol_s.currentIndexChanged.connect(self.al_modificar_combos)
        self.combo_peso_s.currentIndexChanged.connect(self.al_modificar_combos)

        # Asignar callback en GestorFases para refrescar la información en vivo al arrastrar
        if self.gestor_fases:
            self.gestor_fases.al_actualizar_callback = self.actualizar_info_fases

        self.graficar_mseed()

    def al_modificar_combos(self):
        if self.gestor_fases:
            fases_est = self.gestor_fases.obtener_fases()
            fases_est['tipo_p'] = self.combo_tipo_p.currentText()
            fases_est['polaridad_p'] = self.combo_pol_p.currentText()
            try:
                fases_est['peso_p'] = int(self.combo_peso_p.currentText())
            except ValueError:
                fases_est['peso_p'] = 0
            fases_est['polaridad_s'] = self.combo_pol_s.currentText()
            try:
                fases_est['peso_s'] = int(self.combo_peso_s.currentText())
            except ValueError:
                fases_est['peso_s'] = 2
        self.actualizar_info_fases()

    def actualizar_info_fases(self):
        fases_est = self.gestor_fases.obtener_fases() if self.gestor_fases else {}
        t_p = fases_est.get('P', [0.0])[0] if fases_est.get('P') else 0.0
        t_s = fases_est.get('S', [0.0])[0] if fases_est.get('S') else 0.0
        t_coda = fases_est.get('Coda', [0.0])[0] if fases_est.get('Coda') else 0.0

        partes_fases = []
        if t_p > 0:
            desc_p = f"{self.combo_tipo_p.currentText()}P{self.combo_pol_p.currentText()}{self.combo_peso_p.currentText()}".replace(' ', '')
            partes_fases.append(f"P: {t_p:.2f}s [{desc_p}]")
        if t_s > 0:
            desc_s = f"S{self.combo_pol_s.currentText()}{self.combo_peso_s.currentText()}".replace(' ', '')
            partes_fases.append(f"S: {t_s:.2f}s [{desc_s}]")
        if t_coda > 0:
            partes_fases.append(f"Coda: {t_coda:.2f}s")

        if t_s > t_p and t_p > 0:
            ts_tp = t_s - t_p
            dist_aprox = ts_tp * 8.0  # Vp/Vs estándar ~ 8 km/s para corteza
            partes_fases.append(f"Ts-Tp: {ts_tp:.2f}s")
            self.lbl_delta.setText(f"Ts-Tp: {ts_tp:.2f}s | Dist ~ {dist_aprox:.1f} km")
        else:
            self.lbl_delta.setText("Ts-Tp: -- | Dist: --")

        texto_fases = " | ".join(partes_fases) if partes_fases else "Sin marcas"
        if hasattr(self, 'ax') and self.ax:
            self.ax.set_title(texto_fases, fontsize=8.5, color='darkred', fontweight='bold', pad=3, loc='right')
            self.canvas.draw_idle()

    def graficar_mseed(self):
        self.figura.clear()
        ruta_completa = os.path.join(self.directorio_eventos, self.archivo_seleccionado)
        try:
            st = obspy.read(ruta_completa)
            self.ax = self.figura.add_subplot(111)

            nombre_corto = self.archivo_seleccionado.split('_')[0]
            aporta, comp_token, orden, f_inf, f_sup = (
                self.parent.obtener_info_estacion(nombre_corto) if self.parent and hasattr(self.parent, 'obtener_info_estacion')
                else (True, '1', 0, 0.0, 0.0)
            )
            color_traza = "#1b4f72" if aporta else "#7f8c8d"

            indice_stream = 0
            if self.parent and hasattr(self.parent, 'mapa_estaciones'):
                if nombre_corto in self.parent.mapa_estaciones:
                    _, comp = self.parent.mapa_estaciones[nombre_corto]
                    try:
                        indice_stream = int(comp) - 1
                    except (ValueError, TypeError):
                        indice_stream = 0

            if 0 <= indice_stream < len(st):
                tr = st[indice_stream]
            else:
                tr = st[0]

            tr_mostrar = tr.copy()
            if (self.parent and hasattr(self.parent, 'checkbox_filtro') and
                    self.parent.checkbox_filtro.isChecked() and orden > 0):
                try:
                    if f_inf > 0 and f_sup > f_inf:
                        tr_mostrar.filter('bandpass', freqmin=f_inf, freqmax=f_sup, corners=orden, zerophase=True)
                    elif f_sup > 0:
                        tr_mostrar.filter('lowpass', freq=f_sup, corners=orden, zerophase=True)
                    elif f_inf > 0:
                        tr_mostrar.filter('highpass', freq=f_inf, corners=orden, zerophase=True)
                except Exception as e:
                    print(f"Advertencia al filtrar en detalle {nombre_corto}: {e}")

            self.id_estacion = tr_mostrar.id
            estado_texto = "Aporta" if aporta else "No Aporta"

            if orden > 0:
                if f_inf > 0 and f_sup > f_inf:
                    texto_filtro = f"Filtro: {f_inf:g}-{f_sup:g} Hz (Ord {orden})"
                elif f_sup > 0:
                    texto_filtro = f"Filtro: < {f_sup:g} Hz (Ord {orden})"
                elif f_inf > 0:
                    texto_filtro = f"Filtro: > {f_inf:g} Hz (Ord {orden})"
                else:
                    texto_filtro = f"Filtro: Ord {orden}"
            else:
                texto_filtro = "Sin filtro"

            if self.parent and hasattr(self.parent, 'checkbox_filtro') and not self.parent.checkbox_filtro.isChecked() and orden > 0:
                texto_filtro += " [Inactivo]"

            # Graficar traza completa (sin recuadro de leyenda flotante)
            self.ax.plot(tr_mostrar.times(), tr_mostrar.data, color=color_traza, linewidth=0.9)
            self.ax.set_title(
                f"Estación: {self.nombre_estacion} ({nombre_corto}) | {texto_filtro} | Estado: {estado_texto}",
                fontsize=9, pad=3, loc='left', color='#1a252f', fontweight='bold'
            )
            self.ax.set_xlabel("Tiempo (s)", fontsize=9)
            self.ax.set_yticks([])
            self.ax.tick_params(axis='y', which='both', left=False, labelleft=False)
            self.ax.grid(True, linestyle=':', alpha=0.6)

            # Dibujar líneas verticales a través del gestor de fases
            self.gestor_fases.inicializar_fases(self.ax)
            self.actualizar_info_fases()

            # Conexión limpia de eventos interactivos:
            # - Clic Izquierdo (button=1): Picar / arrastrar marcas de fase
            # - Clic Derecho (button=3): Alternar herramienta de Zoom (o doble clic para Home)
            self.canvas.mpl_connect('button_press_event', self.al_presionar_mouse)
            self.canvas.mpl_connect('button_release_event', self.gestor_fases.al_soltar)
            self.canvas.mpl_connect('motion_notify_event', lambda event: self.gestor_fases.al_mover(event, self.canvas))

            self.figura.tight_layout()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al cargar el archivo {self.archivo_seleccionado}: {e}")

    def al_presionar_mouse(self, event):
        """Maneja clics de mouse: clic derecho alterna Zoom, clic izquierdo pica marcas"""
        if event.button == 3:  # Clic derecho
            if getattr(event, 'dblclick', False):
                self.toolbar.home()  # Doble clic derecho restaura escala original
            else:
                self.toolbar.zoom()  # Clic derecho alterna modo Zoom
        elif event.button == 1:  # Clic izquierdo
            # Solo permitir arrastre/marcado si no se está usando activamente el zoom rectangular
            if getattr(self.toolbar, 'mode', '') != 'zoom rect':
                self.gestor_fases.al_presionar(event, self.ax, self.canvas)

    def keyPressEvent(self, event):
        """Atajos de teclado para agilizar el análisis"""
        if event.key() == Qt.Key_Z:
            self.toolbar.zoom()
        elif event.key() == Qt.Key_R or event.key() == Qt.Key_H:
            self.toolbar.home()
        elif event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        fases_actualizadas = self.gestor_fases.obtener_fases()
        fases_est = fases_actualizadas if isinstance(fases_actualizadas, dict) else {}
        fases_est['tipo_p'] = self.combo_tipo_p.currentText()
        fases_est['polaridad_p'] = self.combo_pol_p.currentText()
        try:
            fases_est['peso_p'] = int(self.combo_peso_p.currentText())
        except ValueError:
            fases_est['peso_p'] = 0
        fases_est['polaridad_s'] = self.combo_pol_s.currentText()
        try:
            fases_est['peso_s'] = int(self.combo_peso_s.currentText())
        except ValueError:
            fases_est['peso_s'] = 2

        if self.parent:
            self.parent.fases_detectadas[self.archivo_seleccionado] = fases_est
            self.parent.guardar_evento()
            self.parent.graficar_evento()
            self.parent.actualizar_controles_estacion_activa(self.archivo_seleccionado)
            self.parent.actualizar_etiqueta_tiempos_estacion(self.archivo_seleccionado)
        super().closeEvent(event)



