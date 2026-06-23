"""
Exportación a TXT: ficha "maestra" (con culpable y V/M visibles) y ficha
"jugable" (ofuscada, sin spoilers), con el formato de caja ASCII y el
reglamento narrativo del juego.
"""

from datetime import datetime

from datos import sospechosos_del_distrito, nombre_distrito
from cartas import TEXTOS_CARTAS, CATEGORIAS_CARTAS
from validaciones import evaluar_carta
from generacion import Ficha

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
    pool = sospechosos_del_distrito(f.distrito)
    sus = {i: pool[i] for i in f.sospechosos}
    etiqueta_modo = f"{f.cantidad} {f.modo} en la partida"
    bloques = []

    bloques.append(tope_sup())
    bloques.append(linea(f"FICHA DE CASO  #{f.id:02d}  [{f.dificultad.upper()}]"))
    bloques.append(linea(f"{nombre_distrito(f.distrito)}"))
    bloques.append(linea(f"{f.n_sospechosos} sospechosos  │  {etiqueta_modo}"))
    bloques.append(separador())
    bloques.append(linea(f"{'#':<3} {'Sospechoso':<16} {'Clase':<8} {'Edad':<10} {'Carta'}"))
    bloques.append(separador())

    for sid in f.sospechosos:
        s = pool[sid]
        carta_id = f.asignacion[sid]
        fila = f"{sid:<3} {s['nombre']:<16} {s['clase']:<8} {s['edad']:<10} #{carta_id:02d}"
        bloques.append(linea(fila))

    bloques.append(separador())
    culp_nombre = pool[f.culpable]["nombre"]
    bloques.append(linea(f"CULPABLE: {f.culpable}  [{culp_nombre}]"))
    bloques.append(linea("          [NÚMERO OCULTO EN TINTA ROJA]"))
    bloques.append(separador())
    bloques.append(linea("DECLARACIONES  (V = verdad  M = mentira)"))
    bloques.append(separador())

    for sid in f.sospechosos:
        carta_id = f.asignacion[sid]
        texto    = TEXTOS_CARTAS[carta_id]
        verdad   = evaluar_carta(carta_id, f.culpable, sid, sus, f.asignacion)
        estado   = "V" if verdad else "M"
        nombre   = pool[sid]["nombre"]
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
        "  FICHAS DE CASO  —  Juego de deducción noir",
        f"  Generado: {ts}   Total: {len(fichas)} fichas",
        "═" * (W + 2),
    ])
    cuerpo = "\n\n".join(ficha_a_txt(f) for f in fichas)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(REGLAMENTO + "\n" + cabecera + "\n\n" + cuerpo + "\n")
    print(f"\n  TXT guardado  →  {ruta}")

def ficha_a_txt_jugable(f: Ficha) -> str:
    """Versión jugable: sin culpable visible ni V/M en declaraciones."""
    pool = sospechosos_del_distrito(f.distrito)
    bloques = []

    bloques.append(tope_sup())
    bloques.append(linea(f"FICHA DE CASO  #{f.id:02d}  [NIVEL {f.dificultad.upper()}]"))
    bloques.append(linea(f"{nombre_distrito(f.distrito)}"))
    bloques.append(linea(f"{f.n_sospechosos} sospechosos  │  {f.cantidad} verdades en la partida"))
    bloques.append(separador())
    bloques.append(linea(f"{'#':<3} {'Sospechoso':<16} {'Clase':<8} {'Edad':<10} {'Carta'}"))
    bloques.append(separador())

    for sid in f.sospechosos:
        s = pool[sid]
        carta_id = f.asignacion[sid]
        fila = f"{sid:<3} {s['nombre']:<16} {s['clase']:<8} {s['edad']:<10} #{carta_id:02d}"
        bloques.append(linea(fila))

    bloques.append(separador())
    bloques.append(linea("DECLARACIONES"))
    bloques.append(separador())

    for sid in f.sospechosos:
        carta_id = f.asignacion[sid]
        texto    = TEXTOS_CARTAS[carta_id]
        nombre   = pool[sid]["nombre"]
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
        pool = sospechosos_del_distrito(f.distrito)
        sus = {i: pool[i] for i in f.sospechosos}
        culp_nombre = pool[f.culpable]["nombre"]
        estados = []
        for sid in f.sospechosos:
            carta_id = f.asignacion[sid]
            verdad = evaluar_carta(carta_id, f.culpable, sid, sus, f.asignacion)
            estados.append("V" if verdad else "M")
        vm_str = " ".join(estados)
        lineas.append(f"  #{f.id:02d}  [D{f.distrito}]  Culpable: {culp_nombre:<16}  [{vm_str}]")
    lineas.append(sep)
    return "\n".join(lineas)

def exportar_txt_jugable(fichas: list, ruta: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    cabecera = "\n".join([
        "═" * (W + 2),
        "  FICHAS DE CASO  —  CÓDIGO OMERTÁ",
        f"  Generado: {ts}   Total: {len(fichas)} fichas",
        "═" * (W + 2),
    ])
    cuerpo = "\n\n".join(ficha_a_txt_jugable(f) for f in fichas)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(REGLAMENTO + "\n" + cabecera + "\n\n" + cuerpo + "\n")
        fh.write(resumen_soluciones(fichas) + "\n")
    print(f"  TXT jugable   →  {ruta}")

