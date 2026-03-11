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

import struct
import scipy.signal as signal
import numpy as np
from obspy import read

import sys
import os
import xml.etree.ElementTree as ET
from metodos_gestion import obtener_directorios,obtencion_hora,parametros_estaciones
from rsa_io import conversion_mseed,lectura_archivo,escritura_archivo
from PyQt5.QtCore import QDate
from datetime import timedelta,date
import calendar

IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19


def extraccion(evento_auxiliar, solo_eventos, archivo, bandera_forzar):
    """
    evento_auxiliar : línea del AAMMDD_aux.csv 
    solo_eventos    : lista de eventos ya procesados del día (para evitar duplicados)
    archivo         : ruta base ..\DIA\AAMMDD000000
    bandera_forzar  : se mantiene por compatibilidad (no se usa para iterar)
    """
    estaciones_analogicas = lectura_archivo(os.path.join(ruta_datos, 'analogicas.csv'))
    directorios = obtener_directorios(archivo)
    parametros = parametros_estaciones()

    evento, tipo_evento = evento_auxiliar[1], evento_auxiliar[2]
    t_inicio, t_final = float(evento_auxiliar[4]), float(evento_auxiliar[5])
    print('Extrayendo ', evento)

    # Referencias de tiempo
    fecha_ = obtencion_hora(archivo)
    t_ini = fecha_ + t_inicio
    t_fin = fecha_ + t_final
    numero_de_muestras = int((t_fin - t_ini) * 64)

    # Nombres de salida
    nombre_sis = os.path.join(directorios['Directorio_dia'], t_ini.strftime('%Y%m%d_%H%M%S.sis'))
    hora_formateada = t_ini.strftime(" %H: %M: %S")

    # Rango de tiempo inválido
    if t_inicio > t_final:
        print("Advertencia:\n", "Hora incorrecta: Tiempo de inicio mayor a final")
        return

    # Evitar reprocesar eventos ya presentes
    if evento in solo_eventos:
        return

    # ------------------------------------------------------------------
    # Estaciones aportantes (tokens):
    # 1) CSV del día (preferente si existe la fila)
    # 2) Auxiliar (completa lo faltante)
    # ------------------------------------------------------------------
    # Tokens desde auxiliar (si vinieron)
    if len(evento_auxiliar) > 6 and evento_auxiliar[7].strip():
        tokens_aux = evento_auxiliar[7].split()
    else:
        tokens_aux = []

    # Tokens desde CSV del día (preferentes si existe la fila)
    fila_csv = None
    tokens_csv = []
    eventos_csv_dia = lectura_archivo(directorios['archivo_csv'])
    for fila_ev in eventos_csv_dia:
        if fila_ev[1] == evento_auxiliar[1]:
            fila_csv = fila_ev
            break
    if fila_csv:
        # columnas 3..N contienen tokens o '-'
        tokens_csv = [tok for tok in fila_csv[3:] if tok != '-']

    # ------------------------------------------------------------------
    # Extracción a .mseed por estación habilitada (si el evento no es "Ruido")
    # ------------------------------------------------------------------
    if tipo_evento != "Ruido":
        sismo_extraido = []
        estaciones_con_senial = []

        # Estaciones habilitadas con mseed del día disponible
        for numero_estacion, habil in enumerate(parametros['HAB_CANAL']):
            if habil == '1':
                archivo_mseed_dia = os.path.join(
                    directorios['Directorio_registros'],
                    parametros['CODIGO'][numero_estacion] + directorios['sufijo_mseed']
                )
                if os.path.exists(archivo_mseed_dia):
                    estaciones_con_senial.append(
                        (numero_estacion, parametros['NOMBRE'][numero_estacion], parametros['CODIGO'][numero_estacion])
                    )

        # Corte del intervalo y guardado del .mseed de evento por estación
        for numero_estacion, _, codigo_est in estaciones_con_senial:
            componente = int(parametros['COMPONENTE'][numero_estacion]) - 1
            archivo_mseed_dia = os.path.join(
                directorios['Directorio_registros'],
                parametros['CODIGO'][numero_estacion] + directorios['sufijo_mseed']
            )
            stcanal = read(archivo_mseed_dia, format="MSEED",
                           starttime=t_ini, endtime=t_fin, nearest_sample=False)
            if len(stcanal) == 0:
                continue

            # Corrección de polaridad si aplica
            if parametros['POLARIDAD'][numero_estacion] == 'N':
                stcanal[componente].data *= -1

            # Guardar .mseed de evento
            nombre_mseed_ev = os.path.join(
                directorios['Directorio_eventos'],
                codigo_est + t_ini.strftime('_%Y%m%d_%H%M%S.mseed')
            )
            stcanal.write(nombre_mseed_ev, format='MSEED', encoding='STEIM1', reclen=512)
            print('Grabando:', nombre_mseed_ev)

        # Conversión a “analógicas” (V2) y remuestreo a 64 Hz
        for estacion_analogica in estaciones_analogicas:
            if estacion_analogica[0] == 'ESTACION':
                continue

            numero_estacion = int(estacion_analogica[0])
            componente = int(parametros['COMPONENTE'][numero_estacion]) - 1

            nombre_mseed_ev = os.path.join(
                directorios['Directorio_eventos'],
                parametros['CODIGO'][numero_estacion] + t_ini.strftime('_%Y%m%d_%H%M%S.mseed')
            )
            if not os.path.exists(nombre_mseed_ev):
                sis_extraido = np.array([], dtype=np.int32)
                sismo_extraido.append(sis_extraido)
                continue

            stcanal = read(nombre_mseed_ev)
            stcanal.detrend("demean")
            stcanal[componente].data = stcanal[componente].data.astype('int32')

            sis_extraido = stcanal[componente].data
            fs = stcanal[componente].stats.sampling_rate

            if fs != 64:
                sis_extraido = signal.resample(sis_extraido, numero_de_muestras)
                sis_extraido = np.rint(sis_extraido).astype(np.int32)

            # Forzar tamaño exacto
            if sis_extraido.size != numero_de_muestras:
                if sis_extraido.size > numero_de_muestras:
                    sis_extraido = sis_extraido[:numero_de_muestras]
                else:
                    faltantes = numero_de_muestras - sis_extraido.size
                    sis_extraido = np.pad(sis_extraido, (0, faltantes), mode='constant')

            sismo_extraido.append(sis_extraido)

        # Construcción del archivo .sis (solo si es SISMO)
        if tipo_evento == "SISMO":
            archivo_cabecera = os.path.join(directorios['Directorio_trabajo'], "cabecera_sismo")
            try:
                with open(archivo_cabecera, 'rb') as archivo_leer:
                    cabecera = b''
                    contador = 0
                    # Avanza dos etiquetas 0x0008
                    while contador < 2:
                        marcador = archivo_leer.read(2)
                        if marcador == b'\x08\x00':
                            cabecera_0 = archivo_leer.read(2)
                            num_caracteres = struct.unpack("<H", cabecera_0)[0]
                            archivo_leer.read(num_caracteres)
                            contador += 1
                    puntero = archivo_leer.tell()
                    archivo_leer.seek(0)
                    cabecera = (
                        archivo_leer.read(puntero) +
                        b'\x08\x00\x0B\x00' + hora_formateada.encode('utf-8') +
                        archivo_leer.read()
                    )

                with open(nombre_sis, 'wb') as archivo_escribir:
                    archivo_escribir.write(cabecera)

                    segundo_ = t_ini.hour * 3600 + t_ini.minute * 60 + t_ini.second
                    segundo_string = f'{segundo_:05}'
                    archivo_escribir.write(segundo_string.encode())

                    k = 0
                    for n in range(numero_de_muestras):
                        if k == 0:
                            archivo_escribir.write(
                                b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00'
                            )
                        k += 1
                        if k == 64:
                            k = 0

                        for i, estacion_analogica in enumerate(estaciones_analogicas):
                            if estacion_analogica[0] == 'ESTACION':
                                continue
                            m = i - 1
                            estacion = int(estacion_analogica[0])

                            if parametros['HAB_CANAL'][estacion] == "1" and sismo_extraido[m].size > 0:
                                valor = int(sismo_extraido[m][n])
                            else:
                                valor = 0

                            try:
                                archivo_escribir.write(valor.to_bytes(2, byteorder='little', signed=True))
                            except OverflowError:
                                print(valor)
                                valor = 0
                                archivo_escribir.write(valor.to_bytes(2, byteorder='little', signed=True))
            except FileNotFoundError:
                print("Cabecera binaria no encontrada:", archivo_cabecera)

    # ------------------------------------------------------------------
    # Construcción de la línea para el CSV de eventos (101 columnas)
    # ------------------------------------------------------------------
    if evento not in solo_eventos:
        lista_guiones = ['-'] * 101

        # Paso 2: tokens desde CSV del día
        for tok in tokens_csv:
            cod = tok[:4]
            try:
                idx = parametros['CODIGO'].index(cod)
                lista_guiones[idx] = tok
            except ValueError:
                pass

        # Paso 3: tokens desde auxiliar (solo si no fue ya rellenado)
        for tok in tokens_aux:
            cod = tok[:4]
            try:
                idx = parametros['CODIGO'].index(cod)
                if lista_guiones[idx] == '-':
                    lista_guiones[idx] = tok
            except ValueError:
                pass

        # Paso 4: generar token por existencia real de .mseed del evento
        timestamp_ev = t_ini.strftime('_%Y%m%d_%H%M%S.mseed')
        total_estaciones = min(101, len(parametros['CODIGO']))
        for idx in range(total_estaciones):
            if lista_guiones[idx] != '-':
                continue  # ya cubierto por CSV o AUX

            nombre_mseed_ev = os.path.join(
                directorios['Directorio_eventos'],
                parametros['CODIGO'][idx] + timestamp_ev
            )
            if os.path.exists(nombre_mseed_ev):
                cod = parametros['CODIGO'][idx]
                canal = str(parametros['COMPONENTE'][idx]) if str(parametros['COMPONENTE'][idx]) else '0'
                hab = '0'  # No aportante si no vino en CSV/AUX
                token_generado = f"{cod}{canal}{hab}000000"
                lista_guiones[idx] = token_generado

        evento = list(evento_auxiliar[:3]) + lista_guiones

    return evento



