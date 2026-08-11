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

import numpy as np
import csv
from datetime import datetime, timedelta
import sys
import os
import xml.etree.ElementTree as ET
from metodos_gestion import obtener_directorios,VentanaProgreso
from rsa_io import lectura_archivo,escritura_archivo
from rsa_utilidades import extraccion,codigos,ubicacion,agregar_evento

IDX_INDICE,IDX_ANIO,IDX_MES,IDX_DIA,IDX_HORA,IDX_MINUTO,IDX_SEGUNDO,\
IDX_LATITUD,IDX_LONGITUD,IDX_PROFUNDIDAD,IDX_RMS,IDX_E_X,IDX_E_Y,IDX_E_0,\
IDX_E_Z,IDX_MAGNITUD,IDX_UNIDAD_MAG,\
IDX_FUENTE,IDX_EVENTO,IDX_LUGAR = 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19


def lectura_rsa(archivo, directorio_trabajo, usuario, archivo_rsa_detectado=''):
    # Método para obtener la información completa del sismo
    print("Lectura RSA")

    directorios = obtener_directorios(os.path.join(directorio_trabajo, archivo))
    eventos = lectura_archivo(directorios['archivo_csv'])

    archivos_evento = []
    base_evento = Path(archivo).stem.replace('_', '')

    if len(base_evento) == 12:  # AAMMDDhhmmss
        ss_evento = int(base_evento[10:12])
    else:  # AAAAMMDDhhmmss
        ss_evento = int(base_evento[12:14])

    # Si ya sé cuál RSA cambió en virtual, uso ese como prioritario
    if archivo_rsa_detectado:
        archivos_evento = archivos_fast(archivo, directorio_trabajo, usuario, modo_minuto_fast='auto')
        archivos_evento[2] = archivo_rsa_detectado

        nombre_rsa = Path(archivo_rsa_detectado).stem.rstrip('abc')
        mm_fast = nombre_rsa[0:2]
        dd_fast = nombre_rsa[2:4]
        hh_fast = nombre_rsa[4:6]
        minu_fast = nombre_rsa[6:8]

        dir_fast = os.path.dirname(archivo_rsa_detectado)
        archivos_evento[3] = os.path.join(dir_fast, f"Phase{dd_fast}{hh_fast[0]}.{hh_fast[1]}{minu_fast}")

        base_lp = f"{mm_fast}{dd_fast}{hh_fast}.{minu_fast}"
        archivos_evento[4] = os.path.join(dir_fast, base_lp + "L")
        archivos_evento[5] = os.path.join(dir_fast, base_lp + "P")
        archivos_evento[6] = os.path.join(dir_fast, base_lp + "S")

    else:
        archivos_evento = archivos_fast(archivo, directorio_trabajo, usuario, modo_minuto_fast='auto')

    # El sufijo solo aplica en host
    if usuario == '':
        archivos_evento = verificar_coincidencias(eventos, archivo, archivos_evento)

    archivo_fas = archivos_evento[1]
    archivo_rsa = archivos_evento[2]
    archivo_fase = archivos_evento[3]

    bandera_error = 0
    archivo_estaciones = os.path.join(directorio_trabajo, directorios["archivo_estaciones"])
    lectura_estaciones = lectura_archivo(archivo_estaciones)

    aux = len(archivo)
    if archivo[-11:-10] == "_":
        sismo_aux = archivo[-17:-11] + archivo[-10:aux]
    else:
        sismo_aux = archivo[-10:aux]

    lectura_fase = []
    auxiliar = ["Disp.", "t_pr.", "t_sec.", "marc.s", "t_cod."]
    lectura_fase.append(auxiliar)

    if os.path.exists(archivo_fase):
        with open(archivo_fase, newline='') as f_f:
            lectura_archivo_fase = csv.reader(f_f, delimiter='\n', quotechar=';')
            for lectura in lectura_archivo_fase:
                for v in lectura:
                    auxiliar = [v[4:8], v[19:24], v[31:36], v[36:40], v[70:75]]
                    lectura_fase.append(auxiliar)

    elif os.path.exists(archivo_fas):
        archivo_abrir = open(archivo_fas, 'rb')
        bandera_1 = 1
        auxiliar = []
        contador = 0

        while bandera_1:
            cabecera_0 = archivo_abrir.read(2)
            resultado = codigos(cabecera_0, archivo_abrir)

            if cabecera_0 == b'\x08\x00':
                if contador == 2:
                    auxiliar.append(resultado[0])
                    contador = 3
                if contador == 1:
                    auxiliar.append(resultado[0][:5])
                    auxiliar.append(resultado[0][-4:])
                    contador = 2
                if resultado[1] == 28:
                    auxiliar = []
                    if resultado[0][:4] != '    ':
                        if contador == 0:
                            auxiliar = [resultado[0][4:8], resultado[0][-5:]]
                            contador = 1
                if auxiliar != [] and contador == 3:
                    lectura_fase.append(auxiliar)
                    contador = 0

            if len(cabecera_0) == 0:
                bandera_1 = 0
                archivo_abrir.close()
    else:
        auxiliar = ['    ', '    ', '    ', '    ', '    ']
        lectura_fase.append(auxiliar)

    if os.path.exists(archivo_rsa):
        with open(archivo_rsa, newline='') as f_r:
            lectura_archivo_rsa = csv.reader(f_r, delimiter=' ', quotechar=';')
            estaciones_evento = ""
            lectura_total = []

            for lectura in lectura_archivo_rsa:
                datos_ = []
                for v in lectura:
                    if v == '' or v == ' ':
                        pass
                    else:
                        datos_.append(v)
                lectura_total.append(datos_)

            for i, datos_ in enumerate(lectura_total):
                try:
                    if len(datos_) > 0:
                        if datos_[0] == 'sta':
                            if lectura_total[i - 1] != []:
                                latitud = float(lectura_total[i - 1][0])
                                longitud = float(lectura_total[i - 1][1])
                                profundidad = round(float(lectura_total[i - 1][2]), 1)
                                segundo_sismo = float(lectura_total[i - 1][3])
                                datos_estaciones = []
                                auxiliar = lectura_estaciones[0][2:8] + datos_[1:] + lectura_fase[0]
                                datos_estaciones.append(auxiliar)
                                indice = i

                                while lectura_total[i] != []:
                                    i = i + 1
                                    if lectura_total[i] != []:
                                        estacion_ = lectura_total[i][0]
                                        lista_seleccionada = next(
                                            (lista for lista in lectura_estaciones if lista[2] == estacion_),
                                            None
                                        )

                                        if lista_seleccionada is None:
                                            if estacion_ == 'CALCULO':
                                                estaciones = ''
                                                for estacion in datos_estaciones:
                                                    if estacion != 'nombre':
                                                        estaciones = estaciones + estacion[0] + ' '
                                                return
                                            print("Estacion ", estacion_)
                                            return

                                        if len(lectura_fase) != 2:
                                            auxiliar_est = lista_seleccionada[2:8] + lectura_total[i][1:] + lectura_fase[i - indice]
                                        else:
                                            auxiliar_est = lista_seleccionada[2:8] + lectura_total[i][1:] + lectura_fase[1]

                                        datos_estaciones.append(auxiliar_est)

                        if datos_[0] == 'error':
                            ex = float(datos_[3])
                            ey = float(datos_[6])
                            e0 = float(datos_[10])

                        if datos_[0] == 'event':
                            id_sismo = '20' + sismo_aux[0:10] + '00'
                            anio_sismo = 2000 + int(datos_[3])
                            mes_sismo = int(datos_[4])
                            dia_sismo = int(datos_[5])
                            hora_sismo = int(datos_[6])
                            minuto_sismo = int(datos_[7])

                        if datos_[0] == 'rms=':
                            rms = float(datos_[1])
                            aux = len(lectura_total[i + 3][1])
                            ez = float(lectura_total[i + 3][1][0:aux - 2])
                            i = i + 3

                        if datos_[0] == 'Promedio':
                            if datos_[4] != 'No':
                                magnitud = float(datos_[4])
                            else:
                                magnitud = 0.0

                except ValueError:
                    bandera_error = 1

            if bandera_error:
                return 1
            else:
                ubicacion_sismo = ubicacion(latitud, longitud)
                ruta = archivo

                if segundo_sismo < 0:
                    segundo_sismo = 60 + segundo_sismo
                    minuto_sismo = minuto_sismo - 1
                    if minuto_sismo == -1:
                        minuto_sismo = 59
                        hora_sismo = hora_sismo - 1

                for ev in datos_estaciones:
                    if ev != [] and ev[0] != "sta" and ev[0] != '    ' and ev[0] != 'nombre':
                        estaciones_evento = estaciones_evento + ev[0] + " "

                datos_sismo = [
                    id_sismo, str(anio_sismo), str(mes_sismo), str(dia_sismo),
                    str(hora_sismo), str(minuto_sismo), str(segundo_sismo),
                    str(latitud), str(longitud), str(profundidad), str(rms),
                    str(ex), str(ey), str(e0), str(ez), str(magnitud),
                    'Md', 'RSA', ruta, ubicacion_sismo
                ]

                datos_estaciones = [sublista[:12] + sublista[13:15] + sublista[16:17] + sublista[19:] for sublista in datos_estaciones]

                return (datos_sismo, estaciones_evento, archivo_rsa, datos_estaciones)
    else:
        return

