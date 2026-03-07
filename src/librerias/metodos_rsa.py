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
from obspy import read, Trace, Stream
from datetime import datetime, timedelta
import sys
import os
import xml.etree.ElementTree as ET
import struct

import numpy as np
import scipy.signal as signal
from datetime import date
import calendar
from metodos_gestion import obtencion_hora,parametros_estaciones,obtener_directorios
import pandas as pd

# metodos_rsa.py (archivo puente temporal)

#from rsa_io import leer_mseed,conversion_mseed,lectura_resumen,lectura_archivo,escritura_archivo,copiar_archivos,num_reportes
#from rsa_dominio import correccion,calidad_estacion,obtenerTraza,punto_fijo_a_punto_flotante,convertir_lista,decimal_a_hexadecimal,obtener_caracter_hexadecimal,intervalo_reporte
#from rsa_procesamiento import lectura_rsa,archivos_fast,verificar_coincidencias,guardar_intento,guardar_informacion_diaria,ordenar_y_eliminar_duplicados,extraer_dia

#from rsa_io import *
#from rsa_dominio import *
from rsa_procesamiento import *

from rsa_io import leer_mseed,conversion_mseed,lectura_archivo,escritura_archivo

#from rsa_procesamiento import lectura_rsa,ordenar_y_eliminar_duplicados




IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19




def grafico_evento_int(visor, stLeido, t_inicio, t_final, estaciones_evento, hab_grafico, bandera_marcas, pagina):
    #visor   es la ventana donde se grafica
    #stLeido es la traza donde se encuetra el Mseed de la estaciòn
    #t_inicio----- incio del perido del grafico
    #t_final------ fin del perido del grafico
    #estaciones_evento---Estaciones que están marcadas con el contenido del evento en extraer  
    #hab_grafico---- Vector con la habilitacion de los graficos desde el archivo de configuracion 
    #bandera_marcas---- Permite ver las marcas para la extraccion
    #pagina-------- Variable que genera paginas para el despliegue, son de 6 en 6.
    # Limpiar la figura existente
    visor.clear()
    # Crear subplots dentro de la figura existente
    ax = [visor.add_subplot(6, 1, i+1) for i in range(6)]
    minorLocator = MultipleLocator(320)
    
    # Código original para preparar los datos y las marcas...

    parametros = parametros_estaciones()  # (nombre_canal_total_, nombre_canal, tipo_canal_, n_canales_, hab_canal, componente_canal, grafico_)
    estaciones_graficar = []
    st_graficar = []

    for kk in range(len(stLeido)):
        if stLeido[kk] != []:
            st_tiempo = stLeido[kk][0].stats.starttime
            break

    for i in range(pagina * 6, pagina * 6 + 6):
        if i < len(estaciones_evento):
            canal_ = int(estaciones_evento[i])
            comp_ = int(parametros['COMPONENTE'][canal_]) - 1
            estaciones_graficar.append(canal_)
            st_graficar.append(stLeido[canal_][comp_])

    t = st_graficar[0].stats.starttime  # Obtención de la referencia del tiempo
    if t == t_inicio:
        t_i = t_inicio
        t_f = t_final
    else:
        t_i = t + t_inicio
        t_f = t + t_final

    for i in range(len(st_graficar)):
        st_graficar[i].trim(t_i, t_f)  # Aquí la trama, sobre esta hay que trabajar filtros, corrección de línea de base, etc.
        st_graficar[i].detrend('linear')  # Hace la corrección de línea de base lineal

    anio_ = st_graficar[0].stats.starttime.year
    mes_ = st_graficar[0].stats.starttime.month
    dia_ = st_graficar[0].stats.starttime.day
    hora_ = st_graficar[0].stats.starttime.hour
    minuto_ = st_graficar[0].stats.starttime.minute
    segundo_ = st_graficar[0].stats.starttime.second
    tiempo_inicio = datetime(anio_, mes_, dia_, hora_, minuto_, segundo_)
    marca_1 = tiempo_inicio + timedelta(seconds=420)
    marca_2 = tiempo_inicio + timedelta(seconds=780)
    marca_0 = tiempo_inicio + timedelta(seconds=60)

    # Preparar los datos para el gráfico
    for i in range(6):
        try:
            canal_ = estaciones_graficar[5 - i]
            componente_graficar = int(parametros['COMPONENTE'][canal_]) - 1

            ax[i].plot(stLeido[canal_][componente_graficar].times("matplotlib"), st_graficar[5 - i].data, "b-")
            ax[i].set_title(parametros['NOMBRE'][canal_])
            if bandera_marcas:
                ax[i].axvline(marca_0, color="red")
                ax[i].axvline(marca_1, color="green")
                ax[i].axvline(marca_2, color="green")
            ax[i].xaxis.set_minor_locator(minorLocator)
            ax[i].get_yaxis().set_visible(False)
            ax[i].grid(which='minor')
            ax[i].grid(True)
            ax[i].xaxis_date()
        except IndexError:
            pass

    visor.autofmt_xdate()

    # Redibujar el canvas para mostrar los gráficos actualizados
    visor.canvas.draw()





#########################################################################################    
# Método lectura_eventos(archivo)
# Depurado; archivo es un parámetro para poder ubicar los directorios de almacenamiento.
# Tipicamente está en la dirección G:\Mi unidad\DIA en la computadora de procesamiento 
# y tiene la forma AAMMDDhhmmss sin extensión.
# la fuente es el archivo puntos.csv generado en el surfer
# la respuesta es una tupla de dos elementos, un mensaje y la lista con las horas 
# aproximadas de los eventos
#########################################################################################
def lectura_eventos(archivo):
    hora_sismo=[]
    contador=0
    directorios=obtener_directorios(archivo)
    archivo_puntos=directorios['Directorio_base']+"/puntos.csv"
    try:
        auxiliar=open(archivo_puntos)
        auxiliar.close
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
    except FileNotFoundError:
        text="Listado de eventos no encontrado\n\nVerificar Archivos\n\noescoger otro día"
        hora_sismo=0
    return(text,hora_sismo)