def codigos(opcion,archivo_abrir):
        def entero():
            dato_salida=str(struct.unpack("<H", archivo_abrir.read(2))[0])
            salida=4
            return (dato_salida,salida)
        def flotante():
            dato_salida=struct.unpack("<q", archivo_abrir.read(8))[0]
            #dato_salida=decimal_a_hexadecimal(struct.unpack("<Q", archivo_abrir.read(8))[0])
            #dato_salida=str(archivo_abrir.read(8))
            salida=10
            return (dato_salida,salida)
        def flotante1():
            dato_salida=struct.unpack("<q", archivo_abrir.read(8))[0]
            #dato_salida=decimal_a_hexadecimal(struct.unpack("<Q", archivo_abrir.read(8))[0])
            #dato_salida=str(archivo_abrir.read(8))
            salida=10
            return (dato_salida,salida)
        def cadena():
            dato_salida=""
            salida=0
            cabecera_0=archivo_abrir.read(2)
            numero_caracteres=struct.unpack("<H", cabecera_0)[0]
            if (numero_caracteres < 64 and numero_caracteres > 0 ): #numero_caracteres<32
                cabecera_0=archivo_abrir.read(numero_caracteres)
                try:
                    dato_salida=str(cabecera_0.decode())
                except UnicodeDecodeError:
                    dato_salida='SENOR PUNGO'
                salida=numero_caracteres+4
                if numero_caracteres==5:
                    cabecera_1=archivo_abrir.read(20)
                    if cabecera_1 == b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00':
                        numero_segundo=int(cabecera_0)
                        return (None,numero_segundo)
            else:
                numero_segundo=0
                return (None,numero_segundo)
                
            return (dato_salida,salida)
        def default():
            return ('',1)
