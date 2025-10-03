import sys
import os
from pathlib import Path
import matplotlib
matplotlib.use('Qt5Agg')  # Seguridad en entornos PyQt5
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel
from metodos_rsa import lectura_archivo, escritura_archivo


# ========================
# Utilitario de proyecto
# ========================
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    """
    Extrae el path hasta el directorio dado (incluyéndolo).
    Si no existe en la ruta, devuelve ''.
    """
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    else:
        return ''


# Resolver rutas de librerías/datos (opcional; si no las usas, no pasa nada)
ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias and ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
# Nota: no es habitual meter "datos" en sys.path; lo omito para no ensuciar imports.


# ============================
# Clase principal de la GUI
# ============================
class ProcesadorNiveles(QWidget):
    """
    Procesa archivos .csv de niveles:
    - Detecta formato de fecha por archivo.
    - Normaliza y consolida en niveles.csv
    - Mantiene archivo de historial archivos.csv
    - Resuelve duplicados por timestamp y filtra atípicos locales.
    - Grafica la serie resultante.
    """

    def __init__(self):
        super().__init__()
        self.initUI()

    # -----------------------
    # Interfaz básica
    # -----------------------
    def initUI(self):
        layout = QVBoxLayout()
        self.label = QLabel("Selecciona el directorio con los archivos CSV")
        layout.addWidget(self.label)

        self.button = QPushButton("Seleccionar Directorio")
        self.button.clicked.connect(self.seleccionar_directorio)
        layout.addWidget(self.button)

        self.setLayout(layout)
        self.setWindowTitle("Procesador de Niveles de Presa")
        self.setGeometry(300, 300, 520, 200)

    def seleccionar_directorio(self):
        directory = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio")
        if directory:
            self.label.setText(f"Directorio seleccionado: {directory}")
            self.procesar_archivos(directory)

    # ----------------------------------------------
    # Detección de formato de fecha (por archivo)
    # ----------------------------------------------
    def determinar_formato_fecha(self, fechas):
        """
        Determina el formato de fecha a partir de una muestra pequeña del archivo.
        Devuelve el primer formato que parsea TODA la muestra.
        Esta función se llama por CADA ARCHIVO a procesar.
        """
        # Muestra acotada para rendimiento y robustez
        muestra = [f for f in fechas if f]  # descarta None/'' en la muestra
        muestra = muestra[:50] if len(muestra) > 50 else muestra

        formatos = [
            # dd/mm/AAAA y mm/dd/AAAA con o sin segundos
            '%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M',    '%m/%d/%Y %H:%M',
            # separador con guiones
            '%d-%m-%Y %H:%M:%S', '%m-%d-%Y %H:%M:%S',
            '%d-%m-%Y %H:%M',    '%m-%d-%Y %H:%M',
            # ISO-like
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'
        ]

        for formato in formatos:
            try:
                for f in muestra:
                    datetime.strptime(f, formato)
                return formato
            except Exception:
                continue

        raise ValueError("Formato de fecha no reconocido en la muestra de datos del archivo.")

    # ------------------------------------------------------
    # Normalización por archivo (usa formato detectado)
    # ------------------------------------------------------
    def leer_csv_con_formato_por_archivo(self, ruta_csv):
        """
        Lee un csv con cabecera en 3 primeras filas, detecta FORMATO DE FECHA PARA ESE ARCHIVO,
        y retorna filas normalizadas con:
          - fecha (columna 1) como datetime
          - valor (columna 2) como float (soporta coma decimal)
        Devuelve lista vacía si no se puede parsear.
        """
        datos_crudos = lectura_archivo(ruta_csv)
        if not datos_crudos or len(datos_crudos) < 4:
            return []

        # Quitamos 3 filas de cabecera del archivo fuente
        filas_datos = datos_crudos[3:]

        # Extraemos pequeña muestra de fechas de la columna 1
        fechas_muestra = []
        for fila in filas_datos[:80]:
            if len(fila) > 1 and fila[1]:
                fechas_muestra.append(str(fila[1]).strip())

        # Detectar formato **para este archivo**
        formato = self.determinar_formato_fecha(fechas_muestra)

        # Parsear filas
        normalizadas = []
        for fila in filas_datos:
            if len(fila) < 3:
                continue
            fecha_txt = str(fila[1]).strip()
            valor_txt = str(fila[2]).strip()
            if not fecha_txt:
                continue
            try:
                fecha_dt = datetime.strptime(fecha_txt, formato)
                valor_num = float(valor_txt.replace(',', '.'))
                fila_out = list(fila)
                fila_out[1] = fecha_dt
                fila_out[2] = valor_num
                normalizadas.append(fila_out)
            except Exception as ex:
                print("Error parseando fila:", fila, "->", ex)
                continue

        return normalizadas

    # --------------------------------------------------------------------
    # Depuración por vecindad: duplicados y atípicos locales
    # --------------------------------------------------------------------
    def depurar_por_vecindad(self, filas, max_delta_por_hora=None,
                             umbral_abs_interpolacion=0.25,
                             factor_relativo_vecinos=3.0):
        """
        1) Resuelve duplicados por timestamp eligiendo el candidato más coherente con vecinos.
        2) Elimina valores atípicos locales (outliers) basados en:
           - Desviación respecto a interpolación lineal entre vecinos (si existen ambos).
           - Desviación relativa respecto a un único vecino (si falta uno).
           - (Opcional) Cota física de variación por hora (max_delta_por_hora).

        Entradas:
            filas: lista de filas con fecha(datetime) en [1], valor(float) en [2].
        Retorna:
            lista depurada, ordenada, sin duplicados ni outliers.
        """
        from statistics import median

        if not filas:
            return []

        # Orden temporal y agrupación por timestamp
        filas_ordenadas = sorted(filas, key=lambda x: x[1])
        grupos = {}
        for fila in filas_ordenadas:
            grupos.setdefault(fila[1], []).append(fila)
        tiempos = sorted(grupos.keys())

        # Mediana preliminar por timestamp (referencia robusta)
        prelim = {t: median(float(f[2]) for f in grupos[t]) for t in tiempos}

        # 1) Resolver duplicados por coherencia con vecinos
        elegidos = {}
        ultimo_valor_elegido = None
        for i, t in enumerate(tiempos):
            candidatos = grupos[t]
            v_prev = ultimo_valor_elegido
            v_sig = prelim[tiempos[i+1]] if i + 1 < len(tiempos) else None

            if len(candidatos) == 1:
                fila_ok = candidatos[0]
            else:
                mejor, mejor_costo = None, float('inf')
                for fila in candidatos:
                    v = float(fila[2])
                    costo = 0.0
                    if v_prev is not None:
                        costo += abs(v - v_prev)
                    if v_sig is not None:
                        costo += abs(v - v_sig)
                    if v_prev is None and v_sig is None:
                        costo += abs(v - prelim[t])  # sin vecinos: caemos a mediana local
                    if costo < mejor_costo:
                        mejor_costo, mejor = costo, fila
                fila_ok = mejor

            elegidos[t] = fila_ok
            ultimo_valor_elegido = float(fila_ok[2])

        base = [elegidos[t] for t in tiempos]

        # 2) Filtrado de outliers locales
        def horas_entre(t1, t2):
            return abs((t2 - t1).total_seconds()) / 3600.0

        depurada = []
        n = len(base)
        for i, fila in enumerate(base):
            t = fila[1]
            v = float(fila[2])

            # Buscar vecinos válidos
            j_prev = i - 1
            while j_prev >= 0 and base[j_prev] is None:
                j_prev -= 1
            j_sig = i + 1
            while j_sig < n and base[j_sig] is None:
                j_sig += 1

            tiene_prev = (j_prev >= 0)
            tiene_sig = (j_sig < n)

            descartar = False

            # c) Cota física de variación por hora (si aplica)
            if max_delta_por_hora is not None:
                if tiene_prev:
                    dt_h = horas_entre(base[j_prev][1], t)
                    if dt_h > 0:
                        if abs((v - float(base[j_prev][2])) / dt_h) > max_delta_por_hora:
                            descartar = True
                if not descartar and tiene_sig:
                    dt_h = horas_entre(t, base[j_sig][1])
                    if dt_h > 0:
                        if abs((float(base[j_sig][2]) - v) / dt_h) > max_delta_por_hora:
                            descartar = True

            # a) Interpolación lineal si hay ambos vecinos
            if not descartar and tiene_prev and tiene_sig:
                t_prev, v_prev = base[j_prev][1], float(base[j_prev][2])
                t_sig, v_sig = base[j_sig][1], float(base[j_sig][2])
                dt_total = (t_sig - t_prev).total_seconds()
                if dt_total > 0:
                    alfa = (t - t_prev).total_seconds() / dt_total
                    v_interp = v_prev + alfa * (v_sig - v_prev)
                    if abs(v - v_interp) > umbral_abs_interpolacion:
                        descartar = True

            # b) Solo un vecino: test relativo
            if not descartar and (tiene_prev ^ tiene_sig):
                v_vecino = float(base[j_prev][2]) if tiene_prev else float(base[j_sig][2])
                diff_tipica = abs(v_vecino - prelim[t]) if t in prelim else abs(v - v_vecino)
                if diff_tipica == 0:
                    diff_tipica = 1e-9
                if abs(v - v_vecino) > factor_relativo_vecinos * diff_tipica:
                    descartar = True

            if not descartar:
                depurada.append(fila)

        return depurada

    # ----------------------------------------------
    # Procesamiento principal de archivos
    # ----------------------------------------------
    def procesar_archivos(self, directory):
        """
        Flujo completo:
        - Lee niveles.csv y archivos.csv (si existen) y quita cabeceras si corresponde.
        - Recorre los .csv del directorio, detecta formato POR ARCHIVO y normaliza.
        - Mergea con lo existente.
        - Resuelve duplicados y filtra atípicos locales.
        - Escribe niveles.csv y archivos.csv con cabeceras coherentes.
        - Grafica la serie final.
        """
        archivo_niveles = os.path.join(directory, 'niveles.csv')
        archivo_archivos = os.path.join(directory, 'archivos.csv')

        # Lectura de existentes
        niveles_existentes = lectura_archivo(archivo_niveles) or []
        archivos_existentes = lectura_archivo(archivo_archivos) or []

        def quitar_cabecera_si_corresponde(filas):
            """
            Si la primera fila parece cabecera (tiene letras), quitamos 3 filas.
            Si el archivo ya no tiene cabeceras, no quitamos nada.
            """
            if len(filas) >= 3:
                hay_texto = any(any(c.isalpha() for c in str(celda)) for celda in filas[0])
                return filas[3:] if hay_texto else filas
            return filas

        niveles_existentes = quitar_cabecera_si_corresponde(niveles_existentes)
        archivos_existentes = quitar_cabecera_si_corresponde(archivos_existentes)

        # Convertir niveles existentes a datetime/float, aceptando formatos mixtos
        formatos_posibles = [
            '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M',
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
            '%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M',
            '%d/%m/%y %H:%M:%S', '%d/%m/%y %H:%M'
        ]

        def a_datetime(maybe_str):
            if isinstance(maybe_str, datetime):
                return maybe_str
            if not maybe_str:
                return None
            s = str(maybe_str).strip()
            for fmt in formatos_posibles:
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
            return None

        niveles_normalizados = []
        for fila in niveles_existentes:
            if len(fila) < 3:
                continue
            fdt = a_datetime(fila[1])
            if fdt is None:
                continue
            try:
                v = float(str(fila[2]).replace(',', '.'))
            except Exception:
                continue
            fila_norm = list(fila)
            fila_norm[1] = fdt
            fila_norm[2] = v
            niveles_normalizados.append(fila_norm)

        # Historial de archivos ya procesados
        ya_procesados = set()
        for fila in archivos_existentes:
            if fila and len(fila) >= 1:
                ya_procesados.add(str(fila[0]).strip())

        # Procesar nuevos .csv del directorio (formato por archivo)
        nuevos_archivos = []
        for nombre in sorted(os.listdir(directory)):
            if not nombre.lower().endswith('.csv'):
                continue
            if nombre in ('niveles.csv', 'archivos.csv'):
                continue
            if nombre in ya_procesados:
                continue

            ruta_csv = os.path.join(directory, nombre)
            print("Procesando:", ruta_csv)
            filas_norm = self.leer_csv_con_formato_por_archivo(ruta_csv)
            if not filas_norm:
                print("Saltando (vacío o ilegible):", nombre)
                continue

            niveles_normalizados.extend(filas_norm)
            nuevos_archivos.append([nombre])

        # Resolver duplicados y filtrar outliers locales (ajusta parámetros a tu realidad)
        niveles_depurados = self.depurar_por_vecindad(
            niveles_normalizados,
            max_delta_por_hora=0.30,        # 30 cm/h; pon None si no quieres este control
            umbral_abs_interpolacion=0.25,  # tolerancia vs interpolación
            factor_relativo_vecinos=3.0     # severidad con un solo vecino
        )

        # Orden ya viene temporal por la depuración; convertimos fecha a string estable (AAAA de 4 dígitos)
        for fila in niveles_depurados:
            fila[1] = fila[1].strftime("%d/%m/%Y %H:%M:%S")
            # valor en formato compacto
            fila[2] = f"{float(fila[2]):.6f}".rstrip('0').rstrip('.')

        # Escribir niveles.csv con CABECERA
        cabecera_niveles = [
            ["# Archivo consolidado de niveles"],
            ["# Formato: identificador, fecha(dd/mm/AAAA HH:MM:SS), valor, ..."],
            ["# Generado por ProcesadorNiveles"]
        ]
        escritura_archivo(archivo_niveles, cabecera_niveles + niveles_depurados)

        # Actualizar archivos.csv (historial + nuevos, sin duplicados) con cabecera
        todos_archivos = []
        ya = set()
        for fila in archivos_existentes:
            if not fila:
                continue
            n = str(fila[0]).strip()
            if n and n not in ya:
                ya.add(n)
                todos_archivos.append([n])
        for fila in nuevos_archivos:
            n = str(fila[0]).strip()
            if n and n not in ya:
                ya.add(n)
                todos_archivos.append([n])

        cabecera_archivos = [
            ["# Archivos procesados"],
            ["# Una fila por archivo"],
            ["# nombre"]
        ]
        escritura_archivo(archivo_archivos, cabecera_archivos + todos_archivos)

        self.label.setText("Procesamiento completado.")
        print("Filas consolidadas:", len(niveles_depurados))

        # Graficar usando el mismo formato que guardamos
        self.graficar_niveles(niveles_depurados, "%d/%m/%Y %H:%M:%S")

    # -----------------------
    # Gráfica simple
    # -----------------------
    def graficar_niveles(self, niveles, formato_fecha):
        """
        Recibe niveles con fecha en [1] (string con formato_fecha) y valor en [2].
        Dibuja la serie en Matplotlib.
        """
        try:
            fechas = [datetime.strptime(fila[1], formato_fecha) for fila in niveles]
            valores = [float(fila[2]) for fila in niveles]
        except Exception as ex:
            print("Error preparando datos para gráfico:", ex)
            return

        plt.figure(figsize=(10, 6))
        plt.plot(fechas, valores, marker='o', linestyle='-')
        plt.xlabel('Fecha')
        plt.ylabel('Nivel de la Presa')
        plt.title('Niveles de la Presa a lo Largo del Tiempo')
        plt.xticks(rotation=45)
        plt.grid(True)

        date_format = DateFormatter("%d-%m-%Y %H:%M")
        plt.gca().xaxis.set_major_formatter(date_format)
        plt.tight_layout()
        plt.show()


# ========================
# Ejecución del programa
# ========================
if __name__ == '__main__':
    app = QApplication([])
    ex = ProcesadorNiveles()
    ex.show()
    app.exec_()
