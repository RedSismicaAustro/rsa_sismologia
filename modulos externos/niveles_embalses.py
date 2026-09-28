import sys
import os
import re
import math
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QFileDialog, QLabel, QDateTimeEdit, QDoubleSpinBox, QMessageBox
)
from PyQt5.QtCore import QDateTime, Qt

def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    return ''

ruta_librerias = os.path.dirname(os.path.abspath(__file__))
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


# Estructura de una marca de tiempo numérica: primer campo, separador, segundo campo, año de 2 o 4
# dígitos y hora opcional (con segundos opcionales). El orden día/mes NO se presupone aquí.
PATRON_FECHA = re.compile(
    r"^\s*(\d{1,2})([/\-.])(\d{1,2})\2(\d{4}|\d{2})"
    r"(?:[ T]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?\s*$"
)

# Estructura año/mes/día (ISO y variantes): el orden de los campos no es ambiguo.
PATRON_FECHA_ISO = re.compile(
    r"^\s*(\d{4})([/\-.])(\d{1,2})\2(\d{1,2})"
    r"(?:[ T]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?\s*$"
)


def analizar_estructura_fecha(texto):
    """
    Descompone una marca de tiempo en su estructura, sin decidir todavía el orden día/mes.

    Devuelve un diccionario con el separador, los campos numéricos, el año, la longitud del año, la
    presencia de hora y segundos y, cuando el orden es inequívoco por construcción (año primero,
    formato ISO), la clave `orden_fijo`. Devuelve None si el texto no tiene estructura de fecha.
    """
    texto = str(texto)

    coincidencia_iso = PATRON_FECHA_ISO.match(texto)
    if coincidencia_iso:
        anio, separador, mes, dia, hora, minuto, segundos = coincidencia_iso.groups()
        return {
            'orden_fijo': 'YMD',
            'separador': separador,
            'primer': int(mes),
            'segundo': int(dia),
            'anio': int(anio),
            'longitud_anio': 4,
            'con_hora': hora is not None,
            'con_segundos': segundos is not None,
        }

    coincidencia = PATRON_FECHA.match(texto)
    if not coincidencia:
        return None

    primer, separador, segundo, anio, hora, minuto, segundos = coincidencia.groups()
    return {
        'orden_fijo': None,
        'separador': separador,
        'primer': int(primer),
        'segundo': int(segundo),
        'anio': int(anio),
        'longitud_anio': len(anio),
        'con_hora': hora is not None,
        'con_segundos': segundos is not None,
    }


def construir_formato_fecha(estructura, orden):
    """
    Construye la cadena de formato `strptime` correspondiente a una estructura de fecha.

    `orden` es 'DMY' (día/mes/año), 'MDY' (mes/día/año) o 'YMD' (año/mes/día, formato ISO); el
    separador, la longitud del año y la presencia de hora se toman de la estructura detectada.
    """
    separador = estructura['separador']
    if orden == 'YMD' or estructura.get('orden_fijo') == 'YMD':
        formato = "%Y{0}%m{0}%d".format(separador)
    else:
        codigo_dia, codigo_mes = ('%d', '%m') if orden == 'DMY' else ('%m', '%d')
        codigo_anio = '%Y' if estructura['longitud_anio'] == 4 else '%y'
        formato = "{}{}{}{}{}".format(
            codigo_dia, separador, codigo_mes, separador, codigo_anio
        )
    if estructura['con_hora']:
        formato += " %H:%M:%S" if estructura['con_segundos'] else " %H:%M"
    return formato


def sugerir_orden_por_evidencia(estructuras):
    """
    Deduce el orden día/mes a partir de evidencia categórica: un campo mayor que 12 no puede ser
    un mes, de modo que decide por sí solo.

    Devuelve (orden, votos_dia_primero, votos_mes_primero); `orden` es None si todos los registros
    son ambiguos (ambos campos <= 12) y, por tanto, la evidencia no alcanza para decidir.
    """
    votos_dia_primero = 0
    votos_mes_primero = 0

    for estructura in estructuras:
        if estructura['primer'] > 12 and estructura['segundo'] <= 12:
            votos_dia_primero += 1
        elif estructura['segundo'] > 12 and estructura['primer'] <= 12:
            votos_mes_primero += 1

    orden = None
    if votos_dia_primero > votos_mes_primero:
        orden = 'DMY'
    elif votos_mes_primero > votos_dia_primero:
        orden = 'MDY'

    return orden, votos_dia_primero, votos_mes_primero


def medir_coherencia_temporal(textos, estructura, orden):
    """
    Mide qué tan coherente es una interpretación día/mes con la secuencia real del archivo.

    Devuelve (retrocesos, regularidad, intervalo_modal_segundos):
      * `retrocesos`: veces que la marca de tiempo retrocede respecto a la anterior.
      * `regularidad`: fracción de intervalos iguales al intervalo modal (0.0 a 1.0).

    Una interpretación equivocada convierte cada cambio de mes en un salto de decenas de días, lo
    que destruye la regularidad del muestreo y suele producir retrocesos en el orden del archivo.
    """
    formato = construir_formato_fecha(estructura, orden)
    marcas = []
    for texto in textos:
        try:
            marcas.append(datetime.strptime(str(texto).strip(), formato))
        except Exception:
            continue

    if len(marcas) < 3:
        return 0, 0.0, 0.0

    intervalos = [(marcas[i + 1] - marcas[i]).total_seconds() for i in range(len(marcas) - 1)]
    retrocesos = sum(1 for intervalo in intervalos if intervalo < 0)
    intervalos_abs = [abs(intervalo) for intervalo in intervalos if intervalo != 0]
    if not intervalos_abs:
        return retrocesos, 0.0, 0.0

    intervalo_modal = max(set(intervalos_abs), key=intervalos_abs.count)
    regulares = sum(1 for intervalo in intervalos_abs if intervalo == intervalo_modal)
    regularidad = regulares / float(len(intervalos_abs))
    return retrocesos, regularidad, intervalo_modal


def deducir_orden_por_cambio_de_dia(textos, maximo_comparaciones=200):
    """
    Deduce el orden día/mes observando directamente el cambio de día dentro de la serie.

    Los registros de niveles son horarios (24 por día), de modo que al pasar de un día al siguiente
    cambia un único campo de la fecha. Basta comparar el primer registro con el último del mismo día
    para saber cuál de los dos campos es el día:

    * si cambia el **segundo** campo y el primero permanece -> el segundo es el día (mes/día/año);
    * si cambia el **primer** campo y el segundo permanece -> el primero es el día (día/mes/año).

    En el cambio de mes cambian ambos campos: entonces el día es el que vuelve a 1. Si el cambio
    resulta ambiguo (1 de enero), se continúa con el siguiente cambio de día de la serie.

    Devuelve (orden, detalle) o (None, '') si no hay ningún cambio de día concluyente (por ejemplo,
    un archivo con datos de un solo día).
    """
    estructuras = []
    for texto in textos[:maximo_comparaciones]:
        estructura = analizar_estructura_fecha(texto)
        if estructura is not None and not estructura.get('orden_fijo'):
            estructuras.append((str(texto).strip(), estructura))

    if len(estructuras) < 2:
        return None, ''

    for indice in range(1, len(estructuras)):
        texto_previo, previa = estructuras[indice - 1]
        texto_actual, actual = estructuras[indice]
        if texto_previo == texto_actual:
            continue

        cambia_primero = previa['primer'] != actual['primer']
        cambia_segundo = previa['segundo'] != actual['segundo']

        if cambia_segundo and not cambia_primero:
            return 'MDY', "cambio de día «{}» -> «{}»: se mueve el segundo campo".format(
                texto_previo, texto_actual)
        if cambia_primero and not cambia_segundo:
            return 'DMY', "cambio de día «{}» -> «{}»: se mueve el primer campo".format(
                texto_previo, texto_actual)

        reinicia_segundo = actual['segundo'] == 1 and previa['segundo'] > 1
        reinicia_primero = actual['primer'] == 1 and previa['primer'] > 1
        if reinicia_segundo and not reinicia_primero:
            return 'MDY', "cambio de mes «{}» -> «{}»: el segundo campo vuelve a 1".format(
                texto_previo, texto_actual)
        if reinicia_primero and not reinicia_segundo:
            return 'DMY', "cambio de mes «{}» -> «{}»: el primer campo vuelve a 1".format(
                texto_previo, texto_actual)

    return None, ''