def imprimir_plt(archivo,trCanal1,ganancia,diezmado,factor_mult):   #Depurado
    #Método utilizado para la impresión de un archivo miniseed dado por la variabel trCanal hasta un archivo típicamente con extensión .plt
    #dentro de un archivo habierto dado en la variable archivo.  Como es referido al registro contínuo de la RSA, el dleta o variable de tiempo
    #es directamente 1/640.
    numero_muestras=trCanal1.stats.npts
    tiempo=trCanal1.stats.starttime
    f_muestreo=trCanal1.stats.sampling_rate
    hora=tiempo.hour
    minuto=tiempo.minute
    segundo=tiempo.second
    muestra_inicio=(hora*3600+minuto*60+segundo)*f_muestreo
    tiempo=trCanal1.stats.endtime
    n_muestras_maximo=int(86400*f_muestreo)
    hora=tiempo.hour
    minuto=tiempo.minute
    segundo=tiempo.second
    muestra_fin=(hora*3600+minuto*60+segundo)*f_muestreo
    promedio=0
    for i in range(0, int(f_muestreo*5)):
        promedio=promedio+trCanal1[i]
    promedio=int(promedio/(f_muestreo*5))
    if trCanal1.stats.npts>n_muestras_maximo:  #Se presentò un dia con mas de segundos en un dia 
        muestra_fin=n_muestras_maximo
    n_muestras=trCanal1.stats.npts
    muestra=0
    punto=0
    datos_linea=int(360*f_muestreo/diezmado)
    delta=diezmado/(10*f_muestreo)

    for j in range(0,241):#Numero total de segundos en un día /360 segundos (6 minutos por línea} mas 1)
        print("linea " ,j,"Punto",punto)
        if j>2 and j<240:
            promedio=0
            val_ini=int(muestra)
            num_muestras=int(f_muestreo*5)
            for k in range(0, num_muestras):
                if k+val_ini<numero_muestras:
                    promedio=promedio+trCanal1[k+val_ini]
                else:
                    break
            if k!=0:
                promedio=int(promedio/(k))
            else:
                promedio=trCanal1[val_ini-1]
        contador=0.
        if(j==0):
            archivo.write('SC 1.00 1.00\nRO 00\nFL 2\nSC 1.0 0.5\nSP 14\nTR 0.00 .00\n')
        else:
            archivo.write('SC 1.00 2.00\nRO 00\nFL 2\nSC 1.0 0.5\nSP 14\nTR 0.00 -0.10\n')
        for k in range(0, datos_linea): #360 segundos (6 minutos por línea) por la frecuencia de muestreo (64 mps)
            #los datos_lienea=23040 equivalen   a  6 minutos con 64 mps, es decir grafica un línea completa en el plt.
            punto+=diezmado
            valor=0.

            if punto>muestra_inicio and punto<muestra_fin:

                if(muestra<n_muestras):
                    valor=ganancia*(trCanal1[muestra]-promedio)/factor_mult# maximo fondo escala en entero con signo de 16 bits.
                    
                    muestra=muestra+diezmado
            if(k==0):
                archivo.write('MA .0  {:2.3}\n'.format(valor))#archivo.write('MA {:2.5}  {:2.3}\n'.format(contador, valor))
            else:
                contador_s=str(round(contador, 5))
                if(contador<1.):
                    aux=len(contador_s)
                    contador_s=contador_s[1:aux]

                archivo.write('PA {}  {:2.3}\n'.format(contador_s,valor))#archivo.write('PA {:2.5}  {:2.3}\n'.format(contador, valor))
                contador=contador+delta
    


import os



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


def extraccion_dato(dato,separador):
    salida=[]
    xxx=dato.split(separador)
    for i in range(0,len(xxx)):
        if(len(xxx[i])>0):
            salida.append(xxx[i])
    return(salida)


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








def filtro_evento(visor,stLeido,freqmin_,freqmax_,grado_,t_inicio,t_final,estaciones_eventos,hab_grafico,bandera_marcas,pagina,filtros_estaciones,estaciones_eventos_total,bandera_todos):
    #stLeido es la traza donde se encuetra el mseed de la estaciòn
    #freqmin_ Frecuencia mínima de cada estacion
    #freqmax_ Frecuencia máxima de cada estacion
    #grado_ de cada estacion
    #freqmin_frecuencia minima del filtro a implementar.  
    #freqmax_frecuencia màxima del filtro a implementar. 
    #grado_ grado del filtro a implementar.
    #t_inicio Tiempo de inicio del evento
    #t_final Tiempo final del evento
    #estaciones_eventos_total  Todas las estaciones presentes en el evento.
    #estaciones_eventos  Estaciones que forman parte del evento
    #hab_grafico  Estaciones que se muestran en el grafico, originalmente todos los que tienen registros mseed
    #bandera_marcas  Hay que avericuar 
    #pagina página del despleigue
    #filtros_estaciones    Todos los filtros estacion por estación
    #estaciones_eventos_total  Todas las estaciones que tienen registros mseed del evento
    #bandera_todos    Bandera para filtrar todos los canales con los parametros generales o con los filtros estacion por estación.

    num_canal=len(estaciones_eventos)
    for i in range(0, num_canal):
        indice=estaciones_eventos_total.index(estaciones_eventos[i])
        canal_= int(estaciones_eventos[i])
        if bandera_todos:
            grado_=int(filtros_estaciones[indice][0:2])
            freqmin_=int(filtros_estaciones[indice][2:4])
            freqmax_=int(filtros_estaciones[indice][4:6])
        if grado_!=0:
            try:
                stLeido[canal_].filter("bandpass",freqmin=freqmin_,freqmax=freqmax_,corners=grado_)
            except ValueError:
                pass
    aux=t_final-t_inicio
    plt.close()
    #stLeido[0] = obspy.signal.filter.highpass(stLeido[0].data, 1.0, corners=1, zerophase=True, df=stLeido[0].stats.sampling_rate)
    #stLeido[0][0] = obspy.realtime.signal.offset(stLeido[0][0], offset=5.0, rtmemory_list=None)
    grafico_evento_int(visor,stLeido,0,aux,estaciones_eventos,hab_grafico,bandera_marcas,pagina)





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


