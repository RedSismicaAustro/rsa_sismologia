import os
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel
from metodos_rsa import lectura_archivo, escritura_archivo

#Programa para generar los nivles de chanlud yl abrado
#archivos.csv  lista de archivos csv con la información de los niveles entrada 
#niveles.csv   archivo con kla información de los nivles de las presas salida
#
#


class ProcesadorNiveles(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.label = QLabel("Selecciona el directorio con los archivos CSV")
        layout.addWidget(self.label)

        self.button = QPushButton("Seleccionar Directorio")
        self.button.clicked.connect(self.seleccionar_directorio)
        layout.addWidget(self.button)

        self.setLayout(layout)
        self.setWindowTitle("Procesador de Niveles de Presa")
        self.setGeometry(300, 300, 400, 200)

    def seleccionar_directorio(self):
        directory = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio")
        if directory:
            self.label.setText(f"Directorio seleccionado: {directory}")
            self.procesar_archivos(directory)

    def determinar_formato_fecha(self, fechas):
        formatos = ['%m/%d/%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%m/%d/%Y %H:%M', '%d/%m/%Y %H:%M']
        for formato in formatos:
            try:
                fecha_ = ''
                for fecha in fechas:
                    fecha_ = datetime.strptime(fecha, formato)
                return formato
            except ValueError:
                print('formato erroneo', formato, fecha, fecha_)
                continue

        raise ValueError("Formato de fecha no reconocido en el archivo.")

    def procesar_archivos(self, directory):
        # Leer archivos existentes usando el método lectura_archivo
        archivo_niveles = os.path.join(directory, 'niveles.csv')
        archivo_archivos = os.path.join(directory, 'archivos.csv')

        niveles = lectura_archivo(archivo_niveles) or []
        archivos_procesados = lectura_archivo(archivo_archivos) or []

        # Eliminar cabeceras de archivos leídos
        niveles = niveles[3:] if len(niveles) > 3 else []
        archivos_procesados = [item[0] for item in archivos_procesados[3:]] if len(archivos_procesados) > 3 else []

        # Procesar nuevos archivos
        nuevos_niveles = []
        nuevos_archivos_procesados = []

        for archivo in sorted(os.listdir(directory)):
            print('Archivo:', archivo)
            if archivo.endswith('.csv') and archivo not in archivos_procesados and archivo not in ['niveles.csv', 'archivos.csv']:
                archivo_path = os.path.join(directory, archivo)
                datos_crudos = lectura_archivo(archivo_path)
                if datos_crudos is None:
                    continue

                # Extraer datos relevantes desde la cuarta línea
                datos = datos_crudos[3:]

                # Extraer fechas para determinar el formato
                fechas = [fila[1] for fila in datos[:313]]  # Tomar los primeros 313 registros para determinar el formato

                formato_fecha = self.determinar_formato_fecha(fechas)

                # Convertir fechas y acumular datos
                for fila in datos:
                    try:
                        fecha = datetime.strptime(fila[1], formato_fecha)
                        fila[1] = fecha  # Guardar la fecha convertida
                        nuevos_niveles.append(fila)
                    except ValueError:
                        continue

                # Registrar archivo procesado
                nuevos_archivos_procesados.append([archivo])

        # Actualizar las listas y escribir en los archivos
        niveles.extend(nuevos_niveles)

        # Asegurarse de que todas las fechas en niveles son objetos datetime para ordenarlas
        for fila in niveles:
            if isinstance(fila[1], str):
                fila[1] = datetime.strptime(fila[1], formato_fecha)

        # Ordenar los niveles por la fecha (segundo elemento de cada fila)
        niveles.sort(key=lambda x: x[1])

        # Convertir las fechas de nuevo a cadenas antes de guardar
        for fila in niveles:
            fila[1] = fila[1].strftime(formato_fecha)

        escritura_archivo(archivo_niveles, niveles)
        escritura_archivo(archivo_archivos, nuevos_archivos_procesados)

        self.label.setText("Procesamiento completado.")

        # Llamar a la función para graficar los niveles
        self.graficar_niveles(niveles, formato_fecha)

    def graficar_niveles(self, niveles, formato_fecha):
        # Convertir fechas de vuelta a objetos datetime para graficar, usando el formato adecuado
        fechas = [datetime.strptime(fila[1], formato_fecha) for fila in niveles]
        valores = [float(fila[2]) for fila in niveles]

        plt.figure(figsize=(10, 6))
        plt.plot(fechas, valores, marker='o', linestyle='-', color='b')
        plt.xlabel('Fecha')
        plt.ylabel('Nivel de la Presa')
        plt.title('Niveles de la Presa a lo Largo del Tiempo')
        plt.xticks(rotation=45)
        plt.grid(True)

        # Formatear el eje x para mostrar las fechas de forma clara
        date_format = DateFormatter("%d-%m-%Y %H:%M")
        plt.gca().xaxis.set_major_formatter(date_format)
        plt.tight_layout()

        # Mostrar la gráfica
        plt.show()

if __name__ == '__main__':
    app = QApplication([])
    ex = ProcesadorNiveles()
    ex.show()
    app.exec_()

