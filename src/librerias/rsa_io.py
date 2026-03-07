import sys
import os
from pathlib import Path
def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    else:
        return ''
ruta_librerias=os.path.dirname(__file__)
ruta_proyecto=extraer_hasta_directorio(ruta_librerias, 'rsa_sismologia')
ruta_librerias = os.path.abspath(os.path.join(ruta_proyecto, 'src','librerias'))
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto,'datos'))
# Insertar la ruta al inicio del sys.path
if ruta_librerias not in sys.path:
    sys.path.insert(0, ruta_librerias)

import re
import csv
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QDate
import matplotlib
matplotlib.use('Qt5Agg')  # Asegúrate de que esto está antes de importar matplotlib.pyplot
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator    
import subprocess
from obspy import UTCDateTime, read, Trace, Stream
from datetime import datetime, timedelta
import sys
import os
import xml.etree.ElementTree as ET
import struct

import numpy as np
import scipy.signal as signal
from datetime import date
import calendar
import shutil
from metodos_gestion import obtencion_hora,parametros_estaciones,obtener_directorios,VentanaProgreso
import pandas as pd
from rsa_dominio import obtenerTraza

def leer_mseed(archivo, tipo, t_inicio=None, t_final=None):
    directorios = obtener_directorios(archivo)
    parametros = parametros_estaciones()
    nombre_canal = parametros['CODIGO']
    num_estaciones = len(nombre_canal)
    fecha_ = obtencion_hora(archivo)
    trCanal = [[] for _ in range(num_estaciones)]

    # Convertimos t_inicio y t_final a UTCDateTime
    if t_inicio is not None and t_final is not None:
        t_inicio_utc = fecha_ + t_inicio
        t_final_utc = fecha_ + t_final
    else:
        t_inicio_utc = None
        t_final_utc = None

    for i in range(num_estaciones):
        if tipo != 0:
            nombreMseed = f"{directorios['Directorio_eventos']}/{nombre_canal[i]}{fecha_.strftime('_%Y%m%d_%H%M%S.mseed')}"
        else:
            nombreMseed = f"{directorios['Directorio_registros']}/{nombre_canal[i]}{fecha_.strftime('_%Y%m%d_%H%M%S.mseed')}"

        try:
            with open(nombreMseed, 'rb'):
                # ✅ Lectura parcial
                if t_inicio_utc and t_final_utc:
                    stLeido = read(nombreMseed, starttime=t_inicio_utc, endtime=t_final_utc)
                else:
                    stLeido = read(nombreMseed)
                trCanal[i] = stLeido

        except FileNotFoundError:
            pass
 
    return trCanal

