# -*- coding: utf-8 -*-
"""
Vigilante Residente de Caudales y Filtraciones (RSA Sismología)
Proceso ligero en bandeja del sistema de Windows (System Tray) que vigila periódicamente
el archivo caudales.csv, emite notificaciones nativas de Windows en caso de olvido o alerta
de paro de bomba/inundación, y permite abrir la herramienta con un solo clic.
"""

import sys
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush, QPen, QFont
from PyQt5.QtCore import QTimer, QTime

def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    else:
        return ''

ruta_actual = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_actual, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)

from rsa_io import lectura_archivo


class VigilanteCaudales(QtWidgets.QApplication):

    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)

        self.directorio_trabajo = "G:/Mi unidad/DIA/"
        self.ruta_script_caudales = os.path.abspath(os.path.join(ruta_actual, "caudales_filtraciones.py"))
        
        # Historial de alertas para no spamear notificaciones innecesarias
        self.ultima_notificacion_alerta = None
        self.ultima_notificacion_recordatorio = None

        # Configurar icono del System Tray
        self.tray_icon = QSystemTrayIcon(self)
        self.menu = QMenu()
        
        self.accion_info = QAction("📊 Monitoreo de Caudales RSA", self)
        self.accion_info.setEnabled(False)
        self.menu.addAction(self.accion_info)
        
        self.accion_estado = QAction("Estado: Inicializando...", self)
        self.accion_estado.setEnabled(False)
        self.menu.addAction(self.accion_estado)
        
        self.menu.addSeparator()
        
        self.accion_abrir = QAction("🚀 Abrir Caudales y Filtraciones", self)
        self.accion_abrir.triggered.connect(self.abrir_caudales)
        self.menu.addAction(self.accion_abrir)
        
        self.accion_verificar = QAction("🔍 Verificar Estado Ahora", self)
        self.accion_verificar.triggered.connect(lambda: self.verificar_caudales(manual=True))
        self.menu.addAction(self.accion_verificar)
        
        self.menu.addSeparator()
        
        self.accion_salir = QAction("❌ Salir del Vigilante", self)
        self.accion_salir.triggered.connect(self.quit)
        self.menu.addAction(self.accion_salir)
        
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self.al_activar_icono)
        
        # Temporizador periódico: verificación cada 30 minutos
        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(lambda: self.verificar_caudales(manual=False))
        self.temporizador.start(30 * 60 * 1000)  # 30 minutos en milisegundos
        
        # Primera verificación inmediata al iniciar
        self.actualizar_icono("NORMAL")
        self.tray_icon.show()
        QTimer.singleShot(1500, lambda: self.verificar_caudales(manual=False))

    def crear_icono_estado(self, estado):
        """Genera un icono gráfico dinámico de 32x32 px según el estado del sistema."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        if estado == "ALERTA_CRITICA":
            color_fondo = QColor("#dc2626")  # Rojo
            color_borde = QColor("#991b1b")
            texto = "!"
        elif estado == "PENDIENTE":
            color_fondo = QColor("#f59e0b")  # Amarillo / Naranja
            color_borde = QColor("#b45309")
            texto = "?"
        else:
            color_fondo = QColor("#16a34a")  # Verde
            color_borde = QColor("#15803d")
            texto = "Q"

        painter.setBrush(QBrush(color_fondo))
        painter.setPen(QPen(color_borde, 2))
        painter.drawEllipse(2, 2, 28, 28)

        painter.setPen(QPen(QColor("white")))
        fuente = QFont("Segoe UI", 12, QFont.Bold)
        painter.setFont(fuente)
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, texto)
        painter.end()

        return QIcon(pixmap)

    def actualizar_icono(self, estado):
        """Actualiza el icono del System Tray con el color y estado actual."""
        icono = self.crear_icono_estado(estado)
        self.tray_icon.setIcon(icono)

    def al_activar_icono(self, razon):
        """Si el usuario hace doble clic o clic en la notificación, abre la aplicación principal."""
        if razon in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.abrir_caudales()

    def abrir_caudales(self):
        """Ejecuta el script principal de caudales en un proceso independiente."""
        try:
            if os.path.isfile(self.ruta_script_caudales):
                # Utilizar el mismo ejecutable de Python que corre el vigilante
                subprocess.Popen([sys.executable, self.ruta_script_caudales], cwd=ruta_actual)
            else:
                self.tray_icon.showMessage(
                    "Error al Iniciar",
                    f"No se encontró el script en {self.ruta_script_caudales}",
                    QSystemTrayIcon.Critical,
                    5000
                )
        except Exception as e:
            print(f"[ERROR] No se pudo lanzar caudales_filtraciones.py: {e}")

    def leer_estado_caudales(self):
        """Lee caudales.csv y evalúa el tiempo transcurrido desde el último bombeo registrado."""
        archivo_caudales = os.path.join(self.directorio_trabajo, "caudales.csv")
        if not os.path.isfile(archivo_caudales):
            return None

        try:
            filas = lectura_archivo(archivo_caudales)
            eventos_confirmados = []
            for fila in filas:
                if len(fila) < 3 or str(fila[2]).strip() != "1":
                    continue
                nom = str(fila[0]).strip()
                if len(nom) == 17:
                    nom = '20' + nom
                try:
                    dt = datetime.strptime(nom.replace(".sis", ""), "%Y%m%d_%H%M%S")
                    caudal = int(fila[1]) if len(fila) > 1 else 0
                    eventos_confirmados.append((dt, nom, caudal))
                except Exception:
                    pass

            if not eventos_confirmados:
                return None

            eventos_confirmados.sort(key=lambda x: x[0])
            ultimo_dt, ultimo_nom, ultimo_caudal = eventos_confirmados[-1]

            if ultimo_caudal > 0:
                delta_t_seg = int(1.214 * 3500000 / ultimo_caudal)
            elif len(eventos_confirmados) >= 2:
                dt_penultimo = eventos_confirmados[-2][0]
                delta_t_seg = max(1800, int((ultimo_dt - dt_penultimo).total_seconds()))
                ultimo_caudal = int(1.214 * 3500000 / delta_t_seg) if delta_t_seg > 0 else 400
            else:
                delta_t_seg = 28800
                ultimo_caudal = int(1.214 * 3500000 / delta_t_seg)

            dt_esperado = ultimo_dt + timedelta(seconds=delta_t_seg)
            ahora = datetime.now()
            segundos_transcurridos = (ahora - ultimo_dt).total_seconds()
            horas_transcurridas = round(segundos_transcurridos / 3600.0, 1)
            ratio = segundos_transcurridos / delta_t_seg if delta_t_seg > 0 else 0

            if ratio > 1.5:
                estado = "ALERTA_CRITICA"
            elif ratio > 1.0 or ultimo_dt.date() < ahora.date():
                estado = "PENDIENTE"
            else:
                estado = "NORMAL"

            return {
                'ultimo_dt': ultimo_dt,
                'ultimo_caudal': ultimo_caudal,
                'delta_t_horas': round(delta_t_seg / 3600.0, 1),
                'dt_esperado': dt_esperado,
                'horas_transcurridas': horas_transcurridas,
                'estado': estado,
                'ciclos_pendientes': max(0, int(ratio))
            }
        except Exception as e:
            print(f"[ERROR] Error al evaluar caudales.csv en Vigilante: {e}")
            return None

    def verificar_comunicacion_cha2(self):
        """Verifica si la estación CHA2 presenta corte de comunicación."""
        archivo_com = os.path.join(self.directorio_trabajo, "comunicaciones.csv")
        if os.path.isfile(archivo_com):
            try:
                filas = lectura_archivo(archivo_com)
                for f in filas:
                    if len(f) >= 3 and str(f[0]).strip().upper() == "CHA2":
                        return str(f[2]).strip() == "1"
            except Exception:
                pass

        hoy_str = datetime.now().strftime("%Y%m%d")
        ruta_mseed_hoy = os.path.join(self.directorio_trabajo, hoy_str, "mseed", f"CHA2_{hoy_str}_000000.mseed")
        if os.path.isfile(ruta_mseed_hoy):
            return True

        ruta_datos_cha2 = os.path.join(self.directorio_trabajo, "Datos Estaciones", "CHA2")
        if os.path.isdir(ruta_datos_cha2):
            for arch in os.listdir(ruta_datos_cha2):
                if hoy_str in arch:
                    return True

        return False

    def verificar_caudales(self, manual=False):
        """Evalúa el estado actual y emite notificaciones de Windows según la urgencia."""
        comunicacion_ok = self.verificar_comunicacion_cha2()
        info = self.leer_estado_caudales()
        ahora = datetime.now()

        # Si hay corte de comunicación en CHA2
        if not comunicacion_ok:
            self.actualizar_icono("PENDIENTE")
            self.accion_estado.setText("Estado: Corte de comunicación (CHA2)")
            self.tray_icon.setToolTip("Vigilante Caudales RSA\nEstado: Corte de comunicación (CHA2)")
            
            debe_notificar = manual or (
                self.ultima_notificacion_alerta is None or
                (ahora - self.ultima_notificacion_alerta).total_seconds() > 3600
            )
            if debe_notificar:
                self.ultima_notificacion_alerta = ahora
                self.tray_icon.showMessage(
                    "⚠️ RSA — Corte de Comunicación",
                    "Estación CHA2: corte de comunicación.",
                    QSystemTrayIcon.Warning,
                    8000
                )
            return

        if not info:
            self.actualizar_icono("PENDIENTE")
            self.accion_estado.setText("Estado: Sin registros de caudales")
            if manual:
                self.tray_icon.showMessage(
                    "Vigilante de Caudales RSA",
                    "No se encontraron registros confirmados en caudales.csv.",
                    QSystemTrayIcon.Warning,
                    5000
                )
            return

        self.actualizar_icono(info['estado'])
        texto_estado = f"Último: {info['ultimo_dt'].strftime('%d/%m %H:%M')} ({info['ultimo_caudal']} L/s) | Hace {info['horas_transcurridas']}h"
        self.accion_estado.setText(f"Estado: {texto_estado}")
        self.tray_icon.setToolTip(f"Vigilante Caudales RSA\n{texto_estado}\nEstado: {info['estado']}")

        # 1. Alerta Crítica: Posible paro de bomba o inundación
        if info['estado'] == "ALERTA_CRITICA":
            # Notificar cada 2 horas si sigue crítico o si es manual
            debe_notificar = manual or (
                self.ultima_notificacion_alerta is None or
                (ahora - self.ultima_notificacion_alerta).total_seconds() > 7200
            )
            if debe_notificar:
                self.ultima_notificacion_alerta = ahora
                self.tray_icon.showMessage(
                    "🚨 ALERTA CRÍTICA: RIESGO DE INUNDACIÓN",
                    f"Bomba inactiva por {info['horas_transcurridas']} horas (~{info['ciclos_pendientes']} ciclos sin bombeo).\nHaz clic para auditar el sismograma.",
                    QSystemTrayIcon.Critical,
                    10000
                )

        # 2. Recordatorio Diario: Si no se ha procesado hoy y ya pasaron las 09:00 AM
        elif info['estado'] == "PENDIENTE":
            es_hora_recordatorio = ahora.hour >= 9
            debe_notificar = manual or (
                es_hora_recordatorio and (
                    self.ultima_notificacion_recordatorio is None or
                    self.ultima_notificacion_recordatorio.date() < ahora.date()
                )
            )
            if debe_notificar:
                self.ultima_notificacion_recordatorio = ahora
                self.tray_icon.showMessage(
                    "⚠️ Recordatorio Diario - Monitoreo de Filtraciones",
                    f"Aún no se ha realizado la revisión diaria de caudales (Último: {info['ultimo_dt'].strftime('%d/%m %H:%M')}).\nHaz clic para abrir el análisis.",
                    QSystemTrayIcon.Warning,
                    8000
                )

        # 3. Estado Normal
        elif manual:
            self.tray_icon.showMessage(
                "🟢 Monitoreo de Filtraciones al Día",
                f"Último bombeo registrado: {info['ultimo_dt'].strftime('%Y-%m-%d %H:%M')} ({info['ultimo_caudal']} L/s).\nSistema operando con normalidad.",
                QSystemTrayIcon.Information,
                5000
            )


if __name__ == '__main__':
    app = VigilanteCaudales(sys.argv)
    sys.exit(app.exec_())
