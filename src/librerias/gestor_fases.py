import json
import os
from obspy.signal.trigger import classic_sta_lta, trigger_onset

class GestorFases:
    def __init__(self, fases_detectadas=None, al_actualizar_callback=None):
        self.linea_seleccionada = None
        self.arrastrando = False
        self.fases = fases_detectadas if fases_detectadas else {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}
        self.colores = {'P': 'red', 'S': 'darkorange', 'Coda': 'green'}
        self.lineas = {'P': None, 'S': None, 'Coda': None}
        self.textos = {'P': None, 'S': None, 'Coda': None}
        self.texto_info = None
        self.al_actualizar_callback = al_actualizar_callback

    def al_presionar(self, evento, ax, canvas):
        if evento.xdata is None or evento.inaxes is None:
            return
        if not evento.dblclick:
            x = evento.xdata
            tipo_fase = self.encontrar_fase_mas_cercana(x, ax)
            if tipo_fase is not None:
                self.linea_seleccionada = self.lineas.get(tipo_fase)
                self.arrastrando = True
                self.tipo_fase = tipo_fase
            else:
                self.arrastrando = False
        else:
            self.doble_click(evento, ax, canvas)
        canvas.draw()

    def al_soltar(self, evento):
        if self.arrastrando and self.al_actualizar_callback:
            try:
                self.al_actualizar_callback()
            except Exception:
                pass
        self.linea_seleccionada = None
        self.tipo_fase = None
        self.arrastrando = False

    def al_mover(self, evento, canvas):
        if self.linea_seleccionada is not None and self.arrastrando:
            if evento.xdata is not None and evento.inaxes is not None:
                x = float(evento.xdata)
                self.linea_seleccionada.set_xdata([x, x])
                if self.tipo_fase in self.fases:
                    self.fases[self.tipo_fase][0] = round(x, 3)
                if self.al_actualizar_callback:
                    try:
                        self.al_actualizar_callback()
                    except Exception:
                        pass
                canvas.draw()

    def doble_click(self, evento, ax, canvas):
        if evento.xdata is None or evento.inaxes is None:
            return
        x = float(evento.xdata)
        tipo_fase = self.encontrar_fase_mas_cercana(x, ax)
        if tipo_fase is not None:
            self.eliminar_fase_por_tipo(tipo_fase, ax, canvas)
            self.fases[tipo_fase] = [0.0]
        else:
            tipo_fase = self.obtener_tipo_fase()
            if tipo_fase:
                self.fases[tipo_fase] = [x]
                if self.lineas.get(tipo_fase) is not None:
                    try:
                        self.lineas[tipo_fase].remove()
                    except Exception:
                        pass
                self.lineas[tipo_fase] = ax.axvline(
                    x, color=self.colores[tipo_fase], linestyle='--', label=f'Fase {tipo_fase}'
                )
        if self.al_actualizar_callback:
            try:
                self.al_actualizar_callback()
            except Exception:
                pass
        canvas.draw()

    def encontrar_fase_mas_cercana(self, x, ax):
        if x is None or ax is None:
            return None
        tipo_fase_mas_cercana = None
        try:
            x_min, x_max = ax.get_xlim()
            distancia_minima = abs(x_max - x_min) * 0.02  # 2% de tolerancia del ancho de ventana
        except Exception:
            distancia_minima = 1.0

        menor_distancia = float('inf')
        for tipo_fase in ['P', 'S', 'Coda']:
            tiempos = self.fases.get(tipo_fase, [])
            if tiempos and len(tiempos) > 0 and tiempos[0] > 0:
                tiempo = tiempos[0]
                distancia = abs(tiempo - x)
                if distancia < distancia_minima and distancia < menor_distancia:
                    menor_distancia = distancia
                    tipo_fase_mas_cercana = tipo_fase
        return tipo_fase_mas_cercana

    def eliminar_fase_por_tipo(self, tipo_fase, ax, canvas):
        self.fases[tipo_fase] = [0.0]
        if self.lineas.get(tipo_fase) is not None:
            try:
                self.lineas[tipo_fase].remove()
            except Exception:
                pass
            self.lineas[tipo_fase] = None
        if self.textos.get(tipo_fase) is not None:
            try:
                self.textos[tipo_fase].remove()
            except Exception:
                pass
            self.textos[tipo_fase] = None
        canvas.draw()

    def obtener_tipo_fase(self):
        # Determina qué tipo de fase agregar, en orden de P, S, luego Coda
        if self.fases.get('P', [0.0]) == [0.0] or not self.fases.get('P'):
            return 'P'
        elif self.fases.get('S', [0.0]) == [0.0] or not self.fases.get('S'):
            return 'S'
        elif self.fases.get('Coda', [0.0]) == [0.0] or not self.fases.get('Coda'):
            return 'Coda'
        return None

    def inicializar_fases(self, ax):
        for tipo_fase in ['P', 'S', 'Coda']:
            tiempos = self.fases.get(tipo_fase, [])
            if tiempos and len(tiempos) > 0 and tiempos[0] > 0:
                tiempo = tiempos[0]
                if self.lineas.get(tipo_fase) is not None:
                    try:
                        self.lineas[tipo_fase].remove()
                    except Exception:
                        pass
                self.lineas[tipo_fase] = ax.axvline(
                    tiempo, color=self.colores[tipo_fase], linestyle='--', label=f'Fase {tipo_fase}'
                )

    def obtener_fases(self):
        return self.fases

