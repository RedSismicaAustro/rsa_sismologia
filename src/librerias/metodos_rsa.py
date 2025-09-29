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
from PyQt5.QtWidgets import (QMessageBox,QGraphicsScene)
from PyQt5.QtCore import QDate,QDateTime
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView
import matplotlib
matplotlib.use('Qt5Agg')  # Asegúrate de que esto está antes de importar matplotlib.pyplot
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator    
from matplotlib.widgets import Cursor, Button
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MultipleLocator
from time import sleep
import subprocess

from obspy import UTCDateTime, read, Trace, Stream
from datetime import datetime, timedelta
from reportlab.graphics.charts.linecharts import HorizontalLineChart
#from reportlab.graphics.shapes import *
from reportlab.lib.colors import *
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics import shapes
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.pagesizes import letter, A4
import sys
from pathlib import Path
from PyQt5.QtCore import QDate,QDateTime,Qt
import os
import re
import xml.etree.ElementTree as ET
import struct
import copy
import numpy as np
import scipy.signal as signal
from scipy import integrate  
from scipy.signal import hilbert, chirp
from datetime import date,datetime, timedelta
import calendar

from obspy import read
import tkinter as tk
import shutil
from metodos_gestion import obtencion_hora,parametros_estaciones,obtener_directorios,denegar_escritura,habilitar_escritura,revisar_csv,VentanaProgreso
import pandas as pd


IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19


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
            print("Canal:",canal_,"Componente:",comp_ )
            print(stLeido[canal_])
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



def calidad_estacion(stLeido):
    #stLeido es l atraza donde se encuetra el Mseed de la estaciòn
    parametros=parametros_estaciones()
    num_canal=len(parametros['CODIGO'])
    evaluacion={}
    envolvente=[]
    for i in range(0, num_canal):
        evaluacion[i]=-1
        if stLeido[i]!=[]:
            #evaluacion[i]=90   #Es para hacer mas rápido el proceso.
            stLeido[i].decimate(factor=8)
            promedio=0
            for j in range(0,100):
                promedio=promedio+stLeido[i][0].data[j]
            promedio=int(promedio/100)
            pasos=3.0#pasos=1.5
            muestras=stLeido[i][0].stats.npts
            dato_anterior=stLeido[i][0].data[0]-0.0-promedio
            for j in range(0,muestras):
                stLeido[i][0].data[j]=abs(stLeido[i][0].data[j]-promedio)
                if  (stLeido[i][0].data[j])>dato_anterior:
                    dato_anterior=(stLeido[i][0].data[j])+0.0
                else:
                    dato_anterior=dato_anterior-pasos
                    stLeido[i][0].data[j]=int(dato_anterior)
            aux_env=stLeido[i][0].data
            contador=0
            for j in range(0,muestras):
                if  (aux_env[j])<parametros['RUIDO'][i]:
                    contador=contador+1
            eval_=(contador/muestras)#/0.95
            evaluacion[i]=round(eval_*100,0)
            envolvente.append(aux_env)
    return evaluacion,envolvente



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
    

def obtenerTraza(nombreCanal,num_canal, data, anio, mes, dia, horas, minutos, segundos, microsegundos):#Depurado
    # Define todas las caracteristicas de la traza
    parametros=parametros_estaciones()
    nombre_estacion=parametros['CODIGO']
    for estacion in range(0,len(nombre_estacion)):
        if nombreCanal==nombre_estacion[estacion]:
            break
    nombreRed=parametros['RED'][estacion]
    nombreEstacion=parametros['CODIGO'][estacion]
    tipoEstacion=parametros['SENSOR'][estacion]
    localizacion=parametros['UBICACION'][estacion]
    nCanal=parametros['CANAL'][estacion]
    fsample=int(parametros['MUESTREO'][estacion])
    calidad=parametros['CALIDAD'][estacion]
    if fsample>80:
        nombreCanal='E'
    else:
        nombreCanal='S'
    if tipoEstacion=='SISMICO':
        nombreCanal=nombreCanal+'L'
    else:
        nombreCanal=nombreCanal+'N'
    num_canal=num_canal-3*(int((num_canal-1)/3))
    nombreCanal=nombreCanal+nCanal[num_canal-1:num_canal]
    stats = {'network': nombreRed, 'station': nombreEstacion, 'location': localizacion,
             'channel': nombreCanal, 'npts': len(data), 'sampling_rate': fsample,
             'mseed': {'dataquality': calidad}}
    # Establece el tiempo
    stats['starttime'] = UTCDateTime(anio, mes, dia, horas, minutos, segundos, microsegundos)    
    # Crea la traza con los datos las caracteristicas
    traza = Trace(data = data, header = stats)
    return traza

def conversion_mseed(canal_np,hab_canal,nombre_canal,fecha_,directorio):
    #Canal_np es ela arreglo numpy donde está el registro continuo por estación
    #hab_canal es un vector donde están los canales habilitados del registro continuo de los 16 manejados en el sistema analógico
    #nombe_canal, vector con valores string de 4 caracteres para el nombre de cada uno de los canales
    #fecha_ variable generada desde el programa con la fecha    
    #directorio de los archvios mseed, registros o events
    trCanal = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
    anio=fecha_.year
    mes=fecha_.month
    dia=fecha_.day
    horas=fecha_.hour
    minutos=fecha_.minute
    segundos=fecha_.second
    canal_np = canal_np.astype(np.int32)
    for i in range(0, 16):
         if hab_canal[i]!="0":
            # Nombre del archivo en funcion del tiempo de inicio
            hora_string=fecha_.strftime('%y%m%d_%H%M%S')
            #hora_string=fecha_[1][0]+fecha_[1][1]+fecha_[1][2]+'_'+fecha_[1][3]+fecha_[1][4]+fecha_[1][5]        
            fileName = directorio+"/"+nombre_canal[i]+'_20'+hora_string#fileName = directorio+nombre_canal[i]+'.UC.Z..20'+hora_string
    # Una vez que se tiene los datos, llama al metodo para obtener la traza
    # Todos los parametros que recibe se detallan en el metodo (mas abajo)
            trazaCH1 = obtenerTraza(nombre_canal[i],1,canal_np[i],(anio), mes, dia, horas, minutos, segundos, 0)
    # Crea un objeto Stream con la traza
            stData = Stream(traces=[trazaCH1])
    # Si se desea varias trazas, esto seria para cuando se tiene 3 canales
    # stData = Stream(traces=[trazaCH1, trazaCH2, trazaCH3])
    # Guarda todas las trazas en un archivo en formato miniseed con codificacion
    # STEIM1 para disminuir el tamaño del archivo
            nombreMseed = fileName + ".mseed"
            stData.write(nombreMseed, format = 'MSEED', encoding = 'STEIM1', reclen = 512)
            trCanal[i]=stData
    return(trCanal)#en trCanal es un arrglo donde se encuentra todos los cananles en mseed.

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

def loc_cabecera(archivo_abrir):
    puntero=0
    bandera_1=1
    bandera_2=0
    dato=[]
    configuracion=[]
    numero_segundo=0
    contador=0
    dato_salida=""
    salida=0
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

def obtener_caracter_hexadecimal(valor):
    # Lo necesitamos como cadena
    valor = str(valor)
    equivalencias = {
        "10": "A",
        "11": "B",
        "12": "C",
        "13": "D",
        "14": "E",
        "15": "F",
    }
    if valor in equivalencias:
        return equivalencias[valor]
    else:
        return valor