def espectro_respuesta(acelerograma, dt,factor,directorio):
    """
    Calcula el espectro de respuesta de un sistema de un grado de libertad (SDOF)
    usando el método de Newmark a partir de un archivo mseed.

    Args:
        acelerogrma:  Datos desde el mseed
        dt:Delta t del acelerograma
        factor: factor de conversión par avolverlo en g

    Returns:
        tuple: (T, Spa, Spv, Sd, Sa, Sv)
            - T: Periodos del espectro.
            - Spa: Pseudoaceleración (GAL).
            - Spv: Pseudovelocidad (cm/s).
            - Sd: Desplazamiento máximo (cm).
            - Sa: Aceleración máxima (cm/s²).
            - Sv: Velocidad máxima (cm/s).
    """
    
    damp=0.05   #damp (float): Amortiguamiento adimensional. Default: 0.05 (5%).
    Tmin=0.02   #Tmin (float): Periodo mínimo para el espectro (s). Default: 0.02.
    Tmax=4.0    #Tmax (float): Periodo máximo para el espectro (s). Default: 4.0.
    Ax_g = acelerograma * factor/980.  # Suponemos que el factor convierte a m/s²

    # Convertir a fuerza externa
    m = 1  # Masa normalizada
    p = -m * Ax_g

    # Selección del método según dt
    beta = 1/4 if dt > 0.005 else 1/6
    gamma = 0.5  # Método de aceleración promedio

    # Definir periodos T
    deltaT = 0.05
    T = np.arange(Tmin, Tmax + deltaT, deltaT)

    # Inicialización de resultados
    nT = len(T)
    ls = len(Ax_g)
    Sd = np.zeros(nT)
    Sv = np.zeros(nT)
    Sa = np.zeros(nT)
    Spd = np.zeros(nT)
    Spv = np.zeros(nT)
    Spa = np.zeros(nT)

    # Cálculo para cada periodo T
    for j in range(nT):
        wn = 2 * np.pi / T[j]
        k = m * wn**2
        c = 2 * m * wn * damp

        # Inicializar variables del oscilador
        u = np.zeros(ls)
        udot = np.zeros(ls)
        uddot = np.zeros(ls)

        # Calcular parámetros para Newmark
        khat = k + gamma / beta / dt * c + m / beta / dt**2
        a = m / beta / dt + gamma * c / beta
        b = m / (2 * beta) + dt * (gamma / (2 * beta) - 1) * c

        # Resolver la ecuación para cada paso de tiempo
        for i in range(1, ls):
            dp = p[i] - p[i - 1]
            du = (dp + a * udot[i - 1] + b * uddot[i - 1]) / khat
            dudot = gamma / beta / dt * du - gamma / beta * udot[i - 1] + dt * (1 - gamma / (2 * beta)) * uddot[i - 1]
            duddot = du / (beta * dt**2) - udot[i - 1] / (beta * dt) - uddot[i - 1] / (2 * beta)

            # Actualizar variables
            u[i] = u[i - 1] + du
            udot[i] = udot[i - 1] + dudot
            uddot[i] = uddot[i - 1] + duddot

        # Calcular valores máximos
        Sd[j] = np.max(np.abs(u))
        Sv[j] = np.max(np.abs(udot))
        Sa[j] = np.max(np.abs(uddot))

        # Cálculo de pseudocantidades
        Spd[j] = Sd[j]
        Spv[j] = 2 * np.pi * Spd[j] / T[j]
        Spa[j] = 2 * np.pi * Spv[j] / T[j]

    return T, Spa, Spv, Sd, Sa, Sv

def cargar_evento(parametro,eventos_reporte,catalogo,eventos,canales_eventos_dia,directorio_trabajo,directorio_reporte):
    """
    Carga el evento para procesamiento o reporte
    Args:
        parametro(texto):       Texto desde un cmbx_text.currenttext.
        eventos_reporte (list):         Lista de eventos del día.
        catalogo (list):        Catalogo del día.
        eventos:                 Dato generado en cargar dia
        evento_canales:         Dato generado en cargar dia
        directorio_trabajo:     Directorio de trabajo de ..\DIA\
        directorio_reporte:     Directorio donde se guarda el reporte
    """
    if parametro=='':
            return
    ext=len(eventos_reporte)
    dato=parametro
    dato=dato.split("  ")
    indice_local=int(dato[0])
    evento_local=dato[1]
    parametros=parametros_estaciones()
    directorios=obtener_directorios(evento_local)
    indice=0
    for i in range(0,ext):
        if indice_local==eventos_reporte[i][0]:
            indice=i
            break
    ext=len(catalogo)
    for i in range(0,ext):
        if evento_local==catalogo[i][18]:
            break
    indice_catalogo=i
    evento_reporte_escogido=[]
    evento_reporte_escogido.append(eventos_reporte[indice]) #evento desde el reporte completo del día
    archivo_escogido=directorio_trabajo+'\\'+eventos[indice_local-1][1][0:8]+eventos[indice_local-1][1][9:15]#Variable que tiene el nombre en el formato adecuado para la ubicación de los eventos.
    canales=canales_eventos_dia[indice_local-1]
    trCanal=leer_mseed(archivo_escogido,1)
    dato_escogido=eventos[indice_local-1] #evento desde el formato simple del día, solo número de evento y tipo
    archivo_reporte=directorio_reporte+'/'+dato_escogido[1][:-4]+'_rep.pdf'
    estaciones_eventos=[]
    for i in range(0, len(parametros['CODIGO'])):#Verifica todos los archivos MSEED de registro continuo encontrados en la base de datos.
        nombreMseed = directorio_trabajo+'/'+directorios['Directorio_eventos']+"/"+parametros['CODIGO'][i]+'_'+evento_reporte_escogido[0][1][0:-4]+".mseed"
        if os.path.exists(nombreMseed):            
            estaciones_eventos.append(int(parametros['NUM_ESTACION'][i]))
            parametros['HAB_GRAFICO'][i]="1"
        else:
            parametros['HAB_GRAFICO'][i]="0"
    return (indice,indice_local,indice_catalogo,archivo_escogido,evento_reporte_escogido,canales,trCanal,archivo_reporte,parametros['HAB_GRAFICO'],estaciones_eventos)


    
