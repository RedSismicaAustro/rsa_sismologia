"""
PROCESAMIENTO SISMICO – Programa unificado (Analógico / Digital)

Modos excluyentes:
- Modo Analógico (automático): lee binario continuo, reanuda con analogico.csv, inyecta al MSEED diario.
- Modo Digital (acelerógrafos): detecta MSEED del día, une SIEMPRE los nuevos, actualiza digital.csv (multiestación).

Reglas:
- Sin manejo especial de OBSID.
- Fechas siempre en YYYYMMDD.
- digital.csv: cabecera + una fila por estación digital del día (Archivo;Estacion;mseeds), reinicio si no es el día actual.
- analogico.csv: 2 líneas (Archivo;puntero;segundo_m;contador_s), reanudación exacta del binario analógico.

Autor: Tu equipo
"""

import os
import sys
import re
import csv
import struct
from pathlib import Path
from datetime import datetime

# ========= CONFIGURACIÓN RÁPIDA =========
MODO_POR_DEFECTO = "digital"   # "digital" o "analogico"
# ========================================

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
from metodos_gestion import parametros_estaciones, obtener_directorios, loc_cabecera
import numpy as np
import obspy
from obspy import read, Stream, Trace, UTCDateTime
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import QDate, QCoreApplication

# =============================================================================
# Utilitarios comunes (nombres y conversiones)
# =============================================================================

def nombre_mseed(nombre_prefijo: str, fecha_):
    """
    Construye 'NOMBRE_AAAAMMDD_hhmmss.mseed' usando:
      fecha_ = ((anio,mes,dia,hora,min,seg,n_seg), (anio_s,mes_s,dia_s,hora_s,min_s,seg_s))
    """
    anio_s, mes_s, dia_s, hora_s, minuto_s, segundo_s = fecha_[1]
    return f"{nombre_prefijo}{anio_s}{mes_s}{dia_s}_{hora_s}{minuto_s}{segundo_s}.mseed"