def decimal_a_hexadecimal(decimal):
    hexadecimal = ""
    while decimal > 0:
        residuo = decimal % 16
        verdadero_caracter = obtener_caracter_hexadecimal(residuo)
        hexadecimal = verdadero_caracter + hexadecimal
        decimal = int(decimal / 16)
    return hexadecimal

def correccion(acelerograma, fondo_escala): 
    # acelerograma: Trace de ObsPy (aceleración)
    # fondo_escala: valor para normalizar las señales
    # Devuelve: aceleración, velocidad y desplazamiento corregidos (como np.ndarray)

    def integrar_por_trapecios(datos, dt):  
        return np.cumsum((datos[:-1] + datos[1:]) * 0.5) * dt

    # Aceleración corregida
    trCanal_acc = copy.deepcopy(acelerograma)
    trCanal_acc.detrend("spline", order=5, dspline=250)
    dt = trCanal_acc.stats.delta

    # Velocidad (integrando aceleración)
    datos_vel = integrar_por_trapecios(trCanal_acc.data, dt)
    datos_vel = np.insert(datos_vel, 0, 0.0)  # para conservar longitud
    trCanal_vel = copy.deepcopy(trCanal_acc) #Truco para mantener la misma estrucutura de aceleración para la velocidad
    trCanal_vel.data = datos_vel
    trCanal_vel.detrend("spline", order=5, dspline=250)

    # Desplazamiento (integrando velocidad)
    datos_des = integrar_por_trapecios(trCanal_vel.data, dt)
    datos_des = np.insert(datos_des, 0, 0.0)
    trCanal_des = copy.deepcopy(trCanal_acc) #Truco para mantener la misma estrucutura de aceleración para el desplazameinto
    trCanal_des.data = datos_des
    trCanal_des.detrend("spline", order=5, dspline=250)

    # Normalización
    Acel = trCanal_acc.data
    Vel  = trCanal_vel.data
    Des  = trCanal_des.data

    Acorreg_ = np.array([n / fondo_escala for n in Acel])
    Vcorreg_ = np.array([n / fondo_escala for n in Vel])
    Dcorreg_ = np.array([n / fondo_escala for n in Des])

    return (Acorreg_, Vcorreg_, Dcorreg_)


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
        
def punto_fijo_a_punto_flotante(data):
    # Convertir los datos en formato de bytes a un número entero sin signo de 32 bits
    num = int.from_bytes(data, byteorder='big', signed=False)
    # Convertir el número entero sin signo a un número entero con signo de 32 bits
    if num >= (1 << 31):
        num -= (1 << 32)
    # Dividir el número entero con signo por 2^23 para obtener el valor en punto flotante correspondiente
    valor_punto_flotante = num / (2 ** 23)
    return valor_punto_flotante


def intervalo_reporte(fecha_inicio,fecha_final):
    def dias_al_domingo(weekday):
        return {0:0,1:6,2:5,3:4,4:3,5:2,6:1}[weekday]
    def ingresar_dias(fecha_actual,fecha_final):
        if fecha_actual.day==1:
            if fecha_actual.month==1:
                sigue="anio"
                return fecha_actual,sigue
        if fecha_actual.weekday()==0:
            fechas.append(fecha_actual.strftime('%Y/%m/%d'))
            fecha_actual += timedelta(days=1)
        for i in range(0,dias_al_domingo(fecha_actual.weekday())):
            fechas.append(fecha_actual.strftime('%Y/%m/%d'))
            if fecha_actual<fecha_final:
                mes=fecha_actual.month
                fecha_actual += timedelta(days=1)
                if fecha_actual.month!=mes:
                    sigue="mes"
                    break
            else:
                sigue="fin"
                break
            sigue="semana"
        return fecha_actual,sigue
    def ingresar_semanas(fecha_actual,fecha_final):
        while True:
            fecha_siguiente = fecha_actual + timedelta(days=7)
            if fecha_siguiente>fecha_final:
                break
            if fecha_siguiente.month!=fecha_actual.month:
                break
            fechas.append(fecha_actual.strftime( '%Y/%W'))
            fecha_actual=fecha_siguiente    
            return fecha_actual,"dia"
    def ingresar_mes(fecha_actual,fecha_final):
        anio_actual = fecha_actual.year
        while True:
            year, month,day = fecha_actual.year, fecha_actual.month, fecha_actual.day
            last_day_of_month = calendar.monthrange(year, month)[1]
            fecha_siguiente = fecha_actual + timedelta(days=last_day_of_month)
            if fecha_siguiente > fecha_final:
                sigue="dia"
                break
            fechas.append(fecha_actual.strftime('%y/%m'))
            fecha_actual=fecha_siguiente
            if year!=fecha_siguiente.year:
                sigue="anio"
                break
            return fecha_actual,sigue
    def ingresar_anio(fecha_actual,fecha_final):
        anio_actual = fecha_actual.year
        while True:
            if calendar.isleap(anio_actual):
                dias=366
            else:
                dias=365
            fecha_siguiente=fecha_actual+timedelta(days=dias)
            anio_actual += 1
            if fecha_final <= fecha_siguiente:
                sigue="mes"
                break    
            fechas.append(str(anio_actual))
            fecha_actual=fecha_siguiente
        return fecha_actual,sigue
    def fechas_exactas(fecha_actual,fecha_final):
        year, month,day = fecha_actual.year, fecha_actual.month,fecha_actual.day
        if fecha_actual>fecha_final:
            return fecha_actual,"fin"
        if day!=1:
            return fecha_actual,"dia"
        last_day_of_month = calendar.monthrange(year, month)[1]
        if calendar.isleap(year):
            dias=366
        else:
            dias=365
        fecha_siguiente=fecha_actual+timedelta(days=dias-1)
        if fecha_siguiente<=fecha_final:
            fechas.append(fecha_siguiente.strftime('%Y'))
            fecha_actual=fecha_siguiente+timedelta(days=1)
            return fecha_actual,"inicio"
        fecha_siguiente=fecha_actual+timedelta(days=last_day_of_month-1)
        if fecha_siguiente<=fecha_final:
            fechas.append(fecha_siguiente.strftime('%y/%m'))
            fecha_actual=fecha_siguiente+timedelta(days=1)
            return fecha_actual,"inicio"
        return fecha_actual,"dia"

   
    # Crear la tupla que almacenará las fechas
    fechas = []
    # Agregar la fecha de inicio a la tupla

    fecha_actual=fecha_inicio
    estado="inicio"
    while estado!="fin":
        if estado=="inicio":
            proceso=fechas_exactas(fecha_actual,fecha_final)
        elif estado=="dia":
            proceso=ingresar_dias(fecha_actual,fecha_final)
        elif estado=="semana":
            proceso=ingresar_semanas(fecha_actual,fecha_final)
        elif estado=="mes":
            proceso=ingresar_mes(fecha_actual,fecha_final)
        elif estado=="anio":
            proceso=ingresar_anio(fecha_actual,fecha_final)
        else:
            pass
        fecha_actual=proceso[0]
        estado=proceso[1]
    return fechas


def convertir_lista(lista):
    nueva_lista = []
    for elemento in lista:
        # Intentar convertir a entero
        try:
            nuevo_elemento = int(elemento)
            nueva_lista.append(nuevo_elemento)
            continue
        except ValueError:
            pass
        
        # Intentar convertir a flotante
        try:
            nuevo_elemento = float(elemento)
            nueva_lista.append(nuevo_elemento)
            continue
        except ValueError:
            pass
        
        # Si no se puede convertir a número, dejar como caracter
        nueva_lista.append(elemento)
    
    return nueva_lista


