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
ruta_datos = os.path.abspath(os.path.join(ruta_proyecto, 'datos'))
from obspy import UTCDateTime
import csv
import json
import re
import obspy
import subprocess
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QMessageBox
from PyQt5.QtCore import Qt, QCoreApplication, QEventLoop


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



def lectura_eventos(archivo):
#########################################################################################    
# Método lectura_eventos(archivo)
# Depurado; archivo es un parámetro para poder ubicar los directorios de almacenamiento.
# Tipicamente está en la dirección G:\Mi unidad\DIA en la computadora de procesamiento 
# y tiene la forma AAMMDDhhmmss sin extensión.
# la fuente es el archivo puntos.csv generado en el surfer
# la respuesta es una tupla de dos elementos, un mensaje y la lista con las horas 
# aproximadas de los eventos
#########################################################################################

    hora_sismo=[]
    contador=0
    directorios=obtener_directorios(archivo)
    archivo_marcas=directorios['archivo_marcas']
    if os.path.exists(archivo_marcas):
        with open(archivo_marcas, 'r') as f:
            marcas = [obspy.UTCDateTime(marca) for marca in json.load(f)]
            for hora in marcas:
                hora_sismo.append((hora.hour*3600+hora.minute*60+hora.second)*64)
        hora_sismo.sort()
        text="Lectura completada"
    else:
        archivo_puntos=directorios['Directorio_base']+"/puntos.csv"
        if  os.path.exists(archivo_puntos):
            with open(archivo_puntos,newline='') as f:
                datos=csv.reader(f,delimiter=',',quotechar=';')
                for r in datos:
                    contador=contador+1
                    if contador==2:
                        x0=float(r[0])
                        y0=float(r[1])
                    if contador==3:
                        x1=float(r[0])
                        y1=float(r[1])
                    if contador > 3:
                        xn=float(r[0])
                        yn=float(r[1])
                        an=round(239*(yn-y0)/(y1-y0)+0.4)
                        cn=6*(xn-x0)/(x1-x0)
                        bn=an*6+cn
                        tiempo=bn/1440
                        tiempo=int(tiempo*86400*64-20)
                        hora_sismo.append(tiempo)
            hora_sismo.sort()
            for i in range(0,len(hora_sismo)):
                hora_sismo[i]=int(hora_sismo[i]/64)*64
            text="Lectura completada"
        else:
            text="Listado de eventos no encontrado\n\nVerificar Archivos\n\noescoger otro día"
            hora_sismo=0
    return(text,hora_sismo)

