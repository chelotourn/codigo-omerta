"""
Definición de las 73 cartas del juego: lógica de verdad/mentira de cada una,
sus categorías, sus textos narrativos, y la maquinaria de evaluación
(incluyendo Omertá y las cartas meta/indirectas que inspeccionan otras
declaraciones de la misma ficha).
"""

from typing import Optional

# ── Helpers para lógica meta ─────────────────────────────────────────────────
# evaluar_carta_simple inspecciona las cartas asignadas a otros sospechosos
# y evalúa si sus declaraciones son verdad/mentira dado el culpable.
# Se usa en la categoría "meta".

# Set de cartas actualmente en evaluación — usado para detectar recursión.
# Cuando evaluar_carta_simple detecta que ya está evaluando una carta,
# devuelve True (asume verdad) para cortar el ciclo.
_VISITADOS_EVAL: set = set()

def evaluar_carta_simple(carta_id, culpable_id, declarante_id, sus):
    """Evaluación con protección anti-recursión via set de visitados.
    Para cartas de veracidad (21-30), meta/indirecta (57-72) y la carta
    especial Omertá (73): usa CARTAS (evaluación completa) pero registra la
    carta en _VISITADOS_EVAL antes de entrar, y si ya está registrada
    (ciclo), devuelve True para cortar la recursión sin crashear."""
    if carta_id in range(21, 31) or carta_id in range(57, 73) or carta_id == ID_CARTA_OMERTA:
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
_CB[7]  = lambda c, s, sus: c in (8, 9)     # acusa a El Vagabundo o Crupier
_CB[8]  = lambda c, s, sus: c in (3, 7)     # acusa a Carnicero o Heredero
_CB[9]  = lambda c, s, sus: c in (2, 5)     # acusa a Aprendiz o Vidente
_CB[10] = lambda c, s, sus: (sus[c]["edad"] == "viejo" and sus[c]["clase"] == "rico")  # viejo y rico
_CB[11] = lambda c, s, sus: (sus[c]["edad"] == "mediana" and sus[c]["clase"] == "pobre")  # mediana y pobre

# ── DEFENSA (12–20) ──────────────────────────────────────────────────────────
_CB[12] = lambda c, s, sus: c != 1                        # el Notario no fue
_CB[13] = lambda c, s, sus: c != 3                        # el Carnicero no fue
_CB[14] = lambda c, s, sus: c != 4                        # el Coronel no fue
_CB[15] = lambda c, s, sus: c != 6                        # el Médico no fue
_CB[16] = lambda c, s, sus: c not in (1, 4)               # ni Notario ni Coronel
_CB[17] = lambda c, s, sus: c not in (2, 5)               # ni Aprendiz ni Vidente
_CB[18] = lambda c, s, sus: c not in (3, 6)               # ni Carnicero ni Médico
_CB[19] = lambda c, s, sus: sus[c]["clase"] != "rico"    # el culpable no es rico
_CB[20] = lambda c, s, sus: sus[c]["edad"] != "mediana"     # el culpable no es mediana

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

def _descripciones_o_dudas_mienten(c, s, sus, asig):
    """Verdad cuando AL MENOS UNA descriptiva o AL MENOS UNA duda presente (excl. declarante)
    es falsa dado el culpable. Falsa solo si todas las descriptivas y todas las dudas
    presentes son verdaderas.
    Refleja: 'Las descripciones que he escuchado son muy vagas y quienes dudan carecen
    de condiciona. Aquí alguien esta mintiendo.'
    - Requiere al menos 1 descriptiva Y al menos 1 duda presentes (excl. declarante);
      si falta alguna de las dos categorías, la afirmación es vacía → falso."""
    descriptivas = [sid for sid, cid in asig.items()
                    if sid != s and CATEGORIAS_CARTAS.get(cid) == "descriptiva"]
    dudas = [sid for sid, cid in asig.items()
             if sid != s and CATEGORIAS_CARTAS.get(cid) == "duda"]
    if not descriptivas or not dudas:
        return False   # falta alguna de las dos categorías → afirmación vacía → falso
    objetivo = descriptivas + dudas
    return any(not evaluar_carta_simple(asig[sid], c, sid, sus) for sid in objetivo)

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