def plot_streams(stream1, stream2):
    root = tk.Tk()
    root.title("Ajuste de tiempo del Obsidian")
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)

    # Graficar el primer stream
    texto=stream1.stats.station
    ax1.plot(stream1.times(), stream1.data, 'k')
    ax1.set_ylabel(texto)

    # Graficar el segundo stream
    texto=stream2.stats.station
    ax2.plot(stream2.times(), stream2.data, 'r')
    ax2.set_ylabel(texto)
    ax2.set_xlabel('Tiempo (s)')

    # Configurar límites de los ejes
    ax1.set_ylim(min(stream1.data), max(stream1.data))
    ax2.set_ylim(min(stream2.data), max(stream2.data))

    # Crear cursores en los gráficos
    cursor1 = Cursor(ax1, useblit=True, color='blue', linewidth=1)
    cursor2 = Cursor(ax2, useblit=True, color='green', linewidth=1)

    # Variable para almacenar la línea de marcado
    last_line1 = None
    last_line2 = None

    # Lista para almacenar las referencias de tiempo
    references = [0,0]

    # Función para actualizar la posición de los cursores y mostrar los valores
    def update_cursor(event):
        nonlocal last_line1, last_line2

        if event.inaxes == ax1:
            if last_line1:
                last_line1.remove()
            last_line1 = ax1.axvline(x=event.xdata, color='blue', linewidth=1)
            reference = event.xdata
            references[0]=reference
        elif event.inaxes == ax2:
            if last_line2:
                last_line2.remove()
            last_line2 = ax2.axvline(x=event.xdata, color='green', linewidth=1)
            reference = event.xdata
            references[1]=reference
        fig.canvas.draw()

    # Función para cerrar la ventana de plot
    def close_plot(event):
        plt.close(fig)

    # Agregar botón para cerrar el plot
    button_ax = fig.add_axes([0.9, 0.9, 0.1, 0.1])
    close_button = Button(button_ax, 'Cerrar')
    close_button.on_clicked(close_plot)

    # Crear el lienzo de la figura y agregarlo a la ventana de Tkinter
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Agregar barra de herramientas de navegación
    toolbar = NavigationToolbar2Tk(canvas, root)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    # Conectar la función de actualización al evento 'button_press_event'
    fig.canvas.mpl_connect('button_press_event', update_cursor)

    # Mostrar la figura
    tk.mainloop()

    return (references[0]-references[1])


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


def lectura_archivo__(archivo):
    # Inicializamos una lista vacía para almacenar los valores
    valores = []
    try:
        # Abrimos el archivo en modo lectura
        with open(archivo, 'r') as file:
            # Leemos cada línea del archivo
            for linea in file:
                # Dividimos la línea en valores usando punto y coma como separador
                elementos = linea.strip().split(';')
                # Agregamos los elementos a la lista
                valores.append(elementos)
    except FileNotFoundError:
        print(f"El archivo {archivo} no fue encontrado.")
        return None
    return valores



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
    from PyQt5.QtWidgets import QMessageBox

    try:
        with open(archivo, 'w', encoding='utf-8') as file:
            for sublist in valores:
                if sublist != []:
                    lista_como_cadenas = [str(elemento) for elemento in sublist]
                    linea = ';'.join(lista_como_cadenas)
                    file.write(linea + '\n')

    except Exception as e:
        mensaje = f"No se pudo escribir en el archivo:\n{archivo}\n\nEs posible que esté abierto en otro programa como Excel.\n\nDetalles: {str(e)}"
        print(mensaje)
        QMessageBox.warning(None, "Error al escribir archivo", mensaje)



def copiar_archivos(archivos_origen, archivos_destino):
    lista=(17,17,12,11,10,10,10)
    for i in range(0,7):
        try:
            archivo_dest=archivos_destino[i][:-lista[i]]+archivos_origen[i][-lista[i]:]
            shutil.copyfile(archivos_origen[i],archivo_dest)
            print("Copiando:",archivos_origen[i],archivo_dest)
        except FileNotFoundError:
            print("Archivo no encontrado:",archivos_origen[i])
            pass