def parametros_estaciones():
#################################################################
#Método de Extracción de datos de conficuración de las estaciones
#Desde el archivo estaciones.csv que debe estar presente en el mismo directorio del ejecutable.
    ruta_csv =  os.path.join(ruta_datos, "estaciones.csv")
    ruta_csv = os.path.abspath(ruta_csv)
    estaciones=lectura_archivo(ruta_csv)
    nombre_canal_total_=[] #Variable que guarda el nombre completo de las estaciones       
    nombre_canal=[]        #Variable que guarda el nombre codigo del canal de las estaciones
    tipo_sensor=[]         #Variable que guarda el tipo de sensor de la estacion (Velocidad o aceleracion)
    n_canales_=[]          #Variable que guarda el número de canales de las estaciones
    hab_canal=[]           #Variable que guarda si se habilita o no la decodificación de la estación
    componente_canal=[]    #Variable que guarda la componente de la estacion usada en el proceso V2
    grafico_=[]            #Variable que guarda la si se grafica o no la señal ára extracción
    hab_plt=[]             #Variable que guarda si se habilita o no la impresión plt de la estación
    gan_plt=[]             #Variable que guarda si se habilita o no la impresión plt de la estación
    ganancia=[]
    diez_plt=[]
    factor_mult=[]             #Variable que guarda si se habilita o no la impresión plt de la estación
    calidad_=[]
    ubicacion_=[]
    tipo_canal=[]
    red_=[]
    muestreo_=[]
    longitud_=[]
    latitud_=[]
    altura_=[]
    ruido_=[]
    numero_est=[]
    filtro_=[]
    polaridad_=[]
    reserva_1=[]
    for i,estacion in enumerate(estaciones):
        if i==0:
            continue
        nombre_canal_total_.append(estacion[1])
        nombre_canal.append(estacion[2])
        tipo_sensor.append(estacion[3])
        n_canales_.append(estacion[4])
        hab_canal.append(estacion[5])
        componente_canal.append(estacion[6])
        grafico_.append(estacion[7])
        hab_plt.append(estacion[8])
        gan_plt.append(estacion[9])
        ganancia.append(estacion[10])
        diez_plt.append(estacion[11])
        factor_mult.append(estacion[12])
        calidad_.append(estacion[13])
        ubicacion_.append(estacion[14])
        tipo_canal.append(estacion[15])
        red_.append(estacion[16])
        muestreo_.append(estacion[17])
        longitud_.append(estacion[18])
        latitud_.append(estacion[19])
        altura_.append(estacion[20])
        ruido_.append((estacion[21]))
        numero_est.append((estacion[0]))
        filtro_.append(estacion[22])
        polaridad_.append(estacion[23])
        reserva_1.append(estacion[24])              
    return{'NOMBRE':nombre_canal_total_,    #Canal 0  'NOMBRE' Nombre con detalle
           'CODIGO':nombre_canal,           #Canal 1  'CODIGO' Nombre abrebiado 2n 4 letras mayusculas
           'SENSOR':tipo_sensor,            #Canal 2  'SENSOR' Tipo se sensor, sismico o acelerografio
           'CANALES':n_canales_,            #Canal 3  'CANALES' Numero de canales de la estacion, 1 , 3 , 6 o mas
           'HAB_CANAL':hab_canal,           #Canal 4  'HAB_CANAL'  Estacion habilitadaa
           'COMPONENTE':componente_canal,   #Canal 5  'COMPONENTE' Numero de componente a procesar
           'HAB_GRAFICO':grafico_,          #Canal 6  'HAB_GRAFICO'
           'BITS':hab_plt,                  #Canal 7  'BITS'  Numero de bits de cuantificacion
           'CALIBRACION':gan_plt,           #Canal 8  'CALIBRACION' Fa
           'GANANCIA':ganancia,             #Canal 9  'GANANCIA'
           'DIEZMADO_PLT':diez_plt,         #Canal 10 'DIEZ_PLT'
           'FACTOR_MUL':factor_mult,        #Canal 11 'FACTOR_MUL'
           'LONGITUD':longitud_,            #Canal 12 'LONGITUD'
           'LATITUD':latitud_,              #Canal 13 'LATITUD'
           'ALTITUD':altura_,               #Canal 14 'ALTITUD'
           'RUIDO':ruido_,                  #Canal 15 'RUIDO'
           'CALIDAD':calidad_,              #Canal 16 'CALIDAD'
           'UBICACION':ubicacion_,          #Canal 17 'UBICACIÓN'
           'CANAL':tipo_canal,              #Canal 18 'CANAL'
           'RED':red_,                      #Canal 19 'RED'
           'MUESTREO': muestreo_,           #Canal 20 'MUESTREO'
           'NUM_ESTACION':numero_est,       #Canal 21 'N° ESTACION'
           'FILTRO':filtro_,                #Canal 22 'FILTRO' 
           'POLARIDAD':polaridad_,          #Canal 23 'Polaridad'            
           'RESERVA':reserva_1}             #Canal 24 'Reserva 1'
                
                
    return(nombre_canal_total_, #Canal 0  'NOMBRE'
           nombre_canal,        #Canal 1  'CODIGO'
           tipo_sensor,         #Canal 2  'SENSOR'
           n_canales_,          #Canal 3  'CANALES'
           hab_canal,           #Canal 4  'HAB_CANAL'
           componente_canal,    #Canal 5  'COMPONENTE'
           grafico_,            #Canal 6  'HAB_GRAFICO'
           hab_plt,             #Canal 7  'HAB_PLT'
           gan_plt,             #Canal 8  'GAN_PLT'
           ganancia,            #Canal 9  'GANANCIA'
           diez_plt,            #Canal 10 'DIEZ_PLT'
           factor_mult,         #Canal 11 'FACTOR_MUL'
           longitud_,           #Canal 12 'LONGITUD'
           latitud_,            #Canal 13 'LATITUD'
           altura_,             #Canal 14 'ALTITUD'
           ruido_,              #Canal 15 'RUIDO'
           calidad_,            #Canal 16 'CALIDAD'
           ubicacion_,          #Canal 17 'UBICACIÓN'
           tipo_canal,          #Canal 18 'CANAL'
           red_,                #Canal 19 'RED'
           muestreo_,           #Canal 20 'MUESTREO'
           numero_est,          #Canal 21 'N° ESTACION'
           filtro_,             #Canal 22 'FILTRO' 
           polaridad_,          #Canal 23 'Polaridad'            
           reserva_1)           #Canal 24 'Reserva 2'



