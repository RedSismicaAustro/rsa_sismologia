import json
import os
from obspy.signal.trigger import classic_sta_lta, trigger_onset

class GestorFases:
    def __init__(self, fases_detectadas=None):
        self.linea_seleccionada = None
        self.arrastrando = False
        self.fases = fases_detectadas if fases_detectadas else {'P': [0.0], 'S': [0.0], 'Coda': [0.0]}
        self.colores = {'P': 'red', 'S': 'blue', 'Coda': 'green'}
        self.lineas = {'P': None, 'S': None, 'Coda': None}
        self.textos = {'P': None, 'S': None, 'Coda': None}
        self.texto_info = None
        

    def al_presionar(self, evento, ax, canvas):
        #print(f"Evento presionado: {evento}")
        if not evento.dblclick:
            x = evento.xdata
            tipo_fase = self.encontrar_fase_mas_cercana(x, ax)
            if tipo_fase is not None:
                # Iniciar arrastre
                self.linea_seleccionada = self.lineas[tipo_fase]
                self.arrastrando = True
                self.tipo_fase = tipo_fase
                #print(f"Fase {tipo_fase} seleccionada para arrastrar")
            else:
                self.arrastrando = False
        else:
            self.doble_click(evento, ax, canvas)
        canvas.draw()


    def al_soltar(self, evento):
        if self.arrastrando:
            #print("Fase movida")
            pass
        else:
            #print("Clic realizado")
            pass
        self.linea_seleccionada = None
        self.tipo_fase = None
        self.arrastrando = False


    def al_mover(self, evento, canvas):
        if self.linea_seleccionada is not None and self.arrastrando:
            # Verificar si el evento está dentro de los ejes
            if evento.inaxes == canvas.figure.gca():
                #print("Movimiento detectado")
                
                x = evento.xdata
                self.linea_seleccionada.set_xdata([x, x])  # Mueve la línea a la nueva posición
                self.fases[self.tipo_fase][0] = x
                #print(f"Fase {self.tipo_fase} movida a posición {x}")
                canvas.draw()

    def doble_click(self, evento, ax, canvas):
        x = evento.xdata
        tipo_fase = self.encontrar_fase_mas_cercana(x, ax)
        if tipo_fase is not None:
            # Borrar la fase más cercana dentro del margen y asignar valor 0
            self.eliminar_fase_por_tipo(tipo_fase, ax, canvas)
            self.fases[tipo_fase] = [0.0]
            #print(f"Fase {tipo_fase} eliminada y asignada a 0")
        else:
            # Graficar la primera fase que tenga valor 0 usando obtener_tipo_fase()
            tipo_fase = self.obtener_tipo_fase()
            if tipo_fase:
                self.fases[tipo_fase][0] = x
                self.lineas[tipo_fase] = ax.axvline(x, color=self.colores[tipo_fase], linestyle='--', label=f'Fase {tipo_fase}')
                #print(f"Fase {tipo_fase} agregada en la posición {x}")
        canvas.draw()


    def encontrar_fase_mas_cercana(self, x,ax):
        tipo_fase_mas_cercana = None
        for tipo_fase in ['P', 'S', 'Coda']:
            if self.fases[tipo_fase] and self.fases[tipo_fase][0] > 0:
                tiempo = self.fases[tipo_fase][0]
                x_min, x_max = ax.get_xlim()#
                distancia_minima=(x_max - x_min) * 0.01  # Proporción del rango total de x para calcular la distancia mínima
                distancia = abs(tiempo - x)
                if distancia < distancia_minima:
                    tipo_fase_mas_cercana = tipo_fase
        #print('Fase mas cercana', tipo_fase_mas_cercana)
        return tipo_fase_mas_cercana

    def eliminar_fase_por_tipo(self, tipo_fase, ax, canvas):
        self.fases[tipo_fase] = [0.0]
        if self.lineas[tipo_fase] is not None:
            self.lineas[tipo_fase].remove()
            self.lineas[tipo_fase] = None
        if self.textos[tipo_fase] is not None:
            self.textos[tipo_fase].remove()
            self.textos[tipo_fase] = None
        canvas.draw()

    def obtener_tipo_fase(self):
        # Determina qué tipo de fase agregar, en orden de P, S, luego Coda
        if self.fases['P'] == [0.0]:
            return 'P'
        elif self.fases['S'] == [0.0]:
            return 'S'
        else:
            return 'Coda'


    def inicializar_fases(self, ax):
        for tipo_fase in ['P', 'S', 'Coda']:
            if self.fases[tipo_fase] and self.fases[tipo_fase][0] > 0:
                tiempo = self.fases[tipo_fase][0]
                if self.lineas[tipo_fase] is not None:
                    self.lineas[tipo_fase].remove()
                self.lineas[tipo_fase] = ax.axvline(tiempo, color=self.colores[tipo_fase], linestyle='--')

    def obtener_fases(self):
        return self.fases

