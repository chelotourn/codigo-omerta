"""
Flujo del Caso completo y la ficha-conclusión sobre el Distrito 3 dinámico
(ver documento de diseño Codigo_Omerta_Concepto_Caso): agrupa los culpables
de N fichas, resuelve el distrito de cada nombre, valida las reglas de
descarte y construye la ficha-conclusión final reusando el motor de reparto
de cartas normal.
"""

import random
from typing import Optional

import datos
from datos import DISTRITOS, SOSPECHOSOS_1, sospechosos_del_distrito
from cartas import (
    CARTAS, ID_CARTA_OMERTA, ID_CARTA_OMERTA_DEFENSA, CARTAS_TRIVIALES,
    validar_indirectas_en_ficha,
)
from validaciones import (
    tiene_solucion_unica, validar_dificultad, validar_sin_solapamiento,
    validar_requisitos_categoria, validar_tope_omerta, validar_omerta_activable,
)
from generacion import Ficha, generar_fichas, _armar_asignacion_cartas

# ─────────────────────────────────────────────
#  CASO Y FICHA-CONCLUSIÓN (Distrito 3 dinámico)
# ─────────────────────────────────────────────
# Implementa el flujo descripto en Codigo_Omerta_Concepto_Caso.docx:
#   Paso A — Recolección de culpables de las N fichas del Caso.
#   Paso B — Agrupación por nombre_id + resolución de distrito (desempate).
#            El resultado se materializa como un distrito más en DISTRITOS
#            (id=3, "Codigo Omertá"), construido dinámicamente. A partir
#            de ahí se lo trata exactamente igual que el Distrito 1 o 2: todo
#            el código existente (sospechosos_del_distrito, evaluar_carta,
#            ficha_a_dict, etc.) sigue funcionando sin tocarlo.
#   Paso C — Validaciones de descarte (Regla 1: rango por dificultad;
#            Regla 2: tope de repetición de atributo, máx. 4).
#   Paso D — Construcción de la ficha-conclusión reusando el reparto de
#            cartas normal (_armar_asignacion_cartas) sobre el Distrito 3.
#
# Si el Caso se descarta en cualquier paso (empate, Regla 1 o Regla 2), no se
# "recorta" nada: se descarta el Caso completo y se reintenta desde cero
# (Paso A) hasta encontrar uno que cierre, tal como especifica el documento
# ("todo o nada").

ID_DISTRITO_SINTESIS = 3

RANGO_SOSPECHOSOS_POR_DIFICULTAD = {"urbano": (3, 5), "metropoli": (4, 6), "omerta": (6, 8)}
TOPE_REPETICION_ATRIBUTO = 4   # Regla 2: ningún valor de clase/edad puede aparecer más de 4 veces


def _paso_b_agrupar_y_resolver_distrito(culpables_por_ficha: list):
    """
    Paso B del documento de diseño.

    culpables_por_ficha: lista de tuplas (nombre_id, distrito_id, ficha_id),
    una por cada una de las N fichas del Caso (Paso A ya resuelto).

    Devuelve (distrito_3_sospechosos, hubo_empate):
      - Si hubo_empate es True, distrito_3_sospechosos es None (conflicto
        irresoluble — el Caso se descarta de inmediato, sin evaluar el resto).
      - Si hubo_empate es False, distrito_3_sospechosos es un dict
        {nombre_id: {"nombre":, "clase":, "edad":}} con cada nombre único
        que apareció como culpable, ya con sus atributos resueltos (los del
        distrito que tuvo más apariciones para ese nombre).
    """
    cuentas = {}  # nombre_id -> {1: cuenta_d1, 2: cuenta_d2}
    for nombre_id, distrito_id, _ficha_id in culpables_por_ficha:
        cuentas.setdefault(nombre_id, {1: 0, 2: 0})
        cuentas[nombre_id][distrito_id] += 1

    distrito_3 = {}
    for nombre_id, c in cuentas.items():
        d1, d2 = c[1], c[2]
        if d1 == d2:
            return None, True   # empate → conflicto irresoluble, descarte inmediato
        distrito_ganador = 1 if d1 > d2 else 2
        atributos = sospechosos_del_distrito(distrito_ganador)[nombre_id]
        distrito_3[nombre_id] = {
            "nombre": atributos["nombre"],
            "clase":  atributos["clase"],
            "edad":   atributos["edad"],
            "_distrito_origen": distrito_ganador,  # uso interno, se separa luego
        }
    return distrito_3, False


