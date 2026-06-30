// ── AYUDA: PISTAS Y CATEGORÍAS ───────────────────────────────────────────────
// Carga los índices de ayuda (json/categorias.json y json/pistas.json) y
// expone un modal que se abre al hacer clic en el número o la categoría
// de una carta dentro de una declaración.
//
// Nota: todos los estilos del modal se inyectan desde aquí (no dependen de
// css/estilo.css) para evitar problemas de caché del navegador con el CSS.

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

// ── ESTILOS (inyectados, autosuficientes) ───────────────────────────────────
function inyectarEstilosAyuda() {
  if (document.getElementById('estilos-ayuda')) return;
  const style = document.createElement('style');
  style.id = 'estilos-ayuda';
  style.textContent = `
    .ayuda-clicable {
      cursor: pointer !important;
      display: inline-block;
      transition: color .25s, text-decoration-color .25s;
      text-decoration: underline;
      text-decoration-style: dotted;
      text-decoration-color: rgba(184,147,58,.45);
      text-underline-offset: .22em;
    }
    .ayuda-clicable:hover {
      color: #b8933a;
      text-decoration-color: #b8933a;
    }

    #modal-ayuda {
      position: fixed; inset: 0; z-index: 999999;
      display: none; align-items: center; justify-content: center;
      background: radial-gradient(ellipse at 50% 40%, rgba(26,22,16,.92) 0%, rgba(8,6,4,.95) 100%);
      backdrop-filter: blur(4px);
      padding: 1.25rem;
      opacity: 0;
      transition: opacity .25s ease;
      font-family: 'Crimson Text', Georgia, serif;
    }
    #modal-ayuda.activo { opacity: 1; }

    #modal-ayuda .modal-ayuda-caja {
      position: relative;
      background: linear-gradient(180deg, rgba(184,147,58,.06) 0%, transparent 16%), #1a1610;
      border: 1px solid rgba(184,147,58,.4);
      box-shadow: 0 24px 60px rgba(0,0,0,.65), inset 0 0 40px rgba(0,0,0,.35);
      max-width: 560px; width: 100%;
      max-height: 80vh; overflow-y: auto;
      padding: 2.1rem 2rem 2rem;
      border-radius: 3px;
      transform: scale(.94) translateY(8px);
      opacity: 0;
      transition: transform .3s cubic-bezier(.22,1,.36,1), opacity .3s ease;
      box-sizing: border-box;
    }
    #modal-ayuda.activo .modal-ayuda-caja {
      transform: scale(1) translateY(0);
      opacity: 1;
    }

    #modal-ayuda .modal-ayuda-caja::before {
      content: '✦';
      position: absolute;
      top: -.65em; left: 50%; transform: translateX(-50%);
      color: #b8933a;
      background: #1a1610;
      padding: 0 .6rem;
      font-size: .95rem;
    }

    #modal-ayuda .modal-ayuda-cerrar {
      position: absolute; top: .55rem; right: .65rem;
      width: 1.9rem; height: 1.9rem;
      display: flex; align-items: center; justify-content: center;
      background: none; border: 1px solid rgba(184,147,58,.3); border-radius: 50%;
      color: #8a7d65; font-size: 1.15rem; line-height: 1;
      cursor: pointer; transition: color .2s, border-color .2s, transform .2s, background .2s;
      padding: 0;
    }
    #modal-ayuda .modal-ayuda-cerrar:hover {
      color: #9b2020;
      border-color: #9b2020;
      background: rgba(122,26,26,.12);
      transform: rotate(90deg);
    }

    #modal-ayuda .modal-ayuda-eyebrow {
      font-family: 'Special Elite', monospace; font-size: .7rem;
      letter-spacing: .22em; text-transform: uppercase;
      color: #b8933a; margin-bottom: .55rem;
      display: flex; align-items: center; gap: .55rem;
    }
    #modal-ayuda .modal-ayuda-eyebrow::after {
      content: ''; flex: 1; height: 1px;
      background: linear-gradient(90deg, rgba(184,147,58,.5), transparent);
    }

    #modal-ayuda .modal-ayuda-titulo {
      font-family: 'Playfair Display', serif; font-weight: 700;
      font-size: 1.55rem; color: #e8dcc4; margin-bottom: 1.1rem;
      padding-right: 1.5rem; letter-spacing: .01em;
    }

    #modal-ayuda .modal-ayuda-texto {
      font-size: 1.06rem; line-height: 1.75; color: #d4c9a8;
      font-style: italic; white-space: pre-line;
      border-left: 2px solid rgba(184,147,58,.3);
      padding-left: 1.1rem;
    }

    @media (max-width: 600px) {
      #modal-ayuda .modal-ayuda-caja { padding: 1.8rem 1.3rem 1.5rem; max-height: 85vh; }
      #modal-ayuda .modal-ayuda-titulo { font-size: 1.25rem; }
      #modal-ayuda .modal-ayuda-texto { font-size: .98rem; padding-left: .85rem; }
    }
  `;
  document.head.appendChild(style);
}

// ── MODAL ─────────────────────────────────────────────────────────────────
function asegurarModalAyuda() {
  let modal = document.getElementById('modal-ayuda');
  if (modal) return modal;

  inyectarEstilosAyuda();

  modal = document.createElement('div');
  modal.id = 'modal-ayuda';
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

// El cursor pointer en los elementos clicables depende de la clase
// ayuda-clicable; nos aseguramos de que los estilos estén inyectados
// apenas se carga el script, sin esperar al primer clic.
inyectarEstilosAyuda();
