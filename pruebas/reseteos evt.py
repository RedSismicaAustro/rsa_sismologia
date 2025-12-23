import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta, time
import bisect

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from obspy import read


# ==== Rutas base del proyecto =================================================
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        idx = partes.index(nombre_directorio)
        return str(Path(*partes[:idx + 1])) + os.sep
    return ''


ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.join(ruta_proyecto, 'src', 'librerias')

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)

import metodos_gestion as mg
from metodos_gestion import obtener_directorios, parametros_estaciones
from metodos_rsa import lectura_archivo, clasificar_evento_sismico


# ==== Canvas ==================================================================
class Lienzo(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(9, 6))
        super().__init__(self.fig)

    def graficar(self, stream):
        self.fig.clear()
        ejes = self.fig.subplots(3, 1, sharex=True)

        for i, traza in enumerate(stream[:3]):
            ejes[i].plot(traza.times(), traza.data, lw=0.6)
            ejes[i].set_yticks([])

        ejes[-1].set_xlabel("Tiempo [s]")
        self.fig.tight_layout()
        self.draw()


# ==== Ventana principal =======================================================
class VisorEVT(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Clasificación EVT – Catálogo – MSEED")
        self.resize(1600, 950)

        self.directorio_trabajo = r"G:\Mi unidad\DIA"

        self.eventos_evt = []
        self.orden_canales = []
        self.periodos_por_canal = {}
        self.catalogos_por_canal = {}

        self.indice_evt = 0
        self.eventos_ruido = set()

        self._construir_ui()

    # -------------------------------------------------------------------------
    def _construir_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        barra = QHBoxLayout()
        layout.addLayout(barra)

        self.lbl_directorio_evt = QLabel("Directorio EVT: -")
        barra.addWidget(self.lbl_directorio_evt, 1)

        self.lbl_directorio_trabajo = QLabel("Directorio trabajo: -")
        barra.addWidget(self.lbl_directorio_trabajo)

        btn_evt = QPushButton("Abrir EVT")
        btn_evt.clicked.connect(self.abrir_evt)
        barra.addWidget(btn_evt)

        btn_dia = QPushButton("..\\dia\\")
        btn_dia.clicked.connect(self.cambiar_directorio_dia)
        barra.addWidget(btn_dia)

        barra.addWidget(QLabel("Estación:"))
        self.cmb_estaciones = QComboBox()
        barra.addWidget(self.cmb_estaciones)

        btn_verificar = QPushButton("Verificar sincronización")
        btn_verificar.clicked.connect(self.verificar_sincronizacion)
        barra.addWidget(btn_verificar)

        fila = QHBoxLayout()
        layout.addLayout(fila)

        self.cmb_evt = QComboBox()
        self.cmb_evt.currentIndexChanged.connect(self.cambiar_evt)
        fila.addWidget(self.cmb_evt, 3)

        self.cmb_catalogo = QComboBox()
        self.cmb_catalogo.currentIndexChanged.connect(self._graficar_mseed)
        fila.addWidget(self.cmb_catalogo, 4)

        self.cmb_estaciones.currentIndexChanged.connect(self._graficar_mseed)

        controles = QHBoxLayout()
        layout.addLayout(controles)

        self.chk_ruido = QCheckBox("RUIDO")
        self.chk_ruido.stateChanged.connect(self.marcar_ruido)
        controles.addWidget(self.chk_ruido)

        btn_prev = QPushButton("<<")
        btn_prev.clicked.connect(self.anterior)
        controles.addWidget(btn_prev)

        btn_next = QPushButton(">>")
        btn_next.clicked.connect(self.siguiente)
        controles.addWidget(btn_next)

        self.lbl_evt = QLabel("-")
        self.lbl_periodo = QLabel("-")
        self.lbl_delta = QLabel("-")
        controles.addWidget(self.lbl_evt)
        controles.addWidget(self.lbl_periodo)
        controles.addWidget(self.lbl_delta)
        controles.addStretch()

        self.txt_sync = QLabel("")
        self.txt_sync.setStyleSheet("font-family: Consolas;")
        self.txt_sync.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.txt_sync.setWordWrap(True)
        layout.addWidget(self.txt_sync)

        graficos = QHBoxLayout()
        layout.addLayout(graficos, 1)

        self.lienzo_evt = Lienzo()
        self.lienzo_mseed = Lienzo()
        graficos.addWidget(self.lienzo_evt, 1)
        graficos.addWidget(self.lienzo_mseed, 1)

        self._cargar_estaciones_habilitadas()

    # -------------------------------------------------------------------------
    def _cargar_estaciones_habilitadas(self):
        self.cmb_estaciones.clear()
        parametros = parametros_estaciones()
        estaciones = [
            parametros["CODIGO"][i]
            for i in range(101)
            if parametros["HAB_CANAL"][i] == "1"
        ]
        self.cmb_estaciones.addItems(estaciones)

    # -------------------------------------------------------------------------
    def cambiar_directorio_dia(self):
        directorio = QFileDialog.getExistingDirectory(self, "Directorio DIA")
        if directorio:
            self.directorio_trabajo = directorio
            self.lbl_directorio_trabajo.setText(directorio)

    # -------------------------------------------------------------------------
    def abrir_evt(self):
        directorio = QFileDialog.getExistingDirectory(self, "Directorio AAAAMMDD")
        if not directorio:
            return

        base = Path(directorio)
        self.lbl_directorio_evt.setText(str(base))

        with open(base / f"{base.name}.json", encoding="utf-8") as f:
            data = json.load(f)

        self.eventos_evt, self.orden_canales = self._leer_evt_desde_json(data, base)
        self._calcular_periodos(base)
        self._cargar_catalogos_por_periodo()

        self.cmb_evt.clear()
        self.cmb_evt.addItems([e["evt"] for e in self.eventos_evt])

        self.indice_evt = 0
        self.mostrar_evento_evt()

    # -------------------------------------------------------------------------
    def cambiar_evt(self, indice):
        if indice >= 0:
            self.indice_evt = indice
            self.mostrar_evento_evt()

    # -------------------------------------------------------------------------
    def mostrar_evento_evt(self):
        evento_evt = self.eventos_evt[self.indice_evt]

        stream_evt = read(str(evento_evt["ruta"]))
        self.lienzo_evt.graficar(stream_evt)

        self.lbl_evt.setText(evento_evt["dt"].strftime("%Y%m%d_%H%M%S.sis"))

        periodo = self.periodos_por_canal[evento_evt["cc"]]
        self.lbl_periodo.setText(
            f'{evento_evt["cc"]} ({periodo["tipo"]}): '
            f'{periodo["inicio"]} → {periodo["fin"]}'
        )

        resultado = clasificar_evento_sismico(stream_evt)
        if not resultado.get("evento_sismico_probable", False):
            self.eventos_ruido.add(evento_evt["evt"])
        else:
            self.eventos_ruido.discard(evento_evt["evt"])

        self.chk_ruido.blockSignals(True)
        self.chk_ruido.setChecked(evento_evt["evt"] in self.eventos_ruido)
        self.chk_ruido.blockSignals(False)

        self._actualizar_catalogo_evt(evento_evt)
        self._graficar_mseed()

    # -------------------------------------------------------------------------
    def _actualizar_catalogo_evt(self, evento_evt):
        self.cmb_catalogo.blockSignals(True)
        self.cmb_catalogo.clear()

        if evento_evt["evt"] in self.eventos_ruido:
            self.lbl_delta.setText("RUIDO")
            self.cmb_catalogo.blockSignals(False)
            return

        codigo_canal = evento_evt["cc"]
        eventos_catalogo = self.catalogos_por_canal.get(codigo_canal, [])

        if not eventos_catalogo:
            self.lbl_delta.setText("-")
            self.cmb_catalogo.blockSignals(False)
            return

        for _, nombre in eventos_catalogo:
            self.cmb_catalogo.addItem(nombre)

        fechas_catalogo = [x[0] for x in eventos_catalogo]
        indice = bisect.bisect_left(fechas_catalogo, evento_evt["dt"])
        if indice == len(fechas_catalogo):
            indice -= 1

        self.cmb_catalogo.setCurrentIndex(indice)
        self.lbl_delta.setText(str(fechas_catalogo[indice] - evento_evt["dt"]))

        self.cmb_catalogo.blockSignals(False)

    # -------------------------------------------------------------------------
    def _graficar_mseed(self):
        self.lienzo_mseed.fig.clear()

        estacion = self.cmb_estaciones.currentText()
        evento_sis = self.cmb_catalogo.currentText()

        if not estacion or not evento_sis:
            self.lienzo_mseed.draw()
            return

        fecha = evento_sis.replace(".sis", "")
        carpeta_dia = fecha[:8] + "000000"

        info = obtener_directorios(os.path.join(self.directorio_trabajo, carpeta_dia))
        ruta_eventos = info.get("Directorio_eventos", "")

        if not ruta_eventos:
            self.lienzo_mseed.draw()
            return

        ruta_mseed = os.path.join(ruta_eventos, f"{estacion}_{fecha}.mseed")
        if not os.path.exists(ruta_mseed):
            self.lienzo_mseed.draw()
            return

        self.lienzo_mseed.graficar(read(ruta_mseed))

    # -------------------------------------------------------------------------
    def verificar_sincronizacion(self):
        if not self.eventos_evt:
            return

        # EVT actualmente seleccionado (solo para identificar el período/canal)
        evento_actual = self.eventos_evt[self.indice_evt]
        codigo_canal = evento_actual["cc"]

        # Todos los EVT del mismo período/canal
        eventos_evt_periodo = [
            e for e in self.eventos_evt if e["cc"] == codigo_canal
        ]

        if not eventos_evt_periodo:
            return

        # Catálogo del período
        eventos_catalogo = self.catalogos_por_canal.get(codigo_canal, [])
        if not eventos_catalogo:
            self.txt_sync.setText("No hay catálogo para este período.")
            return

        fechas_catalogo = [x[0] for x in eventos_catalogo]

        # EVT ancla: primer EVT del período (solo para tiempo relativo)
        evento_ancla = eventos_evt_periodo[0]
        fecha_evt_ancla = evento_ancla["dt"]

        # SIS ancla: seleccionado en el combobox
        texto_sis_ancla = self.cmb_catalogo.currentText()
        if not texto_sis_ancla:
            self.txt_sync.setText("No hay evento de catálogo seleccionado.")
            return

        fecha_sis_ancla = datetime.strptime(
            texto_sis_ancla, "%Y%m%d_%H%M%S.sis"
        )

        # Umbral para decidir si el delta directo es válido (2 días)
        umbral_segundos = 2 * 24 * 3600

        # Construcción del reporte
        lineas = [
            f"Período: {codigo_canal}",
            f"EVT ancla : {evento_ancla['evt']}  →  SIS ancla : {texto_sis_ancla}",
            "-" * 80
        ]

        for evento_evt in eventos_evt_periodo:
            if evento_evt["evt"] in self.eventos_ruido:
                continue

            # ==========================
            # Paso 1: delta directo
            # ==========================
            indice = bisect.bisect_left(fechas_catalogo, evento_evt["dt"])
            if indice == len(fechas_catalogo):
                indice -= 1

            fecha_cat_directo, nombre_cat_directo = eventos_catalogo[indice]
            delta_directo = fecha_cat_directo - evento_evt["dt"]

            # ==========================
            # Paso 2: decidir referencia
            # ==========================
            if abs(delta_directo.total_seconds()) <= umbral_segundos:
                # Delta válido: usar tiempo absoluto
                nombre_cat = nombre_cat_directo
                delta_final = delta_directo

            else:
                # Delta muy grande: usar tiempo relativo + referencia SIS ancla
                delta_relativo = evento_evt["dt"] - fecha_evt_ancla
                fecha_estimado = fecha_sis_ancla + delta_relativo

                indice_ref = bisect.bisect_left(fechas_catalogo, fecha_estimado)
                if indice_ref == len(fechas_catalogo):
                    indice_ref -= 1

                fecha_cat_ref, nombre_cat = eventos_catalogo[indice_ref]
                delta_final = fecha_cat_ref - fecha_estimado

            lineas.append(
                f"{evento_evt['evt']:10s} → {nombre_cat:20s} Δt = {delta_final}"
            )

        self.txt_sync.setText("\n".join(lineas))





    def verificar_sincronizacion___(self):
        if not self.eventos_evt:
            return

        evento_referencia = self.eventos_evt[self.indice_evt]
        codigo_canal = evento_referencia["cc"]

        eventos_evt_canal = [
            e for e in self.eventos_evt if e["cc"] == codigo_canal
        ]
        eventos_catalogo = self.catalogos_por_canal.get(codigo_canal, [])

        if not eventos_catalogo:
            self.txt_sync.setText("No hay catálogo para este período.")
            return

        fechas_catalogo = [x[0] for x in eventos_catalogo]

        lineas = [
            f"Período: {codigo_canal}",
            "-" * 70
        ]

        for evento_evt in eventos_evt_canal:
            if evento_evt["evt"] in self.eventos_ruido:
                continue

            indice = bisect.bisect_left(fechas_catalogo, evento_evt["dt"])
            if indice == len(fechas_catalogo):
                indice -= 1

            fecha_cat, nombre_cat = eventos_catalogo[indice]
            delta = fecha_cat - evento_evt["dt"]

            lineas.append(
                f"{evento_evt['evt']:10s} → {nombre_cat:20s} Δt = {delta}"
            )

        self.txt_sync.setText("\n".join(lineas))

    # -------------------------------------------------------------------------
    def marcar_ruido(self, estado):
        evt = self.eventos_evt[self.indice_evt]["evt"]
        if estado:
            self.eventos_ruido.add(evt)
        else:
            self.eventos_ruido.discard(evt)

    def siguiente(self):
        idx = self.indice_evt + 1
        while idx < len(self.eventos_evt):
            if self.eventos_evt[idx]["evt"] not in self.eventos_ruido:
                self.cmb_evt.setCurrentIndex(idx)
                return
            idx += 1

    def anterior(self):
        idx = self.indice_evt - 1
        while idx >= 0:
            if self.eventos_evt[idx]["evt"] not in self.eventos_ruido:
                self.cmb_evt.setCurrentIndex(idx)
                return
            idx -= 1

    # -------------------------------------------------------------------------
    def _leer_evt_desde_json(self, data, base):
        fs_evt = {p.name.upper(): p for p in base.rglob("*.EVT")}
        patron = re.compile(r"^([A-Z]{2})(\d{3})\.EVT$")

        eventos_encontrados = []

        def recorrer(nodo):
            if isinstance(nodo, dict):
                if nodo.get("tipo") == "archivo":
                    nombre = nodo.get("nombre", "").upper()
                    if nombre in fs_evt:
                        m = patron.match(nombre)
                        if m:
                            fecha_evt = datetime.strptime(
                                nodo["modificado"], "%Y-%m-%d %H:%M:%S"
                            )
                            eventos_encontrados.append({
                                "cc": m.group(1),
                                "nnn": int(m.group(2)),
                                "evt": nombre,
                                "ruta": fs_evt[nombre],
                                "dt": fecha_evt
                            })
                for h in nodo.get("contenido", []):
                    recorrer(h)
            elif isinstance(nodo, list):
                for h in nodo:
                    recorrer(h)

        recorrer(data)

        orden_canales = []
        for evento in eventos_encontrados:
            if evento["cc"] not in orden_canales:
                orden_canales.append(evento["cc"])

        eventos_encontrados.sort(
            key=lambda x: (orden_canales.index(x["cc"]), x["nnn"])
        )

        return eventos_encontrados, orden_canales

    # -------------------------------------------------------------------------
    def _calcular_periodos(self, base):
        self.periodos_por_canal = {}

        fecha_bajada = datetime.combine(
            datetime.strptime(base.name, "%Y%m%d").date(),
            time(17, 0)
        )

        eventos_por_canal = {}
        for evento in self.eventos_evt:
            eventos_por_canal.setdefault(evento["cc"], []).append(evento)

        canal_base = None
        for cc in self.orden_canales:
            fechas = [e["dt"] for e in eventos_por_canal[cc]]
            if min(fechas).year != 1980:
                canal_base = cc
                break

        fechas_base = [e["dt"] for e in eventos_por_canal[canal_base]]
        self.periodos_por_canal[canal_base] = {
            "inicio": min(fechas_base),
            "fin": max(fechas_base),
            "tipo": "fijo"
        }

        duraciones = {}
        for cc in self.orden_canales:
            if cc == canal_base:
                continue
            fechas = [e["dt"] for e in eventos_por_canal[cc]]
            duraciones[cc] = max(fechas) - min(fechas)

        inicio_ventana = self.periodos_por_canal[canal_base]["fin"]
        fin_ventana = fecha_bajada

        canales_moviles = [cc for cc in self.orden_canales if cc != canal_base]

        for i, cc in enumerate(canales_moviles):
            suma_prev = sum(
                (duraciones[canales_moviles[j]] for j in range(i)),
                timedelta()
            )
            suma_post = sum(
                (duraciones[canales_moviles[j]] for j in range(i + 1, len(canales_moviles))),
                timedelta()
            )

            self.periodos_por_canal[cc] = {
                "inicio": inicio_ventana + suma_prev,
                "fin": fin_ventana - suma_post,
                "tipo": "movil"
            }

    # -------------------------------------------------------------------------
    def _cargar_catalogos_por_periodo(self):
        self.catalogos_por_canal = {}
        mg.directorio_trabajo = self.directorio_trabajo

        for cc, periodo in self.periodos_por_canal.items():
            eventos_catalogo = []
            fecha = periodo["inicio"].date()

            while fecha <= periodo["fin"].date():
                carpeta = os.path.join(
                    self.directorio_trabajo,
                    fecha.strftime("%Y%m%d") + "000000"
                )
                info = obtener_directorios(carpeta)
                ruta_catalogo = info.get("archivo_catalogo", "")

                if os.path.exists(ruta_catalogo):
                    datos = lectura_archivo(ruta_catalogo)
                    for fila in datos:
                        if fila[18] != "ruta":
                            fecha_evt = datetime.strptime(
                                fila[18], "%Y%m%d_%H%M%S.sis"
                            )
                            eventos_catalogo.append((fecha_evt, fila[18]))

                fecha += timedelta(days=1)

            eventos_catalogo.sort(key=lambda x: x[0])
            self.catalogos_por_canal[cc] = eventos_catalogo


# ==== MAIN ====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    visor = VisorEVT()
    visor.show()
    sys.exit(app.exec_())


