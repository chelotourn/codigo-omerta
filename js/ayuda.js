// ── AYUDA: PISTAS Y CATEGORÍAS ───────────────────────────────────────────────
// Carga los índices de ayuda (json/categorias.json y json/pistas.json) y
// expone un modal que se abre al hacer clic en el número o la categoría
// de una carta dentro de una declaración.

let CATEGORIAS_AYUDA = {};
let PISTAS_AYUDA = {};

(function cargarAyuda() {
  fetch('json/categorias.json')
    .then(r => r.json())
    .then(d => {
      (d.categorias || []).forEach(c => { CATEGORIAS_AYUDA[c.id] = c; });
    })
    .catch(() => { /* sin ayuda de categorías disponible */ });

  fetch('json/pistas.json')
    .then(r => r.json())
    .then(d => {
      (d.cartas || []).forEach(c => { PISTAS_AYUDA[c.id] = c; });
    })
    .catch(() => { /* sin pistas disponibles */ });
})();

// ── MODAL ─────────────────────────────────────────────────────────────────
function asegurarModalAyuda() {
  let modal = document.getElementById('modal-ayuda');
  if (modal) return modal;

  modal = document.createElement('div');
  modal.id = 'modal-ayuda';
  modal.className = 'modal-ayuda-overlay';
  // Estilos inline como respaldo: garantizan el overlay aunque el CSS
  // externo no haya cargado/refrescado o exista algún conflicto de stacking.
  modal.style.cssText = `
    position: fixed; inset: 0; z-index: 999999;
    display: none; align-items: center; justify-content: center;
    background: rgba(10,8,6,.78); padding: 1.25rem;
  `;
  modal.innerHTML = `
    <div class="modal-ayuda-caja">
      <button class="modal-ayuda-cerrar" type="button" title="Cerrar" aria-label="Cerrar">×</button>
      <div class="modal-ayuda-eyebrow" id="modal-ayuda-eyebrow"></div>
      <div class="modal-ayuda-titulo" id="modal-ayuda-titulo"></div>
      <div class="modal-ayuda-texto" id="modal-ayuda-texto"></div>
    </div>`;
  document.body.appendChild(modal);

  modal.addEventListener('click', (ev) => {
    if (ev.target === modal) cerrarModalAyuda();
  });
  modal.querySelector('.modal-ayuda-cerrar').addEventListener('click', cerrarModalAyuda);
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') cerrarModalAyuda();
  });

  return modal;
}

function abrirModalAyuda({ eyebrow, titulo, texto }) {
  const modal = asegurarModalAyuda();
  modal.querySelector('#modal-ayuda-eyebrow').textContent = eyebrow || '';
  modal.querySelector('#modal-ayuda-titulo').textContent = titulo || '';
  modal.querySelector('#modal-ayuda-texto').textContent = texto || '';
  modal.style.display = 'flex';
  // pequeño respiro para que el navegador registre el estado inicial
  // antes de animar la entrada (fade + scale) al agregar la clase activo
  requestAnimationFrame(() => {
    requestAnimationFrame(() => modal.classList.add('activo'));
  });
}

function cerrarModalAyuda() {
  const modal = document.getElementById('modal-ayuda');
  if (!modal) return;
  modal.classList.remove('activo');
  setTimeout(() => { modal.style.display = 'none'; }, 250);
}

function mostrarAyudaCategoria(catId) {
  const cat = CATEGORIAS_AYUDA[catId];
  if (!cat) {
    abrirModalAyuda({
      eyebrow: 'Categoría',
      titulo: catId,
      texto: 'Sin información disponible para esta categoría.'
    });
    return;
  }
  abrirModalAyuda({
    eyebrow: `Categoría · cartas ${cat.rango}`,
    titulo: cat.titulo,
    texto: cat.explicacion
  });
}

function mostrarAyudaCarta(cartaId) {
  const pista = PISTAS_AYUDA[cartaId];
  abrirModalAyuda({
    eyebrow: `Carta #${String(cartaId).padStart(2, '0')}`,
    titulo: 'Pista de Dalton',
    texto: pista ? pista.pista : 'Dalton no tiene nada que decir sobre esta carta.'
  });
}

// ── DELEGACIÓN DE CLICS ──────────────────────────────────────────────────────
// Se delega sobre el documento para que funcione con contenido renderizado
// dinámicamente (las declaraciones se vuelven a pintar en cada ficha).
document.addEventListener('click', (ev) => {
  const numEl = ev.target.closest('.decl-id[data-carta-id]');
  if (numEl) {
    mostrarAyudaCarta(parseInt(numEl.dataset.cartaId, 10));
    return;
  }
  const catEl = ev.target.closest('.decl-cat[data-cat-id]');
  if (catEl) {
    mostrarAyudaCategoria(catEl.dataset.catId);
    return;
  }
});
