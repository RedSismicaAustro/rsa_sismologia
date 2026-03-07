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
from metodos_gestion import obtencion_hora,parametros_estaciones,obtener_directorios,VentanaProgreso
import pandas as pd

# metodos_rsa.py (archivo puente temporal)

from rsa_io import leer_mseed,conversion_mseed,lectura_resumen,lectura_archivo,escritura_archivo,copiar_archivos,num_reportes
from rsa_dominio import *
from rsa_procesamiento import *
from metodos_rsa import extraccion

IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19

def lectura_rsa(archivo,directorio_trabajo,usuario):
#  Mètodo para obtebner la información completa del sismo
#  archivo es el nombre del archivo .sis generado por el registro continuo sin el .sis
#  archivo_rsa es el archivo genrardo por el fasthypo con extencion .rsa generada a partir del archivo.
#  usuario es para tomar información del sistema o de procesamiento, cuaNdo el valor es '', toma del sistema y si no toma de procesamiento asignando los valores 
#   del drive adecuado en las computadoras de procesamiento.
    
    directorios=obtener_directorios(os.path.join(directorio_trabajo,archivo))    
    eventos=lectura_archivo(directorios['archivo_csv'])
    archivo_procesamiento=verificar_coincidencias(eventos,archivo,archivos_fast(archivo,directorio_trabajo,usuario))
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

def archivos_fast(evento, dir_trabajo, usuario, retornar_validaciones=False):
    """
    Regla FINAL:
        - sis y fas → SIEMPRE minuto exacto
        - FASTHYPO (rsa, Phase, L, P, S):
              * si .fas existe y .rsa NO → minuto +1
              * si .fas existe y .rsa SI → minuto exacto
              * si .fas NO → minuto exacto

    Siempre retorna las 7 rutas, existan o no.
    """

    # ------------------------------------------------------------
    # 1) Carpetas base
    # ------------------------------------------------------------
    info = obtener_directorios(evento)
    dir_dia  = os.path.join(dir_trabajo, info['Directorio_dia'])
    dir_fast = os.path.join(dir_trabajo, info['Directorio_fastHypo'])

    # Virtual (usuario)
    if usuario:
        csv_path = os.path.join(ruta_datos, "responsables.csv")
        for fila in lectura_archivo(csv_path):
            if fila and fila[0].strip() == usuario.strip():
                dir_dia, dir_fast = fila[1], fila[2]
                break

    # ------------------------------------------------------------
    # 2) Parseo del nombre base
    # ------------------------------------------------------------
    base = evento[:-4]

    if len(base) == 13:      # AAMMDD_hhmmss
        yy = 2000 + int(base[:2])
        mm = base[2:4]
        dd = base[4:6]
        hh = base[7:9]
        minu = base[9:11]
        ss  = base[11:13]
        sisfas_base = base
    else:                    # AAAAMMDD_hhmmss
        yy = int(base[:4])
        mm = base[4:6]
        dd = base[6:8]
        hh = base[9:11]
        minu = base[11:13]
        ss  = base[13:15]
        sisfas_base = base if usuario == '' else base[2:]

    # ------------------------------------------------------------
    # 3) Archivos SIS y FAS (siempre exactos)
    # ------------------------------------------------------------
    archivo_sis = os.path.join(dir_dia, f"{sisfas_base}.sis")
    archivo_fas = os.path.join(dir_dia, f"{sisfas_base}.fas")

    fas_existe = os.path.exists(archivo_fas)

    # ------------------------------------------------------------
    # 4) Determinar minuto FASTHYPO
    # ------------------------------------------------------------
    # RSA exacto
    rsa_nom_exacto = f"{mm}{dd}{hh}{minu}.rsa"
    archivo_rsa_exacto = os.path.join(dir_fast, rsa_nom_exacto)
    rsa_existe = os.path.exists(archivo_rsa_exacto)

    # Aplicar regla
    if fas_existe and not rsa_existe:
        # Incrementar el minuto en 1
        dt = datetime(yy, int(mm), int(dd), int(hh), int(minu), int(ss)) + timedelta(minutes=1)
        mm, dd, hh, minu = dt.strftime("%m %d %H %M").split()

    # ------------------------------------------------------------
    # 5) Construir archivos FASTHYPO con el minuto definitivo
    # ------------------------------------------------------------
    rsa_nom = f"{mm}{dd}{hh}{minu}.rsa"
    archivo_rsa = os.path.join(dir_fast, rsa_nom)

    phase_nom = f"Phase{dd}{hh[0]}.{hh[1]}{minu}"
    archivo_phase = os.path.join(dir_fast, phase_nom)

    base_lp = f"{mm}{dd}{hh}.{minu}"
    archivo_L = os.path.join(dir_fast, base_lp + "L")
    archivo_P = os.path.join(dir_fast, base_lp + "P")
    archivo_S = os.path.join(dir_fast, base_lp + "S")

    # ------------------------------------------------------------
    # 6) Retorno final
    # ------------------------------------------------------------
    rutas = [archivo_sis, archivo_fas, archivo_rsa,
             archivo_phase, archivo_L, archivo_P, archivo_S]

    etiquetas = ['.sis', '.fas', '.rsa', 'Phase', '.L', '.P', '.S']
    existe = {etq: os.path.isfile(ruta) for etq, ruta in zip(etiquetas, rutas)}
    faltantes = [etq for etq, ok in existe.items() if not ok]
    if retornar_validaciones:
        return rutas, existe, faltantes
    return rutas