def deducir_orden_fecha(textos, maximo_coherencia=2000):
    """
    Deduce si las fechas de un archivo están en orden día/mes/año (DMY) o mes/día/año (MDY).

    Estrategia, en orden de prioridad:
      1. **Evidencia categórica**: un campo mayor que 12 sólo puede ser un día, lo que resuelve el
         orden sin ambigüedad (p. ej. `25/03/2024` es día/mes y `03/25/2024` es mes/día).
      2. **Coherencia temporal** (cuando todos los registros son ambiguos): se interpreta la serie
         completa con ambas hipótesis y gana la que reproduce un muestreo regular; la hipótesis
         equivocada transforma los cambios de mes en saltos de decenas de días.
      3. **Convención local**: si ambas interpretaciones resultan equivalentes (por ejemplo, datos
         de un solo día), se asume día/mes/año y se advierte para revisión del analista.

    Devuelve (orden, informe). El informe documenta la evidencia utilizada, los votos de cada
    hipótesis y la advertencia correspondiente, para que quede constancia en la consola del IDE y
    en el inventario de archivos procesados.
    """
    estructuras = [e for e in (analizar_estructura_fecha(t) for t in textos) if e is not None]
    if not estructuras:
        raise ValueError("No se reconoce ninguna estructura de fecha en el archivo.")

    # Estructuras de orden inequívoco por construcción (año primero): no hay nada que deducir.
    if all(estructura.get('orden_fijo') for estructura in estructuras):
        orden = estructuras[0]['orden_fijo']
        return orden, {
            'orden': orden,
            'votos_dia_primero': 0,
            'votos_mes_primero': 0,
            'ambiguo': False,
            'evidencia': 'estructura año/mes/día (ISO): el orden de los campos no es ambiguo',
            'advertencia': '',
        }

    # Método directo: observar el cambio de día en la propia serie horaria.
    orden_cambio, detalle_cambio = deducir_orden_por_cambio_de_dia(textos)
    if orden_cambio is not None:
        return orden_cambio, {
            'orden': orden_cambio,
            'votos_dia_primero': 0,
            'votos_mes_primero': 0,
            'ambiguo': False,
            'evidencia': detalle_cambio,
            'advertencia': '',
        }

    orden, votos_dia_primero, votos_mes_primero = sugerir_orden_por_evidencia(estructuras)
    informe = {
        'orden': orden,
        'votos_dia_primero': votos_dia_primero,
        'votos_mes_primero': votos_mes_primero,
        'ambiguo': orden is None,
        'evidencia': '',
        'advertencia': '',
    }

    if orden is not None:
        nombre_orden = 'día/mes/año' if orden == 'DMY' else 'mes/día/año'
        informe['evidencia'] = (
            "evidencia categórica: {} registro(s) con un campo > 12 -> {}".format(
                votos_dia_primero + votos_mes_primero, nombre_orden)
        )
        if votos_dia_primero and votos_mes_primero:
            informe['advertencia'] = (
                "El archivo mezcla registros que sólo pueden ser día/mes ({}) con otros que sólo "
                "pueden ser mes/día ({}). Se aplicó la interpretación mayoritaria y, en cada fila, "
                "la evidencia propia del registro.".format(votos_dia_primero, votos_mes_primero)
            )
        return orden, informe

    estructura = estructuras[0]
    muestra = textos[:maximo_coherencia]
    retrocesos_dmy, regularidad_dmy, _ = medir_coherencia_temporal(muestra, estructura, 'DMY')
    retrocesos_mdy, regularidad_mdy, _ = medir_coherencia_temporal(muestra, estructura, 'MDY')
    clave_dmy = (retrocesos_dmy, -regularidad_dmy)
    clave_mdy = (retrocesos_mdy, -regularidad_mdy)

    informe['retrocesos_dia_primero'] = retrocesos_dmy
    informe['retrocesos_mes_primero'] = retrocesos_mdy
    informe['regularidad_dia_primero'] = round(regularidad_dmy, 4)
    informe['regularidad_mes_primero'] = round(regularidad_mdy, 4)

    detalle = (
        "sin evidencia categórica (día y mes <= 12 en todos los registros): coherencia temporal "
        "-> retrocesos día/mes {} vs mes/día {}, regularidad {:.2f} vs {:.2f}".format(
            retrocesos_dmy, retrocesos_mdy, regularidad_dmy, regularidad_mdy)
    )

    if clave_mdy < clave_dmy:
        orden = 'MDY'
        informe['evidencia'] = detalle + " -> mes/día/año"
    else:
        orden = 'DMY'
        informe['evidencia'] = detalle + " -> día/mes/año"
        if clave_dmy == clave_mdy:
            informe['advertencia'] = (
                "Todos los registros son ambiguos (día y mes <= 12) y ambas interpretaciones "
                "resultan equivalentes; se asumió día/mes/año por convención de la RSA. Verifique "
                "el archivo si proviene de una fuente con formato mes/día."
            )

    informe['orden'] = orden
    informe['ambiguo'] = True
    return orden, informe


def interpretar_fecha(fecha_txt, orden_archivo, formato_referencia):
    """
    Convierte el texto de una fecha en `datetime` aplicando el orden deducido para el archivo y,
    cuando la propia fila aporta evidencia (un campo mayor que 12 sólo puede ser el día), el orden
    que esa fila impone. Devuelve None si el texto no puede interpretarse.
    """
    fecha_txt = str(fecha_txt).strip()
    estructura = analizar_estructura_fecha(fecha_txt)

    if estructura is None:
        formato_fila = formato_referencia
    else:
        orden_fila = orden_archivo
        if estructura.get('orden_fijo'):
            orden_fila = estructura['orden_fijo']
        elif estructura['primer'] > 12 and estructura['segundo'] <= 12:
            orden_fila = 'DMY'
        elif estructura['segundo'] > 12 and estructura['primer'] <= 12:
            orden_fila = 'MDY'
        formato_fila = construir_formato_fecha(estructura, orden_fila)

    try:
        return datetime.strptime(fecha_txt, formato_fila)
    except Exception:
        return None