#Dictionary mapping
        dict={
            b'\x02\x00': entero,
            b'\x05\x00': flotante1,
            b'\x06\x00': flotante,
            b'\x08\x00': cadena,
        }
        aux=dict.get(opcion,default)()    
        return(aux)#return(aux,numero_segundo)



def loc_cabecera(archivo_abrir):
    puntero=0
    bandera_1=1
    bandera_2=0
    dato=[]
    configuracion=[]
    numero_segundo=0
    contador=0
    #Ubica la posición de la cabecera en el registro continuo, sea de un sismo o del registro continuo.
    #global archivo_abrir
    while bandera_1:
        #input()
        archivo_abrir.seek(puntero)     # Ubica el puntero en cierta dirección del archivo
        cabecera_0=archivo_abrir.read(2)
        resultado=codigos(cabecera_0,archivo_abrir)
        if resultado[0]==None:
            numero_segundo=resultado[1]
            puntero=archivo_abrir.tell()
            bandera_1=0
            break
        else:
            if resultado[0]=='canal':
                bandera_2=1
        puntero=puntero+resultado[1]
        if bandera_2:
            dato.append(resultado[0])
            contador+=1
            if contador==9:
                configuracion.append(dato)
                dato=[]
                contador=0
        if len(cabecera_0) == 0:
            bandera_1=0
    archivo_abrir.seek(puntero) #Devuelve la ubicaciòn justo en donde está el numero de segundo.
    return(numero_segundo,configuracion,puntero-20)

