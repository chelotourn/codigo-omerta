"""
Modelo de Ficha y motor de generación: reparto de cartas a sospechosos
respetando todas las restricciones de presencia/diversidad/categoría, y
búsqueda por fuerza bruta de fichas con solución única.
"""

import math
import random
from dataclasses import dataclass
from typing import Optional

import cartas
import datos
from datos import (
    SOSPECHOSOS_1, sospechosos_del_distrito, PORC_MAX_REPETICION_CARTA,
    MOSTRAR_INFORME_CARTAS,
)
from cartas import (
    CARTAS, CATEGORIAS_CARTAS, TEXTOS_CARTAS, CARTAS_SIEMPRE_VERDAD,
    ID_CARTA_OMERTA,
)
from validaciones import (
    tiene_solucion_unica, evaluar_carta, validar_dificultad,
    validar_sin_solapamiento, validar_requisitos_categoria,
)
from cartas import validar_indirectas_en_ficha

# Alias mutable (igual que en datos.py): generar_fichas lo reasigna en cada
# intento al pool del distrito que corresponda. Vive también aquí, y no solo
# en datos.py, porque "global SOSPECHOSOS" dentro de generar_fichas solo
# puede mutar un nombre del namespace de ESTE módulo.
SOSPECHOSOS = SOSPECHOSOS_1

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
    distrito: int = 1            # 1 = Distrito Industrial | 2 = Distrito Comercial | 3 = Codigo Omertá (ficha-conclusión)
    distrito_origen: Optional[dict] = None  # solo en ficha-conclusión: {sospechoso_id: 1 o 2} — de qué distrito
                                              # ganó cada sospechoso en el desempate del Paso B. Puramente
                                              # informativo/debug para la UI web; ninguna regla de juego lo usa.
    es_conclusion: bool = False              # True solo para la ficha-conclusión de un Caso


def mezclar_y_renumerar(fichas: list, distrito_modo: int = 0) -> list:
    """
    Reordena las fichas al azar (in-place) y renumera sus IDs desde 1 en ese
    nuevo orden. Debe llamarse UNA sola vez por corrida, después de generar
    las fichas y antes de exportarlas, para que TXT y JSON queden con el
    mismo orden y la misma numeración.

    Si distrito_modo == 0 (alternado), un shuffle plano rompería el patrón
    1, 2, 1, 2... con el que generar_fichas fue armando las fichas. En ese
    caso se mezcla CADA grupo de distrito por separado y luego se vuelven a
    intercalar — así el orden final es aleatorio dentro de cada distrito pero
    la secuencia de distritos sigue siendo alternada.
    Para distrito_modo fijo (1 o 2) se hace un shuffle plano normal, ya que
    todas las fichas pertenecen al mismo distrito de todos modos.
    """
    if distrito_modo == 0 and fichas:
        grupo1 = [f for f in fichas if f.distrito == 1]
        grupo2 = [f for f in fichas if f.distrito == 2]
        random.shuffle(grupo1)
        random.shuffle(grupo2)
        nuevas = []
        i1 = i2 = 0
        while i1 < len(grupo1) or i2 < len(grupo2):
            if i1 < len(grupo1):
                nuevas.append(grupo1[i1]); i1 += 1
            if i2 < len(grupo2):
                nuevas.append(grupo2[i2]); i2 += 1
        fichas[:] = nuevas
    else:
        random.shuffle(fichas)
    for i, f in enumerate(fichas, start=1):
        f.id = i
    return fichas