def conversion_mseed(canal_np, hab_canal, nombre_canal, fecha_, directorio):
    """
    Convierte canales habilitados a MiniSEED acumulando por día.
    - SR fijo = 64 sps.
    - Si ya existe el MSEED del día para el canal, se lee y se acumula al final (sin solapar):
      starttime_nuevo = fin_prev + 1/64.
    - Si no existe, el bloque inicia en 'fecha_' y el archivo se nombra con 00:00:00 del día.
    - Se asume que 'canal_np[i]' contiene SOLO muestras nuevas (no repetidas).
    """
    # Asegurar tipo entero de 32 bits para STEIM1 (evita copias innecesarias)
    if canal_np.dtype != np.int32:
        canal_np = canal_np.astype(np.int32, copy=False)

    # Componentes de tiempo para este bloque
    anio, mes, dia = fecha_.year, fecha_.month, fecha_.day
    horas, minutos, segundos = fecha_.hour, fecha_.minute, fecha_.second

    # Nombre de archivo DIARIO: desde medianoche del mismo día
    fecha_dia_cero = fecha_.replace(hour=0, minute=0, second=0, microsecond=0)
    hora_string_dia = fecha_dia_cero.strftime('%Y%m%d_%H%M%S')  # yymmdd_000000

    # SR por defecto (sps)
    sr_defecto = 64.0
    dt = 1.0 / sr_defecto

    trCanal = [[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []]

    for i in range(16):
        if hab_canal[i] != "0":
            # Ruta del archivo diario del canal
            base_dia = os.path.join(directorio, f"{nombre_canal[i]}_{hora_string_dia}")
            nombre_mseed = base_dia + ".mseed"

            # 1) Construir traza nueva con hora de referencia (se ajustará si ya existe archivo)
            traza = obtenerTraza(
                nombre_canal[i],
                1,
                canal_np[i],
                anio, mes, dia, horas, minutos, segundos,
                0  # subsegundos/offset si aplica
            )

            # Asegurar SR = 64 sps y starttime explícito
            traza.stats.sampling_rate = sr_defecto
            try:
                traza.stats.starttime = UTCDateTime(anio, mes, dia, horas, minutos, segundos)
            except Exception:
                # Si por algún motivo falla, dejamos lo que ponga obtenerTraza
                pass

            st_nuevo = Stream(traces=[traza])

            # 2) Si ya existe el archivo del día, leer y acumular al final sin solapes
            if os.path.exists(nombre_mseed):
                try:
                    st_prev = read(nombre_mseed)
                    # Unificar el previo (por si tiene varias trazas) antes de calcular fin_prev
                    st_prev.merge(method=0, fill_value='latest')
                    # Fin real del previo (máximo endtime entre trazas)
                    fin_prev = max(tr.stats.endtime for tr in st_prev)
                    # Ajustar inicio del nuevo bloque a continuación exacta
                    traza.stats.starttime = fin_prev + dt
                    # Acumular y volver a unificar
                    st_prev += st_nuevo
                    st_prev.merge(method=0, fill_value='latest')
                    # Escribir de vuelta el archivo del día
                    st_prev.write(nombre_mseed, format='MSEED', encoding='STEIM1', reclen=512)
                    trCanal[i] = st_prev
                except Exception:
                    # Si algo sale mal al leer/mergear, como fallback escribe solo el nuevo
                    st_nuevo.write(nombre_mseed, format='MSEED', encoding='STEIM1', reclen=512)
                    trCanal[i] = st_nuevo
            else:
                # 3) No existe archivo del día: escribir solo el bloque nuevo (comienza en fecha_)
                st_nuevo.write(nombre_mseed, format='MSEED', encoding='STEIM1', reclen=512)
                trCanal[i] = st_nuevo
        else:
            trCanal[i] = []

    return trCanal


#############################################################################################
#  Método que lee linea por línea el contenido de los archivos diarios generados, tanto los archivo del catalog como los de reportes y los resumenes
def lectura_resumen(archivo):#Depurado
    eventos=[]
    contador=0
    with open(archivo,newline='') as f:
        datos=csv.reader(f,delimiter=';',quotechar=';')
        for r in datos:
            if(contador==0):
                contador=contador+1
            else:
                eventos.append(r)
    return(eventos)



def lectura_archivo(archivo):
    """
    Lee un archivo de texto donde cada línea contiene valores separados por punto y coma.
    Intenta detectar automáticamente la codificación entre varias comunes (UTF-8, Latin-1, cp1252).
    Devuelve una lista de listas con los datos.
    Args:
        archivo (str): Ruta del archivo a leer.
    Returns:
        list: Lista de listas con los datos del archivo o None si ocurre un error.
    """
    import codecs
    codificaciones_posibles = ['utf-8', 'latin-1', 'cp1252']
    valores = []
    for codificacion in codificaciones_posibles:
        try:
            with codecs.open(archivo, 'r', encoding=codificacion, errors='strict') as file:
                for linea in file:
                    elementos = linea.strip().split(';')
                    if elementos != ['']:
                        valores.append(elementos)
            return valores  # Si se logra leer correctamente, retornamos aquí
        except UnicodeDecodeError:
            continue  # Intenta con la siguiente codificación
        except FileNotFoundError:
            print(f"El archivo {archivo} no fue encontrado.")
            return []
        except Exception as e:
            print(f"Ocurrió un error al leer el archivo con codificación {codificacion}: {e}")
            return None
    print("No se pudo leer el archivo con ninguna de las codificaciones conocidas.")
    return []

def escritura_archivo(archivo, valores):
    try:
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        with open(archivo, 'w', encoding='utf-8') as file:
            for sublist in valores:
                if sublist != []:
                    lista_como_cadenas = [str(elemento) for elemento in sublist]
                    linea = ';'.join(lista_como_cadenas)
                    file.write(linea + '\n')

    except Exception as e:
        mensaje = f"No se pudo escribir en el archivo:\n{archivo}\n\nEs posible que esté abierto en otro programa como Excel.\n\nDetalles: {str(e)}"
        print(mensaje)




def copiar_archivos(archivos_origen, archivos_destino):
    lista=(17,17,12,11,10,10,10)
    for i in range(0,7):
        try:
            archivo_dest=archivos_destino[i][:-lista[i]]+archivos_origen[i][-lista[i]:]
            shutil.copyfile(archivos_origen[i],archivo_dest)
        except FileNotFoundError:
            pass





def num_reportes(directorio):
    contador_12=0
    contador_18=0
    contador_24=0
    archivos_auxiliar = os.listdir(directorio)
    archivos=sorted(archivos_auxiliar)
    tamanio=len(archivos)
    for j in range(0,tamanio):
        if archivos[j][-4:-1]==".pd":
            hora=int(archivos[j][-14:-8])
            if hora<120000:
                contador_12=contador_12+1
            else:
                if hora<180000:
                    contador_18=contador_18+1
                else:
                    contador_24=contador_24+1
    return (contador_12,contador_18,contador_24)



