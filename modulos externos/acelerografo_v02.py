# -*- coding: utf-8 -*-
"""
PROCESAMIENTO SISMICO – Unión incremental de MSEED con control multiestación (digital.csv)
- Control: archivo_digital = os.path.join(directorio_trabajo, "digital.csv")
- Formato: Archivo;Estacion;mseeds
  * Archivo  : AAAAMMDD000000 (día actual). Si no coincide → se reinicia todo el control.
  * Estacion : EEEE (código por estación)
  * mseeds   : "m1 m2 m3 ..." (nombres BASE, separados por espacio, sin rutas)
- Lógica:
  * Para cada estación habilitada, recolecta sus MSEED del día.
  * Calcula cuáles son NUEVOS (no registrados en su fila).
  * Une SIEMPRE los nuevos al archivo unido {EEEE}_{AAAAMMDD000000}.mseed.
  * Actualiza/crea la fila de esa estación en digital.csv.
  * Al final, escribe digital.csv completo (cabecera + N filas).
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime

# ==== Rutas base del proyecto ====
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + os.sep
    else:
        return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)

# ==== Librerías del proyecto / terceros ====
from metodos_rsa import imprimir_plt, obtenerTraza, lectura_archivo, escritura_archivo
from metodos_gestion import parametros_estaciones, obtener_directorios

import numpy as np
import obspy
from obspy import read, Stream
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import QDate, QCoreApplication


# =============================================================================
# Utilitarios de digital (manteniendo tu estilo y sin crear APIs nuevas de I/O)
# =============================================================================

def nombre_mseed(nombre_prefijo: str, fecha_):
    """
    Construye 'NOMBRE_AAAAMMDD_hhmmss.mseed' usando la tupla fecha_:
      fecha_ = ((anio,mes,dia,hora,min,seg,n_seg), (anio_s,mes_s,dia_s,hora_s,min_s,seg_s))
    """
    anio_s, mes_s, dia_s, hora_s, minuto_s, segundo_s = fecha_[1]
    return f"{nombre_prefijo}{anio_s}{mes_s}{dia_s}_{hora_s}{minuto_s}{segundo_s}.mseed"

def conversion_mseed_digital(self, fileName: str, fecha_, data_np):
    """
    Construye 3 trazas y escribe un MSEED STEIM1.
    """
    anio, mes, dia, horas, minutos, segundos, _ = fecha_[0]
    nombre_estacion = self.datos_estacion[2]

    trazaCH1 = obtenerTraza(nombre_estacion, 1, data_np[0], (2000 + anio), mes, dia, horas, minutos, segundos, 0)
    trazaCH2 = obtenerTraza(nombre_estacion, 2, data_np[1], (2000 + anio), mes, dia, horas, minutos, segundos, 0)
    trazaCH3 = obtenerTraza(nombre_estacion, 3, data_np[2], (2000 + anio), mes, dia, horas, minutos, segundos, 0)

    stData = Stream(traces=[trazaCH1, trazaCH2, trazaCH3])
    stData.write(fileName, format='MSEED', encoding='STEIM1', reclen=512)

def verificacion_archivo(self, archivo_bin: str):
    """
    Verifica cabecera del archivo binario digital y devuelve tupla fecha_.
    """
    with open(archivo_bin, "rb") as f:
        tramaDatos = np.fromfile(f, np.int8, 2506)

    hora = int(tramaDatos[2503]); minuto = int(tramaDatos[2504]); segundo = int(tramaDatos[2505])
    n_segundo = hora * 3600 + minuto * 60 + segundo
    anio = int(tramaDatos[2500]); mes = int(tramaDatos[2501]); dia = int(tramaDatos[2502])

    anio_s = f"{anio:02d}"; mes_s = f"{mes:02d}"; dia_s = f"{dia:02d}"
    hora_s = f"{hora:02d}"; minuto_s = f"{minuto:02d}"; segundo_s = f"{segundo:02d}"

    return ((anio, mes, dia, hora, minuto, segundo, n_segundo),
            (anio_s, mes_s, dia_s, hora_s, minuto_s, segundo_s))

def lectura_archivo_digital(self, archivo_bin: str):
    """
    Lee archivo digital empaquetado en 20 bits (3 canales, 250 muestras por trama).
    Devuelve numpy.array shape=(3, N).
    """
    datos = [[], [], []]
    bandera = 1
    contador = 0
    avance = 0

    with open(archivo_bin, "rb") as f:
        while bandera:
            trama = np.fromfile(f, np.int8, 2506)
            contador += 1
            if len(trama) != 2506:
                bandera = 0
                break

            if contador == 864:
                contador = 0
                avance += 1
                try:
                    self.Lbl_Mensajes.setText(f'Avance {avance} %')
                    QCoreApplication.processEvents()
                except Exception:
                    pass

            # Decodificación 20 bits por canal
            for j in range(0, 3):
                for i in range(0, 250):
                    d1 = int(trama[i * 10 + j * 3 + 1]) & 0xFF
                    d2 = int(trama[i * 10 + j * 3 + 2]) & 0xFF
                    d3 = int(trama[i * 10 + j * 3 + 3]) & 0xFF
                    x = ((d1 << 12) & 0xFF000) | ((d2 << 4) & 0xFF0) | ((d3 >> 4) & 0xF)
                    if x >= 0x80000:
                        x = x & 0x7FFFF
                        x = -1 * (((~x) + 1) & 0x7FFFF)
                    datos[j].append(int(x))

    return np.asarray(datos)


# =============================================================================
# Interfaz PyQt – aplicación principal
# =============================================================================

ruta_ui = os.path.abspath(os.path.join(ruta_proyecto, "src", "ui", "acelerografos.ui"))
Ui_MainWindow, QtBassClass = uic.loadUiType(ruta_ui)

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PROCESAMIENTO SISMICO")
        self.setupUi(self)

        # Conexiones UI
        self.Btn_Iniciar.clicked.connect(self.Iniciar)
        self.Btn_drive.clicked.connect(self.seleccionar_drive)

        # Fecha hoy → QDate (yyyy-MM-dd)
        d = QDate.currentDate()
        self.dateEdit.setDate(d)
        self.dateEdit.dateChanged.connect(self.showDate)

        # Directorios por defecto
        self.directorio_trabajo = f"G:{os.sep}Mi unidad{os.sep}DIA{os.sep}"
        self.Lbl_directorio.setText(self.directorio_trabajo)
        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
        self.Lbl_directorio_2.setText(self.directorio_binario)

        # Inicializar con fecha actual
        self.showDate(d)
        self.definir_dia()

        # Parámetros/estaciones
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

    # ---------------- UI helpers ---------------- #

    def seleccionar_drive(self):
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Seleccionar carpeta base DIA')
        if not folderpath:
            return
        if not folderpath.endswith(os.sep):
            folderpath += os.sep

        self.directorio_trabajo = folderpath
        self.Lbl_directorio.setText(self.directorio_trabajo)

        self.directorio_binario = os.path.join(self.directorio_trabajo, "Datos Estaciones") + os.sep
        if not os.path.exists(self.directorio_binario):
            folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'SELECCIONAR DIRECTORIO "Datos Estaciones"')
            if not folderpath:
                return
            if not folderpath.endswith(os.sep):
                folderpath += os.sep
            self.directorio_binario = folderpath

        self.Lbl_directorio_2.setText(self.directorio_binario)

    def showDate(self, date: QDate):
        """Inicializa self.archivo (ID base del día) con AAAAMMDD000000."""
        self.date = date
        self.archivo = os.path.join(self.directorio_trabajo, date.toString('yyyyMMdd') + '000000')

    # ------------- Lógica principal ------------- #

    def Iniciar(self):
        """
        Por cada estación habilitada:
          1) Recolecta MSEED del día
          2) Une SIEMPRE los MSEED NO registrados (digital.csv, una fila por estación)
          3) Actualiza/crea fila de la estación
          4) Al final, escribe digital.csv completo
          5) Genera dayplot del canal seleccionado
        """
        self.definir_dia()

        try:
            dir_aux = os.listdir(self.directorio_binario)
        except FileNotFoundError:
            QMessageBox.information(self, "Advertencia", f"No existe el directorio: {self.directorio_binario}")
            return

        dia_yyyymmdd = self.date.toString('yyyyMMdd')   # 8 dígitos
        archivo_evento = dia_yyyymmdd + "_000000"        # AAAAMMDD000000
        archivo_digital = os.path.join(self.directorio_trabajo, "digital.csv")  # CONTROL MULTIESTACIÓN

        # ==============================
        # Cargar CONTROL al inicio (una sola vez)
        # ==============================
        if os.path.exists(archivo_digital):
            filas_ctrl = lectura_archivo(archivo_digital)
        else:
            filas_ctrl = []

        # Normalizar cabecera
        if not filas_ctrl or len(filas_ctrl) == 0 or filas_ctrl[0][0] != 'Archivo':
            filas_ctrl = [['Archivo', 'Estacion', 'mseeds']]

        # Si el archivo tiene filas de datos y el primer dato no corresponde al día actual,
        # entonces REINICIAR TODO (nuevo día → empezar de cero).
        # (se revisa la primera fila de datos válida)
        indice_primera_fila_valida = None
        for idx in range(1, len(filas_ctrl)):
            if len(filas_ctrl[idx]) >= 2:
                indice_primera_fila_valida = idx
                break
        if indice_primera_fila_valida is not None:
            archivo_en_control = filas_ctrl[indice_primera_fila_valida][0]
            if archivo_en_control != archivo_evento:
                # Día distinto → reiniciar control (mantener solo cabecera)
                filas_ctrl = [['Archivo', 'Estacion', 'mseeds']]

        # ==============================
        # Procesar estaciones habilitadas
        # ==============================
        for estacion_digital in self.est_digitales_[1:]:
            num_estacion = int(estacion_digital[1])
            if self.estacion_habilitada[num_estacion] != '1':
                print(f"Estación {self.nombre_estacion[num_estacion]}, {self.codigo_estacion[num_estacion]} no habilitada")
                continue
            print(f"Estación {self.nombre_estacion[num_estacion]}, {self.codigo_estacion[num_estacion]} habilitada")

            nombre_dir_estacion = estacion_digital[0]             
            estacion = self.codigo_estacion[num_estacion]         # 'EEEE'
            self.lista_archivos_mseed = []                        # limpia lista por estación

            # ¿Existe el directorio de la estación?
            if nombre_dir_estacion not in dir_aux:
                print(f"Estación {nombre_dir_estacion}: no existe carpeta dentro de 'Datos Estaciones'")
                print(f"Estacion {nombre_dir_estacion} no tiene registros para este día.")
                continue

            ruta_est = os.path.join(self.directorio_binario, nombre_dir_estacion)
            try:
                arch_aux = os.listdir(ruta_est)
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo listar {ruta_est}: {e}")
                continue

            # --- Recolección de MSEED del día (como tu lógica original) ---


            
            for arch_ in arch_aux:
                    try:
                        if arch_[5:13] == dia_yyyymmdd:
                            self.lista_archivos_mseed.append(os.path.join(ruta_est, arch_))
                    except Exception:
                        continue
            if not self.lista_archivos_mseed:
                print(f"Estacion {nombre_dir_estacion} no tiene registros para este día.")
                continue

            # ==============================
            # CONTROL: localizar/crear la fila de esta estación
            # ==============================
            indice_fila_estacion = None
            for idx in range(1, len(filas_ctrl)):
                if len(filas_ctrl[idx]) >= 2:
                    if filas_ctrl[idx][0] == archivo_evento and filas_ctrl[idx][1] == estacion:
                        indice_fila_estacion = idx
                        break

            if indice_fila_estacion is None:
                filas_ctrl.append([archivo_evento, estacion, ''])
                indice_fila_estacion = len(filas_ctrl) - 1

            # Lista previa de mseed registrados para ESTA estación
            campo_prev = filas_ctrl[indice_fila_estacion][2] if len(filas_ctrl[indice_fila_estacion]) > 2 else ''
            previos = [p for p in str(campo_prev).strip().strip('"').strip("'").split(' ') if p]
            # Quitar duplicados preservando orden
            previos = list(dict.fromkeys(previos))
            prev_set = set(previos)

            # Detectados actuales (basenames) y NUEVOS
            detectados_base = [os.path.basename(p) for p in self.lista_archivos_mseed]
            detectados_base = list(dict.fromkeys([p for p in detectados_base if p]))
            nuevos_base = [m for m in detectados_base if m not in prev_set]

            # Mapear nuevos basenames → rutas completas para unir
            mapa_rutas = {os.path.basename(p): p for p in self.lista_archivos_mseed}
            nuevos_rutas = [mapa_rutas[m] for m in nuevos_base if m in mapa_rutas]

            # ==============================
            # UNIÓN: SIEMPRE de lo nuevo (ordenar por starttime real)
            # ==============================
            archivo_unido = os.path.join(self.directorio_registros, f"{estacion}_{archivo_evento}.mseed")

            if nuevos_rutas:
                meta, atrasados = [], []
                for ruta_m in nuevos_rutas:
                    try:
                        st_head = obspy.read(ruta_m, headonly=True)
                        t0 = min(tr.stats.starttime for tr in st_head)
                        meta.append((t0, ruta_m))
                    except Exception:
                        atrasados.append(ruta_m)
                meta.sort(key=lambda x: x[0])
                ordenados = [r for _, r in meta] + atrasados

                # Cargar base y sumar nuevos en memoria
                if os.path.exists(archivo_unido):
                    st_base = obspy.read(archivo_unido)
                else:
                    st_base = obspy.Stream()

                st_add = obspy.Stream()
                for ruta_m in ordenados:
                    try:
                        st_add += obspy.read(ruta_m)
                    except Exception as e:
                        print(f"[ADVERTENCIA] No se pudo leer {ruta_m}: {e}")

                if len(st_add) > 0:
                    st_base += st_add
                    st_base.merge(method=0, fill_value='latest')
                    st_base.write(archivo_unido, format='MSEED', encoding='STEIM1', reclen=512)

            # ==============================
            # ACTUALIZAR FILA de esta estación en control
            # ==============================
            totales = previos + [m for m in nuevos_base]
            filas_ctrl[indice_fila_estacion] = [archivo_evento, estacion, " ".join(totales)]
            print(f"[{estacion}] Nuevos unidos: {len(nuevos_base)} | Total registrados: {len(totales)}")

            # ---------- Parámetros y gráfico dayplot ----------
            try:
                ganancia = self.ganancia[num_estacion]
                diezmado = self.diezmado[num_estacion]
                factor_mult = self.factor_mult[num_estacion]
                canal_sel = int(self.canal_[num_estacion]) - 1  # índice 0..2
            except Exception:
                ganancia, diezmado, factor_mult, canal_sel = 1.0, 1, 1.0, 0

            try:
                st_final = obspy.read(archivo_unido)
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo leer el unido {archivo_unido}: {e}")
                continue

            try:
                nombrepng = os.path.join(self.directorio, f"{estacion}_{archivo_evento}.png")

                st_final[canal_sel].plot(
                    type='dayplot',
                    outfile=nombrepng,
                    dpi=200,
                    size=(2400, 1800),
                    linewidth=0.2
                )
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo generar dayplot para {estacion}: {e}")

        # ==============================
        # Al FINAL: escribir digital.csv completo (cabecera + N filas)
        # ==============================
        escritura_archivo(archivo_digital, filas_ctrl)
        print("¡¡Estaciones digitales terminadas!!")

    # ---------------- Rutas del día ---------------- #

    def definir_dia(self):
        """Crea/asegura directorios base del día usando obtener_directorios(self.archivo)."""
        self.directorios_ = obtener_directorios(self.archivo)
        self.directorio = self.directorios_['Directorio_base']
        self.directorio_dia = self.directorios_['Directorio_dia']
        self.directorio_registros = self.directorios_['Directorio_registros']

        for ruta in (self.directorio, self.directorio_dia, self.directorio_registros):
            try:
                Path(ruta).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo crear {ruta}: {e}")


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    app.exec_()