def lectura_rsa(archivo,directorio_trabajo,usuario):
#  Mètodo para obtebner la información completa del sismo
#  archivo es el nombre del archivo .sis generado por el registro continuo sin el .sis
#  archivo_rsa es el archivo genrardo por el fasthypo con extencion .rsa generada a partir del archivo.
#  usuario es para tomar información del sistema o de procesamiento, cuaNdo el valor es '', toma del sistema y si no toma de procesamiento asignando los valores 
#   del drive adecuado en las computadoras de procesamiento.
    directorios=obtener_directorios(archivo)    
    archivo_procesamiento=archivos_fast(archivo,directorio_trabajo,usuario)
    archivo_fas=archivo_procesamiento[1]
    archivo_rsa=archivo_procesamiento[2]
    archivo_fase=archivo_procesamiento[3]
    bandera_error=0
    archivo_estaciones = os.path.join(directorio_trabajo, directorios["archivo_estaciones"])
    lectura_estaciones=lectura_archivo(archivo_estaciones)
    aux=len(archivo)
    if archivo[-11:-10]=="_":
        sismo_aux=archivo[-17:-11]+archivo[-10:aux]
    else:
        sismo_aux=archivo[-10:aux]
    lectura_fase=[]
    auxiliar=["Disp.","t_pr.","t_sec.","marc.s","t_cod."]
    lectura_fase.append(auxiliar)
    if os.path.exists(archivo_fase): #Toma lectura del archivo phase si existe
        with open(archivo_fase,newline='') as f_f:
            lectura_archivo_fase=csv.reader(f_f,delimiter='\n',quotechar=';')
            for lectura in lectura_archivo_fase:
                for v in lectura:
                    auxiliar=[v[4:8],v[19:24],v[31:36],v[36:40],v[70:75]]
                    lectura_fase.append(auxiliar)
    elif os.path.exists(archivo_fas):# Si no esiste phase lee del .fas
        archivo_abrir = open(archivo_fas,'rb')
        bandera_1=1
        auxiliar=[]
        contador=0
        while bandera_1:
            cabecera_0=archivo_abrir.read(2)
            resultado=codigos(cabecera_0,archivo_abrir)
            if cabecera_0==b'\x08\x00':
                if contador==2:
                    auxiliar.append(resultado[0])
                    contador=3
                if contador==1:
                    auxiliar.append(resultado[0][:5])
                    auxiliar.append(resultado[0][-4:])
                    contador=2
                if resultado[1]==28:
                    auxiliar=[]
                    if resultado[0][:4]!='    ':
                        if contador==0:
                            auxiliar=[resultado[0][4:8],resultado[0][-5:]]
                            contador=1
                if auxiliar!=[]and contador==3:
                    lectura_fase.append(auxiliar)
                    contador=0
            if len(cabecera_0) == 0:
                bandera_1=0
    else:
        auxiliar=['    ','    ','    ','    ','    ']
        lectura_fase.append(auxiliar)

    if os.path.exists(archivo_rsa):
        with open(archivo_rsa,newline='') as f_r:
            lectura_archivo_rsa=csv.reader(f_r,delimiter=' ',quotechar=';')
            estaciones_evento=""
            lectura_total=[] #Variable que tiene los datos del archivo linea por linea
            for lectura in lectura_archivo_rsa:
                datos_=[]
                for v in lectura:
                    if v=='' or v==' ':
                        pass
                    else:
                        datos_.append(v)
                lectura_total.append(datos_)
            for i, datos_ in enumerate(lectura_total):
                try:
                    if len(datos_)>0:
                        if datos_[0]=='sta':
                            if lectura_total[i-1]!=[]:
                                latitud=float(lectura_total[i-1][0])
                                longitud=float(lectura_total[i-1][1])
                                profundidad=round(float(lectura_total[i-1][2]),1)
                                segundo_sismo=float(lectura_total[i-1][3])
                                datos_estaciones=[]
                                auxiliar=lectura_estaciones[0][2:8]+datos_[1:]+lectura_fase[0]
                                datos_estaciones.append(auxiliar)
                                indice=i
                                while lectura_total[i]!=[]:
                                    i=i+1
                                    if lectura_total[i]!=[]:
                                        estacion_=lectura_total[i][0]
                                        lista_seleccionada = next((lista for lista in lectura_estaciones if lista[2] == estacion_), None)
                                        if lista_seleccionada==None:
                                            
                                            if estacion_=='CALCULO':
                                                estaciones=''
                                                for estacion in datos_estaciones:
                                                    if estacion!='nombre':
                                                        estaciones=estaciones+estacion[0]+' ' 
                                                return
                                            print("Estacion ",estacion_)
                                            return
                                        if len(lectura_fase)!=2:
                                            auxiliar_est=lista_seleccionada[2:8]+lectura_total[i][1:]+lectura_fase[i-indice]
                                        else:
                                            auxiliar_est=lista_seleccionada[2:8]+lectura_total[i][1:]+lectura_fase[1]
                                        datos_estaciones.append(auxiliar_est)
                        if datos_[0]=='error':
                            ex=float(datos_[3])
                            ey=float(datos_[6])
                            e0=float(datos_[10])
                        if datos_[0]=='event':
                            id_sismo='20'+sismo_aux[0:10]+'00'
                            anio_sismo=2000+int(datos_[3])
                            mes_sismo=int(datos_[4])
                            dia_sismo=int(datos_[5])
                            hora_sismo=int(datos_[6])
                            minuto_sismo=int(datos_[7])
                        if datos_[0]=='rms=':
                            rms=float(datos_[1])
                            aux=len(lectura_total[i+3][1])
                            ez=float(lectura_total[i+3][1][0:aux-2])
                            i=i+3
                        if datos_[0]=='Promedio':
                            if datos_[4]!='No':
                                magnitud= float(datos_[4])
                            else:
                                magnitud= 0.0
                except ValueError:
                    bandera_error=1


            if bandera_error:#Cuando hay error en el procesamiento por  conversion de variables.
                return 1
            else:                
                ubicacion_sismo=ubicacion(latitud,longitud)
                ruta=archivo
                if segundo_sismo<0:#hay que transformar en archivo datetime y hacer la operaciòn para que sea exacto
                    segundo_sismo=60+segundo_sismo
                    minuto_sismo = minuto_sismo-1
                    if minuto_sismo==-1:
                        minuto_sismo=59
                        hora_sismo=hora_sismo-1
                for ev in datos_estaciones:
                    if ev!=[] and ev[0]!="sta" and ev[0]!='    ' and ev[0]!='nombre':
                        estaciones_evento=estaciones_evento+ev[0]+" "
                datos_sismo=[id_sismo,str(anio_sismo),str(mes_sismo),str(dia_sismo),str(hora_sismo),str(minuto_sismo),str(segundo_sismo),str(latitud),str(longitud),str(profundidad),str(rms),str(ex),str(ey),str(e0),str(ez),str(magnitud),'Md','RSA',ruta,ubicacion_sismo]
                datos_estaciones = [sublista[:12]+sublista[13:15]+sublista[16:17]+sublista[19:]  for sublista in datos_estaciones]
                #datos_sismo-------------Datos extraidos del registro aammddhhmmss.rsa
                #estaciones_evento-------Datos extraidos del registro aammddhhmmss.rsa
                #datos_estaciones--------Datos extraidos del registro aammddhhmmss.rsa

                return(datos_sismo,estaciones_evento,archivo_rsa,datos_estaciones)
    else:
        return 


def archivos_fast(evento, dir_trabajo, usuario):
    """
    Devuelve las rutas:
        [ .sis, .fas, .rsa, Phase, .L, .P, .S ]

    ─ Host    (usuario == '') → .sis/.fas con AAAA
    ─ Virtual (usuario != '') → .sis/.fas con AA  (se recortan los dos primeros dígitos)

    Formatos FASTHYPO (todos con año AA):
        · MMDDhhmm.rsa
        · PhaseDDh.hmm
        · MMDDhh.mm[L|P|S]

    Si el .rsa exacto no existe se suma 1 minuto y ese minuto “ajustado” se
    reutiliza en Phase y L/P/S.
    """

    # ------------------------------------------------------------------ #
    # 1 · Carpetas base
    # ------------------------------------------------------------------ #
    info = obtener_directorios(evento)
    dir_dia  = os.path.join(dir_trabajo, info['Directorio_dia'])
    dir_fast = os.path.join(dir_trabajo, info['Directorio_fastHypo'])

    if usuario:
        csv_path = os.path.join(ruta_datos, "responsables.csv")
        for fila in lectura_archivo(csv_path):
            if fila[0].strip() == usuario.strip():
                dir_dia, dir_fast = fila[1], fila[2]
                break

    # ------------------------------------------------------------------ #
    # 2 · Despiece de nombre base
    # ------------------------------------------------------------------ #
    base = evento[:-4]                             # quita '.sis'
    if len(base) == 13:                            # AAMMDD_hhmmss
        yy, mm, dd = 20 + int(base[:2]), base[2:4], base[4:6]
        hh, minu, ss = base[7:9], base[9:11], base[11:13]
        sisfas_base  = base                        # ya en AA
    else:                                          # AAAAMMDD_hhmmss
        yy, mm, dd = int(base[:4]), base[4:6], base[6:8]
        hh, minu, ss = base[9:11], base[11:13], base[13:15]
        sisfas_base  = base if usuario == '' else base[2:]  # recorta '20' sólo para virtual
    # ------------------------------------------------------------------ #
    # 3 · .sis / .fas
    # ------------------------------------------------------------------ #
    archivo_sis = os.path.join(dir_dia, f"{sisfas_base}.sis")
    archivo_fas = os.path.join(dir_dia, f"{sisfas_base}.fas")

    # ------------------------------------------------------------------ #
    # 4 · .rsa  (intento minuto real)
    # ------------------------------------------------------------------ #
    rsa_nom = f"{mm}{dd}{hh}{minu}.rsa"
    archivo_rsa = os.path.join(dir_fast, rsa_nom)

    # ------------------------------------------------------------------ #
    # 5 · Redondeo (+1 min) si falta el .rsa
    # ------------------------------------------------------------------ #
    if not os.path.exists(archivo_rsa):
        dt = datetime(yy, int(mm), int(dd), int(hh), int(minu), int(ss)) + timedelta(minutes=1)
        mm, dd, hh, minu = dt.strftime("%m %d %H %M").split()
        rsa_nom = f"{mm}{dd}{hh}{minu}.rsa"
        archivo_rsa = os.path.join(dir_fast, rsa_nom)

    # ------------------------------------------------------------------ #
    # 6 · Phase  y  L / P / S (mismo minuto usado en .rsa)
    # ------------------------------------------------------------------ #
    phase_nom = f"Phase{dd}{hh[0]}.{hh[1]}{minu}"
    archivo_phase = os.path.join(dir_fast, phase_nom)

    base_lp = f"{mm}{dd}{hh}.{minu}"
    archivo_L = os.path.join(dir_fast, base_lp + 'L')
    archivo_P = os.path.join(dir_fast, base_lp + 'P')
    archivo_S = os.path.join(dir_fast, base_lp + 'S')

    # ------------------------------------------------------------------ #
    return [archivo_sis, archivo_fas, archivo_rsa,
            archivo_phase, archivo_L, archivo_P, archivo_S]