def conversion_mseed_digital(self, fileName: str, fecha_, data_np):
    """
    Construye 3 trazas y escribe un MSEED STEIM1 desde datos digitales ya decodificados (20 bits).
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
# Analógico: lectura binaria común con reanudación (analogico.csv)
# =============================================================================

def Leer_binario_comun(directorio_trabajo, archivo_binario, barra_progreso, Lbl_Mensajes):
    """
    Lee un binario (registro continuo/evento .sis) con 16 canales a 64 sps, int16 LE.
    Reanuda usando analogico.csv (2 líneas): Archivo;puntero;segundo_m;contador_s
    No corta por tiempo: el stream resultante empieza justo después de lo ya existente (sin solapes).
    """
    bytes_por_segundo = 2075  # Diferencia entre marcas observada en equipos (1176 → 3251)
    canal = [[] for _ in range(16)]
    linea = [0]*16
    suma  = [0]*16
    segundos_leidos = []

    # ----- Archivo de control -----
    archivo_analogico = os.path.join(directorio_trabajo, "analogico.csv")
    referencias = []
    contador_segundos = 0
    referencias.append(['Archivo', 'puntero', 'segundo_m', 'contador_s'])

    if os.path.exists(archivo_analogico):
        referencias = lectura_archivo(archivo_analogico)
        # validar estructura mínima
        if len(referencias) < 2 or len(referencias[0]) < 4:
            referencias = [['Archivo','puntero','segundo_m','contador_s'],
                           [archivo_binario, '0', '00000', str(contador_segundos)]]
            escritura_archivo(archivo_analogico, referencias)
        elif referencias[1][0] != archivo_binario:
            # Cambio de archivo o de día → reinicia
            referencias[1] = [archivo_binario, '0', '00000', str(contador_segundos)]
            escritura_archivo(archivo_analogico, referencias)
    else:
        referencias.append([archivo_binario, '0', '00000', str(contador_segundos)])
        escritura_archivo(archivo_analogico, referencias)

    # ----- Abrir binario, localizar cabecera -----
    f = open(archivo_binario, 'rb')
    numero_segundo, configuracion, puntero = loc_cabecera(f)
    with open(obtener_directorios(archivo_binario)['archivo_estaciones'], 'a', newline='') as archivo_estaciones:
        escritor_csv_ = csv.writer(archivo_estaciones, delimiter=';')
        for fila in configuracion:
            escritor_csv_.writerow(fila)

    # Guardar cabecera binaria en archivo para referencia
    puntero = puntero - 5
    f.seek(0)
    cabecera = f.read(puntero)
    ruta_cabecera = os.path.join(directorio_trabajo, "cabecera_sismo")
    with open(ruta_cabecera, "wb") as fout:
        fout.write(cabecera)

    # ----- Estimación de segundos -----
    tamano_archivo = os.path.getsize(archivo_binario)
    segundos_estimados = (max(0, (tamano_archivo - max(0, puntero))) // bytes_por_segundo) - int(referencias[1][3])
    if Lbl_Mensajes is not None:
        Lbl_Mensajes.setText(f"Segundos estimados: {segundos_estimados}")
        QCoreApplication.processEvents()

    if barra_progreso is not None:
        barra_progreso.setRange(0, int(segundos_estimados))
        barra_progreso.setValue(0)
        QCoreApplication.processEvents()

    # ----- Reanudar desde analogico.csv si procede -----
    if puntero == 0:
        try:
            puntero = int(referencias[1][1])
            contador_segundos = int(referencias[1][3])
        except Exception:
            puntero = 0
            contador_segundos = 0

    f.seek(max(0, puntero - 4))  # inicio del segundo menos 4 por el formato de marcas
    contador = 0
    contador_m = 0
    bandera_linea = 1
    bandera_colgado = 0

    if Lbl_Mensajes is not None:
        Lbl_Mensajes.setText("Leyendo archivo binario (analógico)…")
        QCoreApplication.processEvents()

    try:
        while True:
            puntero_marcas = f.tell()
            cabecera_0 = f.read(4)
            if len(cabecera_0) == 0:
                break

            if cabecera_0 == b'\x08\x00\x05\x00':
                numero_segundo = f.read(5)      # 5 bytes del número de segundo (ascii)
                texto_segundo = numero_segundo.decode('ascii', errors='ignore')
                segundos_leidos.append(numero_segundo)
                cabecera_1 = f.read(20)
                if cabecera_1 == b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00':
                    puntero_a = f.tell()
                    cuerpo_ = f.read(2048)
                    if len(cuerpo_) < 2048:
                        break
                    f.seek(puntero_a)
                    contador += 1
                    contador_m += 1
                    if contador_m == 3600:
                        contador_m = 0

                    # Procesamiento 16 canales × 64 muestras
                    for k in range(64):
                        for m in range(16):
                            dato = struct.unpack("<h", f.read(2))[0]
                            if bandera_linea:
                                suma[m] += dato
                                canal[m].append(dato)
                            else:
                                canal[m].append(dato - linea[m])

                    # Corrección offset DC del primer segundo
                    if bandera_linea:
                        for m in range(16):
                            linea[m] = int(suma[m] / 64)
                            inicio = len(canal[m]) - 64
                            for i in range(inicio, inicio + 64):
                                canal[m][i] -= linea[m]
                        bandera_linea = 0

                    # UI progreso
                    if barra_progreso is not None:
                        barra_progreso.setValue(min(contador, int(segundos_estimados)))
                        QCoreApplication.processEvents()

                    contador_segundos += 1

                    # Persistir reanudación (puntero seguro del segundo actual)
                    referencias[1] = [archivo_binario, str(puntero_marcas), texto_segundo, str(contador_segundos)]
                    escritura_archivo(archivo_analogico, referencias)

                else:
                    continue
            else:
                # Búsqueda local si se "colgó" entre marcas
                if bandera_colgado == 0:
                    bandera_colgado = 1
                    for ii in range(0, 2048):
                        f.seek(puntero_marcas + ii)
                        cabecera_0 = f.read(4)
                        if cabecera_0 == b'\x08\x00\x05\x00':
                            puntero_marcas = puntero_marcas + ii
                            bandera_colgado = 0
                            break
                continue

        # Finaliza: guardar último puntero y segundo
        referencias[1] = [archivo_binario, str(puntero_marcas), texto_segundo, str(contador_segundos)]
        escritura_archivo(archivo_analogico, referencias)

    finally:
        f.close()

    huecos = 86400 - contador
    if Lbl_Mensajes is not None:
        Lbl_Mensajes.setText(f"Lectura terminada. Segundos leídos: {contador} — Faltantes: {huecos}")
        QCoreApplication.processEvents()

    return canal, huecos

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

        # Parámetros/estaciones (digital)
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

        # Modo por defecto (puedes cambiarlo a 'analogico')
        self.modo = MODO_POR_DEFECTO

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

    # ------------- Entradas principales ------------- #

    def Iniciar(self):
        """
        Punto de entrada: decide modo a ejecutar. Por defecto: Digital.
        Si tu UI tiene algún control (checkbox/radiobutton) para modo, puedes leerlo aquí.
        """
        if hasattr(self, 'Lbl_Mensajes') and self.Lbl_Mensajes is not None:
            self.Lbl_Mensajes.setText(f"Iniciando en modo: {self.modo.upper()}")
            QCoreApplication.processEvents()

        if self.modo.lower() == "analogico":
            self.procesar_modo_analogico()
        else:
            self.procesar_modo_digital()

    # ===================== MODO DIGITAL (ACELERÓGRAFOS) ===================== #

    def procesar_modo_digital(self):
        """
        Por cada estación digital habilitada:
          1) Recolecta MSEED del día (regex YYYYMMDD)
          2) Calcula NUEVOS (digital.csv multiestación)
          3) Une SIEMPRE nuevos, merge(method=0), un solo write
          4) Actualiza fila de esa estación en digital.csv
          5) Genera PNG EEEE_AAAAMMDD_000000.png
        """
        self.definir_dia()

        try:
            dir_aux = os.listdir(self.directorio_binario)
        except FileNotFoundError:
            QMessageBox.information(self, "Advertencia", f"No existe el directorio: {self.directorio_binario}")
            return

        dia_yyyymmdd = self.date.toString('yyyyMMdd')   # 8 dígitos
        archivo_evento = dia_yyyymmdd + "000000"        # AAAAMMDD000000
        archivo_digital = os.path.join(self.directorio_trabajo, "digital.csv")  # CONTROL MULTIESTACIÓN

        # Cargar/normalizar control
        if os.path.exists(archivo_digital):
            filas_ctrl = lectura_archivo(archivo_digital)
        else:
            filas_ctrl = []

        if not filas_ctrl or len(filas_ctrl) == 0 or filas_ctrl[0][0] != 'Archivo':
            filas_ctrl = [['Archivo', 'Estacion', 'mseeds']]

        # Reinicio por día: limpiar cualquier fila que no coincida con el día actual
        filas_filtradas = [filas_ctrl[0]]
        for idx in range(1, len(filas_ctrl)):
            if len(filas_ctrl[idx]) >= 2 and filas_ctrl[idx][0] == archivo_evento:
                filas_filtradas.append(filas_ctrl[idx])
        filas_ctrl = filas_filtradas

        # Recorrer estaciones digitales (saltando cabecera de digitales.csv)
        for estacion_digital in self.est_digitales_[1:]:
            num_estacion = int(estacion_digital[1])
            if self.estacion_habilitada[num_estacion] != '1':
                if hasattr(self, 'Lbl_Mensajes'):
                    self.Lbl_Mensajes.setText(f"Estación {self.nombre_estacion[num_estacion]} ({self.codigo_estacion[num_estacion]}) NO habilitada")
                    QCoreApplication.processEvents()
                continue

            nombre_dir_estacion = estacion_digital[0]
            estacion = self.codigo_estacion[num_estacion]  # 'EEEE'
            self.lista_archivos_mseed = []

            if nombre_dir_estacion not in dir_aux:
                if hasattr(self, 'Lbl_Mensajes'):
                    self.Lbl_Mensajes.setText(f"Estación {nombre_dir_estacion}: sin carpeta en 'Datos Estaciones' (sin registros)")
                    QCoreApplication.processEvents()
                continue

            ruta_est = os.path.join(self.directorio_binario, nombre_dir_estacion)
            try:
                archivos_est = os.listdir(ruta_est)
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo listar {ruta_est}: {e}")
                continue

            # Detección robusta por regex YYYYMMDD_hhmmss
            patron = re.compile(rf"^{re.escape(estacion)}_(\d{{8}})_(\d{{6}})\.mseed$", re.IGNORECASE)
            for nombre_arch in archivos_est:
                m = patron.match(nombre_arch)
                if not m:
                    continue
                fecha8 = m.group(1)
                if fecha8 == dia_yyyymmdd:
                    self.lista_archivos_mseed.append(os.path.join(ruta_est, nombre_arch))

            if not self.lista_archivos_mseed:
                if hasattr(self, 'Lbl_Mensajes'):
                    self.Lbl_Mensajes.setText(f"Estación {nombre_dir_estacion}: sin MSEED del día {dia_yyyymmdd}")
                    QCoreApplication.processEvents()
                continue

            # Localizar/crear fila de esta estación
            indice_fila_est = None
            for idx in range(1, len(filas_ctrl)):
                if len(filas_ctrl[idx]) >= 2 and filas_ctrl[idx][0] == archivo_evento and filas_ctrl[idx][1] == estacion:
                    indice_fila_est = idx
                    break
            if indice_fila_est is None:
                filas_ctrl.append([archivo_evento, estacion, ''])
                indice_fila_est = len(filas_ctrl) - 1

            campo_prev = filas_ctrl[indice_fila_est][2] if len(filas_ctrl[indice_fila_est]) > 2 else ''
            previos = [p for p in str(campo_prev).strip().strip('"').strip("'").split(' ') if p]
            previos = list(dict.fromkeys(previos))
            prev_set = set(previos)

            detectados_base = [os.path.basename(p) for p in self.lista_archivos_mseed]
            detectados_base = list(dict.fromkeys([p for p in detectados_base if p]))
            nuevos_base = [m for m in detectados_base if m not in prev_set]

            mapa_rutas = {os.path.basename(p): p for p in self.lista_archivos_mseed}
            nuevos_rutas = [mapa_rutas[m] for m in nuevos_base if m in mapa_rutas]

            archivo_unido = os.path.join(self.directorio_registros, f"{estacion}_{archivo_evento}.mseed")

            if hasattr(self, 'Lbl_Mensajes'):
                self.Lbl_Mensajes.setText(f"[{estacion}] detectados: {len(detectados_base)} | nuevos: {len(nuevos_base)}")
                QCoreApplication.processEvents()

            # Unión incremental siempre de lo nuevo
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

            # Actualizar control de esta estación
            totales = previos + [m for m in nuevos_base]
            filas_ctrl[indice_fila_est] = [archivo_evento, estacion, " ".join(totales)]

            if hasattr(self, 'Lbl_Mensajes'):
                self.Lbl_Mensajes.setText(f"[{estacion}] Unión completada: {len(nuevos_base)} nuevos → {archivo_unido}")
                QCoreApplication.processEvents()

            # Dayplot PNG
            try:
                st_final = obspy.read(archivo_unido)
                canal_sel = max(0, int(self.canal_[num_estacion]) - 1)  # 0..2
                nombrepng = os.path.join(self.directorio, f"{estacion}_{archivo_evento[:8]}_{archivo_evento[8:]}.png")
                st_final[canal_sel].plot(
                    type='dayplot',
                    outfile=nombrepng,
                    dpi=200,
                    size=(2400, 1800),
                    linewidth=0.2
                )
                if hasattr(self, 'Lbl_Mensajes'):
                    self.Lbl_Mensajes.setText(f"[{estacion}] Dayplot generado: {nombrepng}")
                    QCoreApplication.processEvents()
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo generar dayplot para {estacion}: {e}")

        # Escribir digital.csv al final
        escritura_archivo(archivo_digital, filas_ctrl)
        print("¡¡Estaciones digitales terminadas!!")

    # ===================== MODO ANALÓGICO (AUTOMÁTICO) ===================== #

    def procesar_modo_analogico(self):
        """
        Flujo analógico:
          1) Determina archivo binario a leer (según self.archivo y reglas de tu fuente).
          2) Reanuda con analogico.csv y obtiene canales.
          3) Convierte a Stream/trazas y lo inyecta al MSEED diario de su estación (merge method=0).
          4) Genera PNG EEEE_AAAAMMDD_000000.png.
          5) NO toca digital.csv.
        """
        self.definir_dia()

        # 1) Localizar binario analógico del día actual.
        #    Aquí asumo convención: archivo_binario = self.archivo + ".sis" (ajústalo si tu naming cambia)
        archivo_binario = self.archivo + ".sis"
        if not os.path.exists(archivo_binario):
            QMessageBox.information(self, "Advertencia", f"No existe el binario analógico: {archivo_binario}")
            return

        # Estación asociada al analógico: usa el índice correcto según tu configuración
        # Aquí se asume que la estación (analog) es conocida; puedes mapear por nombre de archivo o UI.
        # Para ejemplo, tomo la estación 0 (ajústalo a tu caso real):
        num_estacion = 0
        estacion = self.codigo_estacion[num_estacion]
        archivo_evento = self.date.toString('yyyyMMdd') + "000000"

        # 2) Leer binario con reanudación
        barra = getattr(self, 'barra_progreso', None) if hasattr(self, 'barra_progreso') else None
        lbl = getattr(self, 'Lbl_Mensajes', None) if hasattr(self, 'Lbl_Mensajes') else None
        canales, huecos = Leer_binario_comun(self.directorio_trabajo, archivo_binario, barra, lbl)

        # 3) Convertir a traza(s) e inyectar al MSEED diario (ajusta canales/frecuencia si corresponde)
        #    Aquí muestro un ejemplo con 3 canales a partir de los 16 leídos (elige los índices que correspondan).
        try:
            # Selección de 3 canales (ejemplo: 0,1,2). Ajusta según tu equipo.
            data_np = np.array([np.array(canales[0], dtype=np.int32),
                                np.array(canales[1], dtype=np.int32),
                                np.array(canales[2], dtype=np.int32)])

            # Tiempo de inicio: derivarlo del binario o de self.date (inicio del día)
            t0 = UTCDateTime(f"{self.date.toString('yyyy-MM-dd')}T00:00:00")

            # Construir trazas crudas (si no usas obtenerTraza para analógico)
            fs = 64.0  # Hz
            trazas = []
            for i, comp in enumerate(('HN1', 'HE2', 'HZ')):  # etiquetas ejemplo
                tr = Trace(data=data_np[i].astype(np.int32))
                tr.stats.network = "XX"
                tr.stats.station = estacion
                tr.stats.location = ""
                tr.stats.channel = comp
                tr.stats.starttime = t0
                tr.stats.sampling_rate = fs
                trazas.append(tr)
            st_new = Stream(traces=trazas)

            # Inyectar/Unir al diario
            archivo_unido = os.path.join(self.directorio_registros, f"{estacion}_{archivo_evento}.mseed")
            if os.path.exists(archivo_unido):
                st_base = obspy.read(archivo_unido)
            else:
                st_base = Stream()

            st_base += st_new
            st_base.merge(method=0, fill_value='latest')
            st_base.write(archivo_unido, format='MSEED', encoding='STEIM1', reclen=512)

            if hasattr(self, 'Lbl_Mensajes'):
                self.Lbl_Mensajes.setText(f"[{estacion}] Analógico unido → {archivo_unido}")
                QCoreApplication.processEvents()

            # 4) Dayplot PNG
            try:
                canal_sel = 0  # elige la traza a graficar
                nombrepng = os.path.join(self.directorio, f"{estacion}_{archivo_evento[:8]}_{archivo_evento[8:]}.png")
                st_base[canal_sel].plot(
                    type='dayplot',
                    outfile=nombrepng,
                    dpi=200,
                    size=(2400, 1800),
                    linewidth=0.2
                )
                if hasattr(self, 'Lbl_Mensajes'):
                    self.Lbl_Mensajes.setText(f"[{estacion}] Dayplot analógico generado: {nombrepng}")
                    QCoreApplication.processEvents()
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo generar dayplot analógico para {estacion}: {e}")

        except Exception as e:
            QMessageBox.information(self, "Error", f"Error en conversión/inyección analógica: {e}")
            return


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    app.exec_()