def cargar_dia(directorios):
    """
    Carga el dia para procesamiento o reporte
    Args:
        archivo_csv: Nombre del archivo para escoger el dian ia con formato AAMMDDhhmmss.
    """
    directorio_trabajo=directorios['Directorio_trabajo']
    if not(os.path.exists(directorios['Directorio_base'])):
        return [],[],[],[],[],[],[],[]
    eventos_reporte=[['0',"Fecha; Hora (UTC)","Evento","Magn.","Prof.(km)","Lat.","Long.","Ubicación"]]
    catalogo=[["Id","anio","mes","dia","hora","min","seg","lat","long","prof","rms","e-x","e-y","e-0","e-z","Mag","Tipo Mag","Fuente","ruta","Ubicacion"]]
    eventos=[]
    vector=[]
    canales_eventos_dia=[]
    contador_n_canales=[[0,0,0,0,0,0],[0,0,0,0,0,0],[0,0,0,0,0,0]]#Tupla que contiene el número de estaciones por evento sísmico.
    root = ET.Element("sismo")
    lista_eventos=lectura_archivo(directorios['archivo_csv'])
    for evento_individual in lista_eventos:
            if evento_individual==[]:
                continue
            catalogo_grabar=[]#Variable donde se guarda lo que se va a grabar en el catalogo diario .csv
            evento_grabar=[]#Variable donde se guarda lo que se va a grabar en el resumen diario .csv
            canales_evento=[]#Variable que muestra los canales donde se tiene el evento con banderas 1 o 0
            vector_temporal=[]
            #self.cmbx_evento_escogido.addItem(str(self.evento_individual[0])+"  "+str(self.evento_individual[1])+"  "+str(self.evento_individual[2]))
            for i in range(0,101): # En vez de 100 16, numero de canales
                if evento_individual[i+3]=='-':
                    canales_evento.append(0)
                else:
                    canales_evento.append(1)
            evento_grabar.append(int(evento_individual[0]))
            evento_grabar.append(evento_individual[1])
            evento_grabar.append(evento_individual[2])
            if(evento_individual[2]=="SISMO"):
                catalogo_grabar=lectura_rsa(evento_individual[1],directorio_trabajo,'')
                if catalogo_grabar==None:
                    print("Error detectado:",evento_individual[1])
                    QMessageBox.information(None, "Aviso", evento_individual[1]+'\nNo procesado')
                    evento_grabar.append("revisar")
                    catalogo_grabar=[]
                elif catalogo_grabar==1:
                    QMessageBox.information(None, "Aviso", evento_individual[1]+"\nError en procesamiento")
                    catalogo_grabar=[]
                else:
                    agregar_evento(root,catalogo_grabar[0],catalogo_grabar[3])
                    for i in(15,9,7,8,19):
                        evento_grabar.append(catalogo_grabar[0][i])
                    evento_grabar.append(catalogo_grabar[1])# catalogo_grabar[1] tiene la información de las estaciones que intervienen en la localización del evento.
                    estaciones__=catalogo_grabar[1]
                    n_estaciones=len(estaciones__.split(' '))-1#aux tiene el número de estaciones involucradas en el procesamiento.
                    n_hora=int(catalogo_grabar[0][0][8:14])
                    if(n_hora<120000):
                        n_periodo=0
                    elif (n_hora<180000):
                        n_periodo=1
                    else:
                        n_periodo=2
                    contador_n_canales[n_periodo][n_estaciones-3]=contador_n_canales[n_periodo][n_estaciones-3]+1
                    for i in(7,8,9,15):
                        vector_temporal.append(catalogo_grabar[0][i])#Variable con datos del evento para desplegar en reporte diario.
                    vector_temporal.append(0)
                    vector_temporal.append(catalogo_grabar[0][18])
                    vector.append(vector_temporal)
                    catalogo_grabar=catalogo_grabar[0]
            if catalogo_grabar!=[]:
                catalogo.append(catalogo_grabar)
            eventos_reporte.append(evento_grabar)
            eventos.append(evento_individual)
            canales_eventos_dia.append(canales_evento)
    # Regenerar catálogo solo con eventos de otras redes (Id termina en != '00') manteniendo la cabecera 'Id'
    if os.path.exists(directorios['archivo_catalogo']):
            catalogo_existente = lectura_archivo(directorios['archivo_catalogo'])
            if catalogo_existente is not None:
                # 2.a) Desde el archivo existente
                for evento_existente in catalogo_existente:
                    if not evento_existente:
                        continue
                    if evento_existente[0] == 'Id':
                        continue
                    if evento_existente[0][-2:] != '00':   # IGEPN (..01), USGS (..02) u otras no-RSA
                        catalogo.append(evento_existente)
                catalogo = ordenar_y_eliminar_duplicados(catalogo, 0)
    indice_responsables=[0,0,0]
    cont_sismo=[0,0,0]
    cont_indefinido=[0,0,0]
    cont_FC=[0,0,0]
    cont_FF=[0,0,0]
    cont_ruido=[0,0,0]
    cont_local=[0,0,0]
    cont_tele=[0,0,0]
    hora_=['12H','18H','24H']
    for evento_ in eventos:
        h=int(evento_[1][-10:-8])
        if h<12:
            indice_hora=0
        elif h<18 and h>11:
            indice_hora=1
        else:
            indice_hora=2
        if evento_[2] == 'SISMO':
            cont_sismo[indice_hora]=cont_sismo[indice_hora]+1
        elif evento_[2] == 'FF':
            cont_FF[indice_hora]=cont_FF[indice_hora]+1
        elif evento_[2] == 'FC':
            cont_FC[indice_hora]=cont_FC[indice_hora]+1
        elif evento_[2] == 'INDEFINIDO':
            cont_indefinido[indice_hora]=cont_indefinido[indice_hora]+1
        elif evento_[2] == 'TELESISMO':
            cont_tele[indice_hora]=cont_tele[indice_hora]+1
        elif evento_[2] == 'Evento_local' or evento_[2] == 'CONTROL':
            cont_local[indice_hora]=cont_local[indice_hora]+1
        else:
            cont_ruido[indice_hora]=cont_ruido[indice_hora]+1
    responsables=lectura_archivo(directorios['archivo_tiempos'])
    aux=['','','']
    if responsables==None:
        aux[0]=['RSA','']
        aux[1]=['RSA','']
        aux[2]=['RSA','']
        responsables=aux
        indice_responsables[0]=0
        indice_responsables[1]=1
        indice_responsables[2]=2
    else:
        aux=len(responsables)
        if aux==3:
            indice_responsables[0]=0#ind_0=0
            indice_responsables[1]=1#ind_1=1
            indice_responsables[2]=2#ind_2=2
        if aux==4:
            indice_responsables[0]=0#ind_0=0
            indice_responsables[1]=2#ind_1=2
            indice_responsables[2]=3#ind_2=3
        if aux==5:
            indice_responsables[0]=0#ind_0=0
            indice_responsables[1]=1#ind_1=1
            indice_responsables[2]=4#ind_2=4
        if aux==6:
            indice_responsables[0]=0#ind_0=0
            indice_responsables[1]=2#ind_1=2
            indice_responsables[2]=5#ind_2=5
    variable_responsables=[["RESPONSABLE","HORA","TOT.","SIS.","FF","FC","IND.","TEL.","Local_CONTROL.","Ruido","3 est","4 est","5 est","6 est","7 est","8 est"]]
    for i in range (0,3):
        total=cont_sismo[i]+cont_FF[i]+cont_FC[i]+cont_indefinido[i]+cont_tele[i]+cont_local[i]+cont_ruido[i]
        aux=[responsables[indice_responsables[i]][0],hora_[i],total,cont_sismo[i],cont_FF[i],cont_FC[i],cont_indefinido[i],cont_tele[i],cont_local[i],cont_ruido[i]]
        aux=aux+contador_n_canales[i]
        variable_responsables.append(aux)
    resumen=[["SISMO","FF","FC","TELESISMOS","Local_CONTROL","INDEFINIDO","Ruido"],[sum(cont_sismo),sum(cont_FF),sum(cont_FC),sum(cont_tele),sum(cont_local),sum(cont_indefinido),sum(cont_ruido)]]
    return eventos_reporte,catalogo,eventos,vector,canales_eventos_dia,root,variable_responsables,resumen