def _paso_c_validar_caso(distrito_3: dict, dificultad: str) -> bool:
    """
    Paso C del documento de diseño — Reglas 1 y 2 de la §5.

    Regla 1: la cantidad de nombres únicos sobrevivientes debe caer dentro
             del rango de sospechosos propio de la dificultad del Caso.
    Regla 2: ningún valor de atributo (de los 6 posibles: rico/media/pobre/
             joven/mediana/viejo) puede aparecer más de TOPE_REPETICION_ATRIBUTO
             veces entre los únicos sobrevivientes.

    Devuelve True si el Caso pasa ambas reglas, False si debe descartarse.
    """
    minimo, maximo = RANGO_SOSPECHOSOS_POR_DIFICULTAD[dificultad]
    n_unicos = len(distrito_3)
    if n_unicos < minimo or n_unicos > maximo:
        return False   # Regla 1

    conteo_attr = {}
    for datos in distrito_3.values():
        for attr in ("clase", "edad"):
            valor = datos[attr]
            conteo_attr[valor] = conteo_attr.get(valor, 0) + 1
    if any(cnt > TOPE_REPETICION_ATRIBUTO for cnt in conteo_attr.values()):
        return False   # Regla 2

    return True


def generar_caso(n_fichas: int, cantidad_fija: Optional[int],
                  dificultad: str, n_sosp_fijo: int = 0,
                  max_intentos_ficha: int = 200_000,
                  max_reintentos_caso: int = 500, seed: Optional[int] = None) -> dict:
    """
    Genera un Caso completo: N fichas normales (distrito_modo=0, cíclico
    Industrial/Comercial) + intenta cerrar con una ficha-conclusión sobre el
    Distrito 3 dinámico.

    Si el cierre se descarta (empate, Regla 1 o Regla 2), las N fichas
    completas se tiran y se reintenta desde cero — hasta max_reintentos_caso
    veces — porque el documento especifica "todo o nada": no hay forma de
    reparar un Caso descartado, solo de generar otro.

    Devuelve un dict:
      {
        "fichas": [...N fichas del Caso...],
        "ficha_conclusion": Ficha | None,
        "descartado": bool,          # True si se agotaron los reintentos sin cerrar
        "reintentos_caso": int,      # cuántas corridas de N fichas se probaron
      }
    Si "ficha_conclusion" es None y "descartado" es False, significa que las
    N fichas son válidas pero el último intento de cierre no convergió dentro
    de max_reintentos_caso — se entregan igual las N fichas (nunca se pierden).

    Condición de elegibilidad para intentar el cierre: n_fichas debe ser
    mayor o igual al mínimo de sospechosos de la dificultad del Caso
    (3 urbano / 4 metrópoli / 5 omertà). Por debajo de ese mínimo no hay
    margen matemático para que sobrevivan suficientes nombres únicos y
    pasar la Regla 1 — así que ni se intenta: se generan las N fichas una
    sola vez, sin pasar por Pasos B/C/D, y se devuelven sin ficha-conclusión.
    """
    minimo_dificultad, _maximo = RANGO_SOSPECHOSOS_POR_DIFICULTAD[dificultad]
    if n_fichas < minimo_dificultad:
        if seed is not None:
            random.seed(seed)
        fichas = generar_fichas(
            n_fichas=n_fichas,
            cantidad_fija=cantidad_fija,
            max_intentos=max_intentos_ficha,
            seed=None,
            n_sosp_fijo=n_sosp_fijo,
            dificultad=dificultad,
            distrito_modo=0,
        )
        return {
            "fichas": fichas,
            "ficha_conclusion": None,
            "descartado": False,
            "reintentos_caso": 0,
            "motivo": f"n_fichas ({n_fichas}) < mínimo de sospechosos para {dificultad} "
                      f"({minimo_dificultad}) — no se intentó el cierre del Caso.",
        }

    if seed is not None:
        random.seed(seed)

    intentos_caso = 0
    while intentos_caso < max_reintentos_caso:
        intentos_caso += 1

        fichas = generar_fichas(
            n_fichas=n_fichas,
            cantidad_fija=cantidad_fija,
            max_intentos=max_intentos_ficha,
            seed=None,              # no resemillar: ya seedeamos una vez arriba
            n_sosp_fijo=n_sosp_fijo,
            dificultad=dificultad,
            distrito_modo=0,        # alternado: el Paso B necesita ambos distritos representados
        )
        if not fichas or len(fichas) < n_fichas:
            continue   # no se pudieron generar las N fichas; reintentar Caso completo

        # ── Paso A: recolección de culpables, en orden de id de ficha ──
        culpables_por_ficha = [
            (f.culpable, f.distrito, f.id)
            for f in sorted(fichas, key=lambda f: f.id)
        ]

        # ── Paso B: agrupación + resolución de distrito ──
        distrito_3, hubo_empate = _paso_b_agrupar_y_resolver_distrito(culpables_por_ficha)
        if hubo_empate:
            continue   # conflicto irresoluble: descartar Caso completo, reintentar

        # ── Paso C: validaciones de descarte ──
        if not _paso_c_validar_caso(distrito_3, dificultad):
            continue   # Regla 1 o Regla 2 incumplida: descartar Caso completo, reintentar

        # ── Registrar el Distrito 3 dinámicamente (como un distrito más) ──
        distrito_origen_por_sospechoso = {
            nombre_id: datos.pop("_distrito_origen")
            for nombre_id, datos in distrito_3.items()
        }
        DISTRITOS[ID_DISTRITO_SINTESIS] = {
            "nombre": "Caso final — Romper Omertá",
            "sospechosos": distrito_3,
        }

        # ── Paso D: construcción de la ficha-conclusión ──
        ficha_conclusion = _generar_ficha_conclusion(
            distrito_3=distrito_3,
            distrito_origen_por_sospechoso=distrito_origen_por_sospechoso,
            cantidad_fija=cantidad_fija,
            dificultad=dificultad,
            max_intentos=max_intentos_ficha,
        )
        if ficha_conclusion is None:
            continue   # no se pudo repartir cartas válidas para el Distrito 3: reintentar Caso completo

        return {
            "fichas": fichas,
            "ficha_conclusion": ficha_conclusion,
            "descartado": False,
            "reintentos_caso": intentos_caso,
            "motivo": "Caso cerrado con ficha-conclusión.",
        }

    # Se agotaron los reintentos sin lograr cerrar un Caso
    return {
        "fichas": [],
        "ficha_conclusion": None,
        "descartado": True,
        "reintentos_caso": intentos_caso,
        "motivo": f"Se agotaron los {max_reintentos_caso} reintentos de Caso sin cerrar "
                  f"(empates / Regla 1 / Regla 2 persistentes).",
    }


