import sys
import os
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont

from metodos_rsa import lectura_archivo
from metodos_gestion import parametros_estaciones, obtener_directorios


class PanelEstadoJornada(QWidget):
    """
    Panel nativo en PyQt5 de monitoreo y diagnóstico de la jornada sísmica:
    - Estado de la estructura de directorios del día.
    - Disponibilidad de registro continuo por estación sísmica.
    - Estado de evacuación por turnos (00H-12H, 12H-18H, 18H-24H).
    - Estado de emisión de reportes diarios (PDF).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.inicializar_ui()

    def inicializar_ui(self):
        # Estilos modernos para evitar el bug de recorte de títulos de QGroupBox en Windows
        self.setStyleSheet("""
            QGroupBox {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
                font-weight: bold;
                color: #1a237e;
                border: 1px solid #b0bec5;
                border-radius: 6px;
                margin-top: 14px;
                padding-top: 12px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 6px;
                background-color: #fafafa;
            }
            QLabel {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 9pt;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # 1. Cabecera de Estado General
        self.grupo_general = QGroupBox("ESTADO GENERAL DE LA JORNADA")
        layout_general = QVBoxLayout(self.grupo_general)
        layout_general.setContentsMargins(12, 12, 12, 10)
        layout_general.setSpacing(5)

        self.lbl_fecha = QLabel("📅 Fecha: --")
        self.lbl_directorio = QLabel("📁 Directorio Base: --")
        self.lbl_estado_dia = QLabel("⚪ Estado de Estructura: Sin verificar")

        for lbl in (self.lbl_fecha, self.lbl_directorio, self.lbl_estado_dia):
            layout_general.addWidget(lbl)

        layout.addWidget(self.grupo_general)

        # 2. Estado por Estaciones Sísmicas (Grid dinámico)
        self.grupo_estaciones = QGroupBox("CONDICIÓN Y REGISTRO POR ESTACIONES SÍSMICAS (MONITOREO CONTINUO)")
        layout_est = QVBoxLayout(self.grupo_estaciones)
        layout_est.setContentsMargins(10, 12, 10, 10)

        self.scroll_estaciones = QScrollArea()
        self.scroll_estaciones.setWidgetResizable(True)
        self.scroll_estaciones.setFrameShape(QFrame.NoFrame)

        self.widget_grid_estaciones = QWidget()
        self.grid_estaciones = QGridLayout(self.widget_grid_estaciones)
        self.grid_estaciones.setContentsMargins(4, 4, 4, 4)
        self.grid_estaciones.setSpacing(8)
        self.scroll_estaciones.setWidget(self.widget_grid_estaciones)

        layout_est.addWidget(self.scroll_estaciones)
        layout.addWidget(self.grupo_estaciones, 2)

        # 3. Estado de Turnos y Reportes Oficiales
        self.grupo_turnos = QGroupBox("EVACUACIÓN DE TURNOS Y REPORTES INSTITUCIONALES")
        layout_turnos = QGridLayout(self.grupo_turnos)
        layout_turnos.setContentsMargins(12, 12, 12, 10)
        layout_turnos.setSpacing(8)

        self.lbl_turno1 = QLabel("🕒 Turno 00:00 - 12:00: ⚪ Pendiente")
        self.lbl_turno2 = QLabel("🕒 Turno 12:00 - 18:00: ⚪ Pendiente")
        self.lbl_turno3 = QLabel("🕒 Turno 18:00 - 24:00: ⚪ Pendiente")
        self.lbl_reporte_pdf = QLabel("📄 Reporte Diario PDF: ⚪ No generado")

        for i, lbl in enumerate((self.lbl_turno1, self.lbl_turno2, self.lbl_turno3, self.lbl_reporte_pdf)):
            layout_turnos.addWidget(lbl, i // 2, i % 2)

        layout.addWidget(self.grupo_turnos, 1)

    def actualizar_diagnostico(self, ruta_archivo, directorio_base_trabajo, parametros_est=None):
        """
        Inspecciona el sistema de archivos para la fecha seleccionada y actualiza
        el estado visual del panel.
        """
        if parametros_est is None:
            try:
                parametros_est = parametros_estaciones()
            except Exception:
                parametros_est = {}

        try:
            directorios = obtener_directorios(ruta_archivo)
        except Exception as e:
            self.lbl_estado_dia.setText(f"❌ Error al calcular rutas: {e}")
            return

        dir_base = Path(directorios.get("Directorio_base", ""))
        dir_registros = Path(directorios.get("Directorio_registros", ""))
        archivo_csv = Path(directorios.get("archivo_csv", ""))
        archivo_pdf = Path(directorios.get("archivo_reporte_dia", ""))

        fecha_str = Path(ruta_archivo).name[:8]
        try:
            fecha_fmt = datetime.strptime(fecha_str, "%Y%m%d").strftime("%d/%m/%Y")
        except Exception:
            fecha_fmt = fecha_str

        self.lbl_fecha.setText(f"📅 Fecha de Diagnóstico: <b>{fecha_fmt}</b>")
        self.lbl_directorio.setText(f"📁 Directorio Base: <code>{dir_base}</code>")

        # Verificar existencia de estructura
        if dir_base.exists():
            self.lbl_estado_dia.setText("🟢 Estructura del Día: <b>EXISTE Y DISPONIBLE</b>")
            self.lbl_estado_dia.setStyleSheet("color: #2e7d32;")
        else:
            self.lbl_estado_dia.setText("🟡 Estructura del Día: <b>NO CREADA (Se inicializará al comenzar)</b>")
            self.lbl_estado_dia.setStyleSheet("color: #e65100;")

        # Limpiar grid de estaciones
        while self.grid_estaciones.count():
            item = self.grid_estaciones.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Obtener listas de estaciones
        if isinstance(parametros_est, dict):
            nombres_totales = parametros_est.get('NOMBRE', [])
            nombres_canales = parametros_est.get('CODIGO', [])
            hab_canales = parametros_est.get('HAB_CANAL', [])
            hab_graficos = parametros_est.get('HAB_GRAFICO', [])
        elif isinstance(parametros_est, (list, tuple)):
            nombres_totales = parametros_est[0] if len(parametros_est) > 0 else []
            nombres_canales = parametros_est[1] if len(parametros_est) > 1 else []
            hab_canales = parametros_est[4] if len(parametros_est) > 4 else []
            hab_graficos = parametros_est[6] if len(parametros_est) > 6 else []
        else:
            nombres_totales, nombres_canales, hab_canales, hab_graficos = [], [], [], []

        columnas = 3
        fila = 0
        col = 0

        for i, nom_total in enumerate(nombres_totales):
            if not nom_total:
                continue

            es_hab_canal = (str(hab_canales[i]).strip() == '1') if i < len(hab_canales) else False
            es_hab_grafico = (str(hab_graficos[i]).strip() == '1') if i < len(hab_graficos) else False
            if not (es_hab_canal and es_hab_grafico):
                continue

            nombre_c = nombres_canales[i] if i < len(nombres_canales) else nom_total
            existe_registro = False
            if dir_registros.exists():
                try:
                    for f in os.listdir(dir_registros):
                        if str(nombre_c).lower() in f.lower() or str(nom_total).lower() in f.lower():
                            existe_registro = True
                            break
                except Exception:
                    pass

            tarjeta = QFrame()
            tarjeta.setFrameShape(QFrame.StyledPanel)
            tarjeta.setMinimumHeight(34)
            layout_t = QHBoxLayout(tarjeta)
            layout_t.setContentsMargins(8, 4, 8, 4)
            layout_t.setSpacing(6)

            lbl_est = QLabel(f"<b>{nom_total}</b> ({nombre_c})")
            lbl_est.setFont(QFont("Segoe UI", 9))
            lbl_est.setStyleSheet("border: none; background: transparent; color: #212121;")

            texto_tag = "🟢 OK" if existe_registro else "⚪ Sin Reg."
            lbl_tag = QLabel(texto_tag)
            lbl_tag.setFont(QFont("Segoe UI", 9))
            lbl_tag.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_tag.setMinimumWidth(80)
            lbl_tag.setStyleSheet("border: none; background: transparent;")

            if existe_registro:
                tarjeta.setStyleSheet("QFrame { background-color: #e8f5e9; border: 1px solid #81c784; border-radius: 4px; }")
            else:
                tarjeta.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 4px; }")

            layout_t.addWidget(lbl_est, 1)
            layout_t.addWidget(lbl_tag, 0)

            self.grid_estaciones.addWidget(tarjeta, fila, col)
            col += 1
            if col >= columnas:
                col = 0
                fila += 1

        # Diagnóstico de Turnos y Eventos
        conteo_turno1 = 0
        conteo_turno2 = 0
        conteo_turno3 = 0

        if archivo_csv.exists():
            try:
                eventos = lectura_archivo(str(archivo_csv)) or []
                for ev in eventos:
                    if len(ev) > 1:
                        try:
                            hora_txt = str(ev[1]).strip()
                            if len(hora_txt) >= 2 and hora_txt[:2].isdigit():
                                hora_ev = int(hora_txt[:2])
                                if 0 <= hora_ev < 12:
                                    conteo_turno1 += 1
                                elif 12 <= hora_ev < 18:
                                    conteo_turno2 += 1
                                elif 18 <= hora_ev <= 24:
                                    conteo_turno3 += 1
                        except Exception:
                            pass
            except Exception:
                pass

        self.lbl_turno1.setText(
            f"🕒 Turno 00:00 - 12:00: {'🟢 ' + str(conteo_turno1) + ' eventos' if conteo_turno1 > 0 else '⚪ 0 eventos'}"
        )
        self.lbl_turno2.setText(
            f"🕒 Turno 12:00 - 18:00: {'🟢 ' + str(conteo_turno2) + ' eventos' if conteo_turno2 > 0 else '⚪ 0 eventos'}"
        )
        self.lbl_turno3.setText(
            f"🕒 Turno 18:00 - 24:00: {'🟢 ' + str(conteo_turno3) + ' eventos' if conteo_turno3 > 0 else '⚪ 0 eventos'}"
        )

        # Diagnóstico de Reporte Diario PDF
        if archivo_pdf.exists():
            self.lbl_reporte_pdf.setText("📄 Reporte Diario PDF: 🟢 <b>EMITIDO</b>")
            self.lbl_reporte_pdf.setStyleSheet("color: #2e7d32;")
        else:
            self.lbl_reporte_pdf.setText("📄 Reporte Diario PDF: ⚪ <b>PENDIENTE</b>")
            self.lbl_reporte_pdf.setStyleSheet("color: #424242;")
