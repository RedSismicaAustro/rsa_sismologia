import sys
import os
import csv
import re
import glob
import shutil
import stat
from obspy import read
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QTextEdit, QListWidget, QListWidgetItem, QLabel,
    QMessageBox, QSplitter, QDialog, QPlainTextEdit, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QKeySequence
from PyQt5.QtWidgets import QShortcut
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from datetime import datetime, timedelta


def es_carpeta_reseteo_valida(nombre_carpeta):
    # Formato AAAAMMDD (8 dígitos)
    if len(nombre_carpeta) == 8 and nombre_carpeta.isdigit():
        try:
            fecha = datetime.strptime(nombre_carpeta, "%Y%m%d")
            return datetime(1980, 1, 1) <= fecha < datetime(2000, 1, 1)
        except ValueError:
            return False
    # Formato AAMMDD (6 dígitos) - ej: 800125
    elif len(nombre_carpeta) == 6 and nombre_carpeta.isdigit():
        try:
            fecha = datetime.strptime(nombre_carpeta, "%y%m%d")
            return datetime(1980, 1, 1) <= fecha < datetime(2000, 1, 1)
        except ValueError:
            return False
    return False


def obtener_fecha_desde_nombre_carpeta(nombre_carpeta):
    if len(nombre_carpeta) == 8 and nombre_carpeta.isdigit():
        try:
            return datetime.strptime(nombre_carpeta, "%Y%m%d")
        except ValueError:
            return None
    if len(nombre_carpeta) == 6 and nombre_carpeta.isdigit():
        try:
            return datetime.strptime(nombre_carpeta, "%y%m%d")
        except ValueError:
            return None
    return None


def es_carpeta_posterior_2000(nombre_carpeta):
    fecha = obtener_fecha_desde_nombre_carpeta(nombre_carpeta)
    return fecha is not None and fecha >= datetime(2000, 1, 1)


