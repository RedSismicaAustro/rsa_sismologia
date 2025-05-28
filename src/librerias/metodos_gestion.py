from obspy import UTCDateTime
import os
import csv
import json
import obspy
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox
import sys



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
    estaciones_=[]

    RAIZ_PROYECTO = os.path.dirname(os.path.abspath(__file__))
    RAIZ_PROYECTO=os.path.join(RAIZ_PROYECTO, "..","..")
    ruta_csv =  os.path.join(RAIZ_PROYECTO, "datos", "estaciones.csv")
    ruta_csv = os.path.abspath(ruta_csv)

    with open(ruta_csv,newline='') as f:
            datos=csv.reader(f,delimiter=';',quotechar=';')
            for r in datos:
                estaciones_.append(r)
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
    total_est=len(estaciones_)
    for i in range(0, total_est):
            if(i!=0):
                nombre_canal_total_.append(estaciones_[i][1])
                nombre_canal.append(estaciones_[i][2])
                tipo_sensor.append(estaciones_[i][3])
                n_canales_.append(estaciones_[i][4])
                hab_canal.append(estaciones_[i][5])
                componente_canal.append(estaciones_[i][6])
                grafico_.append(estaciones_[i][7])
                hab_plt.append(estaciones_[i][8])
                gan_plt.append(estaciones_[i][9])
                ganancia.append(estaciones_[i][10])
                diez_plt.append(estaciones_[i][11])
                factor_mult.append(estaciones_[i][12])
                calidad_.append(estaciones_[i][13])
                ubicacion_.append(estaciones_[i][14])
                tipo_canal.append(estaciones_[i][15])
                red_.append(estaciones_[i][16])
                muestreo_.append(estaciones_[i][17])
                longitud_.append(estaciones_[i][18])
                latitud_.append(estaciones_[i][19])
                altura_.append(estaciones_[i][20])
                ruido_.append(int(estaciones_[i][21]))
                numero_est.append(int(estaciones_[i][0]))
                filtro_.append(estaciones_[i][22])
                polaridad_.append(estaciones_[i][23])
                reserva_1.append(estaciones_[i][24])              

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



def obtener_directorios(archivo):
    #archivo:   archivo de evento con el formato AAMMDDhhmmss.sis,AAMMDD_hhmmss.sis,AAMMDDhhmmss o AAMMDDhhmmss.csv
    #EN el formato AAMMDDhhmmss tiene que tener el directorio de trabajo.
    bandera_extension=1
    if archivo=='  ':
        return
    x = archivo.find(".sis")
    if x!=-1:
        archivo=archivo[0:x]
        bandera_extension=0
    y = archivo.find(".csv")
    if y!=-1:
        archivo=archivo[0:y]
        bandera_extension=0
    if archivo[-7]=='_':
        archivo=archivo[0:-7]+archivo[-6:x]
    aux_0=len(archivo)
    if aux_0==12 or bandera_extension:
        anio='20'+archivo[-12:-10]
        directorio_trabajo=archivo[:-12]
    else:
        anio=archivo[-14:-10]
        directorio_trabajo=archivo[:-14]
    mes=archivo[-10:-8]
    dia=archivo[-8:-6]
    hora=archivo[-6:-4]
    minuto=archivo[-4:-2]
    segundo=archivo[-2:]
    directorio_base=directorio_trabajo+anio+'/'+anio+'_'+mes+'/'+anio+'_'+mes+'_'+dia