def guardar_informacion_diaria(archivo,directorio_trabajo,catalogo_anterior,eventos):
    #archivo:          Archivo del día con formato AAMMDD_hhmmss.csv
    #directorio_trabajo:   Directorio del drive de trabajo
    #catalogo_anterior:    Catalogo encontrado en el día para cargar la información de otras redes.
    archivo=archivo[-16:]
    directorios=obtener_directorios(archivo)
    archivo_csv=directorio_trabajo+'/'+directorios['Directorio_base']+'/'+archivo
    catalogo=[["Id","anio","mes","dia","hora","min","seg","lat","long","prof","rms","e-x","e-y","e-0","e-z","Mag","Tipo Mag","Fuente","ruta","Ubicacion"]]
    eventos_reporte=[['0',"Fecha Hora (UTC)","Evento","Magn.","Prof.(km)","Lat.","Long.","Ubicación"]]
    archivo_xml=archivo_csv[:-4]+".xml"
    archivo_dat=archivo_csv[:-4]+"_rep.csv"
    archivo_cat=archivo_csv[:-4]+"_cat.csv"
    archivo_res=archivo_csv[:-4]+"_res.csv"
    nombre_directorio_reportes=directorios['Directorio_reportes']
    archivo_responsables=directorio_trabajo+nombre_directorio_reportes+'/'+archivo_csv[-25:-23]+archivo_csv[-22:-20]+archivo_csv[-19:-17]+'_tiempos.csv'
    rep_responsables=directorio_trabajo+nombre_directorio_reportes+archivo_csv[-25:-23]+archivo_csv[-22:-20]+archivo_csv[-19:-17]+'_resp.csv'
    contador_n_canales=[[0,0,0,0,0,0],[0,0,0,0,0,0],[0,0,0,0,0,0]]#Tupla que contiene el número de estaciones por evento sísmico.
    indice_responsables=[0,0,0]
    root = ET.Element("sismo")
    for evento_individual in eventos:
        catalogo_grabar=[]#Variable donde se guarda lo que se va a grabar en el catalogo diario .csv
        evento_grabar=[]#Variable donde se guarda lo que se va a grabar en el resumen diario .csv
        evento_canales=[]#Variable que muestra los canales donde se tiene el evento con banderas 1 o 0
        for i in range(0,101): # En vez de 100 16, numero de canales
            if evento_individual[i+3]=='-':
                evento_canales.append(0)
            else:
                evento_canales.append(1)
        evento_grabar.append(evento_individual[0])
        evento_grabar.append(evento_individual[1])
        evento_grabar.append(evento_individual[2])
        if(evento_individual[2]=="SISMO"):
            catalogo_grabar=lectura_rsa(evento_individual[1],directorio_trabajo,'')
            if catalogo_grabar==None or catalogo_grabar==1:
                evento_grabar.append("revisar")
                catalogo_grabar=[]
            else:
                agregar_evento(root,catalogo_grabar[0],catalogo_grabar[3])
                for i in(15,9,7,8,19):
                    evento_grabar.append(str(catalogo_grabar[0][i]))
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
                catalogo_grabar=catalogo_grabar[0]
        catalogo.append(catalogo_grabar)
        eventos_reporte.append(evento_grabar)
        evento_canales.append(evento_canales)
        
        ############################################################################
        #Rutina para cargar el número de eventos y los responsables del día procesado
    if os.path.exists(archivo_responsables):
            with open(archivo_responsables) as archivo_leer:
                lector_csv = csv.reader(archivo_leer)
                lectura=[]
                for row in lector_csv:
                    lectura.append(row)
                aux=len(lectura)
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
            with open(rep_responsables, 'w', newline='') as archivo_grabar:
                escritor_csv = csv.writer(archivo_grabar,delimiter=';')
                escritor_csv.writerow(["RESPONSABLE","HORA","TOT.","SIS.","FF","FC","IND.","TEL.","Local_CONTROL.","Ruido","3 est","4 est","5 est","6 est","7 est","8 est"])
                responsable=[]
                for i in range (0,3):
                    aux=lectura[indice_responsables[i]][0].split(';')+contador_n_canales[i]
                    escritor_csv.writerow(aux)
                    responsable.append(aux[0])
    else:
            pass
    for i  in range(1,len(catalogo_anterior)):
        if catalogo_anterior[i]==[]:
            continue
        id_evento=catalogo_anterior[i][0]
        if id_evento[-1]=='0':#La ultima cifra del id del evento diferente de 0, es decir es de otras redes
            continue
        numero=int(id_evento)
        for j in range(1,len(catalogo)):
            if catalogo[j]==[]:
                continue
            evento=catalogo[j][0]
            otro_numero=int(evento)
            if otro_numero>numero:
                    catalogo.insert(j,catalogo_anterior[i])
                    break
        evento_otras_redes=catalogo_anterior[i]
        numero=int(evento_otras_redes [18][-10:-4])
        for j in range(1,len(eventos_reporte)):
            otro_numero=int(eventos_reporte[j][1][-10:-4])
            if otro_numero>numero:
                variable=[eventos[j-1][0],evento_otras_redes[18],evento_otras_redes[17],evento_otras_redes[15],evento_otras_redes[9],evento_otras_redes[7],evento_otras_redes[8]]
                eventos_reporte.insert(j,variable)
                break
    catalogo=ordenar_y_eliminar_duplicados(catalogo,0)
    escritura_archivo(archivo_cat,catalogo)
    escritura_archivo(archivo_dat,eventos_reporte)
    cont_sismos=0
    cont_FF=0
    cont_FC=0
    cont_tel=0
    cont_ev=0
    cont_ruido=0
    cont_indefinido=0
    for i in range(0,len(eventos)):
            if(eventos[i][2]=="SISMO"):
                cont_sismos=cont_sismos+1
            if(eventos[i][2]=="FF"or eventos[i][2]=="REVISION" ):
                cont_FF=cont_FF+1
            if(eventos[i][2]=="FC"):
                cont_FC=cont_FC+1
            if(eventos[i][2]=="TELESISMO"):
                cont_tel=cont_tel+1
            if(eventos[i][2]=="Evento_local" or eventos[i][2]=="CONTROL" ):
                cont_ev=cont_ev+1
            if(eventos[i][2]=="Ruido"):
                cont_ruido=cont_ruido+1
            if(eventos[i][2]=="INDEFINIDO"):
                cont_indefinido=cont_indefinido+1    

    with open(archivo_res, 'w', newline='') as archivo_grabar:
                escritor_csv = csv.writer(archivo_grabar,delimiter=';')
                escritor_csv.writerow(["SISMO",     "FF",   "FC","TELESISMOS","Local_CONTROL","INDEFINIDO","Ruido"])
                escritor_csv.writerow([cont_sismos,cont_FF,cont_FC,cont_tel,cont_ev,      cont_indefinido,cont_ruido])
    tree = ET.ElementTree(root)
        # Escribir el archivo XML
    tree.write(archivo_xml, encoding="utf-8", xml_declaration=True)
    return catalogo,eventos_reporte