# 26: "Las descripciones que he escuchado son muy vagas y quienes dudan carecen de
# condiciona. Aquí alguien esta mintiendo."
# Verdad cuando al menos una descriptiva o una duda presente (excl. declarante) es falsa.
_CB[26] = _meta(lambda c, s, sus, asig: _descripciones_o_dudas_mienten(c, s, sus, asig))

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
_CB[43] = lambda c, s, sus: sus[c]["clase"] == "pobre" and sus[c]["edad"] != "viejo"  # pobre y no viejo
_CB[44] = lambda c, s, sus: True
_CB[45] = lambda c, s, sus: False
_CB[46] = lambda c, s, sus: sus[c]["clase"] != "media"     # no fue alguien de clase media
_CB[47] = lambda c, s, sus: sus[c]["edad"] != "joven"      # no fue alguien joven
_CB[48] = lambda c, s, sus: sus[c]["clase"] != "pobre"     # no fue alguien pobre
_CB[49] = lambda c, s, sus: sus[c]["clase"] != "pobre" and sus[c]["edad"] != "joven"    # ni pobre ni joven
_CB[50] = lambda c, s, sus: sus[c]["clase"] != "media" and sus[c]["edad"] != "mediana"  # ni clase media ni mediana edad

# ── GRUPAL (51–56) ───────────────────────────────────────────────────────────
_CB[51] = lambda c, s, sus: 4 in sus and 1 in sus and c in (4, 1)    # Coronel y Notario, uno de ellos
_CB[52] = lambda c, s, sus: 2 in sus and 3 in sus and c in (2, 3)    # Aprendiz y Carnicero
_CB[53] = lambda c, s, sus: 5 in sus and 6 in sus and c in (5, 6)    # Vidente y Médico
_CB[54] = _meta(lambda c, s, sus, asig:
    sus[c]["clase"] == "rico" and _alguno_con_atributo_miente(c, s, sus, asig, "clase", "rico")
)
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

# ── CARTA ESPECIAL: OMERTÁ (73) ──────────────────────────────────────────────
# "Aquí dentro nadie habla. Quien me acuse, directa o indirectamente, será
# silenciado." Exclusiva de la ficha-conclusión del Caso, en dificultad
# metrópoli y omertá (nunca en fichas normales ni en urbano).
#
# Efecto: protege a su propio DECLARANTE (no al culpable de la ronda) — si
# otra carta de la mesa lo nombra, o si su perfil real (clase+edad) encaja
# en lo que esa carta exige del culpable, esa carta queda SILENCIADA: no
# cuenta como verdad ni como mentira en el total de la partida. El efecto
# es independiente de quién resulte ser el culpable real.
#
# La propia carta Omertá es verdad si y solo si logró silenciar al menos
# una carta; si nadie la desafiaba, es mentira (la amenaza fue vacía).
ID_CARTA_OMERTA = 73

# Categorías cuya verdad/mentira depende DIRECTAMENTE del atributo (clase o
# edad) del culpable evaluado. Acusación, descriptiva y grupal entran
# siempre; de duda, solo la 43 ("pobre y no viejo").
CATS_SENSIBLES_ATRIBUTO = {"acusación", "descriptiva", "grupal"}
CARTAS_DUDA_SENSIBLES = {43}

# Excepción puntual: la 39 está categorizada como "descriptiva" pero es en
# esencia una defensa por exclusión ("el culpable NO era ni rico ni viejo")
# — niega un atributo en vez de afirmarlo. Es la única negativa del bloque
# 31-40; se excluye a mano en vez de generalizar una regla de "negación".
CARTAS_EXCLUIDAS_OMERTA = {39}

# Indirectas cuyo antecedente A no depende del atributo del culpable, pero
# cuyo consecuente B sí — Omertá las apaga únicamente cuando A se cumple.
# Decisión explícita: SOLO estas tres entran al criterio condicional, no se
# generaliza a 67/68/70/72 aunque tengan estructura similar.
INDIRECTAS_CONDICIONADAS_A_PREMISA = {66, 69, 71}


