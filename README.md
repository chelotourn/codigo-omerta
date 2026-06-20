# 🕶️ Código Omertá — Generador noir de fichas y casos

[![Estado](https://img.shields.io/badge/Estado-En%20desarrollo-orange.svg)](#)
[![Licencia](https://img.shields.io/badge/Licencia-MIT-blue.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow.svg)](#)

> *“Un buen detective aprende más de una mentira que de una verdad.”*

**Código Omertá** es un generador en Python de fichas de caso para un juego de deducción con estética noir. El núcleo del proyecto construye combinaciones de sospechosos y cartas por fuerza bruta, valida que cada caso tenga una solución lógica única y exporta el resultado en formatos **TXT** y **JSON**.

El proyecto actual está concentrado en un solo script principal: **`codigo_omerta_v0_44.py`**.

---

## Estado actual del proyecto

El motor ya incluye, a día de hoy:

- **Dos distritos jugables** con los mismos sospechosos, pero atributos distintos:
  - Distrito Industrial
  - Distrito Comercial
- **72 cartas** repartidas en categorías de acusación, defensa, veracidad, descriptivas, duda, grupales, meta e indirectas.
- **Tres dificultades**:
  - **Urbano**: sin cartas meta ni indirectas.
  - **Metrópoli**: permite como máximo 1 carta compleja por ficha.
  - **Omertà**: exige al menos 1 carta meta y 1 indirecta.
- **Modo de generación por distritos**:
  - **Cíclico**: alterna Industrial / Comercial.
  - **Fijo**: fuerza un solo distrito.
- **Fichas normales** y, cuando corresponde, un **caso cerrado** con **ficha-conclusión**.
- **Salida en consola** para jugar una ficha en pantalla y revelar después la solución.
- **Exportación** a TXT legible y JSON técnico.

---

## Qué resuelve el motor

Cada ficha contiene:

- una cantidad de sospechosos,
- una asignación de cartas a cada sospechoso,
- un culpable único,
- y un conteo exacto de verdades o mentiras.

El generador prueba candidatos hasta encontrar una configuración válida que cumpla las restricciones del modo elegido. También descarta fichas que repiten demasiado una misma carta, que contienen cartas redundantes o que rompen las reglas lógicas de las cartas indirectas.

---

## Sospechosos y distritos

Los mismos nombres se reutilizan en ambos distritos, pero con combinaciones distintas de clase social y edad.

Sospechosos base:

- El Notario
- La Aprendiz
- El Carnicero
- El Coronel
- La Vidente
- El Médico
- El Heredero
- El Crupier
- El Vagabundo

Cada uno combina:

- **Clase**: `rico` | `media` | `pobre`
- **Edad**: `joven` | `mediana` | `viejo`

---

## Cartas y categorías

El juego trabaja con estas familias de cartas:

- **Acusación**: apunta a un culpable concreto o grupo concreto.
- **Defensa**: descarta sospechosos o perfiles.
- **Veracidad**: habla sobre quién miente o dice la verdad.
- **Descriptiva**: define rasgos del culpable.
- **Duda**: afirmaciones más ambiguas o débiles.
- **Grupal**: relaciones entre varios sospechosos.
- **Meta**: evalúan la estructura lógica de la propia ficha.
- **Indirecta**: condiciones del tipo “si A, entonces B”.

---

## Filtros de validación

Antes de aceptar una ficha, el motor comprueba varias cosas:

- que exista **solución única**,
- que la dificultad elegida se respete,
- que no haya **solapamientos lógicos** entre cartas,
- que las cartas indirectas no apunten a sospechosos ausentes,
- y que el reparto de cartas mantenga diversidad dentro de la corrida.

---

## Modos de uso

Al ejecutar el script, el programa pregunta:

1. **Dificultad**
2. **Cantidad de sospechosos por ficha**
3. **Distrito de generación**
   - `0` = cíclico
   - `1` = Industrial
   - `2` = Comercial
4. **Cantidad de verdades**
5. **Cantidad de fichas**
6. **Seed**
7. **Si querés ofuscar las respuestas** en el TXT

### Modo rápido

Si pedís **1 ficha**, el script la muestra directamente en pantalla y permite revelar la solución al final.

### Dossier

Si pedís **2 a 50 fichas**, el script genera archivos en la carpeta actual.

---

## Archivos generados

### Generación normal

Cuando el caso no se cierra automáticamente, el programa genera:

- `fichas_YYYYMMDD_HHMMSS.txt`
- `fichas_YYYYMMDD_HHMMSS.json`

### Caso cerrado

Cuando se puede resolver el cierre del caso, exporta:

- `fichas_YYYYMMDD_HHMMSS.txt`
- `fichas_YYYYMMDD_HHMMSS.json`

En ese caso, el JSON incluye además un bloque `caso` con metadatos del cierre y, si existe, la ficha-conclusión.

### Modo mixto

La opción **4** genera tres archivos JSON:

- `fichas_urbano.json`
- `fichas_metro.json`
- `fichas_omerta.json`

Cada uno corresponde a una dificultad distinta.

---

## Estructura del JSON

Cada ficha exportada incluye, entre otros datos:

- `ficha_id`
- `distrito_id`
- `distrito_nombre`
- `es_conclusion`
- `n_sospechosos`
- `sospechosos_ids`
- `modo`
- `cantidad`
- `dificultad`
- `culpable_id`
- `culpable_nombre`
- `declaraciones`

Cada declaración trae su sospechoso, carta, categoría, texto y estado de verdad/mentira.

---

## Cómo ejecutar

```bash
python codigo_omerta_v0_44.py
```

---

## Requisitos

- Python 3.9 o superior
- No requiere dependencias externas

---

## Nota sobre el desarrollo

Este README refleja el estado del generador **según el script actual**. Si más adelante se reincorpora una interfaz web o se separa el motor en varios módulos, conviene ampliar esta documentación con la nueva arquitectura.

---

## Licencia

Este proyecto se distribuye bajo licencia **MIT**.