class VisorEVT(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Depuración de archivos EVT - Acelerógrafo ETNA")
        self.setGeometry(100, 100, 1200, 800)

        self.etiquetas = {}
        self.asociaciones = {}
        self.fechas_asignadas = {}
        self.cache_catalogos = {}
        self.ruta_descarga_actual = None
        self.ruta_destino_preclasificacion = None
        self.archivos_evt = []          # (ruta, subcarpeta, nombre, mtime)
        self.archivo_actual_ruta = None
        self.archivo_referencia_ruta = None
        # Referencia original (sin calibrar) y referencia actual (puede cambiar tras calibración)
        self.fecha_base_ref_original = None
        self.fecha_base_ref = None
        self.mtime_ref = None
        self.fecha_descarga_str = None
        self.evento_ancla_calibracion = None
        self.periodos_evt = []
        self.referencias_periodos = {}
        self.eventos_ancla_periodos = {}
        self.usar_reconstruccion_por_periodos = False

        self.figura = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figura)

        self.shortcut_sismo = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_sismo.activated.connect(lambda: self.marcar_actual("evento"))
        self.shortcut_ruido = QShortcut(QKeySequence("Ctrl+R"), self)
        self.shortcut_ruido.activated.connect(lambda: self.marcar_actual("ruido"))

        # Widgets principales
        self.label_ruta_principal = QLabel("Directorio principal: ninguno")
        self.label_ruta_principal.setFont(QFont("Arial", 10, QFont.Bold))
        self.label_destino_preclasificacion = QLabel("Destino: no seleccionado")
        self.label_destino_preclasificacion.setFont(QFont("Arial", 9))
        self.label_subcarpeta = QLabel("Subcarpeta (día): --")
        self.label_subcarpeta.setFont(QFont("Arial", 10, QFont.Bold))
        self.label_archivo = QLabel("Archivo: --")
        self.label_archivo.setFont(QFont("Arial", 10))
        self.label_etiqueta_actual = QLabel("Etiqueta: ruido (por defecto)")
        self.label_etiqueta_actual.setFont(QFont("Arial", 10))
        self.label_ultimo_sismo = QLabel("Último sismo: --")
        self.label_ultimo_sismo.setFont(QFont("Arial", 9))
        self.label_ultimo_sismo.setStyleSheet("color: blue;")

        # Botones
        self.boton_destino_preclasificacion = QPushButton("Seleccionar carpeta de destino")
        self.boton_destino_preclasificacion.clicked.connect(self.seleccionar_destino_preclasificacion)
        self.boton_cargar_carpeta = QPushButton("Seleccionar carpeta de descarga (AAAAMMDD)")
        self.boton_cargar_carpeta.clicked.connect(self.seleccionar_carpeta_descarga)

        self.boton_marcar_evento = QPushButton("Marcar como Evento (Sismo) [Ctrl+S]")
        self.boton_marcar_evento.clicked.connect(lambda: self.marcar_actual("evento"))
        self.boton_marcar_ruido = QPushButton("Marcar como Ruido [Ctrl+R]")
        self.boton_marcar_ruido.clicked.connect(lambda: self.marcar_actual("ruido"))

        self.boton_mostrar_fechas = QPushButton("Mostrar fechas de sismos")
        self.boton_mostrar_fechas.clicked.connect(self.mostrar_fechas_sismos)
        self.boton_guardar = QPushButton("Guardar eventos")
        self.boton_guardar.clicked.connect(self.guardar_eventos)
        self.boton_salir = QPushButton("Salir")
        self.boton_salir.clicked.connect(self.salir)

        # Lista de archivos EVT
        self.lista_archivos = QListWidget()
        self.lista_archivos.currentItemChanged.connect(self.cargar_archivo_desde_lista)

        # Tabla de resultados de asignación automática
        self.label_margen = QLabel("Margen para asignación automática (minutos):")
        self.spin_margen = QSpinBox()
        self.spin_margen.setRange(1, 30)
        self.spin_margen.setValue(5)
        self.spin_margen.setSuffix(" min")

        self.tabla_asignaciones = QTableWidget()
        self.tabla_asignaciones.setColumnCount(4)
        self.tabla_asignaciones.setHorizontalHeaderLabels(
            ["EVT", "Fecha/Hora corregida", "Evento asignado", "Diferencia (min)"]
        )
        self.tabla_asignaciones.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_asignaciones.setAlternatingRowColors(True)
        self.tabla_asignaciones.itemDoubleClicked.connect(self.abrir_mseed_desde_tabla)

        # Sección para cargar catálogo (raíz)
        layout_raiz = QHBoxLayout()
        self.label_raiz = QLabel("Raíz (carpeta que contiene DIA):")
        self.edit_raiz = QLineEdit("C:\\")
        self.edit_raiz.setReadOnly(False)
        self.boton_raiz = QPushButton("Seleccionar raíz")
        self.boton_raiz.clicked.connect(self.seleccionar_raiz_catalogo)
        layout_raiz.addWidget(self.label_raiz)
        layout_raiz.addWidget(self.edit_raiz)
        layout_raiz.addWidget(self.boton_raiz)

        self.boton_cargar_catalogo = QPushButton("Calibrar y asignar con catalogo")
        self.boton_cargar_catalogo.clicked.connect(self.calibrar_con_ultimo_sismo)

        # Layout principal
        splitter_principal = QSplitter(Qt.Horizontal)
        panel_izquierdo = QWidget()
        layout_izq = QVBoxLayout(panel_izquierdo)
        layout_izq.addWidget(self.label_destino_preclasificacion)
        layout_izq.addWidget(self.boton_destino_preclasificacion)
        layout_izq.addWidget(self.label_ruta_principal)
        layout_izq.addWidget(self.label_subcarpeta)
        layout_izq.addWidget(self.label_archivo)
        layout_izq.addWidget(self.label_etiqueta_actual)
        layout_izq.addWidget(self.label_ultimo_sismo)
        layout_izq.addWidget(self.boton_cargar_carpeta)
        layout_izq.addWidget(self.boton_marcar_evento)
        layout_izq.addWidget(self.boton_marcar_ruido)
        layout_izq.addWidget(self.boton_mostrar_fechas)
        layout_izq.addWidget(self.lista_archivos)
        layout_izq.addWidget(self.label_margen)
        layout_izq.addWidget(self.spin_margen)
        layout_izq.addWidget(QLabel("Resultados de asignación automática (doble click para ver mseed):"))
        layout_izq.addWidget(self.tabla_asignaciones)
        layout_izq.addLayout(layout_raiz)
        layout_izq.addWidget(self.boton_cargar_catalogo)
        layout_izq.addWidget(self.boton_guardar)
        layout_izq.addWidget(self.boton_salir)

        panel_derecho = QWidget()
        layout_der = QVBoxLayout(panel_derecho)
        layout_der.addWidget(self.canvas)

        splitter_principal.addWidget(panel_izquierdo)
        splitter_principal.addWidget(panel_derecho)
        splitter_principal.setSizes([400, 800])

        layout_main = QVBoxLayout()
        layout_main.addWidget(splitter_principal)
        self.setLayout(layout_main)
        self.habilitar_widgets_trabajo(False)

    # ------------------------------------------------------------
    # Funciones de catálogo y carga
    # ------------------------------------------------------------
    def seleccionar_raiz_catalogo(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta raíz (que contiene DIA)", self.edit_raiz.text())
        if carpeta:
            self.edit_raiz.setText(carpeta)

    def habilitar_widgets_trabajo(self, habilitado):
        widgets = [
            self.boton_cargar_carpeta,
            self.boton_marcar_evento,
            self.boton_marcar_ruido,
            self.boton_mostrar_fechas,
            self.lista_archivos,
            self.label_margen,
            self.spin_margen,
            self.tabla_asignaciones,
            self.label_raiz,
            self.edit_raiz,
            self.boton_raiz,
            self.boton_cargar_catalogo,
            self.boton_guardar,
        ]
        for widget in widgets:
            widget.setEnabled(habilitado)
        self.shortcut_sismo.setEnabled(habilitado)
        self.shortcut_ruido.setEnabled(habilitado)

    def seleccionar_destino_preclasificacion(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de destino")
        if not carpeta:
            return
        self.ruta_destino_preclasificacion = carpeta
        self.label_destino_preclasificacion.setText(f"Destino: {carpeta}")
        self.habilitar_widgets_trabajo(True)

    def extraer_hora_desde_nombre(self, nombre_archivo):
        match = re.search(r'_(\d{6})\.', nombre_archivo)
        if match:
            hhmmss = match.group(1)
            return f"{hhmmss[:2]}:{hhmmss[2:4]}:{hhmmss[4:]}"
        return ""

    def obtener_fecha_hora_evento_catalogo(self, nombre_evento, fecha_respaldo=None, hora_respaldo=None):
        match = re.search(r"(\d{8})_(\d{6})", str(nombre_evento))
        if match:
            try:
                return datetime.strptime(f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S")
            except ValueError:
                return None

        if fecha_respaldo and hora_respaldo:
            hora_limpia = str(hora_respaldo).replace(":", "")
            try:
                return datetime.strptime(f"{fecha_respaldo}_{hora_limpia}", "%Y%m%d_%H%M%S")
            except ValueError:
                return None

        return None

    def cargar_catalogo_por_fecha(self, fecha_str):
        if fecha_str in self.cache_catalogos:
            return self.cache_catalogos[fecha_str]

        raiz = self.edit_raiz.text()
        if not os.path.isdir(raiz):
            return None

        try:
            fecha_obj = datetime.strptime(fecha_str, "%Y%m%d")
            año = fecha_obj.strftime("%Y")
            año_mes = fecha_obj.strftime("%Y_%m")
            dia_carpeta = fecha_obj.strftime("%Y_%m_%d")
            archivo_nombre = fecha_obj.strftime("%Y%m%d") + "000000.csv"
        except:
            return None

        ruta_csv = os.path.join(raiz, "DIA", año, año_mes, dia_carpeta, archivo_nombre)
        if not os.path.isfile(ruta_csv):
            return None

        try:
            with open(ruta_csv, 'r', encoding='utf-8', newline='') as f:
                lector = csv.reader(f, delimiter=';')
                lineas = list(lector)
            matriz = []
            for fila in lineas:
                if len(fila) >= 2:
                    num = fila[0].strip()
                    nombre_archivo = fila[1].strip()
                    tipo = fila[2].strip() if len(fila) >= 3 else ""
                    hora_str = self.extraer_hora_desde_nombre(nombre_archivo)
                    matriz.append([num, nombre_archivo, tipo, hora_str, ruta_csv])
            self.cache_catalogos[fecha_str] = matriz
            return matriz
        except:
            return None

    # ------------------------------------------------------------
    # Calibracion (usa el ultimo EVT marcado como sismo y la referencia original)
    # ------------------------------------------------------------
    def calibrar_con_ultimo_sismo(self):
        if self.usar_reconstruccion_por_periodos:
            self.calibrar_periodos_con_reseteos()
            return

        evt_eventos = [(ruta, sub, nom, mtime) for (ruta, sub, nom, mtime) in self.archivos_evt
                       if self.etiquetas.get(ruta) == "evento"]
        if not evt_eventos:
            QMessageBox.warning(self, "Sin sismos", "No hay archivos EVT marcados como sismo.")
            return

        evt_eventos.sort(key=lambda x: x[3])
        ruta_ult, sub_ult, nom_ult, mtime_ult = evt_eventos[-1]

        # Siempre se parte de la referencia original: cada intento recalcula desde cero.
        fecha_corr_ult = self.corregir_fecha_con_referencia(mtime_ult, self.fecha_base_ref_original)
        if not fecha_corr_ult:
            QMessageBox.warning(self, "Error", "No se pudo obtener la hora corregida del ultimo EVT.")
            return

        fecha_evt_str = fecha_corr_ult.strftime("%Y%m%d")
        catalogo_fecha = self.cargar_catalogo_por_fecha(fecha_evt_str)
        if catalogo_fecha is None:
            QMessageBox.warning(self, "Catalogo no encontrado", f"No se encontro catalogo para la fecha {fecha_evt_str}")
            return

        margen_horas = 5
        opciones = []
        for num, evento, tipo, hora_str, path_csv in catalogo_fecha:
            tiempo_catalogo = self.obtener_fecha_hora_evento_catalogo(evento, fecha_evt_str, hora_str)
            if tiempo_catalogo is None:
                continue
            diferencia_seg = abs((tiempo_catalogo - fecha_corr_ult).total_seconds())
            if diferencia_seg <= margen_horas * 3600:
                opciones.append((num, evento, tipo, hora_str, path_csv, tiempo_catalogo, diferencia_seg))

        if not opciones:
            QMessageBox.warning(self, "Sin coincidencias", f"No hay eventos en el catalogo de {fecha_evt_str} dentro de +/-{margen_horas} horas.")
            return

        opciones.sort(key=lambda item: item[5])
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Calibracion - seleccione el evento real")
        dialogo.setGeometry(300, 300, 700, 400)
        layout = QVBoxLayout(dialogo)

        lbl_info = QLabel(f"Ultimo EVT marcado como sismo: {nom_ult}\n"
                          f"Fecha corregida inicial: {fecha_corr_ult.strftime('%Y-%m-%d %H:%M:%S')}\n"
                          f"Catalogo de: {fecha_evt_str}\n"
                          f"Seleccione el evento real. Ese evento quedara con diferencia 0.")
        layout.addWidget(lbl_info)

        lista = QListWidget()
        for num, ev, tp, hr, path_csv, tiempo_catalogo, diferencia_seg in opciones:
            item = QListWidgetItem(
                f"{num} - {ev} ({tp})  Hora: {hr}  Dif inicial: {diferencia_seg/60:.1f} min"
            )
            item.setData(Qt.UserRole, (num, ev, tp, hr, path_csv, tiempo_catalogo))
            lista.addItem(item)
        layout.addWidget(lista)

        btn_ok = QPushButton("Aceptar, recalibrar y asignar")
        layout.addWidget(btn_ok)

        def on_accept():
            sel = lista.currentItem()
            if not sel:
                QMessageBox.warning(dialogo, "Seleccion", "Debe seleccionar un evento.")
                return
            num, ev, tp, hora_real_str, path_csv, tiempo_catalogo = sel.data(Qt.UserRole)
            if not self.recalibrar_referencia_desde_original(ruta_ult, tiempo_catalogo):
                return
            self.evento_ancla_calibracion = (ruta_ult, num, ev, path_csv, tiempo_catalogo)
            dialogo.accept()
            self.asignar_todos_automaticamente()

        btn_ok.clicked.connect(on_accept)
        dialogo.exec_()

    def cargar_eventos_catalogo_en_rango(self, inicio, fin):
        eventos = []
        fecha = inicio.date()
        while fecha <= fin.date():
            fecha_str = fecha.strftime("%Y%m%d")
            catalogo = self.cargar_catalogo_por_fecha(fecha_str)
            if catalogo:
                for num, evento, tipo, hora_str, path_csv in catalogo:
                    tiempo_catalogo = self.obtener_fecha_hora_evento_catalogo(evento, fecha_str, hora_str)
                    if tiempo_catalogo and inicio <= tiempo_catalogo <= fin:
                        eventos.append((num, evento, tipo, hora_str, path_csv, tiempo_catalogo))
            fecha = fecha + timedelta(days=1)
        return eventos

    def obtener_ultimo_sismo_periodo(self, periodo):
        eventos = []
        for numero, ruta, nombre, subcarpeta, mtime in periodo["elementos"]:
            if self.etiquetas.get(ruta) == "evento":
                eventos.append((ruta, nombre, subcarpeta, mtime))
        if not eventos:
            return None
        return max(eventos, key=lambda item: item[3])

    def seleccionar_ancla_periodo(self, periodo, evt_ancla, referencia_preliminar,
                                  limite_inicio, limite_fin,
                                  eventos_catalogo_usados=None,
                                  validar_periodo_completo=True):
        ruta_evt, nombre_evt, subcarpeta_evt, mtime_evt = evt_ancla
        fecha_evt_preliminar = referencia_preliminar + timedelta(seconds=mtime_evt - periodo["ultimo_mtime"])
        eventos_catalogo = self.cargar_eventos_catalogo_en_rango(limite_inicio, limite_fin)
        eventos_catalogo_usados = eventos_catalogo_usados or set()
        opciones = []

        for num, evento, tipo, hora_str, path_csv, tiempo_catalogo in eventos_catalogo:
            clave_catalogo = (path_csv, num)
            if clave_catalogo in eventos_catalogo_usados:
                continue

            fecha_ultimo_evt = tiempo_catalogo - timedelta(seconds=mtime_evt - periodo["ultimo_mtime"])
            fecha_primer_evt = fecha_ultimo_evt + timedelta(seconds=periodo["primer_mtime"] - periodo["ultimo_mtime"])

            if validar_periodo_completo:
                if fecha_ultimo_evt > limite_fin:
                    continue
                if fecha_primer_evt < limite_inicio:
                    continue

            diferencia_preliminar = abs((tiempo_catalogo - fecha_evt_preliminar).total_seconds())
            opciones.append((num, evento, tipo, hora_str, path_csv, tiempo_catalogo,
                             fecha_primer_evt, fecha_ultimo_evt, diferencia_preliminar))

        if not opciones:
            QMessageBox.warning(
                self,
                "Sin candidatos",
                f"No se encontraron candidatos coherentes para el periodo {periodo['prefijo']}."
            )
            return None

        opciones.sort(key=lambda item: item[8])
        dialogo = QDialog(self)
        dialogo.setWindowTitle(f"Periodo {periodo['prefijo']} - seleccionar evento de catalogo")
        dialogo.setGeometry(300, 300, 850, 450)
        layout = QVBoxLayout(dialogo)
        descripcion_rango = "Rango permitido"
        if not validar_periodo_completo:
            descripcion_rango = "Ventana original de busqueda"
        layout.addWidget(QLabel(
            f"Periodo {periodo['prefijo']}\n"
            f"EVT ancla marcado como sismo: {nombre_evt}\n"
            f"Fecha preliminar del EVT: {fecha_evt_preliminar.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{descripcion_rango}: {limite_inicio.strftime('%Y-%m-%d %H:%M:%S')} -> {limite_fin.strftime('%Y-%m-%d %H:%M:%S')}"
        ))

        lista = QListWidget()
        for opcion in opciones:
            num, evento, tipo, hora_str, path_csv, tiempo_catalogo, fecha_primer_evt, fecha_ultimo_evt, diferencia = opcion
            item = QListWidgetItem(
                f"{num} - {evento} ({tipo}) | {tiempo_catalogo.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"dif prelim {diferencia/60:.1f} min | periodo "
                f"{fecha_primer_evt.strftime('%Y-%m-%d %H:%M:%S')} -> {fecha_ultimo_evt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            item.setData(Qt.UserRole, opcion)
            lista.addItem(item)
        layout.addWidget(lista)

        btn_ok = QPushButton("Aceptar periodo")
        layout.addWidget(btn_ok)
        seleccion = {"opcion": None}

        def aceptar():
            item = lista.currentItem()
            if item is None:
                QMessageBox.warning(dialogo, "Seleccion", "Debe seleccionar un evento.")
                return
            seleccion["opcion"] = item.data(Qt.UserRole)
            dialogo.accept()

        btn_ok.clicked.connect(aceptar)
        dialogo.exec_()
        return seleccion["opcion"]

    def registrar_periodo_sin_sismo(self, periodo, limite_fin):
        fecha_ultimo_evt = limite_fin
        fecha_primer_evt = fecha_ultimo_evt + timedelta(seconds=periodo["primer_mtime"] - periodo["ultimo_mtime"])
        self.referencias_periodos[periodo["prefijo"]] = {
            "fecha_ultimo_evt": fecha_ultimo_evt,
            "mtime_ultimo_evt": periodo["ultimo_mtime"],
            "fecha_primer_evt": fecha_primer_evt,
        }
        return fecha_primer_evt

    def calibrar_periodos_con_reseteos(self):
        if not self.periodos_evt:
            QMessageBox.warning(self, "Sin periodos", "No hay periodos EVT identificados.")
            return
        if self.fecha_base_ref_original is None:
            QMessageBox.warning(self, "Sin referencia", "No hay fecha de descarga valida para iniciar la reconstruccion.")
            return

        self.referencias_periodos.clear()
        self.eventos_ancla_periodos.clear()
        self.evento_ancla_calibracion = None

        periodos_pendientes = list(self.periodos_evt)
        eventos_catalogo_usados = set()
        periodos_sin_sismo = []

        indice_ultimo = len(periodos_pendientes) - 1
        periodo_ultimo = periodos_pendientes[indice_ultimo]
        evt_ancla_ultimo = self.obtener_ultimo_sismo_periodo(periodo_ultimo)
        if evt_ancla_ultimo is None:
            periodos_sin_sismo.append(periodo_ultimo["prefijo"])
            limite_fin_periodo_siguiente = self.registrar_periodo_sin_sismo(
                periodo_ultimo,
                self.fecha_base_ref_original
            )
        else:
            fecha_ancla_preliminar = self.corregir_fecha_con_referencia(
                evt_ancla_ultimo[3],
                self.fecha_base_ref_original
            )
            if fecha_ancla_preliminar is None:
                QMessageBox.warning(self, "Error", "No se pudo obtener la hora corregida del ultimo periodo.")
                return

            limite_inicio = fecha_ancla_preliminar - timedelta(hours=5)
            limite_fin = fecha_ancla_preliminar + timedelta(hours=5)

            opcion = self.seleccionar_ancla_periodo(
                periodo_ultimo,
                evt_ancla_ultimo,
                self.fecha_base_ref_original,
                limite_inicio,
                limite_fin,
                eventos_catalogo_usados=eventos_catalogo_usados,
                validar_periodo_completo=False
            )
            if opcion is None:
                return

            num, evento, tipo, hora_str, path_csv, tiempo_catalogo, fecha_primer_evt, fecha_ultimo_evt, diferencia = opcion
            self.referencias_periodos[periodo_ultimo["prefijo"]] = {
                "fecha_ultimo_evt": fecha_ultimo_evt,
                "mtime_ultimo_evt": periodo_ultimo["ultimo_mtime"],
                "fecha_primer_evt": fecha_primer_evt,
            }
            self.eventos_ancla_periodos[periodo_ultimo["prefijo"]] = (
                evt_ancla_ultimo[0], num, evento, path_csv, tiempo_catalogo
            )
            self.evento_ancla_calibracion = (
                evt_ancla_ultimo[0], num, evento, path_csv, tiempo_catalogo
            )
            eventos_catalogo_usados.add((path_csv, num))
            limite_fin_periodo_siguiente = fecha_primer_evt

        for indice in range(indice_ultimo - 1, -1, -1):
            periodo = periodos_pendientes[indice]
            evt_ancla = self.obtener_ultimo_sismo_periodo(periodo)
            if evt_ancla is None:
                periodos_sin_sismo.append(periodo["prefijo"])
                limite_fin_periodo_siguiente = self.registrar_periodo_sin_sismo(
                    periodo,
                    limite_fin_periodo_siguiente
                )
                continue

            duracion_pendiente = sum(
                self.obtener_duracion_periodo_segundos(p)
                for p in periodos_pendientes[:indice + 1]
            )
            limite_inicio = limite_fin_periodo_siguiente - timedelta(seconds=duracion_pendiente)
            referencia_preliminar = limite_fin_periodo_siguiente

            opcion = self.seleccionar_ancla_periodo(
                periodo,
                evt_ancla,
                referencia_preliminar,
                limite_inicio,
                limite_fin_periodo_siguiente,
                eventos_catalogo_usados=eventos_catalogo_usados,
                validar_periodo_completo=True
            )
            if opcion is None:
                return

            num, evento, tipo, hora_str, path_csv, tiempo_catalogo, fecha_primer_evt, fecha_ultimo_evt, diferencia = opcion
            self.referencias_periodos[periodo["prefijo"]] = {
                "fecha_ultimo_evt": fecha_ultimo_evt,
                "mtime_ultimo_evt": periodo["ultimo_mtime"],
                "fecha_primer_evt": fecha_primer_evt,
            }
            self.eventos_ancla_periodos[periodo["prefijo"]] = (
                evt_ancla[0], num, evento, path_csv, tiempo_catalogo
            )
            eventos_catalogo_usados.add((path_csv, num))
            limite_fin_periodo_siguiente = fecha_primer_evt

        self.asignar_todos_automaticamente()
        detalle_sin_sismo = ""
        if periodos_sin_sismo:
            detalle_sin_sismo = (
                "\n\nPeriodos sin sismo marcado, reconstruidos solo por continuidad temporal: "
                + ", ".join(periodos_sin_sismo)
            )

        QMessageBox.information(
            self,
            "Reconstruccion completada",
            f"Se reconstruyeron {len(self.referencias_periodos)} periodos EVT.\n"
            "Revise la tabla de asignaciones antes de guardar."
            f"{detalle_sin_sismo}"
        )

    def recalibrar_referencia_desde_original(self, ruta_evt, tiempo_real_catalogo):
        """Recalcula la referencia desde la referencia original y ancla el EVT elegido al catalogo."""
        for r, sub, nom, mtime in self.archivos_evt:
            if r == ruta_evt:
                evt_info = (r, sub, nom, mtime)
                break
        else:
            return False

        fecha_corr_original = self.corregir_fecha_con_referencia(evt_info[3], self.fecha_base_ref_original)
        if not fecha_corr_original:
            return False

        delta = tiempo_real_catalogo - fecha_corr_original
        self.fecha_base_ref = self.fecha_base_ref_original + delta

        fecha_verificacion = self.corregir_fecha(evt_info[3])
        diferencia_verificacion = abs((fecha_verificacion - tiempo_real_catalogo).total_seconds())
        if diferencia_verificacion > 0.001:
            QMessageBox.warning(
                self,
                "Calibracion",
                f"La referencia no quedo exactamente en cero. Diferencia: {diferencia_verificacion:.6f} s"
            )
            return False

        self.actualizar_info_ultimo_sismo()
        for i in range(self.lista_archivos.count()):
            ruta = self.archivos_evt[i][0]
            if ruta == self.archivo_actual_ruta:
                self.cargar_y_graficar_evt(ruta, self.archivos_evt[i][3])
                break
        return True

    # ------------------------------------------------------------
    # Asignación automática (usa la referencia actual)
    # ------------------------------------------------------------
    def asignar_todos_automaticamente(self):
        eventos_evt = [(ruta, sub, nom, mtime) for (ruta, sub, nom, mtime) in self.archivos_evt
                       if self.etiquetas.get(ruta) == "evento"]
        if not eventos_evt:
            self.tabla_asignaciones.setRowCount(0)
            return

        margen_min = self.spin_margen.value()
        margen_seg = margen_min * 60
        self.tabla_asignaciones.setRowCount(0)
        self.asociaciones.clear()
        self.fechas_asignadas.clear()

        for ruta, sub, nom, mtime in eventos_evt:
            fecha_corr = self.corregir_fecha_en_periodo(ruta, mtime)  # usa referencia global o referencia del periodo
            if not fecha_corr:
                self.agregar_fila_tabla(nom, "Error en corrección", "", "")
                continue

            fecha_str = fecha_corr.strftime("%Y%m%d")
            catalogo = self.cargar_catalogo_por_fecha(fecha_str)
            if catalogo is None:
                self.agregar_fila_tabla(nom, fecha_corr.strftime("%Y-%m-%d %H:%M:%S"),
                                        "No se encontró catálogo", "")
                continue

            periodo = self.obtener_periodo_por_ruta(ruta)
            if periodo and periodo["prefijo"] in self.eventos_ancla_periodos:
                ruta_ancla, numero_ancla, evento_ancla, path_csv_ancla, tiempo_ancla = self.eventos_ancla_periodos[periodo["prefijo"]]
                if ruta == ruta_ancla:
                    self.asociaciones[ruta] = numero_ancla
                    self.fechas_asignadas[ruta] = tiempo_ancla
                    self.agregar_fila_tabla(nom, fecha_corr.strftime("%Y-%m-%d %H:%M:%S"),
                                            f"{numero_ancla} - {evento_ancla}", "0.0")
                    row = self.tabla_asignaciones.rowCount() - 1
                    self.tabla_asignaciones.item(row, 0).setData(Qt.UserRole, (fecha_str, evento_ancla, path_csv_ancla))
                    for i in range(self.lista_archivos.count()):
                        if self.archivos_evt[i][0] == ruta:
                            self.lista_archivos.item(i).setForeground(QColor("darkgreen"))
                            break
                    continue

            if self.evento_ancla_calibracion and ruta == self.evento_ancla_calibracion[0]:
                _, numero_ancla, evento_ancla, path_csv_ancla, tiempo_ancla = self.evento_ancla_calibracion
                self.asociaciones[ruta] = numero_ancla
                self.fechas_asignadas[ruta] = tiempo_ancla
                self.agregar_fila_tabla(nom, fecha_corr.strftime("%Y-%m-%d %H:%M:%S"),
                                        f"{numero_ancla} - {evento_ancla}", "0.0")
                row = self.tabla_asignaciones.rowCount() - 1
                self.tabla_asignaciones.item(row, 0).setData(Qt.UserRole, (fecha_str, evento_ancla, path_csv_ancla))
                for i in range(self.lista_archivos.count()):
                    if self.archivos_evt[i][0] == ruta:
                        self.lista_archivos.item(i).setForeground(QColor("darkgreen"))
                        break
                continue

            mejor_evento = None
            mejor_diff = margen_seg + 1
            mejor_num = None
            mejor_ev = None
            mejor_path_csv = None
            mejor_tiempo = None

            for num, ev, tp, hora_str, path_csv in catalogo:
                tiempo_catalogo = self.obtener_fecha_hora_evento_catalogo(ev, fecha_str, hora_str)
                if tiempo_catalogo is None:
                    continue
                diff = abs((tiempo_catalogo - fecha_corr).total_seconds())
                if diff < mejor_diff:
                    mejor_diff = diff
                    mejor_evento = (num, ev, path_csv)
                    mejor_num = num
                    mejor_ev = ev
                    mejor_path_csv = path_csv
                    mejor_tiempo = tiempo_catalogo

            if mejor_evento and mejor_diff <= margen_seg:
                self.asociaciones[ruta] = mejor_num
                self.fechas_asignadas[ruta] = mejor_tiempo
                self.agregar_fila_tabla(nom, fecha_corr.strftime("%Y-%m-%d %H:%M:%S"),
                                        f"{mejor_num} - {mejor_ev}", f"{mejor_diff/60:.1f}")
                row = self.tabla_asignaciones.rowCount() - 1
                self.tabla_asignaciones.item(row, 0).setData(Qt.UserRole, (fecha_str, mejor_ev, mejor_path_csv))
                for i in range(self.lista_archivos.count()):
                    if self.archivos_evt[i][0] == ruta:
                        self.lista_archivos.item(i).setForeground(QColor("darkgreen"))
                        break
            else:
                self.agregar_fila_tabla(nom, fecha_corr.strftime("%Y-%m-%d %H:%M:%S"),
                                        "Ninguno", f">{margen_min} min")
                for i in range(self.lista_archivos.count()):
                    if self.archivos_evt[i][0] == ruta:
                        self.lista_archivos.item(i).setForeground(QColor("green"))
                        break

        self.tabla_asignaciones.resizeColumnsToContents()

    def agregar_fila_tabla(self, evt_nom, fecha_hora, evento_asignado, diff):
        row = self.tabla_asignaciones.rowCount()
        self.tabla_asignaciones.insertRow(row)
        self.tabla_asignaciones.setItem(row, 0, QTableWidgetItem(evt_nom))
        self.tabla_asignaciones.setItem(row, 1, QTableWidgetItem(fecha_hora))
        self.tabla_asignaciones.setItem(row, 2, QTableWidgetItem(evento_asignado))
        self.tabla_asignaciones.setItem(row, 3, QTableWidgetItem(diff))

    # ------------------------------------------------------------
    # Abrir mseed desde la tabla (doble click)
    # ------------------------------------------------------------
    def abrir_mseed_desde_tabla(self, item):
        row = item.row()
        evt_item = self.tabla_asignaciones.item(row, 0)
        if evt_item is None:
            return
        data = evt_item.data(Qt.UserRole)
        if data is None:
            QMessageBox.warning(self, "Sin datos", "No hay información de evento asignado para este registro.")
            return
        fecha_str, nombre_evento, ruta_csv = data
        directorio_csv = os.path.dirname(ruta_csv)
        mseed_dir = os.path.join(directorio_csv, "mseed", "eventos")
        if not os.path.isdir(mseed_dir):
            QMessageBox.warning(self, "Directorio no encontrado", f"No existe el directorio:\n{mseed_dir}")
            return

        match = re.search(r'_(\d{6})\.', nombre_evento)
        if not match:
            QMessageBox.warning(self, "Formato inválido", f"No se pudo extraer hora del nombre: {nombre_evento}")
            return
        hora_evento = match.group(1)
        patron = f"*_{fecha_str}_{hora_evento}.mseed"
        archivos_mseed = glob.glob(os.path.join(mseed_dir, patron))
        if not archivos_mseed:
            QMessageBox.warning(self, "Sin archivos mseed", f"No se encontraron archivos mseed para:\n{fecha_str} {hora_evento}\nEn {mseed_dir}")
            return

        estaciones = {}
        for arch in archivos_mseed:
            nombre_arch = os.path.basename(arch)
            est = nombre_arch.split('_')[0]
            estaciones[est] = arch

        dialogo = QDialog(self)
        dialogo.setWindowTitle(f"Seleccionar estación - Evento {nombre_evento}")
        dialogo.setGeometry(300, 300, 400, 200)
        layout = QVBoxLayout(dialogo)

        layout.addWidget(QLabel(f"Evento: {nombre_evento}\nFecha: {fecha_str} Hora: {hora_evento[:2]}:{hora_evento[2:4]}:{hora_evento[4:]}"))
        layout.addWidget(QLabel("Seleccione la estación para cargar el mseed:"))

        combo = QComboBox()
        for est in sorted(estaciones.keys()):
            combo.addItem(est)
        layout.addWidget(combo)

        btn_ver = QPushButton("Ver señal")
        layout.addWidget(btn_ver)

        def cargar_mseed():
            est = combo.currentText()
            ruta_mseed = estaciones[est]
            try:
                st = read(ruta_mseed)
                ventana_mseed = QDialog(dialogo)
                ventana_mseed.setWindowTitle(f"Señal mseed - Estación {est} - {nombre_evento}")
                ventana_mseed.setGeometry(200, 200, 800, 500)
                layout_m = QVBoxLayout(ventana_mseed)
                fig = Figure(figsize=(8, 4))
                canvas = FigureCanvas(fig)
                layout_m.addWidget(canvas)
                ax = fig.add_subplot(111)
                for tr in st:
                    ax.plot(tr.times(), tr.data, label=tr.stats.channel, alpha=0.7)
                ax.set_title(f"Estación {est} - {nombre_evento}")
                ax.set_xlabel("Tiempo (s)")
                ax.set_ylabel("Amplitud")
                ax.legend()
                ax.grid(True)
                fig.tight_layout()
                canvas.draw()
                btn_cerrar = QPushButton("Cerrar")
                layout_m.addWidget(btn_cerrar)
                btn_cerrar.clicked.connect(ventana_mseed.accept)
                ventana_mseed.exec_()
            except Exception as e:
                QMessageBox.critical(dialogo, "Error", f"No se pudo leer el archivo mseed:\n{e}")

        btn_ver.clicked.connect(cargar_mseed)
        dialogo.exec_()

    # ------------------------------------------------------------
    # Métodos auxiliares
    # ------------------------------------------------------------
    def limpiar_interfaz(self):
        self.label_ruta_principal.setText("Directorio principal: ninguno")
        self.label_subcarpeta.setText("Subcarpeta (día): --")
        self.label_archivo.setText("Archivo: --")
        self.label_etiqueta_actual.setText("Etiqueta: ruido (por defecto)")
        self.label_ultimo_sismo.setText("Último sismo: --")
        self.lista_archivos.clear()
        self.tabla_asignaciones.setRowCount(0)
        self.figura.clear()
        self.canvas.draw()
        self.etiquetas.clear()
        self.asociaciones.clear()
        self.fechas_asignadas.clear()
        self.cache_catalogos.clear()
        self.archivos_evt = []
        self.archivo_actual_ruta = None
        self.archivo_referencia_ruta = None
        self.fecha_base_ref_original = None
        self.fecha_base_ref = None
        self.mtime_ref = None
        self.fecha_descarga_str = None
        self.evento_ancla_calibracion = None
        self.periodos_evt = []
        self.referencias_periodos.clear()
        self.eventos_ancla_periodos.clear()
        self.usar_reconstruccion_por_periodos = False

    def obtener_ruta_destino_disponible(self, ruta_destino_base):
        if not os.path.exists(ruta_destino_base):
            return ruta_destino_base
        contador = 1
        while True:
            ruta_candidata = f"{ruta_destino_base}_{contador:03d}"
            if not os.path.exists(ruta_candidata):
                return ruta_candidata
            contador += 1

    def eliminar_directorio_origen(self, ruta_directorio):
        def desbloquear_y_reintentar(funcion, ruta, _exc_info):
            try:
                os.chmod(ruta, stat.S_IWRITE)
                funcion(ruta)
            except Exception:
                raise

        shutil.rmtree(ruta_directorio, onerror=desbloquear_y_reintentar)

    def eliminar_archivo_origen(self, ruta_archivo):
        try:
            os.remove(ruta_archivo)
        except PermissionError:
            os.chmod(ruta_archivo, stat.S_IWRITE)
            os.remove(ruta_archivo)

    def eliminar_carpetas_vacias_origen(self):
        if not self.ruta_descarga_actual or not os.path.isdir(self.ruta_descarga_actual):
            return
        for root, dirs, files in os.walk(self.ruta_descarga_actual, topdown=False):
            if root == self.ruta_descarga_actual:
                continue
            try:
                if not os.listdir(root):
                    os.rmdir(root)
            except OSError:
                continue

    def preclasificar_carpetas_posteriores_2000(self, carpeta_origen):
        if not self.ruta_destino_preclasificacion:
            QMessageBox.warning(self, "Destino requerido", "Seleccione primero la carpeta de destino.")
            return False

        origen_abs = os.path.abspath(carpeta_origen)
        destino_abs = os.path.abspath(self.ruta_destino_preclasificacion)
        try:
            if os.path.commonpath([origen_abs, destino_abs]) == origen_abs:
                QMessageBox.warning(
                    self,
                    "Destino invalido",
                    "La carpeta de destino no puede estar dentro de la carpeta de origen."
                )
                return False
        except ValueError:
            pass

        carpetas_a_mover = []
        try:
            for nombre in os.listdir(carpeta_origen):
                ruta = os.path.join(carpeta_origen, nombre)
                if os.path.isdir(ruta) and es_carpeta_posterior_2000(nombre):
                    carpetas_a_mover.append((nombre, ruta))
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo revisar la carpeta de origen:\n{e}")
            return False

        if not carpetas_a_mover:
            return True

        nombres = "\n".join(f"  {nombre}" for nombre, _ in carpetas_a_mover)
        respuesta = QMessageBox.question(
            self,
            "Mover carpetas posteriores al 2000",
            "Se copiaran integramente estas carpetas al destino y luego se borraran del origen:\n\n"
            f"{nombres}\n\n"
            "Desea continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if respuesta != QMessageBox.Yes:
            return False

        os.makedirs(self.ruta_destino_preclasificacion, exist_ok=True)
        movidas = []
        for nombre, ruta_origen in carpetas_a_mover:
            ruta_destino_base = os.path.join(self.ruta_destino_preclasificacion, nombre)
            ruta_destino = self.obtener_ruta_destino_disponible(ruta_destino_base)
            try:
                shutil.copytree(ruta_origen, ruta_destino)
                self.eliminar_directorio_origen(ruta_origen)
                movidas.append((ruta_origen, ruta_destino))
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error al mover carpetas",
                    f"No se pudo mover:\n{ruta_origen}\n\nError:\n{e}"
                )
                return False

        resumen = "\n".join(f"{os.path.basename(origen)} -> {destino}" for origen, destino in movidas)
        QMessageBox.information(
            self,
            "Preclasificacion completada",
            f"Se movieron {len(movidas)} carpetas posteriores al 2000:\n\n{resumen}"
        )
        return True

    def obtener_fecha_base_desde_carpeta(self, carpeta):
        nombre = os.path.basename(carpeta)
        if len(nombre) == 8 and nombre.isdigit():
            try:
                fecha = datetime.strptime(nombre, "%Y%m%d")
                return fecha.replace(hour=17, minute=0, second=0)
            except:
                pass
        return None

    def encontrar_archivo_referencia(self, carpeta):
        archivo_mas_reciente = None
        fecha_mas_reciente = None
        for root, dirs, files in os.walk(carpeta):
            if root == carpeta:
                dirs[:] = [d for d in dirs if es_carpeta_reseteo_valida(d)]
            for f in files:
                ruta = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(ruta)
                    if fecha_mas_reciente is None or mtime > fecha_mas_reciente:
                        fecha_mas_reciente = mtime
                        archivo_mas_reciente = ruta
                except OSError:
                    continue
        return archivo_mas_reciente, fecha_mas_reciente

    def extraer_serie_evt(self, nombre_archivo):
        nombre_base = os.path.splitext(os.path.basename(nombre_archivo))[0]
        match = re.search(r"([A-Za-z]+)(\d{3})", nombre_base)
        if not match:
            return None, None
        return match.group(1).upper(), int(match.group(2))

    def analizar_posibles_reseteos_evt(self):
        periodos = {}
        sin_patron = []

        for ruta, subcarpeta, nombre, mtime in self.archivos_evt:
            prefijo, numero = self.extraer_serie_evt(nombre)
            if prefijo is None:
                sin_patron.append(nombre)
                continue
            periodos.setdefault(prefijo, []).append((numero, ruta, nombre, subcarpeta, mtime))

        self.periodos_evt = []
        for prefijo, elementos in sorted(periodos.items()):
            elementos_ordenados = sorted(elementos, key=lambda item: (item[0], item[4], item[2]))
            self.periodos_evt.append({
                "prefijo": prefijo,
                "elementos": elementos_ordenados,
                "primer_mtime": min(item[4] for item in elementos_ordenados),
                "ultimo_mtime": max(item[4] for item in elementos_ordenados),
            })
        self.usar_reconstruccion_por_periodos = len(self.periodos_evt) > 1

        if len(periodos) <= 1:
            return

        lineas = ["Se detectaron posibles reseteos del ETNA por cambio de serie EVT:"]
        for prefijo, elementos in sorted(periodos.items()):
            numeros = [numero for numero, _, _, _, _ in elementos]
            lineas.append(
                f"  {prefijo}: {len(elementos)} archivos, "
                f"rango {min(numeros):03d}-{max(numeros):03d}"
            )

        lineas.append("")
        lineas.append("Esto indica varios periodos de marcas dentro de la misma descarga.")
        lineas.append("La correccion por una sola referencia puede no ser suficiente.")

        if sin_patron:
            lineas.append("")
            lineas.append(f"Archivos sin patron de serie reconocido: {len(sin_patron)}")

        QMessageBox.warning(self, "Posibles reseteos EVT", "\n".join(lineas))

    def obtener_periodo_por_ruta(self, ruta_evt):
        for periodo in self.periodos_evt:
            if any(ruta == ruta_evt for _, ruta, _, _, _ in periodo["elementos"]):
                return periodo
        return None

    def obtener_duracion_periodo_segundos(self, periodo):
        inicio_reloj_etna = datetime(1980, 1, 1).timestamp()
        return max(0, periodo["ultimo_mtime"] - inicio_reloj_etna)

    def corregir_fecha_en_periodo(self, ruta_evt, mtime_real):
        periodo = self.obtener_periodo_por_ruta(ruta_evt)
        if periodo is None:
            return self.corregir_fecha(mtime_real)

        referencia_periodo = self.referencias_periodos.get(periodo["prefijo"])
        if referencia_periodo is None:
            return self.corregir_fecha(mtime_real)

        return referencia_periodo["fecha_ultimo_evt"] + timedelta(
            seconds=mtime_real - referencia_periodo["mtime_ultimo_evt"]
        )

    def corregir_fecha_con_referencia(self, mtime_real, fecha_base):
        if self.mtime_ref is None or fecha_base is None:
            return None
        delta = timedelta(seconds=mtime_real - self.mtime_ref)
        return fecha_base + delta

    def corregir_fecha(self, mtime_real):
        return self.corregir_fecha_con_referencia(mtime_real, self.fecha_base_ref)

    def actualizar_info_ultimo_sismo(self):
        if not self.archivos_evt or self.archivo_referencia_ruta is None or self.fecha_base_ref is None:
            self.label_ultimo_sismo.setText("Último sismo: -- (sin referencia)")
            return
        eventos = [(ruta, mtime) for (ruta, _, _, mtime) in self.archivos_evt if self.etiquetas.get(ruta) == "evento"]
        if not eventos:
            self.label_ultimo_sismo.setText("Último sismo: ningún evento marcado")
            return
        ruta_ultimo, mtime_ultimo = max(eventos, key=lambda x: x[1])
        fecha_corregida = self.corregir_fecha_en_periodo(ruta_ultimo, mtime_ultimo)
        if fecha_corregida is None:
            self.label_ultimo_sismo.setText("Último sismo: error en corrección")
            return
        diff = self.fecha_base_ref - fecha_corregida
        if diff.total_seconds() < 0:
            diff_texto = f"(futuro, {abs(diff)} después de referencia?)"
        else:
            dias = diff.days
            horas = diff.seconds // 3600
            minutos = (diff.seconds % 3600) // 60
            if dias > 0:
                diff_texto = f"hace {dias} días, {horas} horas"
            elif horas > 0:
                diff_texto = f"hace {horas} horas, {minutos} minutos"
            else:
                diff_texto = f"hace {minutos} minutos"
        nombre_archivo = os.path.basename(ruta_ultimo)
        self.label_ultimo_sismo.setText(
            f"📅 Último sismo: {nombre_archivo} - {fecha_corregida.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(referencia: {self.fecha_base_ref.strftime('%Y-%m-%d %H:%M:%S')} -> {diff_texto})"
        )

    def mostrar_fechas_sismos(self):
        eventos = [(ruta, mtime, nombre) for (ruta, _, nombre, mtime) in self.archivos_evt if self.etiquetas.get(ruta) == "evento"]
        if not eventos:
            QMessageBox.information(self, "Sin sismos", "No hay archivos marcados como evento.")
            return
        eventos.sort(key=lambda x: x[1], reverse=True)
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Fechas corregidas de sismos")
        dialogo.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout(dialogo)
        texto = QPlainTextEdit()
        texto.setReadOnly(True)
        contenido = ""
        for ruta, mtime, nombre in eventos:
            fecha_corr = self.corregir_fecha_en_periodo(ruta, mtime)
            if fecha_corr:
                contenido += f"{nombre}\n  -> {fecha_corr.strftime('%Y-%m-%d %H:%M:%S')}\n  (ruta: {ruta})\n\n"
            else:
                contenido += f"{nombre}\n  → Error en corrección\n\n"
        texto.setPlainText(contenido)
        layout.addWidget(texto)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialogo.accept)
        layout.addWidget(btn_cerrar)
        dialogo.exec_()

    def seleccionar_carpeta_descarga(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de descarga (ej: 20260306)")
        if not carpeta:
            return

        if not self.ruta_destino_preclasificacion:
            QMessageBox.warning(self, "Destino requerido", "Seleccione primero la carpeta de destino.")
            return

        if not self.preclasificar_carpetas_posteriores_2000(carpeta):
            return

        self.limpiar_interfaz()

        self.ruta_descarga_actual = carpeta
        self.label_ruta_principal.setText(f"Directorio principal: {carpeta}")
        nombre_carpeta = os.path.basename(carpeta)
        if len(nombre_carpeta) == 8 and nombre_carpeta.isdigit():
            self.fecha_descarga_str = nombre_carpeta
            self.evento_ancla_calibracion = None
        else:
            self.fecha_descarga_str = None
            self.evento_ancla_calibracion = None
            QMessageBox.warning(self, "Formato de carpeta", "La carpeta no tiene nombre AAAAMMDD.")

        # Establecer la referencia original
        self.fecha_base_ref_original = self.obtener_fecha_base_desde_carpeta(carpeta)
        if self.fecha_base_ref_original is None:
            QMessageBox.warning(self, "Formato inválido", "No se puede establecer referencia horaria.")
            self.fecha_base_ref_original = None
        self.fecha_base_ref = self.fecha_base_ref_original  # inicialmente igual

        self.archivo_referencia_ruta, self.mtime_ref = self.encontrar_archivo_referencia(carpeta)
        if self.archivo_referencia_ruta is None:
            QMessageBox.warning(self, "Sin referencia", "No se pudo determinar el archivo más reciente.")
            self.mtime_ref = None

        # Recorrer archivos EVT
        for root, dirs, files in os.walk(carpeta):
            if root == carpeta:
                dirs[:] = [d for d in dirs if es_carpeta_reseteo_valida(d)]
            for f in files:
                if f.lower().endswith('.evt'):
                    ruta_completa = os.path.join(root, f)
                    subcarpeta = os.path.basename(root)
                    try:
                        mtime = os.path.getmtime(ruta_completa)
                    except OSError:
                        mtime = 0
                    self.archivos_evt.append((ruta_completa, subcarpeta, f, mtime))

        if not self.archivos_evt:
            QMessageBox.information(self, "Sin archivos", "No se encontraron archivos .evt.")
            return

        self.archivos_evt.sort(key=lambda x: x[0])
        self.analizar_posibles_reseteos_evt()
        for ruta, subcarpeta, nombre, mtime in self.archivos_evt:
            self.etiquetas[ruta] = "ruido"
            item = QListWidgetItem(f"{subcarpeta}/{nombre}")
            if ruta == self.archivo_referencia_ruta:

                item.setText(f"[REF] {subcarpeta}/{nombre}")
            item.setForeground(QColor("red"))
            self.lista_archivos.addItem(item)

        QMessageBox.information(self, "Archivos encontrados", f"Se encontraron {len(self.archivos_evt)} archivos .evt\nTodos marcados como RUIDO por defecto.")
        self.lista_archivos.setCurrentRow(0)
        self.actualizar_info_ultimo_sismo()

    def cargar_archivo_desde_lista(self, current, previous):
        if current is None:
            return
        idx = self.lista_archivos.row(current)
        ruta_completa, subcarpeta, nombre_archivo, mtime_real = self.archivos_evt[idx]
        self.archivo_actual_ruta = ruta_completa
        self.label_subcarpeta.setText(f"Subcarpeta (día): {subcarpeta}")
        self.label_archivo.setText(f"Archivo: {nombre_archivo}")
        etiqueta = self.etiquetas.get(ruta_completa, "ruido")
        self.label_etiqueta_actual.setText(f"Etiqueta: {etiqueta}")
        self.cargar_y_graficar_evt(ruta_completa, mtime_real)

    def cargar_y_graficar_evt(self, ruta_archivo, mtime_real=None):
        try:
            st = read(ruta_archivo)
            n_trazas = len(st)
            if n_trazas == 0:
                raise ValueError("El archivo no contiene ninguna traza.")
            if mtime_real is None:
                try:
                    mtime_real = os.path.getmtime(ruta_archivo)
                except:
                    mtime_real = 0
            # No mostramos metadatos, solo gráfica
            self.graficar_componentes(st)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo EVT:\n{e}")
            self.figura.clear()
            self.canvas.draw()

    def graficar_componentes(self, stream):
        self.figura.clear()
        n = len(stream)
        if n > 3:
            QMessageBox.warning(self, "Más de 3 canales", f"El archivo tiene {n} canales. Se graficarán solo los 3 primeros.")
            n = 3
        gs = GridSpec(n, 1, figure=self.figura, hspace=0.3)
        for i in range(n):
            tr = stream[i]
            ax = self.figura.add_subplot(gs[i])
            tiempo = tr.times()
            ax.plot(tiempo, tr.data, 'k-', linewidth=0.8)
            canal = tr.stats.get('channel', f'Componente {i+1}')
            ax.set_ylabel(canal)
            ax.grid(True, alpha=0.3)
            if i == n-1:
                ax.set_xlabel("Tiempo (s)")
            else:
                ax.set_xticklabels([])
            max_val = np.max(np.abs(tr.data))
            duracion = tr.stats.npts / tr.stats.sampling_rate
            ax.set_title(f"{canal} | máx={max_val:.4g} | dur={duracion:.1f}s", fontsize=9)
        self.canvas.draw()

    def marcar_actual(self, tipo):
        if self.archivo_actual_ruta is None:
            QMessageBox.warning(self, "Sin archivo", "No hay ningún archivo cargado para marcar.")
            return
        self.etiquetas[self.archivo_actual_ruta] = tipo
        current_item = self.lista_archivos.currentItem()
        if current_item:
            if tipo == "evento":
                if self.archivo_actual_ruta in self.asociaciones:
                    current_item.setForeground(QColor("darkgreen"))
                else:
                    current_item.setForeground(QColor("green"))
            else:
                if self.archivo_actual_ruta in self.asociaciones:
                    del self.asociaciones[self.archivo_actual_ruta]
                current_item.setForeground(QColor("red"))
        self.label_etiqueta_actual.setText(f"Etiqueta: {tipo}")
        self.actualizar_info_ultimo_sismo()

    def exportar_todos_evt(self, directorio_destino):
        if not self.archivos_evt:
            return False
        try:
            os.makedirs(directorio_destino, exist_ok=True)
            self.ultimo_resumen_exportacion = []
            for ruta_original, sub, nombre_original, mtime in self.archivos_evt:
                fecha_corr = self.corregir_fecha_en_periodo(ruta_original, mtime)
                if fecha_corr is None:
                    continue

                # Obtener la fecha asignada del catálogo, si no tiene asignación usar fecha corregida
                fecha_destino = self.fechas_asignadas.get(ruta_original)
                if fecha_destino is None:
                    fecha_destino = fecha_corr

                # Carpeta con formato AAAAMMDD
                carpeta_fecha = fecha_destino.strftime("%Y%m%d")
                ruta_carpeta_destino = os.path.join(directorio_destino, carpeta_fecha)
                os.makedirs(ruta_carpeta_destino, exist_ok=True)

                # Mantener el nombre original del archivo
                ruta_destino = os.path.join(ruta_carpeta_destino, nombre_original)

                # Manejar colisión de nombres (si ya existe en esa subcarpeta)
                nombre_base, ext = os.path.splitext(nombre_original)
                contador = 1
                while os.path.exists(ruta_destino):
                    nombre_nuevo = f"{nombre_base}_{contador:03d}{ext}"
                    ruta_destino = os.path.join(ruta_carpeta_destino, nombre_nuevo)
                    contador += 1

                # Copiar archivo y modificar su fecha de modificación a la asignada/corregida
                shutil.copy2(ruta_original, ruta_destino)
                marca_tiempo = fecha_destino.timestamp()
                os.utime(ruta_destino, (marca_tiempo, marca_tiempo))
                if not os.path.exists(ruta_destino) or os.path.getsize(ruta_destino) == 0:
                    raise IOError(f"La copia no quedo valida en destino: {ruta_destino}")
                self.eliminar_archivo_origen(ruta_original)

                etiqueta = self.etiquetas.get(ruta_original, "ruido")
                self.ultimo_resumen_exportacion.append([
                    ruta_original,
                    ruta_destino,
                    etiqueta,
                    fecha_destino.strftime("%Y-%m-%d %H:%M:%S"),
                    sub,
                    nombre_original,
                    "si",
                ])
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar: {e}")
            return False

    def guardar_eventos(self):
        if not self.archivos_evt:
            QMessageBox.warning(self, "Sin datos", "No hay archivos EVT para exportar.")
            return

        destino = self.ruta_destino_preclasificacion
        if not destino:
            QMessageBox.warning(self, "Destino requerido", "Seleccione primero la carpeta de destino.")
            return

        if self.exportar_todos_evt(destino):
            self.eliminar_carpetas_vacias_origen()
            QMessageBox.information(self, "Exportación", f"Archivos EVT exportados a:\n{destino}")

        if getattr(self, "ultimo_resumen_exportacion", None):
            archivo_resumen = os.path.join(destino, "evt_exportados_todos.csv")
            try:
                with open(archivo_resumen, "w", encoding="utf-8", newline="") as f:
                    escritor = csv.writer(f, delimiter=";")
                    escritor.writerow(["ruta_original", "ruta_exportada", "etiqueta", "fecha_corregida", "subcarpeta", "nombre_original", "origen_borrado"])
                    escritor.writerows(self.ultimo_resumen_exportacion)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar resumen de exportacion: {e}")
        rutas_eventos = [ruta for ruta, tipo in self.etiquetas.items() if tipo == "evento"]
        if rutas_eventos:
            archivo_salida = os.path.join(destino, "eventos_sismos.txt")
            try:
                with open(archivo_salida, "w", encoding="utf-8") as f:
                    for ruta in rutas_eventos:
                        f.write(ruta + "\n")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar eventos: {e}")

        if self.asociaciones:
            archivo_asoc = os.path.join(destino, "asociaciones_sismos.txt")
            try:
                with open(archivo_asoc, "w", encoding="utf-8") as f:
                    for ruta, num in self.asociaciones.items():
                        f.write(f"{ruta};{num}\n")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar asignaciones: {e}")

        self.limpiar_interfaz()

    def salir(self):
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VisorEVT()
    ventana.show()
    sys.exit(app.exec_())
