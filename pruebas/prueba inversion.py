import pygimli as pg
import pygimli.meshtools as mt
from pygimli.physics import ert
import matplotlib.pyplot as plt

# 1) Electrodos en línea
elecs = pg.utils.grange(start=0, end=20, n=21)
scheme = ert.createData(elecs=elecs, schemeName="dd")  # dipolo-dipolo

# 2) Modelo sintético: mundo + anomalía
world = mt.createWorld(start=[-5, 0], end=[25, -15], worldMarker=True)
anomalia = mt.createCircle(pos=[10, -5], radius=2, marker=2)
geom = world + anomalia

mesh = mt.createMesh(geom, quality=33)

# 3) Resistividades del modelo
rhomap = [
    [1, 100],   # fondo
    [2, 20]     # anomalía conductiva
]

# 4) Simulación de datos aparentes
data = ert.simulate(
    mesh,
    scheme=scheme,
    res=rhomap,
    noiseLevel=1,
    noiseAbs=1e-6,
    seed=42
)

# 5) Inversión
mgr = ert.ERTManager()
inv = mgr.invert(data, lam=20, verbose=True)

# 6) Mostrar resultado
ax1, cb1 = mgr.showResult(cMap="Spectral_r", label="Resistividad invertida (ohm.m)")
plt.show()

print("Inversión terminada correctamente")