def _armar_asignacion_cartas(sosp_ids: list, SOSPECHOSOS: dict, ids_cartas: list,
                              fichas_por_carta: dict, limite_repeticion_carta: int,
                              permitir_omerta: bool = False):
    """
    Reparte una carta a cada sospechoso de sosp_ids, respetando todas las
    restricciones de presencia / tercera persona / pluralidad / diversidad.

    Extraído de generar_fichas para que el mismo reparto de cartas pueda
    reusarse tanto para una ficha normal (sosp_ids muestreados al azar de un
    solo distrito) como para la ficha-conclusión de un Caso (sosp_ids fijos,
    viniendo de un pool ya resuelto — el "Distrito 3" dinámico).

    permitir_omerta: la carta 73 (Omertá) solo se reparte si este flag es
    True. Por diseño, Omertá es exclusiva de la ficha-conclusión del Caso
    en dificultad metrópoli y omertá — en fichas normales y en urbano
    queda vetada.

    Devuelve (asignacion, sus) si se pudo completar, o None si algún
    sospechoso se quedó sin cartas disponibles en el pool.
    """
    sus = {i: SOSPECHOSOS[i] for i in sosp_ids}
    asignacion = {}
    cartas_usadas = set()
    for sid in sosp_ids:
        pool = [
            cid for cid in ids_cartas
            if cid not in cartas_usadas
            # Diversidad: la carta ya alcanzó su tope de fichas en esta corrida
            and fichas_por_carta[cid] < limite_repeticion_carta
            # Carta especial Omertá: solo disponible si se permite explícitamente
            and not (cid == ID_CARTA_OMERTA and not permitir_omerta)
            # Restricciones de presencia: el sospechoso nombrado debe estar en la partida
            and not (cid == 1  and 3 not in sosp_ids)
            and not (cid == 2  and 1 not in sosp_ids)
            and not (cid == 3  and 6 not in sosp_ids)
            and not (cid == 4  and 5 not in sosp_ids)
            and not (cid == 5  and 2 not in sosp_ids)
            and not (cid == 6  and 4 not in sosp_ids)
            and not (cid == 7  and not (8 in sosp_ids and 9 in sosp_ids))
            and not (cid == 8  and not (3 in sosp_ids and 7 in sosp_ids))
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
            # Cartas meta/indirectas: verifican que la categoría requerida esté disponible
            # en las cartas aún no usadas (no en asignacion parcial — el orden no importa al jugador)
            # #26: necesita >=1 descriptiva Y >=1 duda disponibles
            and not (cid == 26 and not (
                any(CATEGORIAS_CARTAS.get(c) == "descriptiva" for c in ids_cartas if c not in cartas_usadas and c != cid) and
                any(CATEGORIAS_CARTAS.get(c) == "duda"        for c in ids_cartas if c not in cartas_usadas and c != cid)
            ))
            # #57: necesita >=1 defensa disponible
            and not (cid == 57 and not any(CATEGORIAS_CARTAS.get(c) == "defensa"     for c in ids_cartas if c not in cartas_usadas and c != cid))
            # #58: necesita >=1 acusación disponible
            and not (cid == 58 and not any(CATEGORIAS_CARTAS.get(c) == "acusación"   for c in ids_cartas if c not in cartas_usadas and c != cid))
            # #59: necesita >=1 defensa disponible
            and not (cid == 59 and not any(CATEGORIAS_CARTAS.get(c) == "defensa"     for c in ids_cartas if c not in cartas_usadas and c != cid))
            # #61: necesita >=1 descriptiva disponible
            and not (cid == 61 and not any(CATEGORIAS_CARTAS.get(c) == "descriptiva" for c in ids_cartas if c not in cartas_usadas and c != cid))
            # #63: necesita >=1 acusación Y >=1 defensa disponibles
            and not (cid == 63 and not (
                any(CATEGORIAS_CARTAS.get(c) == "acusación" for c in ids_cartas if c not in cartas_usadas and c != cid) and
                any(CATEGORIAS_CARTAS.get(c) == "defensa"   for c in ids_cartas if c not in cartas_usadas and c != cid)
            ))
            # #64: requiere >=1 viejo presente (excl. declarante) y ninguna duda disponible en el resto
            and not (cid == 64 and sum(1 for x in sosp_ids if x != sid and SOSPECHOSOS[x]["edad"] == "viejo") < 1)
            and not (cid == 64 and any(CATEGORIAS_CARTAS.get(asignacion.get(x)) == "duda" for x in asignacion))
            # #65: necesita >=1 defensa Y >=1 descriptiva disponibles
            and not (cid == 65 and not (
                any(CATEGORIAS_CARTAS.get(c) == "defensa"     for c in ids_cartas if c not in cartas_usadas and c != cid) and
                any(CATEGORIAS_CARTAS.get(c) == "descriptiva" for c in ids_cartas if c not in cartas_usadas and c != cid)
            ))
            # #72: necesita >=1 acusación disponible Y >=1 pobre en la partida (excl. declarante)
            and not (cid == 72 and not any(CATEGORIAS_CARTAS.get(c) == "acusación" for c in ids_cartas if c not in cartas_usadas and c != cid))
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
            and not (cid == 48 and not any(SOSPECHOSOS[x]["clase"] == "pobre" for x in sosp_ids))
            and not (cid == 56 and not any(SOSPECHOSOS[x]["edad"] == "mediana" for x in sosp_ids))            
            # Carta 43: "era pobre..." — necesita al menos 1 pobre presente en la partida
            and not (cid == 43 and not any(SOSPECHOSOS[x]["clase"] == "pobre" for x in sosp_ids))
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
            # Carta 49: "ni pobre ni joven" — necesita al menos 1 sospechoso que no sea pobre ni joven
            and not (cid == 49 and not any(SOSPECHOSOS[x]["clase"] != "pobre" and SOSPECHOSOS[x]["edad"] != "joven" for x in sosp_ids))
            # Carta 50: "ni clase media ni mediana edad" — necesita al menos 1 sospechoso que no sea de clase media ni mediana edad
            and not (cid == 50 and not any(SOSPECHOSOS[x]["clase"] != "media" and SOSPECHOSOS[x]["edad"] != "mediana" for x in sosp_ids))
            # Cartas grupales: requieren pluralidad del grupo que referencian
            and not (cid == 54 and sum(1 for x in sosp_ids if SOSPECHOSOS[x]["clase"] == "rico")  < 2)
            and not (cid == 55 and sum(1 for x in sosp_ids if SOSPECHOSOS[x]["edad"]  == "viejo") < 2)
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
            and not (cid == 7  and sid in (8, 9))
            and not (cid == 8  and sid in (3, 7))
            and not (cid == 9  and sid in (2, 5))
            and not (cid == 12 and sid == 1)
            and not (cid == 13 and sid == 3)
            and not (cid == 14 and sid == 4)
            and not (cid == 15 and sid == 6)
            and not (cid == 16 and sid in (1, 4))
            and not (cid == 17 and sid in (2, 5))
            and not (cid == 18 and sid in (3, 6))
            and not (cid == 37 and sid == 4)
            and not (cid == 38 and sid == 2)
            and not (cid == 51 and sid in (1, 4))
            and not (cid == 52 and sid in (2, 3))
            and not (cid == 53 and sid in (5, 6))
            # Carta 54: el declarante no puede ser rico — el texto habla de
            # "los ricos" como un grupo ajeno ("ellos"), y la lógica ya excluye
            # al declarante al evaluar si "alguno rico miente". Si el propio
            # declarante fuera rico, el texto se leería como ambiguo/auto-
            # incluyente aunque la lógica lo excluya, induciendo a error.
            and not (cid == 54 and SOSPECHOSOS[sid]["clase"] == "rico")
            # Indirectas: no pueden asignarse al sospechoso que referencian
            # #65 ya no referencia a un sospechoso nombrado; restricciones se manejan abajo
            and not (cid == 66 and sid == 9)   # #66 referencia al Vagabundo
            and not (cid == 67 and sid == 7)   # #67 referencia al Heredero
            and not (cid == 68 and sid == 8)   # #68 referencia al Crupier
            # #69: necesita al menos 1 sospechoso de clase media presente (excl. declarante)
            # para que su antecedente A pueda activarse; sin clase media la carta siempre es False
            and not (cid == 69 and not any(SOSPECHOSOS[x]["clase"] == "media" for x in sosp_ids if x != sid))
            # #72 ya no referencia a ningún sospechoso nominado → sin restricción de tercera persona
            # #60 y #71 son mutuamente excluyentes: ambas usan la lógica de "mayoría miente"
            # y combinarlas en la misma ficha resulta redundante/confuso. Si una ya fue
            # asignada a otro sospechoso de esta ficha, la otra queda vetada.
            and not (cid == 60 and 71 in asignacion.values())
            and not (cid == 71 and 60 in asignacion.values())
        ]
        if not pool:
            return None
        cid = random.choice(pool)
        asignacion[sid] = cid
        cartas_usadas.add(cid)
    return asignacion, sus