def obtener_directorios(ruta_archivo: str) -> dict:
    """
    Construye la estructura de carpetas y nombres de archivo estándar para un
    evento sísmico a partir de cualquier ruta que contenga una marca de tiempo
    o que pertenezca a un directorio de trabajo sísmico.

    Soporta dinámicamente múltiples estructuras de carpetas bajo DIA:
    - DIA/AAAA/AAAA_MM/AAAA_MM_DD
    - DIA/AAAA_MM/AAAA_MM_DD
    - DIA/AAAA_MM_DD
    """
    # --------------------------------------------------------------------- #
    ruta_original = Path(ruta_archivo.strip())
    nombre_base   = ruta_original.stem           # sin extensión
    marca_tiempo  = nombre_base.replace("_", "") # quita guion bajo

    # Si el nombre_base contiene prefijo de estación (ej. LABR_20260824_124011), extraer dígitos
    if not (marca_tiempo.isdigit() and len(marca_tiempo) in (12, 14)):
        m14 = re.search(r'(20\d{12})', marca_tiempo)
        if m14:
            marca_tiempo = m14.group(1)
        else:
            m12 = re.search(r'(\d{12})', marca_tiempo)
            if m12:
                marca_tiempo = m12.group(1)
            else:
                # Buscar en las partes de la ruta carpetas con fecha
                encontrada = False
                for p in reversed(ruta_original.parts):
                    p_limpio = p.replace("_", "")
                    if len(p_limpio) == 8 and p_limpio.isdigit():
                        marca_tiempo = p_limpio + "000000"
                        encontrada = True
                        break
                    elif len(p_limpio) == 14 and p_limpio.isdigit():
                        marca_tiempo = p_limpio
                        encontrada = True
                        break
                if not encontrada:
                    raise ValueError(f"No reconozco la marca de tiempo en: {ruta_archivo}")

    # ----------- hallar “DIA” y el posible directorio-año --------------- #
    partes = ruta_original.parts
    try:
        idx_dia = next(i for i, p in enumerate(partes) if p.upper() == "DIA")
    except StopIteration:
        idx_dia = None  # por si acaso la ruta no contiene “DIA”

    candidato_anio = (
        partes[idx_dia + 1]                 # carpeta justo después de “DIA”
        if idx_dia is not None and idx_dia + 1 < len(partes)
        else None
    )
    es_anio_4d = candidato_anio and candidato_anio.isdigit() and len(candidato_anio) == 4

    # --------------------------- caso 14 dígitos -------------------------- #
    if len(marca_tiempo) == 14:            # AAAA MM DD hh mm ss
        anio_largo  = marca_tiempo[:4]
        fecha_larga = marca_tiempo[:8]     # YYYYMMDD
        fecha_corta = anio_largo[2:] + marca_tiempo[4:8]  # AAMMDD
        timestamp_largo  = marca_tiempo   # 14 dígitos
        timestamp_corto  = marca_tiempo[2:]
        usar_4digitos    = True

    # --------------------------- caso 12 dígitos -------------------------- #
    else:                                  # AA MM DD hh mm ss
        aa = marca_tiempo[:2]

        if es_anio_4d:                     # …/DIA/AAAA/…/ AAMMDDhhmmss*
            anio_largo = candidato_anio
        else:                              # …/DIA/ AAMMDDhhmmss*
            anio_largo = "20" + aa

        fecha_larga = anio_largo + marca_tiempo[2:6]      # YYYYMMDD
        fecha_corta = marca_tiempo[:6]                    # AAMMDD
        timestamp_corto = marca_tiempo
        timestamp_largo = anio_largo + marca_tiempo[2:]
        usar_4digitos   = False  # los nombres de archivo conservan el prefijo AAMMDD

    # -------------- descomponer para directorios / sufijos --------------- #
    anio, mes, dia = anio_largo, fecha_larga[4:6], fecha_larga[6:8]
    hora, minuto, segundo = timestamp_corto[6:8], timestamp_corto[8:10], timestamp_corto[10:12]
    nombre_dia_guiones = f"{anio}_{mes}_{dia}"

    # ----- ubicar carpeta “DIA” en la ruta para armar directorio_base ----- #
    directorio_trabajo = (
        Path(*partes[: idx_dia + 1])  # desde la raíz hasta “DIA”
        if idx_dia is not None
        else ruta_original.parent     # fallback
    )

    # 1. Verificar si la ruta original ya contiene la carpeta del día
    directorio_base = None
    for p in [ruta_original] + list(ruta_original.parents):
        if p.name in (nombre_dia_guiones, fecha_larga) and p.is_dir():
            directorio_base = p
            break

    # 2. Si no, buscar entre las estructuras existentes en disco
    if directorio_base is None:
        candidatos_base = [
            directorio_trabajo / anio / f"{anio}_{mes}" / nombre_dia_guiones, # DIA/2026/2026_08/2026_08_24
            directorio_trabajo / f"{anio}_{mes}" / nombre_dia_guiones,        # DIA/2026_08/2026_08_24
            directorio_trabajo / nombre_dia_guiones,                          # DIA/2026_08_24
            directorio_trabajo / anio / fecha_larga,                          # DIA/2026/20260824
            directorio_trabajo / fecha_larga,                                 # DIA/20260824
        ]
        for cand in candidatos_base:
            if cand.exists():
                directorio_base = cand
                break

    # 3. Si ninguno existe aún (ej. se va a crear el día), inferir el layout adecuado
    if directorio_base is None:
        if (directorio_trabajo / anio).exists():
            directorio_base = directorio_trabajo / anio / f"{anio}_{mes}" / nombre_dia_guiones
        elif (directorio_trabajo / f"{anio}_{mes}").exists():
            directorio_base = directorio_trabajo / f"{anio}_{mes}" / nombre_dia_guiones
        else:
            # Detectar si hay carpetas tipo YYYY_MM en el directorio de trabajo
            tiene_meses_directos = any(
                p.is_dir() and len(p.name.split('_')) == 2 and p.name.split('_')[0].isdigit()
                for p in directorio_trabajo.iterdir()
            ) if directorio_trabajo.exists() and directorio_trabajo.is_dir() else False

            if tiene_meses_directos:
                directorio_base = directorio_trabajo / f"{anio}_{mes}" / nombre_dia_guiones
            else:
                directorio_base = directorio_trabajo / anio / f"{anio}_{mes}" / nombre_dia_guiones


    # ---------------- subcarpetas estándar -------------------------------- #
    directorio_dia             = directorio_base / "dia"
    directorio_eventos         = directorio_base / "mseed" / "eventos"
    directorio_registros       = directorio_base / "mseed" / "registros"
    directorio_reportes        = directorio_base / "reportes"
    directorio_fast            = directorio_base / "fastHypo"
    directorio_procesamiento   = directorio_base / "procesamiento"
    directorio_acelerogramas   = directorio_base / "acelerogramas"

    # -------------- nombres de archivo derivados -------------------------- #
    prefijo_fecha = fecha_larga if usar_4digitos else fecha_corta
    sufijo_mseed  = f"_{anio}{mes}{dia}_{hora}{minuto}{segundo}.mseed"

    archivo_estaciones      = directorio_base / f"{prefijo_fecha}_estaciones.csv"
    archivo_comportamiento  = directorio_base / f"{prefijo_fecha}_est.csv"
    archivo_csv             = directorio_base / f"{prefijo_fecha}000000.csv"
    archivo_rep             = directorio_base / f"{prefijo_fecha}000000_rep.csv"
    archivo_cat             = directorio_base / f"{prefijo_fecha}000000_cat.csv"
    archivo_xml             = directorio_base / f"{prefijo_fecha}000000.xml"
    archivo_res             = directorio_base / f"{prefijo_fecha}000000_res.csv"
    archivo_reporte_dia     = directorio_base / f"{prefijo_fecha}000000_rep.pdf"
    archivo_resp            = directorio_reportes / f"{prefijo_fecha}_resp.csv"
    archivo_tiempos         = directorio_reportes / f"{prefijo_fecha}_tiempos.csv"
    archivo_marcas          = directorio_base / f"{prefijo_fecha}000000_marcas.json"
    archivo_auxiliar        = directorio_base / f"{prefijo_fecha}_aux.csv"
    archivo_proc            = directorio_procesamiento / f"{prefijo_fecha}_{hora}{minuto}{segundo}_proc.csv"
    archivo_analogico       = directorio_base / f"{prefijo_fecha}_analogico.csv"
    archivo_digital         = directorio_base / f"{prefijo_fecha}_digital.csv"
    archivo_referencia      = timestamp_largo if usar_4digitos else timestamp_corto

    # ---------------------------- salida ----------------------------------- #
    return {
        "Directorio_trabajo":           str(directorio_trabajo),
        "Directorio_base":              str(directorio_base),
        "Directorio_dia":               str(directorio_dia),
        "Directorio_eventos":           str(directorio_eventos),
        "Directorio_registros":         str(directorio_registros),
        "Directorio_reportes":          str(directorio_reportes),
        "Directorio_fastHypo":          str(directorio_fast),
        "Directorio_procesamiento":     str(directorio_procesamiento),
        "Directorio_acelerogramas":     str(directorio_acelerogramas),
        "archivo_estaciones":           str(archivo_estaciones),
        "archivo_csv":                  str(archivo_csv),
        "archivo_reporte":              str(archivo_rep),
        "archivo_catalogo":             str(archivo_cat),
        "archivo_xml":                  str(archivo_xml),
        "archivo_resumen":              str(archivo_res),
        "archivo_responsables":         str(archivo_resp),
        "archivo_tiempos":              str(archivo_tiempos),
        "archivo_marcas":               str(archivo_marcas),
        "archivo_auxiliar":             str(archivo_auxiliar),
        "sufijo_mseed":                 sufijo_mseed,
        "archivo_referencia":           archivo_referencia,
        "archivo_procesamiento":        str(archivo_proc),
        "archivo_comportamiento":       str(archivo_comportamiento),
        "archivo_reporte_dia":          str(archivo_reporte_dia),
        "archivo_analogico":            str(archivo_analogico),
        "archivo_digital":              str(archivo_digital),
        "anio":                         str(anio_largo)
    }


