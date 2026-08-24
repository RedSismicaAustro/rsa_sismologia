import sys
import os
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel

def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    return ''

ruta_librerias = os.path.dirname(__file__)
ruta_proyecto = extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
if not ruta_proyecto:
    raise RuntimeError('No se encontro la raiz del proyecto rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src', 'librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))

if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)
if ruta_datos not in sys.path:
    sys.path.insert(0, ruta_datos)

from rsa_io import lectura_archivo, escritura_archivo


class ProcesadorNiveles(QWidget):
    """
    Procesador y consolidador de registros de nivel de embalses (Chanlud, Labrado):
    - Detecta el formato de fecha de forma independiente por cada archivo CSV.
    - Normaliza fechas al estándar canónico (dd/mm/AAAA HH:MM:SS) y valores numéricos.
    - Resuelve duplicados temporales por coherencia con vecinos.
    - Filtra valores atípicos (outliers) por cota física de variación e interpolación lineal.
    - Mantiene el inventario de archivos procesados y genera la gráfica temporal.
    """

    def __init__(self):
        super().__init__()
        self.inicializar_interfaz()

    def inicializar_interfaz(self):
        layout = QVBoxLayout()
        self.label_estado = QLabel("Selecciona el directorio con los archivos CSV de niveles de embalse")
        layout.addWidget(self.label_estado)

        self.boton_seleccionar = QPushButton("Seleccionar Directorio")
        self.boton_seleccionar.clicked.connect(self.seleccionar_directorio)
        layout.addWidget(self.boton_seleccionar)

        self.setLayout(layout)
        self.setWindowTitle("Procesador de Niveles de Embalse - RSA")
        self.setGeometry(300, 300, 520, 180)

    def seleccionar_directorio(self):
        directorio = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio con Archivos CSV")
        if directorio:
            self.label_estado.setText(f"Directorio seleccionado:\n{directorio}")
            self.procesar_archivos(directorio)

    def determinar_formato_fecha(self, fechas):
        """
        Determina el formato de fecha evaluando una muestra de registros del archivo.
        Devuelve el primer formato que parsea exitosamente la muestra.
        """
        muestra = [f for f in fechas if f][:50]
        formatos = [
            '%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M',    '%m/%d/%Y %H:%M',
            '%d-%m-%Y %H:%M:%S', '%m-%d-%Y %H:%M:%S',
            '%d-%m-%Y %H:%M',    '%m-%d-%Y %H:%M',
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
            '%d/%m/%y %H:%M:%S', '%d/%m/%y %H:%M'
        ]

        for formato in formatos:
            try:
                for f in muestra:
                    datetime.strptime(f, formato)
                return formato
            except Exception:
                continue

        raise ValueError("Formato de fecha no reconocido en la muestra de datos del archivo.")

    def leer_csv_con_formato_por_archivo(self, ruta_csv):
        """
        Lee un archivo CSV individual, determina su formato de fecha propio y
        retorna las filas normalizadas con fecha (datetime) y valor (float).
        """
        datos_crudos = lectura_archivo(ruta_csv)
        if not datos_crudos or len(datos_crudos) < 4:
            return []

        filas_datos = datos_crudos[3:]
        fechas_muestra = []
        for fila in filas_datos[:80]:
            if len(fila) > 1 and fila[1]:
                fechas_muestra.append(str(fila[1]).strip())

        formato = self.determinar_formato_fecha(fechas_muestra)

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
                print(f"Advertencia: No se pudo parsear fila en {os.path.basename(ruta_csv)}: {fila} -> {ex}")
                continue

        return normalizadas

    def depurar_por_vecindad(self, filas, max_delta_por_hora=0.30,
                             umbral_abs_interpolacion=0.25,
                             factor_relativo_vecinos=3.0):
        """
        1) Resuelve duplicados por timestamp eligiendo el candidato más coherente con vecinos.
        2) Elimina valores atípicos locales (outliers) basados en:
           - Cota física de variación por hora (max_delta_por_hora en m/h).
           - Desviación respecto a interpolación lineal entre vecinos contiguos.
           - Desviación relativa respecto a un único vecino disponible.
        """
        from statistics import median

        if not filas:
            return []

        filas_ordenadas = sorted(filas, key=lambda x: x[1])
        grupos = {}
        for fila in filas_ordenadas:
            grupos.setdefault(fila[1], []).append(fila)
        tiempos = sorted(grupos.keys())

        prelim = {t: median(float(f[2]) for f in grupos[t]) for t in tiempos}

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
                        costo += abs(v - prelim[t])
                    if costo < mejor_costo:
                        mejor_costo, mejor = costo, fila
                fila_ok = mejor

            elegidos[t] = fila_ok
            ultimo_valor_elegido = float(fila_ok[2])

        base = [elegidos[t] for t in tiempos]

        def horas_entre(t1, t2):
            return abs((t2 - t1).total_seconds()) / 3600.0

        depurada = []
        n = len(base)
        for i, fila in enumerate(base):
            t = fila[1]
            v = float(fila[2])

            j_prev = i - 1
            while j_prev >= 0 and base[j_prev] is None:
                j_prev -= 1
            j_sig = i + 1
            while j_sig < n and base[j_sig] is None:
                j_sig += 1

            tiene_prev = (j_prev >= 0)
            tiene_sig = (j_sig < n)

            descartar = False

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

            if not descartar and tiene_prev and tiene_sig:
                t_prev, v_prev = base[j_prev][1], float(base[j_prev][2])
                t_sig, v_sig = base[j_sig][1], float(base[j_sig][2])
                dt_total = (t_sig - t_prev).total_seconds()
                if dt_total > 0:
                    alfa = (t - t_prev).total_seconds() / dt_total
                    v_interp = v_prev + alfa * (v_sig - v_prev)
                    if abs(v - v_interp) > umbral_abs_interpolacion:
                        descartar = True

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

    def procesar_archivos(self, directorio):
        archivo_niveles = os.path.join(directorio, 'niveles.csv')
        archivo_archivos = os.path.join(directorio, 'archivos.csv')

        niveles_existentes = lectura_archivo(archivo_niveles) or []
        archivos_existentes = lectura_archivo(archivo_archivos) or []

        def quitar_cabecera_si_corresponde(filas):
            if len(filas) >= 3:
                hay_texto = any(any(c.isalpha() for c in str(celda)) for celda in filas[0])
                return filas[3:] if hay_texto else filas
            return filas

        niveles_existentes = quitar_cabecera_si_corresponde(niveles_existentes)
        archivos_existentes = quitar_cabecera_si_corresponde(archivos_existentes)

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

        ya_procesados = set()
        for fila in archivos_existentes:
            if fila and len(fila) >= 1:
                ya_procesados.add(str(fila[0]).strip())

        nuevos_archivos = []
        for nombre in sorted(os.listdir(directorio)):
            if not nombre.lower().endswith('.csv'):
                continue
            if nombre in ('niveles.csv', 'archivos.csv'):
                continue
            if nombre in ya_procesados:
                continue

            ruta_csv = os.path.join(directorio, nombre)
            print(f"Procesando: {ruta_csv}")
            filas_norm = self.leer_csv_con_formato_por_archivo(ruta_csv)
            if not filas_norm:
                print(f"Saltando (vacio o ilegible): {nombre}")
                continue

            niveles_normalizados.extend(filas_norm)
            nuevos_archivos.append([nombre])

        niveles_depurados = self.depurar_por_vecindad(
            niveles_normalizados,
            max_delta_por_hora=0.30,
            umbral_abs_interpolacion=0.25,
            factor_relativo_vecinos=3.0
        )

        for fila in niveles_depurados:
            fila[1] = fila[1].strftime("%d/%m/%Y %H:%M:%S")
            fila[2] = f"{float(fila[2]):.6f}".rstrip('0').rstrip('.')

        cabecera_niveles = [
            ["# Archivo consolidado de niveles de embalse"],
            ["# Formato: identificador, fecha(dd/mm/AAAA HH:MM:SS), valor_nivel(m), ..."],
            ["# Generado por ProcesadorNiveles - RSA"]
        ]
        escritura_archivo(archivo_niveles, cabecera_niveles + niveles_depurados)

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
            ["# Archivos de nivel procesados"],
            ["# Una fila por archivo CSV incorporado"],
            ["# nombre_archivo"]
        ]
        escritura_archivo(archivo_archivos, cabecera_archivos + todos_archivos)

        self.label_estado.setText(f"Procesamiento completado con éxito.\nTotal registros consolidados: {len(niveles_depurados)}")
        print(f"Filas consolidadas en niveles.csv: {len(niveles_depurados)}")

        self.graficar_niveles(niveles_depurados, "%d/%m/%Y %H:%M:%S")

    def graficar_niveles(self, niveles, formato_fecha):
        try:
            fechas = [datetime.strptime(fila[1], formato_fecha) for fila in niveles]
            valores = [float(fila[2]) for fila in niveles]
        except Exception as ex:
            print(f"Error preparando datos para grafico: {ex}")
            return

        plt.figure(figsize=(10, 6))
        plt.plot(fechas, valores, marker='o', markersize=3, linestyle='-', color='#1f77b4', lw=1.2)
        plt.xlabel('Fecha y Hora')
        plt.ylabel('Nivel de la Presa (m s.n.m.)')
        plt.title('Niveles del Embalse a lo Largo del Tiempo')
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.6)

        date_format = DateFormatter("%d/%m/%Y %H:%M")
        plt.gca().xaxis.set_major_formatter(date_format)
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = ProcesadorNiveles()
    ventana.show()
    sys.exit(app.exec_())
