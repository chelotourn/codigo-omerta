# 🕶️ Código Omertá — Juego de Deducción Noir

[![Fase del Proyecto](https://img.shields.io/badge/Fase-Alfa-orange.svg)](#)
[![Licencia](https://img.shields.io/badge/Licencia-MIT-blue.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.9+-yellow.svg)](#)

> *"Un buen detective aprende más de una mentira que de una verdad."*

**Código Omertá** es un prototipo de videojuego de deducción lógica e investigación ambientado en una atmósfera de novela negra (*noir*). El núcleo del proyecto es un **motor matemático generador de acertijos por fuerza bruta** escrito en Python que garantiza la creación de fichas de casos con soluciones lógicas únicas, acompañado de una **interfaz web reactiva** diseñada para testear y jugar el concepto de manera interactiva.

---

## 🧭 Estado del Proyecto (Fase Alfa)

El proyecto se encuentra actualmente en **Fase Alfa funcional**:
1. **Generador Local (`generador.py`)**: Totalmente operativo. Capaz de procesar matrices complejas de declaraciones cruzadas, aislar paradojas lógicas y exportar casos listos para jugar tanto en formato técnico (`.json`) como en texto legible y jugable para humanos (`.txt`).
2. **Interfaz Web de Pruebas**: Un entorno *frontend* minimalista y altamente estilizado (utilizando fuentes clásicas, paletas sepia y un filtro estético de grano de película) diseñado para cargar los archivos JSON autogenerados y permitir al usuario interactuar, tachar sospechosos y marcar la veracidad o falsedad de cada testimonio en tiempo real. ¡Puedes probarla en vivo desde tu navegador!

---

## 🛠️ Arquitectura del Motor de Deducción

El generador funciona mediante un algoritmo de **búsqueda por fuerza bruta con filtrado condicional estricto**. No se limita a asignar datos al azar; valida las reglas del universo matemático del juego para que el acertijo siempre se pueda resolver por pura lógica deductiva.

### 👥 Los Sospechosos y sus Atributos
Cada sospechoso cuenta con tres variables categóricas fijas que el motor utiliza para validar las declaraciones físicas y grupales:
* **Identidad**: El Notario, La Aprendiz, El Carnicero, El Coronel, La Vidente, El Médico, El Heredero, El Archivista, El Vagabundo.
* **Clase Social**: `rico` | `media` | `pobre`
* **Grupo de Edad**: `joven` | `mediana` | `viejo`

### 🎴 Categorías de Cartas y Lógica Meta
El sistema cuenta con **72 tipos de declaraciones** divididas en capas abstractas de complejidad:
* **Directas (Acusación / Defensa)**: Apuntan a identidades fijas (*"El Carnicero lo hizo"*, *"El Notario es innocent"*).
* **Descriptivas**: Definen rasgos del asesino (*"El culpable era rico"*, *"Tenía mi misma edad"*).
* **De Veracidad**: Evalúan la honestidad de un grupo entero en la sala (*"Los viejos en la sala ocultan la verdad"*).
* **Meta-Declaraciones**: Evalúan la estructura lógica de la propia ficha (*"La mayoría de los que hablan aquí mienten"*, *"Hay uno solo que miente y ese uno soy yo"*).
* **Indirectas / Condicionales**: Estructuras avanzadas de tipo condicional material $A 
ightarrow B$ (*"Si el Vagabundo miente, entonces el asesino vino de abajo"*).

### ⚙️ Filtros de Consistencia Lógica (Anti-Paradojas)
Para asegurar la calidad del diseño de juego, el generador local aplica los siguientes filtros antes de validar una ficha como apta:
* **Protección Anti-Recursión**: Un sistema de seguimiento de nodos visitados (`_VISITADOS_EVAL`) que destruye los bucles infinitos causados por mentiras circulares en las meta-declaraciones.
* **Validación de Inversión Unívoca (Regla de la Carta 64)**: Si una afirmación global sobre el culpable es falsa, el motor comprueba que su negación sea clara y libre de ambigüedades para el jugador.
* **Filtro de Solapamiento Lógico**: Descarta fichas donde dos cartas distintas produzcan vectores idénticos de verdad para todos los candidatos, evitando la redundancia de pistas.
* **Filtro de Antecedentes Vacuos**: En cartas condicionales indirectas, descarta el caso si la condición inicial $A$ es falsa, evitando que el jugador se enfrente a verdades vacías que no aportan valor deductivo.

---

## 🎛️ Modos de Dificultad

El generador restringe el pool de cartas basado en tres niveles de experiencia seleccionables desde la consola:

| Dificultad | Descripción Técnica |
| :--- | :--- |
| **Urbano** | Casos directos. Excluye por completo mecánicas de cartas grupales e indirectas. Ideal para partidas rápidas. |
| **Metrópoli** | Nivel equilibrado. Permite la aparición de un máximo de 1 carta compleja (grupal o condicional). |
| **Omertà** | El desafío definitivo. Exige por el código de honor la inclusión obligatoria de al menos 1 carta grupal **y** al menos 1 condicional indirecta por caso. |

---

## 🚀 Guía de Uso del Generador Local

El generador se ejecuta directamente a través de la terminal interactiva en sistemas con Python instalado.

### Ejecución
```bash
python generador.py
```

### Flujo de Trabajo en Consola
1. **Selección de Dificultad**: Elige entre `Urbano` [1], `Metrópoli` [2] u `Omertà` [3].
2. **Tamaño de la Escena**: Define cuántos sospechosos se reunirán en la sala (de 3 a 8, o `0` para que sea aleatorio).
3. **Reglas de Evidencia**: Elige cuántas verdades exactas habrá en la partida (el resto de declaraciones se procesarán automáticamente como mentiras).
4. **Tamaño del Dossier**:
   * Si eliges **1 ficha**, el motor entra en *Modo Rápido*: genera el caso directamente en la pantalla de la terminal ocultando el culpable y permitiendo pulsar `[Enter]` para revelar las soluciones paso a paso.
   * Si eliges **más de una**, genera un dossier completo exportando los resultados.

### Archivos de Salida Generados
Al procesar un lote de fichas, el script guardará en la raíz del proyecto dos archivos con la marca de tiempo correspondiente:
* 📄 `fichas_YYYYMMDD_HHMMSS.txt`: Documento formateado con estética de cables telegráficos de prefectura y cajas ASCII, ideal para impresión o lectura directa, con la sección de respuestas al final.
* 🛠️ `fichas_YYYYMMDD_HHMMSS.json`: Archivo con la estructura de datos purificada, listo para ser parseado por la interfaz web o un motor externo.

---

## 💻 Integración con la Interfaz Web

La interfaz web incluida actúa como el entorno visual de testeo. Está construida en HTML5 puro y CSS adaptativo avanzado, emulando un expediente de la policía clásica.

Puedes acceder a la versión desplegada en vivo aquí:  
🚀 **[Probar Demo en GitHub Pages](https://chelotourn.github.io/codigo-omerta/)**

### ¿Cómo jugar un caso?
1. Genera tus archivos utilizando el script local en Python.
2. Abre la demo en la web o el entorno local.
3. Utiliza el módulo **"Carga de Expediente"** para arrastrar o seleccionar el archivo `.json` exportado.
4. La interfaz renderizará automáticamente las tarjetas de los sospechosos activos, sus atributos visuales y sus declaraciones en formato de lista de chequeo interactiva (`V` para Verdad, `M` para Mentira), lo que permite realizar el proceso de descarte de forma cómoda.
NOTA: Se han añadido 3 ficheros de casos en la interfaz de inicio, uno para cada nivel de dificultad. En su interior dispondrás de 10 casos jugables para evaluar el desafío

---

## 📝 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Siéntete libre de utilizar el motor generador, modificar la base de datos de las cartas o adaptar la lógica meta a tus propios desarrollos de juegos de mesa o digitales.