def archivos_fast(evento, dir_trabajo, usuario, retornar_validaciones=False, modo_minuto_fast='auto'):
    """
    Genera rutas para archivos FASTHYPO.
    
    modo_minuto_fast:
        'real'      -> fuerza minuto exacto
        'siguiente' -> fuerza minuto + 1
        'auto'      -> busca archivos existentes o usa ss>50 si no existen
    """
    info = obtener_directorios(evento)
    dir_dia = os.path.join(dir_trabajo, info['Directorio_dia'])
    dir_fast = os.path.join(dir_trabajo, info['Directorio_fastHypo'])

    if usuario:
        csv_path = os.path.join(ruta_datos, "responsables.csv")
        for fila in lectura_archivo(csv_path):
            if fila and fila[0].strip() == usuario.strip():
                dir_dia, dir_fast = fila[1], fila[2]
                break

    base = Path(evento).stem

    if len(base) == 13:      # AAMMDD_hhmmss
        yy = 2000 + int(base[:2])
        mm = base[2:4]
        dd = base[4:6]
        hh = base[7:9]
        minu = base[9:11]
        ss = base[11:13]
        sisfas_base = base
    else:                    # AAAAMMDD_hhmmss
        yy = int(base[:4])
        mm = base[4:6]
        dd = base[6:8]
        hh = base[9:11]
        minu = base[11:13]
        ss = base[13:15]
        sisfas_base = base if usuario == '' else base[2:]

    archivo_sis = os.path.join(dir_dia, f"{sisfas_base}.sis")
    archivo_fas = os.path.join(dir_dia, f"{sisfas_base}.fas")

    segundo_evento = int(ss)
    dt_evento = datetime(yy, int(mm), int(dd), int(hh), int(minu), segundo_evento)
    dt_siguiente = dt_evento + timedelta(minutes=1)

    def generar_rutas_fast(dt):
        mm_fast = dt.strftime("%m")
        dd_fast = dt.strftime("%d")
        hh_fast = dt.strftime("%H")
        minu_fast = dt.strftime("%M")

        rsa_nom = f"{mm_fast}{dd_fast}{hh_fast}{minu_fast}.rsa"
        archivo_rsa = os.path.join(dir_fast, rsa_nom)

        phase_nom = f"Phase{dd_fast}{hh_fast[0]}.{hh_fast[1]}{minu_fast}"
        archivo_phase = os.path.join(dir_fast, phase_nom)

        base_lp = f"{mm_fast}{dd_fast}{hh_fast}.{minu_fast}"
        archivo_L = os.path.join(dir_fast, base_lp + "L")
        archivo_P = os.path.join(dir_fast, base_lp + "P")
        archivo_S = os.path.join(dir_fast, base_lp + "S")

        return [archivo_rsa, archivo_phase, archivo_L, archivo_P, archivo_S]

    rutas_fast_real = generar_rutas_fast(dt_evento)
    rutas_fast_siguiente = generar_rutas_fast(dt_siguiente)

    if modo_minuto_fast == 'real':
        rutas_fast_elegidas = rutas_fast_real
    elif modo_minuto_fast == 'siguiente':
        rutas_fast_elegidas = rutas_fast_siguiente
    else:
        existe_real = os.path.exists(rutas_fast_real[0])
        existe_siguiente = os.path.exists(rutas_fast_siguiente[0])

        if existe_real or os.path.exists(rutas_fast_real[1]):
            rutas_fast_elegidas = rutas_fast_real
        elif existe_siguiente or os.path.exists(rutas_fast_siguiente[1]):
            rutas_fast_elegidas = rutas_fast_siguiente
        else:
            if segundo_evento >= 50:
                rutas_fast_elegidas = rutas_fast_siguiente
            else:
                rutas_fast_elegidas = rutas_fast_real

    rutas = [
        archivo_sis,
        archivo_fas,
        rutas_fast_elegidas[0],
        rutas_fast_elegidas[1],
        rutas_fast_elegidas[2],
        rutas_fast_elegidas[3],
        rutas_fast_elegidas[4]
    ]

    if retornar_validaciones:
        etiquetas = ['.sis', '.fas', '.rsa', 'Phase', '.L', '.P', '.S']
        existe = {etq: os.path.isfile(ruta) for etq, ruta in zip(etiquetas, rutas)}
        faltantes = [etq for etq, ok in existe.items() if not ok]
        return rutas, existe, faltantes

    return rutas


