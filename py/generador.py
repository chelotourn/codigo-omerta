"""
Generador de fichas de caso — Juego de deducción noir
Busca por fuerza bruta combinaciones con solución única.
Genera salida en TXT legible y JSON técnico.

Punto de entrada. La lógica está repartida en:
  datos.py          — sospechosos, distritos, constantes
  cartas.py         — las 73 cartas, su evaluación y Omertá
  validaciones.py   — solución única y validaciones de ficha
  generacion.py     — modelo Ficha y motor de generación
  caso.py           — Caso completo y ficha-conclusión (Distrito 3)
  exportar_txt.py   — exportación a TXT (maestra y jugable)
  exportar_json.py  — exportación a JSON
  cli.py            — interfaz interactiva de consola
"""

from cli import main

if __name__ == "__main__":
    main()
    while True:
        print("\n\n...Fin")
        input()
