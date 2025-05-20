# diagnostico_entorno.py

import platform
import sys
import importlib

print("🧠 Diagnóstico del entorno Python")
print(f"Sistema operativo : {platform.system()} {platform.release()}")
print(f"Versión de Python : {sys.version.split()[0]}\n")

print("📦 Estado de librerías importantes:")

librerias = [
    'PyQt5', 'matplotlib', 'numpy', 'scipy', 'obspy',
    'pandas', 'geopandas', 'reportlab'
]

for lib in librerias:
    try:
        if lib == 'PyQt5':
            from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
            print(f"{lib:<12} ✅  PyQt5: {PYQT_VERSION_STR}, Qt: {QT_VERSION_STR}")
        else:
            mod = importlib.import_module(lib)
            version = getattr(mod, '__version__', '¿sin __version__?')
            print(f"{lib:<12} ✅  {version}")
    except Exception as e:
        print(f"{lib:<12} ❌  No disponible o error: {e}")