def _omerta_valor_carta(cid_otra, c, sid_otra, sus, asignacion):
    """Evalúa cid_otra(c, sid_otra, sus) inyectando ASIGNACION_EVAL primero,
    para que funcione tanto con cartas simples (CARTAS_BASE) como con
    cartas envueltas en _meta (que leen el global ASIGNACION_EVAL en vez
    de recibir asig como argumento explícito).

    Protección anti-ciclo: usa el MISMO mecanismo de _VISITADOS_EVAL que
    evaluar_carta_simple (agregar la clave antes de evaluar, descartarla al
    salir) en vez de limpiar/restaurar el set completo — necesario porque
    Omertá puede depender de una indirecta (66/69/71) cuya premisa A a su
    vez evalúa la propia carta Omertá para otro declarante.

    CRÍTICO: `asignacion` puede ser el MISMO objeto que ASIGNACION_EVAL
    (cuando se llega aquí desde una carta _meta). Se copia a una variable
    local ANTES de tocar ASIGNACION_EVAL para no vaciarla por aliasing."""
    key = (cid_otra, c, sid_otra)
    if key in _VISITADOS_EVAL:
        return True   # ciclo detectado: cortar con True (conservador)

    asignacion_a_inyectar = dict(asignacion)
    asignacion_previa = dict(ASIGNACION_EVAL)
    ASIGNACION_EVAL.clear()
    ASIGNACION_EVAL.update(asignacion_a_inyectar)
    _VISITADOS_EVAL.add(key)
    try:
        fn = CARTAS.get(cid_otra)
        if fn is None:
            return True
        return fn(c, sid_otra, sus)
    except Exception:
        return True
    finally:
        _VISITADOS_EVAL.discard(key)
        ASIGNACION_EVAL.clear()
        ASIGNACION_EVAL.update(asignacion_previa)


def _antecedente_A_indirecta_omerta(cid_otra, c, sus, asignacion):
    """Replica el antecedente A de las indirectas 66/69/71, en sus propios
    términos (sin tocar B), para decidir si Omertá debe considerarlas. A se
    evalúa contra el culpable REAL de la ronda (c), no contra el declarante
    de Omertá — A no depende de "quién protege Omertá"."""
    asignacion_a_inyectar = dict(asignacion)
    asignacion_previa = dict(ASIGNACION_EVAL)
    ASIGNACION_EVAL.clear()
    ASIGNACION_EVAL.update(asignacion_a_inyectar)
    try:
        if cid_otra == 66:
            if 9 not in asignacion:
                return False
            return not _omerta_valor_carta(asignacion[9], c, 9, sus, asignacion)
        if cid_otra == 69:
            return _hay_media_mintiendo(c, None, sus, asignacion)
        if cid_otra == 71:
            return _mayoria_miente_simple(c, None, sus, asignacion)
        return False
    finally:
        ASIGNACION_EVAL.clear()
        ASIGNACION_EVAL.update(asignacion_previa)


def _omerta_carta_apunta_a(cid_otra, sid_otra, c, sus, asig, declarante_omerta):
    """¿La carta cid_otra (de sid_otra) 'apunta' al declarante de Omertá?
    Funciona independientemente de si declarante_omerta es o no el culpable
    real evaluado (c) — Omertá protege a su propio declarante, no al
    culpable de la ronda.

    Alcance:
      1) Identidad explícita: la carta nombra al declarante_omerta por id
         (acusación/defensa directa, descriptiva 37-38, grupales 51-53).
         NO incluye 66/67/68: esos mencionan un sospechoso fijo como sujeto
         de una premisa condicional, no como acusación/defensa directa.
      2) Atributo directo: acusación/descriptiva/grupal siempre; duda solo
         la 43. Se evalúa la lambda original de la carta poniendo a
         declarante_omerta en el rol de "culpable", con sus atributos
         reales — si da True, su perfil encaja en lo que la carta exige.
      3) Indirectas 66/69/71 (únicas): solo si su antecedente A es verdadero.

    Las demás cartas (incluida la 39, excluida a mano) nunca entran.
    """
    NOMBRA_ID = {
        1: (3,), 2: (1,), 3: (6,), 4: (5,), 5: (2,), 6: (4,),
        7: (8, 9), 8: (3, 7), 9: (2, 5),
        12: (1,), 13: (3,), 14: (4,), 15: (6,),
        16: (1, 4), 17: (2, 5), 18: (3, 6),
        37: (4,), 38: (2,),
        51: (1, 4), 52: (2, 3), 53: (5, 6),
    }
    if cid_otra in NOMBRA_ID and declarante_omerta in NOMBRA_ID[cid_otra]:
        return True

    if cid_otra in CARTAS_EXCLUIDAS_OMERTA:
        return False

    cat = CATEGORIAS_CARTAS.get(cid_otra)

    if cid_otra in INDIRECTAS_CONDICIONADAS_A_PREMISA:
        if not _antecedente_A_indirecta_omerta(cid_otra, c, sus, asig):
            return False
    elif cat == "duda":
        if cid_otra not in CARTAS_DUDA_SENSIBLES:
            return False
    elif cat not in CATS_SENSIBLES_ATRIBUTO:
        return False

    if cid_otra in NOMBRA_ID:
        return False

    return _omerta_valor_carta(cid_otra, declarante_omerta, sid_otra, sus, asig)


