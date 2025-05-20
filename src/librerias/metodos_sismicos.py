from obspy.signal.trigger import classic_sta_lta, trigger_onset
import numpy as np
from scipy.signal import butter, filtfilt, decimate
from obspy import Stream


def detectar_y_marcar_fases(tr):
    # Parámetros para el algoritmo STA/LTA
    longitud_sta = 2
    longitud_lta = 10
    umbral_on = 2.0
    umbral_off = 1.5
    # Calcular STA/LTA
    datos = tr.data
    tiempo = tr.times()
    cf = classic_sta_lta(datos, longitud_sta * tr.stats.sampling_rate, longitud_lta * tr.stats.sampling_rate)
    # Detectar inicios de eventos
    disparos = trigger_onset(cf, umbral_on, umbral_off)
    # Inicializar fases detectadas con 0
    fases_detectadas = {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}
    # Marcar fases P y S
    for i, (inicio, fin) in enumerate(disparos):
        if i == 0:  # Fase P
            tiempo_p = tiempo[inicio]
            #ax.axvline(x=tiempo_p, color='r', linestyle='--', label='Fase P')
            fases_detectadas['P'] = [tiempo_p]
        elif i == 1:  # Fase S
            tiempo_s = tiempo[inicio]
            #ax.axvline(x=tiempo_s, color='b', linestyle='--', label='Fase S')
            fases_detectadas['S'] = [tiempo_s]
        if i >= 2:
            break  # Solo nos interesan las primeras dos fases
    return fases_detectadas

def diezmar_senal(stream, factor):
    if factor == 1:
        # Si el factor de diezmado es 1, no se realiza ninguna operación
        return stream
    for trace in stream:
        # Obtener la frecuencia de muestreo original
        fs = trace.stats.sampling_rate
        # Calcular la nueva frecuencia de muestreo después del diezmado
        fs_nueva = fs / factor
        # Realizar el diezmado sin filtrado adicional
        señal_diezmada = decimate(trace.data, factor, ftype='fir', zero_phase=True)
        # Actualizar la señal y la frecuencia de muestreo en el Trace
        trace.data = señal_diezmada
        trace.stats.sampling_rate = fs_nueva

    return stream