def ordenar_y_eliminar_duplicados(catalogo, indice, bandera=True):
    """
    Ordena una lista de listas o tuplas y elimina duplicados.

    Args:
        catalogo: Lista de listas o tuplas donde la primera sublista contiene los encabezados.
        indice: Índice de la columna por la que se ordenará.
        bandera:   True es catalogo, False es cualquier archivo
    Returns:
        Lista ordenada y sin duplicados.
    """    
    
    if bandera:
        
        if not catalogo or not isinstance(catalogo, list):
            raise ValueError("El catálogo debe ser una lista no vacía.")

        encabezado = catalogo[0]
        datos = [fila for fila in catalogo[1:] if fila]  # Eliminar filas vacías

        # Validar índice
        if not all(len(fila) > indice for fila in datos):
            raise IndexError(f"El índice {indice} es inválido para algunas filas.")

    else:
        
        datos=catalogo

    # Eliminar duplicados
    vistos = set()
    sin_duplicados = []
    for fila in datos:
        clave = tuple(fila)  # Convertimos a tupla para poder agregar al set
        if clave not in vistos:
            vistos.add(clave)
            sin_duplicados.append(fila)

    # Ordenar por el índice especificado, convirtiendo el elemento a str temporalmente
    sin_duplicados.sort(key=lambda x: x[indice])
    if bandera:    
        # Agregar el encabezado
        sin_duplicados.insert(0, encabezado)
    else:
        for i,evento in enumerate(sin_duplicados):
            evento[0]=i+1

    return sin_duplicados




def guardar_intento(archivo,directorio,responsables,procesamiento):
    #Archivo ---   para la lectura del formato para llamar a lectura_rsa
    #directorio  - 
    #responsables
    #procesamiento 
    resultado = lectura_rsa(archivo, directorio, responsables)
    evento_auxiliar = [str(len(procesamiento) - 1)]
    ahora = datetime.now()
    fecha_formateada = ahora.strftime("%Y-%m-%d %H:%M:%S")
    evento_auxiliar.append(fecha_formateada)
    if resultado is None:
        evento_auxiliar.append('Fallido')
    elif resultado ==1:
        evento_auxiliar.append('Fallido')
        evento_auxiliar.append('Error de conversion')
    
    else:
        auxiliar = [9, 15, 7, 8, 10]
        for k in auxiliar:
            evento_auxiliar.append(str(resultado[0][k]))
        evento_auxiliar.append(resultado[1])
    procesamiento.append(evento_auxiliar)
    return procesamiento


def verificar_coincidencias(matriz, vector):
    """
    Verifica si la combinación de horas y minutos (hhmm) del segundo elemento del vector
    se repite en los segundos elementos de las filas de la matriz, excluyendo el vector mismo.
    Muestra un mensaje de advertencia con las coincidencias encontradas.

    Parámetros:
    matriz (lista de listas): La matriz en la que buscar coincidencias.
    vector (lista): El vector con el elemento a verificar.

    Retorno:
    None
    """
    # Obtenemos el segundo elemento del vector y extraemos horas y minutos
    fecha_vector = vector[1]
    horas_minutos_vector = fecha_vector[9:13]  # Extrae el componente hhmm de AAMMDD_hhmmss.sis
    # Lista para almacenar los valores completos que coinciden
    coincidencias = []

    # Iteramos sobre cada fila de la matriz
    for fila in matriz:
        # Obtenemos el segundo elemento de la fila y extraemos horas y minutos
        fecha_fila = fila[1]
        horas_minutos_fila = fecha_fila[9:13]

        # Verificamos si las horas y minutos coinciden y no es la misma fila
        if horas_minutos_vector == horas_minutos_fila and fila != vector:
            # Si coinciden, agregamos el valor completo a las coincidencias
            coincidencias.append(fecha_fila)

    # Si hay coincidencias, mostramos un mensaje de advertencia
    if coincidencias:
        #app = QApplication(sys.argv)
        mensaje_advertencia = f"Se encontraron coincidencias en horas y minutos:\n{', '.join(coincidencias)}"
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(mensaje_advertencia)
        msg_box.setWindowTitle("Advertencia de Coincidencias de Horas y Minutos")
        msg_box.exec_()


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


def extraer_dia(archivo,responsable,bandera_todo):
            directorios=obtener_directorios(archivo)
            nombre_archivo=directorios["archivo_auxiliar"]
            eventos_auxiliar=lectura_archivo(nombre_archivo)
            if os.path.exists(nombre_archivo):
                pass
            else:
                nombre_archivo=directorios["archivo_csv"]
            lista_eventos=lectura_archivo(nombre_archivo)
            archivo_guardar=directorios["archivo_tiempos"]
            if os.path.exists(archivo_guardar):
                datos_tiempo=lectura_archivo(archivo_guardar)
            else:
                datos_tiempo=[["RSA","12H","","","","","","","",""],["RSA","18H","","","","","","","",""],["RSA","24H","","","","","","","",""]]
                escritura_archivo(archivo_guardar, datos_tiempo)
            if True:
                cont_sismo=[0,0,0]
                cont_indefinido=[0,0,0]
                cont_FC=[0,0,0]
                cont_FF=[0,0,0]
                cont_ruido=[0,0,0]
                cont_local=[0,0,0]
                cont_tele=[0,0,0]
                hora_=[12,18,24]
                for evento_ in lista_eventos:
                    h=int(evento_[1][9:11])
                    if h<12:
                        if evento_[2] == 'SISMO':
                            cont_sismo[0]=cont_sismo[0]+1
                        elif evento_[2] == 'FF':
                            cont_FF[0]=cont_FF[0]+1
                        elif evento_[2] == 'FC':
                            cont_FC[0]=cont_FC[0]+1
                        elif evento_[2] == 'INDEFINIDO':
                            cont_indefinido[0]=cont_indefinido[0]+1
                        elif evento_[2] == 'TELESISMO':
                            cont_tele[0]=cont_tele[0]+1
                        elif evento_[2] == 'Evento_local' or evento_[2] == 'CONTROL':
                            cont_local[0]=cont_local[0]+1
                        else:
                            cont_ruido[0]=cont_ruido[0]+1
                    elif h<18 and h>11:
                        if evento_[2] == 'SISMO':
                            cont_sismo[1]=cont_sismo[1]+1
                        elif evento_[2] == 'FF':
                            cont_FF[1]=cont_FF[1]+1
                        elif evento_[2] == 'FC':
                            cont_FC[1]=cont_FC[1]+1
                        elif evento_[2] == 'INDEFINIDO':
                            cont_indefinido[1]=cont_indefinido[1]+1
                        elif evento_[2] == 'TELESISMO':
                            cont_tele[1]=cont_tele[1]+1
                        elif evento_[2] == 'Evento_local'or evento_[2] == 'CONTROL':
                            cont_local[1]=cont_local[1]+1
                        else:
                            cont_ruido[1]=cont_ruido[1]+1
                    else:
                        if evento_[2] == 'SISMO':
                            cont_sismo[2]=cont_sismo[2]+1
                        elif evento_[2] == 'FF':
                            cont_FF[2]=cont_FF[2]+1
                        elif evento_[2] == 'FC':
                            cont_FC[2]=cont_FC[2]+1
                        elif evento_[2] == 'INDEFINIDO':
                            cont_indefinido[2]=cont_indefinido[2]+1
                        elif evento_[2] == 'TELESISMO':
                            cont_tele[2]=cont_tele[2]+1
                        elif evento_[2] == 'Evento_local'or evento_[2] == 'CONTROL':
                            cont_local[2]=cont_local[2]+1
                        else:
                            cont_ruido[2]=cont_ruido[2]+1
            for i in (0,1,2):
                total=cont_sismo[i]+cont_FF[i]+cont_FC[i]+cont_indefinido[i]+cont_tele[i]+cont_local[i]+cont_ruido[i]
                if(total!=0 and datos_tiempo[i][2]==""):
                    datos_tiempo[i][0]=responsable
                    datos_tiempo[i][1]=str(hora_[i])+"H"
                    datos_tiempo[i][2]="0"
                if datos_tiempo[i][2]!="":
                    datos_tiempo[i][2]=str(total)
                    datos_tiempo[i][3]=str(cont_sismo[i])
                    datos_tiempo[i][4]=str(cont_FF[i])
                    datos_tiempo[i][5]=str(cont_FC[i])
                    datos_tiempo[i][6]=str(cont_indefinido[i])
                    datos_tiempo[i][7]=str(cont_tele[i])
                    datos_tiempo[i][8]=str(cont_local[i])
                    datos_tiempo[i][9]=str(cont_ruido[i])
            escritura_archivo(archivo_guardar, datos_tiempo)
            eventos=lectura_archivo(directorios['archivo_csv'])
            maximo=len(eventos)
            ventana = VentanaProgreso("Extrayendo eventos...", maximo)
            if bandera_todo:
                eventos=[]
            solo_eventos = [fila[1] for fila in eventos]
            for i,evento_auxiliar in enumerate(eventos_auxiliar):
                ventana.actualizar(i + 1)
                evento=extraccion(evento_auxiliar,solo_eventos,archivo,False)
                if evento!=None:
                    eventos.append(evento)
            eventos=ordenar_y_eliminar_duplicados(eventos,1,False)
            escritura_archivo(directorios['archivo_csv'],eventos)
            ventana.cerrar()