def verificar_coincidencias(eventos, evento_procesar, rutas_fast):
    print("verificar_coincidencias")
    contador = 0
    sufijo = ['', 'a', 'b', 'c']

    base_evento = Path(evento_procesar).stem.replace('_', '')
    if len(base_evento) == 12:  # AAMMDDhhmmss
        yy = 2000 + int(base_evento[:2])
        mm = int(base_evento[2:4])
        dd = int(base_evento[4:6])
        hh = int(base_evento[6:8])
        minu = int(base_evento[8:10])
        ss = int(base_evento[10:12])
    else:  # AAAAMMDDhhmmss
        yy = int(base_evento[:4])
        mm = int(base_evento[4:6])
        dd = int(base_evento[6:8])
        hh = int(base_evento[8:10])
        minu = int(base_evento[10:12])
        ss = int(base_evento[12:14])

    dt_evento = datetime(yy, mm, dd, hh, minu, ss)
    if ss > 50:
        dt_evento = dt_evento + timedelta(minutes=1)

    clave_minuto = dt_evento.strftime("%Y%m%d%H%M")

    for evento in eventos:
        tipo_evento = evento[2]
        if tipo_evento != 'SISMO':
            continue

        base_actual = Path(evento[1]).stem.replace('_', '')
        if len(base_actual) == 12:  # AAMMDDhhmmss
            yy_a = 2000 + int(base_actual[:2])
            mm_a = int(base_actual[2:4])
            dd_a = int(base_actual[4:6])
            hh_a = int(base_actual[6:8])
            minu_a = int(base_actual[8:10])
            ss_a = int(base_actual[10:12])
        else:  # AAAAMMDDhhmmss
            yy_a = int(base_actual[:4])
            mm_a = int(base_actual[4:6])
            dd_a = int(base_actual[6:8])
            hh_a = int(base_actual[8:10])
            minu_a = int(base_actual[10:12])
            ss_a = int(base_actual[12:14])

        dt_actual = datetime(yy_a, mm_a, dd_a, hh_a, minu_a, ss_a)
        if ss_a > 50:
            dt_actual = dt_actual + timedelta(minutes=1)

        clave_actual = dt_actual.strftime("%Y%m%d%H%M")

        if clave_actual == clave_minuto:
            if base_actual == base_evento:
                break
            contador += 1

    if contador >= len(sufijo):
        contador = len(sufijo) - 1

    suf = sufijo[contador]
    if not suf:
        return rutas_fast

    if rutas_fast[2].lower().endswith('.rsa'):
        rutas_fast[2] = rutas_fast[2][:-4] + suf + '.rsa'

    for i in range(3, 7):
        if rutas_fast[i]:
            rutas_fast[i] = rutas_fast[i] + suf

    return rutas_fast