def _generar_ficha_conclusion(distrito_3: dict, distrito_origen_por_sospechoso: dict,
                               cantidad_fija: Optional[int], dificultad: str,
                               max_intentos: int = 200_000) -> Optional[Ficha]:
    """
    Paso D del documento de diseño: reparte cartas sobre el Distrito 3 ya
    construido y validado, reusando exactamente el mismo motor de reglas
    (_armar_asignacion_cartas, tiene_solucion_unica, validar_dificultad,
    validar_sin_solapamiento, validar_requisitos_categoria,
    validar_indirectas_en_ficha) que cualquier
    ficha normal — la diferencia es que sosp_ids es FIJO (los nombres únicos
    sobrevivientes del Paso B) en vez de muestreado al azar.

    La carta Omertá es exclusiva de esta ficha (la conclusión del Caso) y
    solo en dificultad metrópoli y omertá — en urbano queda vetada, igual
    que en cualquier ficha normal. Existen dos variantes mutuamente
    excluyentes, 73 (silencia acusaciones) y 74 (silencia defensas): nunca
    conviven en la misma ficha. Cuando la dificultad lo permite, se elige
    una de las dos al azar para esta ficha-conclusión y la otra queda
    excluida del reparto; la presencia de la elegida está GARANTIZADA: se
    reintenta hasta que el reparto la incluya, no se inserta a mano sobre
    una asignación ya armada.
    """
    sosp_ids = sorted(distrito_3.keys())
    n_sosp = len(sosp_ids)
    min_requerido = {"urbano": 1, "metropoli": 2, "omerta": 3}[dificultad]
    permitir_omerta = dificultad in ("metropoli", "omerta")

    # Sin límite de diversidad entre cartas para la ficha-conclusión: es una
    # sola ficha, no una corrida — fichas_por_carta queda en cero siempre,
    # así que el filtro de diversidad de _armar_asignacion_cartas no bloquea nada.
    ids_cartas_base = list(CARTAS.keys())
    fichas_por_carta_vacio = {cid: 0 for cid in ids_cartas_base}
    limite_repeticion_carta = n_sosp  # cualquier valor >= 1 alcanza: nunca se llega a tocarlo

    intentos = 0
    while intentos < max_intentos:
        intentos += 1

        # 73 y 74 son mutuamente excluyentes: se elige una al azar para este
        # intento y se excluye la otra del pool, así nunca pueden terminar
        # ambas en la misma ficha.
        omerta_elegida = random.choice([ID_CARTA_OMERTA, ID_CARTA_OMERTA_DEFENSA]) if permitir_omerta else None
        omerta_excluida = (ID_CARTA_OMERTA_DEFENSA if omerta_elegida == ID_CARTA_OMERTA else ID_CARTA_OMERTA) \
            if omerta_elegida is not None else None
        ids_cartas = [cid for cid in ids_cartas_base if cid != omerta_excluida]

        resultado = _armar_asignacion_cartas(
            sosp_ids=sosp_ids,
            SOSPECHOSOS=distrito_3,
            ids_cartas=ids_cartas,
            fichas_por_carta=fichas_por_carta_vacio,
            limite_repeticion_carta=limite_repeticion_carta,
            permitir_omerta=permitir_omerta,
        )
        if resultado is None:
            continue
        asignacion, sus = resultado

        # Garantizar la Omertá elegida en metrópoli/omertá: si el reparto al
        # azar no la incluyó esta vez, descartar y reintentar — nunca
        # insertarla a mano sobre una asignación ya armada (rompería la
        # validez del resto).
        if permitir_omerta and omerta_elegida not in asignacion.values():
            continue

        # Piso simétrico por dificultad para AMBOS lados (verdades y mentiras).
        cantidad = cantidad_fija if cantidad_fija is not None else random.randint(min_requerido, n_sosp - min_requerido)
        if cantidad < min_requerido or (n_sosp - cantidad) < min_requerido:
            continue

        mentiras_en_partida = n_sosp - cantidad
        if 62 in asignacion.values() and mentiras_en_partida < 2:
            continue

        culpable_tentativo = tiene_solucion_unica(asignacion, sus, cantidad, min_mentiras=min_requerido)
        if culpable_tentativo is None:
            continue

        n_vacias = sum(1 for cid in asignacion.values() if cid in CARTAS_TRIVIALES)
        if n_vacias > 1:
            continue

        if not validar_dificultad(asignacion, dificultad):
            continue

        if not validar_sin_solapamiento(asignacion, sus):
            continue

        if not validar_requisitos_categoria(asignacion):
            continue

        if not validar_tope_omerta(asignacion, sus):
            continue

        # Requisito de tensión narrativa: al menos una carta debe poder activar
        # Omertá (apuntar al declarante bajo algún candidato posible). Si la
        # amenaza sería siempre hueca, la ficha se descarta.
        if not validar_omerta_activable(asignacion, sus):
            continue

        culpable = culpable_tentativo

        if not validar_indirectas_en_ficha(asignacion, culpable, sus):
            continue

        return Ficha(
            id=0,   # se renumera junto con las N fichas del Caso o por separado, según exportación
            n_sospechosos=n_sosp,
            sospechosos=sosp_ids,
            asignacion=asignacion,
            culpable=culpable,
            cantidad=cantidad,
            dificultad=dificultad,
            distrito=ID_DISTRITO_SINTESIS,
            distrito_origen=dict(distrito_origen_por_sospechoso),
            es_conclusion=True,
        )

    return None   # no se encontró una asignación de cartas con solución única para el Distrito 3