def calcular_cartas_silenciadas(asignacion: dict, candidato: int, sus: dict) -> set:
    """Devuelve el set de sospechoso_ids cuya carta queda silenciada por
    Omertá. Vacío si no hay carta Omertá en la mesa. No depende de que
    `candidato` sea el declarante de Omertá — Omertá protege a su propio
    declarante sea quien sea el culpable evaluado; `candidato` solo se usa
    para la premisa A de 66/69/71.

    Punto de entrada robusto: sincroniza ASIGNACION_EVAL con `asignacion`
    antes de evaluar nada (puede llamarse desde fuera de cualquier
    evaluación en curso). `asignacion` puede ser el MISMO objeto que
    ASIGNACION_EVAL (si se llega aquí desde _omerta_es_verdad) — por eso se
    congela `asignacion_a_usar = dict(asignacion)` ANTES de tocar el global."""
    asignacion_a_usar = dict(asignacion)
    asignacion_previa = dict(ASIGNACION_EVAL)
    ASIGNACION_EVAL.clear()
    ASIGNACION_EVAL.update(asignacion_a_usar)
    try:
        declarante_omerta = next((sid for sid, cid in asignacion_a_usar.items() if cid == ID_CARTA_OMERTA), None)
        if declarante_omerta is None:
            return set()
        items_fijos = list(asignacion_a_usar.items())
        silenciadas = set()
        for sid_otra, cid_otra in items_fijos:
            if sid_otra == declarante_omerta:
                continue
            if _omerta_carta_apunta_a(cid_otra, sid_otra, candidato, sus, asignacion_a_usar, declarante_omerta):
                silenciadas.add(sid_otra)
        return silenciadas
    finally:
        ASIGNACION_EVAL.clear()
        ASIGNACION_EVAL.update(asignacion_previa)


def _omerta_es_verdad(c, s, sus, asig):
    """Omertá es verdad si y solo si efectivamente logró silenciar al menos
    una carta de la mesa. Si nadie la desafiaba, es mentira."""
    silenciadas = calcular_cartas_silenciadas(asig, c, sus)
    return len(silenciadas) > 0


CARTAS_OMERTA = {
    ID_CARTA_OMERTA: _meta(_omerta_es_verdad),
}

