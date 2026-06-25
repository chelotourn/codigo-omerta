// ── HISTORIAL DE PROGRESO ─────────────────────────────────────────────────────
const HISTORIAL_KEY = 'codigo_omerta_historial';

// Estructura: { urbano: { generado: "...", casos: [{fichaId, correcto, seleccionId}] }, ... }
function cargarHistorial() {
  try { return JSON.parse(localStorage.getItem(HISTORIAL_KEY) || '{}'); }
  catch { return {}; }
}

function guardarResultadoHistorial(dificultad, fichaId, correcto, seleccionId, generado) {
  // No guardar historial en modo demo (sin timestamp)
  if (!generado) return;
  const h = cargarHistorial();
  // Normalizar: si el bloque existe pero es array (formato viejo), migrarlo
  if (!h[dificultad] || Array.isArray(h[dificultad])) {
    h[dificultad] = { generado: generado || null, casos: [] };
  }
  if (!h[dificultad].casos) h[dificultad].casos = [];
  h[dificultad].generado = h[dificultad].generado || generado || null;
  const casos = h[dificultad].casos;
  const existe = casos.findIndex(r => r.fichaId === fichaId);
  const entrada = { fichaId, correcto, seleccionId };
  if (existe >= 0) { casos[existe] = entrada; } else { casos.push(entrada); }
  try { localStorage.setItem(HISTORIAL_KEY, JSON.stringify(h)); } catch {}
}

function resetHistorial() {
  const dif = FICHAS.length ? (FICHAS[fichaActual] || FICHAS[0]).dificultad : null;
  const label = { urbano:'Urbano', metropoli:'Metrópoli', omerta:'Omertá' }[dif] || dif || 'esta dificultad';
  if (!confirm(`¿Reiniciar el historial de ${label}?`)) return;
  const h = cargarHistorial();
  if (dif) delete h[dif];
  FICHAS.forEach((_, i) => {
    if (estado[i]) { estado[i].resuelta = false; estado[i].correcto = null; estado[i].seleccion = null; }
  });
  try { localStorage.setItem(HISTORIAL_KEY, JSON.stringify(h)); } catch {}
  renderNav();
  if (fichaActual !== undefined) mostrarFicha(fichaActual);
}

// Reinicia solo el caso indicado (mismo criterio que resetHistorial, pero
// acotado a una única ficha): borra su entrada del historial persistido y
// reconstruye su estado en memoria desde cero.
function reiniciarCasoActual(idx) {
  const f = FICHAS[idx];
  if (!f) return;
  if (!confirm(`¿Reiniciar el Caso #${String(f.ficha_id).padStart(2,'0')}? Se perderá tu acusación y progreso en este caso.`)) return;

  const dif = f.dificultad || '';
  const h = cargarHistorial();
  if (h[dif] && h[dif].casos) {
    h[dif].casos = h[dif].casos.filter(r => r.fichaId !== f.ficha_id);
    try { localStorage.setItem(HISTORIAL_KEY, JSON.stringify(h)); } catch {}
  }

  estado[idx] = {
    seleccion:   null,
    inocentes:   new Set(),
    marcasVM:    {},
    resuelta:    false,
    correcto:    null,
    acusaciones: {},
    hilos:       [],
    chinchesVerdes:    new Set(),
    chinchesAmarillos: new Set(),
    chinchesAzules:    new Set()
  };

  renderNav();
  mostrarFicha(idx);
}

// Devuelve los casos para una dificultad validando el timestamp.
// Si no coincide con el generado del JSON actual, descarta ese bloque.
function casosHistorial(dificultad, generadoActual) {
  const h = cargarHistorial();
  const bloque = h[dificultad];
  if (!bloque) return [];
  // Formato viejo (array directo) → descartar, no tiene timestamp para validar
  if (Array.isArray(bloque)) {
    delete h[dificultad];
    try { localStorage.setItem(HISTORIAL_KEY, JSON.stringify(h)); } catch {}
    return [];
  }
  if (bloque.generado && generadoActual && bloque.generado !== generadoActual) {
    delete h[dificultad];
    try { localStorage.setItem(HISTORIAL_KEY, JSON.stringify(h)); } catch {}
    return [];
  }
  // Si el bloque no tiene timestamp pero el JSON actual sí → descartar
  if (!bloque.generado && generadoActual) {
    delete h[dificultad];
    try { localStorage.setItem(HISTORIAL_KEY, JSON.stringify(h)); } catch {}
    return [];
  }
  return bloque.casos || [];
}

function renderHistorial() {
  const contenedor = document.getElementById('historial-contenido');
  if (!contenedor) return;
  const h = cargarHistorial();
  const dificultades = [
    { key: 'urbano',    label: 'Urbano' },
    { key: 'metropoli', label: 'Metrópoli' },
    { key: 'omerta',    label: 'Omertá' },
  ];
  const conDatos = dificultades.filter(d => h[d.key] && h[d.key].length > 0);
  if (!conDatos.length) {
    contenedor.innerHTML = '<div class="historial-vacio">Sin resoluciones registradas aún.</div>';
    return;
  }
  contenedor.innerHTML = conDatos.map(({ key, label }) => {
    const casos = h[key] || [];
    const exitos  = casos.filter(c => c.correcto).length;
    const dots = casos.map(c =>
      `<div class="caso-dot ${c.correcto ? 'exito' : 'fracaso'}" title="Caso #${c.fichaId}">${c.correcto ? '✓' : '✕'}</div>`
    ).join('');
    return `<div class="historial-fila">
      <span class="historial-dif">${label}</span>
      <div class="historial-casos">${dots}</div>
      <span class="historial-stats">${exitos}/${casos.length}</span>
    </div>`;
  }).join('');
}

// Llamar al cargar la página para refrescar si hay fichas cargadas
// (renderNav() se encarga de mostrar el historial en la barra)