def generar_fichas(n_fichas: int, modo: str, cantidad_fija: Optional[int],
                   max_intentos: int = 200_000, seed: Optional[int] = None,
                   n_sosp_fijo: int = 0, dificultad: str = "urbano",
                   distrito_modo: int = 0) -> list:
    """
    distrito_modo: 0 = alterna entre distritos ficha a ficha (1, 2, 1, 2, ...)
                   1 = todas las fichas usan el Distrito Industrial
                   2 = todas las fichas usan el Distrito Comercial
    """
    global SOSPECHOSOS
    if seed is not None:
        random.seed(seed)

    ids_todos  = list(SOSPECHOSOS_1.keys())   # los ids son iguales en ambos distritos
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
    verdades_por_carta = {cid: 0 for cid in ids_cartas}  # veces que la carta fue V en su ficha
    mentiras_por_carta = {cid: 0 for cid in ids_cartas}  # veces que la carta fue M en su ficha

    nombre_modo_distrito = {
        0: "cíclico (Industrial / Comercial)",
        1: "fijo — Distrito Industrial",
        2: "fijo — Distrito Comercial",
    }[distrito_modo]
    print(f"\n  Buscando {n_fichas} fichas — modo {modo.upper()} — dificultad {dificultad.upper()} ...")
    print(f"  Distrito: {nombre_modo_distrito}.")
    print(f"  Límite de diversidad: cada carta en máx. {limite_repeticion_carta} ficha(s) de esta corrida ({int(PORC_MAX_REPETICION_CARTA*100)}%).")
    print("  " + "─" * 46)

    while len(fichas) < n_fichas and intentos < max_intentos:
        intentos += 1

        # ── Distrito de esta ficha ──
        # La alternancia se calcula sobre la cantidad de fichas YA ACEPTADAS
        # (no sobre los intentos), de forma que la secuencia de fichas resultante
        # sea 1, 2, 1, 2, ... aunque algunos intentos individuales fallen.
        if distrito_modo == 0:
            distrito_actual = 1 if (len(fichas) % 2 == 0) else 2
        else:
            distrito_actual = distrito_modo
        SOSPECHOSOS = sospechosos_del_distrito(distrito_actual)

        rango_sosp = {"urbano": (3, 5), "metropoli": (4, 6), "omerta": (5, 8)}[dificultad]
        n_sosp    = n_sosp_fijo if n_sosp_fijo >= rango_sosp[0] else random.randint(*rango_sosp)
        sosp_ids  = sorted(random.sample(ids_todos, n_sosp))

        resultado = _armar_asignacion_cartas(
            sosp_ids=sosp_ids,
            SOSPECHOSOS=SOSPECHOSOS,
            ids_cartas=ids_cartas,
            fichas_por_carta=fichas_por_carta,
            limite_repeticion_carta=limite_repeticion_carta,
        )
        if resultado is None:
            continue
        asignacion, sus = resultado

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

        # Validar requisitos de categoría (carta 26, 57, 58, 59, 61, 63, 65, 72):
        # descarta fichas donde la carta exige una categoría de apoyo (descriptiva,
        # duda, acusación, defensa) que terminó NO estando presente en el reparto final.
        if not validar_requisitos_categoria(asignacion):
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
        sus_ficha = {i: SOSPECHOSOS[i] for i in sosp_ids}
        for sid_usado, cid_usado in asignacion.items():
            fichas_por_carta[cid_usado] += 1
            if evaluar_carta(cid_usado, culpable, sid_usado, sus_ficha, asignacion):
                verdades_por_carta[cid_usado] += 1
            else:
                mentiras_por_carta[cid_usado] += 1

        fichas.append(Ficha(
            id=len(fichas) + 1,
            n_sospechosos=n_sosp,
            sospechosos=sosp_ids,
            asignacion=asignacion,
            culpable=culpable,
            modo=modo,
            cantidad=cantidad,
            dificultad=dificultad,
            distrito=distrito_actual,
        ))
        print(f"  Ficha #{len(fichas):02d} encontrada  (intento {intentos})")

    print(f"\n  Total encontradas : {len(fichas)} / {n_fichas}")
    print(f"  Total intentos    : {intentos}")

    if MOSTRAR_INFORME_CARTAS and fichas:
        sep = "─" * 46
        usadas = {cid: cnt for cid, cnt in fichas_por_carta.items() if cnt > 0}
        ordenadas = sorted(usadas.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  {sep}")
        print("  INFORME DE CARTAS — apariciones por ficha")
        print(f"  {sep}")
        for cid, cnt in ordenadas:
            cat = CATEGORIAS_CARTAS.get(cid, "?")
            texto_corto = TEXTOS_CARTAS.get(cid, "")[:38].rstrip()
            v = verdades_por_carta.get(cid, 0)
            m = mentiras_por_carta.get(cid, 0)
            print(f"  #{cid:02d} ({cat:<10}) [{cnt:>3}]  V:{v:<4} M:{m:<4}  \"{texto_corto}...\"")
        print(f"  {sep}")
        no_usadas = [cid for cid, cnt in fichas_por_carta.items() if cnt == 0]
        if no_usadas:
            ids_str = ", ".join(f"#{c}" for c in sorted(no_usadas))
            print(f"  Sin usar ({len(no_usadas)}): {ids_str}")
        print(f"  {sep}")

    return fichas