def binario_a_mseed(archivo_binario):
    #archivo_binario    Archivo binario para la lectura, puede ser registro continuo o un evento .sis
    archivo=referencia_directorio_completa(archivo_binario)
    directorios=obtener_directorios(archivo)
    canal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]   # canal Variable  para la lectura desde el archivo binario
    archivo_abrir = open(archivo_binario,'rb')
    numero_segundo,configuracion,puntero=loc_cabecera(archivo_abrir)  #return(numero_segundo,configuracion,puntero-20)
    archivo_abrir.close()
    escritura_archivo(directorios['archivo_estaciones'],configuracion)
    archivo_abrir = open(archivo_binario,'rb')
    bandera=1
    archivo_abrir.seek(puntero)
    while bandera:
        cabecera_1=archivo_abrir.read(20)
        if cabecera_1 == b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00':
            puntero=archivo_abrir.tell()
            cuerpo_=archivo_abrir.read(2048)
            if len(cuerpo_)<2048:
                bandera=0
                break
            archivo_abrir.seek(puntero)
            for k in range(0, 64):
                for m in range(0,16):
                    dato=struct.unpack("<h", archivo_abrir.read(2))
                    canal[m].append(dato[0])
        else:
            bandera=0
            break
    archivo_abrir.close()
    hab_canal=[]
    nombre_canal=[]
    fecha = obtencion_hora(archivo_binario)
    for i in range(0,16):
        hab_canal.append(configuracion[i+1][1])
        nombre_canal.append(configuracion[i+1][2])
    canal_np=np.asarray(canal)
    conversion_mseed(canal_np,hab_canal,nombre_canal,fecha,directorios['Directorio_eventos'])
    return nombre_canal

