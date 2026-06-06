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
from PyQt5.QtWidgets import QMessageBox
import matplotlib
matplotlib.use('Qt5Agg')  # Asegúrate de que esto está antes de importar matplotlib.pyplot
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator    
import subprocess
from obspy import Trace, Stream
from datetime import datetime, timedelta
import sys
import os
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

# metodos_rsa.py (archivo puente temporal)

#from rsa_io import leer_mseed,conversion_mseed,lectura_resumen,lectura_archivo,escritura_archivo,copiar_archivos,num_reportes,Guardar_dia,extraer_hasta_directorio,lectura_eventos
#from rsa_dominio import correccion,calidad_estacion,obtenerTraza,punto_fijo_a_punto_flotante,convertir_lista,decimal_a_hexadecimal,obtener_caracter_hexadecimal,intervalo_reporte
#from rsa_procesamiento import lectura_rsa,archivos_fast,verificar_coincidencias,guardar_intento,guardar_informacion_diaria,ordenar_y_eliminar_duplicados,extraer_dia,espectro_respuesta
#from rsa_utilidades import extraccion,codigos,loc_cabecera,binario_a_mseed,referencia_directorio_completa,ubicacion,agregar_evento,obtener_datos_reporte,generar_directorios_unidades_basicas,extraccion_dato

#from rsa_io import *
#from rsa_dominio import *
#from rsa_procesamiento import *

from rsa_io import leer_mseed,lectura_archivo
from rsa_procesamiento import lectura_rsa,ordenar_y_eliminar_duplicados
from metodos_gestion import parametros_estaciones,obtener_directorios
from rsa_utilidades import agregar_evento,ubicacion,extraccion_dato



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