def insertar_evento_otras_redes(catalogo,indice_catalogo,eventos_reporte,red_,magnitud_,tipo_magnitud,texto,texto2,evento_reporte_escogido,indice,indice_local):
    #red_:          cmbx_red.currentIndex
    #magnitud_:     cmbx_tipo_mag.currentIndex
    #tipo_magnitud:     cmbx_tipo_mag.currentText
    #texto:         textEdit.toPlainText   
    #print("\nEvento escogido:\n",evento_reporte_escogido)
    eventos_temp=[" "," "," "," "," "," "," "," "]
    catalogo_temp=[" "," "," "," "," "," "," "," "," "," "," "," "," "," "," "," "," "," "," "," "]
    if(red_==0):
            QMessageBox.information(None, "Error", '¡Falta la Red!')
            return
    if(magnitud_==0):
            QMessageBox.information(None, "Error", '¡Falta tipo de sismo!')
            return        
    if(texto==""):
            QMessageBox.information(None, "Error", '¡Falta información del sismo!')
            return  
    lectura=extraccion_dato(texto,"\n")
    if(red_==1):#Cuando la red es IGEPN
        try:
            indice_utc = lectura.index('Tiempo UTC:')
            fecha_utc = lectura[indice_utc + 1]
            anio, mes, dia = fecha_utc[:10].split('-')
            hora, minuto, segundo = fecha_utc[11:].split(':')
            valor_formateado = f"{anio}{mes}{dia}{hora}{minuto}01"
            catalogo_temp[0]=valor_formateado#ID
            catalogo_temp[1]=str(int(anio))#año
            catalogo_temp[2]=str(int(mes))#mes
            catalogo_temp[3]=str(int(dia))#dia
            catalogo_temp[4]=str(int(hora))#hora
            catalogo_temp[5]=str(int(minuto))#min
            catalogo_temp[6]=str(int(segundo))#seg
            indice_localizacion = lectura.index('Localización:')
            localizacion=lectura[indice_localizacion + 1]
            partes = localizacion.split()
            latitud = float(partes[0].replace('°', '')) * (-1 if partes[1] == 'S' else 1)
            longitud = float(partes[2].replace('°', '')) * (-1 if partes[3] == 'W' else 1)
            catalogo_temp[7]=str(longitud)#Longitud
            catalogo_temp[8]=str(latitud)#Latitud
            indice_profundidad = lectura.index('Profundidad:')
            profundidad_str=lectura[indice_profundidad + 1]
            profundidad = float(profundidad_str.replace(' km', ''))
            catalogo_temp[9]=str(profundidad)
            indice_magnitud = lectura.index('Magnitud:')
            magnitud_str=lectura[indice_magnitud + 1]
            valor_magnitud, tipo_magnitud = magnitud_str.split()
            valor_magnitud = float(valor_magnitud)
            catalogo_temp[15]=str(valor_magnitud)   #Magnitud        
            catalogo_temp[16]=tipo_magnitud         #Tipo de Magnitud
            catalogo_temp[17]="IGEPN"               #Fuente
            catalogo_temp[18]=evento_reporte_escogido[0][1]#Ruta
            if catalogo_temp[18][0]=="\n":
                catalogo_temp[18]=catalogo_temp[18][1:-1]
            if catalogo_temp[18][-1]=="\n":
                catalogo_temp[18]=catalogo_temp[18][0:-2]
            catalogo_temp[19]=ubicacion(longitud,latitud)#Ubicacion
            eventos_temp[0]=indice_local
            eventos_temp[1]=anio+"/"+mes+"/"+dia+"_"+hora+":"+minuto+":"+segundo#Fecha; Hora (UTC)
            eventos_temp[2]="IGEPN"#Evento
            eventos_temp[3]=str(valor_magnitud)#Magnitud
            eventos_temp[4]=str(profundidad)#Profundidad
            eventos_temp[5]=str(longitud)#Longitud
            eventos_temp[6]=str(latitud)#Latitud
            eventos_temp[7]=catalogo_temp[19]#Ubicacion
        except Exception as e:
            QMessageBox.information(None, e, '¡Revise la información del sismo en la página de la IGEPN!')
            return

    if(red_==2):#Cuando la red es USGS
            if(texto==""):
                QMessageBox.information(None, "Error", '¡Falta información del sismo!\nRevise la ubicación del sismo en la página de la USGS!')
                return 
            for i in range(0,len(lectura)):
                if(lectura[i]=='Time'):
                    break
            if(i==len(lectura)):
                QMessageBox.information(None, "Error", '¡¡Revise la información del sismo en la página de la USGS!')
                return 
            tiempo=lectura[1]
            localizacion=lectura[2]
            profundidad=lectura[3]  
            #ruta=extraccion_dato(lectura[0],"-")
            magnitud=extraccion_dato(lectura[0]," ")
            catalogo_temp[0]=tiempo[0:4]+tiempo[5:7]+tiempo[8:10]+tiempo[11:13]+tiempo[14:16]+"02"#ID
            catalogo_temp[1]=str(int(tiempo[0:4]))#año
            catalogo_temp[2]=str(int(tiempo[5:7]))#mes
            catalogo_temp[3]=str(int(tiempo[8:10]))#dia
            catalogo_temp[4]=str(int(tiempo[11:13]))#hhora
            catalogo_temp[5]=str(int(tiempo[14:16]))#min
            catalogo_temp[6]=str(int(tiempo[17:19]))#seg
            localizacion=extraccion_dato(localizacion," ")
            catalogo_temp[7]=str(-1*(float(localizacion[0][0:len(localizacion[0])-2])))#Longitud
            catalogo_temp[8]=str(-1*(float(localizacion[1][0:len(localizacion[1])-2])))#Latitud
            profundidad=extraccion_dato(profundidad," ")
            catalogo_temp[9]=str(float(profundidad[0]))
            catalogo_temp[15]=str(float(magnitud[1]))#Magnitud
            catalogo_temp[16]=tipo_magnitud #Tipo de Magnitud
            catalogo_temp[17]="USGS"#Fuente
            catalogo_temp[18]=evento_reporte_escogido[0][1]#Ruta
            catalogo_temp[19]=ubicacion(catalogo_temp[7],catalogo_temp[8])#Ubicacion
            eventos_temp[0]=indice_local
            eventos_temp[1]=tiempo[0:4]+"\\"+tiempo[5:7]+"\\"+tiempo[8:10]+"_"+tiempo[11:13]+":"+tiempo[14:16]#Fecha; Hora (UTC)
            eventos_temp[2]="USGS"#Evento
            eventos_temp[3]=catalogo_temp[15]#Magnitud
            eventos_temp[4]=catalogo_temp[9]#Profundidad
            eventos_temp[5]=catalogo_temp[7]#Longitud
            eventos_temp[6]=catalogo_temp[8]#Latitud
            eventos_temp[7]=catalogo_temp[19]#Ubicacion
    catalogo.insert(indice_catalogo+1, catalogo_temp)
    ordenar_y_eliminar_duplicados(catalogo,0)
    eventos_reporte.insert(indice+1, eventos_temp)    
    #evento_reporte_escogido.append(eventos_temp)
    return catalogo,eventos_reporte