def verificar_coincidencias(eventos, evento_procesar, archivos_fast):
    contador = 0
    sufijo = ['', 'a', 'b', 'c']
    clave_minuto = Path(evento_procesar).stem.replace('_', '')[:12]
    for evento in eventos:
        tipo_evento = evento[2]
        if tipo_evento != 'SISMO':
            continue
        if Path(evento[1]).stem.replace('_', '')[:12] == clave_minuto:
            if evento[1] == evento_procesar:
                break
            contador += 1

    if contador >= len(sufijo):
        contador = len(sufijo) - 1
    suf = sufijo[contador]
    if not suf:
        return archivos_fast  # sin cambios para el primero del minuto

    # .sis (0) y .fas (1) NO cambian; aplicar sufijo al resto
    # RSA (2): antes de la extensión .rsa
    if archivos_fast[2].lower().endswith('.rsa'):
        archivos_fast[2] = archivos_fast[2][:-4] + suf + '.rsa'

    # Phase (3) y L/P/S (4..6): agregar sufijo al final del nombre
    for i in range(3, 7):
        if archivos_fast[i]:
            archivos_fast[i] = archivos_fast[i] + suf
    return archivos_fast

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


def extraer_dia(archivo, responsable, bandera_todo):
    """
    Procesa el día indicado por 'archivo':
      - Selecciona el archivo fuente (AAAAMMDD_aux.csv si existe, caso contrario AAAAMMDD000000.csv)
      - Lee eventos y actualiza los conteos por tramos (0–11, 12–17, 18–23)
      - Actualiza/crea archivo de tiempos (archivo_tiempos)
      - Recorre eventos_auxiliar, ejecuta 'extraccion' y consolida en el CSV principal
    Asume que todos los archivos son generados por el sistema (sin cabeceras y con formato estable).
    """
    # ----------------------------------------------------------------------
    # 1) Selección de archivo fuente y lecturas base
    # ----------------------------------------------------------------------
    print("Entro a extraer dia")
    directorios = obtener_directorios(archivo)

    # Elegimos primero el archivo correcto y recién luego leemos (evita desfasajes)
    nombre_archivo = directorios["archivo_auxiliar"]
    if not os.path.exists(nombre_archivo):
        nombre_archivo = directorios["archivo_csv"]

    # Lecturas de listas (sin cabeceras, según tu pipeline)
    lista_eventos = lectura_archivo(nombre_archivo)         # base para conteos por tramo
    eventos_auxiliar = lectura_archivo(nombre_archivo)      # base para iterar en extraccion()

    # Archivo donde se guardan conteos
    archivo_guardar = directorios["archivo_tiempos"]

    # Si existe, se usa; caso contrario se crea con 3 filas (12H, 18H, 24H)
    if os.path.exists(archivo_guardar):
        datos_tiempo = lectura_archivo(archivo_guardar)
    else:
        datos_tiempo = [
            ["RSA", "12H", "0", "0", "0", "0", "0", "0", "0", "0"],
            ["RSA", "18H", "0", "0", "0", "0", "0", "0", "0", "0"],
            ["RSA", "24H", "0", "0", "0", "0", "0", "0", "0", "0"],
        ]
        escritura_archivo(archivo_guardar, datos_tiempo)

    # ----------------------------------------------------------------------
    # 2) Conteos por tramo y por tipo de evento (sin validaciones adicionales)
    #    Tramos: 0 = 00–11, 1 = 12–17, 2 = 18–23
    # ----------------------------------------------------------------------
    # Estructura: cada clave tiene una lista [c0, c1, c2]
    contadores = {
        "sismo":       [0, 0, 0],
        "ff":          [0, 0, 0],
        "fc":          [0, 0, 0],
        "indefinido":  [0, 0, 0],
        "tele":        [0, 0, 0],
        "local":       [0, 0, 0],
        "ruido":       [0, 0, 0],
    }
    # Etiquetas de salida para datos_tiempo (coinciden con tus columnas)
    etiquetas_tramo = [12, 18, 24]  # Semántico: 12H, 18H, 24H (tramo 18–23)

    # Recorremos eventos tal como vienen (sin encabezados y con formato estable AAAAMMDD_hhmmss)
    for fila in lista_eventos:
        # fila[1] es 'AAAAMMDD_hhmmss' ⇒ la hora está en posiciones [9:11]
        h = int(fila[1][9:11])

        # Tramo según la hora
        if h < 12:
            idx = 0
        elif h < 18:
            idx = 1
        else:
            idx = 2

        # Tipo exacto (según tu pipeline)
        tipo = fila[2]

        # Suma por tipo, con tus equivalencias para 'local'
        if tipo == 'SISMO':
            contadores["sismo"][idx] += 1
        elif tipo == 'FF':
            contadores["ff"][idx] += 1
        elif tipo == 'FC':
            contadores["fc"][idx] += 1
        elif tipo == 'INDEFINIDO':
            contadores["indefinido"][idx] += 1
        elif tipo == 'TELESISMO':
            contadores["tele"][idx] += 1
        elif tipo == 'Evento_local' or tipo == 'CONTROL':
            contadores["local"][idx] += 1
        else:
            contadores["ruido"][idx] += 1

    # ----------------------------------------------------------------------
    # 3) Actualización de datos_tiempo (sin pasos intermedios innecesarios)
    # ----------------------------------------------------------------------
    for i in (0, 1, 2):
        total = (
            contadores["sismo"][i] + contadores["ff"][i] + contadores["fc"][i] +
            contadores["indefinido"][i] + contadores["tele"][i] +
            contadores["local"][i] + contadores["ruido"][i]
        )

        # Si hay eventos en el tramo y la fila está vacía, completar responsable y etiqueta de tramo
        if total != 0 and datos_tiempo[i][2] == "0":
            datos_tiempo[i][0] = responsable
            datos_tiempo[i][1] = f"{etiquetas_tramo[i]}H"

        # Si la fila ya está “abierta” (o la acabamos de abrir), escribir conteos
        if datos_tiempo[i][2] != "" or total != 0:
            datos_tiempo[i][2] = str(total)
            datos_tiempo[i][3] = str(contadores["sismo"][i])
            datos_tiempo[i][4] = str(contadores["ff"][i])
            datos_tiempo[i][5] = str(contadores["fc"][i])
            datos_tiempo[i][6] = str(contadores["indefinido"][i])
            datos_tiempo[i][7] = str(contadores["tele"][i])
            datos_tiempo[i][8] = str(contadores["local"][i])
            datos_tiempo[i][9] = str(contadores["ruido"][i])

    escritura_archivo(archivo_guardar, datos_tiempo)

    # ----------------------------------------------------------------------
    # 4) Extracción y consolidación en el CSV principal
    #     - La barra de progreso usa el tamaño real de 'eventos_auxiliar'
    #     - 'bandera_todo' vacía 'eventos' para reprocesar todo
    # ----------------------------------------------------------------------
    eventos = lectura_archivo(directorios['archivo_csv'])

    # La barra debe reflejar lo que realmente vamos a iterar
    maximo = len(eventos_auxiliar)
    ventana = VentanaProgreso("Extrayendo eventos...", maximo)

    try:
        if bandera_todo:
            eventos = []

        # Lista de claves ya existentes (columna 1 = AAAAMMDD_hhmmss)
        solo_eventos = [fila[1] for fila in eventos]

        for i, evento_auxiliar in enumerate(eventos_auxiliar):
            ventana.actualizar(i + 1)
            evento = extraccion(evento_auxiliar, solo_eventos, archivo, False)
            if evento is not None:
                eventos.append(evento)
                # (Opcional) si quisieras evitar duplicados dentro del mismo ciclo:
                # solo_eventos.append(evento[1])

        # Consolidación final (según tu convención: clave en la columna 1)
        eventos = ordenar_y_eliminar_duplicados(eventos, 1, False)
        escritura_archivo(directorios['archivo_csv'], eventos)

    finally:
        # Asegura cierre de la ventana incluso si hay una excepción intermedia
        ventana.cerrar()