def extraccion(evento_auxiliar,solo_eventos,archivo,bandera_forzar):
    """
    evento_auxiliar              linea de lectura del archivo AAMMDD_aux.csv 
    solo_eventos                 Todos los eventos procesados del día, se puede extraer un evento pasando solo_eventos=[]
    archivo:                     archivo con formato ..\DIA\AAMMDD000000
    bandera_forzar               bandera para forzar la lectura, así esté en el archivo AAMMDD000000.csv
    """
    
    estaciones_analogicas=lectura_archivo(os.path.join(ruta_datos,'analogicas.csv'))
    directorios = obtener_directorios(archivo)
    parametros = parametros_estaciones()
    evento,tipo_evento,t_inicio, t_final = evento_auxiliar[1],evento_auxiliar[2], float(evento_auxiliar[4]), float(evento_auxiliar[5])
    print('Extrayendo ',evento)
    fecha_ = obtencion_hora(archivo)
    t_ini = fecha_ + t_inicio
    t_fin = fecha_ + t_final
    numero_de_muestras=int((t_fin-t_ini)*64)
    nombre_sis = os.path.join(directorios['Directorio_dia'] , t_ini.strftime('%Y%m%d_%H%M%S.sis'))
    hora_formateada = t_ini.strftime(" %H: %M: %S")
    if t_inicio > t_final:
        QMessageBox.about(None, "Advertencia", "Hora incorrecta: Tiempo de inicio mayor a final")
        return
    if evento not in solo_eventos:
        if len(evento_auxiliar)>6:
            estaciones=evento_auxiliar[7]
            lista_estaciones_aportantes =estaciones.split()
        else:
            eventos=lectura_archivo(directorios['archivo_csv'])
            lista_estaciones_aportantes=[]
            for evento in eventos:
                if evento[1]==evento_auxiliar[1]:
                    break
            for estacion_aportante in evento[3:]:
                if estacion_aportante!='-':
                    lista_estaciones_aportantes.append(estacion_aportante)
            
        estaciones_eventos_total=[]
        for estaciones_aportantes in lista_estaciones_aportantes:
            codigo_estacion=estaciones_aportantes[:4]
            indice=parametros['CODIGO'].index(codigo_estacion)
            estaciones_eventos_total.append(indice)
    else:
        return 
    if tipo_evento != "Ruido":
        sismo_extraido=[]
        estaciones_con_senial=[]
        for numero_estacion,estacion_habilitada in enumerate(parametros['HAB_CANAL']):
            if  estacion_habilitada=='1':
                archivo_mseed_dia=os.path.join(directorios['Directorio_registros'],parametros['CODIGO'][numero_estacion]+directorios['sufijo_mseed'])
                if os.path.exists(archivo_mseed_dia):
                    auxiliar=(numero_estacion,parametros['NOMBRE'][numero_estacion],parametros['CODIGO'][numero_estacion])
                    estaciones_con_senial.append(auxiliar)

        ####################################################
        ####Estraccion de eventos en mseed por estación.
        ####################################################
        for estacion_con_senial in estaciones_con_senial:
            numero_estacion=int(estacion_con_senial[0])
            componente=int(parametros['COMPONENTE'][numero_estacion])-1
            archivo_mseed_dia=os.path.join(directorios['Directorio_registros'],parametros['CODIGO'][numero_estacion]+directorios['sufijo_mseed'])
            stcanal = read(archivo_mseed_dia, format="MSEED", starttime=t_ini, endtime=t_fin, nearest_sample=False)
            if len(stcanal)==0:
                    continue
            # Aplica corrección de polaridad si es necesario
            if parametros['POLARIDAD'][numero_estacion] == 'N':
                stcanal[componente].data *= -1
            # Guardar archivo .mseed
            nombre_mseed = os.path.join(directorios['Directorio_eventos'] ,parametros['CODIGO'][numero_estacion] + t_ini.strftime('_%Y%m%d_%H%M%S.mseed'))
            stcanal.write(nombre_mseed, format='MSEED', encoding='STEIM1', reclen=512)
            print('Grabando:',nombre_mseed)
  

        ####################################################
        ####Converesión de las estaciones configuradas en estaciones analógicas
        ####para el proceso V2.
        ####################################################
        for estacion_analogica in estaciones_analogicas:
            if estacion_analogica[0]=='ESTACION':
                continue
            numero_estacion=int(estacion_analogica[0])
            componente=int(parametros['COMPONENTE'][numero_estacion])-1
            if numero_estacion not in estaciones_eventos_total:
                stcanal=[]
                sis_extraido = np.array([], dtype=np.int32)
            else:
                nombre_mseed = os.path.join(directorios['Directorio_eventos'] ,parametros['CODIGO'][numero_estacion] + t_ini.strftime('_%Y%m%d_%H%M%S.mseed'))
                stcanal.detrend("demean")
                if  os.path.exists(nombre_mseed):
                    stcanal = read(nombre_mseed)
                    stcanal.detrend("demean")
                else:
                    continue
                stcanal[componente].data = stcanal[componente].data.astype('int32')
                sis_extraido = stcanal[componente].data
                muestras = stcanal[componente].stats.sampling_rate
                if muestras!=64:
                    sis_extraido = signal.resample(sis_extraido, numero_de_muestras)
                    sis_extraido = np.rint(sis_extraido).astype(np.int32)
                # Forzar tamaño correcto
                if sis_extraido.size != numero_de_muestras:
                    if sis_extraido.size > numero_de_muestras:
                        sis_extraido = sis_extraido[:numero_de_muestras]
                    else:
                        faltantes = numero_de_muestras - sis_extraido.size
                        sis_extraido = np.pad(sis_extraido, (0, faltantes), mode='constant')
            sismo_extraido.append(sis_extraido)
        # Crear archivo .sis si es evento sísmico
        if tipo_evento == "SISMO":
            archivo_cabecera = os.path.join(directorios['Directorio_trabajo'],"cabecera_sismo")
            try:
                with open(archivo_cabecera, 'rb') as archivo_leer:
                    cabecera = b''
                    contador = 0
                    while contador < 2:
                        marcador = archivo_leer.read(2)
                        if marcador == b'\x08\x00':
                            cabecera_0 = archivo_leer.read(2)
                            num_caracteres = struct.unpack("<H", cabecera_0)[0]
                            archivo_leer.read(num_caracteres)
                            contador += 1
                    puntero = archivo_leer.tell()
                    archivo_leer.seek(0)
                    cabecera = archivo_leer.read(puntero) + b'\x08\x00\x0B\x00' + hora_formateada.encode('utf-8') + archivo_leer.read()
                with open(nombre_sis, 'wb') as archivo_escribir:
                    archivo_escribir.write(cabecera)
                    segundo_ = t_ini.hour * 3600 + t_ini.minute * 60 + t_ini.second
                    segundo_string = f'{segundo_:05}'
                    archivo_escribir.write(segundo_string.encode())
                    k = 0
                    for n in range( numero_de_muestras):
                        if k == 0:
                            archivo_escribir.write(
                                b'\x02\x20\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00'
                            )
                        k += 1
                        if k == 64:
                            k = 0
                        for i,estacion_analogica in enumerate(estaciones_analogicas):
                            if estacion_analogica[0]=='ESTACION':
                                continue
                            m=i-1
                            estacion=int(estacion_analogica[0])
                            if parametros['HAB_CANAL'][estacion] == "1" and sismo_extraido[m].size>0:
                                valor = int(sismo_extraido[m][n])
                            else:
                                valor=0




                            #if parametros['BITS'][estacion]=='20':
                                #valor= int(valor/16)
                            try:
                                archivo_escribir.write(valor.to_bytes(2, byteorder='little', signed=True))
                            except OverflowError:
                                print(valor)
                                valor=0
                                archivo_escribir.write(valor.to_bytes(2, byteorder='little', signed=True))
            except FileNotFoundError:
                print("Cabecera binaria no encontrada:", archivo_cabecera)
    if evento not in solo_eventos:
        estaciones_eventos_total=[]
        lista_guiones = ['-'] * 101
        if lista_estaciones_aportantes != []:#if tipo_evento != "Ruido":
            for estacion_aportante in lista_estaciones_aportantes or bandera_forzar:
                codigo_estacion=estacion_aportante[:4]
                indice=parametros['CODIGO'].index(codigo_estacion)
                nombre_mseed = os.path.join(directorios['Directorio_eventos'] ,parametros['CODIGO'][indice] + t_ini.strftime('_%Y%m%d_%H%M%S.mseed'))
                lista_guiones[indice]=estacion_aportante
        evento=list(evento_auxiliar[:3])+lista_guiones
    #input("Enter:")
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
    print("Cargar evento:",parametro)
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


    
def cargar_dia(archivo_csv):
    """
    Carga el dia para procesamiento o reporte
    Args:
        archivo_csv: Nombre del archivo para escoger el dian ia con formato AAMMDDhhmmss.
    """
    directorio_trabajo=extraer_hasta_directorio(archivo_csv,'DIA')
    archivo=referencia_directorio_completa(archivo_csv)
    directorios=obtener_directorios(archivo)
    if not(os.path.exists(directorios['Directorio_base'])):
        return [],[],[],[],[],[],[],[]
    eventos_reporte=[['0',"Fecha; Hora (UTC)","Evento","Magn.","Prof.(km)","Lat.","Long.","Ubicación"]]
    catalogo=[["Id","anio","mes","dia","hora","min","seg","lat","long","prof","rms","e-x","e-y","e-0","e-z","Mag","Tipo Mag","Fuente","ruta","Ubicacion"]]
    eventos=[]
    vector=[]
    canales_eventos_dia=[]

    contador_n_canales=[[0,0,0,0,0,0],[0,0,0,0,0,0],[0,0,0,0,0,0]]#Tupla que contiene el número de estaciones por evento sísmico.
    root = ET.Element("sismo")
    lista_eventos=lectura_archivo(archivo_csv)
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
    if os.path.exists(directorios['archivo_catalogo']):
            catalogo_existente=lectura_archivo(directorios['archivo_catalogo'])
            if catalogo_existente!=None:
                for evento_existente in catalogo_existente:
                    if evento_existente[0]=='Id':
                        continue
                    if evento_existente[0][-2:]!='00':
                        for n_evento,evento in enumerate(catalogo):
                            if evento==[]:
                                continue
                            if evento[0]=='Id':
                                continue
                            if int(evento_existente[0])<int(evento[0]):
                                catalogo.insert(n_evento,evento_existente)
                                break
                catalogo=ordenar_y_eliminar_duplicados(catalogo,0)
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
        if(total!=0):
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
    print(lectura)
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
            print(partes)
            latitud = float(partes[0].replace('°', '')) * (-1 if partes[1] == 'S' else 1)
            longitud = float(partes[2].replace('°', '')) * (-1 if partes[3] == 'W' else 1)
            print(latitud, longitud)
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
    print("Revisando en dicrectorio ",directorio_base )
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