# ── INDIRECTAS (65–72) — confesión condicional indirecta ─────────────────────
# Usan evaluar_carta_simple para no recursar.
# Las cartas que referencian al Crupier (8), Vagabundo (9) o Heredero (7)
# solo se pueden asignar si ese sospechoso está presente en la partida.

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
    """¿Más de la mitad de los DEMÁS sospechosos (sin contar al propio declarante)
    miente? (versión simple, sin recursión en meta). El declarante queda fuera
    del conteo para evitar que la carta se evalúe a sí misma (auto-referencia)."""
    otros = [(sid, cid) for sid, cid in asig.items() if sid != s]
    if not otros:
        return False  # sin nadie más a quien contar, la afirmación es vacía
    mentiras = sum(1 for sid, cid in otros if not evaluar_carta_simple(cid, c, sid, sus))
    return mentiras > len(otros) / 2

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
    # 65: "Escucho a quienes se defienden y quienes describen al culpable, pero si unos dicen la verdad, todos los otros mienten por miedo o por vergüenza"
    # A = hay al menos una carta de defensa Y al menos una carta descriptiva en la ficha
    # B = todas las defensas son verdad Y todas las descriptivas son mentira, o viceversa
    #     (viceversa: todas las defensas son mentira Y todas las descriptivas son verdad)
    # Verdad jugable: A AND B
    # A falsa → carta falsa, B indeterminada
    65: _meta(lambda c, s, sus, asig:
        (lambda defensas, descriptivas:
            None if not defensas or not descriptivas else (
                (lambda n_def_v, n_desc_v:
                    (n_def_v == len(defensas) and n_desc_v == 0) or
                    (n_def_v == 0 and n_desc_v == len(descriptivas))
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
    # 67: "Si el Heredero dice verdad, el culpable no es media"
    # A = eval(heredero)   B = sus[c]["clase"]!="media"
    # Verdad jugable: A AND B  → el Heredero dice verdad Y el culpable no es media
    # A falsa (Heredero miente) → carta falsa, B indeterminada
    # Heredero ausente → None (ficha inválida)
    67: _meta(lambda c, s, sus, asig:
        (None if 7 not in asig else
         (evaluar_carta_simple(asig[7], c, 7, sus)
          and sus[c]["clase"] != "media"))
    ),
    # 68: "Si el Crupier miente, quien lo hizo no era viejo"
    # A = NOT eval(Crupier)   B = sus[c]["edad"]!="viejo"
    # Verdad jugable: A AND B  → el Crupier miente Y el culpable no es viejo
    # A falsa (Crupier dice verdad) → carta falsa, B indeterminada
    # Crupier ausente → None (ficha inválida)
    68: _meta(lambda c, s, sus, asig:
        (None if 8 not in asig else
         (not evaluar_carta_simple(asig[8], c, 8, sus)
          and sus[c]["edad"] != "viejo"))
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
    # 71: "Si la mayoría de los demás sospechosos miente, el culpable tiene años encima"
    # A = mayoria_miente_simple (excl. declarante)   B = sus[c]["edad"]=="viejo"
    # Verdad jugable: A AND B  → hay mayoría de mentiras entre los demás Y el culpable es viejo
    # A falsa (no hay mayoría de mentiras entre los demás) → carta falsa (False), B indeterminada
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

CARTAS = {**CARTAS_BASE, **CARTAS_META, **CARTAS_INDIRECTAS, **CARTAS_OMERTA}

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
    if carta_id == 71:   # A = mayoría de los demás miente (excl. declarante)
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
CARTAS_SIEMPRE_VERDAD = {41, 42, 43, 44, 45, 62}

TEXTOS_CARTAS = {
    # ACUSACIÓN
    1:  "El Carnicero lo hizo. Lo vi salir con las manos limpias y los ojos sucios.",
    2:  "El Notario. Nadie más conocía la hora exacta. Nadie más tenía motivo.",
    3:  "Solo el Médico sabe cómo borrar lo que no quiere que se encuentre.",
    4:  "La Vidente sabía lo que iba a pasar. Pero no creo en sus visiones, creo que lo planificó.",
    5:  "La Aprendiz aprendió demasiado rápido. Y alguien pagó el precio.",
    6:  "El Coronel fue. Lo delataron sus hábitos, no sus palabras.",
    7:  "Solo el El Vagabundo o el Crupier estaban en la escena del crimen. Uno de ellos lo hizo.",
    8:  "El Carnicero o el Heredero. Cualquiera de los dos tiene las manos entrenadas para esto.",
    9:  "Fue la Aprendiz o la Vidente. El instinto lo dice. Las pruebas, también.",
    10: "El asesino ya tenía la edad de quien no teme nada y el dinero de quien nunca tuvo que temerlo.",
    11: "El asesino tenía los bolsillos vacíos y sintiendo el peso de los años se negó a llegar a viejo en la miseria. No lo culpo",
    # DEFENSA
    12: "El Notario no tiene el temple. Conozco a los que pueden hacer algo así. Él no.",
    13: "El Carnicero es muchas cosas. Un asesino no es una de ellas. Que quede claro.",
    14: "El Coronel lleva años protegiéndonos. Acusarlo es insultarnos a todos.",
    15: "El Médico juró no hacer daño. Y lo cumple. Eso no se finge.",
    16: "Ni el Notario ni el Coronel. Ambos estaban conmigo cuando ocurrió.",
    17: "Ni la Aprendiz ni la Vidente. Las dos tienen coartada. Yo mismo la verifiqué.",
    18: "Ni el Carnicero ni el Médico. Sus herramientas no cuadran con lo que vi.",
    19: "El culpable no era rico. Vi sus ropas. Menuda falta de gusto.",
    20: "Quien lo hizo no era de mediana edad. Esta claro pues no tuvo la fuerza para mover el cuerpo.",
    # VERACIDAD
    21: "Todos esos viejos en la sala saben más de lo que dicen. Eligieron con cuidado que contar y sobre todo que ocultar.",
    22: "Desconfíen de todos los demas ricos. El porte da una confianza que cuesta distinguir de la inocencia.",
    23: "A su edad los viejos ya no se gastan en mentir. No temen a la verdad.",
    24: "Los pobres no mienten pues hoy han comido bien. Yo les creo.",
    25: "La experiencia no se oculta. Quien tiene mediana edad ya ha aprendido a mentir y lo hará almenos uan vez.",
    26: "Las descripciones que he escuchado esconden algo y quienes han dudado al hablar lo confirman. Aquí alguien está mintiendo.",
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
    38: "Quien buscas tenía la misma edad que la Aprendiz. Eso y su misma frialdad.",
    39: "El culpable no era ni rico ni viejo. Lo que vi fue a alguien que podría confundirse con cualquiera.",
    40: "Era rico y de mediana edad. Esa combinación no abunda en esta sala.",
    # DUDA
    41: "Yo no he sido ni sé quién pudo hacerlo. Pero sé que lo volverá a hacer si no lo encontramos.",
    42: "Podría haber sido cualquiera. Cualquiera con suficiente razón para odiar.",
    43: "No estoy seguro, era pobre, y quizás joven o de mediana edad pero no viejo",
    44: "Es inutil mentir, al final usted descubre la verdad.",
    45: "Me temo que no podrá resolver este caso Detective, el tiempo juega en su contra.",
    46: "Estoy seguro que alguien de clase media tendría mejores cosas que hacer. El resto quizás no.",
    47: "No fue alguien joven. La frialdad de esto requiere años que aún no se tienen.",
    48: "No fue alguien pobre. El reloj que tenía la victima era costoso y allí quedó",
    49: "No estoy muy seguro; no era joven ni tampoco parecía pobre. Siento no poder aportar más.",
    50: "Vestía de forma extravagante; yo diría que no era de clase media y era alguien joven o quizás viejo.",
    # GRUPAL
    51: "El Coronel y el Notario llegaron juntos esa noche. Solo uno de ellos sabe por qué.",
    52: "La Aprendiz y el Carnicero se conocen de antes. Eso no es casualidad.",
    53: "La Vidente y el Médico compartían secretos. Alguno de esos secretos mató.",
    54: "Los ricos en esta sala se cubren entre sí. Uno de ellos miente, uno de ellos lo hizo y no podra esconderlo.",
    55: "Los viejos se protegen. Es lo único que les queda. Uno de ellos debe ser el asesino.",
    56: "Somos un grupo grande, algunos demasiado jóvenes otros demasiado viejos, y luego está el asesino.",
    # META
    57: "Quien se defiende en esta sala está mintiendo. La inocencia no necesita tanto ruido.",
    58: "Cada acusación que escuché esta noche sonó a verdad. Eso debería asustarnos.",
    59: "El culpable no se está defendiendo. Eso es incluso más peligroso. Ande con cuidado.",
    60: "La mayoría de las declaraciones que escuché ahí hoy son puras mentiras. Calcule a quién conviene mentir.",
    61: "Al menos una descripción dicha en esta sala suena convincente. Aférrese a esa y le llevará al culpable.",
    62: "Hay uno solo que miente en esta sala. Solo uno. Y ese uno soy yo.",
    63: "Alguien acusa y alguien defiende, y ambos dicen la verdad. Eso es una contradicción. O es una trampa.",
    64: "No he escuchado una sola duda en esta sala, es como si los más reflexivos callaran, señal de que todos ellos mienten.",
    # INDIRECTAS
    65: "Escucho a quienes defienden y quienes describen al culpable, pero si los unos dicen la verdad, los otros mienten.",
    66: "Si el Vagabundo miente, entonces el asesino vino de abajo. La pobreza no es excusa, pero sí es pista.",
    67: "Si el Heredero no miente, podemos descartar a los de clase media. Está claro  que obraron de buena fe.",
    68: "Si el Crupier miente, quien lo hizo no era viejo. Son los únicos a los que él nunca defendería.",
    69: "Cuando alguien de la clase media miente, suele ser por sentimentalismo. Ese viejo impulso de proteger a los más jóvenes.",
    70: "Si el culpable esgrime una defensa esta noche, algún inocente también miente para cubrirlo. La complicidad tiene sus reglas.",
    71: "Si la mayoria de los demás sospechosos miente, el culpable tiene años encima. La vejez enseña a esconderse.",
    72: "Si nadie acusa directamente al culpable, es porque este los está presionando. Pero los pobres no tienen nada que perder y dirán la verdad.",
    # OMERTA
    73: "Solo tengo una palabra para usted, detective: Omertá. Quien me acuse, directa o indirectamente, será silenciado.",
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
    73: "omerta",
}