def normalizar_fechas_consolidadas(filas, informe=None):
    """
    Interpreta las fechas de un archivo ya consolidado (`niveles.csv`) deduciendo su orden día/mes
    con el mismo criterio que los archivos fuente: observar el cambio de día en la serie horaria.

    Es indispensable porque el consolidado se relee y se reescribe en cada ejecución: si se leyera
    con un orden fijo, un archivo escrito en mes/día se invertiría en cada pasada.

    Devuelve (filas_normalizadas, filas_no_interpretadas); ninguna fila se descarta en silencio.
    """
    textos = [str(fila[1]).strip() for fila in filas
              if len(fila) > 1 and str(fila[1]).strip()]
    if not textos:
        if informe is not None:
            informe['error'] = 'el consolidado no contiene marcas de tiempo'
        return [], [list(fila) for fila in filas]

    # Las filas con fecha ilegible no deben impedir la deducción del orden del resto del archivo.
    textos_reconocibles = [texto for texto in textos if analizar_estructura_fecha(texto) is not None]
    if not textos_reconocibles:
        if informe is not None:
            informe['error'] = 'ninguna fecha del consolidado tiene estructura reconocible'
        return [], [list(fila) for fila in filas]

    try:
        orden, informe_orden = deducir_orden_fecha(textos_reconocibles)
    except Exception as error:
        orden, informe_orden = 'DMY', {
            'orden': 'DMY', 'votos_dia_primero': 0, 'votos_mes_primero': 0, 'ambiguo': True,
            'evidencia': 'no fue posible deducir el orden ({})'.format(error),
            'advertencia': 'No se pudo deducir el orden día/mes del consolidado; se asumió '
                           'día/mes/año. Verifique las fechas del archivo.',
        }

    estructura = None
    for texto in textos_reconocibles:
        estructura = analizar_estructura_fecha(texto)
        if estructura is not None:
            break
    if estructura is None:
        if informe is not None:
            informe['error'] = 'ninguna fecha del consolidado tiene estructura reconocible'
        return [], [list(fila) for fila in filas]

    formato_referencia = construir_formato_fecha(estructura, orden)
    if informe is not None:
        informe.update(informe_orden)
        informe['formato'] = formato_referencia

    normalizadas = []
    no_interpretadas = []
    for fila in filas:
        if len(fila) < 3:
            no_interpretadas.append(list(fila))
            continue
        fecha_dt = interpretar_fecha(fila[1], orden, formato_referencia)
        try:
            valor_num = float(str(fila[2]).replace(',', '.'))
        except Exception:
            valor_num = None
        if fecha_dt is None or valor_num is None:
            no_interpretadas.append(list(fila))
            continue
        fila_norm = list(fila)
        fila_norm[1] = fecha_dt
        fila_norm[2] = valor_num
        normalizadas.append(fila_norm)

    return normalizadas, no_interpretadas


def detectar_inicio_datos(filas, columna_fecha=1, maximo_filas=25):
    """
    Localiza el índice de la primera fila que contiene una fecha reconocible en la columna
    indicada, de modo que las cabeceras y metadatos de cada exportación queden fuera del conjunto
    de datos sin descartar registros válidos (el número de líneas de cabecera es variable).
    """
    for indice, fila in enumerate(filas[:maximo_filas]):
        if len(fila) <= columna_fecha:
            continue
        if analizar_estructura_fecha(str(fila[columna_fecha]).strip()):
            return indice
    return None


def detectar_filas_con_orden_invertido(marcas, factor_cadencia=5.0):
    """
    Detecta filas sueltas cuya fecha rompe la cadencia del archivo y que, leídas con el orden de
    campos alterno, encajarían en ella. Es la firma de un registro exportado con el orden
    invertido (p. ej. una fila mes/día dentro de un archivo día/mes).

    `marcas` es una lista de tuplas `(fecha_interpretada, texto_original, orden_usado)` en el orden
    del archivo. La posición esperada de cada fila se deduce de la cadencia modal, de modo que
    también se revisan la primera y la última fila.

    No modifica los datos: devuelve descripciones legibles para que el analista decida.
    """
    if len(marcas) < 3:
        return []

    intervalos = []
    for indice in range(len(marcas) - 1):
        diferencia = (marcas[indice + 1][0] - marcas[indice][0]).total_seconds()
        if diferencia > 0:
            intervalos.append(diferencia)
    if not intervalos:
        return []

    cadencia = max(set(intervalos), key=intervalos.count)
    if cadencia <= 0:
        return []

    sospechosas = []
    for indice, (marca, texto, orden) in enumerate(marcas):
        if indice == 0:
            esperada = marcas[1][0] - timedelta(seconds=cadencia)
        else:
            esperada = marcas[indice - 1][0] + timedelta(seconds=cadencia)

        desvio_actual = abs((marca - esperada).total_seconds())
        if desvio_actual <= factor_cadencia * cadencia:
            continue

        estructura = analizar_estructura_fecha(texto)
        if estructura is None or estructura.get('orden_fijo'):
            continue
        # Si la evidencia categórica ya fijó el orden, el desvío es un hueco real, no una inversión.
        if estructura['primer'] > 12 or estructura['segundo'] > 12:
            continue

        orden_alterno = 'MDY' if orden == 'DMY' else 'DMY'
        try:
            candidata = datetime.strptime(texto, construir_formato_fecha(estructura, orden_alterno))
        except Exception:
            continue

        if abs((candidata - esperada).total_seconds()) <= cadencia:
            sospechosas.append(
                "{}: leída como {} ({}) se desvía {:.0f} min de la cadencia; con el orden alterno "
                "sería {}, que encaja en la secuencia".format(
                    texto,
                    marca.strftime('%d/%m/%Y %H:%M:%S'), orden,
                    desvio_actual / 60.0,
                    candidata.strftime('%d/%m/%Y %H:%M:%S'))
            )
    return sospechosas


def calcular_paso_optimo(rango, divisiones_deseadas=6):
    """
    Calcula un paso representativo y estético (1, 2, 5 o 10 x 10^k) para graduar un eje.
    """
    if rango <= 0:
        return 1.0
    paso_bruto = rango / divisiones_deseadas
    potencia = 10 ** math.floor(math.log10(paso_bruto))
    fraccion = paso_bruto / potencia
    if fraccion <= 1.5:
        multiplicador = 1.0
    elif fraccion <= 3.0:
        multiplicador = 2.0
    elif fraccion <= 4.5:
        multiplicador = 4.0
    elif fraccion <= 7.5:
        multiplicador = 5.0
    else:
        multiplicador = 10.0
    return potencia * multiplicador


def calcular_ticks_eje_y(y0, y1, divisiones_deseadas=4):
    """
    Calcula los niveles o cotas de las líneas horizontales principales entre y0 e y1.
    """
    rango = y1 - y0
    if rango <= 0:
        return [y0, y0 + 1.0], 1.0
    paso = calcular_paso_optimo(rango, divisiones_deseadas)
    num_div = round(rango / paso)
    if abs(rango - num_div * paso) < 1e-4:
        ticks = [round(y0 + i * paso, 4) for i in range(num_div + 1)]
    else:
        primer_tick = math.ceil(y0 / paso) * paso
        ticks = []
        t = primer_tick
        while t <= y1 + 1e-5:
            ticks.append(round(t, 4))
            t += paso
        if not ticks or ticks[0] > y0:
            ticks.insert(0, round(y0, 4))
        if ticks[-1] < y1:
            ticks.append(round(y1, 4))
    return ticks, paso



