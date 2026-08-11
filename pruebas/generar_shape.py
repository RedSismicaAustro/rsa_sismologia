"""Genera un shapefile de eventos RSA y sus metadatos.

El archivo de metadatos se guarda como ``<nombre>.metadata.json`` junto al
shapefile. También se crean ``.prj`` y ``.cpg`` para que el CRS y la
codificación sean reconocidos por los programas GIS.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import traceback
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from pyproj import CRS, Transformer
import shapefile


CRS_SALIDA = CRS.from_epsg(32717)
TRANSFORMADOR_UTM_17S = Transformer.from_crs(4326, CRS_SALIDA, always_xy=True)
NOMBRE_CRS = "WGS 84 / UTM Zona 17S (EPSG:32717)"
COLUMNAS_REQUERIDAS = {"Id", "lat", "long", "prof", "Mag", "Fuente"}


@dataclass
class Metadatos:
    titulo: str
    resumen_abstract: str
    fecha: str
    idioma: str
    palabras_clave: list[str]
    sistema_referencia_coordenadas_crs: str
    categoria: str
    creador_autor: str
    contacto: str
    licencia: str

    @classmethod
    def desde_diccionario(cls, datos: dict) -> "Metadatos":
        """Acepta las claves nuevas y conserva compatibilidad con nombres breves."""
        palabras = datos.get("palabras_clave", datos.get("Palabras clave", []))
        if isinstance(palabras, str):
            palabras = [p.strip() for p in palabras.split(",") if p.strip()]
        return cls(
            titulo=str(datos.get("titulo", datos.get("Título", ""))).strip(),
            resumen_abstract=str(
                datos.get("resumen_abstract", datos.get("Resumen (Abstract)", ""))
            ).strip(),
            fecha=str(datos.get("fecha", datos.get("Fecha", date.today().isoformat()))).strip(),
            idioma=str(datos.get("idioma", datos.get("Idioma", "Español"))).strip(),
            palabras_clave=palabras,
            sistema_referencia_coordenadas_crs=str(
                datos.get(
                    "sistema_referencia_coordenadas_crs",
                    datos.get("Sistema de Referencia de Coordenadas (CRS)", NOMBRE_CRS),
                )
            ).strip(),
            categoria=str(datos.get("categoria", datos.get("Categoría", ""))).strip(),
            creador_autor=str(datos.get("creador_autor", datos.get("Creador / Autor", "RSA"))).strip(),
            contacto=str(
                datos.get("contacto", datos.get("Contacto", "redsismica@ucuenca.edu.ec"))
            ).strip(),
            licencia=str(datos.get("licencia", datos.get("Licencia", ""))).strip(),
        )

    def validar(self) -> None:
        faltantes = []
        opcionales = {"categoria", "licencia"}
        for nombre, valor in asdict(self).items():
            if nombre in opcionales:
                continue
            if not valor:
                faltantes.append(nombre)
        try:
            for extremo in self.fecha.split("/"):
                datetime.fromisoformat(extremo.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                "La fecha debe usar ISO 8601, por ejemplo 2026-08-11T15:30:00Z."
            ) from exc
        if faltantes:
            raise ValueError("Faltan metadatos obligatorios: " + ", ".join(faltantes))


def leer_csv(ruta_csv: Path) -> pd.DataFrame:
    """Lee CSV separados por punto y coma, probando codificaciones habituales."""
    ruta_csv = ruta_csv.resolve()
    print(f"[FUENTE] Leyendo catálogo: {ruta_csv}", flush=True)
    if not ruta_csv.name.lower().endswith("_cat.csv"):
        raise ValueError(
            "Debe seleccionar un catálogo cuyo nombre termine en '_cat.csv'."
        )
    ultimo_error = None
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(ruta_csv, sep=";", encoding=codificacion)
            print(
                f"[FUENTE] Catálogo leído con codificación {codificacion}: "
                f"{len(df)} registros",
                flush=True,
            )
            break
        except UnicodeDecodeError as exc:
            ultimo_error = exc
    else:
        raise ValueError(f"No se pudo decodificar el CSV: {ultimo_error}")

    faltantes = sorted(COLUMNAS_REQUERIDAS.difference(df.columns))
    if faltantes:
        raise ValueError("Faltan columnas requeridas: " + ", ".join(faltantes))
    return df


def numero(valor, campo: str, fila: int) -> float:
    try:
        resultado = float(str(valor).strip().replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Fila {fila}: {campo} no es numérico ({valor!r}).") from exc
    if not math.isfinite(resultado):
        raise ValueError(f"Fila {fila}: {campo} debe ser un número finito.")
    return resultado


def buscar_columna(df: pd.DataFrame, *nombres: str) -> str | None:
    normalizadas = {str(columna).strip().lower(): columna for columna in df.columns}
    for nombre in nombres:
        if nombre.lower() in normalizadas:
            return normalizadas[nombre.lower()]
    return None


def texto_celda(fila, columna: str | None) -> str:
    if columna is None or pd.isna(fila[columna]):
        return ""
    return str(fila[columna]).strip()


def fecha_gmt_fila(fila, df: pd.DataFrame) -> str:
    columnas = [
        buscar_columna(df, "año", "anio"),
        buscar_columna(df, "mes"),
        buscar_columna(df, "día", "dia"),
        buscar_columna(df, "hora"),
        buscar_columna(df, "min", "minuto"),
        buscar_columna(df, "seg", "segundo"),
    ]
    if any(columna is None for columna in columnas[:3]):
        return ""
    valores = []
    for posicion, columna in enumerate(columnas):
        if columna is None or pd.isna(fila[columna]):
            valores.append(0)
        else:
            valor = float(str(fila[columna]).replace(",", "."))
            valores.append(int(valor) if posicion != 5 else valor)
    segundos = int(valores[5])
    microsegundos = round((valores[5] - segundos) * 1_000_000)
    instante = datetime(
        *map(int, valores[:5]), segundos, microsegundos, tzinfo=timezone.utc
    )
    return instante.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def eventos_rsa(df: pd.DataFrame):
    """Valida y devuelve eventos RSA; una fila dañada nunca queda oculta."""
    for indice, fila in df.iterrows():
        numero_fila = indice + 2  # La primera línea del CSV contiene encabezados.
        if str(fila["Fuente"]).strip().upper() != "RSA":
            continue
        latitud = numero(fila["lat"], "latitud", numero_fila)
        longitud = numero(fila["long"], "longitud", numero_fila)
        profundidad = numero(fila["prof"], "profundidad", numero_fila)
        magnitud = numero(fila["Mag"], "magnitud", numero_fila)
        if not -90 <= latitud <= 90:
            raise ValueError(f"Fila {numero_fila}: latitud fuera del rango [-90, 90].")
        if not -180 <= longitud <= 180:
            raise ValueError(f"Fila {numero_fila}: longitud fuera del rango [-180, 180].")
        if profundidad < 0:
            raise ValueError(f"Fila {numero_fila}: la profundidad no puede ser negativa.")
        ubicacion = texto_celda(fila, buscar_columna(df, "Ubicación", "Ubicacion"))
        fecha_gmt = fecha_gmt_fila(fila, df)
        yield str(fila["Id"]), latitud, longitud, profundidad, magnitud, fecha_gmt, ubicacion


def metadatos_sugeridos(df: pd.DataFrame, nombre_archivo: str) -> Metadatos:
    filas = df[df["Fuente"].astype(str).str.strip().str.upper() == "RSA"]
    fechas = [fecha_gmt_fila(fila, df) for _, fila in filas.iterrows()]
    fechas = [valor for valor in fechas if valor]
    columna_ubicacion = buscar_columna(df, "Ubicación", "Ubicacion")
    ubicaciones = []
    if columna_ubicacion:
        ubicaciones = [
            str(valor).strip() for valor in filas[columna_ubicacion].dropna().unique()
            if str(valor).strip()
        ]
    lugar = ", ".join(ubicaciones[:3]) or "localización registrada en el catálogo"
    if len(filas) == 1:
        instante_titulo = f" - {fechas[0]}" if fechas else ""
        titulo = f"Evento sísmico RSA - {lugar}{instante_titulo}"
        resumen = f"Evento sísmico localizado en {lugar}, registrado por la RSA."
        fecha_metadata = fechas[0] if fechas else date.today().isoformat()
    else:
        titulo = f"Catálogo de eventos sísmicos RSA - {nombre_archivo}"
        resumen = f"Catálogo de {len(filas)} eventos sísmicos localizados en {lugar}."
        if fechas:
            fecha_metadata = fechas[0] if len(fechas) == 1 else f"{min(fechas)}/{max(fechas)}"
        else:
            fecha_metadata = date.today().isoformat()
    return Metadatos(
        titulo=titulo,
        resumen_abstract=resumen,
        fecha=fecha_metadata,
        idioma="Español",
        palabras_clave=["sismo"],
        sistema_referencia_coordenadas_crs=NOMBRE_CRS,
        categoria="",
        creador_autor="RSA",
        contacto="redsismica@ucuenca.edu.ec",
        licencia="",
    )


def escribir_metadatos(ruta_base: Path, metadatos: Metadatos, cantidad: int) -> Path:
    ruta = Path(f"{ruta_base}.metadata.json")
    print(f"[GENERANDO] {ruta}", flush=True)
    contenido = {
        "formato_metadatos": "RSA-GIS-1.0",
        "Título": metadatos.titulo,
        "Resumen (Abstract)": metadatos.resumen_abstract,
        "Fecha": metadatos.fecha,
        "Idioma": metadatos.idioma,
        "Palabras clave": metadatos.palabras_clave,
        "Sistema de Referencia de Coordenadas (CRS)": (
            metadatos.sistema_referencia_coordenadas_crs
        ),
        "Categoría": metadatos.categoria,
        "Creador / Autor": metadatos.creador_autor,
        "Contacto": metadatos.contacto,
        "Licencia": metadatos.licencia,
        "recurso": {
            "archivo": Path(f"{ruta_base}.shp").name,
            "tipo_geometria": "Punto",
            "cantidad_elementos": cantidad,
        },
    }
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[GENERADO]  {ruta}", flush=True)
    return ruta


def agregar_texto_xml(padre: ET.Element, etiqueta: str, texto: str = "") -> ET.Element:
    elemento = ET.SubElement(padre, etiqueta)
    elemento.text = texto
    return elemento


def escribir_metadatos_qgis(
    ruta_base: Path, metadatos: Metadatos, registros: list[tuple]
) -> Path:
    """Escribe metadatos nativos de capa en el formato QMD de QGIS."""
    ruta = Path(f"{ruta_base}.qmd")
    print(f"[GENERANDO] {ruta}", flush=True)
    raiz = ET.Element("qgis", {"version": "3.40.8-Bratislava"})
    agregar_texto_xml(raiz, "identifier", ruta_base.name)
    agregar_texto_xml(raiz, "parentidentifier")
    agregar_texto_xml(raiz, "language", "spa")
    agregar_texto_xml(raiz, "type", "dataset")
    agregar_texto_xml(raiz, "title", metadatos.titulo)
    agregar_texto_xml(raiz, "abstract", metadatos.resumen_abstract)

    palabras = ET.SubElement(raiz, "keywords", {"vocabulary": "RSA"})
    for palabra in metadatos.palabras_clave:
        agregar_texto_xml(palabras, "keyword", palabra)
    if metadatos.categoria:
        agregar_texto_xml(raiz, "category", metadatos.categoria)

    contacto = ET.SubElement(raiz, "contact")
    agregar_texto_xml(contacto, "name", metadatos.creador_autor)
    agregar_texto_xml(contacto, "organization", "RSA")
    agregar_texto_xml(contacto, "position")
    agregar_texto_xml(contacto, "voice")
    agregar_texto_xml(contacto, "fax")
    agregar_texto_xml(contacto, "email", metadatos.contacto)
    agregar_texto_xml(contacto, "role", "owner")

    agregar_texto_xml(raiz, "fees")
    agregar_texto_xml(raiz, "license", metadatos.licencia)
    agregar_texto_xml(raiz, "encoding", "UTF-8")
    crs = ET.SubElement(raiz, "crs")
    sistema = ET.SubElement(crs, "spatialrefsys")
    agregar_texto_xml(sistema, "authid", "EPSG:32717")
    agregar_texto_xml(sistema, "description", "WGS 84 / UTM zone 17S")

    coordenadas_utm = [
        TRANSFORMADOR_UTM_17S.transform(registro[2], registro[1])
        for registro in registros
    ]
    estes = [punto[0] for punto in coordenadas_utm]
    nortes = [punto[1] for punto in coordenadas_utm]
    extension = ET.SubElement(raiz, "extent")
    ET.SubElement(
        extension,
        "spatial",
        {
            "dimensions": "2",
            "crs": "EPSG:32717",
            "minx": str(min(estes)),
            "miny": str(min(nortes)),
            "minz": "0",
            "maxx": str(max(estes)),
            "maxy": str(max(nortes)),
            "maxz": "0",
        },
    )
    temporal = ET.SubElement(extension, "temporal")
    extremos = metadatos.fecha.split("/")
    if len(extremos) == 2:
        periodo = ET.SubElement(temporal, "period")
        agregar_texto_xml(periodo, "start", extremos[0])
        agregar_texto_xml(periodo, "end", extremos[1])
    else:
        agregar_texto_xml(temporal, "instant", extremos[0])
    agregar_texto_xml(raiz, "history", "Generado automáticamente desde el catálogo RSA.")

    arbol = ET.ElementTree(raiz)
    ET.indent(arbol, space="  ")
    arbol.write(ruta, encoding="utf-8", xml_declaration=True)
    print(f"[GENERADO]  {ruta}", flush=True)
    return ruta


def generar_shapefile(
    ruta_csv: Path, metadatos: Metadatos
) -> tuple[int, list[Path]]:
    df = leer_csv(ruta_csv)
    registros = list(eventos_rsa(df))  # Valida todo antes de crear archivos parciales.
    if not registros:
        raise ValueError("El CSV no contiene eventos cuya Fuente sea RSA.")

    # Regla de salida: siempre junto al catálogo fuente, sin excepciones.
    ruta_csv = ruta_csv.resolve()
    ruta_base = ruta_csv.parent / ruta_csv.stem
    print(f"[SALIDA] Carpeta destino: {ruta_base.parent}", flush=True)
    metadatos.validar()
    if metadatos.sistema_referencia_coordenadas_crs != NOMBRE_CRS:
        raise ValueError(f"El generador está configurado para {NOMBRE_CRS}.")

    # Los auxiliares se escriben en la misma ruta base que usa pyshp. De este
    # modo no dependen del directorio de ejecución actual del programa.
    ruta_prj = Path(f"{ruta_base}.prj")
    ruta_cpg = Path(f"{ruta_base}.cpg")
    ruta_metadata = escribir_metadatos(ruta_base, metadatos, len(registros))
    ruta_qmd = escribir_metadatos_qgis(ruta_base, metadatos, registros)
    print(f"[GENERANDO] {ruta_prj}", flush=True)
    # WKT1_ESRI ofrece compatibilidad con versiones antiguas de QGIS y evita
    # el mensaje "proyección no válida" que puede producir el WKT2 moderno.
    ruta_prj.write_text(CRS_SALIDA.to_wkt(version="WKT1_ESRI"), encoding="ascii")
    print(f"[GENERADO]  {ruta_prj}", flush=True)
    print(f"[GENERANDO] {ruta_cpg}", flush=True)
    ruta_cpg.write_text("UTF-8", encoding="ascii")
    print(f"[GENERADO]  {ruta_cpg}", flush=True)

    rutas_shape = [
        Path(f"{ruta_base}.shp"),
        Path(f"{ruta_base}.shx"),
        Path(f"{ruta_base}.dbf"),
    ]
    for ruta in rutas_shape:
        print(f"[GENERANDO] {ruta}", flush=True)
    with shapefile.Writer(str(ruta_base), shapeType=shapefile.POINT, encoding="utf-8") as sf:
        # Datos numéricos del evento, necesarios para consulta y análisis GIS.
        sf.field("Latitud", "F", size=12, decimal=6)
        sf.field("Longitud", "F", size=13, decimal=6)
        sf.field("Prof_km", "F", size=12, decimal=3)
        sf.field("Magnitud", "F", size=8, decimal=2)
        # Lista exacta de metadatos solicitados. Los nombres de más de diez
        # caracteres se abrevian porque DBF limita los nombres a 10 caracteres.
        sf.field("Titulo", "C", size=254)
        sf.field("Resumen", "C", size=254)
        sf.field("Fecha", "C", size=30)
        sf.field("Idioma", "C", size=20)
        sf.field("Pal_clave", "C", size=100)
        sf.field("CRS", "C", size=80)
        sf.field("Categoria", "C", size=80)
        sf.field("Creador", "C", size=80)
        sf.field("Contacto", "C", size=120)
        sf.field("Licencia", "C", size=254)
        for identificador, latitud, longitud, profundidad, magnitud, fecha_gmt, ubicacion in registros:
            este, norte = TRANSFORMADOR_UTM_17S.transform(longitud, latitud)
            sf.point(este, norte)
            lugar = ubicacion or "localización registrada en el catálogo"
            instante = fecha_gmt or "fecha GMT no disponible"
            titulo_evento = f"Evento sísmico RSA {identificador}"
            resumen_evento = f"Evento sísmico localizado en {lugar}, registrado por la RSA."
            sf.record(
                latitud,
                longitud,
                profundidad,
                magnitud,
                titulo_evento,
                resumen_evento,
                instante,
                "Español",
                "sismo",
                NOMBRE_CRS,
                "",
                "RSA",
                "redsismica@ucuenca.edu.ec",
                "",
            )
    for ruta in rutas_shape:
        if ruta.is_file():
            print(f"[GENERADO]  {ruta}", flush=True)
        else:
            print(f"[FALTANTE]  {ruta}", flush=True)

    archivos = [
        *rutas_shape,
        ruta_prj,
        ruta_cpg,
        ruta_metadata,
        ruta_qmd,
    ]
    faltantes = [str(ruta) for ruta in archivos if not ruta.is_file()]
    if faltantes:
        raise OSError("No se generaron los siguientes archivos: " + ", ".join(faltantes))
    return len(registros), archivos


def seleccionar_archivo() -> Path | None:
    from PyQt5.QtWidgets import QFileDialog

    archivo, _ = QFileDialog.getOpenFileName(
        None,
        "Seleccionar catálogo *_cat.csv",
        "",
        "Catálogos RSA (*_cat.csv)",
    )
    return Path(archivo) if archivo else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", type=Path, help="Catálogo CSV de entrada")
    parser.add_argument("--metadatos", type=Path, help="JSON con los metadatos")
    args = parser.parse_args(argv)

    app = None
    try:
        ruta_csv = args.csv
        if ruta_csv is None:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance() or QApplication(sys.argv)
            ruta_csv = seleccionar_archivo()
            if ruta_csv is None:
                return 0

        if args.metadatos:
            datos = json.loads(args.metadatos.read_text(encoding="utf-8-sig"))
            metadatos = Metadatos.desde_diccionario(datos)
        else:
            print(
                "[METADATOS] Construyendo automáticamente desde el catálogo.",
                flush=True,
            )
            metadatos = metadatos_sugeridos(leer_csv(ruta_csv), ruta_csv.stem)
            print(f"[METADATOS] Título: {metadatos.titulo}", flush=True)
            print(f"[METADATOS] Resumen: {metadatos.resumen_abstract}", flush=True)
            print(f"[METADATOS] Fecha GMT: {metadatos.fecha}", flush=True)
            print(f"[METADATOS] Idioma: {metadatos.idioma}", flush=True)
            print(
                f"[METADATOS] Palabras clave: {', '.join(metadatos.palabras_clave)}",
                flush=True,
            )
            print(
                "[METADATOS] CRS: "
                f"{metadatos.sistema_referencia_coordenadas_crs}",
                flush=True,
            )
            print(f"[METADATOS] Categoría: {metadatos.categoria}", flush=True)
            print(f"[METADATOS] Creador: {metadatos.creador_autor}", flush=True)
            print(f"[METADATOS] Contacto: {metadatos.contacto}", flush=True)
            print(f"[METADATOS] Licencia: {metadatos.licencia}", flush=True)

        cantidad, archivos = generar_shapefile(ruta_csv, metadatos)
        mensaje = (
            f"Shapefile generado con {cantidad} eventos RSA.\n\n"
            f"Carpeta:\n{archivos[0].parent}\n\nArchivos:\n"
            + "\n".join(ruta.name for ruta in archivos)
        )
        print(mensaje)
        if app is not None:
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.information(None, "Generación completada", mensaje)
        return 0
    except Exception as exc:
        mensaje = f"No se pudo completar el shapefile:\n{exc}"
        print(mensaje, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        if app is not None:
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.critical(None, "Error al generar", mensaje)
        return 1
    finally:
        if app is not None:
            app.quit()


if __name__ == "__main__":
    raise SystemExit(main())