def guardar_seniales_csv(archivo_csv, seniales_ascii, stats):
    """
    Guarda los datos de las señales en un archivo CSV con cabecera de estadísticas.

    Parámetros:
    archivo_csv (str): Nombre del archivo CSV de salida.
    seniales_ascii (list): Lista con las señales y sus etiquetas.
    stats (dict): Diccionario con la información estadística del archivo trcanal.
    """

    # Extraer dinámicamente los nombres de las señales y sus datos
    etiquetas = [seniales_ascii[0].strip(), seniales_ascii[2].strip(), seniales_ascii[4].strip()]
    datos_seniales = [seniales_ascii[1][0], seniales_ascii[3][0], seniales_ascii[5][0]]

    # Determinar la longitud máxima de las señales para alinear los datos
    max_len = max(len(datos_seniales[0]), len(datos_seniales[1]), len(datos_seniales[2]))

    # Rellenar con NaN para igualar las longitudes
    columnas = {}
    for etiqueta, datos in zip(etiquetas, datos_seniales):
        columnas[etiqueta] = pd.Series(datos).reindex(range(max_len))

    # Crear el DataFrame con las etiquetas dinámicas
    df = pd.DataFrame(columnas)

    # Abrir el archivo y escribir la cabecera con los datos de stats
    with open(archivo_csv, 'w', encoding='utf-8') as f:
        f.write("# Información de estadísticas:\n")
        for clave, valor in stats.items():
            f.write(f"# {clave}: {valor}\n")
        f.write("\n")

    # Guardar los datos de las señales debajo de la cabecera
    df.to_csv(archivo_csv, mode='a', index=False)
   
    
