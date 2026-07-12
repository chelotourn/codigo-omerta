"""
Exportación a JSON: representación estructurada de cada ficha (incluyendo
veracidad de cada declaración) y del resultado completo de un Caso con su
ficha-conclusión.
"""

import json
from datetime import datetime

from datos import sospechosos_del_distrito, nombre_distrito
import cartas
from cartas import CATEGORIAS_CARTAS, TEXTOS_CARTAS, calcular_cartas_silenciadas
from validaciones import _evaluar_sin_setup
from generacion import Ficha
from exportar_txt import (
    W, REGLAMENTO, linea, ficha_a_txt, ficha_a_txt_jugable, resumen_soluciones,
)

# ─────────────────────────────────────────────

def ficha_a_dict(f: Ficha) -> dict:
    pool = sospechosos_del_distrito(f.distrito)
    sus = {i: pool[i] for i in f.sospechosos}
    # Setup global una sola vez — igual que tiene_solucion_unica — para que las
    # cartas meta/veracidad se evalúen con el mismo contexto que usó la validación.
    # Usar evaluar_carta por separado limpiaba _MAYORIA_CACHE entre declaraciones,
    # lo que causaba que el conteo de es_verdad difiriera del campo `cantidad`.
    cartas.ASIGNACION_EVAL.clear()
    cartas.ASIGNACION_EVAL.update(f.asignacion)
    cartas._VISITADOS_EVAL.clear()
    cartas._MAYORIA_CACHE.clear()
    silenciadas = calcular_cartas_silenciadas(f.asignacion, f.culpable, sus, incluir_declarante=True)
    cartas._SILENCIADAS_EVAL.clear()
    cartas._SILENCIADAS_EVAL.update(silenciadas)
    declaraciones = []
    for sid in f.sospechosos:
        carta_id   = f.asignacion[sid]
        silenciada = sid in silenciadas
        # Las cartas silenciadas no cuentan como verdad ni mentira; es_verdad
        # queda None para que la UI pueda distinguirlas de un V/M real.
        verdad = None if silenciada else _evaluar_sin_setup(carta_id, f.culpable, sid, sus)
        declaracion = {
            "sospechoso_id"  : sid,
            "sospechoso"     : pool[sid]["nombre"],
            "clase"          : pool[sid]["clase"],
            "edad"           : pool[sid]["edad"],
            "carta_id"       : carta_id,
            "carta_categoria": CATEGORIAS_CARTAS[carta_id],
            "carta_texto"    : TEXTOS_CARTAS[carta_id],
            "silenciada"     : silenciada,
            "es_verdad"      : verdad,
        }
        # distrito_origen: solo presente en la ficha-conclusión. Puramente
        # informativo/debug para la UI web — ninguna regla de juego lo usa.
        if f.distrito_origen is not None and sid in f.distrito_origen:
            declaracion["distrito_origen"] = f.distrito_origen[sid]
        declaraciones.append(declaracion)
    return {
        "ficha_id"        : f.id,
        "distrito_id"     : f.distrito,
        "distrito_nombre" : nombre_distrito(f.distrito),
        "es_conclusion"   : f.es_conclusion,
        "n_sospechosos"   : f.n_sospechosos,
        "sospechosos_ids" : f.sospechosos,
        "cantidad"        : f.cantidad,
        "dificultad"      : f.dificultad,
        "culpable_id"     : f.culpable,
        "culpable_nombre" : pool[f.culpable]["nombre"],
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


def exportar_caso(resultado_caso: dict, ruta_base: str, jugable: bool = False):
    """
    Toma el dict devuelto por generar_caso(...) y escribe a disco:
      {ruta_base}.txt   — las N fichas + la ficha-conclusión al final
      {ruta_base}.json  — idem, más un bloque "caso" con metadatos del cierre

    Si resultado_caso["descartado"] es True (se agotaron los reintentos sin
    cerrar el Caso), no hay ficha_conclusion: se exportan igual las fichas
    disponibles (puede ser una lista vacía) y el JSON deja constancia del
    descarte en el bloque "caso".

    La ficha-conclusión se renumera como la ficha N+1 y queda marcada con
    es_conclusion=True tanto en el TXT (encabezado) como en el JSON.
    """
    fichas = list(resultado_caso["fichas"])
    ficha_conclusion = resultado_caso["ficha_conclusion"]

    # Renumerar: las N fichas ya tienen id 1..N (asignado por generar_fichas).
    # La ficha-conclusión, si existe, pasa a ser la N+1 — al final, nunca mezclada.
    if ficha_conclusion is not None:
        ficha_conclusion.id = len(fichas) + 1
        fichas_a_exportar = fichas + [ficha_conclusion]
    else:
        fichas_a_exportar = fichas

    ruta_txt  = f"{ruta_base}.txt"
    ruta_json = f"{ruta_base}.json"

    # ── TXT ──
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    estado_caso = "CASO CERRADO — con ficha-conclusión" if ficha_conclusion is not None \
        else ("CASO DESCARTADO — sin ficha-conclusión" if resultado_caso["descartado"]
              else "CASO ABIERTO — sin ficha-conclusión (no convergió)")
    cabecera = "\n".join([
        "═" * (W + 2),
        "  CASO — CÓDIGO OMERTÁ",
        f"  Generado: {ts}   Fichas del Caso: {len(fichas)}   {estado_caso}",
        f"  Reintentos de Caso: {resultado_caso['reintentos_caso']}",
        f"  {resultado_caso.get('motivo', '')}",
        "═" * (W + 2),
    ])
    fn_ficha = ficha_a_txt_jugable if jugable else ficha_a_txt
    bloques_txt = []
    for f in fichas_a_exportar:
        if f.es_conclusion:
            bloques_txt.append(linea("▼" * (W - 2)))
            bloques_txt.append(linea("FICHA-CONCLUSIÓN DEL CASO"))
            bloques_txt.append(linea("▲" * (W - 2)))
            bloques_txt.append("")
        bloques_txt.append(fn_ficha(f))
    cuerpo = "\n\n".join(bloques_txt)
    with open(ruta_txt, "w", encoding="utf-8") as fh:
        fh.write(REGLAMENTO + "\n" + cabecera + "\n\n" + cuerpo + "\n")
        if jugable:
            fh.write(resumen_soluciones(fichas_a_exportar) + "\n")
    print(f"\n  TXT del Caso  →  {ruta_txt}")

    # ── JSON ──
    datos = {
        "generado": datetime.now().isoformat(),
        "caso": {
            "n_fichas_caso"     : len(fichas),
            "descartado"        : resultado_caso["descartado"],
            "reintentos_caso"   : resultado_caso["reintentos_caso"],
            "tiene_conclusion"  : ficha_conclusion is not None,
            "conclusion_ficha_id": ficha_conclusion.id if ficha_conclusion is not None else None,
            "motivo"            : resultado_caso.get("motivo", ""),
        },
        "total_fichas": len(fichas_a_exportar),
        "fichas"      : [ficha_a_dict(f) for f in fichas_a_exportar],
    }
    with open(ruta_json, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)
    print(f"  JSON del Caso →  {ruta_json}")