def referencia_directorio_completa(archivo) -> str:
    """
    Devuelve la ruta estándar …\DIA\AAAAMMDD000000.

    · Si la ruta ya es exactamente …\DIA\AAAAMMDD000000     → se devuelve tal cual.
    · Si la ruta es …\DIA\AAAAMMDD000000.[ext]              → se quita la extensión.
    · Para cualquier archivo bajo …\DIA\AAAA\AAAA_MM\AAAA_MM_DD\… →
      se construye y devuelve …\DIA\AAAAMMDD000000.
    """
    ruta = Path(archivo).expanduser().resolve()
    partes = ruta.parts

    # ------------------------------------------------------------------ #
    # 1) Ubicar la carpeta “DIA” en la ruta.
    # ------------------------------------------------------------------ #
    try:
        idx_dia = next(i for i, p in enumerate(partes) if p.upper() == "DIA")
    except StopIteration:
        raise ValueError("La ruta no contiene un directorio 'DIA'.")

    # ------------------------------------------------------------------ #
    # 2) CASO 1: la entrada YA tiene la forma …\DIA\AAAAMMDD000000 o
    #            …\DIA\AAAAMMDD000000.[ext]  → salir pronto.
    # ------------------------------------------------------------------ #
    if len(partes) == idx_dia + 2:                      # solo un elemento tras 'DIA'
        nombre = Path(partes[-1]).stem                  # sin extensión
        if nombre.isdigit() and len(nombre) == 14 and nombre.endswith("000000"):
            return os.path.join(Path(*partes[:idx_dia + 1]), nombre)

    # ------------------------------------------------------------------ #
    # 3) CASO 2: ruta completa …\DIA\AAAA\AAAA_MM\AAAA_MM_DD\…\archivo.ext
    #            → extraer AAAA, MM, DD de las carpetas.
    # ------------------------------------------------------------------ #
    try:
        anio = partes[idx_dia + 1]                     # AAAA
        mes  = partes[idx_dia + 2].split("_")[1]       # MM
        dia  = partes[idx_dia + 3].split("_")[2]       # DD
    except (IndexError, ValueError):
        raise ValueError(
            "La ruta no sigue el patrón esperado 'AAAA/AAAA_MM/AAAA_MM_DD/'."
        )

    referencia = f"{anio}{mes}{dia}000000"
    directorio_dia = Path(*partes[:idx_dia + 1])       # …\DIA

    return os.path.join(directorio_dia, referencia)

def ubicacion(latitud,longitud):
    coordenadas=[]
    latitud=float(latitud)
    longitud=float(longitud)

    poblaciones=os.path.join(ruta_datos,"poblaciones.csv")
    coordenadas=lectura_archivo(poblaciones)
    auxiliar=len(coordenadas)
    distancia=pow(pow(longitud-float(coordenadas[1][0]),2)+pow(latitud-float(coordenadas[1][1]),2),0.5)
    indice=1
    for i in range(1,auxiliar):
        a=pow(longitud-float(coordenadas[i][0]),2)+pow(latitud-float(coordenadas[i][1]),2)
        d=pow(a,0.5)
        if d<distancia:
            distancia=d
            indice=i
    distancia=int(round(distancia*111.321,0))
    if coordenadas[indice][2]==" ":
        ubi_s="a "+str(distancia)+" Km. de "+coordenadas[indice][3]
    else:
        ubi_s="a "+str(distancia)+" Km. de "+coordenadas[indice][3]+" ("+coordenadas[indice][2]+")"
    if coordenadas[indice][4]=="parroquia":
        ubi_s=ubi_s+", cantón "+coordenadas[indice][6]
    if coordenadas[indice][4]=="Ciudad":
        ubi_s="a "+str(distancia)+" Km. de la Ciudad de "+coordenadas[indice][3]    
    ubi_s=ubi_s+", "+coordenadas[indice][5]
    return (ubi_s)



##return((id_sismo,anio_sismo,mes_sismo,dia_sismo,hora_sismo,minuto_sismo,segundo_sismo,latitud,longitud,profundidad,rms,ex,ey,e0,ez,magnitud,'Md','RSA',ruta,ubicacion_sismo),estaciones_evento,archivo_rsa,datos_estaciones)
def agregar_evento(root,sismo,estaciones_sismo):
    sismo_campos=['id_evento', 'anio', 'mes', 'dia', 'hora', 'minuto', 'segundo', 'latitud', 'longitud', 'profundidad', 'rms', 'e_x', 'e_y', 'e_0', 'e_z', 'magnitud', 'tipo_magnitud', 'fuente', 'ruta', 'ubicacion']


