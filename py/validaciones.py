"""
Validaciones de fichas: resolución de solución única, restricciones de
dificultad, detección de solapamiento lógico entre cartas, requisitos de
categoría de apoyo, y tope de cartas silenciadas por Omertá.
"""

from typing import Optional

import cartas
from cartas import (
    CARTAS, CATEGORIAS_CARTAS,
    ID_CARTA_OMERTA, calcular_cartas_silenciadas, evaluar_carta_simple,
)
from datos import TOPE_CARTAS_APAGADAS_OMERTA, MINIMO_CARTAS_VIVAS_TRAS_OMERTA

def evaluar_carta(carta_id: int, culpable_id: int, declarante_id: int, sus: dict,
                  asignacion: dict = None) -> bool:
    """Evaluación top-level: inyecta estado global y limpia visitados. Usar solo
    cuando se evalúa una carta aislada (exportación, debug). Para validación en
    bulk usar tiene_solucion_unica que hace el setup una sola vez por candidato."""
    if asignacion is not None:
        cartas.ASIGNACION_EVAL.clear()
        cartas.ASIGNACION_EVAL.update(asignacion)
    cartas._VISITADOS_EVAL.clear()
    cartas._MAYORIA_CACHE.clear()
    # Recalcular silenciadas para esta evaluación aislada y dejarlas disponibles
    # en _SILENCIADAS_EVAL, de forma que las cartas meta/indirecta no las vean.
    if asignacion is not None:
        silenciadas = calcular_cartas_silenciadas(asignacion, culpable_id, sus)
        cartas._SILENCIADAS_EVAL.clear()
        cartas._SILENCIADAS_EVAL.update(silenciadas)
    else:
        cartas._SILENCIADAS_EVAL.clear()
    fn = CARTAS[carta_id]
    return fn(culpable_id, declarante_id, sus)

def _evaluar_sin_setup(carta_id: int, culpable_id: int, declarante_id: int, sus: dict) -> bool:
    """Evaluación sin setup — asume que ASIGNACION_EVAL y _VISITADOS_EVAL ya están listos.
    Usar solo dentro de tiene_solucion_unica donde el setup se hace una vez por candidato."""
    fn = CARTAS[carta_id]
    return fn(culpable_id, declarante_id, sus)

def tiene_solucion_unica(asignacion: dict, sus: dict, modo: str, cantidad: int) -> Optional[int]:
    """Busca un único culpable que satisfaga el conteo de verdades/mentiras.
    Optimización: inyecta ASIGNACION_EVAL una sola vez por candidato (no por carta)
    y usa _evaluar_sin_setup para evitar el overhead de clear+update en cada carta.

    Cartas silenciadas por Omertá quedan EXCLUIDAS del conteo de verdades y
    del de mentiras — el universo evaluable para ese candidato se reduce,
    en vez de que la carta silenciada "cuente" hacia cualquiera de los dos
    lados con su valor lógico de fondo."""
    n = len(sus)
    soluciones = []
    items = list(asignacion.items())   # materializar para no re-iterar el dict
    for candidato in sus:
        # Setup global una sola vez para este candidato
        cartas.ASIGNACION_EVAL.clear()
        cartas.ASIGNACION_EVAL.update(asignacion)
        cartas._VISITADOS_EVAL.clear()
        cartas._MAYORIA_CACHE.clear()
        silenciadas = calcular_cartas_silenciadas(asignacion, candidato, sus)
        cartas._SILENCIADAS_EVAL.clear()
        cartas._SILENCIADAS_EVAL.update(silenciadas)
        n_evaluable = n - len(silenciadas)
        verdades = sum(
            1 for sosp_id, carta_id in items
            if sosp_id not in silenciadas and _evaluar_sin_setup(carta_id, candidato, sosp_id, sus)
        )
        mentiras = n_evaluable - verdades
        if modo == "verdades" and verdades == cantidad:
            soluciones.append(candidato)
            if len(soluciones) > 1:
                return None   # ya hay más de uno: no es única, salir temprano
        elif modo == "mentiras" and mentiras == cantidad:
            soluciones.append(candidato)
            if len(soluciones) > 1:
                return None
    return soluciones[0] if len(soluciones) == 1 else None


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