def incrementar_catalogo_eventos(directorio_trabajo,eventos,eventos_catalogo):
    """
    eventos:   Eventos tomados de AAAAMMDD_000000.csv
    eventos_catalogo:  Eventos tomados del catálogo 
    """
    for evento in eventos:
        directorios=obtener_directorios(evento[1])
        archivo_procesamiento=directorio_trabajo+directorios['archivo_procesamiento']
        aux=['00000000000000', '2025', '1', '1', '0', '0', '0', '-2.00', '-79.00', '0', 'rms', 'e-x', 'e-y', 'e-0', 'e-z', '0', ' ', 'No procesado', evento[1],' , , ']
        if os.path.exists(archivo_procesamiento):
            lectura=lectura_archivo(archivo_procesamiento)
            if len(lectura)==1:
                #os.remove(archivo_procesamiento)
                continue
            else:
                for k in range(len(lectura),1,-1):
                    pass
        evento_buscado =int(evento[1].replace('_', '')[:-4])
        tamanio_catalogo=len(eventos_catalogo)
        indice=1
        for i in range(indice,tamanio_catalogo):
            evento_analizado=int(eventos_catalogo[i][IDX_EVENTO].replace('_', '')[:-4])
            if evento_buscado==evento_analizado:
                break
            if evento_analizado>evento_buscado:
                eventos_catalogo.insert(i,aux)
                break
    return eventos_catalogo


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


def recolectar_evt(directorio_base):
    archivos_evt = []

    # Función para verificar formato AAAAMMDD
    def es_formato_aaaammdd(nombre):
        return re.fullmatch(r"\d{8}", nombre) is not None

    # Función para verificar formato AAMMDD
    def es_formato_aammdd(nombre):
        return re.fullmatch(r"\d{6}", nombre) is not None

    # Revisar el contenido del directorio base
    print("Revisando en directorio ",directorio_base )
    subdirectorios_encontrados=os.listdir(directorio_base)
    print("Subdirectorios encontrados:",subdirectorios_encontrados)
    for subdirectorio in subdirectorios_encontrados:
        print("Trabajando sobre ",subdirectorio)
        ruta_subdirectorio = os.path.join(directorio_base, subdirectorio)
        if os.path.isfile(ruta_subdirectorio):
            if subdirectorio.lower().endswith(".evt"):
                archivos_evt.append(ruta_subdirectorio)
        elif os.path.isdir(ruta_subdirectorio) and es_formato_aaaammdd(subdirectorio):
            # Directorio tipo AAAAMMDD encontrado
            for subdirectorio_fecha in os.listdir(ruta_subdirectorio):
                ruta_subdirectorio_fecha = os.path.join(ruta_subdirectorio, subdirectorio_fecha)

                if os.path.isdir(ruta_subdirectorio_fecha) and es_formato_aammdd(subdirectorio_fecha):
                    # Subdirectorio tipo AAMMDD encontrado
                    for archivo in os.listdir(ruta_subdirectorio_fecha):
                        ruta_archivo = os.path.join(ruta_subdirectorio_fecha, archivo)
                        if os.path.isfile(ruta_archivo) and archivo.lower().endswith(".evt"):
                            archivos_evt.append(ruta_archivo)

    return archivos_evt




from scipy.stats import kurtosis, skew
from scipy.fft import rfft, rfftfreq

def clasificar_evento_sismico(traza):
    """
    Analiza un evento sísmico segmentado (con múltiples componentes) y determina si alguna componente
    muestra evidencia de un evento sísmico real. Si encuentra una positiva, retorna esa; si no, retorna
    la última con clasificación falsa.

    Parámetros:
    -----------
    traza : obspy.Stream
        Objeto Stream que contiene una o más trazas (componentes).

    Retorna:
    --------
    dict con métricas del evento y clasificación (de la componente que cumpla o la última).
    """

    # Umbrales de decisión (ajustables)
    umbrales = {
        "duracion_min": 0.8,         # segundos
        "rms_min": 100,              # depende del instrumento
        "kurtosis_min": 2.5,         # picos
        "frecuencia_max": 20         # Hz
    }

    resultado_final = {}

    for tr in traza:
        fs = tr.stats.sampling_rate
        datos = tr.data

        # Preprocesamiento
        tr.detrend("demean")
        tr.filter("bandpass", freqmin=1.0, freqmax=20.0)

        # Estadísticas
        rms = np.sqrt(np.mean(datos ** 2))
        duracion = len(datos) / fs
        kurt = kurtosis(datos)
        sesgo = skew(datos)

        # Espectro
        N = len(datos)
        fft_vals = np.abs(rfft(datos))
        freqs = rfftfreq(N, d=1/fs)
        frecuencia_dominante = freqs[np.argmax(fft_vals)]

        es_evento = (
            duracion >= umbrales["duracion_min"] and
            rms >= umbrales["rms_min"] and
            kurt >= umbrales["kurtosis_min"] and
            frecuencia_dominante <= umbrales["frecuencia_max"]
        )

        resultado = {
            "componente": tr.stats.channel,
            "duracion_s": round(duracion, 2),
            "rms": round(rms, 2),
            "kurtosis": round(kurt, 2),
            "skewness": round(sesgo, 2),
            "frecuencia_dominante_Hz": round(frecuencia_dominante, 2),
            "evento_sismico_probable": es_evento
        }

        # Si ya se detectó un evento, lo retornamos inmediatamente
        if es_evento:
            return resultado

        # Si no es evento, seguimos pero guardamos el último por si todas fallan
        resultado_final = resultado

    # Ninguna componente clasificó como evento verdadero
    return resultado_final

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

