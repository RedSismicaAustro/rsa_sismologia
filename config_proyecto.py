# config_proyecto.py
import sys
import os
from pathlib import Path

def _buscar_raiz_proyecto():
    """Busca la raíz del proyecto (donde está este archivo)."""
    current = Path(__file__).resolve().parent
    # Opcional: verifica que exista una carpeta 'src/librerias' o 'datos' como señal
    if (current / 'src' / 'librerias').exists() or (current / 'datos').exists():
        return current
    # Si no, sube un nivel (por si se llamó desde subcarpeta)
    for parent in current.parents:
        if (parent / 'src' / 'librerias').exists() or (parent / 'datos').exists():
            return parent
    return None

def configurar():
    """Configura el entorno según el contexto (Spyder o externo)."""
    # Si estamos en Spyder (con proyecto configurado), asumimos que ya está todo listo
    # Para detectar Spyder: puede ser por variable de entorno o por módulo 'spyder'
    if 'SPYDER' in os.environ or 'spyder' in sys.modules:
        # No hacemos nada, confiamos en la configuración del proyecto
        return

    # Fuera de Spyder: necesitamos buscar la raíz y configurar manualmente
    proyecto_raiz = _buscar_raiz_proyecto()
    if not proyecto_raiz:
        raise RuntimeError("No se pudo encontrar la raíz del proyecto 'rsa_sismologia'")

    # 1. Agregar src/librerias al sys.path
    ruta_librerias = proyecto_raiz / 'src' / 'librerias'
    if str(ruta_librerias) not in sys.path:
        sys.path.insert(0, str(ruta_librerias))

    # 2. Cambiar el directorio de trabajo a la raíz del proyecto
    os.chdir(proyecto_raiz)

    # 3. (Opcional) Crear una variable de entorno con la ruta de datos
    os.environ['RUTA_DATOS'] = str(proyecto_raiz / 'datos')

# Ejecutar la configuración al importar este módulo
configurar()