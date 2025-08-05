import sys
from PyQt5.QtWidgets import QApplication, QFileDialog
import shapefile
import pandas as pd

# Inicializar QApplication
app = QApplication(sys.argv)

# Seleccionar archivo CSV
archivo, _ = QFileDialog.getOpenFileName(None, "Seleccionar archivo", "", "Archivos csv (*.csv);;Todos los archivos (*.*)")

# Verificar si se seleccionó un archivo
if not archivo:
    print("No se seleccionó ningún archivo. Finalizando el programa.")
    sys.exit()

print(archivo[:-3])
archivo_shape = archivo[:-4] + ".shp"  # Corregido el índice para eliminar '.csv'

# Leer archivo CSV
df = pd.read_csv(archivo, delimiter=';', encoding='latin-1')

# Crear objeto shapefile
sf = shapefile.Writer(archivo_shape, shapeType=shapefile.POINT)
sf.field('ID', 'C')
sf.field('Latitud', 'F', decimal=4)
sf.field('Longitud', 'F', decimal=4)
sf.field('Profundidad', 'F', decimal=1)
sf.field('Magnitud', 'F', decimal=1)

# Iterar sobre cada fila del DataFrame y agregar al shapefile
for index, row in df.iterrows():
    try:
        id = row['Id']
        lat = row['lat']
        lon = row['long']
        depth = row['prof']
        mag = row['Mag']
        fuente = row['Fuente']
    except KeyError as e:
        print(f"Error: Falta la columna {e} en el archivo CSV.")
        continue

    if fuente == "RSA":
        # Agregar punto al shapefile
        sf.point(lon, lat)
        
        # Agregar registro al shapefile
        sf.record(str(id), lat, lon, depth, mag)

# Guardar shapefile
sf.close()

# Cerrar la aplicación de forma segura
app.quit()