# Creación del elemento Evento
    evento = ET.SubElement(root, "Evento")
    
# Creación de los elementos hijo del elemento Evento

    for i, nombre_campo in enumerate(sismo_campos):
        campo_estacion = ET.SubElement(evento, nombre_campo)
        campo_estacion.text = str(sismo[i])

# Añadir las estaciones como sub-elementos de "sismo"
    estaciones = ET.SubElement(evento, "estaciones")

    for i,est in enumerate(estaciones_sismo):
        if i==0:
            estaciones_campos=est
        else:
            estacion = ET.SubElement(estaciones, "estacion")
            for j, campo in enumerate(est):
                nombre_campo = estaciones_campos[j]
                campo_estacion = ET.SubElement(estacion, nombre_campo)
                campo_estacion.text = str(campo)
    return root
        

def obtener_datos_reporte(fecha_ini, fecha_fin, directorio_trabajo, mapa_="Ecuador"):
    """
    Retorna:
        - periodo_reporte (str): Texto descriptivo del período
        - directorio_reporte (str): Ruta donde se guardará el reporte
        - tipo (int): Tipo de período deducido
        - mes (str): Nombre del mes (si aplica)
        - anio (str): Año como texto
    """

    def dias_mes(anio, mes):
        """Retorna el último día del mes, considerando años bisiestos."""
        return calendar.monthrange(anio, mes)[1]

    def deducir_tipo(fecha_ini, fecha_fin):
        """Deducción automática del tipo de reporte."""
        if fecha_ini > fecha_fin:
            fecha_ini, fecha_fin = fecha_fin, fecha_ini

        # Año completo
        if (fecha_ini.month, fecha_ini.day) == (1, 1) and (fecha_fin.month, fecha_fin.day) == (12, 31) and fecha_ini.year == fecha_fin.year:
            return 0

        # Mes completo
        ultimo_dia = dias_mes(fecha_ini.year, fecha_ini.month)
        if (fecha_ini.day == 1 and
            fecha_ini.year == fecha_fin.year and
            fecha_ini.month == fecha_fin.month and
            fecha_fin.day == ultimo_dia):
            return 1

        # Semana completa (lunes a domingo)
        delta = fecha_fin - fecha_ini
        if delta.days == 6 and fecha_ini.weekday() == 0 and fecha_fin.weekday() == 6:
            return 2

        return 3  # Otro período
    # --- Inicialización ---

    meses_es = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    tipo = deducir_tipo(fecha_ini, fecha_fin)
    anio = str(fecha_ini.year)
    mes = meses_es[fecha_ini.month - 1]  # Nombre del mes
    semana = f"{fecha_ini.isocalendar()[1]:02d}"  # Número de semana ISO
    fecha_ = QDate(fecha_ini.year, fecha_ini.month, fecha_ini.day)

    # --- Generación del período y ruta según tipo ---
    if tipo == 0:
        periodo_reporte = f"Período: {anio}"
        directorio_reporte = f"{directorio_trabajo}/{anio}/reportes/"

    elif tipo == 1:
        periodo_reporte = f"Período: {mes} del {anio}"
        directorio_reporte = directorio_trabajo + fecha_.toString('/yyyy/yyyy_MM/reporte')

    elif tipo == 2:
        periodo_reporte = f"Semana {semana} del {anio}: del {fecha_.toString('dd/MM/yyyy')} al "
        fecha_ = QDate(fecha_fin.year, fecha_fin.month, fecha_fin.day)
        periodo_reporte += fecha_.toString('/dd/MM/yyyy')
        directorio_reporte = directorio_trabajo + fecha_.toString('/yyyy/reportes/semanal/semana') + semana + "/"

    elif tipo == 3:
        mismo_mes_anio = (fecha_ini.year == fecha_fin.year) and (fecha_ini.month == fecha_fin.month)
    
        fecha_ = QDate(fecha_ini.year, fecha_ini.month, fecha_ini.day)
        periodo_reporte = "Período: " + fecha_.toString('dd/MM/yyyy')

        if mismo_mes_anio:
            directorio_reporte = directorio_trabajo + fecha_.toString('/yyyy/yyyy_MM/reporte')
        else:
            directorio_reporte = directorio_trabajo + "/reportes" + fecha_.toString('/yyyy')
            auxiliar = fecha_.toString('/yyyy_MM_dd')
            fecha_ = QDate(fecha_fin.year, fecha_fin.month, fecha_fin.day)
            auxiliar += fecha_.toString('_yyyy_MM_dd')
            directorio_reporte += auxiliar

        fecha_ = QDate(fecha_fin.year, fecha_fin.month, fecha_fin.day)
        periodo_reporte += fecha_.toString(' a dd/MM/yyyy')

    else:
        periodo_reporte = ""
        directorio_reporte = ""

    if periodo_reporte.startswith("Período: "):
        nombre_archivo = periodo_reporte[9:].replace('/', '_')
    else:
        nombre_archivo = periodo_reporte[:10]
    archivo_reporte = f"{directorio_reporte}/{mapa_}/{nombre_archivo}"
    return periodo_reporte, directorio_reporte, archivo_reporte