def Guardar_dia(eventos_reporte,catalogo,eventos,root,responsables,resumen,directorios):#self.eventos_reporte,self.catalogo,self.eventos,self.root,self.responsable,self.directorios
    #return eventos_reporte,catalogo,eventos,vector,canales_eventos_dia,root,variable_responsables,resumen
    escritura_archivo(directorios['archivo_reporte'],eventos_reporte)        
    escritura_archivo(directorios['archivo_catalogo'],catalogo)
    escritura_archivo(directorios['archivo_csv'],eventos)
    escritura_archivo(directorios['archivo_responsables'],responsables)
    escritura_archivo(directorios['archivo_resumen'],resumen)
    # Crear el objeto de árbol y agregar la raíz
    tree = ET.ElementTree(root)
    # Escribir el archivo XML
    tree.write(directorios['archivo_xml'], encoding="utf-8", xml_declaration=True)


def extraer_hasta_directorio(ruta_completa, nombre_directorio):
    partes = Path(ruta_completa).parts
    if nombre_directorio in partes:
        indice = partes.index(nombre_directorio)
        ruta_recortada = Path(*partes[:indice + 1])
        return str(ruta_recortada) + '/'
    else:
        return ''
          

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



def extraer_kinemetrics_evt(ruta_shd_txt):
    """
    Extrae metadatos de un archivo EVT convertido a texto (.SHD)
    y devuelve un diccionario tipo kinemetrics_evt.
    """
    evt_dict = {
        'nombre_estacion': None,
        'latitud': None,
        'longitud': None,
        'altura': None,
        'profundiad': None,
        'numero_serie_sensor': None,
        'sensitividad': None,
        'unidades': None,
        'modelo': None,
        'serialnumber': None,
        'canales':None,
        'muestreo':None,
        'pre_evento':None,
        'post_evento':None,
        'tiempo_incicio':None,
        'tiempo_disparo':None,
        'duracion':None,
        'frames':None,
        'scans':None,
        'instrument':None,
        'comment': ''

    }
    with open(ruta_shd_txt, "r", encoding="latin1") as f:
        cabecera = f.read().splitlines()

    evt_dict['nombre_estacion'] = cabecera[2].split()[2]
    evt_dict['latitud'] = None
    evt_dict['longitud'] = None
    evt_dict['altura'] = None
    evt_dict['profundiad'] = None
    evt_dict['numero_serie_sensor'] = None
    evt_dict['sensitividad'] = None
    evt_dict['unidades'] = None 
    evt_dict['modelo'] = None 
    evt_dict['serialnumber'] = cabecera[1].split()[-1] 
    evt_dict['canales'] = cabecera[3].split()[2] 
    evt_dict['muestreo'] = cabecera[3].split()[-1] 
    evt_dict['pre_evento'] = cabecera[4].split()[1] 
    evt_dict['post_evento'] = cabecera[4].split()[3] 
    evt_dict['tiempo_incicio'] = cabecera[6].split()[2] + "T" + cabecera[6].split()[4]
    evt_dict['tiempo_disparo'] = cabecera[7].split()[2] + "T" + cabecera[7].split()[4]
    evt_dict['duracion'] = cabecera[8].split()[1]
    evt_dict['frames'] = cabecera[8].split()[3]
    evt_dict['scans'] = cabecera[8].split()[-2] 
    evt_dict['instrument'] = None 
    evt_dict['comment'] = None 
    return evt_dict

def ejecutar_en_vm(evt_path,virtual_path):
        try:
            usuario = "vbox"
            password = "rsa"

            comando = [
                "VBoxManage", "guestcontrol", "RSA1", "run",
                "--username", usuario,
                "--password", password,
                "--exe", "C:\\Windows\\System32\\cmd.exe",
                "--timeout", "10000",
                "--", "cmd.exe", "/c", "C:\\DIA\\KINEMETRICS\\ejecutar_kw2asc.bat"
            ]
            subprocess.run(comando, capture_output=True, text=True)
            nombre_base = evt_path.stem
            archivos_txt = [virtual_path  / f"{nombre_base}.00{i+1}" for i in range(3)]
            archivo_shd = virtual_path  / f"{nombre_base}.SHD"
            datos_evt=extraer_kinemetrics_evt(archivo_shd)
            with open(archivo_shd, "r", encoding="latin1") as f:
                cabecera = f.read().splitlines()
            estacion = datos_evt['nombre_estacion']
            sampling_rate=float(datos_evt['muestreo'])
            linea_tiempo = cabecera[6].split()
            fecha_str = linea_tiempo[2] + "T" + linea_tiempo[4]
            starttime = datetime.strptime(fecha_str, '%m/%d/%YT%H:%M:%S.%f')
            canales = ["Z", "N", "E"]
            stream = Stream()
            for path, comp in zip(archivos_txt, canales):
                with open(path, "r") as f:
                    datos = np.array([float(x) for x in f.read().split()], dtype=np.float32)
                tr = Trace(data=datos)
                tr.stats.station = estacion
                tr.stats.channel = comp
                tr.stats.starttime = starttime
                tr.stats.sampling_rate = sampling_rate
                tr.stats.kinemetrics_evt = datos_evt
                stream += tr

            for ext in [".001", ".002", ".003", ".SHD"]:
                archivo = virtual_path / f"{nombre_base}{ext}"
                if archivo.exists():
                    os.remove(archivo)
            return stream
        except Exception as e:
            print(e)
            return None

