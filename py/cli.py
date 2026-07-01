"""
Interfaz interactiva de consola: lee las opciones del usuario (dificultad,
cantidad de sospechosos, distrito, semilla, etc.) y dispara el flujo de
generación correspondiente (fichas normales, Caso completo, modo Mixta para
sitio web, o Casos Finales de prueba para iterar el balance de Omertá).
"""

import json
import os
from datetime import datetime
from typing import Optional

import datos
from datos import (
    DISTRITOS, nombre_distrito, sospechosos_del_distrito,
    TOPE_CARTAS_APAGADAS_OMERTA, MINIMO_CARTAS_VIVAS_TRAS_OMERTA,
)
from cartas import calcular_cartas_silenciadas
from generacion import generar_fichas, mezclar_y_renumerar
from caso import (
    generar_caso, generar_distrito_3_aleatorio, _generar_ficha_conclusion_prueba,
    ID_DISTRITO_SINTESIS,
)
from exportar_txt import REGLAMENTO, W, ficha_a_txt, exportar_txt, exportar_txt_jugable
from exportar_json import ficha_a_dict, exportar_json, exportar_caso

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

    # ── Nivel de dificultad ──
    print("\n  ¿Nivel de DIFICULTAD?")
    print("  [1] Urbano    (sin cartas meta ni indirectas)")
    print("  [2] Metrópoli (máximo 1 carta meta o indirecta)")
    print("  [3] Omertà    (requiere al menos 1 meta y 1 indirecta)")
    print("  [4] Mixta     (genera 3 JSON para sitio web: 5+1 urbano, 7+1 metro, 9+1 omertà)")
    print("  [5] Caso Final (genera Distritos 3 sintéticos forzando Omertá)")
    nivel = pedir_entero("  Elegí una opción [1-5]: ", minimo=1, maximo=5)

    # ── Probar casos finales: generación rápida de fichas-conclusión con ──
    # Omertá forzada, sin tener que generar y cerrar un Caso completo cada
    # vez. Útil para iterar el balance de la carta Omertá (tope de cartas
    # apagadas / mínimo de cartas vivas) de forma aislada.
    if nivel == 5:
        dificultad_prueba = {1: "urbano", 2: "metropoli", 3: "omerta"}[
            pedir_entero(
                "\n  ¿Dificultad para el Distrito 3 de prueba?\n"
                "  [1] Urbano [2] Metrópoli [3] Omertà: ", minimo=1, maximo=3)
        ]
        n_fichas_prueba = pedir_entero(
            "\n  ¿Cuántos casos finales de prueba generar? [1-50]: ",
            minimo=1, maximo=50
        )
        print(f"\n  Tope actual de cartas apagadas por Omertá: {TOPE_CARTAS_APAGADAS_OMERTA}")
        print(f"  Mínimo de cartas vivas exigido: {MINIMO_CARTAS_VIVAS_TRAS_OMERTA}")
        print("  (editar TOPE_CARTAS_APAGADAS_OMERTA / MINIMO_CARTAS_VIVAS_TRAS_OMERTA")
        print("   al inicio del archivo para ajustar el balance entre corridas)")
        print(f"  Generando {n_fichas_prueba} casos finales de prueba...")

        max_intentos_distrito = 500
        fichas = []
        resumenes = []   # (n_silenciadas, n_intentos_distrito) por ficha, para el resumen final

        for n_ficha in range(1, n_fichas_prueba + 1):
            slot_interno = 1000 + n_ficha   # slot único por ficha del lote, no pisa 1/2/3 reales
            intento_distrito = 0
            ficha = None
            distrito_3 = None
            while intento_distrito < max_intentos_distrito and ficha is None:
                intento_distrito += 1
                distrito_3, distrito_origen_por_sospechoso = generar_distrito_3_aleatorio(dificultad_prueba)
                DISTRITOS[slot_interno] = {
                    "nombre": f"Operación Código Omertá (prueba #{n_ficha})",
                    "sospechosos": distrito_3,
                }
                ficha = _generar_ficha_conclusion_prueba(
                    distrito_3=distrito_3,
                    distrito_origen_por_sospechoso=distrito_origen_por_sospechoso,
                    cantidad_fija=None,
                    dificultad=dificultad_prueba,
                    max_intentos=20_000,
                    distrito_id=slot_interno,
                )

            if ficha is None:
                print(f"\n  Caso final #{n_ficha}: no se logró armar tras "
                      f"{intento_distrito} Distritos-3 de prueba. Se omite y se sigue con el próximo.")
                continue

            ficha.id = n_ficha
            sus = {i: distrito_3[i] for i in ficha.sospechosos}
            silenciadas = calcular_cartas_silenciadas(ficha.asignacion, ficha.culpable, sus)
            fichas.append(ficha)
            resumenes.append((len(silenciadas), intento_distrito))
            print(f"  Caso final #{n_ficha}: listo (silenciadas={len(silenciadas)}, "
                  f"intentos de distrito={intento_distrito})")

        if not fichas:
            print("\n  No se logró armar ningún caso final con Omertá. Probá subir el tope.")
            return

        carpeta = "."
        ts_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_txt  = os.path.join(carpeta, f"casos_finales_{ts_archivo}.txt")
        ruta_json = os.path.join(carpeta, f"casos_finales_{ts_archivo}.json")

        # ── Forzar distrito_id=3 de cara afuera (TXT/JSON), aunque cada ──
        # ficha se generó en su propio slot interno para no pisarse entre
        # sí durante la búsqueda. Se exporta ficha por ficha: antes de cada
        # una se carga DISTRITOS[3] con el pool correcto de esa ficha, y la
        # ficha se reapunta a distrito=3 — así nunca hay dos fichas leyendo
        # el slot 3 al mismo tiempo con datos ajenos.
        bloques_txt = []
        dicts_json = []
        for f in fichas:
            pool_ficha = sospechosos_del_distrito(f.distrito)  # slot interno único (1000+n)
            DISTRITOS[ID_DISTRITO_SINTESIS] = {
                "nombre": "Caso Final — Romper Omertá",
                "sospechosos": pool_ficha,
            }
            f.distrito = ID_DISTRITO_SINTESIS
            bloques_txt.append(ficha_a_txt(f))
            dicts_json.append(ficha_a_dict(f))

        cabecera_txt = "\n".join([
            "═" * (W + 2),
            "  CASOS FINALES — ROMPER OMERTÁ",
            f"  Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}   "
            f"Casos: {len(fichas)}/{n_fichas_prueba}",
            f"  Tope cartas apagadas: {TOPE_CARTAS_APAGADAS_OMERTA}   "
            f"Mínimo cartas vivas: {MINIMO_CARTAS_VIVAS_TRAS_OMERTA}",
            "═" * (W + 2),
        ])
        with open(ruta_txt, "w", encoding="utf-8") as fh:
            fh.write(REGLAMENTO + "\n" + cabecera_txt + "\n\n" + "\n\n".join(bloques_txt) + "\n")
        print(f"\n  TXT guardado  →  {ruta_txt}")

        datos_json = {
            "generado"    : datetime.now().isoformat(),
            "total_fichas": len(fichas),
            "fichas"      : dicts_json,
        }
        with open(ruta_json, "w", encoding="utf-8") as fh:
            json.dump(datos_json, fh, ensure_ascii=False, indent=2)
        print(f"  JSON guardado →  {ruta_json}")

        conteos = [n for n, _ in resumenes]
        print()
        print("╔══════════════════════════════════════════════╗")
        print(f"║  Listo. {len(fichas)}/{n_fichas_prueba} casos finales de prueba generados.   ║")
        print("╚══════════════════════════════════════════════╝")
        print(f"  Tope configurado: {TOPE_CARTAS_APAGADAS_OMERTA} "
              f"| Mínimo de cartas vivas: {MINIMO_CARTAS_VIVAS_TRAS_OMERTA}")
        print(f"  Cartas silenciadas por ficha: {conteos}")
        print(f"  Promedio de silenciadas: {sum(conteos)/len(conteos):.2f}")
        print(f"  Fichas con Omertá activada (≥1 silenciada): {sum(1 for n in conteos if n > 0)}/{len(fichas)}")
        return

    # ── Modo Mixta: generación directa para sitio web ──
    if nivel == 4:
        distrito_modo = pedir_entero(
            "\n  ¿Qué DISTRITO genera las respuestas?\n"
            "  [0] = Cíclico,  [1] = Distrito Industrial,  [2] = Distrito Comercial: ",
            minimo=0, maximo=2
        )
        print("\n  → Modo MIXTA: generando fichas por dificultad...")
        print("  " + "─" * 46)
        carpeta = "."
        nombres = {"urbano": "fichas_urbano.json", "metropoli": "fichas_metro.json", "omerta": "fichas_omerta.json"}
        n_fichas_por_dif = {"urbano": 5, "metropoli": 7, "omerta": 9}
        total = 0
        for dif in ("urbano", "metropoli", "omerta"):
            n_fichas_dif = n_fichas_por_dif[dif]
            # Igual que en el flujo normal: el cierre del Caso (ficha-conclusión)
            # solo se intenta con distrito cíclico (0); con distrito fijo (1 o 2)
            # no hay nada que comparar/desempatar entre distritos.
            if distrito_modo == 0:
                resultado_caso = generar_caso(
                    n_fichas=n_fichas_dif,
                    cantidad_fija=None,
                    dificultad=dif,
                    n_sosp_fijo=0,
                    seed=None,
                )
                fichas = resultado_caso["fichas"]
                if not fichas:
                    print(f"\n  ✗ No se encontraron fichas para {dif.upper()}. Saltando.")
                    continue
                mezclar_y_renumerar(fichas, distrito_modo=0)
                ruta = os.path.join(carpeta, nombres[dif])
                # exportar_caso escribe ruta_base.txt y ruta_base.json; acá solo
                # nos interesa el JSON, así que exportamos a una ruta temporal
                # y luego nos quedamos únicamente con el .json, descartando el .txt.
                ruta_base, _ext = os.path.splitext(ruta)
                exportar_caso(resultado_caso, ruta_base, jugable=False)
                ruta_txt_temp = f"{ruta_base}.txt"
                if os.path.exists(ruta_txt_temp):
                    os.remove(ruta_txt_temp)
                ruta_json_temp = f"{ruta_base}.json"
                if ruta_json_temp != ruta:
                    os.replace(ruta_json_temp, ruta)
                n_exportadas = len(fichas) + (1 if resultado_caso["ficha_conclusion"] is not None else 0)
                if resultado_caso["ficha_conclusion"] is None:
                    print(f"  ⚠ {dif.upper()}: sin ficha-conclusión ({resultado_caso.get('motivo', 'no convergió')}).")
                total += n_exportadas
            else:
                fichas = generar_fichas(
                    n_fichas=n_fichas_dif,
                    cantidad_fija=None,
                    seed=None,
                    n_sosp_fijo=0,
                    dificultad=dif,
                    distrito_modo=distrito_modo,
                )
                if not fichas:
                    print(f"\n  ✗ No se encontraron fichas para {dif.upper()}. Saltando.")
                    continue
                mezclar_y_renumerar(fichas, distrito_modo=distrito_modo)
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
    rango_sosp_por_dif = {"urbano": (3, 5), "metropoli": (4, 6), "omerta": (6, 8)}
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

    # ── Distrito que genera las respuestas ──
    distrito_modo = pedir_entero(
        "\n  ¿Qué DISTRITO genera las respuestas?\n"
        "  [0] = Cíclico,  [1] = Distrito Industrial,  [2] = Distrito Comercial: ",
        minimo=0, maximo=2
    )
    if distrito_modo == 0:
        print("  → Distrito Cíclico por ficha.")
    else:
        print(f"  → Distrito fijo: {nombre_distrito(distrito_modo)}.")

    # ── Cantidad de verdades (solo si los sospechosos son fijos) ──
    min_verdades_dif = {"urbano": 1, "metropoli": 2, "omerta": 3}[dificultad]
    if n_sosp_fijo == 0:
        cantidad_fija = None
        print("  -> Cantidad de verdades aleatoria por ficha.")
    else:
        max_verdades = n_sosp_fijo - min_verdades_dif  # deja lugar al mínimo de mentiras también
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
        "\n  ¿Cuántas fichas generar? \n  Ingresá [1–50]: ",
        minimo=1, maximo=50
    )

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

    # ── Generación normal, sin cierre de Caso ──
    # Las opciones 1/2/3 (Urbano/Metrópoli/Omertà) generan únicamente fichas
    # sueltas, nunca ficha-conclusión. El cierre de Caso completo solo ocurre
    # en el modo Mixta (opción 4, para metro/omertà) y en Caso Final (opción 5,
    # que arma su propio Distrito 3 sintético y no pasa por aquí).
    fichas = generar_fichas(
        n_fichas=n_fichas,
        cantidad_fija=cantidad_fija,
        seed=seed,
        n_sosp_fijo=n_sosp_fijo,
        dificultad=dificultad,
        distrito_modo=distrito_modo,
    )

    if not fichas:
        print("\n  No se encontraron fichas válidas. Probá con otros parámetros.")
        return

    mezclar_y_renumerar(fichas, distrito_modo=distrito_modo)

    if jugable:
        exportar_txt_jugable(fichas, ruta_txt)
    else:
        exportar_txt(fichas, ruta_txt)
    exportar_json(fichas, ruta_json)

    print()
    print("╔══════════════════════════════════════════════╗")
    print(f"║  Listo. {len(fichas)} fichas generadas.{' ' * (22 - len(str(len(fichas))))}       ║")
    print("╚══════════════════════════════════════════════╝")