# ── PRUEBA: generación rápida de un Distrito 3 sintético para iterar Omertá ──
def generar_distrito_3_aleatorio(dificultad: str, max_intentos: int = 10_000) -> tuple:
    """
    Sustituto rápido del Paso A+B+C reales del Caso, para poder probar la
    carta Omertá (y casos finales en general) sin tener que generar y cerrar
    un Caso completo cada vez. Toma una muestra al azar de sospechosos
    (mezclando ambos distritos, igual que haría un Distrito 3 real) y les
    asigna los atributos de uno de los dos distritos de origen, también al
    azar — así el resultado tiene la misma "forma" que un Distrito 3 real
    sin tener que correr los Pasos A/B/C.

    IMPORTANTE: aunque este atajo no corre _paso_b_agrupar_y_resolver_distrito
    ni _paso_c_validar_caso, el Distrito 3 que devuelve SÍ debe cumplir la
    Regla 2 (TOPE_REPETICION_ATRIBUTO) tal como la exige _paso_c_validar_caso
    en el camino real — de lo contrario esta vía de prueba puede colar
    distritos con, por ejemplo, 5 sospechosos "rico" cuando el tope es 4,
    algo que el Caso real nunca dejaría pasar. Por eso se reintenta el
    muestreo hasta que el resultado pase la misma Regla 2 (la Regla 1 ya
    queda garantizada porque n_sosp se toma fijo dentro del rango).

    Devuelve (distrito_3, distrito_origen_por_sospechoso) — el segundo es
    {sospechoso_id: 1 o 2}, de qué distrito salieron los atributos de cada
    sospechoso, para poder informarlo luego en el JSON igual que en una
    ficha-conclusión real.
    """
    rango_sosp = RANGO_SOSPECHOSOS_POR_DIFICULTAD[dificultad]
    ids_todos = list(SOSPECHOSOS_1.keys())

    for _ in range(max_intentos):
        n_sosp = random.randint(*rango_sosp)
        sosp_ids = random.sample(ids_todos, min(n_sosp, len(ids_todos)))

        distrito_3 = {}
        distrito_origen_por_sospechoso = {}
        for nombre_id in sosp_ids:
            origen = random.choice([1, 2])
            atributos = sospechosos_del_distrito(origen)[nombre_id]
            distrito_3[nombre_id] = {
                "nombre": atributos["nombre"],
                "clase":  atributos["clase"],
                "edad":   atributos["edad"],
            }
            distrito_origen_por_sospechoso[nombre_id] = origen

        if _paso_c_validar_caso(distrito_3, dificultad):
            return distrito_3, distrito_origen_por_sospechoso

    raise RuntimeError(
        f"No se pudo generar un Distrito 3 de prueba que cumpla la Regla 2 "
        f"(tope {TOPE_REPETICION_ATRIBUTO}) en {max_intentos} intentos."
    )


