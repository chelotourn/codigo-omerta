"""
Generador de fichas de caso — Juego de deducción noir
Busca por fuerza bruta combinaciones con solución única.
Genera salida en TXT legible y JSON técnico.
"""

import random
import json
import os
import math
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

# ─────────────────────────────────────────────
#  DATOS DEL JUEGO
# ─────────────────────────────────────────────

PORC_MAX_REPETICION_CARTA = 0.16  # tope hardcodeado: ninguna carta puede aparecer
                                   # en más del 30% de las fichas de una misma corrida

MOSTRAR_INFORME_CARTAS = True      # si True, imprime al final de cada corrida el listado
                                   # de cartas ordenado por cantidad de apariciones
                                   
SOSPECHOSOS = {
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



# ── Helpers para lógica meta ─────────────────────────────────────────────────
# Estas funciones inspeccionan las cartas asignadas a otros sospechosos
# y evalúan si sus declaraciones son verdad/mentira dado el culpable.
# Se usan en la categoría "meta".

def _cartas_de_categoria(asignacion_global, categoria, sus):
    """Devuelve los sospechoso_ids que tienen carta de la categoría dada."""
    if asignacion_global is None:
        return []
    return [sid for sid, cid in asignacion_global.items()
            if CATEGORIAS_CARTAS.get(cid) == categoria]

def _declarante_miente(sid, c, sus, asignacion_global):
    """True si el sospechoso sid miente dado el culpable c."""
    if asignacion_global is None or sid not in asignacion_global:
        return False
    return not evaluar_carta_simple(asignacion_global[sid], c, sid, sus)

# Set de cartas actualmente en evaluación — usado para detectar recursión.
# Cuando evaluar_carta_simple detecta que ya está evaluando una carta,
# devuelve True (asume verdad) para cortar el ciclo.
_VISITADOS_EVAL: set = set()

def evaluar_carta_simple(carta_id, culpable_id, declarante_id, sus):
    """Evaluación con protección anti-recursión via set de visitados.
    Para cartas de veracidad (21-30) y meta (57-73): usa CARTAS (evaluación completa)
    pero registra la carta en _VISITADOS_EVAL antes de entrar, y si ya está registrada
    (ciclo), devuelve True para cortar la recursión sin crashear."""
    if carta_id in range(21, 31) or carta_id in range(57, 73):
        # Evaluación completa con protección anti-recursión
        key = (carta_id, culpable_id, declarante_id)
        if key in _VISITADOS_EVAL:
            return True   # ciclo detectado: cortar con True (conservador)
        _VISITADOS_EVAL.add(key)
        try:
            fn = CARTAS.get(carta_id)
            if fn is None:
                return True
            return fn(culpable_id, declarante_id, sus)
        finally:
            _VISITADOS_EVAL.discard(key)
    fn = CARTAS_BASE.get(carta_id)
    if fn is None:
        return True
    return fn(culpable_id, declarante_id, sus)

# Cartas base (sin meta — las meta se agregan más apobre)
CARTAS_BASE = {}

# ASIGNACION_EVAL es un dict mutable que evaluar_carta() inyecta antes de
# llamar a cualquier lambda que inspeccione las cartas de otros sospechosos.
# Es seguro porque la evaluación es completamente síncrona.
ASIGNACION_EVAL = {}   # {sospechoso_id: carta_id} — se sobreescribe por ficha

def _meta(fn):
    """Convierte una función f(c, s, sus, asig) en lambda(c, s, sus) leyendo ASIGNACION_EVAL."""
    return lambda c, s, sus: fn(c, s, sus, ASIGNACION_EVAL)

# Llenamos CARTAS_BASE primero; luego CARTAS = CARTAS_BASE | CARTAS_META
_CB = CARTAS_BASE   # alias corto

# ── ACUSACIÓN (1–10) ─────────────────────────────────────────────────────────
_CB[1]  = lambda c, s, sus: c == 3          # acusa al Carnicero
_CB[2]  = lambda c, s, sus: c == 1          # acusa al Notario
_CB[3]  = lambda c, s, sus: c == 6          # acusa al Médico
_CB[4]  = lambda c, s, sus: c == 5          # acusa a la Vidente
_CB[5]  = lambda c, s, sus: c == 2          # acusa a la Aprendiz
_CB[6]  = lambda c, s, sus: c == 4          # acusa al Coronel
_CB[11] = lambda c, s, sus: c == 7          # acusa al Heredero
_CB[7]  = lambda c, s, sus: c in (1, 4)     # acusa a Notario o Coronel
_CB[8]  = lambda c, s, sus: c in (3, 6)     # acusa a Carnicero o Médico
_CB[9]  = lambda c, s, sus: c in (2, 5)     # acusa a Aprendiz o Vidente
_CB[10] = lambda c, s, sus: (sus[c]["edad"] == "viejo" and sus[c]["clase"] == "rico")  # viejo y rico

# ── DEFENSA (12–20) ──────────────────────────────────────────────────────────
_CB[12] = lambda c, s, sus: c != 1                        # el Notario no fue
_CB[13] = lambda c, s, sus: c != 3                        # el Carnicero no fue
_CB[14] = lambda c, s, sus: c != 4                        # el Coronel no fue
_CB[15] = lambda c, s, sus: c != 6                        # el Médico no fue
_CB[16] = lambda c, s, sus: c not in (1, 4)               # ni Notario ni Coronel
_CB[17] = lambda c, s, sus: c not in (2, 5)               # ni Aprendiz ni Vidente
_CB[18] = lambda c, s, sus: c not in (3, 6)               # ni Carnicero ni Médico
_CB[19] = lambda c, s, sus: sus[c]["clase"] != "rico"    # el culpable no es rico
_CB[20] = lambda c, s, sus: sus[c]["edad"] == "joven"     # el culpable es joven

# ── VERACIDAD (21–30) ────────────────────────────────────────────────────────
# Estas cartas afirman algo sobre la honestidad de *otros* sospechosos presentes.
# Su verdad se evalúa inspeccionando si las cartas de esos otros son efectivamente
# verdaderas o falsas dado el culpable c. Usan ASIGNACION_EVAL como las meta.

def _todos_con_atributo_mienten(c, s, sus, asig, attr, valor):
    """Verdad si TODOS los sospechosos con atributo=valor (excluyendo al declarante)
    tienen cartas que son mentira dado c. Requiere al menos uno presente."""
    targets = [sid for sid in asig if sid != s and sus[sid][attr] == valor]
    if not targets:
        return False
    return all(not evaluar_carta_simple(asig[sid], c, sid, sus) for sid in targets)

def _alguno_con_atributo_miente(c, s, sus, asig, attr, valor):
    """Verdad si AL MENOS UNO con atributo=valor (excl. declarante) miente."""
    targets = [sid for sid in asig if sid != s and sus[sid][attr] == valor]
    if not targets:
        return False
    return any(not evaluar_carta_simple(asig[sid], c, sid, sus) for sid in targets)

def _todos_con_atributo_dicen_verdad(c, s, sus, asig, attr, valor):
    """Verdad si TODOS con atributo=valor (excl. declarante) dicen verdad."""
    targets = [sid for sid in asig if sid != s and sus[sid][attr] == valor]
    if not targets:
        return False
    return all(evaluar_carta_simple(asig[sid], c, sid, sus) for sid in targets)

def _acusadores_del_declarante_mienten(c, s, sus, asig):
    """Verdad si todos los que tienen carta de acusación que apunta al declarante s mienten.
    'Carta de acusación que apunta a s' = carta cuya lambda devuelve True solo cuando c==s.
    Aproximación: cartas 1–6 apuntan a sospechoso fijo; chequeamos si su verdad con c==s es True
    y con cualquier otro candidato es False. En la práctica: la carta es verdad <=> c==s."""
    acusadores = [sid for sid, cid in asig.items()
                  if sid != s and CATEGORIAS_CARTAS.get(cid) == "acusación"
                  and evaluar_carta_simple(cid, s, sid, sus)]   # la carta acusa a s
    if not acusadores:
        return False   # nadie me acusa: afirmación vacía → falso (más interesante)
    return all(not evaluar_carta_simple(asig[sid], c, sid, sus) for sid in acusadores)

# 21: "Los viejos de esta sala mienten" — verdad si todos los viejos presentes (excl. declarante) mienten
_CB[21] = _meta(lambda c, s, sus, asig: _todos_con_atributo_mienten(c, s, sus, asig, "edad", "viejo"))

# 22: "Los ricos ocultan la verdad" — verdad si todos los ricos presentes (excl. declarante) mienten
_CB[22] = _meta(lambda c, s, sus, asig: _todos_con_atributo_mienten(c, s, sus, asig, "clase", "rico"))

# 23: "Los viejos en esta sala son honestos" — verdad si todos los viejos dicen verdad
_CB[23] = _meta(lambda c, s, sus, asig: _todos_con_atributo_dicen_verdad(c, s, sus, asig, "edad", "viejo"))

# 24: "Los pobres no blefan" — verdad si todos los pobres presentes dicen verdad
_CB[24] = _meta(lambda c, s, sus, asig: _todos_con_atributo_dicen_verdad(c, s, sus, asig, "clase", "pobre"))

# 25: "La experiencia no perdona: los de mediana edad tienen algo que esconder" — verdad si alguno de mediana edad miente
_CB[25] = _meta(lambda c, s, sus, asig: _alguno_con_atributo_miente(c, s, sus, asig, "edad", "mediana"))

# 26: "Quien me acusa directamente está mintiendo" — verdad si todos los que tienen carta de acusación directa al declarante mienten
_CB[26] = _meta(lambda c, s, sus, asig: _acusadores_del_declarante_mienten(c, s, sus, asig))

# 27: "Los de clase media no tienen secretos" — verdad si todos los de clase media dicen verdad
_CB[27] = _meta(lambda c, s, sus, asig: _todos_con_atributo_dicen_verdad(c, s, sus, asig, "clase", "media"))

# 28: "Al menos uno de los jóvenes está mintiendo" — verdad si algún joven presente miente
_CB[28] = _meta(lambda c, s, sus, asig: _alguno_con_atributo_miente(c, s, sus, asig, "edad", "joven"))

# 29: "Los pobres en esta sala no son tan inocentes como parecen" — verdad si algún pobre miente
_CB[29] = _meta(lambda c, s, sus, asig: _alguno_con_atributo_miente(c, s, sus, asig, "clase", "pobre"))

# 30: "quienes dicen la verdad esta noche podrían comprarla" — verdad si todos los ricos presentes dicen verdad
_CB[30] = _meta(lambda c, s, sus, asig:
    _todos_con_atributo_dicen_verdad(c, s, sus, asig, "clase", "rico")
)

# ── descriptiva (31–40) ───────────────────────────────────────────────────────────
_CB[31] = lambda c, s, sus: sus[c]["clase"] == "rico"
_CB[32] = lambda c, s, sus: sus[c]["clase"] == "media"
_CB[33] = lambda c, s, sus: sus[c]["clase"] == "pobre"
_CB[34] = lambda c, s, sus: sus[c]["edad"] == "joven"
_CB[35] = lambda c, s, sus: sus[s]["edad"] == "mediana" and sus[c]["edad"] == "mediana"
_CB[36] = lambda c, s, sus: sus[c]["edad"] == "viejo"
_CB[37] = lambda c, s, sus: 4 in sus and sus[c]["clase"] == sus[4]["clase"]   # misma clase que el Coronel
_CB[38] = lambda c, s, sus: 2 in sus and sus[c]["edad"] == sus[2]["edad"]       # misma edad que la Aprendiz
_CB[39] = lambda c, s, sus: sus[c]["clase"] != "rico" and sus[c]["edad"] != "viejo"   # ni rico ni viejo
_CB[40] = lambda c, s, sus: sus[c]["clase"] == "rico" and sus[c]["edad"] == "mediana" # rico y de mediana edad

# ── DUDA (41–50) ─────────────────────────────────────────────────────────────
# Cartas que parecen neutras pero siempre devuelven True o dependen de condiciones débiles
_CB[41] = lambda c, s, sus: s != c  # ambigua — falsa si la usa el culpable
_CB[42] = lambda c, s, sus: True
_CB[43] = lambda c, s, sus: True
_CB[44] = lambda c, s, sus: True
_CB[45] = lambda c, s, sus: False
_CB[48] = lambda c, s, sus: sus[c]["edad"] != "mediana"     # no fue alguien mediana edad
_CB[47] = lambda c, s, sus: sus[c]["edad"] != "joven"      # no fue alguien joven
_CB[48] = lambda c, s, sus: sus[c]["clase"] != "pobre"     # no fue alguien pobre
_CB[49] = lambda c, s, sus: 1 in sus and 3 in sus and 4 in sus and c not in (1, 3, 4)  # descarta tres
_CB[50] = lambda c, s, sus: 2 in sus and 5 in sus and 6 in sus and c not in (2, 5, 6)             # descarta los otros tres

# ── GRUPAL (51–56) ───────────────────────────────────────────────────────────
_CB[51] = lambda c, s, sus: 4 in sus and 1 in sus and c in (4, 1)    # Coronel y Notario, uno de ellos
_CB[52] = lambda c, s, sus: 2 in sus and 3 in sus and c in (2, 3)    # Aprendiz y Carnicero
_CB[53] = lambda c, s, sus: 5 in sus and 6 in sus and c in (5, 6)    # Vidente y Médico
_CB[54] = lambda c, s, sus: sum(1 for sid in sus if sus[sid]["clase"] == "rico") >= 2 and sus[c]["clase"] == "rico"
_CB[55] = lambda c, s, sus: sum(1 for sid in sus if sus[sid]["edad"] == "viejo") >= 2 and sus[c]["edad"] == "viejo"
_CB[56] = lambda c, s, sus: len(sus) >= 5 and sus[c]["edad"] == "mediana"

# ── META (57–64) — razona sobre las OTRAS declaraciones ──────────────────────
# Estas cartas son verdad o mentira según si su afirmación SOBRE LAS DEMÁS cartas
# es correcta dado el culpable c.

def _hay_defensor_mintiendo(c, s, sus, asig):
    """¿Algún sospechoso con carta de defensa está mintiendo?
    Si no hay defensores en la partida, la afirmación es falsa (no hay nada que sostenerla)."""
    defensores = [sid for sid, cid in asig.items() if CATEGORIAS_CARTAS.get(cid) == "defensa"]
    if not defensores:
        return False
    return any(not evaluar_carta_simple(asig[sid], c, sid, sus) for sid in defensores)

def _todos_acusadores_verdad(c, s, sus, asig):
    """¿Todos los que acusan dicen verdad? Si no hay acusadores, falso (la afirmación no aplica)."""
    acusadores = [sid for sid, cid in asig.items() if CATEGORIAS_CARTAS.get(cid) == "acusación"]
    if not acusadores:
        return False   # no hay acusaciones: la carta no tiene base, es falsa
    return all(evaluar_carta_simple(asig[sid], c, sid, sus) for sid in acusadores)

def _culpable_se_defiende(c, s, sus, asig):
    """¿El culpable tiene carta de defensa?"""
    return asig.get(c) is not None and CATEGORIAS_CARTAS.get(asig[c]) == "defensa"

# Cache por sesión de evaluación para _mayoria_miente — se limpia en tiene_solucion_unica.
# Evita la explosión combinatoria: _mayoria_miente evalúa todas las cartas de la ficha,
# que a su vez llaman a _mayoria_miente, multiplicando el trabajo innecesariamente.
# Clave (culpable, declarante): el resultado ahora depende de quién declara, porque
# el declarante se excluye de su propio conteo (ver _valor más abajo).
_MAYORIA_CACHE: dict = {}

def _mayoria_miente(c, s, sus, asig):
    """¿Más de la mitad de las DEMÁS declaraciones (sin contar al propio declarante)
    son mentira? El declarante habla de lo que "escuchó" de los otros, no de lo que
    dijo él mismo, así que su propia carta (esta misma, #60) queda fuera del conteo.
    Para cartas meta/veracidad de otros, las evalúa directo con la lambda
    (ASIGNACION_EVAL ya está inyectado) en vez de devolver True por defecto.
    Memoizado por (culpable, declarante) dentro de cada sesión de evaluación."""
    clave = (c, s)
    if clave in _MAYORIA_CACHE:
        return _MAYORIA_CACHE[clave]
    def _valor(sid, cid):
        if cid in range(21, 31) or cid in range(57, 73):
            fn = CARTAS.get(cid)
            if fn is None:
                return True
            try:
                return fn(c, sid, sus)
            except Exception:
                return True
        return evaluar_carta_simple(cid, c, sid, sus)
    otros = [(sid, cid) for sid, cid in asig.items() if sid != s]
    if not otros:
        resultado = False  # sin nadie más a quien "escuchar", la afirmación es vacía
    else:
        mentiras = sum(1 for sid, cid in otros if not _valor(sid, cid))
        resultado = mentiras > len(otros) / 2
    _MAYORIA_CACHE[clave] = resultado
    return resultado

def _alguien_con_fisica_acierta(c, s, sus, asig):
    """¿Alguna carta descriptiva dice verdad?"""
    for sid, cid in asig.items():
        if CATEGORIAS_CARTAS.get(cid) == "descriptiva" and evaluar_carta_simple(cid, c, sid, sus):
            return True
    return False

def _declarante_es_unico_mentiroso(c, s, sus, asig):
    """Carta narrativa: siempre es mentira.
    El declarante afirma ser el único mentiroso — lo cual es una paradoja deliberada.
    Solo se asigna en fichas con >=2 verdades para no crear inconsistencia lógica."""
    return False

def _hay_contradiccion_acusacion_defensa(c, s, sus, asig):
    """¿Hay al menos una acusación verdadera Y una defensa verdadera que se contradicen?"""
    acus_true = any(evaluar_carta_simple(cid, c, sid, sus)
                    for sid, cid in asig.items() if CATEGORIAS_CARTAS.get(cid) == "acusación")
    def_true  = any(evaluar_carta_simple(cid, c, sid, sus)
                    for sid, cid in asig.items() if CATEGORIAS_CARTAS.get(cid) == "defensa")
    return acus_true and def_true

def _sin_duda_y_viejos_mienten(c, s, sus, asig):
    """Verdad cuando no hay ninguna carta de duda en la ficha Y todos los viejos
    presentes (excl. declarante) mienten.
    Si no hay viejos presentes (excl. declarante), la condicion es vacua: se retorna
    False para que la carta no sea trivialmente verdadera."""
    # Condicion 1: ninguna carta de duda en la asignacion
    if any(CATEGORIAS_CARTAS.get(cid) == "duda" for cid in asig.values()):
        return False
    # Condicion 2: todos los viejos (excl. declarante) mienten
    viejos = [sid for sid in asig if sid != s and sus[sid]["edad"] == "viejo"]
    if not viejos:
        return False  # sin viejos la afirmacion es vacia -> falso (no informativa)
    return all(not evaluar_carta_simple(asig[sid], c, sid, sus) for sid in viejos)



# Registro de las 8 cartas meta
CARTAS_META = {
    57: _meta(lambda c, s, sus, asig: _hay_defensor_mintiendo(c, s, sus, asig)),
    58: _meta(lambda c, s, sus, asig: _todos_acusadores_verdad(c, s, sus, asig)),
    59: _meta(lambda c, s, sus, asig: not _culpable_se_defiende(c, s, sus, asig)),
    60: _meta(lambda c, s, sus, asig: _mayoria_miente(c, s, sus, asig)),
    61: _meta(lambda c, s, sus, asig: _alguien_con_fisica_acierta(c, s, sus, asig)),
    62: _meta(lambda c, s, sus, asig: _declarante_es_unico_mentiroso(c, s, sus, asig)),
    63: _meta(lambda c, s, sus, asig: _hay_contradiccion_acusacion_defensa(c, s, sus, asig)),
}

# ── INDIRECTAS (65–72) — confesión condicional indirecta ─────────────────────
# Usan evaluar_carta_simple para no recursar.
# Las cartas que referencian al Crupier (8), Vagabundo (9) o Heredero (7)
# solo se pueden asignar si ese sospechoso está presente en la partida.

def _hay_acusacion_al_culpable(c, s, sus, asig):
    """¿Alguna carta de acusación apunta al culpable y es verdad?"""
    return any(
        CATEGORIAS_CARTAS.get(cid) == "acusación" and evaluar_carta_simple(cid, c, sid, sus)
        for sid, cid in asig.items()
    )

def _hay_media_mintiendo(c, s, sus, asig):
    """¿Algún sospechoso de clase media (excl. declarante) miente?"""
    return any(
        sus[sid]["clase"] == "media" and sid != s
        and not evaluar_carta_simple(asig[sid], c, sid, sus)
        for sid in asig
    )

def _culpable_tiene_defensa(c, s, sus, asig):
    """¿El culpable tiene carta de defensa?"""
    return c in asig and CATEGORIAS_CARTAS.get(asig[c]) == "defensa"

def _hay_inocente_mintiendo(c, s, sus, asig):
    """¿Algún inocente (no culpable) miente?"""
    return any(
        sid != c and not evaluar_carta_simple(asig[sid], c, sid, sus)
        for sid in asig
    )

def _mayoria_miente_simple(c, s, sus, asig):
    """¿Más de la mitad miente? (versión simple, sin recursión en meta)"""
    mentiras = sum(1 for sid, cid in asig.items() if not evaluar_carta_simple(cid, c, sid, sus))
    return mentiras > len(asig) / 2

CARTAS_INDIRECTAS = {
    # Reglas de validez para cartas indirectas (A → B):
    #   - La carta es VERDAD  cuando A es verdadera Y B es verdadera  (A AND B).
    #   - La carta es MENTIRA cuando A es verdadera Y B es falsa       (A AND NOT B).
    #   - Cuando A es falsa  → la carta es FALSA; B queda indeterminada
    #     (no se considera ni verdadera ni falsa para el resto de la deducción).
    #   - Cuando A referencia a un sospechoso ausente → INVÁLIDA (None → ficha descartada).
    #   - El declarante no puede ser parte de A ni de B (se filtra en el pool de asignación).
    #
    # La lambda devuelve:
    #   True  → A AND B            (la indirecta se cumple, aporta información)
    #   False → A AND NOT B        (la indirecta falla, también aporta información)
    #   False → NOT A              (A falsa → carta falsa; B no se evalúa)
    #   None  → sospechoso ausente (ficha inválida, descartada por el generador)

    64: _meta(lambda c, s, sus, asig: _sin_duda_y_viejos_mienten(c, s, sus, asig)),
    # 65: "Escucho a quienes se defienden y quienes describen al culpable, pero si unos dicen la verdad los otros mienten por miedo o por vergüenza"
    # A = hay al menos una carta de defensa Y al menos una carta descriptiva en la ficha
    # B = exactamente una defensa es verdad Y exactamente una descriptiva es mentira, o viceversa
    #     (viceversa: exactamente una defensa es mentira Y exactamente una descriptiva es verdad)
    # Verdad jugable: A AND B
    # A falsa → carta falsa, B indeterminada
    65: _meta(lambda c, s, sus, asig:
        (lambda defensas, descriptivas:
            None if not defensas or not descriptivas else (
                (lambda n_def_v, n_desc_v:
                    (n_def_v == 1 and (len(descriptivas) - n_desc_v) == 1) or
                    ((len(defensas) - n_def_v) == 1 and n_desc_v == 1)
                )(
                    sum(1 for sid, cid in defensas if evaluar_carta_simple(cid, c, sid, sus)),
                    sum(1 for sid, cid in descriptivas if evaluar_carta_simple(cid, c, sid, sus)),
                )
            )
        )(
            [(sid, cid) for sid, cid in asig.items() if CATEGORIAS_CARTAS.get(cid) == "defensa"],
            [(sid, cid) for sid, cid in asig.items() if CATEGORIAS_CARTAS.get(cid) == "descriptiva"],
        )
    ),
    # 66: "Si el Vagabundo miente, el culpable es pobre"
    # A = NOT eval(vagabundo)   B = sus[c]["clase"]=="pobre"
    # Verdad jugable: A AND B  → el Vagabundo miente Y el culpable es pobre
    # A falsa (Vagabundo dice verdad) → carta falsa, B indeterminada
    # Vagabundo ausente → None (ficha inválida)
    66: _meta(lambda c, s, sus, asig:
        (None if 9 not in asig else
         (not evaluar_carta_simple(asig[9], c, 9, sus)
          and sus[c]["clase"] == "pobre"))
    ),
    # 67: "Si el Heredero dice verdad, el culpable no es rico"
    # A = eval(heredero)   B = sus[c]["clase"]!="rico"
    # Verdad jugable: A AND B  → el Heredero dice verdad Y el culpable no es rico
    # A falsa (Heredero miente) → carta falsa, B indeterminada
    # Heredero ausente → None (ficha inválida)
    67: _meta(lambda c, s, sus, asig:
        (None if 7 not in asig else
         (evaluar_carta_simple(asig[7], c, 7, sus)
          and sus[c]["clase"] != "rico"))
    ),
    # 68: "Si el Crupier miente, quien lo hizo no era joven"
    # A = NOT eval(Crupier)   B = sus[c]["edad"]!="joven"
    # Verdad jugable: A AND B  → el Crupier miente Y el culpable no es joven
    # A falsa (Crupier dice verdad) → carta falsa, B indeterminada
    # Crupier ausente → None (ficha inválida)
    68: _meta(lambda c, s, sus, asig:
        (None if 8 not in asig else
         (not evaluar_carta_simple(asig[8], c, 8, sus)
          and sus[c]["edad"] != "joven"))
    ),
    # 69: "Si alguien de clase media miente, el culpable es joven"
    # A = hay_media_mintiendo   B = sus[c]["edad"]=="joven"
    # Verdad jugable: A AND B  → hay alguien de clase media mintiendo Y el culpable es joven
    # A falsa (nadie de media miente) → carta falsa (False), B indeterminada
    69: _meta(lambda c, s, sus, asig:
        _hay_media_mintiendo(c, s, sus, asig)
        and sus[c]["edad"] == "joven"
    ),
    # 70: "Si el culpable se defiende, al menos un inocente también miente"
    # A = culpable_tiene_defensa   B = hay_inocente_mintiendo
    # Verdad jugable: A AND B  → el culpable tiene carta de defensa Y hay un inocente mintiendo
    # A falsa (culpable no tiene defensa) → carta falsa (False), B indeterminada
    70: _meta(lambda c, s, sus, asig:
        _culpable_tiene_defensa(c, s, sus, asig)
        and _hay_inocente_mintiendo(c, s, sus, asig)
    ),
    # 71: "Si hay más mentiras que verdades, el culpable es viejo"
    # A = mayoria_miente   B = sus[c]["edad"]=="viejo"
    # Verdad jugable: A AND B  → hay mayoría de mentiras Y el culpable es viejo
    # A falsa (no hay mayoría de mentiras) → carta falsa (False), B indeterminada
    71: _meta(lambda c, s, sus, asig:
        _mayoria_miente_simple(c, s, sus, asig)
        and sus[c]["edad"] == "viejo"
    ),
    # 72: "Si nadie acusa directamente al culpable, es porque este los está presionando. Pero los pobres no tienen nada que perder y dirán la verdad."
    # A = nadie acusa directamente al culpable (ninguna carta de acusación es verdad dado c)
    # B = todos los pobres presentes (excl. declarante) dicen verdad
    # Verdad jugable: A AND B  → ninguna acusación apunta al culpable Y todos los pobres dicen verdad
    # A falsa (hay al menos una acusación verdadera contra el culpable) → carta falsa, B indeterminada
    # No referencia a ningún sospechoso nominado → nunca devuelve None
    72: _meta(lambda c, s, sus, asig:
        (not any(
            CATEGORIAS_CARTAS.get(cid) == "acusación" and evaluar_carta_simple(cid, c, sid, sus)
            for sid, cid in asig.items()
        ))
        and (lambda pobres: len(pobres) > 0 and all(evaluar_carta_simple(asig[sid], c, sid, sus) for sid in pobres))(
            [sid for sid in asig if sid != s and sus[sid]["clase"] == "pobre"]
        )
    ),
}

CARTAS = {**CARTAS_BASE, **CARTAS_META, **CARTAS_INDIRECTAS}

# ── Validación de cartas indirectas ──────────────────────────────────────────
# Evalúa si la condición A de cada carta indirecta presente en la ficha
# es verdadera para el culpable dado. Si A es falsa, la carta es vacuamente
# verdadera (el jugador lee algo que no sucede en la ficha) → ficha inválida.
# Si el sospechoso referenciado por A no está en la partida → ficha inválida.

def _antecedente_indirecta(carta_id: int, culpable_id: int, declarante_id: int,
                            sus: dict, asig: dict) -> Optional[bool]:
    """
    Devuelve:
      True  → A es verdadera (la indirecta puede ser V o F según B)
      False → A es falsa (la carta es falsa; B queda indeterminada)
      None  → A referencia a un sospechoso ausente (ficha inválida)
    """
    c, s = culpable_id, declarante_id

    # Antecedentes por carta:
    if carta_id == 65:   # A = hay al menos una carta de defensa Y al menos una descriptiva en la ficha
        defensas     = [cid for cid in asig.values() if CATEGORIAS_CARTAS.get(cid) == "defensa"]
        descriptivas = [cid for cid in asig.values() if CATEGORIAS_CARTAS.get(cid) == "descriptiva"]
        if not defensas or not descriptivas: return None
        return True  # A no depende del culpable, solo de la presencia de las categorías
    if carta_id == 66:   # A = el Vagabundo miente
        if 9 not in asig: return None
        return not evaluar_carta_simple(asig[9], c, 9, sus)
    if carta_id == 67:   # A = el Heredero dice verdad
        if 7 not in asig: return None
        return evaluar_carta_simple(asig[7], c, 7, sus)
    if carta_id == 68:   # A = el Crupier miente
        if 8 not in asig: return None
        return not evaluar_carta_simple(asig[8], c, 8, sus)
    if carta_id == 69:   # A = hay alguien de clase media mintiendo
        return _hay_media_mintiendo(c, s, sus, asig)
    if carta_id == 70:   # A = el culpable tiene carta de defensa
        return _culpable_tiene_defensa(c, s, sus, asig)
    if carta_id == 71:   # A = mayoría miente
        return _mayoria_miente_simple(c, s, sus, asig)
    if carta_id == 72:   # A = nadie acusa directamente al culpable
        return not any(
            CATEGORIAS_CARTAS.get(cid) == "acusación" and evaluar_carta_simple(cid, c, sid, sus)
            for sid, cid in asig.items()
        )
    return True   # carta no indirecta: no aplica la restricción

def validar_indirectas_en_ficha(asignacion: dict, culpable_id: int, sus: dict) -> bool:
    """
    Devuelve True si ninguna carta indirecta de la ficha referencia a un sospechoso
    ausente (None). Las fichas con A falsa son válidas: la carta simplemente es falsa
    y B queda indeterminada, lo que aporta información deductiva al jugador.
    """
    ASIGNACION_EVAL.clear()
    ASIGNACION_EVAL.update(asignacion)
    for declarante_id, carta_id in asignacion.items():
        if carta_id not in CARTAS_INDIRECTAS:
            continue
        a = _antecedente_indirecta(carta_id, culpable_id, declarante_id, sus, asignacion)
        if a is None:
            return False
    return True

# Cartas que siempre devuelven True independientemente del culpable.
# No aportan información deductiva al jugador — se limita su uso por ficha.
CARTAS_SIEMPRE_VERDAD = {41, 42, 43, 44, 45}

TEXTOS_CARTAS = {
    # ACUSACIÓN
    1:  "El Carnicero lo hizo. Lo vi salir con las manos limpias y los ojos sucios.",
    2:  "El Notario. Nadie más conocía la hora exacta. Nadie más tenía motivo.",
    3:  "Solo el Médico sabe cómo borrar lo que no quiere que se encuentre.",
    4:  "La Vidente sabía lo que iba a pasar. Pero no creo en sus visiones, creo que lo planificó.",
    5:  "La Aprendiz aprendió demasiado rápido. Y alguien pagó el precio.",
    6:  "El Coronel fue. Lo delataron sus hábitos, no sus palabras.",
    7:  "Solo el Notario o el Coronel tenían acceso a esa habitación. Uno de ellos lo sabe.",
    8:  "El Carnicero o el Médico. Cualquiera de los dos tiene las manos entrenadas para esto.",
    9:  "Fue la Aprendiz o la Vidente. El instinto lo dice. Las pruebas, también.",
    10: "El asesino ya tenía la edad de quien no teme nada y el dinero de quien nunca tuvo que temerlo.",
    11: "Esto es cosa de niños ricos. Quizás algún capricho frívolo le fue negado.",
    # DEFENSA
    12: "El Notario no tiene el temple. Conozco a los que pueden hacer algo así. Él no.",
    13: "El Carnicero es muchas cosas. Un asesino no es una de ellas. Que quede claro.",
    14: "El Coronel lleva años protegiéndonos. Acusarlo es insultarnos a todos.",
    15: "El Médico juró no hacer daño. Y lo cumple. Eso no se finge.",
    16: "Ni el Notario ni el Coronel. Ambos estaban conmigo cuando ocurrió.",
    17: "Ni la Aprendiz ni la Vidente. Las dos tienen coartada. Yo mismo la verifiqué.",
    18: "Ni el Carnicero ni el Médico. Sus herramientas no cuadran con lo que vi.",
    19: "El culpable no era rico. Vi sus ropas. Menuda falta de gusto.",
    20: "Quien lo hizo era joven. Lo delataba el nerviosismo. La vejez da paciencia para el crimen.",
    # VERACIDAD
    21: "Esos viejos en la sala saben más de lo que dicen. Eligieron con cuidado que contar y que ocultar.",
    22: "Desconfíen de todos los demas ricos. El porte da una confianza que cuesta distinguir de la inocencia.",
    23: "A su edad los viejos ya no se gastan en mentir. No temen a la verdad.",
    24: "Los pobres no mienten pues hoy han comido bien. Yo les creo.",
    25: "La experiencia no se oculta. Quien tiene mediana edad ya ha aprendido a mentir y lo hará.",
    26: "Quien me acusa directamente está mintiendo. Eso solo puede significar que algo esconde.",
    27: "Los de clase media no mienten. Son de fiar.",
    28: "Los jóvenes de hoy no tienen respeto por la verdad. Al menos uno de ellos miente.",
    29: "Entre tanta gente pobre seguro hay algun mentiroso. Así es esta gente.",
    30: "Curiosamente, quienes dicen la verdad esta noche podrían perfectamente comprarla.",
    # descriptiva
    31: "El culpable era rico. Estoy seguro. El coche que abandonó la escena era de alta gama.",
    32: "El asesino no era rico ni pobre. Clase media. Alguien que pasa desapercibido. Eso ya dice algo.",
    33: "El asesino era pobre. Su aliento olía a mandarina. Nunca lo olvidaré.",
    34: "El culpable era joven. El crujido de sus pasos era ligero. La juventud tiene ese peso.",
    35: "Tenía mi misma edad, más o menos. Mediana. Lo vi en la forma de moverse.",
    36: "Quien lo hizo era viejo. El paso lento, la respiración pausada. Solo la edad da esa calma.",
    37: "El culpable era exactamente de la misma clase que el Coronel. Lo noto en su andar.",
    38: "Quien buscas tenía la misma edad que la Aprendiz. Joven. Demasiado joven para tanta frialdad.",
    39: "El culpable no era ni rico ni viejo. Lo que vi fue a alguien que podría confundirse con cualquiera.",
    40: "Era rico y de mediana edad. Esa combinación no abunda en esta sala.",
    # DUDA
    41: "Yo no he sido ni sé quién pudo hacerlo. Pero sé que lo volverá a hacer si no lo encontramos.",
    42: "Podría haber sido cualquiera. Cualquiera con suficiente razón para odiar.",
    43: "Hay cosas que no entiendo aún. Pero el culpable está en esta sala.",
    44: "Es inutil mentir, al final usted descubre la verdad.",
    45: "Me temo que no podrá resolver este caso Detective, el tiempo juega en su contra.",
    46: "Estoy seguro que alguien de clase media tendría mejores cosas que hacer. El resto quizás no.",
    47: "No fue alguien joven. La frialdad de esto requiere años que aún no se tienen.",
    48: "No fue alguien pobre. El reloj que tenía la victima era costoso y allí quedó",
    49: "Ni el Notario, ni el Carnicero, ni el Coronel. Los tres tienen algo en común: no pudieron.",
    50: "Ni la Aprendiz, ni la Vidente, ni el Médico. Ninguno de los tres tiene lo que hace falta.",
    # GRUPAL
    51: "El Coronel y el Notario llegaron juntos esa noche. Solo uno de ellos sabe por qué.",
    52: "La Aprendiz y el Carnicero se conocen de antes. Eso no es casualidad.",
    53: "La Vidente y el Médico compartían secretos. Alguno de esos secretos mató.",
    54: "Los ricos en esta sala se cubren entre sí. Uno lo hizo y no podra esconderlo.",
    55: "Los viejos se protegen. Es lo único que les queda. Uno de ellos debe ser el asesino.",
    56: "Somos un grupo grande, algunos demasiado jóvenes otros demasiado viejos, y luego está el asesino.",
    # META
    57: "Quien se defiende en esta sala está mintiendo. La inocencia no necesita tanto ruido.",
    58: "Cada acusación que escuché esta noche sonó a verdad. Eso debería asustarlos.",
    59: "El culpable no se está defendiendo. Eso es incluso más peligroso. Ande con cuidado.",
    60: "La mayoría de las declaraciones que escuché ahí hoy son puras mentiras. Calcule a quién conviene mentir.",
    61: "Al menos una descripción dicha en esta sala suena convincente. Aférrate a esa y te llevará al culpable.",
    62: "Hay uno solo que miente en esta sala. Solo uno. Y ese uno soy yo.",
    63: "Alguien acusa y alguien defiende, y ambos dicen la verdad. Eso es una contradicción. O es una trampa.",
    64: "No he escuchado una sola duda en esta sala, es como si los más reflexivos callaran, señal de que todos ellos mienten.",
    # INDIRECTAS
    65: "Escucho a quienes se defienden y quienes describen al culpable, pero si unos dicen la verdad los otros mienten por miedo o por vergüenza.",
    66: "Si el Vagabundo miente, entonces el asesino vino de abajo. La pobreza no es excusa, pero sí es pista.",
    67: "Si el Heredero no miente, podemos descartar a los ricos. La verdad de un rico tiene su precio.",
    68: "Si el Crupier miente, quien lo hizo no era joven. Los viejos saben cuándo callar y cuándo actuar.",
    69: "Cuando alguien de la clase media miente, suele ser por sentimentalismo. Ese viejo impulso de proteger a los más jóvenes.",
    70: "Si el culpable se defiende esta noche, algún inocente también miente para cubrirlo. La complicidad tiene sus reglas.",
    71: "Si en esta sala hay más mentiras que verdades, el culpable tiene años encima. La vejez enseña a esconderse.",
    72: "Si nadie acusa directamente al culpable, es porque este los está presionando. Pero los pobres no tienen nada que perder y dirán la verdad.",
}


CATEGORIAS_CARTAS = {
    1:  "acusación", 2:  "acusación", 3:  "acusación", 4:  "acusación", 5:  "acusación",
    6:  "acusación", 7:  "acusación", 8:  "acusación", 9:  "acusación", 10: "acusación",
    11: "acusación",
    12: "defensa",   13: "defensa",   14: "defensa",   15: "defensa",
    16: "defensa",   17: "defensa",   18: "defensa",   19: "defensa",   20: "defensa",
    21: "veracidad", 22: "veracidad", 23: "veracidad", 24: "veracidad", 25: "veracidad",
    26: "veracidad", 27: "veracidad", 28: "veracidad", 29: "veracidad", 30: "veracidad",
    31: "descriptiva",    32: "descriptiva",    33: "descriptiva",    34: "descriptiva",    35: "descriptiva",
    36: "descriptiva",    37: "descriptiva",    38: "descriptiva",    39: "descriptiva",    40: "descriptiva",
    41: "duda",      42: "duda",      43: "duda",      44: "duda",      45: "duda",
    46: "duda",      47: "duda",      48: "duda",      49: "duda",      50: "duda",
    51: "grupal",    52: "grupal",    53: "grupal",    54: "grupal",    55: "grupal",    56: "grupal",
    57: "meta",      58: "meta",      59: "meta",      60: "meta",
    61: "meta",      62: "meta",      63: "meta",      64: "indirecta",
    65: "indirecta", 66: "indirecta", 67: "indirecta", 68: "indirecta",
    69: "indirecta", 70: "indirecta", 71: "indirecta", 72: "indirecta",
}

# ─────────────────────────────────────────────
#  LÓGICA
# ─────────────────────────────────────────────

@dataclass
class Ficha:
    id: int
    n_sospechosos: int
    sospechosos: list
    asignacion: dict        # {sospechoso_id: carta_id}
    culpable: int
    modo: str               # "mentiras" | "verdades"
    cantidad: int
    dificultad: str = "urbano"   # "urbano" | "metropoli" | "omerta"

def evaluar_carta(carta_id: int, culpable_id: int, declarante_id: int, sus: dict,
                  asignacion: dict = None) -> bool:
    """Evaluación top-level: inyecta estado global y limpia visitados. Usar solo
    cuando se evalúa una carta aislada (exportación, debug). Para validación en
    bulk usar tiene_solucion_unica que hace el setup una sola vez por candidato."""
    if asignacion is not None:
        ASIGNACION_EVAL.clear()
        ASIGNACION_EVAL.update(asignacion)
    _VISITADOS_EVAL.clear()
    _MAYORIA_CACHE.clear()
    fn = CARTAS[carta_id]
    return fn(culpable_id, declarante_id, sus)

def _evaluar_sin_setup(carta_id: int, culpable_id: int, declarante_id: int, sus: dict) -> bool:
    """Evaluación sin setup — asume que ASIGNACION_EVAL y _VISITADOS_EVAL ya están listos.
    Usar solo dentro de tiene_solucion_unica donde el setup se hace una vez por candidato."""
    fn = CARTAS[carta_id]
    return fn(culpable_id, declarante_id, sus)

def contar_verdades(asignacion: dict, culpable_id: int, sus: dict) -> int:
    return sum(
        1 for sosp_id, carta_id in asignacion.items()
        if evaluar_carta(carta_id, culpable_id, sosp_id, sus, asignacion)
    )

def tiene_solucion_unica(asignacion: dict, sus: dict, modo: str, cantidad: int) -> Optional[int]:
    """Busca un único culpable que satisfaga el conteo de verdades/mentiras.
    Optimización: inyecta ASIGNACION_EVAL una sola vez por candidato (no por carta)
    y usa _evaluar_sin_setup para evitar el overhead de clear+update en cada carta."""
    n = len(sus)
    soluciones = []
    items = list(asignacion.items())   # materializar para no re-iterar el dict
    for candidato in sus:
        # Setup global una sola vez para este candidato
        ASIGNACION_EVAL.clear()
        ASIGNACION_EVAL.update(asignacion)
        _VISITADOS_EVAL.clear()
        _MAYORIA_CACHE.clear()
        verdades = sum(
            1 for sosp_id, carta_id in items
            if _evaluar_sin_setup(carta_id, candidato, sosp_id, sus)
        )
        mentiras = n - verdades
        if modo == "verdades" and verdades == cantidad:
            soluciones.append(candidato)
            if len(soluciones) > 1:
                return None   # ya hay más de uno: no es única, salir temprano
        elif modo == "mentiras" and mentiras == cantidad:
            soluciones.append(candidato)
            if len(soluciones) > 1:
                return None
    return soluciones[0] if len(soluciones) == 1 else None

def mezclar_y_renumerar(fichas: list) -> list:
    """
    Reordena las fichas al azar (in-place) y renumera sus IDs desde 1 en ese
    nuevo orden. Debe llamarse UNA sola vez por corrida, después de generar
    las fichas y antes de exportarlas, para que TXT y JSON queden con el
    mismo orden y la misma numeración.
    """
    random.shuffle(fichas)
    for i, f in enumerate(fichas, start=1):
        f.id = i
    return fichas

def validar_dificultad(asignacion: dict, dificultad: str) -> bool:
    """
    Valida que la ficha cumpla las restricciones de dificultad:
    - urbano   : sin cartas indirecta ni meta
    - metropoli: máximo 1 carta entre indirectas y meta
    - omerta   : requiere al menos 1 meta Y al menos 1 indirecta
    """
    categorias = [CATEGORIAS_CARTAS[cid] for cid in asignacion.values()]
    n_meta      = categorias.count("meta")
    n_indirecta = categorias.count("indirecta")

    if dificultad == "urbano":
        return n_meta == 0 and n_indirecta == 0
    elif dificultad == "metropoli":
        return (n_meta + n_indirecta) <= 1
    elif dificultad == "omerta":
        return n_meta >= 1 and n_indirecta >= 1
    return True   # dificultad desconocida: no filtrar


def validar_sin_solapamiento(asignacion: dict, sus: dict) -> bool:
    """
    Descarta fichas donde dos cartas son lógicamente equivalentes o redundantes
    para todos los sospechosos posibles, lo que hace imposible distinguirlas
    durante la deducción.

    Dos cartas solapan si producen el mismo valor de verdad (True/False) para
    todos los candidatos posibles. Se evalúan sin asignación global (cartas base)
    para no depender de otras cartas — las meta/veracidad se excluyen del chequeo
    ya que su evaluación varía con el contexto y no son redundantes por definición.

    Optimización: se precalcula el vector de verdad de cada carta una sola vez
    antes de comparar pares, evitando evaluaciones duplicadas.
    """
    EXCLUIDAS = set(range(21, 31)) | set(range(57, 73))  # veracidad, meta, indirectas
    cartas_chequeables = [
        (sid, cid) for sid, cid in asignacion.items()
        if cid not in EXCLUIDAS
    ]
    candidatos = list(sus.keys())

    # Precalcular vectores de verdad (una vez por carta, no por par)
    vectores = [
        tuple(evaluar_carta_simple(cid, c, sid, sus) for c in candidatos)
        for sid, cid in cartas_chequeables
    ]

    # Comparar pares de vectores ya calculados
    for i in range(len(vectores)):
        for j in range(i + 1, len(vectores)):
            if vectores[i] == vectores[j]:
                return False  # solapamiento detectado
    return True




def generar_fichas(n_fichas: int, modo: str, cantidad_fija: Optional[int],
                   max_intentos: int = 200_000, seed: Optional[int] = None,
                   n_sosp_fijo: int = 0, dificultad: str = "urbano") -> list:
    if seed is not None:
        random.seed(seed)

    ids_todos  = list(SOSPECHOSOS.keys())
    ids_cartas = list(CARTAS.keys())
    fichas = []
    intentos = 0
    fichas_vistas = set()

    # ── Límite de repeticiones por carta (diversidad) ────────────────────────
    # Se cuenta UNA vez por ficha aceptada (no por slot/sospechoso): si una carta
    # aparece dos veces en la misma ficha eso ya está bloqueado en el pool de abajo
    # ("cid not in cartas_usadas"), así que acá solo importa "en cuántas fichas
    # distintas de esta corrida ya apareció esta carta".
    # round() estándar (0.5 hacia arriba), no el "banker's rounding" de Python.
    limite_repeticion_carta = math.floor(PORC_MAX_REPETICION_CARTA * n_fichas + 0.5)
    limite_repeticion_carta = max(1, limite_repeticion_carta)  # nunca bloquear todo en corridas chicas
    fichas_por_carta = {cid: 0 for cid in ids_cartas}  # cuántas FICHAS (no slots) usaron cada carta

    print(f"\n  Buscando {n_fichas} fichas — modo {modo.upper()} — dificultad {dificultad.upper()} ...")
    print(f"  Límite de diversidad: cada carta en máx. {limite_repeticion_carta} ficha(s) de esta corrida ({int(PORC_MAX_REPETICION_CARTA*100)}%).")
    print("  " + "─" * 46)

    while len(fichas) < n_fichas and intentos < max_intentos:
        intentos += 1

        rango_sosp = {"urbano": (3, 5), "metropoli": (4, 6), "omerta": (5, 8)}[dificultad]
        n_sosp    = n_sosp_fijo if n_sosp_fijo >= rango_sosp[0] else random.randint(*rango_sosp)
        sosp_ids  = sorted(random.sample(ids_todos, n_sosp))
        sus       = {i: SOSPECHOSOS[i] for i in sosp_ids}
        # Asignar cartas una por una, filtrando por sospechoso receptor
        asignacion = {}
        cartas_usadas = set()
        valida = True
        for sid in sosp_ids:
            pool = [
                cid for cid in ids_cartas
                if cid not in cartas_usadas
                # Diversidad: la carta ya alcanzó su tope de fichas en esta corrida
                and fichas_por_carta[cid] < limite_repeticion_carta
                # Restricciones de presencia: el sospechoso nombrado debe estar en la partida
                and not (cid == 1  and 3 not in sosp_ids)
                and not (cid == 2  and 1 not in sosp_ids)
                and not (cid == 3  and 6 not in sosp_ids)
                and not (cid == 4  and 5 not in sosp_ids)
                and not (cid == 5  and 2 not in sosp_ids)
                and not (cid == 6  and 4 not in sosp_ids)
                and not (cid == 11  and 7 not in sosp_ids)
                and not (cid == 7  and not (1 in sosp_ids and 4 in sosp_ids))
                and not (cid == 8  and not (3 in sosp_ids and 6 in sosp_ids))
                and not (cid == 9  and not (2 in sosp_ids and 5 in sosp_ids))
                and not (cid == 12 and 1 not in sosp_ids)
                and not (cid == 13 and 3 not in sosp_ids)
                and not (cid == 14 and 4 not in sosp_ids)
                and not (cid == 15 and 6 not in sosp_ids)
                and not (cid == 16 and not (1 in sosp_ids and 4 in sosp_ids))
                and not (cid == 17 and not (2 in sosp_ids and 5 in sosp_ids))
                and not (cid == 18 and not (3 in sosp_ids and 6 in sosp_ids))
                and not (cid == 22 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["clase"] == "rico") < 2)
                and not (cid == 63 and len(sosp_ids) < 3)
                # Cartas meta: solo validas si la categoria que referencian esta presente en la asignacion parcial
                # #57 "quien se defiende miente" - necesita al menos 1 defensa ya asignada
                and not (cid == 57 and not any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "defensa"     for x in asignacion))
                # #26 "quien me acusa directamente está mintiendo" - solo válida si al menos una carta
                # ya asignada acusa directamente al declarante sid (cartas 1→3, 2→1, 3→6, 4→5, 5→2, 6→4, 11→7)
                and not (cid == 26 and not any(
                    CATEGORIAS_CARTAS.get(asignacion.get(x)) == "acusación"
                    and evaluar_carta_simple(asignacion[x], sid, x, sus)
                    for x in asignacion
                ))
                # #58 "todas las acusaciones son verdad" - necesita al menos 1 acusacion ya asignada
                and not (cid == 58 and not any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "acusación"   for x in asignacion))
                # #59 "el culpable no se defiende" - vacuamente verdadera sin defensas
                and not (cid == 59 and not any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "defensa"     for x in asignacion))
                # #61 "al menos un descriptivo es verdad" - necesita al menos 1 descriptiva ya asignada
                and not (cid == 61 and not any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "descriptiva" for x in asignacion))
                # #63 necesita acusacion + defensa ya asignadas
                and not (cid == 63 and not (
                    any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "acusación" for x in asignacion) and
                    any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "defensa"   for x in asignacion)
                ))
                # #64: requiere al menos 1 viejo presente (excl. declarante) y ninguna carta de duda ya asignada
                and not (cid == 64 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["edad"] == "viejo") < 1)
                and not (cid == 64 and any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "duda" for x in asignacion))
                # #65: necesita al menos 1 carta de defensa y al menos 1 descriptiva ya asignadas
                and not (cid == 65 and not (
                    any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "defensa"     for x in asignacion) and
                    any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "descriptiva" for x in asignacion)
                ))
                # #72: necesita al menos 1 acusación ya asignada (para que A sea evaluable)
                #      y al menos 1 sospechoso pobre en la partida (excl. declarante, para que B sea posible)
                and not (cid == 72 and not any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "acusación" for x in asignacion))
                and not (cid == 72 and not any(SOSPECHOSOS[x]["clase"] == "pobre" for x in sosp_ids if x != sid))
                # Cartas veracidad: texto en plural — requieren al menos 2 del grupo referenciado (excl. declarante)
                and not (cid == 21 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["edad"]  == "viejo")   < 2)
                and not (cid == 23 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["edad"]  == "viejo")   < 2)
                and not (cid == 24 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["clase"] == "pobre")   < 2)
                and not (cid == 25 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["edad"]  == "mediana") < 2)
                and not (cid == 27 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["clase"] == "media")   < 2)
                and not (cid == 28 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["edad"]  == "joven")   < 2)
                and not (cid == 29 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["clase"] == "pobre")   < 2)
                and not (cid == 30 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["clase"] == "rico")    < 2)
                and not (cid == 37 and 4 not in sosp_ids)
                and not (cid == 38 and 2 not in sosp_ids)
                and not (cid == 47 and not any(SOSPECHOSOS[x]["edad"] == "joven" for x in sosp_ids))
                # Cartas descriptivas: el atributo que afirman debe estar representado en la ficha
                and not (cid == 31 and not any(SOSPECHOSOS[x]["clase"] == "rico"    for x in sosp_ids))
                and not (cid == 32 and not any(SOSPECHOSOS[x]["clase"] == "media"   for x in sosp_ids))
                and not (cid == 33 and not any(SOSPECHOSOS[x]["clase"] == "pobre"   for x in sosp_ids))
                and not (cid == 34 and not any(SOSPECHOSOS[x]["edad"]  == "joven"   for x in sosp_ids))
                and not (cid == 35 and not any(SOSPECHOSOS[x]["edad"]  == "mediana" for x in sosp_ids))
                and not (cid == 36 and not any(SOSPECHOSOS[x]["edad"]  == "viejo"   for x in sosp_ids))
                and not (cid == 40 and not any(SOSPECHOSOS[x]["clase"] == "rico" and SOSPECHOSOS[x]["edad"] == "mediana" for x in sosp_ids))
                # Carta 39: "ni rico ni viejo" — necesita al menos 1 sospechoso que no sea rico ni viejo
                and not (cid == 39 and not any(SOSPECHOSOS[x]["clase"] != "rico" and SOSPECHOSOS[x]["edad"] != "viejo" for x in sosp_ids))
                # Cartas grupales: requieren pluralidad del grupo que referencian
                and not (cid == 54 and sum(1 for x in sosp_ids if SOSPECHOSOS[x]["clase"] == "rico")  < 2)
                and not (cid == 55 and sum(1 for x in sosp_ids if SOSPECHOSOS[x]["edad"]  == "viejo") < 2)
                and not (cid == 49 and not all(x in sosp_ids for x in (1, 3, 4)))
                and not (cid == 50 and not all(x in sosp_ids for x in (2, 5, 6)))
                and not (cid == 51 and not (1 in sosp_ids and 4 in sosp_ids))
                and not (cid == 52 and not (2 in sosp_ids and 3 in sosp_ids))
                and not (cid == 53 and not (5 in sosp_ids and 6 in sosp_ids))
                # Restricciones de tercera persona: no hablar de uno mismo
                and not (cid == 1  and sid == 3)
                and not (cid == 2  and sid == 1)
                and not (cid == 3  and sid == 6)
                and not (cid == 4  and sid == 5)
                and not (cid == 5  and sid == 2)
                and not (cid == 6  and sid == 4)
                and not (cid == 7  and sid in (1, 4))
                and not (cid == 8  and sid in (3, 6))
                and not (cid == 9  and sid in (2, 5))
                and not (cid == 11 and sid == 7)
                and not (cid == 12 and sid == 1)
                and not (cid == 13 and sid == 3)
                and not (cid == 14 and sid == 4)
                and not (cid == 15 and sid == 6)
                and not (cid == 16 and sid in (1, 4))
                and not (cid == 17 and sid in (2, 5))
                and not (cid == 18 and sid in (3, 6))
                and not (cid == 37 and sid == 4)
                and not (cid == 38 and sid == 2)
                and not (cid == 49 and sid in (1, 3, 4))
                and not (cid == 50 and sid in (2, 5, 6))
                and not (cid == 51 and sid in (1, 4))
                and not (cid == 52 and sid in (2, 3))
                and not (cid == 53 and sid in (5, 6))
                # Indirectas: no pueden asignarse al sospechoso que referencian
                # #65 ya no referencia a un sospechoso nombrado; restricciones se manejan abajo
                and not (cid == 66 and sid == 9)   # #66 referencia al Vagabundo
                and not (cid == 67 and sid == 7)   # #67 referencia al Heredero
                and not (cid == 68 and sid == 8)   # #68 referencia al Crupier
                # #72 ya no referencia a ningún sospechoso nominado → sin restricción de tercera persona
            ]
            if not pool:
                valida = False
                break
            cid = random.choice(pool)
            asignacion[sid] = cid
            cartas_usadas.add(cid)
        if not valida:
            continue

        # cantidad fija o aleatoria (mínimo según dificultad: urbano=1, metropoli=2, omerta=3)
        min_verdades = {"urbano": 1, "metropoli": 2, "omerta": 3}[dificultad]
        cantidad = cantidad_fija if cantidad_fija is not None else random.randint(min_verdades, n_sosp - 1)
        if cantidad >= n_sosp or cantidad < min_verdades:
            continue

        # Carta 62 es narrativa (siempre miente): solo válida con >=2 mentiras en la partida
        mentiras_en_partida = n_sosp - cantidad if modo == "verdades" else cantidad
        if 62 in asignacion.values() and mentiras_en_partida < 2:
            continue

        culpable_tentativo = tiene_solucion_unica(asignacion, sus, modo, cantidad)
        if culpable_tentativo is None:
            continue

        # Limitar cartas "siempre verdad" (no aportan info deductiva al jugador)
        # Máximo 1 por ficha para mantener la calidad deductiva
        n_vacias = sum(1 for cid in asignacion.values() if cid in CARTAS_SIEMPRE_VERDAD)
        if n_vacias > 1:
            continue

        # Validar restricciones de dificultad
        if not validar_dificultad(asignacion, dificultad):
            continue

        # Validar solapamiento lógico entre cartas
        # Descarta fichas donde dos cartas transmiten información equivalente o redundante,
        # lo que impide al jugador distinguirlas y rompe la deducción.
        if not validar_sin_solapamiento(asignacion, sus):
            continue

        culpable = culpable_tentativo

        # Validar cartas indirectas: descarta fichas donde A referencia a un
        # sospechoso ausente (None). Si A es falsa, la carta es falsa y B queda
        # indeterminada — esto es válido y aporta información deductiva.
        if not validar_indirectas_en_ficha(asignacion, culpable, sus):
            continue

        clave = (tuple(sosp_ids), tuple(sorted(asignacion.items())), culpable, modo, cantidad)
        if clave in fichas_vistas:
            continue
        fichas_vistas.add(clave)

        # Registrar el uso de cada carta de esta ficha (una vez por carta, sin
        # importar que dentro de la ficha ya no pueda repetirse) para el límite
        # de diversidad de la corrida.
        for cid_usado in set(asignacion.values()):
            fichas_por_carta[cid_usado] += 1

        fichas.append(Ficha(
            id=len(fichas) + 1,
            n_sospechosos=n_sosp,
            sospechosos=sosp_ids,
            asignacion=asignacion,
            culpable=culpable,
            modo=modo,
            cantidad=cantidad,
            dificultad=dificultad,
        ))
        print(f"  Ficha #{len(fichas):02d} encontrada  (intento {intentos})")

    print(f"\n  Total encontradas : {len(fichas)} / {n_fichas}")
    print(f"  Total intentos    : {intentos}")

    if MOSTRAR_INFORME_CARTAS and fichas:
        sep = "─" * 46
        usadas = {cid: cnt for cid, cnt in fichas_por_carta.items() if cnt > 0}
        ordenadas = sorted(usadas.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  {sep}")
        print(f"  INFORME DE CARTAS — apariciones por ficha")
        print(f"  {sep}")
        for cid, cnt in ordenadas:
            cat = CATEGORIAS_CARTAS.get(cid, "?")
            texto_corto = TEXTOS_CARTAS.get(cid, "")[:38].rstrip()
            print(f"  #{cid:02d} ({cat:<10}) [{cnt:>2}]  \"{texto_corto}...\"")
        print(f"  {sep}")
        no_usadas = [cid for cid, cnt in fichas_por_carta.items() if cnt == 0]
        if no_usadas:
            ids_str = ", ".join(f"#{c}" for c in sorted(no_usadas))
            print(f"  Sin usar ({len(no_usadas)}): {ids_str}")
        print(f"  {sep}")

    return fichas

# ─────────────────────────────────────────────
#  EXPORTACIÓN TXT
# ─────────────────────────────────────────────

W = 56  # ancho interior de la caja

REGLAMENTO = """\
══════════════════════════════════════════════════════════
  CABLE DE PREFECTURA: TELEGRAMA DEL COMISIONADO
══════════════════════════════════════════════════════════
 1. MISIÓN: Descubra al único asesino de entre los
    sospechosos de la lista.
 2. EVIDENCIA: Incluimos la cantidad EXACTA de
    verdades. El resto miente. No se fíe.
 3. INSTINTO: Un buen detective deduce más de una
    mentira que de una verdad.
    - Acusación Mentira (M) → El acusado es inocente.
    - Descripción Mentira (M) → El rasgo es descartado.
 4. NIEBLA GRIS: Los Inocentes mienten por muchas razones.
    Los Culpables pueden decir la verdad para despistar.
 5. CUIDE SU ESPALDA: Busque gente en quien confiar
    para resolver los casos más desafiantes.
══════════════════════════════════════════════════════════
"""

def linea(texto="", ancho=W, pad=2):
    """Línea interior centrada o alineada a la izquierda."""
    contenido = (" " * pad) + texto
    relleno   = ancho - len(contenido)
    return f"║{contenido}{' ' * max(relleno, 0)}║"

def separador(ancho=W):
    return f"╠{'═' * ancho}╣"

def tope_sup(ancho=W):
    return f"╔{'═' * ancho}╗"

def tope_inf(ancho=W):
    return f"╚{'═' * ancho}╝"

def wrap(texto: str, max_len: int = W - 8) -> list:
    """Parte el texto en líneas de max_len caracteres."""
    palabras = texto.split()
    lineas, actual = [], ""
    for p in palabras:
        if len(actual) + len(p) + (1 if actual else 0) <= max_len:
            actual = actual + (" " if actual else "") + p
        else:
            if actual:
                lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas

def ficha_a_txt(f: Ficha) -> str:
    sus = {i: SOSPECHOSOS[i] for i in f.sospechosos}
    etiqueta_modo = f"{f.cantidad} {f.modo} en la partida"
    bloques = []

    bloques.append(tope_sup())
    bloques.append(linea(f"FICHA DE CASO  #{f.id:02d}  [{f.dificultad.upper()}]"))
    bloques.append(linea(f"{f.n_sospechosos} sospechosos  │  {etiqueta_modo}"))
    bloques.append(separador())
    bloques.append(linea(f"{'#':<3} {'Sospechoso':<16} {'Clase':<8} {'Edad':<10} {'Carta'}"))
    bloques.append(separador())

    for sid in f.sospechosos:
        s = SOSPECHOSOS[sid]
        carta_id = f.asignacion[sid]
        fila = f"{sid:<3} {s['nombre']:<16} {s['clase']:<8} {s['edad']:<10} #{carta_id:02d}"
        bloques.append(linea(fila))

    bloques.append(separador())
    culp_nombre = SOSPECHOSOS[f.culpable]["nombre"]
    bloques.append(linea(f"CULPABLE: {f.culpable}  [{culp_nombre}]"))
    bloques.append(linea(f"          [NÚMERO OCULTO EN TINTA ROJA]"))
    bloques.append(separador())
    bloques.append(linea("DECLARACIONES  (V = verdad  M = mentira)"))
    bloques.append(separador())

    for sid in f.sospechosos:
        carta_id = f.asignacion[sid]
        texto    = TEXTOS_CARTAS[carta_id]
        verdad   = evaluar_carta(carta_id, f.culpable, sid, sus, f.asignacion)
        estado   = "V" if verdad else "M"
        nombre   = SOSPECHOSOS[sid]["nombre"]
        cat      = CATEGORIAS_CARTAS[carta_id]
        cabecera = f"[{estado}] #{carta_id:02d} ({cat})  —  {nombre}"
        bloques.append(linea(cabecera))
        for tl in wrap(texto):
            bloques.append(linea(f"     {tl}"))
        bloques.append(linea())

    bloques.append(tope_inf())
    return "\n".join(bloques)

def exportar_txt(fichas: list, ruta: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    cabecera = "\n".join([
        "═" * (W + 2),
        f"  FICHAS DE CASO  —  Juego de deducción noir",
        f"  Generado: {ts}   Total: {len(fichas)} fichas",
        "═" * (W + 2),
    ])
    cuerpo = "\n\n".join(ficha_a_txt(f) for f in fichas)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(REGLAMENTO + "\n" + cabecera + "\n\n" + cuerpo + "\n")
    print(f"\n  TXT guardado  →  {ruta}")

def ficha_a_txt_jugable(f: Ficha) -> str:
    """Versión jugable: sin culpable visible ni V/M en declaraciones."""
    sus = {i: SOSPECHOSOS[i] for i in f.sospechosos}
    bloques = []

    bloques.append(tope_sup())
    bloques.append(linea(f"FICHA DE CASO  #{f.id:02d}  [NIVEL {f.dificultad.upper()}]"))
    bloques.append(linea(f"{f.n_sospechosos} sospechosos  │  {f.cantidad} verdades en la partida"))
    bloques.append(separador())
    bloques.append(linea(f"{'#':<3} {'Sospechoso':<16} {'Clase':<8} {'Edad':<10} {'Carta'}"))
    bloques.append(separador())

    for sid in f.sospechosos:
        s = SOSPECHOSOS[sid]
        carta_id = f.asignacion[sid]
        fila = f"{sid:<3} {s['nombre']:<16} {s['clase']:<8} {s['edad']:<10} #{carta_id:02d}"
        bloques.append(linea(fila))

    bloques.append(separador())
    bloques.append(linea("DECLARACIONES"))
    bloques.append(separador())

    for sid in f.sospechosos:
        carta_id = f.asignacion[sid]
        texto    = TEXTOS_CARTAS[carta_id]
        nombre   = SOSPECHOSOS[sid]["nombre"]
        cat      = CATEGORIAS_CARTAS[carta_id]
        cabecera = f"#{carta_id:02d} ({cat})  —  {nombre}"
        bloques.append(linea(cabecera))
        for tl in wrap(texto):
            bloques.append(linea(f"     {tl}"))
        bloques.append(linea())

    bloques.append(tope_inf())
    return "\n".join(bloques)

def resumen_soluciones(fichas: list) -> str:
    """Resumen minimalista con culpable y V/M por ficha, al final del archivo jugable."""
    sep = "─" * (W + 2)
    lineas = [
        "",
        sep,
        "  SOLUCIONES",
        sep,
    ]
    for f in fichas:
        sus = {i: SOSPECHOSOS[i] for i in f.sospechosos}
        culp_nombre = SOSPECHOSOS[f.culpable]["nombre"]
        estados = []
        for sid in f.sospechosos:
            carta_id = f.asignacion[sid]
            verdad = evaluar_carta(carta_id, f.culpable, sid, sus, f.asignacion)
            estados.append("V" if verdad else "M")
        vm_str = " ".join(estados)
        lineas.append(f"  #{f.id:02d}  Culpable: {culp_nombre:<16}  [{vm_str}]")
    lineas.append(sep)
    return "\n".join(lineas)

def exportar_txt_jugable(fichas: list, ruta: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    cabecera = "\n".join([
        "═" * (W + 2),
        f"  FICHAS DE CASO  —  CÓDIGO OMERTÁ",
        f"  Generado: {ts}   Total: {len(fichas)} fichas",
        "═" * (W + 2),
    ])
    cuerpo = "\n\n".join(ficha_a_txt_jugable(f) for f in fichas)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(REGLAMENTO + "\n" + cabecera + "\n\n" + cuerpo + "\n")
        fh.write(resumen_soluciones(fichas) + "\n")
    print(f"  TXT jugable   →  {ruta}")

# ─────────────────────────────────────────────
#  EXPORTACIÓN JSON
# ─────────────────────────────────────────────

def ficha_a_dict(f: Ficha) -> dict:
    sus = {i: SOSPECHOSOS[i] for i in f.sospechosos}
    # Setup global una sola vez — igual que tiene_solucion_unica — para que las
    # cartas meta/veracidad se evalúen con el mismo contexto que usó la validación.
    # Usar evaluar_carta por separado limpiaba _MAYORIA_CACHE entre declaraciones,
    # lo que causaba que el conteo de es_verdad difiriera del campo `cantidad`.
    ASIGNACION_EVAL.clear()
    ASIGNACION_EVAL.update(f.asignacion)
    _VISITADOS_EVAL.clear()
    _MAYORIA_CACHE.clear()
    declaraciones = []
    for sid in f.sospechosos:
        carta_id = f.asignacion[sid]
        verdad   = _evaluar_sin_setup(carta_id, f.culpable, sid, sus)
        declaraciones.append({
            "sospechoso_id"  : sid,
            "sospechoso"     : SOSPECHOSOS[sid]["nombre"],
            "clase"         : SOSPECHOSOS[sid]["clase"],
            "edad"           : SOSPECHOSOS[sid]["edad"],
            "carta_id"       : carta_id,
            "carta_categoria": CATEGORIAS_CARTAS[carta_id],
            "carta_texto"    : TEXTOS_CARTAS[carta_id],
            "es_verdad"      : verdad,
        })
    return {
        "ficha_id"        : f.id,
        "n_sospechosos"   : f.n_sospechosos,
        "sospechosos_ids" : f.sospechosos,
        "modo"            : f.modo,
        "cantidad"        : f.cantidad,
        "dificultad"      : f.dificultad,
        "culpable_id"     : f.culpable,
        "culpable_nombre" : SOSPECHOSOS[f.culpable]["nombre"],
        "declaraciones"   : declaraciones,
    }

def exportar_json(fichas: list, ruta: str):
    datos = {
        "generado"    : datetime.now().isoformat(),
        "total_fichas": len(fichas),
        "fichas"      : [ficha_a_dict(f) for f in fichas],
    }
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)
    print(f"  JSON guardado →  {ruta}")

# ─────────────────────────────────────────────
#  INTERFAZ INTERACTIVA
# ─────────────────────────────────────────────

def pedir_entero(mensaje: str, minimo: int, maximo: int) -> int:
    while True:
        try:
            val = int(input(mensaje).strip())
            if minimo <= val <= maximo:
                return val
            print(f"  → Ingresá un número entre {minimo} y {maximo}.")
        except ValueError:
            print("  → Ingresá un número entero.")

def pedir_seed() -> Optional[int]:
    resp = input("\n  Seed aleatoria (Enter para omitir): ").strip()
    return int(resp) if resp.isdigit() else None

def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   GENERADOR DE FICHAS — CÓDIGO OMERTÁ        ║")
    print("╚══════════════════════════════════════════════╝")

    # El modo siempre es verdades
    modo = "verdades"

    # ── Nivel de dificultad ──
    print("\n  ¿Nivel de DIFICULTAD?")
    print("  [1] Urbano    (sin cartas meta ni indirectas)")
    print("  [2] Metrópoli (máximo 1 carta meta o indirecta)")
    print("  [3] Omertà    (requiere al menos 1 meta y 1 indirecta)")
    print("  [4] Mixta     (genera 3 JSON para sitio web, 10 fichas por nivel)")
    nivel = pedir_entero("  Elegí una opción [1-4]: ", minimo=1, maximo=4)

    # ── Modo Mixta: generación directa para sitio web ──
    if nivel == 4:
        print("\n  → Modo MIXTA: generando 10 fichas por dificultad...")
        print("  " + "─" * 46)
        carpeta = "."
        nombres = {"urbano": "fichas_urbano.json", "metropoli": "fichas_metro.json", "omerta": "fichas_omerta.json"}
        total = 0
        for dif in ("urbano", "metropoli", "omerta"):
            fichas = generar_fichas(
                n_fichas=10,
                modo=modo,
                cantidad_fija=None,
                seed=None,
                n_sosp_fijo=0,
                dificultad=dif,
            )
            if not fichas:
                print(f"\n  ✗ No se encontraron fichas para {dif.upper()}. Saltando.")
                continue
            mezclar_y_renumerar(fichas)
            ruta = os.path.join(carpeta, nombres[dif])
            exportar_json(fichas, ruta)
            total += len(fichas)
        print()
        print("╔══════════════════════════════════════════════╗")
        print(f"║  Listo. {total} fichas generadas en 3 archivos.     ║")
        print("╚══════════════════════════════════════════════╝")
        return

    dificultad = {1: "urbano", 2: "metropoli", 3: "omerta"}[nivel]
    print(f"  → Dificultad: {dificultad.upper()}.")

    # ── Cantidad de sospechosos ──
    rango_sosp_por_dif = {"urbano": (3, 5), "metropoli": (4, 6), "omerta": (5, 8)}
    sosp_min, sosp_max = rango_sosp_por_dif[dificultad]
    n_sosp_fijo = pedir_entero(
        f"\n  ¿Cuántos SOSPECHOSOS por ficha?\n"
        f"  [0] = aleatorio,  o ingresá [{sosp_min}-{sosp_max}]: ",
        minimo=0, maximo=sosp_max
    )
    if 0 < n_sosp_fijo < sosp_min:
        print(f"  → Valor inválido para dificultad {dificultad.upper()}, se usará aleatorio.")
        n_sosp_fijo = 0
    if n_sosp_fijo == 0:
        print(f"  → Cantidad de sospechosos aleatoria [{sosp_min}\u2013{sosp_max}] por ficha.")
    else:
        print(f"  → {n_sosp_fijo} sospechosos por ficha.")

    # ── Cantidad de verdades (solo si los sospechosos son fijos) ──
    min_verdades_dif = {"urbano": 1, "metropoli": 2, "omerta": 3}[dificultad]
    if n_sosp_fijo == 0:
        cantidad_fija = None
        print("  -> Cantidad de verdades aleatoria por ficha.")
    else:
        max_verdades = n_sosp_fijo - 1
        cantidad_fija = pedir_entero(
            f"\n  ¿Cuántas VERDADES por ficha?\n"
            f"  [0] = aleatorio,  o ingresá [{min_verdades_dif}-{max_verdades}]: ",
            minimo=0, maximo=max_verdades
        )
        if cantidad_fija == 0:
            print("  -> Cantidad de verdades aleatoria por ficha.")
            cantidad_fija = None
        elif cantidad_fija < min_verdades_dif:
            print(f"  -> Valor inválido para dificultad {dificultad.upper()}, se usará aleatorio.")
            cantidad_fija = None
        else:
            print(f"  -> {cantidad_fija} verdades por ficha.")

    # ── Cuántas fichas ──
    n_fichas = pedir_entero(
        "\n  ¿Cuántas fichas generar? \n  [1] = Jugar en pantalla, o ingresá [2–50] para generar dossier: ",
        minimo=1, maximo=1000
    )

    # ── Modo rápido: 1 ficha → pantalla, sin archivos, sin preguntas extra ──
    if n_fichas == 1:
        os.system('cls')
        print("\n  → Modo rápido: generando 1 ficha en pantalla (seed aleatoria).")
        fichas = generar_fichas(
            n_fichas=1,
            modo=modo,
            cantidad_fija=cantidad_fija,
            seed=None,
            n_sosp_fijo=n_sosp_fijo,
            dificultad=dificultad,
        )
        if not fichas:
            print("\n  No se encontraron fichas válidas. Probá con otros parámetros.")
            return
        print()
        print(ficha_a_txt_jugable(fichas[0]))

        # ── Botón de resolución ──────────────────────────────────────────────
        print()
        print(f"  {'─' * (W - 2)}")
        print(f"  Presioná [Enter] para revelar la solución.")
        respuesta = input("  → ").strip().upper()
        if respuesta == "S":
            return

        # Revelar culpable + V/M al estilo del modo jugable final
        f = fichas[0]
        sus = {i: SOSPECHOSOS[i] for i in f.sospechosos}
        culp_nombre = SOSPECHOSOS[f.culpable]["nombre"]

        print()
        print(f"  {'═' * (W - 2)}")
        print(f"  SOLUCIÓN")
        print(f"  {'═' * (W - 2)}")
        print(f"  Culpable: {f.culpable}  [{culp_nombre}]")
        print()
        print(f"  {'─' * (W - 2)}")
        print(f"  DECLARACIONES  (V = verdad  M = mentira)")
        print(f"  {'─' * (W - 2)}")

        for sid in f.sospechosos:
            carta_id = f.asignacion[sid]
            verdad   = evaluar_carta(carta_id, f.culpable, sid, sus, f.asignacion)
            estado   = "V" if verdad else "M"
            nombre   = SOSPECHOSOS[sid]["nombre"]
            cat      = CATEGORIAS_CARTAS[carta_id]
            texto    = TEXTOS_CARTAS[carta_id]
            cabecera = f"  [{estado}] #{carta_id:02d} ({cat})  —  {nombre}"
            print(cabecera)
            for tl in wrap(texto):
                print(f"       {tl}")
            print()

        print(f"  {'═' * (W - 2)}")
        return

    # ── Seed ──
    seed = pedir_seed()

    # ── Modo jugable ──
    jugable = pedir_entero(
        "\n  ¿Ofuscar Respuestas?\n"
        "  [0] No, [1] Sí: ",
        minimo=0, maximo=1
    ) == 1

    # ── Salida en directorio actual ──
    carpeta = "."
    ts_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_txt  = os.path.join(carpeta, f"fichas_{ts_archivo}.txt")
    ruta_json = os.path.join(carpeta, f"fichas_{ts_archivo}.json")

    # ── Generación ──
    fichas = generar_fichas(
        n_fichas=n_fichas,
        modo=modo,
        cantidad_fija=cantidad_fija,
        seed=seed,
        n_sosp_fijo=n_sosp_fijo,
        dificultad=dificultad,
    )

    if not fichas:
        print("\n  No se encontraron fichas válidas. Probá con otros parámetros.")
        return

    mezclar_y_renumerar(fichas)

    if jugable:
        exportar_txt_jugable(fichas, ruta_txt)
    else:
        exportar_txt(fichas, ruta_txt)
    exportar_json(fichas, ruta_json)

    print()
    print("╔══════════════════════════════════════════════╗")
    print(f"║  Listo. {len(fichas)} fichas generadas.{' ' * (22 - len(str(len(fichas))))}       ║")
    print("╚══════════════════════════════════════════════╝")

if __name__ == "__main__":
    main()
    while True:
        input()