class ProcesadorNiveles(QWidget):
    """
    Procesador y consolidador de registros de nivel de embalses (Chanlud, Labrado):
    - Deduce el formato de fecha de cada archivo por evidencia estructural y coherencia temporal.
    - Normaliza fechas al estándar canónico (dd/mm/AAAA HH:MM:SS) y valores numéricos.
    - Resuelve duplicados temporales por coherencia con vecinos.
    - Filtra valores atípicos (outliers) por cota física de variación e interpolación lineal.
    - Permite seccionar temporal y verticalmente la serie y exportar a DXF.
    """

    def __init__(self):
        super().__init__()
        self.directorio_actual = ""
        self.niveles_consolidados = []
        self.inicializar_interfaz()

    def inicializar_interfaz(self):
        layout = QVBoxLayout()

        # --- Grupo 1: Directorio y Consolidación ---
        grupo_consolidacion = QGroupBox("1. Directorio y Consolidación de CSVs")
        layout_cons = QVBoxLayout()

        self.label_directorio = QLabel("<b>Directorio de trabajo:</b> (No seleccionado)")
        self.label_directorio.setWordWrap(True)
        layout_cons.addWidget(self.label_directorio)

        self.label_estado = QLabel("Selecciona el directorio con los archivos CSV de niveles de embalse.")
        self.label_estado.setWordWrap(True)
        layout_cons.addWidget(self.label_estado)

        self.boton_seleccionar = QPushButton("Seleccionar Directorio y Consolidar")
        self.boton_seleccionar.clicked.connect(self.seleccionar_directorio)
        layout_cons.addWidget(self.boton_seleccionar)

        grupo_consolidacion.setLayout(layout_cons)
        layout.addWidget(grupo_consolidacion)

        # --- Grupo 2: Seccionar Niveles y Exportación DXF ---
        grupo_corte = QGroupBox("2. Seccionar Niveles del Embalse / Exportación DXF")
        layout_corte = QGridLayout()

        # Widgets de selección temporal
        layout_corte.addWidget(QLabel("<b>Fecha Inicio Corte:</b>"), 0, 0)
        self.fecha_inicio_corte = QDateTimeEdit()
        self.fecha_inicio_corte.setCalendarPopup(True)
        self.fecha_inicio_corte.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.fecha_inicio_corte.setDateTime(QDateTime.currentDateTime().addDays(-30))
        layout_corte.addWidget(self.fecha_inicio_corte, 0, 1)

        layout_corte.addWidget(QLabel("<b>Fecha Fin Corte:</b>"), 0, 2)
        self.fecha_fin_corte = QDateTimeEdit()
        self.fecha_fin_corte.setCalendarPopup(True)
        self.fecha_fin_corte.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.fecha_fin_corte.setDateTime(QDateTime.currentDateTime())
        layout_corte.addWidget(self.fecha_fin_corte, 0, 3)

        # Widgets de límites verticales del marco
        layout_corte.addWidget(QLabel("<b>Nivel Mín. Marco [m]:</b>"), 1, 0)
        self.nivel_min_corte = QDoubleSpinBox()
        self.nivel_min_corte.setRange(-1000.0, 10000.0)
        self.nivel_min_corte.setDecimals(2)
        self.nivel_min_corte.setSingleStep(0.5)
        self.nivel_min_corte.setValue(0.0)
        layout_corte.addWidget(self.nivel_min_corte, 1, 1)

        layout_corte.addWidget(QLabel("<b>Nivel Máx. Marco [m]:</b>"), 1, 2)
        self.nivel_max_corte = QDoubleSpinBox()
        self.nivel_max_corte.setRange(-1000.0, 10000.0)
        self.nivel_max_corte.setDecimals(2)
        self.nivel_max_corte.setSingleStep(0.5)
        self.nivel_max_corte.setValue(50.0)
        layout_corte.addWidget(self.nivel_max_corte, 1, 3)

        # Botones de acción del corte
        layout_botones_corte = QHBoxLayout()
        self.boton_previsualizar = QPushButton("Previsualizar Gráfico del Corte")
        self.boton_previsualizar.clicked.connect(self.previsualizar_corte)
        layout_botones_corte.addWidget(self.boton_previsualizar)

        self.boton_generar_dxf = QPushButton("Generar Gráfico DXF")
        self.boton_generar_dxf.clicked.connect(self.generar_dxf_corte)
        layout_botones_corte.addWidget(self.boton_generar_dxf)

        layout_corte.addLayout(layout_botones_corte, 2, 0, 1, 4)
        grupo_corte.setLayout(layout_corte)
        layout.addWidget(grupo_corte)

        # Botón Salir
        layout_abajo = QHBoxLayout()
        layout_abajo.addStretch()
        self.boton_salir = QPushButton("Salir")
        self.boton_salir.clicked.connect(self.close)
        layout_abajo.addWidget(self.boton_salir)
        layout.addLayout(layout_abajo)

        self.setLayout(layout)
        self.setWindowTitle("Procesador y Seccionador de Niveles de Embalse - RSA")
        self.resize(620, 320)

    def seleccionar_directorio(self):
        directorio = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio con Archivos CSV")
        if directorio:
            self.directorio_actual = directorio
            self.label_directorio.setText(f"<b>Directorio de trabajo:</b> {directorio}")
            ruta_csv_existente = os.path.join(directorio, "niveles.csv")
            if os.path.isfile(ruta_csv_existente):
                self.cargar_niveles_desde_csv(ruta_csv_existente)
            self.label_estado.setText("Procesando archivos...")
            QApplication.processEvents()
            self.procesar_archivos(directorio)

    def determinar_formato_fecha(self, fechas, informe=None):
        """
        Determina el formato de fecha de un archivo evaluando sus registros.

        A diferencia de la versión anterior —que probaba una lista fija de formatos con día/mes en
        primer lugar y podía aceptar como válido un archivo mes/día ambiguo, invirtiendo día y mes
        en silencio—, aquí se deduce la estructura real de cada marca de tiempo y el orden día/mes
        se resuelve con evidencia (véase `deducir_orden_fecha`).

        Devuelve la cadena de formato `strptime` del archivo y, si se recibe `informe`, lo completa
        con el orden deducido, la evidencia utilizada y la advertencia correspondiente.
        """
        textos = [str(fecha).strip() for fecha in fechas if str(fecha).strip()]
        if not textos:
            raise ValueError("No se recibieron fechas para determinar el formato del archivo.")

        orden, informe_orden = deducir_orden_fecha(textos)

        estructura = None
        for texto in textos:
            estructura = analizar_estructura_fecha(texto)
            if estructura is not None:
                break
        if estructura is None:
            raise ValueError("Formato de fecha no reconocido en la muestra de datos del archivo.")

        formato = construir_formato_fecha(estructura, orden)
        if informe is not None:
            informe.update(informe_orden)
            informe['formato'] = formato
        return formato

    def leer_csv_con_formato_por_archivo(self, ruta_csv, informe=None):
        """
        Lee un archivo CSV individual, determina su formato de fecha propio y retorna las filas
        normalizadas con fecha (datetime) y valor (float).

        El inicio de los datos se localiza por la primera fila con fecha reconocible, no por un
        número fijo de líneas de cabecera, de modo que ningún registro se pierda ni se confunda con
        metadatos. Cada fila se interpreta con la evidencia disponible: si uno de sus campos supera
        12, ese campo es el día; si la fila es ambigua, se aplica el orden deducido para el archivo.
        """
        datos_crudos = lectura_archivo(ruta_csv)
        if not datos_crudos:
            if informe is not None:
                informe['error'] = 'archivo vacío o ilegible'
            return []

        inicio = detectar_inicio_datos(datos_crudos, columna_fecha=1)
        if inicio is None:
            if informe is not None:
                informe['error'] = 'ninguna fila presenta una fecha reconocible en la columna 2'
            return []

        filas_datos = datos_crudos[inicio:]
        textos_fecha = [str(fila[1]).strip() for fila in filas_datos
                        if len(fila) > 1 and str(fila[1]).strip()]
        if not textos_fecha:
            if informe is not None:
                informe['error'] = 'las filas de datos no contienen marcas de tiempo'
            return []

        formato_archivo = self.determinar_formato_fecha(textos_fecha, informe)
        orden_archivo = informe.get('orden', 'DMY') if informe is not None else 'DMY'

        normalizadas = []
        descartadas = []
        marcas_interpretadas = []
        for fila in filas_datos:
            if len(fila) < 3:
                descartadas.append(list(fila))
                continue

            fecha_txt = str(fila[1]).strip()
            valor_txt = str(fila[2]).strip()
            if not fecha_txt:
                descartadas.append(list(fila))
                continue

            fecha_dt = interpretar_fecha(fecha_txt, orden_archivo, formato_archivo)
            valor_num = None
            try:
                valor_num = float(valor_txt.replace(',', '.'))
            except Exception:
                valor_num = None

            if fecha_dt is None or valor_num is None:
                print(f"Advertencia: No se pudo parsear fila en {os.path.basename(ruta_csv)}: {fila}")
                descartadas.append(list(fila))
                continue

            fila_out = list(fila)
            fila_out[1] = fecha_dt
            fila_out[2] = valor_num
            normalizadas.append(fila_out)
            marcas_interpretadas.append((fecha_dt, fecha_txt, orden_archivo))

        filas_sospechosas = detectar_filas_con_orden_invertido(marcas_interpretadas)
        for descripcion in filas_sospechosas:
            print(f"[AVISO] {os.path.basename(ruta_csv)}: posible orden de fecha invertido -> {descripcion}")

        if informe is not None:
            informe['registros'] = len(normalizadas)
            informe['descartadas'] = len(descartadas)
            informe['fila_inicio_datos'] = inicio
            informe['filas_sospechosas'] = filas_sospechosas
            if filas_sospechosas:
                aviso_previo = informe.get('advertencia', '')
                informe['advertencia'] = (
                    (aviso_previo + ' ') if aviso_previo else ''
                ) + "{} fila(s) con posible orden de fecha invertido: {}".format(
                    len(filas_sospechosas), filas_sospechosas[0]
                )

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
        archivo_no_interpretados = os.path.join(directorio, 'niveles_no_interpretados.csv')

        niveles_existentes = lectura_archivo(archivo_niveles) or []
        archivos_existentes = lectura_archivo(archivo_archivos) or []

        def quitar_cabecera_si_corresponde(filas):
            if len(filas) >= 3:
                hay_texto = any(any(c.isalpha() for c in str(celda)) for celda in filas[0])
                return filas[3:] if hay_texto else filas
            return filas

        niveles_existentes = quitar_cabecera_si_corresponde(niveles_existentes)
        archivos_existentes = quitar_cabecera_si_corresponde(archivos_existentes)

        # El consolidado se relee y se reescribe en cada ejecución: su orden día/mes se deduce con
        # el mismo criterio que los archivos fuente (cambio de día observado en la serie horaria).
        informe_consolidado = {}
        niveles_normalizados, filas_no_interpretadas = normalizar_fechas_consolidadas(
            niveles_existentes, informe_consolidado
        )
        if informe_consolidado.get('error'):
            print(f"[AVISO] niveles.csv: {informe_consolidado['error']}")
        else:
            print(f"[CONSOLIDADO] niveles.csv leído como {informe_consolidado.get('formato', '?')} | "
                  f"{informe_consolidado.get('evidencia', '')}")
            print(f"              registros recuperados: {len(niveles_normalizados)} | "
                  f"no interpretados: {len(filas_no_interpretadas)}")

        ya_procesados = set()
        for fila in archivos_existentes:
            if fila and len(fila) >= 1:
                ya_procesados.add(str(fila[0]).strip())

        nuevos_archivos = []
        for nombre in sorted(os.listdir(directorio)):
            if not nombre.lower().endswith('.csv'):
                continue
            if nombre in ('niveles.csv', 'archivos.csv', 'niveles_no_interpretados.csv'):
                continue
            if nombre in ya_procesados:
                continue

            ruta_csv = os.path.join(directorio, nombre)
            print(f"Procesando: {ruta_csv}")
            informe_archivo = {}
            filas_norm = self.leer_csv_con_formato_por_archivo(ruta_csv, informe_archivo)
            if not filas_norm:
                motivo = informe_archivo.get('error', 'sin registros válidos')
                print(f"Saltando (vacio o ilegible): {nombre} | {motivo}")
                continue

            print(f"[FORMATO] {nombre} -> {informe_archivo.get('formato', '?')} | "
                  f"{informe_archivo.get('evidencia', '')}")
            print(f"          registros válidos: {len(filas_norm)} | "
                  f"filas de datos desde la línea {informe_archivo.get('fila_inicio_datos', 0) + 1} | "
                  f"descartadas: {informe_archivo.get('descartadas', 0)}")
            if informe_archivo.get('advertencia'):
                print(f"[AVISO] {nombre}: {informe_archivo['advertencia']}")

            niveles_normalizados.extend(filas_norm)
            nuevos_archivos.append([
                nombre,
                str(informe_archivo.get('formato', '')),
                str(len(filas_norm)),
            ])

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

        if filas_no_interpretadas:
            print(f"[AVISO] {len(filas_no_interpretadas)} fila(s) de niveles.csv no se pudieron "
                  f"interpretar; se conservaron íntegras en niveles_no_interpretados.csv")
            cabecera_no_interpretadas = [
                ["# Filas de niveles.csv que no pudieron interpretarse"],
                ["# Se conservan tal cual, sin depurar, para revisión manual"],
                ["# contenido_original"]
            ]
            escritura_archivo(archivo_no_interpretados, cabecera_no_interpretadas + filas_no_interpretadas)

        todos_archivos = []
        ya = set()
        for fila in archivos_existentes:
            if not fila:
                continue
            n = str(fila[0]).strip()
            if n and n not in ya:
                ya.add(n)
                todos_archivos.append(list(fila))
        for fila in nuevos_archivos:
            n = str(fila[0]).strip()
            if n and n not in ya:
                ya.add(n)
                todos_archivos.append(list(fila))

        cabecera_archivos = [
            ["# Archivos de nivel procesados"],
            ["# Formato: nombre_archivo;formato_fecha_detectado;registros_validos"],
            ["# nombre_archivo;formato_fecha;registros_validos"]
        ]
        escritura_archivo(archivo_archivos, cabecera_archivos + todos_archivos)

        self.label_estado.setText(f"Procesamiento completado con éxito.\nTotal registros consolidados: {len(niveles_depurados)}")
        print(f"Filas consolidadas en niveles.csv: {len(niveles_depurados)}")

        self.niveles_consolidados = [list(f) for f in niveles_depurados]
        self.actualizar_controles_corte()

        self.graficar_niveles(niveles_depurados, "%d/%m/%Y %H:%M:%S")

    def cargar_niveles_desde_csv(self, ruta_csv):
        """
        Carga registros consolidados desde un niveles.csv existente y actualiza controles de corte.
        """
        if not os.path.isfile(ruta_csv):
            return False
        try:
            filas = lectura_archivo(ruta_csv)
            filas_datos = [f for f in filas if f and not str(f[0]).strip().startswith('#') and len(f) >= 3]
            if filas_datos:
                self.niveles_consolidados = filas_datos
                self.actualizar_controles_corte()
                return True
        except Exception as ex:
            print(f"Error cargando {ruta_csv}: {ex}")
        return False

    def actualizar_controles_corte(self):
        """
        Sincroniza los widgets de fecha y nivel con los extremos reales de la serie consolidada.
        """
        if not self.niveles_consolidados:
            return

        fechas_val = []
        niveles_val = []
        for fila in self.niveles_consolidados:
            try:
                if isinstance(fila[1], datetime):
                    dt = fila[1]
                else:
                    dt = datetime.strptime(str(fila[1]).strip(), "%d/%m/%Y %H:%M:%S")
                fechas_val.append(dt)
                niveles_val.append(float(fila[2]))
            except Exception:
                continue

        if not fechas_val:
            return

        min_fecha = min(fechas_val)
        max_fecha = max(fechas_val)
        min_nivel = min(niveles_val)
        max_nivel = max(niveles_val)

        self.fecha_inicio_corte.setDateTime(
            QDateTime(min_fecha.year, min_fecha.month, min_fecha.day, min_fecha.hour, min_fecha.minute, min_fecha.second)
        )
        self.fecha_fin_corte.setDateTime(
            QDateTime(max_fecha.year, max_fecha.month, max_fecha.day, max_fecha.hour, max_fecha.minute, max_fecha.second)
        )

        nivel_min_marco = math.floor(min_nivel)
        nivel_max_marco = math.ceil(max_nivel)
        if nivel_max_marco <= nivel_min_marco:
            nivel_max_marco = nivel_min_marco + 1.0

        self.nivel_min_corte.setValue(float(nivel_min_marco))
        self.nivel_max_corte.setValue(float(nivel_max_marco))

    def obtener_datos_corte(self):
        """
        Valida los controles de corte y devuelve (fecha_ini, fecha_fin, nivel_min, nivel_max, datos_corte).
        """
        if not self.niveles_consolidados and self.directorio_actual:
            ruta_csv = os.path.join(self.directorio_actual, "niveles.csv")
            if os.path.isfile(ruta_csv):
                self.cargar_niveles_desde_csv(ruta_csv)

        if not self.niveles_consolidados:
            QMessageBox.warning(
                self,
                "Sin datos cargados",
                "No hay datos de niveles disponibles. Selecciona primero un directorio con archivos de niveles."
            )
            return None, None, None, None, []

        fecha_ini = self.fecha_inicio_corte.dateTime().toPyDateTime()
        fecha_fin = self.fecha_fin_corte.dateTime().toPyDateTime()
        if fecha_ini >= fecha_fin:
            QMessageBox.warning(
                self,
                "Rango temporal inválido",
                "La Fecha de Inicio debe ser anterior a la Fecha de Fin del corte."
            )
            return None, None, None, None, []

        nivel_min = self.nivel_min_corte.value()
        nivel_max = self.nivel_max_corte.value()
        if nivel_min >= nivel_max:
            QMessageBox.warning(
                self,
                "Rango de niveles inválido",
                "El Nivel Mínimo del marco debe ser menor que el Nivel Máximo."
            )
            return None, None, None, None, []

        datos_corte = []
        for fila in self.niveles_consolidados:
            try:
                if isinstance(fila[1], datetime):
                    dt = fila[1]
                else:
                    dt = datetime.strptime(str(fila[1]).strip(), "%d/%m/%Y %H:%M:%S")
                val = float(fila[2])
                if fecha_ini <= dt <= fecha_fin:
                    datos_corte.append((dt, val))
            except Exception:
                continue

        if not datos_corte:
            QMessageBox.warning(
                self,
                "Sin registros en el corte",
                f"No existen registros entre {fecha_ini.strftime('%d/%m/%Y %H:%M')} y {fecha_fin.strftime('%d/%m/%Y %H:%M')}."
            )
            return None, None, None, None, []

        datos_corte.sort(key=lambda x: x[0])
        return fecha_ini, fecha_fin, nivel_min, nivel_max, datos_corte

    def previsualizar_corte(self):
        """
        Muestra la previsualización gráfica del corte con el formato exacto solicitado:
        - Curva de nivel en color rojo.
        - Divisiones verticales discontinuas para cada día del mes.
        - Divisiones continuas y franja inferior para cada mes correspondiente.
        - Líneas horizontales en las cotas principales y etiqueta vertical 'NIVEL DEL EMBALSE (m)'.
        """
        fecha_ini, fecha_fin, nivel_min, nivel_max, datos_corte = self.obtener_datos_corte()
        if not datos_corte:
            return

        fechas = [d[0] for d in datos_corte]
        valores = [d[1] for d in datos_corte]

        NOMBRES_MESES = [
            "", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
            "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
        ]

        ticks_y, paso_y = calcular_ticks_eje_y(nivel_min, nivel_max, 4)

        fig, (ax_grafico, ax_meses) = plt.subplots(
            2, 1, figsize=(12, 5.0),
            gridspec_kw={'height_ratios': [8.5, 1.2], 'hspace': 0.0}
        )

        # 1. Curva de niveles en rojo
        ax_grafico.plot(fechas, valores, color='red', lw=1.5, label='Nivel del embalse')

        # Eje Y: líneas horizontales y rótulo
        ax_grafico.set_ylabel('NIVEL DEL EMBALSE (m)', fontweight='bold', fontsize=11)
        ax_grafico.set_ylim(nivel_min, nivel_max)
        ax_grafico.set_yticks(ticks_y)
        ax_grafico.set_yticklabels([f"{int(t)}" if paso_y >= 1 and abs(t - round(t)) < 1e-4 else f"{t:.1f}" for t in ticks_y], fontsize=10)
        ax_grafico.grid(True, which='major', axis='y', color='black', linestyle='-', linewidth=0.8)

        # Eje X en gráfico superior
        ax_grafico.set_xlim(fecha_ini, fecha_fin)
        ax_grafico.tick_params(axis='x', which='both', bottom=False, labelbottom=False)

        # 2. Divisiones verticales: días (discontinuas) y meses (continuas)
        cur_dia = datetime(fecha_ini.year, fecha_ini.month, fecha_ini.day)
        while cur_dia <= fecha_fin:
            if cur_dia >= fecha_ini:
                if cur_dia.day == 1:
                    ax_grafico.axvline(cur_dia, color='black', linestyle='-', linewidth=1.2)
                    ax_meses.axvline(cur_dia, color='black', linestyle='-', linewidth=1.2)
                else:
                    ax_grafico.axvline(cur_dia, color='#888888', linestyle='--', linewidth=0.6, alpha=0.7)
            cur_dia += timedelta(days=1)

        # 3. Franja inferior de meses correspondientes
        cursor_mes = datetime(fecha_ini.year, fecha_ini.month, 1)
        while cursor_mes <= fecha_fin:
            ini_seg = max(fecha_ini, cursor_mes)
            if cursor_mes.month == 12:
                siguiente_mes = datetime(cursor_mes.year + 1, 1, 1)
            else:
                siguiente_mes = datetime(cursor_mes.year, cursor_mes.month + 1, 1)
            fin_seg = min(fecha_fin, siguiente_mes)

            if fin_seg > ini_seg:
                nom_mes = NOMBRES_MESES[cursor_mes.month]
                dt_centro = ini_seg + (fin_seg - ini_seg) / 2
                ax_meses.axvspan(ini_seg, fin_seg, facecolor='#666666', edgecolor='black', linewidth=1.0)
                ax_meses.text(dt_centro, 0.5, nom_mes, color='white', fontweight='bold', fontsize=10, ha='center', va='center')
            cursor_mes = siguiente_mes

        ax_meses.set_xlim(fecha_ini, fecha_fin)
        ax_meses.set_ylim(0, 1)
        ax_meses.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

        fig.suptitle(
            f'Niveles del Embalse — Período: {fecha_ini.strftime("%d/%m/%Y")} al {fecha_fin.strftime("%d/%m/%Y")}',
            fontsize=12, fontweight='bold', y=0.98
        )
        fig.tight_layout()
        plt.show()

    def generar_dxf_corte(self):
        """
        Exporta el corte de niveles y su marco gráfico a formato CAD DXF estándar.
        """
        fecha_ini, fecha_fin, nivel_min, nivel_max, datos_corte = self.obtener_datos_corte()
        if not datos_corte:
            return

        nombre_sugerido = f"corte_niveles_{fecha_ini.strftime('%Y%m%d')}_a_{fecha_fin.strftime('%Y%m%d')}.dxf"
        ruta_sugerida = os.path.join(self.directorio_actual or "", nombre_sugerido)

        ruta_dxf, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Gráfico DXF",
            ruta_sugerida,
            "Archivos DXF (*.dxf)"
        )
        if not ruta_dxf:
            return

        try:
            self.escribir_archivo_dxf(ruta_dxf, fecha_ini, fecha_fin, nivel_min, nivel_max, datos_corte)
            QMessageBox.information(
                self,
                "DXF Generado Exitosamente",
                f"El archivo DXF se guardó correctamente en:\n{ruta_dxf}\n\n"
                f"Total de registros exportados: {len(datos_corte)}\n"
                f"Marco vertical: {nivel_min:.2f} m a {nivel_max:.2f} m\n"
                f"Período: {fecha_ini.strftime('%d/%m/%Y %H:%M')} a {fecha_fin.strftime('%d/%m/%Y %H:%M')}"
            )
        except Exception as ex:
            QMessageBox.critical(
                self,
                "Error al Generar DXF",
                f"No se pudo escribir el archivo DXF:\n{ex}"
            )

    def escribir_archivo_dxf(self, ruta_dxf, fecha_inicio, fecha_final, y_min, y_max, datos_corte):
        """
        Escribe un archivo DXF estándar con la maquetación exacta requerida:
        - Marco rectangular superior con cuadrícula horizontal en cotas principales.
        - Malla vertical discontinua (DASHED) para cada día del mes.
        - Líneas continuas verticales y compartimentos para los meses correspondientes.
        - Franja inferior con relleno gris oscuro y nombres de mes centrados en blanco.
        - Eje vertical rotado a 90° con la etiqueta 'NIVEL DEL EMBALSE (m)'.
        - Curva de nivel continua en capa NIVELES (color rojo).
        """
        NOMBRES_MESES = [
            "", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
            "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
        ]

        duracion_segundos = max((fecha_final - fecha_inicio).total_seconds(), 3600.0)
        x0 = 0.0
        x1 = duracion_segundos / 86400.0
        y0 = float(y_min)
        y1 = float(y_max)

        rango_x = x1 - x0
        rango_y = max(y1 - y0, 0.1)

        # Proporciones estéticas
        alto_barra_meses = max(rango_y * 0.075, 0.6)
        y_barra_fondo = y0 - alto_barra_meses

        margen_x = max(rango_x * 0.05, 0.5)
        margen_y = max(rango_y * 0.08, 0.5)

        contenido = []

        def agregar(codigo, valor):
            contenido.append(str(codigo))
            contenido.append(str(valor))

        def agregar_linea(xa, ya, xb, yb, capa="MARCO", color=7, ltype=None):
            agregar(0, "LINE")
            agregar(8, capa)
            agregar(62, color)
            if ltype:
                agregar(6, ltype)
            agregar(10, f"{xa:.4f}")
            agregar(20, f"{ya:.4f}")
            agregar(30, "0.0")
            agregar(11, f"{xb:.4f}")
            agregar(21, f"{yb:.4f}")
            agregar(31, "0.0")

        def agregar_texto(x, y, texto, alto=0.25, rotacion=0.0, alineacion_h=0, alineacion_v=0, capa="TEXTOS", color=7):
            agregar(0, "TEXT")
            agregar(8, capa)
            agregar(62, color)
            agregar(10, f"{x:.4f}")
            agregar(20, f"{y:.4f}")
            agregar(30, "0.0")
            agregar(40, f"{alto:.4f}")
            agregar(1, str(texto))
            if rotacion != 0.0:
                agregar(50, f"{rotacion:.1f}")
            agregar(7, "STANDARD")
            if alineacion_h != 0 or alineacion_v != 0:
                agregar(72, alineacion_h)
                agregar(11, f"{x:.4f}")
                agregar(21, f"{y:.4f}")
                agregar(31, "0.0")
                agregar(73, alineacion_v)

        # 1. Encabezado DXF (AutoCAD R12 / AC1009 universal para Vectorworks y AutoCAD)
        agregar(0, "SECTION")
        agregar(2, "HEADER")
        agregar(9, "$ACADVER")
        agregar(1, "AC1009")
        agregar(9, "$LTSCALE")
        agregar(40, "1.0")
        agregar(0, "ENDSEC")

        # 2. Tablas
        agregar(0, "SECTION")
        agregar(2, "TABLES")

        agregar(0, "TABLE")
        agregar(2, "LTYPE")
        agregar(70, 2)
        agregar(0, "LTYPE")
        agregar(2, "CONTINUOUS")
        agregar(70, 0)
        agregar(3, "Solid line")
        agregar(72, 65)
        agregar(73, 0)
        agregar(40, "0.0")
        agregar(0, "LTYPE")
        agregar(2, "DASHED")
        agregar(70, 0)
        agregar(3, "Dashed __ __ __")
        agregar(72, 65)
        agregar(73, 2)
        agregar(40, "1.0")
        agregar(49, "0.6")
        agregar(49, "-0.4")
        agregar(0, "ENDTAB")

        capas = [
            ("0", 7),
            ("MARCO", 7),
            ("MALLA_HORIZONTAL", 8),
            ("MALLA_MESES", 7),
            ("MALLA_DIAS", 8),
            ("FONDO_MESES", 8),
            ("NIVELES", 1),
            ("TEXTOS", 7),
            ("TEXTOS_MESES", 7)
        ]
        agregar(0, "TABLE")
        agregar(2, "LAYER")
        agregar(70, len(capas))
        for nom, col in capas:
            agregar(0, "LAYER")
            agregar(2, nom)
            agregar(70, 0)
            agregar(62, col)
            if nom == "MALLA_DIAS":
                agregar(6, "DASHED")
            else:
                agregar(6, "CONTINUOUS")
        agregar(0, "ENDTAB")

        agregar(0, "TABLE")
        agregar(2, "STYLE")
        agregar(70, 1)
        agregar(0, "STYLE")
        agregar(2, "STANDARD")
        agregar(70, 0)
        agregar(40, "0.0")
        agregar(41, "1.0")
        agregar(50, "0.0")
        agregar(71, 0)
        agregar(42, "0.2")
        agregar(3, "ARIAL")
        agregar(0, "ENDTAB")

        agregar(0, "ENDSEC")

        # 3. Bloques (requerido por ODA Vectorworks)
        agregar(0, "SECTION")
        agregar(2, "BLOCKS")
        agregar(0, "ENDSEC")

        # 4. Entidades gráficas
        agregar(0, "SECTION")
        agregar(2, "ENTITIES")

        # 1. Marco rectangular del gráfico y barra de meses
        agregar_linea(x0, y0, x1, y0, "MARCO", 7)
        agregar_linea(x1, y0, x1, y1, "MARCO", 7)
        agregar_linea(x1, y1, x0, y1, "MARCO", 7)
        agregar_linea(x0, y1, x0, y0, "MARCO", 7)

        agregar_linea(x0, y_barra_fondo, x1, y_barra_fondo, "MARCO", 7)
        agregar_linea(x0, y_barra_fondo, x0, y0, "MARCO", 7)
        agregar_linea(x1, y_barra_fondo, x1, y0, "MARCO", 7)

        # 2. Ticks horizontales y cotas (Eje Y)
        ticks_y, paso_y = calcular_ticks_eje_y(y0, y1, 4)
        alto_texto_y = max(rango_y * 0.025, 0.18)
        for t_y in ticks_y:
            agregar_linea(x0, t_y, x1, t_y, "MALLA_HORIZONTAL", 8)
            agregar_linea(x0 - margen_x * 0.015, t_y, x0, t_y, "MARCO", 7)
            etiqueta_y = f"{int(round(t_y))}" if paso_y >= 1 and abs(t_y - round(t_y)) < 1e-4 else f"{t_y:.1f}"
            agregar_texto(x0 - margen_x * 0.025, t_y, etiqueta_y, alto=alto_texto_y, alineacion_h=2, alineacion_v=2, capa="TEXTOS", color=7)

        # Rótulo vertical del eje Y
        alto_rotulo_y = max(rango_y * 0.032, 0.25)
        agregar_texto(
            x0 - margen_x * 0.08,
            (y0 + y1) / 2.0,
            "NIVEL DEL EMBALSE (m)",
            alto=alto_rotulo_y,
            alineacion_h=1,
            alineacion_v=2,
            rotacion=90.0,
            capa="TEXTOS",
            color=7
        )

        # 3. Malla vertical de días y meses
        cur_dia = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
        while cur_dia <= fecha_final:
            pos_x = (cur_dia - fecha_inicio).total_seconds() / 86400.0
            if x0 < pos_x < x1:
                if cur_dia.day == 1:
                    agregar_linea(pos_x, y_barra_fondo, pos_x, y1, "MALLA_MESES", 7)
                else:
                    agregar_linea(pos_x, y0, pos_x, y1, "MALLA_DIAS", 8, ltype="DASHED")
            cur_dia += timedelta(days=1)

        # 4. Compartimentos y nombres de mes en la barra inferior
        cursor_mes = datetime(fecha_inicio.year, fecha_inicio.month, 1)
        alto_texto_mes = alto_barra_meses * 0.40
        while cursor_mes <= fecha_final:
            ini_seg = max(fecha_inicio, cursor_mes)
            if cursor_mes.month == 12:
                siguiente_mes = datetime(cursor_mes.year + 1, 1, 1)
            else:
                siguiente_mes = datetime(cursor_mes.year, cursor_mes.month + 1, 1)
            fin_seg = min(fecha_final, siguiente_mes)

            if fin_seg > ini_seg:
                xa = (ini_seg - fecha_inicio).total_seconds() / 86400.0
                xb = (fin_seg - fecha_inicio).total_seconds() / 86400.0

                # Fondo gris oscuro del mes
                agregar(0, "SOLID")
                agregar(8, "FONDO_MESES")
                agregar(62, 8)
                agregar(10, f"{xa:.4f}")
                agregar(20, f"{y_barra_fondo:.4f}")
                agregar(30, "0.0")
                agregar(11, f"{xb:.4f}")
                agregar(21, f"{y_barra_fondo:.4f}")
                agregar(31, "0.0")
                agregar(12, f"{xa:.4f}")
                agregar(22, f"{y0:.4f}")
                agregar(32, "0.0")
                agregar(13, f"{xb:.4f}")
                agregar(23, f"{y0:.4f}")
                agregar(33, "0.0")

                # Nombre del mes centrado en mayúsculas
                nom_mes = NOMBRES_MESES[cursor_mes.month]
                x_centro = (xa + xb) / 2.0
                y_centro = (y_barra_fondo + y0) / 2.0
                agregar_texto(x_centro, y_centro, nom_mes, alto=alto_texto_mes, alineacion_h=1, alineacion_v=2, capa="TEXTOS_MESES", color=7)

            cursor_mes = siguiente_mes

        # 5. Polilínea continua universal R12 de niveles en color rojo
        puntos_nivel = []
        for dt, nivel in datos_corte:
            t_dias = (dt - fecha_inicio).total_seconds() / 86400.0
            puntos_nivel.append((t_dias, float(nivel)))

        if puntos_nivel:
            agregar(0, "POLYLINE")
            agregar(8, "NIVELES")
            agregar(62, 1)  # Color 1 = Rojo
            agregar(66, 1)
            agregar(10, "0.0")
            agregar(20, "0.0")
            agregar(30, "0.0")
            agregar(70, 0)
            for px, py in puntos_nivel:
                agregar(0, "VERTEX")
                agregar(8, "NIVELES")
                agregar(10, f"{px:.4f}")
                agregar(20, f"{py:.4f}")
                agregar(30, "0.0")
            agregar(0, "SEQEND")
            agregar(8, "NIVELES")

        agregar(0, "ENDSEC")
        agregar(0, "EOF")

        with open(ruta_dxf, "w", encoding="ascii", errors="replace") as archivo:
            archivo.write("\n".join(contenido) + "\n")

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