def referencia_directorio_completa__(archivo):
    archivo_base = Path(archivo).name      # Esto aísla el nombre del archivo
    extension = Path(archivo).suffix  # Esto obtiene la extensión (incluye el punto .)
    if extension=='.sis':
        archivo_base=archivo_base[:8]+'000000'
    elif extension=='.csv':
        archivo_base=archivo_base[:8]+'000000'
    elif extension=='.mseed':
        archivo_base=archivo_base[4:12]+'000000'        
    elif extension=='.pdf':
        archivo_base=archivo_base[:8]+'000000'
    else:
        pass
    directorio_trabajo=extraer_hasta_directorio(archivo, 'DIA')
    ruta_archivo = os.path.join(directorio_trabajo, archivo_base)
    return ruta_archivo


def ejecutar_kw2v1(ruta_evt, usar_interactivo=False):
    ruta_evt = Path(ruta_evt)
    if not ruta_evt.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_evt}")
    
    comando = ["O:\\KINETRICS\\KW2V1.EXE", str(ruta_evt.name)]
    if usar_interactivo:
        comando.append("-S")  # modo de entrada de parámetros

    proceso = subprocess.run(
        comando,
        cwd=ruta_evt.parent,  # Directorio de trabajo donde está el EVT
        capture_output=True,
        text=True,
        shell=True
    )

    print("Salida estándar:\n", proceso.stdout)
    print("Errores:\n", proceso.stderr)
    if proceso.returncode == 0:
        print("Conversión exitosa.")
    else:
        print(f"Error al ejecutar KW2V1. Código: {proceso.returncode}")
        
        
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

def diagnostico_memoria(etiqueta=''):
    proceso = psutil.Process(os.getpid())
    uso = proceso.memory_info().rss / 1024 / 1024  # MB
    print(f"[{etiqueta}] Uso de memoria: {uso:.2f} MB")