def cargar_parametros():
        # Asignar todos los parámetros de una sola llamada
        (
            nombre_canal_total,   # NOMBRE
            nombre_canal,         # CODIGO
            tipo_sensor,          # SENSOR
            n_canales,            # CANALES
            hab_canal,            # HAB_CANAL
            componente_canal,     # COMPONENTE
            grafico,              # HAB_GRAFICO
            hab_plt,              # HAB_PLT
            gan_plt,              # GAN_PLT
            ganancia,             # GANANCIA
            diez_plt,             # DIEZ_PLT
            factor_mult,          # FACTOR_MUL
            longitud,             # LONGITUD
            latitud,              # LATITUD
            altura,               # ALTITUD
            ruido,                # RUIDO
            calidad,              # CALIDAD
            ubicacion,            # UBICACIÓN
            tipo_canal,           # CANAL
            red,                  # RED
            muestreo,             # MUESTREO
            numero_est,           # N° ESTACION
            filtro,               # FILTRO
            polaridad,            # Polaridad
            reserva_1             # Reserva 2
        ) = parametros_estaciones()
        # Crear un diccionario para mapear nombres cortos a los nombres completos y el componente a graficar
        mapa_estaciones = dict(zip(nombre_canal, zip(nombre_canal_total, componente_canal)))
        return mapa_estaciones


