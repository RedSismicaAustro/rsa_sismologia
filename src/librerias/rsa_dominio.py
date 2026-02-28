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








import matplotlib
matplotlib.use('Qt5Agg')  # Asegúrate de que esto está antes de importar matplotlib.pyplot
  
from obspy import UTCDateTime, Trace
from datetime import  timedelta
import sys
import os


import copy
import numpy as np


import calendar

from metodos_gestion import parametros_estaciones

# metodos_rsa.py (archivo puente temporal)

from .rsa_io import *
from .rsa_dominio import *
from .rsa_procesamiento import *


import sys
import os



IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19


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


def punto_fijo_a_punto_flotante(data):
    # Convertir los datos en formato de bytes a un número entero sin signo de 32 bits
    num = int.from_bytes(data, byteorder='big', signed=False)
    # Convertir el número entero sin signo a un número entero con signo de 32 bits
    if num >= (1 << 31):
        num -= (1 << 32)
    # Dividir el número entero con signo por 2^23 para obtener el valor en punto flotante correspondiente
    valor_punto_flotante = num / (2 ** 23)
    return valor_punto_flotante


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

def decimal_a_hexadecimal(decimal):
    hexadecimal = ""
    while decimal > 0:
        residuo = decimal % 16
        verdadero_caracter = obtener_caracter_hexadecimal(residuo)
        hexadecimal = verdadero_caracter + hexadecimal
        decimal = int(decimal / 16)
    return hexadecimal


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




