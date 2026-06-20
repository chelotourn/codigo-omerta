# Generador de Fichas de Caso — Juego de Deducción Noir

Este módulo en Python es el motor lógico y generador por fuerza bruta de acertijos de deducción social con ambientación cinematográfica *noir*. El algoritmo distribuye testimonios en forma de cartas a un pool de sospechosos y valida mediante simulación exhaustiva que exista **una única solución posible (culpable único)** bajo las restricciones dadas de verdades o mentiras.

## 🚀 Características Clave (Estado Actual)

*   **Estructura Multi-Distrito Dinámica**: Los sospechosos comparten nombres e IDs fijos, pero alteran por completo sus atributos clave (Clase y Edad) según el territorio asignado. El sistema soporta el **Distrito Industrial** (Pool 1) y el **Distrito Comercial** (Pool 2).
*   **Modo Campaña / Generación de Casos**: Capacidad de agrupar *N* fichas bajo una misma corrida lógica interactiva para dar lugar a un **Caso**.
*   **Ficha-Conclusión (Operación Código Omertá)**: Implementación avanzada del concepto matemático Noir. Recolecta los culpables de las fichas previas, resuelve los solapamientos de distritos mediante un sistema de desempate por apariciones y genera una ficha final sintética sobre un **Distrito 3** mutable construido en tiempo de ejecución.
*   **Clasificación por Dificultad Exigente**:
    *   `urbano`: De 3 a 5 sospechosos. Excluye por completo cartas de lógica meta o condicionales indirectas.
    *   `metropoli`: De 4 a 6 sospechosos. Permite un máximo de 1 carta compleja (meta/indirecta).
    *   `omerta`: De 5 a 8 sospechosos. Exige de forma obligatoria la presencia de al menos 1 carta meta y 1 indirecta.
*   **Garantía de Calidad Deductiva (Anti-Solapamiento)**: Descarta fichas que contengan redundancias lógicas latentes, asegurando que no existan dos cartas en la misma partida con el mismo vector de verdad exacto para todos los candidatos.
*   **Optimización de Rendimiento Extremo**: Inyección estática de entornos (`ASIGNACION_EVAL`), control estricto de recursión infinita mediante sets de visitados en cartas autorreferenciales y cálculo optimizado de vectores de verdad en caché para evitar la explosión combinatoria.

---

## 🗺️ Arquitectura de Datos y Distritos

Cada distrito altera la ficha identitaria de los personajes presentes en la sala, complejizando el metajuego en dificultades altas:

| ID | Nombre del Sospechoso | Atributos Distrito 1 (Industrial) | Atributos Distrito 2 (Comercial) |
| :--- | :--- | :--- | :--- |
| **1** | El Notario | Rico / Viejo | Pobre / Joven |
| **2** | La Aprendiz | Media / Joven | Rico / Viejo |
| **3** | El Carnicero | Pobre / Mediana | Media / Joven |
| **4** | El Coronel | Rico / Mediana | Media / Viejo |
| **5** | La Vidente | Pobre / Viejo | Rico / Mediana |
| **6** | El Médico | Media / Joven | Rico / Viejo |
| **7** | El Heredero | Rico / Joven | Pobre / Mediana |
| **8** | El Crupier | Media / Viejo | Media / Mediana |
| **9** | El Vagabundo | Pobre / Mediana | Pobre / Joven |

---

## 🗂️ Categorías de Cartas (1 a 72)

El motor procesa de forma síncrona reglas semánticas complejas distribuidas en las siguientes categorías:

1.  **Acusación (1–11):** Apuntan a culpables específicos o combinaciones directas de sus atributos.
2.  **Defensa (12–20):** Excluyen sospechosos o descartan rasgos del culpable ("*El culpable no era rico*").
3.  **Veracidad (21–30):** Evalúan la honestidad intrínseca de subgrupos enteros presentes en la sala basados en sus condiciones físicas.
4.  **Descriptivas (31–40):** Aportan datos tangibles sobre la fisonomía, transporte o estatus del asesino.
5.  **Duda (41–50):** Cartas ambiguas, tautologías o falsedades directas que actúan como ruido lógico.
6.  **Grupal (51–56):** Relacionan coartadas y nexos entre múltiples sospechosos a la vez.
7.  **Meta (57–64):** Analizan y condicionan su veracidad al comportamiento del resto de testimonios de la ficha ("*La mayoría de las declaraciones escuchadas son mentiras*").
8.  **Indirectas (65–72):** Estructuras lógicas condicionales puras ($A \rightarrow B$). Si el antecedente no se cumple o referencia a un sospechoso ausente, la ficha se invalida o procesa el estado como información deductiva según las reglas de juego noir.

---

## ⚙️ Reglas del Motor de Fuerza Bruta

Para que una ficha sea guardada y considerada apta para impresión, el generador realiza los siguientes filtros concurrentes en su bucle principal:

1.  **Restricciones de Presencia**: Las cartas en tercera persona que nombran o dependen de un Sospechoso específico (ej. Crupier, Vagabundo) quedan prohibidas si la entidad no fue seleccionada en el muestreo de la partida.
2.  **Límite de Diversidad Estricto**: Hardcodeado para evitar la fatiga del jugador. Ninguna carta puede aparecer en más del **18%** del total de fichas generadas en la corrida.
3.  **Filtrado de Vacías**: Máximo una única carta por ficha del set de cartas triviales o narrativas (`CARTAS_SIEMPRE_VERDAD`), manteniendo el peso analítico del juego.
4.  **Validación de Solución Única**: Simula el escenario asumiendo a cada sospechoso secuencialmente como culpable. Si el conteo exacto de verdades o mentiras se cumple para más de un sospechoso, la combinación es descartada inmediatamente.

---

## 💾 Exportación y Formatos

El script genera salidas automatizadas listas para su distribución e integración:
*   **Formatos TXT (Doble Propósito):**
    *   *Modo Desarrollo:* Muestra la ficha técnica, culpable expuesto y la resolución booleana (V/M) de cada testimonio.
    *   *Modo Jugable:* Remueve las soluciones para su uso en partida impresa e inyecta un telegrama del Comisionado con el reglamento integrado en una interfaz CLI simulando cajas de texto de la época.
*   **Formatos JSON:** Representación técnica estructurada limpia de objetos `Ficha` (ideal para ser consumido por interfaces y aplicaciones web).

*   ## 💻 Integración con la Interfaz Web

La interfaz web incluida actúa como el entorno visual de testeo. Está construida en HTML5 puro y CSS adaptativo avanzado, emulando un expediente de la policía clásica.

Puedes acceder a la versión desplegada en vivo aquí:  
🚀 **[Probar Demo en GitHub Pages](https://chelotourn.github.io/codigo-omerta/)**

---

### ¿Cómo jugar un caso?
1. Genera tus archivos utilizando el script local en Python.
2. Abre la demo en la web o el entorno local.
3. Utiliza el módulo **"Carga de Expediente"** para arrastrar o seleccionar el archivo `.json` exportado.
4. La interfaz renderizará automáticamente las tarjetas de los sospechosos activos, sus atributos visuales y sus declaraciones en formato de lista de chequeo interactiva (`V` para Verdad, `M` para Mentira), lo que permite realizar el proceso de descarte de forma cómoda.

NOTA: Se han añadido 3 ficheros de casos en la interfaz de inicio, uno para cada nivel de dificultad. En su interior dispondrás de 10 casos jugables para evaluar el desafío

---

## 📝 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Siéntete libre de utilizar el motor generador, modificar la base de datos de las cartas o adaptar la lógica meta a tus propios desarrollos de juegos de mesa o digitales.