#    if int(archivo[-12:-10])<95:
#        directorio_mes=archivo[0:aux_0-12]+"20"+archivo[aux_0-12:aux_0-10]+"/20"+archivo[aux_0-12:aux_0-10]+"_"+archivo[aux_0-10:aux_0-8]+"/"
#        directorio_base=directorio_mes+"20"+archivo[aux_0-12:aux_0-10]+"_"+archivo[aux_0-10:aux_0-8]+"_"+archivo[aux_0-8:aux_0-6]
#    else:
#        directorio_mes=archivo[0:aux_0-12]+"19"+archivo[aux_0-12:aux_0-10]+"/19"+archivo[aux_0-12:aux_0-10]+"_"+archivo[aux_0-10:aux_0-8]+"/"
#        directorio_base=directorio_mes+"19"+archivo[aux_0-12:aux_0-10]+"_"+archivo[aux_0-10:aux_0-8]+"_"+archivo[aux_0-8:aux_0-6]
        #directorio_base                                      

    directorio_dia=os.path.join(directorio_base,'dia')
    directorio_eventos=os.path.join(directorio_base,'mseed','eventos')             
    directorio_registros=os.path.join(directorio_base,'mseed','registros')   
    directorio_reportes=directorio_base+"/reportes"           
    directorio_fast=directorio_base+"/fastHypo"               
    directorio_procesamiento=directorio_base+"/procesamiento" 
    directorio_acelerogramas=directorio_base+"/acelerogramas" 
    archivo_estaciones=directorio_base+'/'+archivo[-12:-6]+'_estaciones.csv'
    archivo_comportamiento=directorio_base+'/'+archivo[-12:-6]+'_est.csv'
    archivo_csv=directorio_base+'/'+archivo[-12:-6]+'000000.csv'
    archivo_rep=directorio_base+'/'+archivo[-12:-6]+'000000_rep.csv'
    archivo_cat=directorio_base+'/'+archivo[-12:-6]+'000000_cat.csv'
    archivo_xml=directorio_base+'/'+archivo[-12:-6]+'000000.xml'
    archivo_res=directorio_base+'/'+archivo[-12:-6]+'000000_res.csv'
    archivo_reporte_dia=directorio_base+'/'+archivo[-12:-6]+'000000_rep.pdf'
    archivo_resp=directorio_reportes+'/'+archivo[-12:-6]+'_resp.csv'
    archivo_tiempos=directorio_reportes+'/'+archivo[-12:-6]+'_tiempos.csv'
    archivo_marcas=directorio_base+'/'+archivo[-12:]+'_marcas.json'
    archivo_auxiliar=directorio_base+'/'+archivo[-12:-6]+'_aux.csv'
    archivo_procesamiento=directorio_procesamiento+'/'+archivo[-12:-6]+'_'+archivo[-6:]+'_proc.csv'
    sufijo_mseed='_'+anio+archivo[-10:-6]+'_'+archivo[-6:]+'.mseed'
    archivo_referencia=archivo[-12:]
    return{'Directorio_base':directorio_base,                       #[0] Directorio base 
           'Directorio_dia':directorio_dia,                         #[1] Directorio dia
           'Directorio_eventos':directorio_eventos,                 #[2] Directorio eventos
           'Directorio_registros':directorio_registros,             #[3] Directorio registros
           'Directorio_reportes':directorio_reportes,               #[4] Directorio reportes
           'Directorio_fastHypo':directorio_fast,                   #[5] Directorio fastHypo
           'Directorio_procesamiento':directorio_procesamiento,     #[6] Directorio procesamiento
           'Directorio_acelerogramas':directorio_acelerogramas,     #[7] Directorio acelerogramas
           'archivo_estaciones':archivo_estaciones,
           'archivo_csv':archivo_csv,
           'archivo_reporte':archivo_rep,
           'archivo_catalogo':archivo_cat,
           'archivo_xml':archivo_xml,
           'archivo_resumen':archivo_res,
           'archivo_responsables':archivo_resp,
           'archivo_tiempos':archivo_tiempos,
           'archivo_marcas':archivo_marcas,
           'archivo_auxiliar':archivo_auxiliar,
           'sufijo_mseed':sufijo_mseed,
           'archivo_referencia':archivo_referencia,
           'archivo_procesamiento':archivo_procesamiento,
           'archivo_comportamiento':archivo_comportamiento,
           'archivo_reporte_dia':archivo_reporte_dia
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

from PyQt5.QtWidgets import QApplication, QMessageBox
import sys

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
    app = QApplication(sys.argv)
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

