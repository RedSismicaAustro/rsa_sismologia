# -*- coding: utf-8 -*-
"""
PROCESAMIENTO SISMICO – Unión incremental de MSEED con control multiestación (digital.csv)

Convenciones clave:
- Nombres de salida:
  · MSEED: EEEE_AAAAMMDD_000000.mseed  (va a self.directorio_registros)
  · PNG  : EEEE_AAAAMMDD_000000.png    (va a self.directorio; uso visual manual)

- Control multies estación: digital.csv  (Archivo;Estacion;mseeds)
  * Archivo  : AAAAMMDD_000000 (día actual, con guion bajo antes de hhmmss)
  * Estacion : EEEE (código por estación)
  * mseeds   : "m1 m2 m3 ..." (nombres base, separados por espacio)

Reglas de negocio:
- Si digital.csv contiene filas de otro día (Archivo != AAAAMMDD_000000), se REINICIA el control
  y se RECONSTRUYEN los unidos del día SUMANDO TODOS los MSEED detectados en fuente.
  (Se muestra un mensaje informativo al usuario)
- Si el día coincide, el unido se actualiza como: “lo ya existente + los NUEVOS no registrados”.
- En todos los casos, digital.csv se escribe al final (cabecera + N filas), deduplicando los nombres.
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime

# ==== Rutas base del proyecto =================================================
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

# ==== Librerías del proyecto / terceros ======================================
from metodos_rsa import imprimir_plt, obtenerTraza, lectura_archivo, escritura_archivo
from metodos_gestion import parametros_estaciones, obtener_directorios

import numpy as np
import obspy
from obspy import read, Stream
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import QDate, QCoreApplication
import matplotlib
matplotlib.use('Agg')

# =============================================================================
# Utilitarios digitales (se mantienen por compatibilidad con otros flujos)
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
        """Inicializa self.archivo (ID base del día) con AAAAMMDD000000 (sin guion, solo para obtener_directorios)."""
        self.date = date
        self.archivo = os.path.join(self.directorio_trabajo, date.toString('yyyyMMdd') + '000000')

    # ------------- Lógica principal ------------- #

    def Iniciar(self):
        """
        Por cada estación habilitada:
          1) Recolecta MSEED del día (por regex acorde a EEEE_AAAAMMDD_hhmmss)
          2) Si el día del control no coincide → reinicia y RECONSTRUYE con TODOS los detectados
          3) Si el día coincide → une SOLO los nuevos no registrados y reescribe unido
          4) Actualiza/crea fila de la estación en digital.csv (sin duplicados)
          5) Genera dayplot del canal seleccionado (PNG visual) en self.directorio
          6) Al final, escribe digital.csv completo
        """
        self.definir_dia()

        try:
            dir_aux = os.listdir(self.directorio_binario)
        except FileNotFoundError:
            QMessageBox.information(self, "Advertencia", f"No existe el directorio: {self.directorio_binario}")
            return

        # Parte central del nombre de día para control: AAAAMMDD_000000 (con guion bajo)
        dia_yyyymmdd = self.date.toString('yyyyMMdd')          # 8 dígitos
        archivo_evento = dia_yyyymmdd + "_000000"              # AAAAMMDD_000000 (esta cadena va en digital.csv)

        archivo_digital = os.path.join(self.directorio_trabajo, "digital.csv")  # CONTROL MULTIESTACIÓN

        # ==============================
        # Cargar/controlar digital.csv
        # ==============================
        if os.path.exists(archivo_digital):
            filas_ctrl = lectura_archivo(archivo_digital)
        else:
            filas_ctrl = []

        # Normalizar cabecera
        if not filas_ctrl or len(filas_ctrl) == 0 or filas_ctrl[0][0] != 'Archivo':
            filas_ctrl = [['Archivo', 'Estacion', 'mseeds']]

        # Si el archivo tiene filas de datos y el primer dato no corresponde al día actual,
        # entonces REINICIAR TODO (nuevo día → empezar de cero) y avisar.
        reinicio_por_dia = False
        indice_primera_fila_valida = None
        for idx in range(1, len(filas_ctrl)):
            if len(filas_ctrl[idx]) >= 2:
                indice_primera_fila_valida = idx
                break
        if indice_primera_fila_valida is not None:
            archivo_en_control = filas_ctrl[indice_primera_fila_valida][0]
            if archivo_en_control != archivo_evento:
                reinicio_por_dia = True
                filas_ctrl = [['Archivo', 'Estacion', 'mseeds']]
                try:
                    QMessageBox.information(
                        self, "Información",
                        f"El día analizado ({archivo_evento}) no coincide con el registrado previamente "
                        f"({archivo_en_control}).\nSe reinicia el control y se reconstruirá la unión del día."
                    )
                except Exception:
                    pass
                print(f"[INFO] Reinicio de control: {archivo_en_control} → {archivo_evento}")

        # ==============================
        # Procesar estaciones habilitadas
        # ==============================
        # Regex de nombres: EEEE_AAAAMMDD_hhmmss*.mseed (estación 4 alfanum., guion subrayado, fecha y hora)
        patron_mseed_dia = re.compile(r'^[A-Za-z0-9]{4}_(\d{8})_(\d{6}).*\.mseed$', re.IGNORECASE)

        for estacion_digital in self.est_digitales_[1:]:
            num_estacion = int(estacion_digital[1])
            if self.estacion_habilitada[num_estacion] != '1':
                print(f"Estación {self.nombre_estacion[num_estacion]}, {self.codigo_estacion[num_estacion]} no habilitada")
                continue
            print(f"Estación {self.nombre_estacion[num_estacion]}, {self.codigo_estacion[num_estacion]} habilitada")

            nombre_dir_estacion = estacion_digital[0]              # nombre de carpeta dentro de "Datos Estaciones"
            estacion = self.codigo_estacion[num_estacion]          # 'EEEE'
            self.lista_archivos_mseed = []                         # limpia lista por estación

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

            # --- Recolección robusta de MSEED del día por regex ---
            for arch_ in arch_aux:
                try:
                    m = patron_mseed_dia.match(arch_)
                    if m and m.group(1) == dia_yyyymmdd:
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

            # Detectados actuales (basenames)
            detectados_base = [os.path.basename(p) for p in self.lista_archivos_mseed]
            detectados_base = list(dict.fromkeys([p for p in detectados_base if p]))

            # NUEVOS respecto al control
            nuevos_base = [m for m in detectados_base if m not in prev_set]

            # Mapear basenames → rutas completas
            mapa_rutas = {os.path.basename(p): p for p in self.lista_archivos_mseed}
            nuevos_rutas = [mapa_rutas[m] for m in nuevos_base if m in mapa_rutas]

            # ==============================
            # UNIÓN: incremental / reconstrucción según 'reinicio_por_dia'
            # ==============================
            # Nombre de unido y png (manteniendo convención EEEE_AAAAMMDD_000000.*)
            archivo_unido = os.path.join(self.directorio_registros, f"{estacion}_{archivo_evento}.mseed")
            nombrepng = os.path.join(self.directorio, f"{estacion}_{archivo_evento}.png")

            # Si el control se reinició por día, reconstruimos **desde cero**:
            # - Eliminamos unido previo del día (si existe) para evitar arrastres
            # - Usamos TODOS los detectados del día (no solo "nuevos")
            if reinicio_por_dia:
                try:
                    if os.path.exists(archivo_unido):
                        os.remove(archivo_unido)
                        print(f"[INFO] Eliminado unido previo para reconstrucción: {archivo_unido}")
                except Exception as e:
                    print(f"[ADVERTENCIA] No se pudo eliminar unido previo {archivo_unido}: {e}")

                rutas_a_unir = [mapa_rutas[b] for b in detectados_base if b in mapa_rutas]
            else:
                # Día consistente → seguimos incremental: unido existente + NUEVOS
                rutas_a_unir = list(nuevos_rutas)

            # Ordenar las rutas a unir por starttime real (mejora de coherencia temporal)
            if rutas_a_unir:
                meta, atrasados = [], []
                for ruta_m in rutas_a_unir:
                    try:
                        st_head = obspy.read(ruta_m, headonly=True)
                        t0 = min(tr.stats.starttime for tr in st_head)
                        meta.append((t0, ruta_m))
                    except Exception:
                        atrasados.append(ruta_m)
                meta.sort(key=lambda x: x[0])
                ordenados = [r for _, r in meta] + atrasados
            else:
                ordenados = []

            # Cargar base (solo si NO estamos reconstruyendo desde cero y existe el unido)
            if not reinicio_por_dia and os.path.exists(archivo_unido):
                try:
                    st_base = obspy.read(archivo_unido)
                except Exception as e:
                    print(f"[ADVERTENCIA] No se pudo leer unido base {archivo_unido}. Se iniciará vacío. Error: {e}")
                    st_base = obspy.Stream()
            else:
                st_base = obspy.Stream()

            # Sumar trazas a partir de 'ordenados'
            if ordenados:
                st_add = obspy.Stream()
                for ruta_m in ordenados:
                    try:
                        st_add += obspy.read(ruta_m)
                    except Exception as e:
                        print(f"[ADVERTENCIA] No se pudo leer {ruta_m}: {e}")

                if len(st_add) > 0:
                    st_base += st_add
                    # Merge sin rellenar con ceros; usa último valor en solapes (coherente con tus flujos)
                    st_base.merge(method=0, fill_value='latest')
                    # Escribir unido del día
                    try:
                        st_base.write(archivo_unido, format='MSEED', encoding='STEIM1', reclen=512)
                    except Exception as e:
                        print(f"[ERROR] No se pudo escribir unido {archivo_unido}: {e}")

            # ==============================
            # ACTUALIZAR FILA de esta estación en control (sin duplicados)
            # ==============================
            if reinicio_por_dia:
                # En reconstrucción, lo razonable es que queden TODOS los detectados del día
                totales = detectados_base
            else:
                totales = previos + [m for m in nuevos_base]

            # Deduplicar preservando orden
            totales = list(dict.fromkeys(totales))
            filas_ctrl[indice_fila_estacion] = [archivo_evento, estacion, " ".join(totales)]
            print(f"[{estacion}] Añadidos ahora: {len(ordenados)} | Total registrados: {len(totales)}")

            # ---------- Parámetros y gráfico dayplot (visual manual) ----------
            # NOTA: Mantengo tu lógica por índice de canal, dado que tu pipeline digital conserva orden de trazas.
            try:
                ganancia = self.ganancia[num_estacion]
                diezmado = self.diezmado[num_estacion]
                factor_mult = self.factor_mult[num_estacion]
                canal_sel = int(self.canal_[num_estacion]) - 1  # índice 0..2
            except Exception:
                ganancia, diezmado, factor_mult, canal_sel = 1.0, 1, 1.0, 0

            try:
                if os.path.exists(archivo_unido):
                    st_final = obspy.read(archivo_unido)
                else:
                    st_final = obspy.Stream()
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo leer el unido {archivo_unido}: {e}")
                continue

            # Generar PNG solo si hay trazas suficientes
            try:
                if len(st_final) > canal_sel:
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
        try:
            escritura_archivo(archivo_digital, filas_ctrl)
            print("¡¡Estaciones digitales terminadas!!")
        except Exception as e:
            print(f"[ERROR] No se pudo escribir {archivo_digital}: {e}")

    # ---------------- Rutas del día ---------------- #

    def definir_dia(self):
        """
        Crea/asegura directorios base del día usando obtener_directorios(self.archivo).

        Convención (proporcionada por tus utilidades):
          - self.directorio           → escritorio base del día (PNG manuales)
          - self.directorio_dia       → carpeta del día (si aplica)
          - self.directorio_registros → carpeta exclusiva para MSEED unidos (uso en procesos)
        """
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

