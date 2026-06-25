"""
Script no-interactivo para generar JSON automáticamente a la carpeta /json
Ejecutado por GitHub Actions semanalmente.
"""

import os
import sys
from datetime import datetime
from generacion import generar_fichas, mezclar_y_renumerar
from exportar_json import exportar_json

# Carpeta de salida
CARPETA_JSON = os.path.join(os.path.dirname(__file__), "..", "json")
os.makedirs(CARPETA_JSON, exist_ok=True)

# Parámetros por defecto
modo = "verdades"
dificultad = "omerta"  # Cambiar si quieres otro nivel
n_fichas = 10
n_sosp_fijo = 0  # Aleatorio
cantidad_fija = None
seed = None
distrito_modo = 0  # Cíclico

print(f"Generando fichas ({dificultad}) → {CARPETA_JSON}")

fichas = generar_fichas(
    n_fichas=n_fichas,
    modo=modo,
    cantidad_fija=cantidad_fija,
    seed=seed,
    n_sosp_fijo=n_sosp_fijo,
    dificultad=dificultad,
    distrito_modo=distrito_modo,
)

if not fichas:
    print("❌ Error: no se generaron fichas")
    sys.exit(1)

mezclar_y_renumerar(fichas, distrito_modo=distrito_modo)

# Generar con timestamp
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
ruta_json = os.path.join(CARPETA_JSON, f"fichas_{ts}.json")
exportar_json(fichas, ruta_json)

print(f"✅ {len(fichas)} fichas generadas en {ruta_json}")