def _generar_ficha_conclusion_prueba(distrito_3: dict, distrito_origen_por_sospechoso: dict,
                                      cantidad_fija: Optional[int],
                                      dificultad: str, max_intentos: int = 200_000,
                                      distrito_id: int = ID_DISTRITO_SINTESIS) -> Optional[Ficha]:
    """
    Variante de _generar_ficha_conclusion que:
      1) FUERZA que una carta Omertá esté presente en la asignación
         (reintenta hasta lograrlo, igual que con cualquier otra condición
         de descarte del motor — no se "inserta" la carta a mano). Existen
         dos variantes mutuamente excluyentes, 73 (acusaciones) y 74
         (defensas): se elige una al azar para esta ficha y se excluye la
         otra del pool, nunca conviven.
      2) Aplica validar_tope_omerta para descartar asignaciones donde el
         apagón resultante sea demasiado grande o deje muy poca señal.

    El resto de las reglas (solución única, dificultad, solapamiento,
    requisitos de categoría, indirectas) son exactamente las mismas que en
    cualquier ficha — Omertá no se exime de ninguna validación existente,
    solo agrega una más encima.

    distrito_id: a qué slot de DISTRITOS apunta la ficha resultante mientras
    se genera. Por defecto ID_DISTRITO_SINTESIS (3), pero al generar un LOTE
    de varias fichas de prueba cada una necesita su propio slot interno —
    si todas compartieran el mismo slot 3 se pisarían entre sí mientras se
    generan, ya que sospechosos_del_distrito() siempre lee el valor ACTUAL
    de DISTRITOS[distrito_id]. El slot final que ve el JSON/UI se fuerza a 3
    al exportar (ver "Probar casos finales" en main), independientemente del
    slot interno usado aquí.
    """
    sosp_ids = sorted(distrito_3.keys())
    n_sosp = len(sosp_ids)
    ids_cartas_base = list(CARTAS.keys())
    min_requerido = {"urbano": 1, "metropoli": 2, "omerta": 3}[dificultad]

    fichas_por_carta_vacio = {cid: 0 for cid in ids_cartas_base}
    limite_repeticion_carta = n_sosp

    intentos = 0
    while intentos < max_intentos:
        intentos += 1

        # 73 y 74 son mutuamente excluyentes: se elige una al azar para este
        # intento y se excluye la otra del pool.
        omerta_elegida = random.choice([ID_CARTA_OMERTA, ID_CARTA_OMERTA_DEFENSA])
        omerta_excluida = ID_CARTA_OMERTA_DEFENSA if omerta_elegida == ID_CARTA_OMERTA else ID_CARTA_OMERTA
        ids_cartas = [cid for cid in ids_cartas_base if cid != omerta_excluida]

        resultado = _armar_asignacion_cartas(
            sosp_ids=sosp_ids,
            SOSPECHOSOS=distrito_3,
            ids_cartas=ids_cartas,
            fichas_por_carta=fichas_por_carta_vacio,
            limite_repeticion_carta=limite_repeticion_carta,
            permitir_omerta=True,
        )
        if resultado is None:
            continue
        asignacion, sus = resultado

        # Forzar presencia de la Omertá elegida: si esta asignación no la
        # incluyó (el reparto es al azar dentro del pool permitido), se
        # descarta y se reintenta — no se inserta la carta a mano en una
        # asignación ya armada, para no romper la validez del resto del
        # reparto.
        if omerta_elegida not in asignacion.values():
            continue

        # Piso simétrico por dificultad para AMBOS lados (verdades y mentiras).
        cantidad = cantidad_fija if cantidad_fija is not None else random.randint(min_requerido, n_sosp - min_requerido)
        if cantidad < min_requerido or (n_sosp - cantidad) < min_requerido:
            continue

        mentiras_en_partida = n_sosp - cantidad
        if 62 in asignacion.values() and mentiras_en_partida < 2:
            continue

        culpable_tentativo = tiene_solucion_unica(asignacion, sus, cantidad, min_mentiras=min_requerido)
        if culpable_tentativo is None:
            continue

        n_vacias = sum(1 for cid in asignacion.values() if cid in CARTAS_TRIVIALES)
        if n_vacias > 1:
            continue

        if not validar_dificultad(asignacion, dificultad):
            continue

        if not validar_sin_solapamiento(asignacion, sus):
            continue

        if not validar_requisitos_categoria(asignacion):
            continue

        # Chequeo propio de Omertá: tope de apagado + mínimo de cartas vivas.
        if not validar_tope_omerta(asignacion, sus):
            continue

        # Requisito de tensión narrativa: al menos una carta debe poder activar
        # Omertá (apuntar al declarante bajo algún candidato posible). Si la
        # amenaza sería siempre hueca, la ficha se descarta.
        if not validar_omerta_activable(asignacion, sus):
            continue

        culpable = culpable_tentativo

        if not validar_indirectas_en_ficha(asignacion, culpable, sus):
            continue

        return Ficha(
            id=0,
            n_sospechosos=n_sosp,
            sospechosos=sosp_ids,
            asignacion=asignacion,
            culpable=culpable,
            cantidad=cantidad,
            dificultad=dificultad,
            distrito=distrito_id,
            distrito_origen=dict(distrito_origen_por_sospechoso),
            es_conclusion=True,
        )

    return None