def obtencion_hora(archivo):
    #Retorna un a tupla con los valores de (año, mes, dia, hora, minuto, segundo y valor en segundos).
    #y los valores string (año_s, mes_s, dia_S, hora_s, minuto_s, segundo_s)
    #Como valor de entrada se ingresa una cadena de caracteres con el formato aammddhhmmss o aammdd 
    #valor=0

    if archivo.lower().endswith('.sis'):
        archivo=os.path.normpath(archivo)
        partes_ruta = archivo.split(os.sep)
        anio = int(partes_ruta[-5])  # AAAA
        # Obtener fecha y hora desde el nombre del archivo
        nombre_archivo = os.path.basename(archivo)
        fecha_str, hora_str = nombre_archivo.split('.')[0].split('_')  # 'AAMMDD', 'hhmmss'
        mm = int(fecha_str[2:4])
        dd = int(fecha_str[4:6])
        hh = int(hora_str[0:2])
        minu = int(hora_str[2:4])
        ss = int(hora_str[4:6])
        fecha_utc = UTCDateTime(anio, mm, dd, hh, minu, ss)
        return fecha_utc

    aux=len(archivo)
    if aux==12:
        anio=int(archivo[0:2])
        mes=int(archivo[2:4])
        dia=int(archivo[4:6])
        hora=int(archivo[6:8])
        minuto=int(archivo[8:10])
        segundo=int(archivo[10:12])
    else:
        anio=int(archivo[aux-12:aux-10])
        mes=int(archivo[aux-10:aux-8])
        dia=int(archivo[aux-8:aux-6])
        hora=int(archivo[aux-6:aux-4])
        minuto=int(archivo[aux-4:aux-2])
        segundo=int(archivo[aux-2:aux])
    #valor=hora*3600+minuto*60+segundo
    fecha_utc = UTCDateTime(2000+anio, mes, dia, hora, minuto, segundo)
    return fecha_utc   