def generar_directorios_unidades_basicas(fecha_ini, fecha_fin, directorio_trabajo="G:/Mi unidad/DIA"):
    """
    Divide el rango entre fecha_ini y fecha_fin en unidades básicas (días, meses, años)
    y retorna una lista de rutas de directorio generadas con obtener_datos_reporte().

    Parámetros:
        fecha_ini (date): Fecha inicial del rango.
        fecha_fin (date): Fecha final del rango.
        directorio_trabajo (str): Ruta base del directorio de trabajo.

    Retorna:
        List[str]: Lista de rutas únicas generadas por obtener_datos_reporte().
    """

    def ultimo_dia_mes(fecha):
        return date(fecha.year, fecha.month, calendar.monthrange(fecha.year, fecha.month)[1])

    def ultimo_dia_anio(fecha):
        return date(fecha.year, 12, 31)

    directorios = []
    actual = fecha_ini

    while actual <= fecha_fin:
        # Intentar agregar un año completo
        if actual.day == 1 and actual.month == 1:
            fin_anio = ultimo_dia_anio(actual)
            if fin_anio <= fecha_fin:
                _, ruta,ruta_archivo = obtener_datos_reporte(actual, fin_anio, directorio_trabajo)
                if ruta not in directorios:
                    directorios.append(ruta_archivo)
                actual = fin_anio + timedelta(days=1)
                continue

        # Intentar agregar un mes completo
        if actual.day == 1:
            fin_mes = ultimo_dia_mes(actual)
            if fin_mes <= fecha_fin:
                _, ruta,ruta_archivo = obtener_datos_reporte(actual, fin_mes, directorio_trabajo)
                if ruta not in directorios:
                    directorios.append(ruta_archivo)
                actual = fin_mes + timedelta(days=1)
                continue

        # Día individual
        archivo = f"{str(actual.year)[2:]:0>2}{actual.month:02d}{actual.day:02d}000000"
        ruta_archivo = directorio_trabajo+'/'+obtener_directorios(archivo)['archivo_csv']
        #_, ruta,ruta_archivo = obtener_datos_reporte(actual, actual, directorio_trabajo)

        directorios.append(ruta_archivo)
        actual += timedelta(days=1)

    return directorios


def extraccion_dato(dato,separador):
    salida=[]
    xxx=dato.split(separador)
    for i in range(0,len(xxx)):
        if(len(xxx[i])>0):
            salida.append(xxx[i])
    return(salida)