def guardar_intento(archivo, directorio, responsables, procesamiento, archivo_rsa_detectado=''):
    print("guardar_intento")

    resultado = lectura_rsa(
        archivo,
        directorio,
        responsables,
        archivo_rsa_detectado
    )

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    indice = str(len(procesamiento) - 1)

    if resultado is None:
        fila = [indice, ahora, "Fallido", " ", " ", " ", " "]
        procesamiento.append(fila)
        return procesamiento

    if resultado == 1:
        fila = [indice, ahora, "Fallido", "Error de conversion", " ", " ", " "]
        procesamiento.append(fila)
        return procesamiento

    datos_sismo = resultado[0]

    try:
        profundidad = datos_sismo[9]
        magnitud = datos_sismo[15]
        latitud = datos_sismo[7]
        longitud = datos_sismo[8]
        rms = datos_sismo[10]
        fila = [indice, ahora, profundidad, magnitud, latitud, longitud, rms]
    except Exception:
        fila = [indice, ahora, "Fallido", " ", " ", " ", " "]

    procesamiento.append(fila)
    return procesamiento






def guardar_informacion_diaria(archivo,directorio_trabajo,catalogo_anterior,eventos):
    #archivo:          Archivo del día con formato AAMMDD_hhmmss.csv
    #directorio_trabajo:   Directorio del drive de trabajo
    #catalogo_anterior:    Catalogo encontrado en el día para cargar la información de otras redes.
    print("guardar_informacion_diaria")
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
    print(" ordenar_y_eliminar_duplicados")
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




