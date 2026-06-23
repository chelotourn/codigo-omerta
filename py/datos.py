"""
Datos del juego: sospechosos, distritos y constantes de configuración.
"""

PORC_MAX_REPETICION_CARTA = 0.18  # tope hardcodeado: ninguna carta puede aparecer
                                   # en más del 18% de las fichas de una misma corrida

MOSTRAR_INFORME_CARTAS = True      # si True, imprime al final de cada corrida el listado
                                   # de cartas ordenado por cantidad de apariciones

# ── Carta Omertá ────────────────────────────────────────────────────────────
# Tope de cuántas cartas puede silenciar Omertá en una misma ficha. Si el
# apagón generado supera este número, la ficha se descarta y se reintenta.
TOPE_CARTAS_APAGADAS_OMERTA = 4

# Mínimo de cartas que deben quedar "vivas" (no silenciadas) en la ficha,
# para garantizar que sigue habiendo señal deductiva suficiente.
MINIMO_CARTAS_VIVAS_TRAS_OMERTA = 2

SOSPECHOSOS_1 = {
    1: {"nombre": "El Notario",   "clase": "rico",  "edad": "viejo"},
    2: {"nombre": "La Aprendiz",  "clase": "media", "edad": "joven"},
    3: {"nombre": "El Carnicero", "clase": "pobre",  "edad": "mediana"},
    4: {"nombre": "El Coronel",   "clase": "rico",  "edad": "mediana"},
    5: {"nombre": "La Vidente",   "clase": "pobre",  "edad": "viejo"},
    6: {"nombre": "El Médico",    "clase": "media", "edad": "joven"},
    7: {"nombre": "El Heredero",  "clase": "rico", "edad": "joven"},    
    8: {"nombre": "El Crupier",   "clase": "media", "edad": "viejo"},   
    9: {"nombre": "El Vagabundo", "clase": "pobre", "edad": "mediana"},    
}

SOSPECHOSOS_2 = {
    1: {"nombre": "El Notario",   "clase": "pobre", "edad": "joven"},
    2: {"nombre": "La Aprendiz",  "clase": "rico",  "edad": "viejo"},
    3: {"nombre": "El Carnicero", "clase": "media", "edad": "joven"},
    4: {"nombre": "El Coronel",   "clase": "media", "edad": "viejo"},
    5: {"nombre": "La Vidente",   "clase": "rico",  "edad": "mediana"},
    6: {"nombre": "El Médico",    "clase": "rico", "edad": "viejo"},
    7: {"nombre": "El Heredero",  "clase": "pobre", "edad": "mediana"},
    8: {"nombre": "El Crupier",   "clase": "media", "edad": "mediana"},
    9: {"nombre": "El Vagabundo", "clase": "pobre", "edad": "joven"},
}

# ── Distritos ─────────────────────────────────────────────────────────────
# Un "Distrito" es un pool de sospechosos: mismos nombres/ids que el otro
# distrito, pero con atributos (clase/edad) distintos. Cada ficha generada
# queda asociada a UN distrito (guardado en Ficha.distrito), y tanto el TXT
# como el JSON declaran a qué distrito pertenece.
DISTRITOS = {
    1: {"nombre": "Distrito Industrial", "sospechosos": SOSPECHOSOS_1},
    2: {"nombre": "Distrito Comercial",  "sospechosos": SOSPECHOSOS_2},
}

def sospechosos_del_distrito(distrito_id: int) -> dict:
    return DISTRITOS[distrito_id]["sospechosos"]

def nombre_distrito(distrito_id: int) -> str:
    return DISTRITOS[distrito_id]["nombre"]

# Alias mutable: durante la generación de fichas (generar_fichas) este nombre
# se reasigna en cada intento al pool del distrito que corresponda, de forma
# que todo el código de validación existente (que referencia SOSPECHOSOS a
# secas) siga funcionando sin tener que tocar cada chequeo individualmente.
SOSPECHOSOS = SOSPECHOSOS_1