def obtencion_directorios(archivo):  #Este metodo hay que borrarlo una vez comprobado que ya no está siendo usado por otros métodos.
    #archivo:   archivo de evento con el formato AAMMDDhhmmss.sis,AAMMDD_hhmmss.sis,AAMMDDhhmmss o AAMMDDhhmmss.csv
    x = archivo.find(".sis")
    if x!=-1:
        archivo=archivo[0:x]
    y = archivo.find(".csv")
    if y!=-1:
        archivo=archivo[0:y]
    if archivo[-7]=='_':
        archivo=archivo[0:-7]+archivo[-6:x]
    aux_0=len(archivo)
    if int(archivo[-12:-10])<95:
        directorio=archivo[0:aux_0-12]+"20"+archivo[aux_0-12:aux_0-10]+"/20"+archivo[aux_0-12:aux_0-10]+"_"+archivo[aux_0-10:aux_0-8]+"/"
        directorio_base=directorio+"20"+archivo[aux_0-12:aux_0-10]+"_"+archivo[aux_0-10:aux_0-8]+"_"+archivo[aux_0-8:aux_0-6]
    else:
        directorio=archivo[0:aux_0-12]+"19"+archivo[aux_0-12:aux_0-10]+"/19"+archivo[aux_0-12:aux_0-10]+"_"+archivo[aux_0-10:aux_0-8]+"/"
        directorio_base=directorio+"19"+archivo[aux_0-12:aux_0-10]+"_"+archivo[aux_0-10:aux_0-8]+"_"+archivo[aux_0-8:aux_0-6]
        #directorio_base                                      #[0]
    directorio_dia=directorio_base+"/dia"                     #[1]
    directorio_eventos=directorio_base+"/mseed/eventos"       #[2]
    directorio_registros=directorio_base+"/mseed/registros"   #[3]
    directorio_reportes=directorio_base+"/reportes"           #[4]
    directorio_fast=directorio_base+"/fastHypo"               #[5]
    directorio_procesamiento=directorio_base+"/procesamiento" #[6]
    directorio_acelerogramas=directorio_base+"/acelerogramas" #[7]
    
    return(directorio_base,directorio_dia,directorio_eventos,directorio_registros,directorio_reportes,directorio_fast,directorio_procesamiento,directorio_acelerogramas)


def denegar_escritura(ruta_archivo):
    """
    Deniega el permiso de escritura para un archivo específico en Windows.
    :ruta_archivo: Ruta completa del archivo.
    :usuario: Nombre del usuario o grupo al que se quiere denegar la escritura.
    """
    usuario="Todos"
    try:
        # Comando de icacls para denegar el permiso de escritura (W)
        comando = ['icacls', ruta_archivo, '/deny', f'{usuario}:(W)']
        resultado = subprocess.run(comando, capture_output=True, text=True)
        if resultado.returncode == 0:
            print(f"Permiso de escritura denegado para el usuario {usuario} en el archivo {ruta_archivo}")
        else:
            print(f"Error al cambiar los permisos: {resultado.stderr}")
    except Exception as e:
        print(f"Ha ocurrido un error: {e}")