# Requisitos de categoría por carta: {carta_id: [categoría1, categoría2, ...]}
# Cada categoría listada debe estar presente en la ASIGNACIÓN FINAL de la ficha
# (en algún OTRO sospechoso, no en el propio declarante de la carta) para que
# la carta tenga sentido narrativo/lógico. El chequeo de _armar_asignacion_cartas
# (líneas ~906-933) solo mira el pool de cartas aún no usadas en el momento del
# reparto — no garantiza que esas categorías terminen siendo repartidas. Esta
# función valida sobre el resultado final, una vez completada toda la asignación.
REQUISITOS_CATEGORIA_CARTA = {
    26: ["descriptiva", "duda"],
    57: ["defensa"],
    58: ["acusación"],
    59: ["defensa"],
    61: ["descriptiva"],
    63: ["acusación", "defensa"],
    65: ["defensa", "descriptiva"],
    72: ["acusación"],
}

def validar_requisitos_categoria(asignacion: dict) -> bool:
    """
    Devuelve True si, para cada carta de la ficha que requiere categorías
    de apoyo (ver REQUISITOS_CATEGORIA_CARTA), esas categorías están
    efectivamente presentes en la asignación final, en algún sospechoso
    distinto del declarante de esa carta.

    Esto reemplaza la garantía incompleta de _armar_asignacion_cartas, que
    solo chequeaba disponibilidad en el pool al momento de repartir la carta,
    no presencia real en el resultado final.
    """
    for declarante_id, carta_id in asignacion.items():
        requeridas = REQUISITOS_CATEGORIA_CARTA.get(carta_id)
        if not requeridas:
            continue
        categorias_presentes = {
            CATEGORIAS_CARTAS.get(cid)
            for sid, cid in asignacion.items()
            if sid != declarante_id
        }
        if not all(cat in categorias_presentes for cat in requeridas):
            return False
    return True


def validar_tope_omerta(asignacion: dict, sus: dict) -> bool:
    """
    Si la ficha tiene carta Omertá, calcula cuántas cartas quedarían
    silenciadas y descarta la ficha si:
      (a) el apagón supera TOPE_CARTAS_APAGADAS_OMERTA, o
      (b) las cartas que quedan vivas son menos que MINIMO_CARTAS_VIVAS_TRAS_OMERTA.
    Si no hay carta Omertá, no filtra nada (True directo).
    """
    declarante_omerta = next((sid for sid, cid in asignacion.items() if cid == ID_CARTA_OMERTA), None)
    if declarante_omerta is None:
        return True
    silenciadas = calcular_cartas_silenciadas(asignacion, declarante_omerta, sus)
    n_vivas = len(asignacion) - 1 - len(silenciadas)  # -1: la propia carta Omertá no se autoevalúa
    if len(silenciadas) > TOPE_CARTAS_APAGADAS_OMERTA:
        return False
    if n_vivas < MINIMO_CARTAS_VIVAS_TRAS_OMERTA:
        return False
    return True


def validar_omerta_activable(asignacion: dict, sus: dict) -> bool:
    """
    Garantiza que la amenaza de Omertá sea real: debe existir al menos una
    carta en la ficha que la activaría (es decir, que apunta al declarante
    de Omertá) para AL MENOS UN candidato posible.

    El chequeo evalúa calcular_cartas_silenciadas para cada sospechoso como
    candidato culpable; si en alguno el set de silenciadas no está vacío,
    la validación pasa. Si para todos los candidatos el apagón sería cero
    (nadie desafía a Omertá bajo ningún culpable posible), la ficha se
    descarta — la amenaza sería narrativamente hueca y Omertá quedaría
    siempre como mentira, sin aportar tensión deductiva.

    Si no hay carta Omertá en la ficha, devuelve True directamente.
    """
    declarante_omerta = next(
        (sid for sid, cid in asignacion.items() if cid == ID_CARTA_OMERTA), None
    )
    if declarante_omerta is None:
        return True  # sin Omertá en la ficha, la regla no aplica

    for candidato in sus:
        silenciadas = calcular_cartas_silenciadas(asignacion, candidato, sus)
        if silenciadas:
            return True  # al menos un candidato activaría Omertá

    return False  # ningún candidato activa Omertá: amenaza hueca, descartar
