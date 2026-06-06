import sys
from datetime import datetime, time
from pathlib import Path
import math

import pandas as pd
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QDateEdit,
    QTextEdit,
    QSizePolicy,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates


class VentanaNivelesEmbalse(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Graficador de niveles de embalse")
        self.resize(1300, 850)

        self.datos_completos = pd.DataFrame()
        self.datos_filtrados = pd.DataFrame()

        self.tipo_archivo_adicional = None
        self.datos_caudales = pd.DataFrame()
        self.fechas_geoelectricas = pd.DataFrame()
        self.datos_caudales_filtrados = pd.DataFrame()
        self.fechas_geoelectricas_filtradas = pd.DataFrame()

        self.fecha_referencia_dxf = None
        self.inicializar_interfaz()

    def inicializar_interfaz(self):
        layout_principal = QVBoxLayout(self)

        layout_archivo = QGridLayout()
        layout_archivo.setColumnStretch(0, 0)
        layout_archivo.setColumnStretch(1, 1)
        layout_archivo.setColumnStretch(2, 0)
        layout_archivo.setColumnStretch(3, 0)
        layout_archivo.setColumnStretch(4, 1)

        etiqueta_archivo = QLabel("Archivo de niveles:")
        self.txt_archivo = QLineEdit()
        self.txt_archivo.setReadOnly(True)
        boton_buscar = QPushButton("Buscar")
        boton_buscar.clicked.connect(self.seleccionar_archivo_niveles)

        layout_archivo.addWidget(etiqueta_archivo, 0, 0)
        layout_archivo.addWidget(self.txt_archivo, 0, 1, 1, 3)
        layout_archivo.addWidget(boton_buscar, 0, 4)

        etiqueta_adicional = QLabel("Archivo adicional:")
        self.txt_archivo_adicional = QLineEdit()
        self.txt_archivo_adicional.setReadOnly(True)
        boton_buscar_adicional = QPushButton("Buscar")
        boton_buscar_adicional.clicked.connect(self.seleccionar_archivo_adicional)

        layout_archivo.addWidget(etiqueta_adicional, 1, 0)
        layout_archivo.addWidget(self.txt_archivo_adicional, 1, 1, 1, 3)
        layout_archivo.addWidget(boton_buscar_adicional, 1, 4)

        etiqueta_inicio = QLabel("Fecha inicial:")
        self.fecha_inicial = QDateEdit()
        self.fecha_inicial.setCalendarPopup(True)
        self.fecha_inicial.setDisplayFormat("dd/MM/yyyy")
        self.fecha_inicial.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        etiqueta_fin = QLabel("Fecha final:")
        self.fecha_final = QDateEdit()
        self.fecha_final.setCalendarPopup(True)
        self.fecha_final.setDisplayFormat("dd/MM/yyyy")
        self.fecha_final.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        ancho_fechas = 150
        self.fecha_inicial.setMinimumWidth(ancho_fechas)
        self.fecha_final.setMinimumWidth(ancho_fechas)
        self.fecha_inicial.setMaximumWidth(ancho_fechas)
        self.fecha_final.setMaximumWidth(ancho_fechas)

        layout_archivo.addWidget(etiqueta_inicio, 2, 0)
        layout_archivo.addWidget(self.fecha_inicial, 2, 1)
        layout_archivo.addWidget(etiqueta_fin, 2, 3)
        layout_archivo.addWidget(self.fecha_final, 2, 4)

        layout_botones = QHBoxLayout()
        self.boton_cargar_niveles = QPushButton("Cargar niveles")
        self.boton_cargar_niveles.clicked.connect(self.cargar_archivo_niveles)
        self.boton_cargar_adicional = QPushButton("Cargar adicional")
        self.boton_cargar_adicional.clicked.connect(self.cargar_archivo_adicional)
        self.boton_graficar = QPushButton("Graficar")
        self.boton_graficar.clicked.connect(self.graficar_datos)
        self.boton_guardar = QPushButton("Guardar CSV + DXF")
        self.boton_guardar.clicked.connect(self.guardar_archivos_salida)

        layout_botones.addWidget(self.boton_cargar_niveles)
        layout_botones.addWidget(self.boton_cargar_adicional)
        layout_botones.addWidget(self.boton_graficar)
        layout_botones.addWidget(self.boton_guardar)

        self.figura = Figure(figsize=(11, 7))
        self.canvas = FigureCanvas(self.figura)
        self.barra_navegacion = NavigationToolbar(self.canvas, self)

        self.txt_estado = QTextEdit()
        self.txt_estado.setReadOnly(True)
        self.txt_estado.setMaximumHeight(170)

        layout_principal.addLayout(layout_archivo)
        layout_principal.addLayout(layout_botones)
        layout_principal.addWidget(self.barra_navegacion)
        layout_principal.addWidget(self.canvas)
        layout_principal.addWidget(QLabel("Estado del proceso:"))
        layout_principal.addWidget(self.txt_estado)

    def registrar_mensaje(self, mensaje):
        self.txt_estado.append(mensaje)

    def limpiar_capa_adicional(self):
        self.tipo_archivo_adicional = None
        self.datos_caudales = pd.DataFrame()
        self.fechas_geoelectricas = pd.DataFrame()
        self.datos_caudales_filtrados = pd.DataFrame()
        self.fechas_geoelectricas_filtradas = pd.DataFrame()

    def seleccionar_archivo_niveles(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de niveles",
            "",
            "Archivos CSV (*.csv);;Todos los archivos (*)",
        )
        if ruta_archivo:
            self.txt_archivo.setText(ruta_archivo)
            self.registrar_mensaje(f"Archivo de niveles seleccionado: {ruta_archivo}")

    def seleccionar_archivo_adicional(self):
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo adicional",
            "",
            "Archivos CSV (*.csv);;Todos los archivos (*)",
        )
        if ruta_archivo:
            self.txt_archivo_adicional.setText(ruta_archivo)
            self.registrar_mensaje(f"Archivo adicional seleccionado: {ruta_archivo}")

    def cargar_archivo_niveles(self):
        ruta_archivo = self.txt_archivo.text().strip()
        if not ruta_archivo:
            QMessageBox.warning(self, "Advertencia", "Seleccione primero un archivo de niveles.")
            return

        try:
            registros = []
            with open(ruta_archivo, "r", encoding="utf-8") as archivo:
                for numero_linea, linea in enumerate(archivo, start=1):
                    linea = linea.strip()
                    if not linea or linea.startswith("#"):
                        continue

                    partes = linea.split(";")
                    if len(partes) < 3:
                        self.registrar_mensaje(
                            f"Línea ignorada por formato incompleto en niveles ({numero_linea}): {linea}"
                        )
                        continue

                    registros.append([partes[0].strip(), partes[1].strip(), partes[2].strip()])

            if not registros:
                QMessageBox.warning(self, "Advertencia", "No se encontraron datos válidos en el archivo de niveles.")
                return

            datos = pd.DataFrame(registros, columns=["identificador", "fecha", "nivel"])
            datos["fecha"] = pd.to_datetime(datos["fecha"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
            datos["nivel"] = pd.to_numeric(datos["nivel"], errors="coerce")
            datos = datos.dropna(subset=["fecha", "nivel"]).sort_values("fecha").reset_index(drop=True)

            if datos.empty:
                QMessageBox.warning(self, "Advertencia", "No quedaron registros válidos en el archivo de niveles.")
                return

            self.datos_completos = datos
            fecha_minima = datos["fecha"].min()
            fecha_maxima = datos["fecha"].max()

            self.fecha_inicial.setDate(QDate(fecha_minima.year, fecha_minima.month, fecha_minima.day))
            self.fecha_final.setDate(QDate(fecha_maxima.year, fecha_maxima.month, fecha_maxima.day))

            self.registrar_mensaje(f"Archivo de niveles cargado correctamente. Registros válidos: {len(datos)}")
            self.registrar_mensaje(
                f"Rango detectado en niveles: {fecha_minima.strftime('%d/%m/%Y %H:%M:%S')} a {fecha_maxima.strftime('%d/%m/%Y %H:%M:%S')}"
            )
            self.registrar_mensaje(f"Identificador encontrado: {datos['identificador'].iloc[0]}")
            self.graficar_datos()

        except UnicodeDecodeError:
            QMessageBox.critical(self, "Error", "No se pudo leer el archivo de niveles con codificación UTF-8.")
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Ocurrió un problema al cargar el archivo de niveles:\n{error}")

    def detectar_tipo_archivo_adicional(self, lineas_validas):
        cantidad_caudales = 0
        cantidad_fechas = 0

        for linea in lineas_validas:
            partes = [parte.strip() for parte in linea.split(";")]

            if len(partes) >= 3:
                fecha_caudal = pd.to_datetime(partes[0], format="%Y%m%d_%H%M%S.sis", errors="coerce")
                valor_caudal = pd.to_numeric(partes[1], errors="coerce")
                bandera = pd.to_numeric(partes[2], errors="coerce")
                if pd.notna(fecha_caudal) and pd.notna(valor_caudal) and pd.notna(bandera):
                    cantidad_caudales += 1
                    continue

            if len(partes) == 1:
                fecha_simple = pd.to_datetime(partes[0], format="%Y_%m_%d", errors="coerce")
                if pd.notna(fecha_simple):
                    cantidad_fechas += 1
                    continue

        if cantidad_caudales > 0 and cantidad_fechas == 0:
            return "caudales"
        if cantidad_fechas > 0 and cantidad_caudales == 0:
            return "fechas"
        if cantidad_caudales > 0 and cantidad_fechas > 0:
            if cantidad_caudales >= cantidad_fechas:
                return "caudales"
            return "fechas"
        return None

    def cargar_archivo_adicional(self):
        ruta_archivo = self.txt_archivo_adicional.text().strip()
        self.limpiar_capa_adicional()

        if not ruta_archivo:
            self.registrar_mensaje("No se seleccionó archivo adicional. El gráfico seguirá solo con niveles.")
            self.graficar_datos()
            return

        try:
            lineas_validas = []
            with open(ruta_archivo, "r", encoding="utf-8") as archivo:
                for linea in archivo:
                    linea = linea.strip()
                    if not linea or linea.startswith("#"):
                        continue
                    lineas_validas.append(linea)

            if not lineas_validas:
                QMessageBox.warning(self, "Advertencia", "No se encontraron datos válidos en el archivo adicional.")
                return

            tipo_detectado = self.detectar_tipo_archivo_adicional(lineas_validas)
            if tipo_detectado is None:
                QMessageBox.warning(
                    self,
                    "Advertencia",
                    "No se pudo reconocer el formato del archivo adicional. Debe ser de caudales o de fechas.",
                )
                return

            if tipo_detectado == "caudales":
                registros = []
                for numero_linea, linea in enumerate(lineas_validas, start=1):
                    partes = [parte.strip() for parte in linea.split(";")]
                    if len(partes) < 3:
                        self.registrar_mensaje(
                            f"Línea ignorada por formato incompleto en archivo adicional ({numero_linea}): {linea}"
                        )
                        continue
                    registros.append([partes[0], partes[1], partes[2]])

                datos = pd.DataFrame(registros, columns=["archivo", "caudal", "bandera"])
                datos["fecha"] = pd.to_datetime(datos["archivo"], format="%Y%m%d_%H%M%S.sis", errors="coerce")
                datos["caudal"] = pd.to_numeric(datos["caudal"], errors="coerce")
                datos["bandera"] = pd.to_numeric(datos["bandera"], errors="coerce")
                datos = datos.dropna(subset=["fecha", "caudal", "bandera"])
                datos = datos[datos["bandera"] != 0].copy()
                datos = datos.sort_values("fecha").reset_index(drop=True)

                self.tipo_archivo_adicional = "caudales"
                self.datos_caudales = datos
                if datos.empty:
                    self.registrar_mensaje(
                        "Archivo adicional reconocido como caudales, pero todos los registros quedaron descartados por bandera 0 o errores de formato."
                    )
                else:
                    self.registrar_mensaje(f"Archivo adicional reconocido como caudales. Registros válidos: {len(datos)}")
                    self.registrar_mensaje(
                        f"Rango detectado en caudales: {datos['fecha'].min().strftime('%d/%m/%Y %H:%M:%S')} a {datos['fecha'].max().strftime('%d/%m/%Y %H:%M:%S')}"
                    )

            elif tipo_detectado == "fechas":
                datos = pd.DataFrame(lineas_validas, columns=["fecha_texto"])
                datos["fecha"] = pd.to_datetime(datos["fecha_texto"], format="%Y_%m_%d", errors="coerce")
                datos = datos.dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)

                self.tipo_archivo_adicional = "fechas"
                self.fechas_geoelectricas = datos
                if datos.empty:
                    self.registrar_mensaje(
                        "Archivo adicional reconocido como fechas, pero no quedaron registros válidos con formato AAAA_MM_DD."
                    )
                else:
                    self.registrar_mensaje(f"Archivo adicional reconocido como fechas. Registros válidos: {len(datos)}")
                    self.registrar_mensaje(
                        f"Rango detectado en fechas: {datos['fecha'].min().strftime('%d/%m/%Y')} a {datos['fecha'].max().strftime('%d/%m/%Y')}"
                    )

            self.graficar_datos()

        except UnicodeDecodeError:
            QMessageBox.critical(self, "Error", "No se pudo leer el archivo adicional con codificación UTF-8.")
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Ocurrió un problema al cargar el archivo adicional:\n{error}")

    def obtener_fechas_extremo(self):
        fecha_inicial = datetime.combine(self.fecha_inicial.date().toPyDate(), time(0, 0, 0))
        fecha_final = datetime.combine(self.fecha_final.date().toPyDate(), time(23, 59, 59))
        return fecha_inicial, fecha_final

    def obtener_datos_filtrados(self):
        if self.datos_completos.empty:
            QMessageBox.warning(self, "Advertencia", "Primero cargue un archivo de niveles.")
            return pd.DataFrame()

        fecha_inicial, fecha_final = self.obtener_fechas_extremo()
        if fecha_inicial > fecha_final:
            QMessageBox.warning(self, "Advertencia", "La fecha inicial no puede ser mayor que la fecha final.")
            return pd.DataFrame()

        datos_filtrados = self.datos_completos[
            (self.datos_completos["fecha"] >= fecha_inicial)
            & (self.datos_completos["fecha"] <= fecha_final)
        ].copy()

        if datos_filtrados.empty:
            QMessageBox.warning(self, "Advertencia", "No existen datos de niveles dentro del rango seleccionado.")
            return pd.DataFrame()

        self.datos_filtrados = datos_filtrados
        self.datos_caudales_filtrados = pd.DataFrame()
        self.fechas_geoelectricas_filtradas = pd.DataFrame()

        if self.tipo_archivo_adicional == "caudales" and not self.datos_caudales.empty:
            self.datos_caudales_filtrados = self.datos_caudales[
                (self.datos_caudales["fecha"] >= fecha_inicial)
                & (self.datos_caudales["fecha"] <= fecha_final)
            ].copy()

        if self.tipo_archivo_adicional == "fechas" and not self.fechas_geoelectricas.empty:
            fecha_inicial_normalizada = pd.Timestamp(fecha_inicial).normalize()
            fecha_final_normalizada = pd.Timestamp(fecha_final).normalize()
            self.fechas_geoelectricas_filtradas = self.fechas_geoelectricas[
                (self.fechas_geoelectricas["fecha"] >= fecha_inicial_normalizada)
                & (self.fechas_geoelectricas["fecha"] <= fecha_final_normalizada)
            ].copy()

        return datos_filtrados

    def calcular_paso_representativo(self, valor_maximo):
        if valor_maximo <= 0:
            return 1

        cantidad_objetivo_divisiones = 6
        paso_aproximado = valor_maximo / cantidad_objetivo_divisiones
        base = 10 ** math.floor(math.log10(paso_aproximado))

        for multiplicador in [1, 2, 5, 10]:
            paso = base * multiplicador
            if paso >= paso_aproximado:
                return int(paso) if paso >= 1 else paso

        return max(1, int(math.ceil(paso_aproximado)))

    def obtener_ticks_nivel(self, datos_nivel):
        maximo = float(datos_nivel["nivel"].max()) if not datos_nivel.empty else 1.0
        paso = self.calcular_paso_representativo(maximo)
        nivel_superior = math.ceil(maximo / paso) * paso
        if nivel_superior <= 0:
            nivel_superior = paso
        ticks = list(range(0, int(nivel_superior) + int(paso), int(paso))) if paso >= 1 else [0, nivel_superior]
        if len(ticks) == 1:
            ticks = [0, paso]
        return ticks, nivel_superior, paso

    def obtener_intervalo_dias_menores(self, fecha_inicial, fecha_final):
        dias_rango = max((fecha_final - fecha_inicial).days + 1, 1)
        if dias_rango <= 31:
            return 1
        if dias_rango <= 93:
            return 3
        if dias_rango <= 186:
            return 7
        return 15

    def graficar_datos(self):
        datos_filtrados = self.obtener_datos_filtrados()
        if datos_filtrados.empty:
            return

        fecha_inicial, fecha_final = self.obtener_fechas_extremo()
        ticks_nivel, nivel_superior, paso_nivel = self.obtener_ticks_nivel(datos_filtrados)
        intervalo_dias = self.obtener_intervalo_dias_menores(fecha_inicial, fecha_final)

        self.figura.clear()
        eje = self.figura.add_subplot(111)

        linea_nivel, = eje.plot(
            datos_filtrados["fecha"],
            datos_filtrados["nivel"],
            linewidth=1.8,
            label="Nivel embalse",
        )

        eje.set_title("Niveles del embalse")
        eje.set_xlabel("Tiempo")
        eje.set_ylabel("Nivel [m]")
        eje.set_xlim(fecha_inicial, fecha_final)
        eje.set_ylim(0, nivel_superior)
        eje.set_yticks(ticks_nivel)

        eje.xaxis.set_major_locator(mdates.MonthLocator())
        eje.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        eje.xaxis.set_minor_locator(mdates.DayLocator(interval=intervalo_dias))
        eje.xaxis.set_minor_formatter(mdates.DateFormatter("%d"))

        eje.tick_params(axis="x", which="major", pad=24, labelsize=10)
        eje.tick_params(axis="x", which="minor", pad=6, labelsize=8, rotation=90)
        eje.tick_params(axis="y", which="major", labelsize=10)

        eje.grid(True, which="major", axis="y", linewidth=0.9)
        eje.grid(True, which="major", axis="x", linewidth=0.8, alpha=0.7)
        eje.grid(True, which="minor", axis="x", linewidth=0.35, alpha=0.45)

        linea_inicio = eje.axvline(fecha_inicial, linewidth=2.2, linestyle="--", label="Inicio período")
        eje.annotate(
            f"Inicio: {fecha_inicial.strftime('%d/%m/%Y')}",
            xy=(fecha_inicial, nivel_superior),
            xytext=(10, -10),
            textcoords="offset points",
            ha="left",
            va="top",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=0.8),
        )

        objetos_leyenda = [linea_nivel, linea_inicio]
        etiquetas_leyenda = ["Nivel embalse", "Inicio período"]

        if self.tipo_archivo_adicional == "caudales":
            if not self.datos_caudales_filtrados.empty:
                eje_caudal = eje.twinx()
                maximo_caudal = float(self.datos_caudales_filtrados["caudal"].max())
                paso_caudal = self.calcular_paso_representativo(maximo_caudal)
                caudal_superior = math.ceil(maximo_caudal / paso_caudal) * paso_caudal
                if caudal_superior <= 0:
                    caudal_superior = paso_caudal

                ticks_caudal = list(range(0, int(caudal_superior) + int(paso_caudal), int(paso_caudal)))
                if len(ticks_caudal) <= 1:
                    ticks_caudal = [0, int(max(1, paso_caudal))]

                linea_caudal, = eje_caudal.plot(
                    self.datos_caudales_filtrados["fecha"],
                    self.datos_caudales_filtrados["caudal"],
                    linewidth=1.3,
                    linestyle="-.",
                    marker="o",
                    markersize=3,
                    label="Caudal",
                )
                eje_caudal.set_ylabel("Caudal [cm³/s]")
                eje_caudal.set_ylim(0, caudal_superior)
                eje_caudal.set_yticks(ticks_caudal)
                eje_caudal.tick_params(axis="y", which="major", labelsize=10)

                objetos_leyenda.append(linea_caudal)
                etiquetas_leyenda.append("Caudal")
                self.registrar_mensaje(
                    f"Caudales montados en el gráfico: {len(self.datos_caudales_filtrados)} registros válidos en el período."
                )
            else:
                self.registrar_mensaje("El archivo adicional es de caudales, pero no hay registros válidos dentro del período seleccionado.")

        elif self.tipo_archivo_adicional == "fechas":
            if not self.fechas_geoelectricas_filtradas.empty:
                primer_evento = None
                for fecha_evento in self.fechas_geoelectricas_filtradas["fecha"]:
                    linea_evento = eje.axvline(pd.Timestamp(fecha_evento), linewidth=1.3, linestyle=":", alpha=0.9)
                    if primer_evento is None:
                        primer_evento = linea_evento

                if primer_evento is not None:
                    objetos_leyenda.append(primer_evento)
                    etiquetas_leyenda.append("Fecha adicional")

                self.registrar_mensaje(
                    f"Fechas adicionales montadas en el gráfico: {len(self.fechas_geoelectricas_filtradas)} líneas verticales en el período."
                )
            else:
                self.registrar_mensaje("El archivo adicional es de fechas, pero no hay eventos dentro del período seleccionado.")
        else:
            self.registrar_mensaje("No se ha cargado archivo adicional. El gráfico muestra solo niveles.")

        eje.legend(objetos_leyenda, etiquetas_leyenda, loc="upper right")
        self.figura.subplots_adjust(bottom=0.22, right=0.88)
        self.canvas.draw()

        self.registrar_mensaje(
            f"Gráfico actualizado con {len(datos_filtrados)} registros de nivel entre "
            f"{datos_filtrados['fecha'].min().strftime('%d/%m/%Y %H:%M:%S')} y "
            f"{datos_filtrados['fecha'].max().strftime('%d/%m/%Y %H:%M:%S')}"
        )
        self.registrar_mensaje(
            f"Período solicitado: {fecha_inicial.strftime('%d/%m/%Y 00:00:00')} a {fecha_final.strftime('%d/%m/%Y 23:59:59')}"
        )
        self.registrar_mensaje(
            f"Escala vertical de nivel aplicada desde 0 hasta {nivel_superior} m, con divisiones de {paso_nivel} m."
        )

    def construir_datos_salida(self, datos_filtrados):
        fecha_referencia = pd.Timestamp(datetime.combine(self.fecha_inicial.date().toPyDate(), time(0, 0, 0)))
        datos_salida = datos_filtrados.copy()
        datos_salida["tiempo_dias"] = (datos_salida["fecha"] - fecha_referencia).dt.total_seconds() / 86400.0
        self.fecha_referencia_dxf = fecha_referencia
        return datos_salida

    def guardar_csv_chanlud(self, ruta_csv, datos_salida):
        with open(ruta_csv, "w", encoding="utf-8") as archivo_salida:
            for _, fila in datos_salida.iterrows():
                tiempo_texto = f"{fila['tiempo_dias']:.9f}".rstrip("0").rstrip(".")
                nivel_texto = f"{fila['nivel']:.8f}".rstrip("0").rstrip(".")
                archivo_salida.write(f"{tiempo_texto};{nivel_texto}\n")

    def guardar_dxf_grafico(self, ruta_dxf, datos_salida):
        if datos_salida.empty:
            return

        x_min = 0.0
        x_max = float(datos_salida["tiempo_dias"].max())
        if x_max <= x_min:
            x_max = x_min + 1.0

        ticks_nivel, y_max, paso_nivel = self.obtener_ticks_nivel(datos_salida)
        y_min = 0.0

        margen_x = max((x_max - x_min) * 0.05, 0.5)
        margen_y = max((y_max - y_min) * 0.08, 0.5)
        x0, x1, y0, y1 = x_min, x_max, y_min, y_max

        puntos_nivel = [(float(fila["tiempo_dias"]), float(fila["nivel"])) for _, fila in datos_salida.iterrows()]

        caudales_salida = pd.DataFrame()
        caudal_superior = None
        paso_caudal = None
        if self.tipo_archivo_adicional == "caudales" and not self.datos_caudales_filtrados.empty:
            caudales_salida = self.datos_caudales_filtrados.copy()
            caudales_salida["tiempo_dias"] = (
                caudales_salida["fecha"] - self.fecha_referencia_dxf
            ).dt.total_seconds() / 86400.0
            maximo_caudal = float(caudales_salida["caudal"].max())
            paso_caudal = self.calcular_paso_representativo(maximo_caudal)
            caudal_superior = math.ceil(maximo_caudal / paso_caudal) * paso_caudal
            if caudal_superior <= 0:
                caudal_superior = paso_caudal

        contenido = []

        def agregar(codigo, valor):
            contenido.append(str(codigo))
            contenido.append(str(valor))

        def agregar_texto(x, y, texto, alto=0.3, alineacion_horizontal=None, x_alineacion=None, y_alineacion=None):
            agregar(0, "TEXT")
            agregar(8, "TEXTOS")
            agregar(10, x)
            agregar(20, y)
            agregar(40, alto)
            if alineacion_horizontal is not None:
                agregar(72, alineacion_horizontal)
            agregar(1, texto)
            if x_alineacion is not None:
                agregar(11, x_alineacion)
            if y_alineacion is not None:
                agregar(21, y_alineacion)

        agregar(0, "SECTION")
        agregar(2, "HEADER")
        agregar(0, "ENDSEC")
        agregar(0, "SECTION")
        agregar(2, "TABLES")
        agregar(0, "ENDSEC")
        agregar(0, "SECTION")
        agregar(2, "ENTITIES")

        agregar(0, "LINE")
        agregar(8, "EJES")
        agregar(10, x0)
        agregar(20, y0)
        agregar(11, x1)
        agregar(21, y0)

        agregar(0, "LINE")
        agregar(8, "EJES")
        agregar(10, x0)
        agregar(20, y0)
        agregar(11, x0)
        agregar(21, y1)

        for tick in ticks_nivel:
            agregar(0, "LINE")
            agregar(8, "MALLA")
            agregar(10, x0)
            agregar(20, tick)
            agregar(11, x1)
            agregar(21, tick)

            agregar(0, "LINE")
            agregar(8, "MARCAS")
            agregar(10, x0 - margen_x * 0.02)
            agregar(20, tick)
            agregar(11, x0)
            agregar(21, tick)
            agregar_texto(x0 - margen_x * 0.08, tick - 0.08, str(int(tick)), alto=max(y1 * 0.02, 0.18))

        fecha_inicio = self.fecha_referencia_dxf
        fecha_final = fecha_inicio + pd.to_timedelta(x1, unit="D")
        meses = pd.date_range(fecha_inicio.normalize(), fecha_final.normalize(), freq="MS")
        if len(meses) == 0 or meses[0] != fecha_inicio.normalize():
            meses = meses.insert(0, fecha_inicio.normalize())

        for fecha_mes in meses:
            posicion = (fecha_mes - fecha_inicio).total_seconds() / 86400.0
            if x0 <= posicion <= x1:
                agregar(0, "LINE")
                agregar(8, "MALLA_X")
                agregar(10, posicion)
                agregar(20, y0)
                agregar(11, posicion)
                agregar(21, y1)
                agregar_texto(
                    posicion,
                    y0 - margen_y * 0.30,
                    fecha_mes.strftime("%b %Y"),
                    alto=max(y1 * 0.018, 0.16),
                    alineacion_horizontal=1,
                    x_alineacion=posicion,
                    y_alineacion=y0 - margen_y * 0.30,
                )

        dias = pd.date_range(fecha_inicio.normalize(), fecha_final.normalize(), freq="D")
        intervalo_dias = self.obtener_intervalo_dias_menores(fecha_inicio.to_pydatetime(), fecha_final.to_pydatetime())
        for fecha_dia in dias[::intervalo_dias]:
            posicion = (fecha_dia - fecha_inicio).total_seconds() / 86400.0
            if x0 <= posicion <= x1:
                agregar(0, "LINE")
                agregar(8, "MARCAS_X")
                agregar(10, posicion)
                agregar(20, y0)
                agregar(11, posicion)
                agregar(21, y0 - margen_y * 0.03)
                agregar_texto(
                    posicion,
                    y0 - margen_y * 0.14,
                    fecha_dia.strftime("%d"),
                    alto=max(y1 * 0.015, 0.14),
                    alineacion_horizontal=1,
                    x_alineacion=posicion,
                    y_alineacion=y0 - margen_y * 0.14,
                )

        agregar(0, "LINE")
        agregar(8, "INICIO_PERIODO")
        agregar(10, 0.0)
        agregar(20, y0)
        agregar(11, 0.0)
        agregar(21, y1)

        if self.tipo_archivo_adicional == "fechas" and not self.fechas_geoelectricas_filtradas.empty:
            for _, fila in self.fechas_geoelectricas_filtradas.iterrows():
                posicion = (pd.Timestamp(fila["fecha"]) - fecha_inicio).total_seconds() / 86400.0
                if x0 <= posicion <= x1:
                    agregar(0, "LINE")
                    agregar(8, "FECHAS_EVENTO")
                    agregar(10, posicion)
                    agregar(20, y0)
                    agregar(11, posicion)
                    agregar(21, y1)

        agregar(0, "LWPOLYLINE")
        agregar(8, "NIVELES")
        agregar(90, len(puntos_nivel))
        agregar(70, 0)
        for x, y in puntos_nivel:
            agregar(10, x)
            agregar(20, y)

        if not caudales_salida.empty and caudal_superior:
            puntos_caudal = []
            for _, fila in caudales_salida.iterrows():
                x = float(fila["tiempo_dias"])
                y_escalado = float(fila["caudal"]) / float(caudal_superior) * y1
                puntos_caudal.append((x, y_escalado))

            agregar(0, "LWPOLYLINE")
            agregar(8, "CAUDALES")
            agregar(90, len(puntos_caudal))
            agregar(70, 0)
            for x, y in puntos_caudal:
                agregar(10, x)
                agregar(20, y)

            ticks_caudal = list(range(0, int(caudal_superior) + int(paso_caudal), int(paso_caudal)))
            for tick in ticks_caudal:
                y_escalado = float(tick) / float(caudal_superior) * y1 if caudal_superior > 0 else 0
                agregar(0, "LINE")
                agregar(8, "MARCAS_CAUDAL")
                agregar(10, x1)
                agregar(20, y_escalado)
                agregar(11, x1 + margen_x * 0.02)
                agregar(21, y_escalado)
                agregar_texto(x1 + margen_x * 0.04, y_escalado - 0.08, str(int(tick)), alto=max(y1 * 0.018, 0.16))

            agregar_texto(x1 + margen_x * 0.04, y1, "Caudal [cm3/s]", alto=max(y1 * 0.02, 0.18))

        agregar_texto(x0, y1 + margen_y * 0.58, "Niveles del embalse", alto=max(y1 * 0.03, 0.25))
        agregar_texto(
            x0,
            y1 + margen_y * 0.34,
            f"Referencia eje X: {self.fecha_referencia_dxf.strftime('%d/%m/%Y 00:00:00')}",
            alto=max(y1 * 0.02, 0.18),
        )
        agregar_texto(
            x0,
            y1 + margen_y * 0.12,
            f"Inicio del período: {self.fecha_inicial.date().toString('dd/MM/yyyy')}",
            alto=max(y1 * 0.02, 0.18),
        )
        agregar_texto(
            x1,
            y0 - margen_y * 0.46,
            "Tiempo [días desde el inicio del período]",
            alto=max(y1 * 0.02, 0.18),
            alineacion_horizontal=2,
            x_alineacion=x1,
            y_alineacion=y0 - margen_y * 0.46,
        )
        agregar_texto(x0 - margen_x * 0.12, y1, "Nivel [m]", alto=max(y1 * 0.02, 0.18))

        agregar(0, "ENDSEC")
        agregar(0, "EOF")

        with open(ruta_dxf, "w", encoding="utf-8") as archivo_dxf:
            archivo_dxf.write("\n".join(contenido))

    def guardar_archivos_salida(self):
        datos_filtrados = self.obtener_datos_filtrados()
        if datos_filtrados.empty:
            return

        ruta_csv, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar archivo en formato Chanlud",
            "niveles_salida.csv",
            "Archivos CSV (*.csv);;Todos los archivos (*)",
        )
        if not ruta_csv:
            return

        try:
            ruta_csv = str(Path(ruta_csv))
            ruta_dxf = str(Path(ruta_csv).with_suffix(".dxf"))
            datos_salida = self.construir_datos_salida(datos_filtrados)
            self.guardar_csv_chanlud(ruta_csv, datos_salida)
            self.guardar_dxf_grafico(ruta_dxf, datos_salida)

            self.registrar_mensaje(f"CSV guardado correctamente: {ruta_csv}")
            self.registrar_mensaje(f"DXF del gráfico guardado correctamente: {ruta_dxf}")
            self.registrar_mensaje(
                f"Fecha de referencia usada para el eje temporal: {self.fecha_referencia_dxf.strftime('%d/%m/%Y 00:00:00')}"
            )
            QMessageBox.information(self, "Proceso completado", "Se guardaron correctamente el CSV y el DXF del gráfico.")
        except Exception as error:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar los archivos:\n{error}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = VentanaNivelesEmbalse()
    ventana.show()
    sys.exit(app.exec_())
