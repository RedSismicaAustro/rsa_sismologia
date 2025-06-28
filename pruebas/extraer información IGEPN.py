import requests
from bs4 import BeautifulSoup
import pandas as pd

def extraer_sismos_igepn():
    url = "https://www.igepn.edu.ec/portal/eventos/informes-ultimos-sismosC.html"
    respuesta = requests.get(url)
    soup = BeautifulSoup(respuesta.text, 'html.parser')

    # Buscar la tabla por clases visuales comunes
    tabla = soup.find('table')

    if not tabla:
        raise ValueError("No se encontró la tabla de eventos sísmicos.")

    # Obtener encabezados (por si se desea usar como claves del DataFrame)
    encabezados = [th.text.strip() for th in tabla.find_all('th')]

    datos_sismos = []
    filas = tabla.find_all('tr')[1:]  # Omitir encabezado

    for fila in filas:
        columnas = fila.find_all('td')
        if len(columnas) < 13:
            continue

        datos = {
            'evento': columnas[1].text.strip(),
            'url_evento': columnas[1].find('a')['href'] if columnas[1].find('a') else None,
            'magnitud': columnas[2].text.strip(),
            'tipo_magnitud': columnas[3].text.strip(),
            'tiempo_local': columnas[4].text.strip(),
            'latitud': columnas[5].text.strip(),
            'longitud': columnas[6].text.strip(),
            'profundidad_km': columnas[7].text.strip(),
            'region': columnas[8].text.strip(),
            'ciudad_cercana': columnas[9].text.strip(),
            'estado': columnas[10].text.strip(),
            'fecha_utc': columnas[11].text.strip(),
            'ultima_actualizacion': columnas[12].text.strip()
        }

        datos_sismos.append(datos)

    return pd.DataFrame(datos_sismos)

# Ejecutar
if __name__ == "__main__":
    df_sismos = extraer_sismos_igepn()
    print(df_sismos.head())  # Mostrar los primeros registros
