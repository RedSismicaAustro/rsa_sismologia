import sys
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox
)
import shutil
import numpy as np
from obspy import Stream, Trace, UTCDateTime
from datetime import datetime
import os
import re

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

def ejecutar_en_vm(evt_path,virtual_path,destino_host):


        try:
            evt_virtual = virtual_path / evt_path.name
            shutil.copy2(evt_path, evt_virtual)

            batch_path = virtual_path / "ejecutar_kw2asc.bat"
            with open(batch_path, 'w') as f:
                f.write(f"@echo off\n")
                f.write(f"cd C:\\DIA\\KINEMETRICS\n")
                f.write(f"KW2ASC.EXE {evt_path.name} > salida_kw2asc.txt 2>&1\n")
        except Exception as e:
            print(e)
            return
    

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
            nombre_archivo = f"{estacion}_{starttime.strftime('%Y%m%d_%H%M%S')}.mseed"
            salida_mseed = destino_host / nombre_archivo
            stream.write(str(salida_mseed), format="MSEED")
            for ext in [".001", ".002", ".003", ".SHD"]:
                archivo = destino_host / f"{nombre_base}{ext}"
                if archivo.exists():
                    os.remove(archivo)
            return stream
        except Exception as e:
            print(e)
            return None
            pass


class CopiarEVT(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Procesar archivo EVT desde entorno virtual")
        self.evt_path = None
        self.virtual_path = Path("O:/KINEMETRICS")
        self.destino_host = None

        layout = QVBoxLayout()

        self.lbl_evt = QLabel("Archivo EVT: No seleccionado")
        self.lbl_destino = QLabel("Directorio destino en host: No seleccionado")

        self.btn_escoger_evt = QPushButton("Seleccionar archivo EVT")
        self.btn_escoger_evt.clicked.connect(self.escoger_evt)

        self.btn_escoger_destino = QPushButton("Seleccionar directorio de destino (host)")
        self.btn_escoger_destino.clicked.connect(self.escoger_destino)

 
        self.btn_ejecutar_vm = QPushButton("Ejecutar remotamente en la VM")
        self.btn_ejecutar_vm.clicked.connect(self.ejecutar_en_vm)

        self.btn_probar_vm = QPushButton("Probar acceso remoto")
        self.btn_probar_vm.clicked.connect(self.probar_acceso_vm)

        self.btn_salir = QPushButton("Salir")
        self.btn_salir.clicked.connect(self.close)

        layout.addWidget(self.lbl_evt)
        layout.addWidget(self.btn_escoger_evt)
        layout.addWidget(self.lbl_destino)
        layout.addWidget(self.btn_escoger_destino)
        layout.addWidget(self.btn_ejecutar_vm)
        layout.addWidget(self.btn_probar_vm)
        layout.addWidget(self.btn_salir)

        self.setLayout(layout)

    def escoger_evt(self):
        archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo EVT", "", "Archivos EVT (*.EVT)")
        if archivo:
            self.evt_path = Path(archivo)
            self.lbl_evt.setText(f"Archivo seleccionado: {self.evt_path.name}")

    def escoger_destino(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar directorio de destino (host)")
        if carpeta:
            self.destino_host = Path(carpeta)
            self.lbl_destino.setText(f"Destino: {self.destino_host}")

    def ejecutar_en_vm(self):
        ejecutar_en_vm(self.evt_path,self.virtual_path,self.destino_host)
 

    def probar_acceso_vm(self):
        try:
            usuario = "vbox"
            password = "rsa"

            comando = [
                "VBoxManage", "guestcontrol", "RSA1", "run",
                "--username", usuario,
                "--password", password,
                "--exe", "C:\\Windows\\System32\\cmd.exe",
                "--timeout", "5000",
                "--", "cmd.exe", "/c", "echo hola"
            ]

            resultado = subprocess.run(comando, capture_output=True, text=True)
            if resultado.returncode == 0:
                QMessageBox.information(self, "Prueba exitosa", f"Conexión remota exitosa. Salida: {resultado.stdout.strip()}")
            else:
                QMessageBox.critical(self, "Fallo de conexión", resultado.stderr)
        except Exception as e:
            QMessageBox.critical(self, "Error inesperado", str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = CopiarEVT()
    ventana.show()
    sys.exit(app.exec_())