def habilitar_escritura(ruta_archivo):
    """
    Restaura los permisos de escritura eliminando la denegación en un archivo específico.
    ruta_archivo: Ruta completa del archivo.
    usuario: Nombre del usuario o grupo al que se quiere restaurar los permisos.
    """
    usuario="Todos"
    try:
        # Comando de icacls para restaurar permisos
        comando = ['icacls', ruta_archivo, '/remove:d', usuario]
        resultado = subprocess.run(comando, capture_output=True, text=True)
        
        if resultado.returncode == 0:
            print(f"Permisos de escritura restaurados para el usuario {usuario} en el archivo {ruta_archivo}")
        else:
            print(f"Error al restaurar los permisos: {resultado.stderr}")
    
    except Exception as e:
        print(f"Ha ocurrido un error: {e}")

def revisar_csv(eventos):
    """
    Ordena una lista de listas por una columna específica (nombre de archivo),
    elimina duplicados en esa columna, ajusta los números de la primera columna
    en un orden secuencial, y permite resolver conflictos en la columna 3 en
    caso de encontrar archivos repetidos mediante un diálogo en Qt.

    Si la columna 3 es la misma en un archivo repetido, simplemente no se graba
    el nuevo registro y muestra un mensaje de evento repetido.

    :param eventos: La lista de listas a procesar.
    :return: Lista ordenada y sin duplicados.
    """
    indice_columna_archivo = 1  # Columna de archivos (.sis)
    indice_columna_tipo_evento = 2  # Columna de tipo de evento (columna 3)
    # Creamos la aplicación Qt (es necesario para los diálogos)
    # Usamos un diccionario para eliminar duplicados, conservando el primer registro encontrado
    eventos_unicos = {}
    for fila in eventos:
        archivo = fila[indice_columna_archivo]
        # Si ya hemos encontrado este archivo antes
        if archivo in eventos_unicos:
            fila_original = eventos_unicos[archivo]
            tipo_evento_original = fila_original[indice_columna_tipo_evento]
            tipo_evento_actual = fila[indice_columna_tipo_evento]
            # Si los tipos de evento son iguales, se omite y muestra mensaje de evento repetido
            if tipo_evento_original == tipo_evento_actual:
                print(f"Evento repetido para el archivo {archivo}. No se graba.")
                continue
            # Si los tipos de evento son diferentes, mostramos el cuadro de diálogo
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("Conflicto de tipo de evento")
            msg_box.setText(f"Diferencia en el tipo de evento para el archivo {archivo}.\n"
                            f"Original: {tipo_evento_original}, Nuevo: {tipo_evento_actual}\n"
                            f"¿Deseas actualizar el tipo de evento con el nuevo valor?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.No)
            # Ejecutamos el mensaje y capturamos la respuesta
            respuesta = msg_box.exec_()
            if respuesta == QMessageBox.Yes:
                fila_original[indice_columna_tipo_evento] = tipo_evento_actual
                print(f"El tipo de evento se ha actualizado a '{tipo_evento_actual}' para el archivo {archivo}.")
            else:
                print(f"Se mantiene el tipo de evento original '{tipo_evento_original}' para el archivo {archivo}.")
        else:
            # Si no es repetido, añadimos el archivo al diccionario
            eventos_unicos[archivo] = fila
    # Convertimos el diccionario de vuelta a una lista
    eventos_filtrados = list(eventos_unicos.values())
    # Ordenamos por la columna del archivo (.sis)
    eventos_filtrados.sort(key=lambda fila: fila[indice_columna_archivo])
    # Asignamos un número secuencial en la columna 0
    for indice, fila in enumerate(eventos_filtrados, start=1):
        fila[0] = str(indice)
    # Retornamos la lista ajustada y ordenada
    print("Saliendo revisar csv")
    return eventos_filtrados

class VentanaProgreso(QDialog):
    def __init__(self, mensaje="Procesando...", maximo=100, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Progreso")
        self.setFixedSize(300, 100)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        
        layout = QVBoxLayout(self)
        self.etiqueta = QLabel(mensaje)
        layout.addWidget(self.etiqueta)

        self.barra = QProgressBar(self)
        self.barra.setRange(0, maximo)
        self.barra.setValue(0)
        layout.addWidget(self.barra)

        self.show()
        QCoreApplication.processEvents()

    def actualizar(self, valor, mensaje=None):
        self.barra.setValue(valor)
        if mensaje:
            self.etiqueta.setText(mensaje)
        self.barra.repaint()
        self.etiqueta.repaint()
        QCoreApplication.processEvents()

    def cerrar(self):
        self.accept()
        self.deleteLater()

